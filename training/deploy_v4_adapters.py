#!/usr/bin/env python3
"""Deploy v4 hand-authored adapters into both runtimes.

Pipeline per adapter:
  1. Download PEFT dir from Raiff1982/codette-adapters-v4 -> adapters/hf_download_v4/{name}
  2. PEFT safetensors -> GGUF f16   (llama.cpp runtime)
       install: behavioral-lora-f16-gguf/{name}-behavioral-lora-f16.gguf
       backup:  existing file -> {name}-behavioral-lora-f16.v3backup.gguf
  3. PEFT safetensors -> OV safetensors (GGUF tensor naming, fp16)
       install: behavioral_safetensors/{name}-behavioral-lora.safetensors
       backup:  existing file -> {name}-behavioral-lora.v3backup.safetensors

Same convention the v3 rollout used: the newest voice adapter ships under
the behavioral filename; the previous version is kept as a .v3backup so
reverting is a rename. No torch required — numpy + gguf + safetensors only.

Usage:
    python training/deploy_v4_adapters.py               # all 8
    python training/deploy_v4_adapters.py --adapter newton
    python training/deploy_v4_adapters.py --dry-run
"""

import argparse
import json
import shutil
import struct
import sys
from pathlib import Path

import numpy as np
from gguf import GGUFWriter, GGMLQuantizationType
from safetensors.numpy import save_file as st_save
from huggingface_hub import snapshot_download

REPO = Path(__file__).resolve().parent.parent
HUB_REPO = "Raiff1982/codette-adapters-v4"
STAGING = REPO / "adapters" / "hf_download_v4"
GGUF_DIR = REPO / "behavioral-lora-f16-gguf"
OV_DIR = REPO / "behavioral_safetensors"

ADAPTERS = [
    "newton", "davinci", "empathy", "philosophy", "quantum",
    "consciousness", "multi_perspective", "systems_architecture",
]

PROJ_MAP = {
    "q_proj": "attn_q",
    "k_proj": "attn_k",
    "v_proj": "attn_v",
    "o_proj": "attn_output",
}


def bf16_to_f16(raw: bytes) -> np.ndarray:
    u16 = np.frombuffer(raw, dtype=np.uint16)
    f32 = (u16.astype(np.uint32) << 16).view(np.float32)
    return f32.astype(np.float16)


def read_safetensors(path: Path) -> dict:
    with open(path, "rb") as f:
        header_size = struct.unpack("<Q", f.read(8))[0]
        header = json.loads(f.read(header_size))
        data_start = 8 + header_size
        tensors = {}
        for name, info in header.items():
            if name == "__metadata__":
                continue
            start, end = info["data_offsets"]
            f.seek(data_start + start)
            raw = f.read(end - start)
            dtype, shape = info["dtype"], info["shape"]
            if dtype == "BF16":
                arr = bf16_to_f16(raw).reshape(shape)
            elif dtype == "F16":
                arr = np.frombuffer(raw, dtype=np.float16).reshape(shape)
            elif dtype == "F32":
                arr = np.frombuffer(raw, dtype=np.float32).reshape(shape).astype(np.float16)
            else:
                raise ValueError(f"Unsupported dtype {dtype} for {name}")
            tensors[name] = arr
    return tensors


def peft_to_gguf_name(peft_name: str) -> str | None:
    # base_model.model.model.layers.{i}.self_attn.{proj}.lora_{AB}.weight
    parts = peft_name.split(".")
    try:
        layer_idx, proj, lora_part = parts[4], parts[6], parts[7]
    except IndexError:
        return None
    gguf_proj = PROJ_MAP.get(proj)
    if gguf_proj is None:
        return None
    return f"blk.{layer_idx}.{gguf_proj}.weight.{lora_part.lower()}"


def write_gguf(tensors: dict, alpha: float, name: str, out: Path) -> int:
    writer = GGUFWriter(str(out), arch="llama")
    writer.add_string("general.type", "adapter")
    writer.add_string("adapter.type", "lora")
    writer.add_string("general.name", name)
    writer.add_uint32("general.base_model.count", 1)
    writer.add_string("general.base_model.0.name", "Llama 3.1 8B Instruct")
    writer.add_string("general.base_model.0.organization", "Meta Llama")
    writer.add_string("general.base_model.0.repo_url",
                      "https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct")
    writer.add_array("general.tags", [
        "base_model:adapter:meta-llama/Llama-3.1-8B-Instruct",
        "lora", "sft", "transformers", "trl", "text-generation",
    ])
    writer.add_float32("adapter.lora.alpha", float(alpha))
    writer.add_uint32("general.quantization_version", 2)

    converted = 0
    for peft_name, data in sorted(tensors.items()):
        gguf_name = peft_to_gguf_name(peft_name)
        if gguf_name is None:
            continue
        writer.add_tensor(gguf_name, data, raw_dtype=GGMLQuantizationType.F16)
        converted += 1

    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_tensors_to_file()
    writer.close()
    return converted


def write_ov_safetensors(tensors: dict, out: Path) -> int:
    """OV backend loads safetensors with GGUF tensor names (same mapping the
    old GGUF->safetensors converter produced)."""
    st_tensors = {}
    for peft_name, data in sorted(tensors.items()):
        gguf_name = peft_to_gguf_name(peft_name)
        if gguf_name is None:
            continue
        st_tensors[gguf_name] = np.ascontiguousarray(data.astype(np.float16))
    out.parent.mkdir(parents=True, exist_ok=True)
    st_save(st_tensors, str(out))
    return len(st_tensors)


def backup_then_install(src: Path, dst: Path, backup_suffix: str, dry: bool):
    if dst.exists():
        bak = dst.with_name(dst.name.replace(dst.suffix, f".v3backup{dst.suffix}")
                            if backup_suffix in dst.name else dst.name)
        # simpler: explicit backup name
        bak = dst.parent / (dst.stem + ".v3backup" + dst.suffix)
        if not bak.exists():
            print(f"    backup: {dst.name} -> {bak.name}")
            if not dry:
                shutil.copy2(dst, bak)
        else:
            print(f"    backup exists: {bak.name} (keeping first backup)")
    print(f"    install: {dst.name}")
    if not dry:
        shutil.move(str(src), str(dst))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", help="only this adapter")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    names = [args.adapter] if args.adapter else ADAPTERS
    unknown = [n for n in names if n not in ADAPTERS]
    if unknown:
        sys.exit(f"Unknown adapters: {unknown}")

    STAGING.mkdir(parents=True, exist_ok=True)
    results = {}

    for name in names:
        print(f"\n=== {name} ===")
        try:
            print(f"  downloading {HUB_REPO}/{name} ...")
            if not args.dry_run:
                snapshot_download(HUB_REPO, allow_patterns=f"{name}/**",
                                  local_dir=str(STAGING))
            peft_dir = STAGING / name
            cfg_path = peft_dir / "adapter_config.json"
            st_path = peft_dir / "adapter_model.safetensors"
            if args.dry_run:
                print("  (dry-run: skipping conversion)")
                results[name] = "DRY"
                continue
            if not st_path.exists():
                results[name] = "FAILED: no safetensors downloaded"
                continue

            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            alpha, rank = cfg.get("lora_alpha", 32), cfg.get("r", 16)
            print(f"  config: rank={rank} alpha={alpha}")
            tensors = read_safetensors(st_path)
            print(f"  loaded {len(tensors)} tensors")

            # GGUF for llama.cpp
            tmp_gguf = STAGING / f"{name}-v4.gguf"
            n1 = write_gguf(tensors, alpha, name, tmp_gguf)
            print(f"  gguf: {n1} tensors ({tmp_gguf.stat().st_size/1048576:.1f} MB)")
            backup_then_install(
                tmp_gguf, GGUF_DIR / f"{name}-behavioral-lora-f16.gguf",
                ".v3backup", args.dry_run)

            # OV safetensors
            tmp_st = STAGING / f"{name}-v4.safetensors"
            n2 = write_ov_safetensors(tensors, tmp_st)
            print(f"  ov-safetensors: {n2} tensors ({tmp_st.stat().st_size/1048576:.1f} MB)")
            backup_then_install(
                tmp_st, OV_DIR / f"{name}-behavioral-lora.safetensors",
                ".v3backup", args.dry_run)

            results[name] = f"OK (gguf {n1}t, ov {n2}t)"
        except Exception as e:
            results[name] = f"FAILED: {type(e).__name__}: {e}"
            print(f"  FAILED: {e}")

    print(f"\n{'='*50}")
    for k, v in results.items():
        print(f"  {k:<24} {v}")
    print("\nRevert any adapter: rename its .v3backup file back over the installed one.")


if __name__ == "__main__":
    main()
