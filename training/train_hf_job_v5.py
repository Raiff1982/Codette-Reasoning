#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "torch",
#   "transformers==4.44.2",
#   "peft==0.12.0",
#   "trl==0.9.6",
#   "accelerate==0.33.0",
#   "bitsandbytes",
#   "datasets",
#   "huggingface_hub>=0.24.0",
#   "sentencepiece",
#   "protobuf",
#   "rich",
# ]
# ///
"""Codette LoRA Training v5 — Full Updated Pipeline

What's new vs v4/train_hf_job.py:
  - uv inline script metadata (PEP 723) — no subprocess pip install
  - Ethics field dataset (ethics_field_awareness category)
  - Style-adaptive dataset (5-register paired examples)
  - Style supplement files for all adapters
  - Updated integrity dataset with ethics_field examples
  - Base: Raiff1982/codette-llama-3.1-8b-merged (not raw Llama)
  - LR: 1e-4 (gentler for fine-tuned base)

Submit via:
    hf jobs run training/train_hf_job_v5.py

Or with explicit hardware:
    hf jobs run --flavor a10g-small training/train_hf_job_v5.py
"""

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

# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════
MODEL_NAME   = "Raiff1982/codette-llama-3.1-8b-merged"
DATASET_REPO = "Raiff1982/codette-training-data"
OUTPUT_REPO  = "Raiff1982/codette-lora-adapters"
HF_TOKEN     = os.environ.get("HF_TOKEN")
LEARNING_RATE = 1e-4   # Gentler LR for fine-tuned base

print("=" * 60)
print("Codette v5 Training Pipeline")
print(f"Base: {MODEL_NAME}")
print(f"CUDA: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory/1024**3:.1f} GB")
print(f"LR: {LEARNING_RATE}  USE_NEW_TRL: {USE_NEW_TRL}")
print("=" * 60)

# ─── Adapter definitions ──────────────────────────────────────
# (adapter_name, dataset_file, epochs)
ADAPTERS = [
    ("newton",               "newton_reasoning.jsonl",               3),
    ("davinci",              "davinci_reasoning.jsonl",               3),
    ("empathy",              "empathy_reasoning.jsonl",               3),
    ("philosophy",           "philosophy_reasoning.jsonl",            3),
    ("quantum",              "quantum_reasoning.jsonl",               3),
    ("consciousness",        "consciousness_reasoning.jsonl",         3),
    ("multi_perspective",    "multi_perspective_reasoning.jsonl",     3),
    ("systems_architecture", "systems_architecture_reasoning.jsonl",  3),
    ("orchestrator",         "orchestrator_reasoning.jsonl",          4),
    # Integrity adapter: holds ground, ethics field, style-adaptive, role transitions
    ("integrity",            "integrity_reasoning.jsonl",             4),
]

# ─── Supplement files merged into each adapter at training time ──────────────
# Each adapter gets up to 3 supplements: integrity + ethics_field + style
SUPPLEMENTS = {
    adapter: [
        f"{adapter}_integrity_supplement.jsonl",
        f"{adapter}_ethics_field_supplement.jsonl",   # new: ethics field awareness
        f"{adapter}_style_supplement.jsonl",           # new: style-adaptive examples
    ]
    for adapter, _, _ in ADAPTERS
    if adapter != "integrity"   # integrity's main dataset already has everything
}

# ─── Create output repo ───────────────────────────────────────
api = HfApi(token=HF_TOKEN)
try:
    api.create_repo(OUTPUT_REPO, private=True, token=HF_TOKEN)
    print(f"Created output repo: {OUTPUT_REPO}")
except Exception as e:
    print(f"Output repo status: {e}")

# ─── Download datasets ────────────────────────────────────────
print("\nDownloading datasets...")
dataset_dir = Path("/tmp/datasets")
dataset_dir.mkdir(exist_ok=True)

all_files_to_download = set()
for name, filename, _ in ADAPTERS:
    all_files_to_download.add(filename)
for supps in SUPPLEMENTS.values():
    for s in supps:
        all_files_to_download.add(s)
# Also download the new standalone style dataset
all_files_to_download.add("style_adaptive_reasoning.jsonl")

for filename in sorted(all_files_to_download):
    try:
        hf_hub_download(
            DATASET_REPO, filename,
            repo_type="dataset", local_dir=str(dataset_dir),
        )
        print(f"  OK: {filename}")
    except Exception as e:
        print(f"  SKIP: {filename} ({e})")

# ─── Load tokenizer + model ───────────────────────────────────
print(f"\nLoading tokenizer: {MODEL_NAME}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

print(f"Loading model (4-bit QLoRA)...")
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
    torch_dtype=torch.bfloat16,
    trust_remote_code=True,
    use_cache=False,
    token=HF_TOKEN,
)
model.gradient_checkpointing_enable()
if torch.cuda.is_available():
    print(f"Model loaded. GPU: {torch.cuda.memory_allocated()/1024**3:.2f} GB")


# ─── Helpers ──────────────────────────────────────────────────
def load_jsonl(path: Path) -> list:
    examples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    examples.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return examples


def load_with_supplements(main_path: Path, supp_files: list, dataset_dir: Path) -> list:
    """Load main dataset and merge any available supplement files."""
    if not main_path.exists():
        return []
    examples = load_jsonl(main_path)
    for supp_name in supp_files:
        supp_path = dataset_dir / supp_name
        if supp_path.exists():
            supp_ex = load_jsonl(supp_path)
            print(f"    + {len(supp_ex)} from {supp_name}")
            examples.extend(supp_ex)
        else:
            print(f"    (no {supp_name})")
    return examples


def format_example(ex):
    return {"text": tokenizer.apply_chat_template(ex["messages"], tokenize=False)}


def build_trainer(peft_model, dataset, output_dir, epochs):
    if USE_NEW_TRL:
        args = SFTConfig(
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
        return SFTTrainer(
            model=peft_model,
            args=args,
            train_dataset=dataset,
            processing_class=tokenizer,
        )
    else:
        args = TrainingArguments(
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
        return SFTTrainer(
            model=peft_model,
            args=args,
            train_dataset=dataset,
            tokenizer=tokenizer,
            dataset_text_field="text",
            max_seq_length=2048,
        )


# ─── Training loop ────────────────────────────────────────────
results = {}
failed_uploads = []
total_start = time.time()

for adapter_name, dataset_file, epochs in ADAPTERS:
    print(f"\n{'=' * 60}")
    print(f"TRAINING: {adapter_name}  ({epochs} epochs, lr={LEARNING_RATE})")
    print(f"{'=' * 60}")
    start = time.time()

    main_path = dataset_dir / dataset_file
    supp_files = SUPPLEMENTS.get(adapter_name, [])

    print(f"  Loading dataset (supplements: {len(supp_files)})...")
    examples = load_with_supplements(main_path, supp_files, dataset_dir)

    if not examples:
        print(f"  WARNING: No examples found for {adapter_name} — skipping")
        continue

    dataset = Dataset.from_list(examples).map(format_example, remove_columns=["messages"])
    print(f"  Total: {len(dataset)} examples")

    lora_config = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        task_type=TaskType.CAUSAL_LM, bias="none",
    )
    peft_model = get_peft_model(model, lora_config)
    trainable = sum(p.numel() for p in peft_model.parameters() if p.requires_grad)
    print(f"  LoRA: {trainable:,} trainable params")

    output_dir = f"/tmp/adapters/{adapter_name}"
    trainer = build_trainer(peft_model, dataset, output_dir, epochs)

    print(f"  Training...")
    result = trainer.train()
    elapsed = time.time() - start
    print(f"  DONE — loss={result.training_loss:.4f}, steps={result.global_step}, time={elapsed:.0f}s")

    peft_model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

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
        "examples": len(dataset),
        "supplements": [s for s in supp_files if (dataset_dir / s).exists()],
    }

    # Release LoRA weights before next adapter
    try:
        model = peft_model.unload()
    except Exception:
        model = peft_model.base_model.model
    del peft_model, trainer, dataset, examples
    gc.collect()
    torch.cuda.empty_cache()

# ─── Summary + retry failed uploads ──────────────────────────
total_elapsed = time.time() - total_start
print(f"\n{'=' * 60}")
print(f"ALL {len(results)} ADAPTERS TRAINED  ({total_elapsed/60:.1f} min)")
print(f"{'=' * 60}")
for name, r in results.items():
    supps = " +" + "+".join(s.split("_")[0] for s in r.get("supplements", [])) if r.get("supplements") else ""
    print(f"  {name}{supps}: loss={r['loss']:.4f}  {r['examples']} ex  {r['time_seconds']:.0f}s")

if failed_uploads:
    print(f"\nRetrying {len(failed_uploads)} failed uploads...")
    for adapter_name in failed_uploads:
        try:
            api.upload_folder(
                folder_path=f"/tmp/adapters/{adapter_name}",
                path_in_repo=adapter_name,
                repo_id=OUTPUT_REPO,
                token=HF_TOKEN,
            )
            print(f"  Retry OK: {adapter_name}")
        except Exception as e:
            print(f"  Retry FAIL: {adapter_name}: {e}")

# ─── Upload results summary ───────────────────────────────────
try:
    with open("/tmp/training_results_v5.json", "w") as f:
        json.dump({"version": 5, "results": results}, f, indent=2)
    api.upload_file(
        path_or_fileobj="/tmp/training_results_v5.json",
        path_in_repo="training_results_v5.json",
        repo_id=OUTPUT_REPO,
        token=HF_TOKEN,
    )
    print("\nResults uploaded.")
except Exception as e:
    print(f"\nResults upload failed: {e}")
    print(json.dumps(results, indent=2))

print(f"\nAdapters: https://huggingface.co/{OUTPUT_REPO}")
