#!/usr/bin/env python3
"""
Codette Intel XPU Environment Setup
===================================

Installs all dependencies required to run PyTorch on Intel Arc GPUs
using Intel Extension for PyTorch (IPEX).

This script will:

1. Remove incompatible PyTorch builds
2. Install Intel XPU PyTorch
3. Install Intel Extension for PyTorch
4. Install required ML dependencies
5. Verify that the Intel GPU is detected
"""

import subprocess
import sys
import importlib


def run(cmd: list[str]):
    """Run shell command and stream output."""
    print("\n>>>", " ".join(cmd))
    subprocess.check_call(cmd)


def pip_install(*packages):
    run([sys.executable, "-m", "pip", "install", *packages])


def pip_uninstall(*packages):
    run([sys.executable, "-m", "pip", "uninstall", "-y", *packages])


def verify_xpu():
    print("\n--- Verifying Intel GPU ---")

    try:
        import torch

        if hasattr(torch, "xpu") and torch.xpu.is_available():

            name = torch.xpu.get_device_name(0)

            print("\nSUCCESS: Intel GPU detected")
            print("Device:", name)

            return True

        else:

            print("\nWARNING: Intel GPU not detected by PyTorch")

            return False

    except Exception as e:

        print("\nVerification failed:", e)

        return False


def main():

    print("\n=== Codette Intel XPU Setup ===")

    print("\nStep 1: upgrading pip")

    pip_install("--upgrade", "pip")

    print("\nStep 2: removing incompatible PyTorch builds")

    pip_uninstall("torch", "torchvision", "torchaudio")

    print("\nStep 3: installing Intel XPU PyTorch")

    pip_install(
        "torch",
        "torchvision",
        "torchaudio",
        "--index-url",
        "https://download.pytorch.org/whl/xpu"
    )

    print("\nStep 4: installing Intel Extension for PyTorch")

    pip_install("intel-extension-for-pytorch")

    print("\nStep 5: installing training dependencies")

    pip_install(
        "transformers",
        "datasets",
        "accelerate",
        "trl",
        "peft",
        "sentencepiece",
        "bitsandbytes",
        "psutil",
        "pyyaml",
        "tqdm"
    )

    print("\nStep 6: verifying installation")

    ok = verify_xpu()

    print("\n=== Setup Complete ===")

    if ok:
        print("\nYour Intel GPU is ready for training.")
    else:
        print("\nPyTorch installed but XPU was not detected.")
        print("Make sure Intel GPU drivers are installed.")


if __name__ == "__main__":
    main()