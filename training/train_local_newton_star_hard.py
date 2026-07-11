#!/usr/bin/env python3
"""Local CPU LoRA training — newton-star-hard (no GPU, no cloud).

Runs the same job as the HF Jobs script, but entirely on this machine's CPU
using bf16 weights + LoRA + pagefile overflow (train_cpu_lean.py's approach).
Slow (~3-9h) but free and fully local. Runs at BELOW_NORMAL priority.

Run with the Python 3.10 that pairs with J:\\Lib:
    J:\\Python310\\python.exe training/train_local_newton_star_hard.py

Base: meta-llama/Llama-3.1-8B-Instruct (cached in J:\\hf_cache; this is the
      base the OpenVINO model was converted from, so the LoRA composes cleanly).
Data: training/datasets/newton_star_hard.jsonl (350 MMLU-Pro STEM chains).
Out:  behavioral_safetensors/newton-star-hard-behavioral-lora.safetensors
"""
import os, sys, ctypes, shutil, json, time
from pathlib import Path

# ── Env: use the J:\Lib cp310 stack + cached models on J: ──────────
_SITE = r"J:\Lib\site-packages"
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)
os.environ["PATH"] = r"J:\Lib\site-packages\Library\bin" + os.pathsep + os.environ.get("PATH", "")
os.environ["HF_HOME"] = r"J:\hf_cache"
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", str(max(1, (os.cpu_count() or 4) - 1)))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ── Background priority so the machine stays usable ────────────────
try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00004000)
    print("  priority: BELOW_NORMAL", flush=True)
except Exception:
    pass

import torch
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig
from trl import SFTTrainer, SFTConfig

ROOT = Path(r"J:\codette-clean")
DATA = ROOT / "training" / "datasets" / "newton_star_hard.jsonl"
OUT_DIR = ROOT / "training" / "checkpoints_newton_star_hard"
FINAL = ROOT / "behavioral_safetensors" / "newton-star-hard-behavioral-lora.safetensors"
MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"

print(f"  torch {torch.__version__} | threads {torch.get_num_threads()}", flush=True)
print(f"  loading dataset: {DATA}", flush=True)
rows = [json.loads(l) for l in open(DATA, encoding="utf-8") if l.strip()]
print(f"  {len(rows)} chains", flush=True)

tok = AutoTokenizer.from_pretrained(MODEL_ID)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

def fmt(ex):
    return {"text": tok.apply_chat_template(ex["messages"], tokenize=False)}
ds = Dataset.from_list(rows).map(fmt, remove_columns=["messages"])

print(f"  loading base (bf16, CPU) — this is the slow part, ~several min + paging...", flush=True)
t0 = time.time()
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID, torch_dtype=torch.bfloat16, device_map="cpu", use_cache=False,
    low_cpu_mem_usage=True,
)
model.gradient_checkpointing_enable()
print(f"  base loaded in {time.time()-t0:.0f}s", flush=True)

args = SFTConfig(
    output_dir=str(OUT_DIR),
    num_train_epochs=3,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=16,
    learning_rate=1e-4,
    warmup_ratio=0.03,
    logging_steps=5,
    save_strategy="steps",   # frequent saves — survive power failures (there was one)
    save_steps=10,
    save_total_limit=2,
    bf16=True,
    use_cpu=True,           # allow bf16 training on CPU (no GPU present)
    max_length=1280,
    gradient_checkpointing=True,
    report_to="none",
    dataset_text_field="text",
    optim="adamw_torch",
)
trainer = SFTTrainer(
    model=model,
    args=args,
    train_dataset=ds,
    processing_class=tok,
    peft_config=LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"], task_type="CAUSAL_LM",
    ),
)
print(f"  training newton-star-hard — 350 chains, 3 epochs, CPU. Expect 3-9h.", flush=True)
# Resume from the latest checkpoint if a prior run left one (power-failure safe).
_ckpts = sorted(OUT_DIR.glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[-1])) if OUT_DIR.exists() else []
if _ckpts:
    print(f"  resuming from {_ckpts[-1].name}", flush=True)
    trainer.train(resume_from_checkpoint=str(_ckpts[-1]))
else:
    trainer.train()

trainer.save_model(str(OUT_DIR))
# Copy the PEFT adapter safetensors to the OV backend's adapter dir
src = OUT_DIR / "adapter_model.safetensors"
if src.exists():
    FINAL.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, FINAL)
    print(f"\n  DONE — adapter -> {FINAL}", flush=True)
else:
    print(f"\n  WARN: {src} not found; check {OUT_DIR}", flush=True)
