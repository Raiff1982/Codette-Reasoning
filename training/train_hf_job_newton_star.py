#!/usr/bin/env python3
"""HF Jobs training: Newton adapter on STaR self-taught data.

Runs ON a Hugging Face Jobs GPU. Fine-tunes ONLY newton, on newton_star.jsonl
(Codette's own correct reasoning chains — see star_generate_newton.py).

Launch (after uploading newton_star.jsonl to the dataset repo):
    hf jobs run --flavor a10g-small \
        --secrets HF_TOKEN=hf_xxx \
        -e SCRIPT=training/train_hf_job_newton_star.py \
        <image> python training/train_hf_job_newton_star.py

Outputs to Raiff1982/codette-lora-adapters/newton-star/ — a SEPARATE name
from the live `newton` adapter. The current newton is NOT overwritten; the
new one only replaces it after GPQA proves it wins. Measure, then promote.
"""

import json
import os
from pathlib import Path

import torch
from huggingface_hub import HfApi, hf_hub_download
from transformers import (AutoModelForCausalLM, AutoTokenizer,
                          BitsAndBytesConfig)
from peft import LoraConfig, get_peft_model, TaskType

try:
    from trl import SFTTrainer, SFTConfig
    USE_NEW_TRL = True
except ImportError:
    from trl import SFTTrainer
    from transformers import TrainingArguments
    USE_NEW_TRL = False

MODEL_NAME   = "Raiff1982/codette-llama-3.1-8b-merged"
DATASET_REPO = "Raiff1982/codette-training-data"
OUTPUT_REPO  = "Raiff1982/codette-lora-adapters"
ADAPTER_NAME = "newton-star"           # separate from live `newton`
DATASET_FILE = "newton_star.jsonl"
HF_TOKEN     = os.environ.get("HF_TOKEN")
LEARNING_RATE = 1e-4
EPOCHS = 3

print(f"Base: {MODEL_NAME}")
print(f"Dataset: {DATASET_REPO}/{DATASET_FILE}")
print(f"Output: {OUTPUT_REPO}/{ADAPTER_NAME}  (live `newton` untouched)")

api = HfApi(token=HF_TOKEN)

# ─── Data ─────────────────────────────────────────────────────
local = hf_hub_download(DATASET_REPO, DATASET_FILE, repo_type="dataset",
                        token=HF_TOKEN)
examples = []
with open(local, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            try:
                examples.append(json.loads(line))
            except json.JSONDecodeError:
                pass
print(f"Loaded {len(examples)} STaR examples")
assert examples, "No training examples — did STaR generation run?"

# ─── Model ────────────────────────────────────────────────────
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

bnb = BitsAndBytesConfig(
    load_in_4bit=True, bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME, quantization_config=bnb, device_map="auto",
    torch_dtype=torch.bfloat16, use_cache=False, token=HF_TOKEN,
)
model.gradient_checkpointing_enable()

lora = LoraConfig(
    r=16, lora_alpha=32, lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    task_type=TaskType.CAUSAL_LM,
)
peft_model = get_peft_model(model, lora)
peft_model.print_trainable_parameters()

# ─── Dataset ──────────────────────────────────────────────────
from datasets import Dataset
def fmt(ex):
    return {"text": tokenizer.apply_chat_template(ex["messages"], tokenize=False)}
ds = Dataset.from_list(examples).map(fmt)

out_dir = f"/tmp/{ADAPTER_NAME}"
if USE_NEW_TRL:
    args = SFTConfig(
        output_dir=out_dir, num_train_epochs=EPOCHS,
        per_device_train_batch_size=2, gradient_accumulation_steps=4,
        learning_rate=LEARNING_RATE, warmup_ratio=0.03, logging_steps=10,
        save_steps=500, bf16=True, report_to="none",
        dataset_text_field="text", max_length=2048,
    )
    trainer = SFTTrainer(model=peft_model, args=args, train_dataset=ds,
                         processing_class=tokenizer)
else:
    args = TrainingArguments(
        output_dir=out_dir, num_train_epochs=EPOCHS,
        per_device_train_batch_size=2, gradient_accumulation_steps=4,
        learning_rate=LEARNING_RATE, warmup_ratio=0.03, logging_steps=10,
        save_steps=500, bf16=True, report_to="none",
    )
    trainer = SFTTrainer(model=peft_model, args=args, train_dataset=ds,
                         tokenizer=tokenizer, dataset_text_field="text",
                         max_seq_length=2048)

print(f"\nTraining {ADAPTER_NAME} — {len(examples)} examples, {EPOCHS} epochs")
trainer.train()

# ─── Save + upload ────────────────────────────────────────────
peft_model.save_pretrained(out_dir)
tokenizer.save_pretrained(out_dir)
try:
    api.create_repo(OUTPUT_REPO, private=True, exist_ok=True, token=HF_TOKEN)
except Exception:
    pass
api.upload_folder(folder_path=out_dir, path_in_repo=ADAPTER_NAME,
                  repo_id=OUTPUT_REPO, token=HF_TOKEN)
print(f"\nDone. Uploaded to {OUTPUT_REPO}/{ADAPTER_NAME}")
print("Next: convert to safetensors + GGUF, wire as `newton-star`,")
print("      GPQA reason mode vs newton's 34.0%. Promote only if it wins.")
