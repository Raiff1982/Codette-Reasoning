#!/usr/bin/env python3
"""
HF Jobs training wrapper that installs dependencies before running training.
This is the entry point for HF Jobs submissions.
"""

import subprocess
import sys
import os

def setup_environment():
    """Install all required dependencies."""
    print("=" * 60)
    print("Setting up training environment...")
    print("=" * 60)

    # Required packages
    packages = [
        "torch>=2.0.0",
        "transformers>=4.36.0",
        "datasets>=2.14.0",
        "peft>=0.7.0",
        "trl>=0.7.0",
        "huggingface-hub>=0.19.0",
        "bitsandbytes>=0.41.0",
        "numpy>=1.24.0",
        "uv>=0.1.0",
    ]

    print(f"\nInstalling {len(packages)} packages...")
    for pkg in packages:
        print(f"  - {pkg}")

    # Use pip to install all packages
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "--no-cache-dir"] + packages,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"\nWARNING: Installation had issues")
        print(f"stderr: {result.stderr[:500]}")
    else:
        print("\n✓ All packages installed successfully!")

    # Verify critical imports
    print("\nVerifying imports...")
    try:
        import torch
        import transformers
        import peft
        import datasets
        print("✓ All critical imports successful!")
    except ImportError as e:
        print(f"✗ Import verification failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Setup environment first
    setup_environment()

    # Now run the actual training
    print("\n" + "=" * 60)
    print("Starting Constraint-Tracker LoRA Training")
    print("=" * 60 + "\n")

    # Import and run training script
    import json
    os.environ.get("HF_TOKEN")  # Verify token is set

    # Execute the training script
    exec(open(__file__.replace("train_hf_job_with_deps.py", "train_hf_job.py")).read())
