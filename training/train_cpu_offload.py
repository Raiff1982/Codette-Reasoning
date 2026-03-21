#!/usr/bin/env python3
"""Pipeline 2: CPU-Offload LoRA Training for Codette Adapters

Ultra-low-memory training using disk offloading and aggressive memory management.
Designed for machines where the model doesn't fit in physical RAM.
Relies heavily on Windows page file — the OS swaps model layers to/from disk.

Memory:  ~8-12 GB active RAM (rest swapped to page file)
Speed:   ~2-5 min per step (heavy disk I/O from page swapping)
Time:    ~6-24 hours per adapter (slow but reliable)

Key differences from Pipeline 1 (lean):
  - LoRA rank=4 (half the parameters)
  - Shorter sequences (128 tokens vs 256)
  - SGD optimizer (50% less memory than AdamW)
  - Aggressive garbage collection every step
  - Layer-by-layer model loading (lower peak RAM)
  - Memory monitoring with automatic abort if critical

Usage:
    python train_cpu_offload.py newton
    python train_cpu_offload.py empathy --epochs 2
    python train_cpu_offload.py --pagefile-info        # Show page file guidance
    python train_cpu_offload.py --list                 # Show available adapters
    python train_cpu_offload.py newton --resume        # Resume from checkpoint

IMPORTANT: Ensure your page file is at least 24 GB.
Run with --pagefile-info for setup instructions.
"""

import os, sys, time, json, gc, argparse, math
from pathlib import Path
from datetime import datetime, timedelta

# ── Environment bootstrap ───────────────────────────────────────
_site = r"J:\Lib\site-packages"
if _site not in sys.path:
    sys.path.insert(0, _site)
os.environ["PATH"] = (
    r"J:\Lib\site-packages\Library\bin" + os.pathsep + os.environ.get("PATH", "")
)
os.environ["HF_HOME"] = r"J:\hf_cache"
os.environ["TRANSFORMERS_CACHE"] = r"J:\hf_cache"

# Reduce torch memory overhead
os.environ["PYTORCH_NO_CUDA_MEMORY_CACHING"] = "1"
os.environ["MALLOC_TRIM_THRESHOLD_"] = "0"

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


# ── Set IDLE priority ──────────────────────────────────────────
def set_idle_priority():
    """Set process to IDLE priority — only runs when nothing else needs CPU."""
    try:
        import ctypes
        IDLE_PRIORITY = 0x00000040
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        ctypes.windll.kernel32.SetPriorityClass(handle, IDLE_PRIORITY)
        print("  Process priority: IDLE (only uses spare CPU cycles)")
    except Exception:
        pass


# ── Memory monitoring ──────────────────────────────────────────
def get_memory_info():
    """Return dict with memory stats in GB."""
    try:
        import ctypes
        class MEMSTAT(ctypes.Structure):
            _fields_ = [
                ('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
            ]
        m = MEMSTAT(dwLength=ctypes.sizeof(MEMSTAT))
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return {
            "ram_used": (m.ullTotalPhys - m.ullAvailPhys) / 1e9,
            "ram_total": m.ullTotalPhys / 1e9,
            "ram_avail": m.ullAvailPhys / 1e9,
            "page_used": (m.ullTotalPageFile - m.ullAvailPageFile) / 1e9,
            "page_total": m.ullTotalPageFile / 1e9,
            "page_avail": m.ullAvailPageFile / 1e9,
            "pct": m.dwMemoryLoad,
        }
    except Exception:
        return {"ram_used": 0, "ram_total": 0, "ram_avail": 0,
                "page_used": 0, "page_total": 0, "page_avail": 0, "pct": 0}


def check_memory_safe(label=""):
    """Check memory and warn/abort if critically low."""
    info = get_memory_info()
    print(
        f"  [{label}] RAM: {info['ram_used']:.1f}/{info['ram_total']:.1f} GB "
        f"({info['pct']}%) | Page avail: {info['page_avail']:.1f} GB"
    )
    if info["page_avail"] < 2.0:
        print(f"\n  WARNING: Page file nearly full! ({info['page_avail']:.1f} GB left)")
        print(f"  Training may crash. Increase page file size or close other programs.")
        print(f"  Run: python train_cpu_offload.py --pagefile-info")
    return info


def aggressive_cleanup():
    """Force garbage collection and release memory back to OS."""
    gc.collect()
    gc.collect()
    # On Windows, try to trim working set
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetCurrentProcess()
        # SetProcessWorkingSetSize with -1, -1 trims the working set
        kernel32.SetProcessWorkingSetSize(handle, ctypes.c_size_t(-1), ctypes.c_size_t(-1))
    except Exception:
        pass


# ── Configuration ──────────────────────────────────────────────
PROJECT_ROOT = Path(r"J:\codette-training-lab")
DATASET_DIR = PROJECT_ROOT / "datasets"
ADAPTER_OUT = PROJECT_ROOT / "adapters"
CKPT_DIR = PROJECT_ROOT / "training" / "checkpoints_offload"
GGUF_CONVERTER = Path(r"J:\TheAI\llama.cpp\convert_lora_to_gguf.py")

MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"

ADAPTER_CONFIG = {
    "newton":               {"dataset": "newton_reasoning.jsonl",               "examples": 3000},
    "davinci":              {"dataset": "davinci_reasoning.jsonl",              "examples": 2500},
    "empathy":              {"dataset": "empathy_reasoning.jsonl",              "examples": 2500},
    "philosophy":           {"dataset": "philosophy_reasoning.jsonl",           "examples": 2000},
    "quantum":              {"dataset": "quantum_reasoning.jsonl",              "examples": 2000},
    "consciousness":        {"dataset": "consciousness_reasoning.jsonl",        "examples": 3000},
    "multi_perspective":    {"dataset": "multi_perspective_reasoning.jsonl",    "examples": 2500},
    "systems_architecture": {"dataset": "systems_architecture_reasoning.jsonl", "examples": 2000},
}


# ── Dataset loading ────────────────────────────────────────────
def load_dataset_jsonl(adapter_name, max_examples=None):
    """Load chat-format JSONL dataset."""
    cfg = ADAPTER_CONFIG[adapter_name]
    path = DATASET_DIR / cfg["dataset"]
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))

    if max_examples and len(data) > max_examples:
        data = data[:max_examples]

    print(f"  Dataset: {path.name} ({len(data)} examples)")
    return data


def format_chat_to_text(messages, tokenizer):
    """Convert chat messages to training text."""
    try:
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    except Exception:
        parts = []
        for msg in messages:
            role, content = msg["role"], msg["content"]
            parts.append(f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>")
        return "<|begin_of_text|>" + "".join(parts)


# ── Training ───────────────────────────────────────────────────
def train_adapter_offload(
    adapter_name,
    epochs=2,
    rank=4,
    alpha=8,
    lr=1e-4,
    batch_size=1,
    grad_accum=8,
    max_seq_len=128,
    save_steps=50,
    resume=False,
    max_examples=None,
):
    """Train a LoRA adapter with extreme memory optimization."""

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model, TaskType

    set_idle_priority()
    check_memory_safe("startup")

    # ── Check page file is adequate ─────────────────────────
    info = get_memory_info()
    if info["page_total"] < 20:
        print(f"\n  WARNING: Page file is only {info['page_total']:.1f} GB.")
        print(f"  Recommend at least 24 GB for offload training.")
        print(f"  Run: python train_cpu_offload.py --pagefile-info")
        print(f"  Continuing anyway...\n")

    # ── Load tokenizer ──────────────────────────────────────
    print(f"\n  Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    aggressive_cleanup()

    # ── Pre-tokenize dataset BEFORE loading model ───────────
    # This way we can free the raw data before the model needs RAM
    print(f"  Pre-tokenizing dataset (before model load to save RAM)...")
    raw_data = load_dataset_jsonl(adapter_name, max_examples=max_examples)

    tokenized = []
    for item in raw_data:
        text = format_chat_to_text(item["messages"], tokenizer)
        tokens = tokenizer(
            text,
            truncation=True,
            max_length=max_seq_len,
            padding="max_length",
            return_tensors="pt",
        )
        if tokens["attention_mask"].sum().item() >= 10:
            tokenized.append({
                "input_ids": tokens["input_ids"].squeeze(0),
                "attention_mask": tokens["attention_mask"].squeeze(0),
                "labels": tokens["input_ids"].squeeze(0).clone(),
            })

    del raw_data
    aggressive_cleanup()
    print(f"  Tokenized: {len(tokenized)} examples (max_seq_len={max_seq_len})")
    check_memory_safe("after tokenize")

    # ── Load model with extreme low-memory settings ─────────
    print(f"\n  Loading model in bf16 with low_cpu_mem_usage...")
    print(f"  This will use page file heavily — expect disk activity.")
    print(f"  First run downloads ~16 GB to {os.environ['HF_HOME']}")

    load_start = time.time()
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True,
        device_map="cpu",
    )
    model.config.use_cache = False
    print(f"  Model loaded in {time.time() - load_start:.0f}s")

    # Enable gradient checkpointing (critical for memory)
    model.gradient_checkpointing_enable()
    aggressive_cleanup()
    check_memory_safe("after model load")

    # ── Configure minimal LoRA ──────────────────────────────
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=rank,
        lora_alpha=alpha,
        lora_dropout=0.0,           # No dropout saves a tiny bit of memory
        target_modules=["q_proj"],   # Single target = minimum LoRA parameters
        bias="none",
    )

    model = get_peft_model(model, lora_config)
    trainable, total = model.get_nb_trainable_parameters()
    print(f"  LoRA: rank={rank}, alpha={alpha}, target=q_proj ONLY")
    print(f"  Trainable: {trainable:,} / {total:,} ({100*trainable/total:.4f}%)")

    # ── Checkpoint handling ─────────────────────────────────
    ckpt_path = CKPT_DIR / adapter_name
    ckpt_path.mkdir(parents=True, exist_ok=True)
    start_step = 0
    start_epoch = 0

    if resume:
        latest = None
        for f in sorted(ckpt_path.glob("step_*")):
            latest = f
        if latest:
            print(f"  Resuming from: {latest.name}")
            model.load_adapter(str(latest), adapter_name="default")
            start_step = int(latest.name.split("_")[1])
            start_epoch = start_step // (len(tokenized) // grad_accum)

    aggressive_cleanup()
    check_memory_safe("ready to train")

    # ── SGD optimizer (much less memory than AdamW) ─────────
    # AdamW stores 2 extra buffers per parameter (momentum + variance)
    # SGD with momentum stores only 1 extra buffer
    optimizer = torch.optim.SGD(
        [p for p in model.parameters() if p.requires_grad],
        lr=lr,
        momentum=0.9,
        weight_decay=0.01,
    )

    # ── Training loop ───────────────────────────────────────
    total_steps = (len(tokenized) * epochs) // grad_accum
    print(f"\n{'='*60}")
    print(f"  OFFLOAD TRAINING: {adapter_name}")
    print(f"  Epochs: {epochs} | Steps: {total_steps}")
    print(f"  Effective batch: {batch_size * grad_accum}")
    print(f"  Seq len: {max_seq_len} | LR: {lr} | Optimizer: SGD+momentum")
    print(f"  Rank: {rank} | Target: q_proj only")
    est_time = total_steps * 180  # ~3 min/step with page file swapping
    print(f"  Est. time: {timedelta(seconds=est_time)} (with page file I/O)")
    print(f"{'='*60}\n")

    model.train()
    global_step = start_step
    running_loss = 0.0
    step_times = []

    for epoch in range(start_epoch, epochs):
        print(f"  --- Epoch {epoch+1}/{epochs} ---")
        import random
        random.shuffle(tokenized)

        accum_loss = 0.0
        accum_count = 0

        for i, batch in enumerate(tokenized):
            step_start = time.time()

            input_ids = batch["input_ids"].unsqueeze(0)
            attention_mask = batch["attention_mask"].unsqueeze(0)
            labels = batch["labels"].unsqueeze(0)

            # Forward + backward
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )
            loss = outputs.loss / grad_accum
            loss.backward()

            accum_loss += outputs.loss.item()
            accum_count += 1

            # Immediately free forward pass memory
            del outputs, loss
            aggressive_cleanup()

            # Gradient accumulation step
            if accum_count >= grad_accum:
                torch.nn.utils.clip_grad_norm_(
                    [p for p in model.parameters() if p.requires_grad],
                    max_norm=1.0,
                )
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)  # set_to_none saves memory
                global_step += 1

                avg_loss = accum_loss / accum_count
                running_loss = (0.9 * running_loss + 0.1 * avg_loss) if running_loss > 0 else avg_loss
                step_time = time.time() - step_start
                step_times.append(step_time)

                # Log every step (since each step is slow)
                if global_step % 2 == 0 or global_step <= 5:
                    avg_step = sum(step_times[-10:]) / len(step_times[-10:])
                    remaining = (total_steps - global_step) * avg_step
                    info = get_memory_info()

                    print(
                        f"  step {global_step:>4}/{total_steps} | "
                        f"loss={avg_loss:.4f} | "
                        f"{avg_step:.0f}s/step | "
                        f"RAM={info['ram_used']:.1f}GB page={info['page_used']:.1f}GB | "
                        f"ETA={timedelta(seconds=int(remaining))}"
                    )

                # Save checkpoint
                if global_step % save_steps == 0:
                    save_path = ckpt_path / f"step_{global_step}"
                    model.save_pretrained(str(save_path))
                    print(f"  >> Saved: {save_path.name}")
                    aggressive_cleanup()

                # Check memory safety
                if global_step % 20 == 0:
                    info = get_memory_info()
                    if info["page_avail"] < 1.0:
                        print(f"\n  CRITICAL: Only {info['page_avail']:.1f} GB page file left!")
                        print(f"  Saving emergency checkpoint and stopping...")
                        emerg_path = ckpt_path / f"emergency_step_{global_step}"
                        model.save_pretrained(str(emerg_path))
                        print(f"  Saved: {emerg_path}")
                        print(f"  Increase page file and run with --resume")
                        return str(emerg_path)

                accum_loss = 0.0
                accum_count = 0
                aggressive_cleanup()

        print(f"  Epoch {epoch+1} done | Loss: {running_loss:.4f}")
        aggressive_cleanup()

    # ── Save final ──────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  TRAINING COMPLETE: {adapter_name}")
    print(f"{'='*60}")

    final_path = ADAPTER_OUT / f"{adapter_name}-lora-offload"
    model.save_pretrained(str(final_path))
    tokenizer.save_pretrained(str(final_path))
    print(f"  Saved: {final_path}")
    print(f"  Final loss: {running_loss:.4f}")

    if step_times:
        total_time = sum(step_times)
        print(f"  Total time: {timedelta(seconds=int(total_time))}")

    # Convert to GGUF
    convert_to_gguf(adapter_name, final_path)
    return str(final_path)


def convert_to_gguf(adapter_name, adapter_path):
    """Convert to GGUF for inference."""
    if not GGUF_CONVERTER.exists():
        print(f"  GGUF converter not found. Convert manually later.")
        return

    gguf_out = ADAPTER_OUT / f"{adapter_name}-lora-f16.gguf"
    print(f"\n  Converting to GGUF...")

    import subprocess
    try:
        result = subprocess.run(
            [sys.executable, str(GGUF_CONVERTER), "--base", MODEL_ID,
             str(adapter_path), "--outfile", str(gguf_out)],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode == 0:
            print(f"  GGUF ready: {gguf_out} ({gguf_out.stat().st_size/1e6:.1f} MB)")
        else:
            print(f"  GGUF conversion failed: {result.stderr[:300]}")
    except Exception as e:
        print(f"  GGUF error: {e}")


def show_pagefile_info():
    """Show page file configuration guidance."""
    info = get_memory_info()

    print(f"""
{'='*60}
  PAGE FILE CONFIGURATION GUIDE
{'='*60}

  Current system:
    Physical RAM:  {info['ram_total']:.1f} GB
    Page file:     {info['page_total']:.1f} GB (current)
    Page available:{info['page_avail']:.1f} GB

  Recommended page file for Codette training:
    Pipeline 1 (lean):    24 GB minimum, 32 GB recommended
    Pipeline 2 (offload): 32 GB minimum, 48 GB recommended

  How to adjust page file on Windows:
  ──────────────────────────────────
  1. Open: Settings > System > About > Advanced system settings
     (or run: SystemPropertiesAdvanced.exe)

  2. Click "Settings..." under Performance

  3. Go to "Advanced" tab > "Change..." under Virtual Memory

  4. Uncheck "Automatically manage paging file size"

  5. Select C: drive (internal NVMe SSD — fastest option)

  6. Choose "Custom size":
     Initial size (MB): 32768    (32 GB)
     Maximum size (MB):  65536   (64 GB)

  7. Click "Set" then "OK"

  8. Restart required for changes to take effect

  NOTE: Page files must be on internal (non-USB) drives.
  C: is the NVMe SSD — best performance for page file swapping.

  After adjusting, verify with:
    python train_cpu_offload.py --pagefile-info
{'='*60}
""")


# ── CLI ────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="CPU-Offload LoRA Trainer for Codette (ultra-low memory)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This pipeline is designed for training with limited physical RAM.
It uses the Windows page file to swap model layers to disk as needed.
Training is slow but reliable — perfect for overnight runs.

Examples:
  python train_cpu_offload.py newton
  python train_cpu_offload.py empathy --epochs 2
  python train_cpu_offload.py --pagefile-info
  python train_cpu_offload.py --list
        """,
    )
    parser.add_argument("adapter", nargs="?", help="Adapter to train")
    parser.add_argument("--list", action="store_true", help="List adapters")
    parser.add_argument("--pagefile-info", action="store_true", help="Page file setup guide")
    parser.add_argument("--epochs", type=int, default=2, help="Epochs (default: 2)")
    parser.add_argument("--rank", type=int, default=4, help="LoRA rank (default: 4)")
    parser.add_argument("--alpha", type=int, default=8, help="LoRA alpha (default: 8)")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate (default: 1e-4)")
    parser.add_argument("--seq-len", type=int, default=128, help="Max seq length (default: 128)")
    parser.add_argument("--grad-accum", type=int, default=8, help="Grad accum (default: 8)")
    parser.add_argument("--save-steps", type=int, default=50, help="Checkpoint every N steps")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--max-examples", type=int, default=None, help="Limit dataset")
    args = parser.parse_args()

    print("=" * 60)
    print("  CODETTE CPU-OFFLOAD TRAINER (Pipeline 2)")
    print("  Ultra-low memory — page file assisted")
    print("=" * 60)

    if args.pagefile_info:
        show_pagefile_info()
        return

    if args.list or not args.adapter:
        print("\nAvailable adapters:")
        for name, cfg in ADAPTER_CONFIG.items():
            ds = DATASET_DIR / cfg["dataset"]
            status = f"{cfg['examples']} examples" if ds.exists() else "MISSING"
            gguf = ADAPTER_OUT / f"{name}-lora-f16.gguf"
            trained = " [TRAINED]" if gguf.exists() else ""
            print(f"  {name:24s} {status}{trained}")
        if not args.adapter:
            print("\nUsage: python train_cpu_offload.py <adapter_name>")
        return

    if args.adapter not in ADAPTER_CONFIG:
        print(f"\nUnknown adapter: {args.adapter}")
        print(f"Available: {', '.join(ADAPTER_CONFIG.keys())}")
        sys.exit(1)

    try:
        train_adapter_offload(
            adapter_name=args.adapter,
            epochs=args.epochs,
            rank=args.rank,
            alpha=args.alpha,
            lr=args.lr,
            max_seq_len=args.seq_len,
            grad_accum=args.grad_accum,
            save_steps=args.save_steps,
            resume=args.resume,
            max_examples=args.max_examples,
        )
    except KeyboardInterrupt:
        print("\n\n  Interrupted. Use --resume to continue.")
    except Exception as e:
        print(f"\n  Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
