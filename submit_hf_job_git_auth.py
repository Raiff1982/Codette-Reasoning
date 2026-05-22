#!/usr/bin/env python3
"""
Submit constraint-tracker LoRA training job to HF Jobs by cloning the repo with auth.
Uses HF_TOKEN for git authentication.
"""

import os
import json
from pathlib import Path
from huggingface_hub import HfApi

HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    print("ERROR: HF_TOKEN environment variable not set")
    exit(1)

print("=" * 70)
print("Codette Constraint-Tracker LoRA - HF Jobs (Git + HF Auth)")
print("=" * 70)

# Configuration
MODEL_REPO = "Raiff1982/codette-llama-3.1-8b-merged"
DATASET_REPO = "Raiff1982/codette-training-data"
OUTPUT_REPO = "Raiff1982/codette-lora-adapters"

print(f"\nJob Configuration:")
print(f"  Base Model: {MODEL_REPO}")
print(f"  Dataset: constraint_tracking.jsonl")
print(f"  Adapter: constraint_tracker")
print(f"  Epochs: 3, LR: 1e-4")
print(f"  Output Repo: {OUTPUT_REPO}")

print(f"\n" + "=" * 70)
print("Submitting job to HF Jobs...")
print("=" * 70)

api = HfApi(token=HF_TOKEN)

# Create job script with proper git authentication
job_script = """#!/bin/bash
set -e

echo "=========================================="
echo "HF Jobs: Constraint-Tracker LoRA Training"
echo "=========================================="

# Install dependencies
echo "Step 1: Installing dependencies..."
pip install -q torch transformers datasets peft trl huggingface-hub bitsandbytes numpy 2>&1 | grep -v "WARNING\\|notice" || true

# Verify imports
python -c "import torch; import transformers; import peft; print('  Dependencies: OK')" || {
    echo "ERROR: Dependency check failed"
    exit 1
}

# Clone the codette repo with HF token authentication
echo "Step 2: Cloning Codette repo..."
cd /tmp

# Use HF_TOKEN for git clone authentication
export GIT_ASKPASS=echo
export GIT_USERNAME=oauth2
export GIT_PASSWORD=$HF_TOKEN

git clone https://huggingface.co/Raiff1982/codette-clean.git 2>&1 | grep -v "Cloning\\|Receiving\\|Resolving" || true

if [ ! -d "codette-clean" ]; then
    echo "ERROR: Failed to clone repo"
    exit 1
fi

cd codette-clean
echo "  Repository cloned: OK"

# Verify training script exists
if [ ! -f "training/train_hf_job.py" ]; then
    echo "ERROR: training/train_hf_job.py not found in repo"
    ls -la training/ || true
    exit 1
fi
echo "  Training script found: OK"

# Run training
echo ""
echo "=========================================="
echo "Step 3: Starting Training"
echo "=========================================="
echo ""

export HF_TOKEN=$HF_TOKEN
python training/train_hf_job.py

echo ""
echo "=========================================="
echo "Training Complete"
echo "=========================================="
"""

try:
    # Submit the job using run_job
    job = api.run_job(
        image="python:3.10",
        command=["/bin/bash", "-c", job_script],
        env={
            "HF_TOKEN": HF_TOKEN,
        },
        token=HF_TOKEN,
    )

    print(f"\n{'=' * 70}")
    print("[SUCCESS] Job submitted!")
    print(f"{'=' * 70}")

    print(f"\nJob Details:")
    print(f"  Job ID: {job.id}")
    print(f"  Status: {job.status}")
    print(f"  URL: {job.url}")

    # Save job info
    job_info = {
        "job_id": job.id,
        "status": str(job.status),
        "url": job.url,
        "repo": OUTPUT_REPO,
        "base_model": MODEL_REPO,
        "dataset": "constraint_tracking.jsonl",
        "adapter": "constraint_tracker",
        "method": "git-clone-with-auth",
    }

    job_info_path = Path("hf_job_info.json")
    with open(job_info_path, "w") as f:
        json.dump(job_info, f, indent=2)

    print(f"\nJob info saved to: {job_info_path}")
    print(f"\nMonitor at: {job.url}")
    print(f"\nThe job will:")
    print(f"  1. Install PyTorch & training dependencies")
    print(f"  2. Clone codette-clean repo (with HF token auth)")
    print(f"  3. Run training/train_hf_job.py")
    print(f"  4. Train constraint_tracker LoRA (3 epochs)")
    print(f"  5. Upload to {OUTPUT_REPO}")
    print(f"\nETA: 4-6 hours on A10G GPU")

except Exception as e:
    print(f"\n{'=' * 70}")
    print("[ERROR] Job submission failed")
    print(f"{'=' * 70}")
    print(f"Error: {e}")

    import traceback
    traceback.print_exc()

    exit(1)

print(f"\n{'=' * 70}")
print("[OK] Training Submitted!")
print("=" * 70 + "\n")
