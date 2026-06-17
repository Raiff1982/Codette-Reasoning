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
"""Convert the empathy_v2 PEFT adapter to runtime GGUF (CPU-only HF Job).

The Codette runtime loads behavioral adapters as
`{name}-behavioral-lora-f16.gguf`. The retrain produced a PEFT/safetensors
adapter at Raiff1982/codette-lora-adapters/empathy_v2. This converts it to GGUF
with llama.cpp's convert_lora_to_gguf.py and uploads it to the repo under
behavioral-gguf/empathy-behavioral-lora-f16.gguf for you to drop into the
local behavioral-lora-f16-gguf/ dir.

--base uses the (ungated) merged repo only as an architecture reference; the
adapter delta itself is independent of the base weights, and Llama-3.1-8B
architecture is identical to the vanilla base the runtime applies it on.
"""
import os, subprocess, sys
from pathlib import Path
from huggingface_hub import snapshot_download, hf_hub_download, HfApi, get_token

TOKEN   = os.environ.get("HF_TOKEN") or get_token()
REPO    = "Raiff1982/codette-lora-adapters"
SUBDIR  = "empathy_v2"
BASE_REF = "Raiff1982/codette-llama-3.1-8b-merged"   # ungated arch reference
OUT_NAME = "empathy-behavioral-lora-f16.gguf"
OUT_REMOTE = f"behavioral-gguf/{OUT_NAME}"

print("[1/5] Clone llama.cpp converter")
if not Path("llama.cpp").exists():
    subprocess.check_call(["git", "clone", "--depth=1",
                           "https://github.com/ggml-org/llama.cpp.git"])
conv = "llama.cpp/convert_lora_to_gguf.py"
assert Path(conv).exists(), conv

print("[2/5] Download empathy_v2 adapter")
adir = snapshot_download(REPO, allow_patterns=f"{SUBDIR}/**", local_dir="adapter_dl", token=TOKEN)
src = str(Path("adapter_dl") / SUBDIR)
print("  adapter at:", src)

print("[3/5] Download base arch reference (config/tokenizer/weights)")
base_dir = snapshot_download(BASE_REF, local_dir="base_ref", token=TOKEN,
                             ignore_patterns=["*.bin", "original/**", "*.pth", "*.gguf"])
print("  base at:", base_dir)

print("[4/5] Convert to GGUF (f16)")
out = str(Path("out") / OUT_NAME); Path("out").mkdir(exist_ok=True)
r = subprocess.run([sys.executable, conv, "--outfile", out, "--base", base_dir, src],
                   capture_output=True, text=True, timeout=900,
                   env={**os.environ, "HF_TOKEN": TOKEN})
print(r.stdout[-2000:])
if r.returncode != 0 or not Path(out).exists():
    print("CONVERT FAILED\n", r.stderr[-3000:]); sys.exit(1)
print(f"  wrote {out} ({Path(out).stat().st_size/1024/1024:.1f} MB)")

print("[5/5] Upload GGUF")
api = HfApi(token=TOKEN)
api.upload_file(path_or_fileobj=out, path_in_repo=OUT_REMOTE, repo_id=REPO, token=TOKEN)
print(f"Done -> {REPO}/{OUT_REMOTE}")
