# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "torch>=2.1.0",
#     "transformers>=4.44.0",
#     "datasets>=2.18.0",
#     "peft>=0.11.0",
#     "trl>=0.9.0",
#     "huggingface-hub>=0.24.0",
#     "bitsandbytes>=0.43.0",
#     "accelerate>=0.30.0",
# ]
# ///
"""Empathy LoRA retrain — self-contained HF Jobs uv script (A10G).

Why this exists: the v1 empathy adapter was trained on template-generated
filler (empathy_reasoning.jsonl v1), so it emits vacuous praise. This job
retrains ONLY the empathy adapter on the hand-authored v2 dataset.

Self-contained: declares its own deps (PEP 723), downloads the merged base
model + the v2 dataset from the Hub, trains, and uploads just the empathy
adapter. It does NOT touch the other adapters.

Hyperparameters are tuned for a small, high-signal dataset (~53 examples):
more epochs + smaller effective batch so the register actually shifts, with
r=16 to limit overfitting to specific phrasings.

Submitted by submit_empathy_uv.py via HfApi.run_uv_job.
"""

import json, os, time, torch
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

MODEL_NAME   = "Raiff1982/codette-llama-3.1-8b-merged"
DATASET_REPO = "Raiff1982/codette-training-data"
OUTPUT_REPO  = "Raiff1982/codette-lora-adapters"
ADAPTER      = "empathy"
DATASET_FILE = "empathy_reasoning.jsonl"               # v2 (uploaded by submit script)
SUPPLEMENT   = "empathy_integrity_supplement.jsonl"    # optional, merged if present
HF_TOKEN     = os.environ.get("HF_TOKEN")

# Tuned for a small high-quality dataset: enough passes to shift register,
# small effective batch for more gradient steps, gentle LR on a fine-tuned base.
EPOCHS        = 6
LEARNING_RATE = 1e-4
BATCH_SIZE    = 2
GRAD_ACCUM    = 2

print("=" * 60)
print("Codette EMPATHY LoRA retrain (v2 data) — HF Jobs A10G")
print(f"Base: {MODEL_NAME}")
print(f"CUDA: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)} "
          f"({torch.cuda.get_device_properties(0).total_memory/1024**3:.1f} GB)")
print(f"epochs={EPOCHS} lr={LEARNING_RATE} batch={BATCH_SIZE} grad_accum={GRAD_ACCUM}")
print("=" * 60)

assert HF_TOKEN, "HF_TOKEN not set in job env"
api = HfApi(token=HF_TOKEN)

# --- Download dataset (+ optional supplement) ---
data_dir = Path("/tmp/data"); data_dir.mkdir(parents=True, exist_ok=True)
hf_hub_download(DATASET_REPO, DATASET_FILE, repo_type="dataset", local_dir=str(data_dir))
examples = []
with open(data_dir / DATASET_FILE, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            examples.append(json.loads(line))
print(f"Loaded {len(examples)} v2 empathy examples")

try:
    hf_hub_download(DATASET_REPO, SUPPLEMENT, repo_type="dataset", local_dir=str(data_dir))
    with open(data_dir / SUPPLEMENT, encoding="utf-8") as f:
        supp = [json.loads(l) for l in f if l.strip()]
    examples.extend(supp)
    print(f"Merged {len(supp)} integrity supplement examples")
except Exception as e:
    print(f"No integrity supplement merged ({e})")

# --- Tokenizer ---
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# --- Model (4-bit QLoRA) ---
bnb = BitsAndBytesConfig(
    load_in_4bit=True, bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME, quantization_config=bnb, device_map="auto",
    dtype=torch.bfloat16, trust_remote_code=True, use_cache=False, token=HF_TOKEN,
)
model.gradient_checkpointing_enable()
print(f"Model loaded. GPU alloc: {torch.cuda.memory_allocated()/1024**3:.2f} GB")

def format_example(ex):
    return {"text": tokenizer.apply_chat_template(ex["messages"], tokenize=False)}

dataset = Dataset.from_list(examples).map(format_example, remove_columns=["messages"])
print(f"Training set: {len(dataset)} examples")

lora_config = LoraConfig(
    r=16, lora_alpha=32, lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    task_type=TaskType.CAUSAL_LM, bias="none",
)
peft_model = get_peft_model(model, lora_config)
trainable = sum(p.numel() for p in peft_model.parameters() if p.requires_grad)
print(f"LoRA trainable params: {trainable:,}")

output_dir = f"/tmp/adapters/{ADAPTER}"
if USE_NEW_TRL:
    args = SFTConfig(
        output_dir=output_dir, num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE, gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=LEARNING_RATE, warmup_ratio=0.05, logging_steps=5, save_strategy="no",
        bf16=True, report_to="none", dataset_text_field="text", max_length=2048,
    )
    trainer = SFTTrainer(model=peft_model, args=args, train_dataset=dataset,
                         processing_class=tokenizer)
else:
    from transformers import TrainingArguments
    args = TrainingArguments(
        output_dir=output_dir, num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE, gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=LEARNING_RATE, warmup_ratio=0.05, logging_steps=5, save_strategy="no",
        bf16=True, report_to="none",
    )
    trainer = SFTTrainer(model=peft_model, args=args, train_dataset=dataset,
                         tokenizer=tokenizer, dataset_text_field="text", max_seq_length=2048)

print("Training...")
start = time.time()
result = trainer.train()
elapsed = time.time() - start
print(f"DONE. loss={result.training_loss:.4f} steps={result.global_step} time={elapsed:.0f}s")

peft_model.save_pretrained(output_dir)
tokenizer.save_pretrained(output_dir)

# Upload to a v2 path first (non-destructive), so the live `empathy` adapter is
# only replaced after you've verified the retrain. Promote by copying later.
path_in_repo = "empathy_v2"
api.upload_folder(folder_path=output_dir, path_in_repo=path_in_repo,
                  repo_id=OUTPUT_REPO, token=HF_TOKEN)
print(f"Uploaded adapter to {OUTPUT_REPO}/{path_in_repo}")

summary = {
    "adapter": ADAPTER, "uploaded_to": path_in_repo, "base_model": MODEL_NAME,
    "examples": len(dataset), "epochs": EPOCHS, "lr": LEARNING_RATE,
    "loss": result.training_loss, "steps": result.global_step, "seconds": elapsed,
    "data_version": "v2-handauthored",
}
try:
    p = Path("/tmp/empathy_v2_results.json"); p.write_text(json.dumps(summary, indent=2))
    api.upload_file(path_or_fileobj=str(p), path_in_repo="empathy_v2_results.json",
                    repo_id=OUTPUT_REPO, token=HF_TOKEN)
except Exception as e:
    print(f"Summary upload failed: {e}\n{json.dumps(summary, indent=2)}")

print(f"\nDone. Verify {OUTPUT_REPO}/{path_in_repo}, then promote to /empathy when satisfied.")
