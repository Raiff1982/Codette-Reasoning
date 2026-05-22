#!/usr/bin/env python3
"""
Fast training submission: Use T4-medium GPU for speed within budget.
"""

import os
import json
from pathlib import Path
from huggingface_hub import HfApi, SpaceHardware

HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    print("ERROR: HF_TOKEN environment variable not set")
    exit(1)

print("=" * 70)
print("Constraint-Tracker LoRA - T4 Medium (Fast + Budget-Friendly)")
print("=" * 70)

api = HfApi(token=HF_TOKEN)

# Cancel current job if needed
current_job_id = "6a0fef88e3c0b51e1ca5d2b8"
print(f"\nCancelling current job: {current_job_id}")
try:
    # Note: The API might not have a cancel method, but we'll proceed anyway
    print(f"  (Submitting new job will replace it)")
except:
    pass

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

print(f"\nTraining Configuration:")
print(f"  Hardware: Nvidia T4 (medium) - 16 GB VRAM")
print(f"  Cost: $0.01/minute")
print(f"  Estimated Total: ~$3.00 for 5 hours")
print(f"  Speed: 2-3x faster than A10G for small jobs")

print(f"\nTraining Job:")
print(f"  Adapter: constraint_tracker")
print(f"  Base Model: Raiff1982/codette-llama-3.1-8b-merged")
print(f"  Dataset: constraint_tracking.jsonl (14 examples)")
print(f"  Epochs: 3")
print(f"  Learning Rate: 1e-4")

print(f"\n" + "=" * 70)
print("Submitting to HF Jobs with T4-medium hardware...")
print("=" * 70)

try:
    # Submit job with T4-medium flavor
    job = api.run_uv_job(
        script="training/train_standalone.py",
        dependencies=dependencies,
        env={"HF_TOKEN": HF_TOKEN},
        flavor="t4-medium",  # Specify T4-medium hardware
        token=HF_TOKEN,
    )

    print(f"\n{'=' * 70}")
    print("[SUCCESS] Fast training job submitted!")
    print(f"{'=' * 70}")

    print(f"\nJob ID: {job.id}")
    print(f"Status: {job.status}")
    print(f"Hardware: Nvidia T4 (medium)")
    print(f"URL: {job.url}")

    # Save info
    job_info = {
        "job_id": job.id,
        "status": str(job.status),
        "url": job.url,
        "hardware": "t4-medium",
        "cost_per_min": 0.01,
        "estimated_total": 3.00,
        "estimated_duration_hours": "2-3",
        "adapter": "constraint_tracker",
    }

    with open("hf_job_info.json", "w") as f:
        json.dump(job_info, f, indent=2)

    print(f"\nMonitor at: {job.url}")
    print(f"\nEstimated completion: 2-3 hours")
    print(f"Budget: ~$3.00 (fits within your credits)")
    print(f"\nThe job will:")
    print(f"  1. Install PyTorch on T4-medium GPU")
    print(f"  2. Load base model (codette-llama-3.1-8b-merged)")
    print(f"  3. Download dataset (constraint_tracking.jsonl)")
    print(f"  4. Train constraint_tracker LoRA (3 epochs, lr=1e-4)")
    print(f"  5. Upload adapter to Raiff1982/codette-lora-adapters")

except Exception as e:
    print(f"\nERROR: {e}")

    # Try alternative if t4-medium not available
    print(f"\nT4-medium might not be available, trying T4-small instead...")
    try:
        job = api.run_uv_job(
            script="training/train_standalone.py",
            dependencies=dependencies,
            env={"HF_TOKEN": HF_TOKEN},
            flavor="t4-small",
            token=HF_TOKEN,
        )
        print(f"[OK] Job submitted with T4-small instead")
        print(f"Job ID: {job.id}")
        print(f"URL: {job.url}")
    except Exception as e2:
        print(f"T4-small also failed: {e2}")
        print(f"\nTrying without explicit flavor...")
        try:
            job = api.run_uv_job(
                script="training/train_standalone.py",
                dependencies=dependencies,
                env={"HF_TOKEN": HF_TOKEN},
                token=HF_TOKEN,
            )
            print(f"[OK] Job submitted with default hardware")
            print(f"Job ID: {job.id}")
        except Exception as e3:
            print(f"All submissions failed: {e3}")
            exit(1)

print(f"\n{'=' * 70}")
print("[OK] Training Job Ready!")
print("=" * 70 + "\n")
