#!/usr/bin/env python3
"""Kaggle one-shot: train the four perspectives that were never given adapters.

    human_intuition   resilient_kindness   mathematical   bias_mitigation

All four are fully specified in `reasoning_forge/perspective_registry.py` — a
`why`, a `goal`, three concrete `answer_must` obligations and an honest
`not_for` — and none has ever had a LoRA. They are registered, unreachable, and
invisible to the router and the synthesis set. Found 2026-08-16 when a new
import-time check made the absence say so.

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
It does not generate its training data.

`J:\\codette\\perspectives.py` holds the ORIGINAL implementations of these four,
and they are slot fillers:

    templates = ["Following the chain of causality: {A} leads to {B}...", ...]
    parts = {'A': ['initial conditions', 'given parameters', ...], ...}
    return f"[Reason] {template.format(A=np.random.choice(parts['A']), ...)}"

That is the same shape as the `*_reasoning.jsonl` generator that produced ~30
unique answer shapes across 600 rows and taught every adapter to emit
boilerplate. Undoing it cost the entire v4 campaign: 419 hand-authored examples
across eight adapters, because the cure for template data is not better
templates. Training these four on the archived implementations, or on anything
generated from them, rebuilds the exact defect on purpose.

So: hand-authored only, same bar as v4. This script trains; it does not write.

DATA
----
Expects `dataset_engine/v5/{name}_reasoning.jsonl`, one chat-format record per
line, uploaded to the Hub as `{name}_v5.jsonl`. It REFUSES to train a perspective
whose file is missing or thin rather than padding it — an adapter trained on
twelve examples is worse than no adapter, because it looks like a voice.

Two of the four are voice-defining rather than technical. `resilient_kindness`
and `human_intuition` decide how she treats a person who is struggling, and
what she sounds like when she is unsure. Those examples are Jonathan's to write
or to approve; nothing here should be the first draft of them.

HOW TO RUN
----------
  1. Kaggle -> New Notebook -> GPU T4 x2 -> Internet ON
  2. Add-ons -> Secrets -> HF_TOKEN = a WRITE token
  3. Paste this file into one cell. Run.

Output: Raiff1982/codette-adapters-v5/{name}/
"""

import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "transformers>=4.46,<5", "trl>=0.12.0", "peft>=0.7.0",
                "bitsandbytes", "accelerate", "datasets"], check=True)

import time
import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig
from trl import SFTTrainer, SFTConfig
from huggingface_hub import login, HfApi, create_repo

# ── Config ───────────────────────────────────────────────────────────────────

BASE_MODEL = "Raiff1982/codette-llama-3.1-8b-merged"
DATA_REPO = "Raiff1982/codette-training-data"
OUT_REPO = "Raiff1982/codette-adapters-v5"

ADAPTERS = ["mathematical", "bias_mitigation", "human_intuition", "resilient_kindness"]

# Same hyperparameters as the v4 run, which produced adapters that verified
# clean on the voice eval. Not re-tuned: changing the recipe and the data at
# once would make a bad result uninterpretable.
EPOCHS = 5
LR = 1e-4
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05

# An adapter trained on a handful of examples is not a weak voice, it is a
# confident wrong one — multi_perspective shipped on 7 examples in v2 and was
# flagged for overfit risk ever since. v4's sets ran 48-57. Refuse below this.
MIN_EXAMPLES = 40


def _load_hf_token():
    try:
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret("HF_TOKEN")
    except Exception:
        return os.environ.get("HF_TOKEN")


def main():
    token = _load_hf_token()
    if not token:
        raise SystemExit("No HF_TOKEN. Kaggle -> Add-ons -> Secrets -> HF_TOKEN (write).")
    login(token=token)
    api = HfApi()
    create_repo(OUT_REPO, repo_type="model", exist_ok=True, private=True, token=token)

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, token=token)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    # Loaded once and reused across adapters. Reloading per adapter is most of
    # the wall clock on a T4 and buys nothing.
    print(f"Loading {BASE_MODEL} ...", flush=True)
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, quantization_config=bnb, device_map={"": 0}, token=token)
    model.config.use_cache = False

    trained, skipped = [], []

    for name in ADAPTERS:
        fn = f"{name}_v5.jsonl"
        print(f"\n{'='*60}\n{name}\n{'='*60}", flush=True)
        try:
            ds = load_dataset(DATA_REPO, data_files=fn, split="train", token=token)
        except Exception as e:
            # Absence says so. A missing dataset is not a reason to synthesise
            # one, and it must not read as "trained".
            print(f"  SKIP — no {fn} on {DATA_REPO}: {e}", flush=True)
            skipped.append((name, f"dataset missing ({fn})"))
            continue

        if len(ds) < MIN_EXAMPLES:
            print(f"  SKIP — {len(ds)} examples, below MIN_EXAMPLES={MIN_EXAMPLES}. "
                  f"Hand-author more rather than lowering the bar.", flush=True)
            skipped.append((name, f"only {len(ds)} examples"))
            continue

        print(f"  {len(ds)} examples, {EPOCHS} epochs, lr={LR}", flush=True)
        t0 = time.time()

        peft_cfg = LoraConfig(
            r=LORA_R, lora_alpha=LORA_ALPHA, lora_dropout=LORA_DROPOUT,
            bias="none", task_type="CAUSAL_LM",
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                            "gate_proj", "up_proj", "down_proj"],
        )
        cfg = SFTConfig(
            output_dir=f"/kaggle/working/{name}",
            num_train_epochs=EPOCHS,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=2,
            learning_rate=LR,
            fp16=True,
            logging_steps=5,
            save_strategy="no",
            report_to=[],
            max_seq_length=2048,
        )
        trainer = SFTTrainer(
            model=model, train_dataset=ds, peft_config=peft_cfg,
            processing_class=tokenizer, args=cfg,
        )
        trainer.train()

        out = f"/kaggle/working/{name}"
        trainer.model.save_pretrained(out)
        tokenizer.save_pretrained(out)
        api.upload_folder(folder_path=out, path_in_repo=name,
                          repo_id=OUT_REPO, repo_type="model", token=token)
        mins = (time.time() - t0) / 60
        print(f"  done in {mins:.1f} min -> {OUT_REPO}/{name}", flush=True)
        trained.append(name)

        # Detach so the next adapter trains from the clean base, not on top of
        # the one before it. Without this the fourth adapter is a stack of four.
        trainer.model.unload()
        del trainer

    print(f"\n{'='*60}\nSUMMARY\n{'='*60}")
    print(f"  trained: {trained or 'none'}")
    for n, why in skipped:
        print(f"  skipped: {n} — {why}")
    print("\nNothing is wired by training. Each adapter still needs converting, "
          "placing, a router entry and an ADAPTER_PROMPTS entry — and the "
          "prompt entry is the one that was missing for constraint_tracker.")


if __name__ == "__main__":
    main()
