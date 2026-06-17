#!/usr/bin/env python3
"""Submit the 7-adapter perspective retrain to HF Jobs (uv).

Two explicit steps so nothing spends credits by accident:
  1) python submit_perspectives_uv.py --upload-data   # back up v1s + upload v2s (cheap)
  2) python submit_perspectives_uv.py --submit        # GPU training job (spends credits)

Requires HF_TOKEN in env or a cached `hf auth login` token.
"""
import argparse, json, os, sys
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download

DATASET_REPO = "Raiff1982/codette-training-data"
OUTPUT_REPO  = "Raiff1982/codette-lora-adapters"
LOCAL_DIR    = Path("dataset_engine/v2")
SCRIPT       = "training/train_perspectives_uv.py"
FLAVOR       = "a10g-large"
TIMEOUT      = "90m"
ADAPTERS     = ["newton", "davinci", "philosophy", "quantum",
                "consciousness", "multi_perspective", "systems_architecture"]


def _token() -> str:
    tok = os.environ.get("HF_TOKEN")
    if not tok:
        try:
            from huggingface_hub import get_token
            tok = get_token()
        except Exception:
            tok = None
    if not tok:
        print("ERROR: no HF token (set HF_TOKEN or run `hf auth login`)."); sys.exit(1)
    return tok


def upload_data(api, token):
    try:
        existing = set(api.list_repo_files(DATASET_REPO, repo_type="dataset", token=token))
    except Exception:
        existing = set()
    for name in ADAPTERS:
        local = LOCAL_DIR / f"{name}_reasoning.jsonl"
        if not local.exists():
            print(f"  MISSING {local} — run: python -m dataset_engine.perspectives_dataset_v2"); sys.exit(1)
        hub = f"{name}_reasoning.jsonl"
        backup = f"{name}_reasoning_templated_v1.jsonl"
        if hub in existing and backup not in existing:
            old = hf_hub_download(DATASET_REPO, hub, repo_type="dataset", token=token)
            api.upload_file(path_or_fileobj=old, path_in_repo=backup,
                            repo_id=DATASET_REPO, repo_type="dataset", token=token)
            print(f"  backed up {name} v1 -> {backup}")
        n = sum(1 for _ in local.open(encoding="utf-8"))
        api.upload_file(path_or_fileobj=str(local), path_in_repo=hub,
                        repo_id=DATASET_REPO, repo_type="dataset", token=token)
        print(f"  uploaded {name} v2 ({n} ex) -> {hub}")


def submit(api, token):
    print(f"Submitting {SCRIPT} flavor={FLAVOR} timeout={TIMEOUT}")
    job = api.run_uv_job(script=SCRIPT, flavor=FLAVOR, timeout=TIMEOUT,
                         env={"HF_TOKEN": token}, token=token)
    print(f"[SUCCESS] job {job.id}\n  {job.url}")
    print(f"  adapters upload to {OUTPUT_REPO}/{{name}}_v2 (verify, then convert+promote)")
    Path("perspectives_job_info.json").write_text(json.dumps(
        {"job_id": job.id, "url": job.url, "adapters": ADAPTERS}, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upload-data", action="store_true")
    ap.add_argument("--submit", action="store_true")
    a = ap.parse_args()
    token = _token(); api = HfApi(token=token)
    if a.upload_data: upload_data(api, token)
    if a.submit: submit(api, token)
    if not (a.upload_data or a.submit):
        print("DRY RUN. Step 1: --upload-data  Step 2: --submit")


if __name__ == "__main__":
    main()
