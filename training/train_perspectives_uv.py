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
"""Retrain all 7 remaining perspective adapters on v2 (hand-authored) data.

One HF Job, one base-model load, adapters trained sequentially. Each uploads to
Raiff1982/codette-lora-adapters/{name}_v2 (non-destructive — live adapters
untouched until you convert + promote). Mirrors the proven empathy job.

NOTE: newton/quantum/systems_architecture contain LLM-authored technical claims;
spot-check the verify output before promoting.
"""
import json, os, gc, time, torch
from pathlib import Path
from huggingface_hub import hf_hub_download, HfApi, get_token
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
HF_TOKEN     = os.environ.get("HF_TOKEN") or get_token()

# (adapter, dataset_file, epochs) — small high-signal sets, 6 epochs like empathy.
ADAPTERS = [
    ("newton",               "newton_reasoning.jsonl",               6),
    ("davinci",              "davinci_reasoning.jsonl",              6),
    ("philosophy",           "philosophy_reasoning.jsonl",           6),
    ("quantum",              "quantum_reasoning.jsonl",              6),
    ("consciousness",        "consciousness_reasoning.jsonl",        6),
    ("multi_perspective",    "multi_perspective_reasoning.jsonl",    7),  # thinnest set
    ("systems_architecture", "systems_architecture_reasoning.jsonl", 6),
]
LR, BATCH, GA = 1e-4, 2, 2

print("=" * 60)
print("Codette PERSPECTIVE adapters retrain (v2 data) — HF Jobs A10G")
print(f"Base: {MODEL_NAME} | CUDA: {torch.cuda.is_available()}")
print("=" * 60)
assert HF_TOKEN, "HF_TOKEN not set"
api = HfApi(token=HF_TOKEN)

# --- Download datasets ---
ddir = Path("/tmp/data"); ddir.mkdir(parents=True, exist_ok=True)
for _n, f, _e in ADAPTERS:
    hf_hub_download(DATASET_REPO, f, repo_type="dataset", local_dir=str(ddir))
    print(f"  downloaded {f}")

# --- Tokenizer + base model (loaded once) ---
tok = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                         bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME, quantization_config=bnb, device_map="auto",
    dtype=torch.bfloat16, trust_remote_code=True, use_cache=False, token=HF_TOKEN)
model.gradient_checkpointing_enable()
print(f"Base loaded. GPU {torch.cuda.memory_allocated()/1024**3:.2f} GB")

results = {}
for name, fname, epochs in ADAPTERS:
    print(f"\n{'='*60}\nTRAINING {name} ({epochs} ep)\n{'='*60}")
    examples = [json.loads(l) for l in open(ddir / fname, encoding="utf-8") if l.strip()]
    ds = Dataset.from_list(examples).map(
        lambda ex: {"text": tok.apply_chat_template(ex["messages"], tokenize=False)},
        remove_columns=["messages"])
    print(f"  {len(ds)} examples")

    lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                      task_type=TaskType.CAUSAL_LM, bias="none")
    pm = get_peft_model(model, lora)
    outdir = f"/tmp/adapters/{name}"

    if USE_NEW_TRL:
        args = SFTConfig(output_dir=outdir, num_train_epochs=epochs,
                         per_device_train_batch_size=BATCH, gradient_accumulation_steps=GA,
                         learning_rate=LR, warmup_ratio=0.05, logging_steps=5, save_strategy="no",
                         bf16=True, report_to="none", dataset_text_field="text", max_length=2048)
        trainer = SFTTrainer(model=pm, args=args, train_dataset=ds, processing_class=tok)
    else:
        from transformers import TrainingArguments
        args = TrainingArguments(output_dir=outdir, num_train_epochs=epochs,
                                 per_device_train_batch_size=BATCH, gradient_accumulation_steps=GA,
                                 learning_rate=LR, warmup_ratio=0.05, logging_steps=5, save_strategy="no",
                                 bf16=True, report_to="none")
        trainer = SFTTrainer(model=pm, args=args, train_dataset=ds, tokenizer=tok,
                             dataset_text_field="text", max_seq_length=2048)

    t0 = time.time(); r = trainer.train(); dt = time.time() - t0
    print(f"  done loss={r.training_loss:.4f} steps={r.global_step} {dt:.0f}s")
    pm.save_pretrained(outdir); tok.save_pretrained(outdir)
    try:
        api.upload_folder(folder_path=outdir, path_in_repo=f"{name}_v2",
                          repo_id=OUTPUT_REPO, token=HF_TOKEN)
        print(f"  uploaded {OUTPUT_REPO}/{name}_v2")
    except Exception as e:
        print(f"  UPLOAD FAILED {name}: {e}")
    results[name] = {"loss": r.training_loss, "steps": r.global_step, "examples": len(ds), "epochs": epochs}

    try:
        model = pm.unload()
    except Exception:
        model = pm.base_model.model
    del pm, trainer, ds, examples
    gc.collect(); torch.cuda.empty_cache()

print("\n" + "=" * 60 + "\nSUMMARY")
for k, v in results.items():
    print(f"  {k:22} loss={v['loss']:.4f} ex={v['examples']} ep={v['epochs']}")
try:
    p = Path("/tmp/perspectives_v2_results.json"); p.write_text(json.dumps(results, indent=2))
    api.upload_file(path_or_fileobj=str(p), path_in_repo="perspectives_v2_results.json",
                    repo_id=OUTPUT_REPO, token=HF_TOKEN)
except Exception as e:
    print("summary upload failed:", e)
print("\nAll uploaded to {name}_v2. Verify, then convert+promote.")
