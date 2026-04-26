#!/usr/bin/env python3
"""Generate new training datasets and upload to HuggingFace Hub.

Generates:
  - integrity_reasoning.jsonl        (updated: +ethics_field category)
  - *_integrity_supplement.jsonl     (per-adapter integrity supplements)
  - style_adaptive_reasoning.jsonl   (NEW: 5-register paired examples)
  - *_style_supplement.jsonl         (NEW: per-adapter style supplements)

Then uploads all new/updated files to Raiff1982/codette-training-data.

Usage:
    uv run scripts/upload_training_datasets.py
    # or
    python scripts/upload_training_datasets.py
"""

import os
import socket
import sys
import tempfile
from pathlib import Path

# DNS override: system DNS fails to resolve huggingface.co — use known IPs
_orig_getaddrinfo = socket.getaddrinfo
_HF_IPS = {
    "huggingface.co":              "143.204.130.84",
    "cdn-lfs.huggingface.co":      "143.204.130.84",
    "cdn-lfs-us-1.huggingface.co": "143.204.130.84",
}
def _patched_getaddrinfo(host, port, *args, **kwargs):
    return _orig_getaddrinfo(_HF_IPS.get(host, host), port, *args, **kwargs)
socket.getaddrinfo = _patched_getaddrinfo

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dataset_engine.integrity_dataset import generate_integrity_dataset
from dataset_engine.style_dataset import generate_style_dataset
from huggingface_hub import HfApi, upload_file

DATASET_REPO = "Raiff1982/codette-training-data"
HF_TOKEN = os.environ.get("HF_TOKEN")


def main():
    token = os.environ.get("HF_TOKEN")
    if not token:
        token_file = Path.home() / ".cache" / "huggingface" / "token"
        if token_file.exists():
            token = token_file.read_text().strip()
            print(f"Using cached HF token from {token_file}")
        else:
            print("ERROR: No HF_TOKEN found. Run `hf login` or set HF_TOKEN.")
            sys.exit(1)

    api = HfApi(token=token)

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)

        # ── Generate integrity dataset (includes new ethics_field examples) ──
        print("Generating integrity dataset...")
        integrity_stats = generate_integrity_dataset(str(out))

        # ── Generate style-adaptive dataset ──────────────────────────────────
        print("\nGenerating style-adaptive dataset...")
        style_stats = generate_style_dataset(str(out))

        all_stats = {**integrity_stats, **style_stats}
        total_examples = sum(all_stats.values())
        print(f"\nGenerated {total_examples} total examples across {len(all_stats)} files.")

        # ── Upload each file ──────────────────────────────────────────────────
        print(f"\nUploading to {DATASET_REPO}...")
        uploaded = 0
        failed = []

        for filename, count in sorted(all_stats.items()):
            local_path = out / filename
            if not local_path.exists():
                print(f"  SKIP (not found): {filename}")
                continue
            try:
                api.upload_file(
                    path_or_fileobj=str(local_path),
                    path_in_repo=filename,
                    repo_id=DATASET_REPO,
                    repo_type="dataset",
                    token=token,
                    commit_message=f"v5 update: {filename} ({count} examples)",
                )
                print(f"  OK: {filename}  ({count} examples)")
                uploaded += 1
            except Exception as e:
                print(f"  FAIL: {filename}: {e}")
                failed.append(filename)

        print(f"\nUploaded {uploaded}/{len(all_stats)} files to {DATASET_REPO}")
        if failed:
            print(f"Failed: {failed}")
            sys.exit(1)

        print(f"\nDataset repo: https://huggingface.co/datasets/{DATASET_REPO}")


if __name__ == "__main__":
    main()
