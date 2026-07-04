#!/usr/bin/env python3
"""Convert Codette's GGUF LoRA adapters to safetensors for OpenVINO GenAI.

OpenVINO GenAI AdapterConfig requires weights in HuggingFace safetensors
format — it cannot read GGUF directly. This script:

  1. Scans adapters/ and behavioral-lora-f16-gguf/ for *-lora-f16.gguf
  2. Loads each via llama-cpp-python's internal GGUF parser
  3. Reconstructs the LoRA A/B weight tensors
  4. Saves as adapters_safetensors/ and behavioral_safetensors/

Requirements (already in codette env, NOT openvino_env):
    pip install gguf safetensors torch

Usage:
    python openvino_backend/convert_adapters.py
    python openvino_backend/convert_adapters.py --adapter newton --verbose
"""

import argparse
import struct
import sys
from pathlib import Path

_REPO = Path(__file__).parent.parent


def _read_gguf_tensors(gguf_path: Path) -> dict:
    """Extract tensor metadata and data from a GGUF file.

    Returns dict of {tensor_name: numpy_array}.
    Uses the `gguf` package (part of llama.cpp python bindings).
    """
    try:
        from gguf import GGUFReader
    except ImportError:
        raise RuntimeError(
            "gguf package not found. Install it:\n"
            "  pip install gguf\n"
            "or activate the environment that has llama-cpp-python."
        )

    reader = GGUFReader(str(gguf_path))
    tensors = {}
    for tensor in reader.tensors:
        tensors[tensor.name] = tensor.data  # numpy array, already dequantized
    return tensors


def _tensors_to_safetensors(tensors: dict, out_path: Path, verbose: bool = False):
    """Save a dict of numpy arrays as a safetensors file."""
    try:
        import torch
        from safetensors.torch import save_file
    except ImportError:
        raise RuntimeError(
            "torch and safetensors are required:\n"
            "  pip install torch safetensors"
        )

    st_tensors = {}
    for name, arr in tensors.items():
        t = torch.from_numpy(arr.copy()).to(torch.float16)
        st_tensors[name] = t
        if verbose:
            print(f"    {name}: {tuple(t.shape)} {t.dtype}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    save_file(st_tensors, str(out_path))
    size_mb = out_path.stat().st_size / 1_048_576
    print(f"  Saved {out_path.name} ({size_mb:.1f} MB)")


def convert_adapter(gguf_path: Path, out_path: Path, verbose: bool = False) -> bool:
    """Convert a single GGUF LoRA to safetensors. Returns True on success."""
    print(f"Converting: {gguf_path.name}")
    try:
        tensors = _read_gguf_tensors(gguf_path)
        if not tensors:
            print(f"  WARNING: no tensors found in {gguf_path.name}, skipping.")
            return False
        _tensors_to_safetensors(tensors, out_path, verbose=verbose)
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Convert Codette GGUF LoRA adapters to safetensors")
    parser.add_argument("--adapter", "-a", help="Convert only this adapter (e.g. 'newton')")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--behavioral-only", action="store_true",
                        help="Only convert behavioral adapters")
    parser.add_argument("--originals-only", action="store_true",
                        help="Only convert original (non-behavioral) adapters")
    args = parser.parse_args()

    original_dir = _REPO / "adapters"
    behavioral_dir = _REPO / "behavioral-lora-f16-gguf"
    out_original = _REPO / "adapters_safetensors"
    out_behavioral = _REPO / "behavioral_safetensors"

    converted = 0
    failed = 0

    # ── Behavioral adapters ────────────────────────────────────────────────────
    if not args.originals_only and behavioral_dir.exists():
        print(f"\n── Behavioral adapters ({behavioral_dir.name}) ──")
        for gguf in sorted(behavioral_dir.glob("*-behavioral-lora-f16.gguf")):
            # Skip backup files
            if ".v" in gguf.stem or "backup" in gguf.stem:
                continue
            name = gguf.stem.replace("-behavioral-lora-f16", "")
            if args.adapter and args.adapter != name:
                continue
            out = out_behavioral / f"{name}-behavioral-lora.safetensors"
            if convert_adapter(gguf, out, verbose=args.verbose):
                converted += 1
            else:
                failed += 1

    # ── Original adapters ──────────────────────────────────────────────────────
    if not args.behavioral_only and original_dir.exists():
        print(f"\n── Original adapters ({original_dir.name}) ──")
        for gguf in sorted(original_dir.glob("*-lora-f16.gguf")):
            name = gguf.stem.replace("-lora-f16", "")
            if args.adapter and args.adapter != name:
                continue
            # Skip if behavioral version already exists
            behavioral_out = out_behavioral / f"{name}-behavioral-lora.safetensors"
            if behavioral_out.exists() and not args.originals_only:
                print(f"  {name}: behavioral version exists, skipping original")
                continue
            out = out_original / f"{name}-lora.safetensors"
            if convert_adapter(gguf, out, verbose=args.verbose):
                converted += 1
            else:
                failed += 1

    print(f"\n{'─'*50}")
    print(f"Done: {converted} converted, {failed} failed")
    print(f"Output dirs:")
    print(f"  {out_original}")
    print(f"  {out_behavioral}")

    if failed > 0:
        print("\nFailed adapters will fall back to base model in OpenVINO backend.")
        sys.exit(1)


if __name__ == "__main__":
    main()
