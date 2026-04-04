#!/usr/bin/env python3
"""Codette LoRA Adapter Training v3 - Remaining 6 Adapters

Newton and Davinci already completed and uploaded.
This script trains ONLY the remaining 6 adapters to save GPU credits.
Robust error handling: upload failures won't kill the job.
"""

# ── Install dependencies first (HF Jobs start with bare Python) ──
import subprocess, sys
print("Installing dependencies...")
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "-q",
    "torch", "transformers", "peft", "trl", "datasets",
    "bitsandbytes", "accelerate", "huggingface_hub", "sentencepiece",
])
print("Dependencies installed.\n")

import json, os, gc, time, torch, traceback
from pathlib import Path
from huggingface_hub import hf_hub_download, HfApi
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

MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"
DATASET_REPO = "Raiff1982/codette-training-data"
OUTPUT_REPO = "Raiff1982/codette-lora-adapters"
HF_TOKEN = os.environ.get("HF_TOKEN")

# --- ONLY the 6 remaining adapters (newton & davinci already done) ---
ADAPTERS = [
    ("empathy", "empathy_reasoning.jsonl", 3),
    ("philosophy", "philosophy_reasoning.jsonl", 3),
    ("quantum", "quantum_reasoning.jsonl", 3),
    ("consciousness", "consciousness_reasoning.jsonl", 3),
    ("multi_perspective", "multi_perspective_reasoning.jsonl", 3),
    ("systems_architecture", "systems_architecture_reasoning.jsonl", 3),
]

print("=" * 60)
print("Codette LoRA Training v3 - Remaining 6 Adapters")
print("=" * 60)
print("SKIPPING: newton (done), davinci (done)")
print(f"TRAINING: {', '.join(a[0] for a in ADAPTERS)}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory/1024**3:.1f} GB")
print(f"HF Token present: {bool(HF_TOKEN)}")
print(f"USE_NEW_TRL: {USE_NEW_TRL}")

# --- Verify output repo exists ---
api = HfApi(token=HF_TOKEN)
try:
    api.repo_info(OUTPUT_REPO, token=HF_TOKEN)
    print(f"Output repo verified: {OUTPUT_REPO}")
except Exception:
    try:
        api.create_repo(OUTPUT_REPO, private=True, token=HF_TOKEN)
        print(f"Created output repo: {OUTPUT_REPO}")
    except Exception as e:
        print(f"Output repo status: {e}")

# --- Download only needed datasets ---
print("\nDownloading datasets...")
dataset_dir = Path("/tmp/datasets")
dataset_dir.mkdir(exist_ok=True)
for name, filename, _ in ADAPTERS:
    try:
        hf_hub_download(DATASET_REPO, filename, repo_type="dataset",
                        local_dir=str(dataset_dir), token=HF_TOKEN)
        print(f"  done: {name}")
    except Exception as e:
        print(f"  FAILED to download {name}: {e}")
        raise

# --- Load tokenizer ---
print("\nLoading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# --- Load model ---
print("Loading model with 4-bit QLoRA...")
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
print(f"Model loaded! GPU: {torch.cuda.memory_allocated()/1024**3:.2f} GB")

# --- Training loop ---
results = {}
failed_uploads = []
completed = []
total_start = time.time()

for adapter_idx, (adapter_name, dataset_file, epochs) in enumerate(ADAPTERS):
    print(f"\n{'=' * 60}")
    print(f"TRAINING [{adapter_idx+1}/{len(ADAPTERS)}]: {adapter_name} ({epochs} epochs)")
    print(f"{'=' * 60}")
    start = time.time()

    try:
        # Load dataset
        dataset_path = dataset_dir / dataset_file
        examples = []
        with open(dataset_path) as f:
            for line in f:
                examples.append(json.loads(line))

        def format_example(ex):
            return {"text": tokenizer.apply_chat_template(ex["messages"], tokenize=False)}

        dataset = Dataset.from_list(examples).map(format_example, remove_columns=["messages"])
        print(f"  Dataset: {len(dataset)} examples")

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
                learning_rate=2e-4,
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
                learning_rate=2e-4,
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
        print(f"  DONE! Loss: {result.training_loss:.4f}, Steps: {result.global_step}, Time: {elapsed:.0f}s")

        # Save locally
        peft_model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)
        print(f"  Saved locally to {output_dir}")

        # Upload (with error handling - don't crash the job!)
        try:
            api.upload_folder(
                folder_path=output_dir,
                path_in_repo=adapter_name,
                repo_id=OUTPUT_REPO,
                token=HF_TOKEN,
            )
            print(f"  Uploaded to {OUTPUT_REPO}/{adapter_name}")
        except Exception as e:
            print(f"  WARNING: Upload failed for {adapter_name}: {e}")
            failed_uploads.append(adapter_name)

        results[adapter_name] = {
            "loss": result.training_loss,
            "steps": result.global_step,
            "time_seconds": elapsed,
        }
        completed.append(adapter_name)

    except Exception as e:
        elapsed = time.time() - start
        print(f"  TRAINING FAILED for {adapter_name}: {e}")
        print(traceback.format_exc())
        results[adapter_name] = {
            "error": str(e),
            "time_seconds": elapsed,
        }
    finally:
        # Cleanup for next adapter
        try:
            model = peft_model.unload()
        except:
            try:
                model = peft_model.base_model.model
            except:
                pass
        for obj_name in ['peft_model', 'trainer', 'dataset']:
            # Explicit cleanup instead of exec() for code quality
            if 'peft_model' in dir() and obj_name == 'peft_model':
                try:
                    del peft_model
                except:
                    pass
            elif 'trainer' in dir() and obj_name == 'trainer':
                try:
                    del trainer
                except:
                    pass
            elif 'dataset' in dir() and obj_name == 'dataset':
                try:
                    del dataset
                except:
                    pass
        gc.collect()
        torch.cuda.empty_cache()
        print(f"  GPU after cleanup: {torch.cuda.memory_allocated()/1024**3:.2f} GB")

# --- Summary ---
total_elapsed = time.time() - total_start
print(f"\n{'=' * 60}")
print(f"TRAINING COMPLETE: {len(completed)}/{len(ADAPTERS)} adapters")
print(f"Total time: {total_elapsed/60:.1f} minutes")
print(f"{'=' * 60}")
print(f"  Previously completed: newton, davinci")
for name, r in results.items():
    if "error" in r:
        print(f"  {name}: FAILED - {r['error']}")
    else:
        print(f"  {name}: loss={r['loss']:.4f}, steps={r['steps']}, time={r['time_seconds']:.0f}s")

# --- Retry failed uploads ---
if failed_uploads:
    print(f"\nRetrying {len(failed_uploads)} failed uploads...")
    for adapter_name in list(failed_uploads):
        output_dir = f"/tmp/adapters/{adapter_name}"
        try:
            api.upload_folder(
                folder_path=output_dir,
                path_in_repo=adapter_name,
                repo_id=OUTPUT_REPO,
                token=HF_TOKEN,
            )
            print(f"  Retry SUCCESS: {adapter_name}")
            failed_uploads.remove(adapter_name)
        except Exception as e:
            print(f"  Retry FAILED: {adapter_name}: {e}")

# --- Upload results summary ---
try:
    # Load existing results if any
    existing_results = {}
    try:
        existing_path = hf_hub_download(
            OUTPUT_REPO, "training_results.json",
            repo_type="model", token=HF_TOKEN
        )
        with open(existing_path) as f:
            existing_results = json.load(f)
        print(f"Loaded existing results: {list(existing_results.keys())}")
    except:
        pass

    # Merge with new results
    existing_results.update(results)

    with open("/tmp/training_results.json", "w") as f:
        json.dump(existing_results, f, indent=2)
    api.upload_file(
        path_or_fileobj="/tmp/training_results.json",
        path_in_repo="training_results.json",
        repo_id=OUTPUT_REPO,
        token=HF_TOKEN,
    )
    print("Combined results uploaded.")
except Exception as e:
    print(f"Results upload failed: {e}")
    print("Results JSON:")
    print(json.dumps(results, indent=2))

# --- Final status ---
all_done = ["newton", "davinci"] + completed
remaining = [a[0] for a in ADAPTERS if a[0] not in completed]
print(f"\n{'=' * 60}")
print(f"OVERALL STATUS")
print(f"{'=' * 60}")
print(f"  Completed ({len(all_done)}/8): {', '.join(all_done)}")
if remaining:
    print(f"  Remaining ({len(remaining)}/8): {', '.join(remaining)}")
if failed_uploads:
    print(f"  Failed uploads: {', '.join(failed_uploads)}")
print(f"\nAdapters: https://huggingface.co/{OUTPUT_REPO}")
