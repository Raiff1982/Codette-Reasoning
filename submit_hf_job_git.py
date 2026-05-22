#!/usr/bin/env python3
"""
Submit constraint-tracker LoRA training job to HF Jobs by cloning the repo.
This approach ensures all dependencies are available.
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
print("Codette Constraint-Tracker LoRA - HF Jobs Submission (Git Clone)")
print("=" * 70)

# Configuration
MODEL_REPO = "Raiff1982/codette-llama-3.1-8b-merged"
DATASET_REPO = "Raiff1982/codette-training-data"
OUTPUT_REPO = "Raiff1982/codette-lora-adapters"

print(f"\nJob Configuration:")
print(f"  Base Model: {MODEL_REPO}")
print(f"  Dataset: constraint_tracking.jsonl")
print(f"  Adapter: constraint_tracker")
print(f"  Epochs: 3")
print(f"  Learning Rate: 1e-4")
print(f"  Output Repo: {OUTPUT_REPO}")

print(f"\n" + "=" * 70)
print("Submitting job to HF Jobs (cloning repo method)...")
print("=" * 70)

api = HfApi(token=HF_TOKEN)

# Create job script that will:
# 1. Install dependencies
# 2. Clone the codette repo
# 3. Run training
job_script = """#!/bin/bash
set -e

echo "=========================================="
echo "HF Jobs Training Setup"
echo "=========================================="

# Install dependencies
echo "Installing dependencies..."
pip install -q torch transformers datasets peft trl huggingface-hub bitsandbytes numpy

# Verify imports
python -c "import torch; import transformers; import peft; print('Dependencies OK')"

# Clone the codette repo
echo "Cloning Codette repo..."
cd /tmp
git clone https://huggingface.co/Raiff1982/codette-clean.git
cd codette-clean

# Run training
echo ""
echo "=========================================="
echo "Starting Constraint-Tracker LoRA Training"
echo "=========================================="
echo ""

export HF_TOKEN=$HF_TOKEN
python training/train_hf_job.py
"""

print(f"\nJob script:")
print(f"  1. Install all dependencies (torch, transformers, peft, trl, etc.)")
print(f"  2. Clone codette repo from HF Hub")
print(f"  3. Run training/train_hf_job.py with constraint_tracker adapter")

try:
    # Submit the job using run_job with a simple Python image
    job = api.run_job(
        image="python:3.10",
        command=["/bin/bash", "-c", job_script],
        env={
            "HF_TOKEN": HF_TOKEN,
        },
        token=HF_TOKEN,
    )

    print(f"\n{'=' * 70}")
    print("[SUCCESS] Job submitted successfully!")
    print(f"{'=' * 70}")

    print(f"\nJob Details:")
    print(f"  Job ID: {job.id}")
    print(f"  Status: {job.status}")
    print(f"  URL: {job.url}")
    print(f"  Repo: {OUTPUT_REPO}")

    # Save job info (convert status to string)
    job_info = {
        "job_id": job.id,
        "status": str(job.status),
        "url": job.url,
        "repo": OUTPUT_REPO,
        "base_model": MODEL_REPO,
        "dataset": "constraint_tracking.jsonl",
        "adapter": "constraint_tracker",
        "epochs": 3,
        "learning_rate": "1e-4",
        "method": "git-clone",
    }

    job_info_path = Path("hf_job_info.json")
    with open(job_info_path, "w") as f:
        json.dump(job_info, f, indent=2)

    print(f"\nJob info saved to: {job_info_path}")
    print(f"\n" + "=" * 70)
    print("TRAINING JOB SUBMITTED")
    print("=" * 70)
    print(f"\nMonitor at: {job.url}")
    print(f"Job will:")
    print(f"  1. Install dependencies")
    print(f"  2. Clone full Codette repo (with training script)")
    print(f"  3. Train constraint_tracker LoRA (3 epochs)")
    print(f"  4. Upload results to {OUTPUT_REPO}")
    print(f"\nEstimated time: 4-6 hours on A10G GPU")

except Exception as e:
    print(f"\n{'=' * 70}")
    print("[ERROR] Job submission failed")
    print(f"{'=' * 70}")
    print(f"\nError: {e}")

    import traceback
    traceback.print_exc()

    exit(1)

print(f"\n{'=' * 70}")
print("[OK] Training Job Submitted!")
print("=" * 70 + "\n")
