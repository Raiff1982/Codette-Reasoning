#!/usr/bin/env python3
"""Convert PEFT LoRA safetensors to llama.cpp GGUF LoRA format.

Lightweight converter — no torch/transformers dependency.
Only needs: safetensors, gguf, numpy, struct.

Matches the exact format produced by llama.cpp's convert_lora_to_gguf.py.
"""

import json
import struct
import sys
from pathlib import Path
import numpy as np

# gguf uses its own writer
from gguf import GGUFWriter, GGMLQuantizationType


# PEFT tensor name -> GGUF tensor name mapping for LLama
# PEFT:  base_model.model.model.layers.{i}.self_attn.{proj}.lora_{AB}.weight
# GGUF:  blk.{i}.attn_{mapped_proj}.weight.lora_{ab}
PROJ_MAP = {
    "q_proj": "attn_q",
    "k_proj": "attn_k",
    "v_proj": "attn_v",
    "o_proj": "attn_output",
}


def bf16_to_f16(data_bytes: bytes) -> np.ndarray:
    """Convert bfloat16 raw bytes to float16 numpy array.

    bf16: sign(1) + exp(8) + mantissa(7)
    f16:  sign(1) + exp(5) + mantissa(10)

    We go bf16 -> f32 -> f16 to avoid precision edge cases.
    """
    # Read as uint16 (same byte layout as bf16)
    bf16 = np.frombuffer(data_bytes, dtype=np.uint16)
    # Convert bf16 to f32: shift left 16 bits
    f32_bytes = np.zeros(len(bf16), dtype=np.uint32)
    f32_bytes[:] = bf16.astype(np.uint32) << 16
    f32 = f32_bytes.view(np.float32)
    # Convert f32 to f16
    return f32.astype(np.float16)


def read_safetensors(path: Path) -> dict:
    """Read safetensors file, handling bf16 manually."""
    with open(path, "rb") as f:
        # Header: 8-byte little-endian uint64 = header size
        header_size = struct.unpack("<Q", f.read(8))[0]
        header_json = f.read(header_size)
        header = json.loads(header_json)

        data_start = 8 + header_size
        tensors = {}

        for name, info in header.items():
            if name == "__metadata__":
                continue
            dtype = info["dtype"]
            shape = info["shape"]
            offsets = info["data_offsets"]
            start, end = offsets

            f.seek(data_start + start)
            raw = f.read(end - start)

            if dtype == "BF16":
                arr = bf16_to_f16(raw).reshape(shape)
            elif dtype == "F16":
                arr = np.frombuffer(raw, dtype=np.float16).reshape(shape)
            elif dtype == "F32":
                arr = np.frombuffer(raw, dtype=np.float32).reshape(shape)
                arr = arr.astype(np.float16)
            else:
                raise ValueError(f"Unsupported dtype: {dtype}")

            tensors[name] = arr

    return tensors


def peft_name_to_gguf(peft_name: str) -> str | None:
    """Map PEFT tensor name to GGUF tensor name.

    Input:  base_model.model.model.layers.0.self_attn.q_proj.lora_A.weight
    Output: blk.0.attn_q.weight.lora_a
    """
    parts = peft_name.split(".")
    # Expected: base_model.model.model.layers.{i}.self_attn.{proj}.lora_{AB}.weight
    try:
        layer_idx = parts[4]  # layer number
        proj = parts[6]       # q_proj, k_proj, etc.
        lora_part = parts[7]  # lora_A or lora_B
    except IndexError:
        return None

    gguf_proj = PROJ_MAP.get(proj)
    if gguf_proj is None:
        return None

    ab = lora_part.lower()  # lora_a or lora_b
    return f"blk.{layer_idx}.{gguf_proj}.weight.{ab}"


def convert(adapter_dir: Path, output_path: Path, adapter_name: str):
    """Convert a PEFT LoRA adapter to GGUF format."""
    config_path = adapter_dir / "adapter_config.json"
    safetensors_path = adapter_dir / "adapter_model.safetensors"

    if not config_path.exists():
        raise FileNotFoundError(f"No adapter_config.json in {adapter_dir}")
    if not safetensors_path.exists():
        raise FileNotFoundError(f"No adapter_model.safetensors in {adapter_dir}")

    # Read config
    with open(config_path) as f:
        config = json.load(f)

    lora_alpha = config.get("lora_alpha", 32)
    lora_rank = config.get("r", 16)
    print(f"  Config: rank={lora_rank}, alpha={lora_alpha}")

    # Read tensors
    print(f"  Reading safetensors...")
    tensors = read_safetensors(safetensors_path)
    print(f"  Loaded {len(tensors)} tensors")

    # Create GGUF writer
    writer = GGUFWriter(str(output_path), arch="llama")

    # Write metadata (matching the newton GGUF format exactly)
    writer.add_string("general.type", "adapter")
    writer.add_string("adapter.type", "lora")
    writer.add_string("general.name", adapter_name)
    writer.add_uint32("general.base_model.count", 1)
    writer.add_string("general.base_model.0.name", "Llama 3.1 8B Instruct")
    writer.add_string("general.base_model.0.organization", "Meta Llama")
    writer.add_string("general.base_model.0.repo_url",
                       "https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct")
    writer.add_array("general.tags", [
        "base_model:adapter:meta-llama/Llama-3.1-8B-Instruct",
        "lora", "sft", "transformers", "trl", "text-generation",
    ])
    writer.add_float32("adapter.lora.alpha", float(lora_alpha))
    writer.add_uint32("general.quantization_version", 2)

    # Convert and add tensors
    converted = 0
    for peft_name, data in sorted(tensors.items()):
        gguf_name = peft_name_to_gguf(peft_name)
        if gguf_name is None:
            print(f"  SKIP: {peft_name}")
            continue

        # GGUF LoRA expects F16 (type=1)
        writer.add_tensor(gguf_name, data, raw_dtype=GGMLQuantizationType.F16)
        converted += 1

    print(f"  Converted {converted} tensors")

    # Write file
    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_tensors_to_file()
    writer.close()

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"  Output: {output_path} ({size_mb:.1f} MB)")


def main():
    adapters_dir = Path("J:/codette-training-lab/adapters")
    hf_dir = adapters_dir / "hf_download"

    # Convert all adapters that have safetensors but no GGUF yet
    to_convert = []
    for name in ["empathy", "philosophy", "quantum",
                  "consciousness", "multi_perspective", "systems_architecture"]:
        src = hf_dir / name
        dst = adapters_dir / f"{name}-lora-f16.gguf"
        if src.exists() and (src / "adapter_model.safetensors").exists():
            if dst.exists():
                print(f"SKIP {name}: GGUF already exists")
            else:
                to_convert.append((name, src, dst))
        else:
            print(f"SKIP {name}: no safetensors found")

    if not to_convert:
        print("Nothing to convert!")
        return

    for name, src, dst in to_convert:
        print(f"\nConverting {name}...")
        try:
            convert(src, dst, name)
            print(f"OK: {name}")
        except Exception as e:
            print(f"FAIL: {name}: {e}")


if __name__ == "__main__":
    main()
