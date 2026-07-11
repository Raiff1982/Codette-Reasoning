#!/usr/bin/env python3
"""Kaggle GPU training — newton-star-hard (free T4/P100 path).

HOW TO RUN (one time, ~20 min):
  1. kaggle.com -> Create -> New Notebook
  2. Settings (right panel):
       - Accelerator: GPU T4 x2 (or P100)
       - Internet: ON
  3. Add-ons -> Secrets -> add secret named HF_TOKEN with a WRITE token
  4. Paste this whole file into one cell. Run.
  5. Watch for "Done — pushed to Raiff1982/codette-newton-star-hard"

Trains ONLY newton-star-hard on newton_star_hard.jsonl (350 MMLU-Pro STEM
chains, already on the Hub). Same config as the HF Jobs run except fp16
instead of bf16 (T4/P100 have no bf16 support). Output goes to a separate
repo — the live `newton` adapter is never touched.
"""

# ── MUST be first: hide GPU 1 before torch loads ──────────────────────
# With both T4s visible, HF Trainer wraps the model in DataParallel and
# replicates it onto cuda:1 while the 4-bit weights stay on cuda:0 ->
# "Expected all tensors to be on the same device". One T4 is plenty.
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

# ── Deps — PIN transformers <5. Kaggle ships transformers v5, whose new
# parallel loader materializes fp16 tensors concurrently BEFORE bnb
# quantization: load peak ~14.25GB OOMs a 14.56GB T4 (fit fine on 24GB
# A10G). The 4.x loader quantizes shard-by-shard with a low peak.
# Pip resolves a matching older trl automatically.
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "transformers>=4.46,<5", "trl>=0.12.0", "peft>=0.7.0",
                "bitsandbytes", "accelerate", "datasets"], check=True)

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig
from trl import SFTTrainer, SFTConfig
from huggingface_hub import login

# ── HF token — Kaggle exposes secrets via UserSecretsClient, not os.environ ──
def _load_hf_token():
    try:
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret("HF_TOKEN")
    except Exception:
        pass
    return os.environ.get("HF_TOKEN")

HF_TOKEN = _load_hf_token()
assert HF_TOKEN, "Add HF_TOKEN as a Kaggle secret (Add-ons -> Secrets)"
login(token=HF_TOKEN)

BASE = "Raiff1982/codette-llama-3.1-8b-merged"
OUT = "Raiff1982/codette-newton-star-hard"

print("Loading HARD STaR dataset (MMLU-Pro STEM)...")
ds = load_dataset("Raiff1982/codette-training-data",
                  data_files="newton_star_hard.jsonl", split="train")
split = ds.train_test_split(test_size=0.05, seed=42)
print(f"train={len(split['train'])} eval={len(split['test'])}")

tok = AutoTokenizer.from_pretrained(BASE)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

# fp16 compute: T4/P100 do not support bf16
bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                         bnb_4bit_compute_dtype=torch.float16,
                         bnb_4bit_use_double_quant=True)
# device_map={"": 0} — pin the whole model to GPU 0. With "auto" on T4 x2,
# accelerate splits the model across GPUs and wraps forward in a
# functools.partial, which crashes TRL's chunked-CE lm_head patcher
# (AttributeError: 'functools.partial' object has no attribute '__func__').
# A 4-bit 8B (~5.5GB) fits comfortably in one T4's 16GB.
model = AutoModelForCausalLM.from_pretrained(
    BASE, quantization_config=bnb, torch_dtype=torch.float16,
    device_map={"": 0}, use_cache=False)

# Version-tolerant config: newer trl uses max_length, older uses
# max_seq_length; newer SFTTrainer takes processing_class, older tokenizer.
cfg_kwargs = dict(
    output_dir="newton-star-hard",
    push_to_hub=True,
    hub_model_id=OUT,
    num_train_epochs=3,
    per_device_train_batch_size=1,     # T4 is smaller than A10G
    gradient_accumulation_steps=8,
    learning_rate=1e-4,
    warmup_ratio=0.03,
    logging_steps=10,
    eval_strategy="steps",
    eval_steps=20,
    save_strategy="epoch",
    fp16=True,                          # not bf16 — T4/P100
    gradient_checkpointing=True,
    report_to="none",
)
try:
    args = SFTConfig(max_length=1536, **cfg_kwargs)
except TypeError:
    args = SFTConfig(max_seq_length=1536, **cfg_kwargs)

trainer_kwargs = dict(
    model=model,
    train_dataset=split["train"],
    eval_dataset=split["test"],
    peft_config=LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                           target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                           task_type="CAUSAL_LM"),
    args=args,
)
try:
    trainer = SFTTrainer(processing_class=tok, **trainer_kwargs)
except TypeError:
    trainer = SFTTrainer(tokenizer=tok, **trainer_kwargs)
print("Training newton-star-hard on 350 MMLU-Pro STEM reasoning chains...")
trainer.train()
trainer.push_to_hub()
print("Done — pushed to", OUT)
