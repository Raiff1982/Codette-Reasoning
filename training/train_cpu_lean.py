#!/usr/bin/env python3
"""Pipeline 1: CPU-Lean LoRA Training for Codette Adapters

Train one adapter at a time on CPU using bf16 weights + LoRA.
Designed for machines with 16-32 GB RAM. Uses page file for overflow.

Memory:  ~18 GB peak (bf16 model + LoRA + activations)
Speed:   ~30-90s per step on Intel Core Ultra (Lunar Lake)
Time:    ~3-9 hours per adapter (depending on dataset size + epochs)

Usage:
    python train_cpu_lean.py newton
    python train_cpu_lean.py empathy --epochs 2
    python train_cpu_lean.py quantum --rank 16 --seq-len 512
    python train_cpu_lean.py --list              # Show available adapters
    python train_cpu_lean.py newton --resume      # Resume from checkpoint

The script auto-converts the trained adapter to GGUF format for inference.
Runs at BELOW_NORMAL priority so your computer stays responsive.
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
os.environ["HF_HOME"] = r"J:\hf_cache"  # Keep model cache on J: (lots of space)
os.environ["TRANSFORMERS_CACHE"] = r"J:\hf_cache"

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# ── Set background priority ────────────────────────────────────
def set_low_priority():
    """Set process to BELOW_NORMAL priority so it doesn't lag the system."""
    try:
        import ctypes
        BELOW_NORMAL = 0x00004000
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        ctypes.windll.kernel32.SetPriorityClass(handle, BELOW_NORMAL)
        print("  Process priority: BELOW_NORMAL (background-friendly)")
    except Exception:
        pass

# ── Memory monitoring ──────────────────────────────────────────
def get_memory_gb():
    """Return (used_gb, total_gb, page_used_gb, page_total_gb)."""
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
        used = (m.ullTotalPhys - m.ullAvailPhys) / 1e9
        total = m.ullTotalPhys / 1e9
        page_used = (m.ullTotalPageFile - m.ullAvailPageFile) / 1e9
        page_total = m.ullTotalPageFile / 1e9
        return used, total, page_used, page_total
    except Exception:
        return 0, 0, 0, 0

def print_memory(label=""):
    used, total, pu, pt = get_memory_gb()
    pct = (used / total * 100) if total > 0 else 0
    page_pct = (pu / pt * 100) if pt > 0 else 0
    print(f"  [{label}] RAM: {used:.1f}/{total:.1f} GB ({pct:.0f}%) | "
          f"Page: {pu:.1f}/{pt:.1f} GB ({page_pct:.0f}%)")

# ── Configuration ──────────────────────────────────────────────
PROJECT_ROOT = Path(r"J:\codette-training-lab")
DATASET_DIR = PROJECT_ROOT / "datasets"
ADAPTER_OUT = PROJECT_ROOT / "adapters"
CKPT_DIR = PROJECT_ROOT / "training" / "checkpoints"
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
    """Load chat-format JSONL dataset for an adapter."""
    cfg = ADAPTER_CONFIG[adapter_name]
    path = DATASET_DIR / cfg["dataset"]

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}\n"
            f"Run the dataset engine first: python dataset_engine/generate.py {adapter_name}"
        )

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
    """Convert chat messages to a single training string using the model's chat template."""
    try:
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    except Exception:
        # Fallback: manual formatting
        parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                parts.append(f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{content}<|eot_id|>")
            elif role == "user":
                parts.append(f"<|start_header_id|>user<|end_header_id|>\n\n{content}<|eot_id|>")
            elif role == "assistant":
                parts.append(f"<|start_header_id|>assistant<|end_header_id|>\n\n{content}<|eot_id|>")
        text = "".join(parts)
    return text


# ── Training loop ──────────────────────────────────────────────
def train_adapter(
    adapter_name,
    epochs=3,
    rank=8,
    alpha=16,
    lr=2e-4,
    batch_size=1,
    grad_accum=16,
    max_seq_len=256,
    save_steps=100,
    resume=False,
    max_examples=None,
):
    """Train a single LoRA adapter on CPU."""

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model, TaskType

    set_low_priority()
    print_memory("before model load")

    # ── Load tokenizer ──────────────────────────────────────
    print(f"\n  Loading tokenizer: {MODEL_ID}")
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        use_fast=True,
        trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    # ── Load model in bf16 ──────────────────────────────────
    print(f"  Loading model in bf16 (this takes a few minutes with page file)...")
    print(f"  If this is the first run, the model will be downloaded (~16 GB).")
    print(f"  Model cache: {os.environ.get('HF_HOME', '~/.cache/huggingface')}")

    load_start = time.time()
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True,      # Load layer-by-layer (lower peak RAM)
        device_map="cpu",
    )
    model.config.use_cache = False   # Required for gradient checkpointing
    print(f"  Model loaded in {time.time() - load_start:.0f}s")
    print_memory("after model load")

    # ── Enable gradient checkpointing ───────────────────────
    model.gradient_checkpointing_enable()
    print("  Gradient checkpointing: ON (saves ~40% activation memory)")

    # ── Configure LoRA ──────────────────────────────────────
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=rank,
        lora_alpha=alpha,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj"],  # Fewer targets = less memory
        bias="none",
    )

    model = get_peft_model(model, lora_config)
    trainable, total = model.get_nb_trainable_parameters()
    print(f"  LoRA: rank={rank}, alpha={alpha}, targets=q_proj,v_proj")
    print(f"  Trainable: {trainable:,} / {total:,} ({100*trainable/total:.4f}%)")
    print_memory("after LoRA")

    # ── Load dataset ────────────────────────────────────────
    data = load_dataset_jsonl(adapter_name, max_examples=max_examples)

    # ── Tokenize dataset ────────────────────────────────────
    print(f"  Tokenizing {len(data)} examples (max_seq_len={max_seq_len})...")
    tokenized = []
    skipped = 0
    for item in data:
        messages = item["messages"]
        text = format_chat_to_text(messages, tokenizer)

        tokens = tokenizer(
            text,
            truncation=True,
            max_length=max_seq_len,
            padding="max_length",
            return_tensors="pt",
        )
        # Only keep examples that have meaningful content
        real_tokens = (tokens["attention_mask"].sum().item())
        if real_tokens < 10:
            skipped += 1
            continue

        tokenized.append({
            "input_ids": tokens["input_ids"].squeeze(0),
            "attention_mask": tokens["attention_mask"].squeeze(0),
            "labels": tokens["input_ids"].squeeze(0).clone(),
        })

    if skipped:
        print(f"  Skipped {skipped} examples (too short)")
    print(f"  Training on {len(tokenized)} examples")

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
            print(f"  Resuming from checkpoint: {latest.name}")
            model.load_adapter(str(latest), adapter_name="default")
            step_num = int(latest.name.split("_")[1])
            start_step = step_num
            start_epoch = step_num // (len(tokenized) // grad_accum)
            print(f"  Resuming at step {start_step}, epoch ~{start_epoch}")

    # ── Optimizer ───────────────────────────────────────────
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=lr,
        weight_decay=0.01,
    )

    # ── Training loop ───────────────────────────────────────
    total_steps = (len(tokenized) * epochs) // grad_accum
    print(f"\n{'='*60}")
    print(f"  TRAINING: {adapter_name}")
    print(f"  Epochs: {epochs} | Steps: {total_steps}")
    print(f"  Batch: {batch_size} x {grad_accum} accum = {batch_size * grad_accum} effective")
    print(f"  Seq len: {max_seq_len} | LR: {lr}")
    est_time = total_steps * 60  # rough estimate: 60s/step
    print(f"  Est. time: {timedelta(seconds=est_time)}")
    print(f"{'='*60}\n")

    model.train()
    global_step = start_step
    running_loss = 0.0
    step_times = []
    best_loss = float("inf")

    for epoch in range(start_epoch, epochs):
        print(f"  --- Epoch {epoch+1}/{epochs} ---")

        # Shuffle training data each epoch
        import random
        random.shuffle(tokenized)

        accum_loss = 0.0
        accum_count = 0

        for i, batch in enumerate(tokenized):
            step_start = time.time()

            input_ids = batch["input_ids"].unsqueeze(0)       # [1, seq_len]
            attention_mask = batch["attention_mask"].unsqueeze(0)
            labels = batch["labels"].unsqueeze(0)

            # Forward pass
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )
            loss = outputs.loss / grad_accum
            loss.backward()

            accum_loss += outputs.loss.item()
            accum_count += 1

            # Gradient accumulation step
            if accum_count >= grad_accum:
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(
                    [p for p in model.parameters() if p.requires_grad],
                    max_norm=1.0,
                )
                optimizer.step()
                optimizer.zero_grad()
                global_step += 1

                avg_loss = accum_loss / accum_count
                running_loss = 0.9 * running_loss + 0.1 * avg_loss if running_loss > 0 else avg_loss
                step_time = time.time() - step_start
                step_times.append(step_time)

                # Logging
                if global_step % 5 == 0 or global_step <= 3:
                    avg_step = sum(step_times[-20:]) / len(step_times[-20:])
                    remaining = (total_steps - global_step) * avg_step
                    used, total_ram, _, _ = get_memory_gb()

                    print(
                        f"  step {global_step:>5}/{total_steps} | "
                        f"loss={avg_loss:.4f} (avg={running_loss:.4f}) | "
                        f"{avg_step:.1f}s/step | "
                        f"RAM={used:.1f}/{total_ram:.1f}GB | "
                        f"ETA={timedelta(seconds=int(remaining))}"
                    )

                # Save checkpoint
                if global_step % save_steps == 0:
                    save_path = ckpt_path / f"step_{global_step}"
                    model.save_pretrained(str(save_path))
                    print(f"  >> Checkpoint saved: {save_path.name}")

                    # Track best
                    if running_loss < best_loss:
                        best_loss = running_loss
                        best_path = ckpt_path / "best"
                        model.save_pretrained(str(best_path))

                accum_loss = 0.0
                accum_count = 0

                # Periodic memory cleanup
                if global_step % 50 == 0:
                    gc.collect()

            # Clean up per-example tensors
            del outputs, loss
            if global_step % 10 == 0:
                gc.collect()

        # End of epoch
        print(f"  Epoch {epoch+1} complete | Running loss: {running_loss:.4f}")
        gc.collect()

    # ── Save final adapter ──────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  TRAINING COMPLETE")
    print(f"{'='*60}")

    final_path = ADAPTER_OUT / f"{adapter_name}-lora-cpu"
    model.save_pretrained(str(final_path))
    tokenizer.save_pretrained(str(final_path))
    print(f"  Adapter saved: {final_path}")
    print(f"  Final loss: {running_loss:.4f}")

    if step_times:
        avg_step = sum(step_times) / len(step_times)
        total_time = sum(step_times)
        print(f"  Avg step time: {avg_step:.1f}s")
        print(f"  Total training time: {timedelta(seconds=int(total_time))}")

    print_memory("final")

    # ── Convert to GGUF ─────────────────────────────────────
    convert_to_gguf(adapter_name, final_path)

    return final_path


def convert_to_gguf(adapter_name, adapter_path):
    """Convert safetensors LoRA adapter to GGUF format for llama.cpp inference."""
    if not GGUF_CONVERTER.exists():
        print(f"\n  GGUF converter not found at: {GGUF_CONVERTER}")
        print(f"  To convert manually later:")
        print(f"    python {GGUF_CONVERTER} --base {MODEL_ID} {adapter_path}")
        return

    gguf_out = ADAPTER_OUT / f"{adapter_name}-lora-f16.gguf"
    print(f"\n  Converting to GGUF: {gguf_out.name}...")

    import subprocess
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(GGUF_CONVERTER),
                "--base", MODEL_ID,
                str(adapter_path),
                "--outfile", str(gguf_out),
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode == 0:
            size_mb = gguf_out.stat().st_size / 1e6
            print(f"  GGUF saved: {gguf_out} ({size_mb:.1f} MB)")
            print(f"  Ready for inference with codette_orchestrator.py!")
        else:
            print(f"  GGUF conversion failed: {result.stderr[:500]}")
    except Exception as e:
        print(f"  GGUF conversion error: {e}")


# ── CLI ────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="CPU-Lean LoRA Trainer for Codette",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python train_cpu_lean.py newton              # Train newton adapter
  python train_cpu_lean.py empathy --epochs 2  # Train empathy, 2 epochs
  python train_cpu_lean.py --list              # List available adapters
  python train_cpu_lean.py quantum --resume    # Resume from checkpoint

Memory: ~18 GB peak. With 16 GB RAM + page file, expect some disk swapping.
Speed: ~30-90s per training step on modern Intel CPU.
        """,
    )
    parser.add_argument("adapter", nargs="?", help="Adapter name to train")
    parser.add_argument("--list", action="store_true", help="List available adapters")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs (default: 3)")
    parser.add_argument("--rank", type=int, default=8, help="LoRA rank (default: 8)")
    parser.add_argument("--alpha", type=int, default=16, help="LoRA alpha (default: 16)")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate (default: 2e-4)")
    parser.add_argument("--seq-len", type=int, default=256, help="Max sequence length (default: 256)")
    parser.add_argument("--grad-accum", type=int, default=16, help="Gradient accumulation steps (default: 16)")
    parser.add_argument("--save-steps", type=int, default=100, help="Save checkpoint every N steps (default: 100)")
    parser.add_argument("--resume", action="store_true", help="Resume from latest checkpoint")
    parser.add_argument("--max-examples", type=int, default=None, help="Limit dataset size (for testing)")
    args = parser.parse_args()

    print("=" * 60)
    print("  CODETTE CPU-LEAN TRAINER (Pipeline 1)")
    print("=" * 60)
    print_memory("startup")

    if args.list or not args.adapter:
        print("\nAvailable adapters:")
        for name, cfg in ADAPTER_CONFIG.items():
            ds_path = DATASET_DIR / cfg["dataset"]
            status = f"{cfg['examples']} examples" if ds_path.exists() else "DATASET MISSING"
            gguf = ADAPTER_OUT / f"{name}-lora-f16.gguf"
            trained = " [TRAINED]" if gguf.exists() else ""
            print(f"  {name:24s} {status}{trained}")
        if not args.adapter:
            print("\nUsage: python train_cpu_lean.py <adapter_name>")
        return

    if args.adapter not in ADAPTER_CONFIG:
        print(f"\nUnknown adapter: {args.adapter}")
        print(f"Available: {', '.join(ADAPTER_CONFIG.keys())}")
        sys.exit(1)

    try:
        train_adapter(
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
        print("\n\n  Training interrupted by user.")
        print("  Use --resume to continue from last checkpoint.")
    except Exception as e:
        print(f"\n  Training failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
