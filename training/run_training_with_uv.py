#!/usr/bin/env python3
"""
Wrapper script for HF Jobs that uses uv to manage dependencies.
This ensures all required packages are installed before training starts.
"""

import subprocess
import sys
import os
from pathlib import Path

def install_dependencies():
    """Use uv to install dependencies from pyproject.toml"""
    print("=" * 60)
    print("Installing dependencies via uv...")
    print("=" * 60)

    # Get the repo root (parent of training directory)
    repo_root = Path(__file__).parent.parent
    print(f"Repository root: {repo_root}")

    # Check if pyproject.toml exists
    pyproject_path = repo_root / "pyproject.toml"
    if not pyproject_path.exists():
        print(f"ERROR: pyproject.toml not found at {pyproject_path}")
        sys.exit(1)

    # First, ensure uv is installed
    print("\nEnsuring uv is installed...")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "uv>=0.1.0"],
                          capture_output=False)
    if result.returncode != 0:
        print("WARNING: Failed to install uv via pip, will try system uv")

    # Use uv to sync dependencies
    print("\nSyncing dependencies with uv...")
    os.chdir(repo_root)
    result = subprocess.run(["uv", "sync"], capture_output=False)

    if result.returncode != 0:
        print("WARNING: uv sync failed, will try pip install directly")
        # Fallback to pip if uv fails
        result = subprocess.run([
            sys.executable, "-m", "pip", "install",
            "torch>=2.0.0",
            "transformers>=4.36.0",
            "datasets>=2.14.0",
            "peft>=0.7.0",
            "trl>=0.7.0",
            "huggingface-hub>=0.19.0",
            "bitsandbytes>=0.41.0",
        ])
        if result.returncode != 0:
            print("ERROR: Failed to install dependencies")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("Dependencies installed successfully!")
    print("=" * 60)

def run_training():
    """Run the actual training script"""
    print("\n" + "=" * 60)
    print("Starting constraint-tracker LoRA training...")
    print("=" * 60)

    # Use uv to run the training script
    training_script = Path(__file__).parent / "train_hf_job.py"

    if not training_script.exists():
        print(f"ERROR: Training script not found at {training_script}")
        sys.exit(1)

    # Run via uv run (which uses the synced environment)
    print(f"Training script: {training_script}")
    result = subprocess.run(["uv", "run", str(training_script)])

    sys.exit(result.returncode)

if __name__ == "__main__":
    install_dependencies()
    run_training()
