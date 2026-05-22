#!/usr/bin/env python3
"""
Standalone Constraint-Tracker LoRA Training Script for HF Jobs
No repo cloning needed - everything is self-contained
"""

import json
import os
import gc
import time
import torch
import traceback
from pathlib import Path
from huggingface_hub import hf_hub_download, snapshot_download, HfApi
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, TaskType

try:
    from trl import SFTTrainer, SFTConfig
    USE_NEW_TRL = True
except ImportError:
    from trl import SFTTrainer
    from transformers import TrainingArguments
    USE_NEW_TRL = False

# Configuration
MODEL_NAME = "Raiff1982/codette-llama-3.1-8b-merged"
DATASET_REPO = "Raiff1982/codette-training-data"
OUTPUT_REPO = "Raiff1982/codette-lora-adapters"
HF_TOKEN = os.environ.get("HF_TOKEN")

ADAPTERS = [
    ("constraint_tracker", "constraint_tracking.jsonl", 3),
]

LEARNING_RATE = 1e-4

print("=" * 60)
print("Constraint-Tracker LoRA Training - Standalone")
print("=" * 60)
print(f"Base model: {MODEL_NAME}")
print(f"Dataset repo: {DATASET_REPO}")
print(f"Output repo: {OUTPUT_REPO}")
print(f"HF Token present: {bool(HF_TOKEN)}")
print(f"CUDA available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory/1024**3:.1f} GB")

# Create output repo if needed
api = HfApi(token=HF_TOKEN)
try:
    api.create_repo(OUTPUT_REPO, private=True, token=HF_TOKEN)
    print(f"Output repo ready: {OUTPUT_REPO}")
except:
    print(f"Output repo exists: {OUTPUT_REPO}")

# Download dataset
print("\nDownloading dataset...")
dataset_dir = Path("/tmp/datasets")
dataset_dir.mkdir(exist_ok=True)

for adapter_name, dataset_file, _ in ADAPTERS:
    try:
        hf_hub_download(DATASET_REPO, dataset_file, repo_type="dataset", local_dir=str(dataset_dir))
        print(f"  Downloaded: {dataset_file}")
    except Exception as e:
        print(f"  ERROR: Could not download {dataset_file}: {e}")
        raise

# Load tokenizer
print("\nLoading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# Load model
print(f"Loading model with QLoRA...")
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    device_map="auto",
    dtype=torch.bfloat16,
    trust_remote_code=True,
    use_cache=False,
    token=HF_TOKEN,
)
model.gradient_checkpointing_enable()
print(f"Model loaded. GPU memory: {torch.cuda.memory_allocated()/1024**3:.2f} GB")

# Training loop
results = {}
failed_uploads = []

for adapter_name, dataset_file, epochs in ADAPTERS:
    print(f"\n{'=' * 60}")
    print(f"Training: {adapter_name} ({epochs} epochs)")
    print(f"{'=' * 60}")

    start = time.time()

    # Load dataset
    dataset_path = dataset_dir / dataset_file
    if not dataset_path.exists():
        print(f"ERROR: Dataset not found: {dataset_path}")
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    examples = []
    with open(dataset_path) as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))

    print(f"  Loaded {len(examples)} examples")

    def format_example(ex):
        return {"text": tokenizer.apply_chat_template(ex["messages"], tokenize=False)}

    dataset = Dataset.from_list(examples).map(format_example, remove_columns=["messages"])

    # Configure LoRA
    lora_config = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        task_type=TaskType.CAUSAL_LM, bias="none",
    )
    peft_model = get_peft_model(model, lora_config)
    trainable = sum(p.numel() for p in peft_model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in peft_model.parameters())
    print(f"  LoRA: {trainable:,}/{total_params:,} trainable")

    output_dir = f"/tmp/adapters/{adapter_name}"

    # Configure trainer
    if USE_NEW_TRL:
        training_args = SFTConfig(
            output_dir=output_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            learning_rate=LEARNING_RATE,
            warmup_ratio=0.03,
            logging_steps=10,
            save_steps=500,
            bf16=True,
            report_to="none",
            dataset_text_field="text",
            max_length=2048,
        )
        trainer = SFTTrainer(
            model=peft_model,
            args=training_args,
            train_dataset=dataset,
            processing_class=tokenizer,
        )
    else:
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            learning_rate=LEARNING_RATE,
            warmup_ratio=0.03,
            logging_steps=10,
            save_steps=500,
            bf16=True,
            report_to="none",
        )
        trainer = SFTTrainer(
            model=peft_model,
            args=training_args,
            train_dataset=dataset,
            tokenizer=tokenizer,
            dataset_text_field="text",
            max_seq_length=2048,
        )

    # Train
    print(f"  Training...")
    result = trainer.train()
    elapsed = time.time() - start
    print(f"  Done! Loss: {result.training_loss:.4f}, Steps: {result.global_step}, Time: {elapsed:.0f}s")

    # Save locally
    peft_model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"  Saved to {output_dir}")

    # Upload
    try:
        api.upload_folder(
            folder_path=output_dir,
            path_in_repo=adapter_name,
            repo_id=OUTPUT_REPO,
            token=HF_TOKEN,
        )
        print(f"  Uploaded to {OUTPUT_REPO}/{adapter_name}")
    except Exception as e:
        print(f"  Upload failed: {e}")
        failed_uploads.append(adapter_name)

    results[adapter_name] = {
        "loss": result.training_loss,
        "steps": result.global_step,
        "time_seconds": elapsed,
    }

    # Cleanup
    try:
        model = peft_model.unload()
    except:
        model = peft_model.base_model.model
    del peft_model, trainer, dataset, examples
    gc.collect()
    torch.cuda.empty_cache()

# Summary
print(f"\n{'=' * 60}")
print(f"Training Complete!")
print(f"{'=' * 60}")
for name, r in results.items():
    print(f"  {name}: loss={r['loss']:.4f}, steps={r['steps']}, time={r['time_seconds']:.0f}s")

# Retry failed uploads
if failed_uploads:
    print(f"\nRetrying {len(failed_uploads)} failed uploads...")
    for adapter_name in failed_uploads:
        output_dir = f"/tmp/adapters/{adapter_name}"
        try:
            api.upload_folder(
                folder_path=output_dir,
                path_in_repo=adapter_name,
                repo_id=OUTPUT_REPO,
                token=HF_TOKEN,
            )
            print(f"  Retry SUCCESS: {adapter_name}")
        except Exception as e:
            print(f"  Retry FAILED: {adapter_name}: {e}")

# Upload results
try:
    with open("/tmp/training_results.json", "w") as f:
        json.dump(results, f, indent=2)
    api.upload_file(
        path_or_fileobj="/tmp/training_results.json",
        path_in_repo="training_results.json",
        repo_id=OUTPUT_REPO,
        token=HF_TOKEN,
    )
    print("Results uploaded.")
except Exception as e:
    print(f"Results upload failed: {e}")

print(f"\nAdapters available at: https://huggingface.co/{OUTPUT_REPO}")
