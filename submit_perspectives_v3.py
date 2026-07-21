#!/usr/bin/env python3
"""Submit v3 targeted retrain (quantum, multi_perspective, newton) to HF Jobs.

Datasets are already uploaded to codette-training-data as *_v3.jsonl.
This script just submits the GPU job.

  python submit_perspectives_v3.py           # dry-run, prints what would happen
  python submit_perspectives_v3.py --submit  # actually spends GPU credits
"""
import argparse, json, os, sys
from pathlib import Path
from huggingface_hub import HfApi, get_token

SCRIPT  = "training/train_perspectives_v3_uv.py"
FLAVOR  = "a10g-large"
TIMEOUT = "45m"


def _token() -> str:
    tok = os.environ.get("HF_TOKEN") or get_token()
    if not tok:
        print("ERROR: no HF token"); sys.exit(1)
    return tok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--submit", action="store_true", help="Actually submit GPU job")
    args = ap.parse_args()

    token = _token()
    api = HfApi(token=token)

    if not args.submit:
        print("DRY RUN — add --submit to actually spend credits")
        print(f"  Script:  {SCRIPT}")
        print(f"  Flavor:  {FLAVOR}")
        print(f"  Timeout: {TIMEOUT}")
        print(f"  Adapters: quantum_v3, multi_perspective_v3, newton_v3")
        return

    print(f"Submitting {SCRIPT} on {FLAVOR} (timeout {TIMEOUT})...")
    job = api.run_uv_job(
        script=SCRIPT,
        flavor=FLAVOR,
        timeout=TIMEOUT,
        env={"HF_TOKEN": token},
        token=token,
    )
    print(f"[SUCCESS] job {job.id}")
    print(f"  URL: {job.url}")
    print(f"  Adapters will upload to Raiff1982/codette-lora-adapters/{{name}}_v3")
    Path("perspectives_v3_job_info.json").write_text(json.dumps(
        {"job_id": job.id, "url": job.url,
         "adapters": ["quantum", "multi_perspective", "newton"],
         "version": "v3"}, indent=2))


if __name__ == "__main__":
    main()
