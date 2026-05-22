#!/usr/bin/env python3
"""
Final submission: Run standalone training script directly on HF Jobs.
No git cloning, no complex setup - just install deps and train.
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
print("Constraint-Tracker LoRA - Final Submission (Direct Upload)")
print("=" * 70)

api = HfApi(token=HF_TOKEN)

# Dependencies
dependencies = [
    "torch>=2.0.0",
    "transformers>=4.36.0",
    "datasets>=2.14.0",
    "peft>=0.7.0",
    "trl>=0.7.0",
    "huggingface-hub>=0.19.0",
    "bitsandbytes>=0.41.0",
]

print(f"\nDependencies: {len(dependencies)}")
for dep in dependencies:
    print(f"  - {dep}")

# Verify training script exists
script_path = Path("training/train_standalone.py")
if not script_path.exists():
    print(f"\nERROR: {script_path} not found")
    exit(1)

print(f"\nTraining script: {script_path} ({script_path.stat().st_size} bytes)")

print(f"\n" + "=" * 70)
print("Submitting to HF Jobs...")
print("=" * 70)

try:
    job = api.run_uv_job(
        script="training/train_standalone.py",
        dependencies=dependencies,
        env={"HF_TOKEN": HF_TOKEN},
        token=HF_TOKEN,
    )

    print(f"\n{'=' * 70}")
    print("[SUCCESS] Job submitted!")
    print(f"{'=' * 70}")

    print(f"\nJob ID: {job.id}")
    print(f"Status: {job.status}")
    print(f"URL: {job.url}")

    # Save info
    job_info = {
        "job_id": job.id,
        "status": str(job.status),
        "url": job.url,
        "adapter": "constraint_tracker",
        "method": "standalone-script",
    }

    with open("hf_job_info.json", "w") as f:
        json.dump(job_info, f, indent=2)

    print(f"\nMonitor at: {job.url}")
    print(f"\nTraining will:")
    print(f"  1. Install PyTorch + dependencies")
    print(f"  2. Load base model (codette-llama-3.1-8b-merged)")
    print(f"  3. Download dataset (constraint_tracking.jsonl)")
    print(f"  4. Train constraint_tracker LoRA (3 epochs, lr=1e-4)")
    print(f"  5. Upload adapter to Raiff1982/codette-lora-adapters")
    print(f"\nETA: 4-6 hours on A10G GPU")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print(f"\n{'=' * 70}")
print("[OK] Job Submitted!")
print("=" * 70 + "\n")
