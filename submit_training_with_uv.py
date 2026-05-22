#!/usr/bin/env python3
"""
Submit constraint-tracker LoRA training job to HF Jobs with proper dependency management.
This script ensures uv and all required packages are available before training starts.
"""

import os
import subprocess
import json
from pathlib import Path
from huggingface_hub import HfApi

HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    print("ERROR: HF_TOKEN environment variable not set")
    exit(1)

# Configuration
REPO_ID = "Raiff1982/codette-training-service"
REPO_TYPE = "model"
MODEL_NAME = "Raiff1982/codette-llama-3.1-8b-merged"
DATASET_REPO = "Raiff1982/codette-training-data"
OUTPUT_REPO = "Raiff1982/codette-lora-adapters"

print("=" * 60)
print("Codette Constraint-Tracker LoRA Training - HF Jobs Submission")
print("=" * 60)

print(f"\nConfiguration:")
print(f"  Base Model: {MODEL_NAME}")
print(f"  Dataset: {DATASET_REPO}")
print(f"  Output Repo: {OUTPUT_REPO}")

# Create a minimal job script that uses uv
job_script = """#!/usr/bin/env python3
import subprocess
import sys
import os

print("=" * 60)
print("HF Jobs Training Environment Setup")
print("=" * 60)

# Step 1: Install uv
print("\\nInstalling uv...")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "uv>=0.1.0"], check=False)

# Step 2: Use uv to install all dependencies from pyproject.toml
print("\\nInstalling dependencies via uv...")
deps = [
    "torch>=2.0.0",
    "transformers>=4.36.0",
    "datasets>=2.14.0",
    "peft>=0.7.0",
    "trl>=0.7.0",
    "huggingface-hub>=0.19.0",
    "bitsandbytes>=0.41.0",
    "numpy>=1.24.0",
]

result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q"] + deps,
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print(f"WARNING: pip install failed")
    print(f"stdout: {result.stdout}")
    print(f"stderr: {result.stderr}")
else:
    print("Dependencies installed successfully!")

# Step 3: Verify imports
print("\\nVerifying core imports...")
try:
    import torch
    print(f"  ✓ torch {torch.__version__}")
    import transformers
    print(f"  ✓ transformers {transformers.__version__}")
    import peft
    print(f"  ✓ peft {peft.__version__}")
    import datasets
    print(f"  ✓ datasets {datasets.__version__}")
except ImportError as e:
    print(f"  ✗ Import failed: {e}")
    sys.exit(1)

# Step 4: Run training
print("\\n" + "=" * 60)
print("Starting Training")
print("=" * 60)

os.chdir("/workspace")
exec(open("/workspace/training/train_hf_job.py").read())
"""

# Save the job script
job_script_path = Path("/tmp/hf_job_training.py")
job_script_path.write_text(job_script)

print(f"\nJob script created at: {job_script_path}")
print(f"Job script size: {job_script_path.stat().st_size} bytes")

# Submit via HF
print(f"\n" + "=" * 60)
print("Submitting to HF Jobs...")
print("=" * 60)

api = HfApi(token=HF_TOKEN)

try:
    # Submit the job
    job = api.run_as_future(
        command=f"python {job_script_path}",
        repo_id=OUTPUT_REPO,
        repo_type=REPO_TYPE,
        private=True,
        token=HF_TOKEN,
    )

    print(f"\n✓ Job submitted successfully!")
    print(f"  Job ID: {job.job_id}")
    print(f"  Repo: {OUTPUT_REPO}")
    print(f"\nMonitor progress at:")
    print(f"  https://huggingface.co/{OUTPUT_REPO}/discussions")

except Exception as e:
    print(f"\n✗ Job submission failed: {e}")
    print(f"\nTroubleshooting:")
    print(f"  1. Check HF_TOKEN is valid")
    print(f"  2. Verify repo {OUTPUT_REPO} exists and is private")
    print(f"  3. Check network connectivity")
    exit(1)

print(f"\n" + "=" * 60)
print("Submission complete!")
print("=" * 60)
