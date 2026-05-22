#!/usr/bin/env python3
"""
Submit constraint-tracker LoRA training job to HF Jobs using the Python API.
Uses uv for dependency management in the job environment.
"""

import os
import json
from pathlib import Path
from huggingface_hub import HfApi, submit_job

HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    print("ERROR: HF_TOKEN environment variable not set")
    exit(1)

print("=" * 70)
print("Codette Constraint-Tracker LoRA - HF Jobs Submission (Python API)")
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
print(f"  Environment: Python 3.10 with torch, transformers, peft, trl")

# Create the training command
# This will run the training script with dependency installation
training_command = """
python -m pip install -q torch transformers datasets peft trl huggingface-hub bitsandbytes numpy &&
cd /workspace &&
python training/train_hf_job_with_deps.py
"""

print(f"\n" + "=" * 70)
print("Submitting job to HF Jobs...")
print("=" * 70)

api = HfApi(token=HF_TOKEN)

try:
    # Submit the job using HF's job submission API
    job = submit_job(
        command=training_command,
        repo_type="model",
        repo_id=OUTPUT_REPO,
        private=True,
        token=HF_TOKEN,
    )

    print(f"\n{'=' * 70}")
    print("✓ Job submitted successfully!")
    print(f"{'=' * 70}")
    print(f"\nJob Details:")
    print(f"  Job ID: {job.job_id}")
    print(f"  Status: {job.status}")
    print(f"  Repo: {OUTPUT_REPO}")

    # Save job info
    job_info = {
        "job_id": job.job_id,
        "status": job.status,
        "repo": OUTPUT_REPO,
        "base_model": MODEL_REPO,
        "dataset": "constraint_tracking.jsonl",
        "adapter": "constraint_tracker",
        "epochs": 3,
        "learning_rate": "1e-4",
        "submission_time": str(Path.cwd()),
    }

    job_info_path = Path("/tmp/hf_job_info.json")
    with open(job_info_path, "w") as f:
        json.dump(job_info, f, indent=2)

    print(f"\nJob info saved to: {job_info_path}")
    print(f"\nMonitor your training at:")
    print(f"  https://huggingface.co/{OUTPUT_REPO}")
    print(f"\nThe job will:")
    print(f"  1. Install dependencies (torch, transformers, peft, trl, etc.)")
    print(f"  2. Download base model: {MODEL_REPO}")
    print(f"  3. Download dataset: constraint_tracking.jsonl from {DATASET_REPO}")
    print(f"  4. Train constraint_tracker LoRA adapter (3 epochs, lr=1e-4)")
    print(f"  5. Upload results to {OUTPUT_REPO}")
    print(f"\nEstimated time: 4-6 hours on A10G GPU")
    print(f"\nNext steps:")
    print(f"  1. Monitor job status at the URL above")
    print(f"  2. Once training completes, run:")
    print(f"     python benchmarks/codette_runtime_benchmark.py")
    print(f"  3. Verify continuity_anchor_recall score ≥ 0.70")

except Exception as e:
    print(f"\n{'=' * 70}")
    print("✗ Job submission failed")
    print(f"{'=' * 70}")
    print(f"\nError: {e}")
    print(f"\nTroubleshooting:")
    print(f"  1. Verify HF_TOKEN is correct")
    print(f"  2. Check that {OUTPUT_REPO} exists and you have write access")
    print(f"  3. Verify internet connection")
    print(f"  4. Check HF API status: https://status.huggingface.co/")
    print(f"\nTo retry, run:")
    print(f"  export HF_TOKEN='your-token'")
    print(f"  python submit_hf_job_api.py")
    exit(1)

print(f"\n{'=' * 70}")
print("Submission complete!")
print(f"{'=' * 70}\n")
