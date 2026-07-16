#!/usr/bin/env python3
"""Kaggle one-shot: train ALL v4 voice adapters on hand-authored data.

v4 changes from v3:
  - ALL training data is hand-authored (no template-generated filler)
  - ~50 curated examples per adapter, matching v2 quality bar
  - Empathy included (53 hand-authored examples from v2)
  - Epochs bumped to 5 for the smaller datasets (overfitting is the
    lesser evil vs undertrained template soup)
  - Integrity + orchestrator excluded (separate training runs)

Datasets expected on Raiff1982/codette-training-data as {name}_v4.jsonl
(uploaded by training/upload_v4_datasets.py).

Output: Raiff1982/codette-adapters-v4/{name}/

HOW TO RUN:
  1. Kaggle -> New Notebook -> GPU T4 x2 -> Internet ON
  2. Add-ons -> Secrets -> HF_TOKEN = a WRITE token
  3. Paste this file into one cell. Run. (~2h for all eight.)
"""

import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "transformers>=4.46,<5", "trl>=0.12.0", "peft>=0.7.0",
                "bitsandbytes", "accelerate", "datasets"], check=True)

import time
import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig
from trl import SFTTrainer, SFTConfig
from huggingface_hub import login, HfApi, create_repo

def _load_hf_token():
    try:
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret("HF_TOKEN")
    except Exception:
        return os.environ.get("HF_TOKEN")

HF_TOKEN = _load_hf_token()
assert HF_TOKEN, "Add HF_TOKEN as a Kaggle secret (Add-ons -> Secrets)"
login(token=HF_TOKEN)
api = HfApi(token=HF_TOKEN)

BASE = "Raiff1982/codette-llama-3.1-8b-merged"
DATA_REPO = "Raiff1982/codette-training-data"
OUT_REPO = "Raiff1982/codette-adapters-v4"

ADAPTERS = [
    "newton", "davinci", "empathy", "philosophy", "quantum",
    "consciousness", "multi_perspective", "systems_architecture",
]
EPOCHS = 5

create_repo(OUT_REPO, private=True, exist_ok=True, token=HF_TOKEN)
already_done = set()
try:
    for f in api.list_repo_files(OUT_REPO):
        if f.endswith("adapter_model.safetensors"):
            already_done.add(f.split("/")[0])
except Exception:
    pass
print(f"Already on hub (will skip): {sorted(already_done) or 'none'}")

data_files = set()
try:
    data_files = set(api.list_repo_files(DATA_REPO, repo_type="dataset"))
except Exception:
    pass

try:
    tok = AutoTokenizer.from_pretrained(BASE)
except ValueError:
    from transformers import PreTrainedTokenizerFast
    tok = PreTrainedTokenizerFast.from_pretrained(BASE)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
assert tok.chat_template, "chat template missing"

print("Loading base (4-bit, GPU 0)...")
bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                         bnb_4bit_compute_dtype=torch.float16,
                         bnb_4bit_use_double_quant=True)
model = AutoModelForCausalLM.from_pretrained(
    BASE, quantization_config=bnb, torch_dtype=torch.float16,
    device_map={"": 0}, use_cache=False)

def build_trainer(dataset, out_dir):
    cfg_kwargs = dict(
        output_dir=out_dir, push_to_hub=False, num_train_epochs=EPOCHS,
        per_device_train_batch_size=1, gradient_accumulation_steps=8,
        learning_rate=1e-4, warmup_ratio=0.05, logging_steps=5,
        save_strategy="no", fp16=True, gradient_checkpointing=True,
        report_to="none",
    )
    try:
        args = SFTConfig(max_length=1024, **cfg_kwargs)
    except TypeError:
        args = SFTConfig(max_seq_length=1024, **cfg_kwargs)
    tk = dict(model=model, train_dataset=dataset, args=args,
              peft_config=LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                                     target_modules=["q_proj","k_proj","v_proj","o_proj"],
                                     task_type="CAUSAL_LM"))
    try:
        return SFTTrainer(processing_class=tok, **tk)
    except TypeError:
        return SFTTrainer(tokenizer=tok, **tk)

results = {}
for name in ADAPTERS:
    fname = f"{name}_v4.jsonl"
    if name in already_done:
        results[name] = "SKIP (already on hub)"
        print(f"\n=== {name}: already trained, skipping ===")
        continue
    if data_files and fname not in data_files:
        results[name] = "SKIP (no dataset)"
        print(f"\n=== {name}: {fname} not on {DATA_REPO}, skipping ===")
        continue

    print(f"\n=== TRAINING {name} ===")
    t0 = time.time()
    try:
        ds = load_dataset(DATA_REPO, data_files=fname, split="train")
        print(f"  {len(ds)} examples (hand-authored v4)")
        trainer = build_trainer(ds, f"/tmp/{name}-v4")
        for p in trainer.model.parameters():
            if p.dtype == torch.bfloat16:
                p.data = p.data.to(torch.float32 if p.requires_grad else torch.float16)
        trainer.train()
        trainer.save_model(f"/tmp/{name}-v4")
        api.upload_folder(folder_path=f"/tmp/{name}-v4", path_in_repo=name,
                          repo_id=OUT_REPO, token=HF_TOKEN,
                          commit_message=f"{name} v4 hand-authored adapter")
        results[name] = f"OK ({(time.time()-t0)/60:.0f} min)"
        print(f"  {name}: uploaded ({results[name]})")
        try:
            trainer.model.unload()
        except Exception:
            pass
        del trainer
        torch.cuda.empty_cache()
    except Exception as e:
        results[name] = f"FAILED: {type(e).__name__}: {str(e)[:120]}"
        print(f"  {name} FAILED — continuing: {e}")
        torch.cuda.empty_cache()

print("\n" + "=" * 60)
print("V4 TRAINING COMPLETE — HAND-AUTHORED DATA ONLY")
for k, v in results.items():
    print(f"  {k:<24} {v}")
print(f"\nAdapters: https://huggingface.co/{OUT_REPO}")
