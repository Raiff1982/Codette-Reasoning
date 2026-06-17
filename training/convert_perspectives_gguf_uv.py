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
"""Convert all 7 retrained perspective adapters ({name}_v2) to runtime GGUF.

CPU-only HF Job. For each adapter, downloads the PEFT adapter, converts via
llama.cpp's convert_lora_to_gguf.py, and uploads
behavioral-gguf/{name}-behavioral-lora-f16.gguf to the repo. --base uses the
ungated merged repo as an architecture reference (delta is base-weight
independent; Llama-3.1-8B arch matches the vanilla base the runtime applies on).
"""
import os, subprocess, sys
from pathlib import Path
from huggingface_hub import snapshot_download, HfApi, get_token

TOKEN    = os.environ.get("HF_TOKEN") or get_token()
REPO     = "Raiff1982/codette-lora-adapters"
BASE_REF = "Raiff1982/codette-llama-3.1-8b-merged"
ADAPTERS = ["newton", "davinci", "philosophy", "quantum",
            "consciousness", "multi_perspective", "systems_architecture"]

print("[1/4] clone llama.cpp")
if not Path("llama.cpp").exists():
    subprocess.check_call(["git", "clone", "--depth=1",
                           "https://github.com/ggml-org/llama.cpp.git"])
conv = "llama.cpp/convert_lora_to_gguf.py"
assert Path(conv).exists(), conv

print("[2/4] download base arch reference")
base_dir = snapshot_download(BASE_REF, local_dir="base_ref", token=TOKEN,
                             ignore_patterns=["*.bin", "original/**", "*.pth", "*.gguf"])

api = HfApi(token=TOKEN)
Path("out").mkdir(exist_ok=True)
ok, failed = [], []
for name in ADAPTERS:
    print(f"\n[3/4] {name}: download + convert")
    try:
        snapshot_download(REPO, allow_patterns=f"{name}_v2/**", local_dir="adl", token=TOKEN)
        src = str(Path("adl") / f"{name}_v2")
        out = str(Path("out") / f"{name}-behavioral-lora-f16.gguf")
        r = subprocess.run([sys.executable, conv, "--outfile", out, "--base", base_dir, src],
                           capture_output=True, text=True, timeout=900,
                           env={**os.environ, "HF_TOKEN": TOKEN})
        if r.returncode != 0 or not Path(out).exists():
            print(f"  FAIL {name}\n{r.stderr[-1500:]}"); failed.append(name); continue
        api.upload_file(path_or_fileobj=out, repo_id=REPO, token=TOKEN,
                        path_in_repo=f"behavioral-gguf/{name}-behavioral-lora-f16.gguf")
        print(f"  ok {name} ({Path(out).stat().st_size/1024/1024:.1f} MB)")
        ok.append(name)
    except Exception as e:
        print(f"  ERROR {name}: {e}"); failed.append(name)

print(f"\n[4/4] done. converted={ok} failed={failed}")
