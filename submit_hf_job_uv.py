#!/usr/bin/env python3
"""
Submit constraint-tracker LoRA training job to HF Jobs using uv for dependency management.
Uses the HuggingFace Hub API with run_uv_job for optimal environment setup.
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
print("Codette Constraint-Tracker LoRA - HF Jobs Submission (uv mode)")
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
print(f"  Environment: Python 3.10 with uv dependency management")

# Dependencies to install
dependencies = [
    "torch>=2.0.0",
    "transformers>=4.36.0",
    "datasets>=2.14.0",
    "peft>=0.7.0",
    "trl>=0.7.0",
    "huggingface-hub>=0.19.0",
    "bitsandbytes>=0.41.0",
]

print(f"\nDependencies to install:")
for dep in dependencies:
    print(f"  - {dep}")

print(f"\n" + "=" * 70)
print("Submitting job to HF Jobs (using uv for dependencies)...")
print("=" * 70)

api = HfApi(token=HF_TOKEN)

try:
    # Use run_uv_job to submit with uv for dependency management
    job = api.run_uv_job(
        script="training/train_hf_job_with_deps.py",
        dependencies=dependencies,
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
        "method": "uv",
        "dependencies": dependencies,
    }

    job_info_path = Path("hf_job_info.json")
    with open(job_info_path, "w") as f:
        json.dump(job_info, f, indent=2)

    print(f"\nJob info saved to: {job_info_path}")
    print(f"\n" + "=" * 70)
    print("TRAINING JOB SUBMITTED - MONITORING & NEXT STEPS")
    print("=" * 70)
    print(f"\nJob Details:")
    print(f"  ID: {job.id}")
    print(f"  Repository: {OUTPUT_REPO}")
    print(f"  Status: {job.status}")
    print(f"\nMonitor your training at:")
    print(f"  {job.url}")
    print(f"\nWhat the job will do:")
    print(f"  Step 1: Install dependencies via uv")
    for dep in dependencies:
        print(f"    - {dep}")
    print(f"  Step 2: Download base model ({MODEL_REPO})")
    print(f"  Step 3: Download training dataset (constraint_tracking.jsonl)")
    print(f"  Step 4: Train constraint_tracker LoRA adapter")
    print(f"    - Epochs: 3")
    print(f"    - Learning rate: 1e-4")
    print(f"    - Batch size: 2")
    print(f"    - Gradient accumulation: 4")
    print(f"  Step 5: Upload trained adapter to {OUTPUT_REPO}")
    print(f"\nEstimated duration: 4-6 hours on A10G GPU")
    print(f"\nNext steps after training:")
    print(f"  1. Monitor job status: {job.url}")
    print(f"  2. Once complete, load the trained adapter")
    print(f"  3. Run runtime benchmark:")
    print(f"     python benchmarks/codette_runtime_benchmark.py")
    print(f"  4. Verify continuity_anchor_recall >= 0.70")
    print(f"     Current: 0.200, Target: 0.70+")

except Exception as e:
    print(f"\n{'=' * 70}")
    print("[ERROR] Job submission failed")
    print(f"{'=' * 70}")
    print(f"\nError: {e}")
    print(f"\nTroubleshooting:")
    print(f"  1. Verify HF_TOKEN is correct and has write permissions")
    print(f"  2. Check that {OUTPUT_REPO} exists and you own it")
    print(f"  3. Verify internet connection")
    print(f"  4. Check HF API status: https://status.huggingface.co/")

    # Print more detailed error info
    import traceback
    print(f"\nFull error trace:")
    traceback.print_exc()

    exit(1)

print(f"\n{'=' * 70}")
print("[OK] Constraint-Tracker LoRA Training Queued Successfully!")
print("=" * 70 + "\n")
