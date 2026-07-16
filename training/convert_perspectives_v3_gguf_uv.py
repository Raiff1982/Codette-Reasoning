# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "torch>=2.1.0",
#     "transformers>=4.44.0",
#     "safetensors>=0.4.0",
#     "peft>=0.11.0",
#     "huggingface-hub>=0.24.0",
#     "sentencepiece>=0.1.99",
#     "numpy",
#     "gguf",
# ]
# ///
"""Convert quantum_v3, multi_perspective_v3, newton_v3 PEFT adapters to GGUF.

CPU HF Job. Downloads each _v3 PEFT adapter, converts via llama.cpp's
convert_lora_to_gguf.py, then uploads to behavioral-gguf/ in
Raiff1982/codette-lora-adapters, backing up the existing v2 file first.

Upload layout after this job:
  behavioral-gguf/{name}-behavioral-lora-f16.gguf        <- new (v3)
  behavioral-gguf/{name}-behavioral-lora-f16.v2backup.gguf  <- old (v2)
"""
import os, subprocess, sys
from pathlib import Path
from huggingface_hub import snapshot_download, hf_hub_download, HfApi, get_token

TOKEN    = os.environ.get("HF_TOKEN") or get_token()
REPO     = "Raiff1982/codette-lora-adapters"
BASE_REF = "Raiff1982/codette-llama-3.1-8b-merged"
ADAPTERS = ["quantum", "multi_perspective", "newton"]

assert TOKEN, "HF_TOKEN not set"
api = HfApi(token=TOKEN)

print("[1/4] clone llama.cpp")
if not Path("llama.cpp").exists():
    subprocess.check_call(["git", "clone", "--depth=1",
                           "https://github.com/ggml-org/llama.cpp.git"])
conv = "llama.cpp/convert_lora_to_gguf.py"
assert Path(conv).exists(), conv

print("[2/4] download base arch reference (weights skipped — arch only)")
base_dir = snapshot_download(
    BASE_REF, local_dir="base_ref", token=TOKEN,
    ignore_patterns=["*.bin", "original/**", "*.pth", "*.gguf"])

# Check which files already exist on hub (for backup step)
try:
    existing = {f.rfilename for f in api.list_repo_tree(REPO, path_in_repo="behavioral-gguf")}
except Exception:
    existing = set()

Path("out").mkdir(exist_ok=True)
ok, failed = [], []

for name in ADAPTERS:
    print(f"\n[3/4] {name}: download _v3 + convert")
    try:
        snapshot_download(REPO, allow_patterns=f"{name}_v3/**",
                          local_dir="adl", token=TOKEN)
        src = str(Path("adl") / f"{name}_v3")
        out = str(Path("out") / f"{name}-behavioral-lora-f16.gguf")

        r = subprocess.run(
            [sys.executable, conv, "--outfile", out, "--base", base_dir, src],
            capture_output=True, text=True, timeout=900,
            env={**os.environ, "HF_TOKEN": TOKEN})

        if r.returncode != 0 or not Path(out).exists():
            print(f"  FAIL {name}\n{r.stderr[-2000:]}"); failed.append(name); continue

        gguf_name = f"{name}-behavioral-lora-f16.gguf"
        backup_name = f"{name}-behavioral-lora-f16.v2backup.gguf"

        # Back up the existing v2 GGUF if present
        if f"behavioral-gguf/{gguf_name}" in existing:
            try:
                old = hf_hub_download(REPO, f"behavioral-gguf/{gguf_name}", token=TOKEN)
                api.upload_file(path_or_fileobj=old, repo_id=REPO, token=TOKEN,
                                path_in_repo=f"behavioral-gguf/{backup_name}",
                                commit_message=f"Backup v2 GGUF for {name}")
                print(f"  backed up v2 -> {backup_name}")
            except Exception as e:
                print(f"  backup skipped: {e}")

        # Upload v3
        api.upload_file(path_or_fileobj=out, repo_id=REPO, token=TOKEN,
                        path_in_repo=f"behavioral-gguf/{gguf_name}",
                        commit_message=f"v3 GGUF for {name} (MCQ training + fixes)")
        sz = Path(out).stat().st_size / 1024 / 1024
        print(f"  uploaded {gguf_name} ({sz:.1f} MB)")
        ok.append(name)

    except Exception as e:
        print(f"  ERROR {name}: {e}"); failed.append(name)

print(f"\n[4/4] done.  ok={ok}  failed={failed}")
if failed:
    raise SystemExit(1)
