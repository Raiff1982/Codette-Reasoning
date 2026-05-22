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
        print("\nAll packages installed successfully!")

    # Verify critical imports
    print("\nVerifying imports...")
    try:
        import torch
        import transformers
        import peft
        import datasets
        print("All critical imports successful!")
    except ImportError as e:
        print(f"Import verification failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Setup environment first
    setup_environment()

    # Now run the actual training
    print("\n" + "=" * 60)
    print("Starting Constraint-Tracker LoRA Training")
    print("=" * 60 + "\n")

    # Verify HF token
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        print("ERROR: HF_TOKEN environment variable not set")
        sys.exit(1)

    # Read and execute the training script directly
    # In HF Jobs, the script is in /data/training/train_hf_job.py
    script_paths = [
        "/data/training/train_hf_job.py",
        "/workspace/training/train_hf_job.py",
        "./training/train_hf_job.py",
    ]

    script_content = None
    script_path = None

    for path in script_paths:
        try:
            with open(path, 'r') as f:
                script_content = f.read()
            script_path = path
            print(f"Found training script: {script_path}\n")
            break
        except FileNotFoundError:
            continue

    if script_content is None:
        print(f"ERROR: Could not find training script in any of:")
        for path in script_paths:
            print(f"  - {path}")
        sys.exit(1)

    # Execute the training script
    exec(script_content)
