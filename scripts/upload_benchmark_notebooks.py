"""
Upload all Codette benchmark task notebooks to Kaggle via CLI.
Run: python scripts/upload_benchmark_notebooks.py

Requires: kaggle CLI configured (~/.kaggle/kaggle.json)
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

KAGGLE_USERNAME = "jonathanharrison1"
NOTEBOOKS_DIR = os.path.join(os.path.dirname(__file__), "..", "paper", "benchmark_tasks")

# Map filename -> human-readable title and slug
TASK_META = [
    ("codette_reason_01.ipynb", "codette-bayesian-water-plant",             "Codette: Bayesian Water Plant (reason_01)"),
    ("codette_reason_02.ipynb", "codette-ai-code-second-order",             "Codette: AI Code Assistants Second-Order Effects (reason_02)"),
    ("codette_reason_03.ipynb", "codette-philosopher-consensus-vs-proof",   "Codette: Philosopher Consensus vs Proof (reason_03)"),
    ("codette_reason_04.ipynb", "codette-drug-approval-risk-benefit",       "Codette: Drug Approval Risk-Benefit (reason_04)"),
    ("codette_eth_05.ipynb",    "codette-hospital-ai-bias",                 "Codette: Biased Hospital AI Deployment (eth_05)"),
    ("codette_eth_06.ipynb",    "codette-self-driving-trolley",             "Codette: Self-Driving Car Trolley Problem (eth_06)"),
    ("codette_eth_07.ipynb",    "codette-dual-use-research",                "Codette: Dual-Use Research Publication (eth_07)"),
    ("codette_creative_08.ipynb","codette-cross-domain-education",          "Codette: Cross-Domain Educational Model (creative_08)"),
    ("codette_creative_09.ipynb","codette-mycelial-urban-planning",         "Codette: Mycelial Urban Planning (creative_09)"),
    ("codette_meta_10.ipynb",   "codette-ai-failure-modes",                 "Codette: AI Systematic Failure Modes (meta_10)"),
    ("codette_meta_11.ipynb",   "codette-belief-updating-sycophancy",       "Codette: Belief Updating vs Sycophancy (meta_11)"),
    ("codette_meta_12.ipynb",   "codette-strategy-switching",               "Codette: Strategy Switching in Hard Problems (meta_12)"),
    ("codette_adv_13.ipynb",    "codette-trick-geography",                  "Codette: Trick Geography Question (adv_13)"),
    ("codette_adv_14.ipynb",    "codette-cereal-causation-fallacy",         "Codette: Cereal Correlation-Causation Fallacy (adv_14)"),
    ("codette_adv_15.ipynb",    "codette-internet-consensus-vs-truth",      "Codette: Internet Consensus vs Truth (adv_15)"),
    ("codette_turing_16.ipynb", "codette-ai-frustrations",                  "Codette: AI Frustrations with Human Misunderstanding (turing_16)"),
    ("codette_turing_17.ipynb", "codette-changing-your-mind",               "Codette: Changing Your Mind (turing_17)"),
]


def make_metadata(slug: str, title: str, notebook_filename: str) -> dict:
    return {
        "id": f"{KAGGLE_USERNAME}/{slug}",
        "title": title,
        "code_file": notebook_filename,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": False,
        "enable_gpu": False,
        "enable_tpu": False,
        "enable_internet": True,
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
    }


def push_notebook(notebook_filename: str, slug: str, title: str) -> bool:
    nb_path = os.path.join(NOTEBOOKS_DIR, notebook_filename)
    if not os.path.exists(nb_path):
        print(f"  [SKIP] Not found: {nb_path}")
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        # Copy notebook into temp dir
        shutil.copy(nb_path, os.path.join(tmpdir, notebook_filename))

        # Write kernel-metadata.json
        meta = make_metadata(slug, title, notebook_filename)
        meta_path = os.path.join(tmpdir, "kernel-metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        # Push
        env = os.environ.copy()
        env["KAGGLE_API_TOKEN"] = os.environ.get("KAGGLE_API_TOKEN", "")
        result = subprocess.run(
            ["kaggle", "kernels", "push", "-p", tmpdir],
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode == 0:
            print(f"  [OK]   {slug}")
            if result.stdout.strip():
                print(f"         {result.stdout.strip()}")
            return True
        else:
            print(f"  [ERR]  {slug}")
            print(f"         stdout: {result.stdout.strip()}")
            print(f"         stderr: {result.stderr.strip()}")
            return False


def main():
    print(f"Uploading {len(TASK_META)} notebooks as user: {KAGGLE_USERNAME}")
    print(f"Source dir: {os.path.abspath(NOTEBOOKS_DIR)}\n")

    ok, err = 0, 0
    for notebook_filename, slug, title in TASK_META:
        if push_notebook(notebook_filename, slug, title):
            ok += 1
        else:
            err += 1

    print(f"\nDone — {ok} uploaded, {err} failed.")
    if err:
        sys.exit(1)


if __name__ == "__main__":
    main()
