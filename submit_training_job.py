#!/usr/bin/env python3
"""Submit constraint-tracker LoRA training job to HF Jobs with proper dependency setup."""

import subprocess
import json
import os
from pathlib import Path

HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    print("ERROR: HF_TOKEN environment variable not set")
    exit(1)

print("=" * 60)
print("Codette Constraint-Tracker LoRA - HF Jobs Submission")
print("=" * 60)
print(f"\nJob Configuration:")
print(f"  Base Model: Raiff1982/codette-llama-3.1-8b-merged")
print(f"  Dataset: constraint_tracking.jsonl")
print(f"  Adapter: constraint_tracker")
print(f"  Epochs: 3")
print(f"  Learning Rate: 1e-4")
print(f"  Output Repo: Raiff1982/codette-lora-adapters")

# The training script with dependency setup is train_hf_job_with_deps.py
# We'll submit it via huggingface-cli

print(f"\n" + "=" * 60)
print("Submitting job to HF Jobs...")
print("=" * 60)

result = subprocess.run([
    "huggingface-cli",
    "run",
    "--repo-type", "model",
    "--algo", "train",
    "python", "training/train_hf_job_with_deps.py"
], env={**os.environ, "HF_TOKEN": HF_TOKEN})

if result.returncode == 0:
    print("\n" + "=" * 60)
    print("✓ Job submitted successfully!")
    print("=" * 60)
    print(f"\nMonitor your training at:")
    print(f"  https://huggingface.co/Raiff1982/codette-lora-adapters")
    print(f"\nThe job will:")
    print(f"  1. Install dependencies (torch, transformers, peft, etc.)")
    print(f"  2. Download base model: codette-llama-3.1-8b-merged")
    print(f"  3. Download dataset: constraint_tracking.jsonl")
    print(f"  4. Train constraint_tracker LoRA adapter (3 epochs)")
    print(f"  5. Upload results to Raiff1982/codette-lora-adapters")
    print(f"\nEstimated time: 4-6 hours on A10G GPU")
else:
    print("\n" + "=" * 60)
    print("✗ Job submission failed")
    print("=" * 60)
    print(f"\nTroubleshooting:")
    print(f"  - Verify HF_TOKEN is set: echo $HF_TOKEN")
    print(f"  - Check huggingface-cli is installed: huggingface-cli --version")
    print(f"  - Verify you have write access to Raiff1982/codette-lora-adapters")

exit(result.returncode)
