#!/usr/bin/env python3
"""Phase 0 ablation — which version of Codette's mind is real?

Runs GPQA-main reason mode (n=100) across three arms sequentially:
  1. _base       — raw model, no adapter (do the adapters help at all?)
  2. (default)   — serial multi-perspective: route -> N adapters -> synthesis -> AAP
  3. blend:auto  — weight-level perspective mixing (single generation)

The fourth arm (forced newton) was measured 2026-07-05: 34.0%.

Requires the Codette server running (OpenVINO backend).
Each arm takes roughly 1-2.5 hours; total ~4-5 hours. Run overnight:

    python scripts/run_phase0_ablation.py

Per-arm logs go to data/results/phase0_<arm>.log; result JSONs are the
standard gpqa_codette_reason_*.json files (one per arm, by timestamp).
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "benchmarks" / "gpqa_codette.py"
LOGDIR = ROOT / "data" / "results"
LOGDIR.mkdir(parents=True, exist_ok=True)

ARMS = [
    ("base",   ["--adapter", "_base"]),
    ("serial", []),                       # default routing: multi-perspective
    ("blend",  ["--adapter", "blend:auto"]),
]

COMMON = ["--mode", "reason", "--dataset", "gpqa_main.csv", "--limit", "100"]


def main():
    print(f"Phase 0 ablation — 3 arms x 100 questions (newton arm done 2026-07-05: 34.0%)")
    summaries = []
    for name, extra in ARMS:
        log_path = LOGDIR / f"phase0_{name}.log"
        cmd = [sys.executable, str(BENCH)] + COMMON + extra
        print(f"\n=== ARM: {name} ===")
        print(f"  cmd: {' '.join(cmd)}")
        print(f"  log: {log_path}")
        t0 = time.time()
        with open(log_path, "w", encoding="utf-8", errors="replace") as log:
            proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
                                  cwd=str(ROOT))
        elapsed = (time.time() - t0) / 60
        # Pull the accuracy line out of the log
        acc = "?"
        try:
            for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
                if "Accuracy:" in line:
                    acc = line.strip()
        except Exception:
            pass
        status = "OK" if proc.returncode == 0 else f"EXIT {proc.returncode}"
        print(f"  [{status}] {acc}  ({elapsed:.0f} min)")
        summaries.append((name, status, acc, f"{elapsed:.0f} min"))

    print("\n" + "=" * 60)
    print("PHASE 0 ABLATION COMPLETE")
    print("=" * 60)
    print(f"  {'newton':8s} 2026-07-05        Accuracy: 34.0%")
    for name, status, acc, mins in summaries:
        print(f"  {name:8s} {status:8s} {acc}  {mins}")
    print("\nResult JSONs: data/results/gpqa_codette_reason_*.json")


if __name__ == "__main__":
    main()
