#!/usr/bin/env python3
"""
Convert behavioral PEFT/safetensors LoRA adapters to GGUF format.
Downloads from Raiff1982/codette-lora-adapters, converts, uploads as GGUF.
"""
import os
import subprocess
import sys

HF_TOKEN = os.environ.get("HF_TOKEN", "")
ADAPTERS = [
    "newton", "davinci", "empathy", "philosophy", "quantum",
    "consciousness", "multi_perspective", "systems_architecture", "orchestrator",
]
REPO_ID = "Raiff1982/codette-lora-adapters"
BASE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"


def main():
    print("=" * 60)
    print("BEHAVIORAL ADAPTER GGUF CONVERSION")
    print("=" * 60)

    # Clone llama.cpp for the conversion script
    print("\n[1/4] Getting llama.cpp conversion tools...")
    if not os.path.exists("llama.cpp"):
        subprocess.check_call([
            "git", "clone", "--depth=1",
            "https://github.com/ggml-org/llama.cpp.git"
        ])
    convert_script = "llama.cpp/convert_lora_to_gguf.py"
    assert os.path.exists(convert_script), f"Missing: {convert_script}"
    print(f"  Converter: {convert_script}")

    # Install conversion dependencies
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "numpy", "sentencepiece", "transformers", "torch", "safetensors",
        "huggingface_hub", "peft", "gguf",
    ])

    from huggingface_hub import snapshot_download, HfApi

    # Download behavioral adapters
    print("\n[2/4] Downloading behavioral adapters...")
    adapter_dir = snapshot_download(
        REPO_ID,
        local_dir="adapters_download",
        allow_patterns="behavioral/**",
        token=HF_TOKEN,
    )
    print(f"  Downloaded to: {adapter_dir}")

    # Convert each adapter
    print("\n[3/4] Converting to GGUF...")
    os.makedirs("gguf_output", exist_ok=True)
    converted = []

    for name in ADAPTERS:
        src = os.path.join(adapter_dir, "behavioral", name)
        if not os.path.exists(src):
            print(f"  SKIP {name}: directory not found")
            continue

        safetensors_file = os.path.join(src, "adapter_model.safetensors")
        if not os.path.exists(safetensors_file):
            print(f"  SKIP {name}: no adapter_model.safetensors")
            continue

        out_file = os.path.join("gguf_output", f"{name}-behavioral-lora-f16.gguf")
        print(f"  Converting {name}...")

        try:
            result = subprocess.run(
                [
                    sys.executable, convert_script,
                    "--outfile", out_file,
                    "--base", BASE_MODEL,
                    src,
                ],
                capture_output=True, text=True, timeout=300,
                env={**os.environ, "HF_TOKEN": HF_TOKEN},
            )
            if result.returncode == 0 and os.path.exists(out_file):
                size_mb = os.path.getsize(out_file) / (1024 * 1024)
                print(f"    ✓ {name}: {size_mb:.1f}MB")
                converted.append((name, out_file))
            else:
                print(f"    ✗ {name} failed:")
                print(f"      stdout: {result.stdout[-500:] if result.stdout else 'none'}")
                print(f"      stderr: {result.stderr[-500:] if result.stderr else 'none'}")
        except Exception as e:
            print(f"    ✗ {name} error: {e}")

    # Upload GGUF files
    print(f"\n[4/4] Uploading {len(converted)} GGUF adapters...")
    if converted:
        api = HfApi(token=HF_TOKEN)
        for name, path in converted:
            remote_path = f"behavioral-gguf/{name}-behavioral-lora-f16.gguf"
            try:
                api.upload_file(
                    path_or_fileobj=path,
                    path_in_repo=remote_path,
                    repo_id=REPO_ID,
                    token=HF_TOKEN,
                )
                print(f"  ✓ Uploaded {remote_path}")
            except Exception as e:
                print(f"  ✗ Upload {name} failed: {e}")

    print(f"\n{'=' * 60}")
    print(f"CONVERSION COMPLETE: {len(converted)}/{len(ADAPTERS)} adapters")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
