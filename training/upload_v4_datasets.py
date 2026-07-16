#!/usr/bin/env python3
"""Upload v4 hand-authored datasets to HuggingFace.

Run locally before training:
    pip install huggingface_hub
    HF_TOKEN=hf_... python training/upload_v4_datasets.py

Or from the repo root with the token in your environment.
"""

import os
import sys
from pathlib import Path
from huggingface_hub import HfApi, login

REPO = Path(__file__).resolve().parent.parent
V4_DIR = REPO / "dataset_engine" / "v4"
EMPATHY_FILE = REPO / "dataset_engine" / "empathy_reasoning.jsonl"
DATASET_REPO = "Raiff1982/codette-training-data"

ADAPTERS = [
    "newton", "davinci", "empathy", "philosophy", "quantum",
    "consciousness", "multi_perspective", "systems_architecture",
]

HF_TOKEN = os.environ.get("HF_TOKEN")
if HF_TOKEN:
    login(token=HF_TOKEN)
api = HfApi(token=HF_TOKEN)  # None -> falls back to cached `hf auth login` credentials

uploaded = []
skipped = []

for name in ADAPTERS:
    if name == "empathy":
        src = EMPATHY_FILE
    else:
        src = V4_DIR / f"{name}_reasoning.jsonl"

    if not src.exists():
        skipped.append(name)
        print(f"  SKIP {name}: {src.name} not found")
        continue

    lines = sum(1 for _ in open(src, encoding="utf-8"))
    remote_name = f"{name}_v4.jsonl"
    print(f"  Uploading {name}: {lines} examples -> {remote_name}")

    api.upload_file(
        path_or_fileobj=str(src),
        path_in_repo=remote_name,
        repo_id=DATASET_REPO,
        repo_type="dataset",
        commit_message=f"v4 hand-authored {name} dataset ({lines} examples)",
    )
    uploaded.append(f"{name} ({lines})")

print(f"\nUploaded: {', '.join(uploaded)}")
if skipped:
    print(f"Skipped (no file): {', '.join(skipped)}")
print(f"\nhttps://huggingface.co/datasets/{DATASET_REPO}")
