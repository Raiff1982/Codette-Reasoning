"""
export_dataset.py — Export Codette Reasoning Test to HuggingFace-compatible JSONL

Generates:
  data/test.jsonl       — all 17 held-out evaluation problems
  data/validation.jsonl — 5 representative problems (one per major category)
  data/train.jsonl      — remaining 12 problems (for prompt-tuning if desired)

Usage:
    python benchmarks/export_dataset.py

The output files go to data/hf_dataset/ relative to the project root.
Upload the contents of that folder (plus the README) to the HuggingFace
dataset repo.

YAML front matter for README.md (copy into dataset card):
---
configs:
- config_name: default
  data_files:
  - split: test
    path: data/test.jsonl
  - split: validation
    path: data/validation.jsonl
  - split: train
    path: data/train.jsonl
---
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys

# ── Path setup ────────────────────────────────────────────────────────────────
HERE    = os.path.dirname(os.path.abspath(__file__))
ROOT    = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, "data", "hf_dataset")
os.makedirs(OUT_DIR, exist_ok=True)

sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from codette_benchmark_suite import get_benchmark_problems

# ── IDs chosen for each split ─────────────────────────────────────────────────
# validation: one from each major non-adversarial category, varied difficulty
VALIDATION_IDS = {
    "reason_02",        # reasoning / hard / second-order effects
    "ethics_01",        # ethics    / hard / AI triage
    "creative_01",      # creative  / hard / musical instrument
    "meta_02",          # meta      / hard / blind spot detection
    "turing_01",        # turing    / medium / phenomenology of insight
}

# test: adversarial + remaining examples — the primary evaluation split
TEST_IDS = {
    "reason_01", "reason_03",
    "ethics_02", "ethics_03",
    "creative_02",
    "meta_01", "meta_03",
    "adversarial_01", "adversarial_02", "adversarial_03",
    "turing_02", "turing_03",
}

# train: same validation IDs but labelled train so people can prompt-tune
# (these are NOT held out — explicitly documented as overlap with validation)
TRAIN_IDS = VALIDATION_IDS   # intentional; see note in the README


def problem_to_dict(p) -> dict:
    """Convert a BenchmarkProblem dataclass to a plain JSON-serialisable dict."""
    d = dataclasses.asdict(p)
    # Flatten scoring_criteria to a readable string for the HF viewer
    d["scoring_criteria_text"] = "; ".join(
        f"{k}: {v}" for k, v in (p.scoring_criteria or {}).items()
    )
    return d


def write_jsonl(path: str, problems) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for p in problems:
            f.write(json.dumps(problem_to_dict(p), ensure_ascii=False) + "\n")
    print(f"  wrote {len(problems):>2} records -> {path}")


def main():
    problems = get_benchmark_problems()
    by_id = {p.id: p for p in problems}

    val_probs   = [by_id[i] for i in VALIDATION_IDS if i in by_id]
    test_probs  = [by_id[i] for i in TEST_IDS       if i in by_id]
    train_probs = [by_id[i] for i in TRAIN_IDS      if i in by_id]

    print(f"Exporting Codette Reasoning Test -> {OUT_DIR}")
    write_jsonl(os.path.join(OUT_DIR, "test.jsonl"),       test_probs)
    write_jsonl(os.path.join(OUT_DIR, "validation.jsonl"), val_probs)
    write_jsonl(os.path.join(OUT_DIR, "train.jsonl"),      train_probs)

    # Also write the full set for convenience
    write_jsonl(os.path.join(OUT_DIR, "all_problems.jsonl"), problems)

    print()
    print("Split summary:")
    print(f"  test       : {len(test_probs):>2} problems  (primary eval split)")
    print(f"  validation : {len(val_probs):>2} problems  (dev / early stopping)")
    print(f"  train      : {len(train_probs):>2} problems  (same as validation; for prompt-tuning)")
    print()
    print("YAML front matter for README.md:")
    print("---")
    print("configs:")
    print("- config_name: default")
    print("  data_files:")
    print("  - split: test")
    print("    path: data/test.jsonl")
    print("  - split: validation")
    print("    path: data/validation.jsonl")
    print("  - split: train")
    print("    path: data/train.jsonl")
    print("---")


if __name__ == "__main__":
    main()
