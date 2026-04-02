#!/usr/bin/env python3
"""Run a practical verification pass for Codette."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def run_step(label: str, cmd: list[str]) -> int:
    print(f"[verify] {label}: {' '.join(cmd)}")
    completed = subprocess.run(cmd, cwd=ROOT)
    if completed.returncode != 0:
        print(f"[verify] {label} failed with code {completed.returncode}")
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a verification pass over tests and optional benchmarks.")
    parser.add_argument("--include-benchmarks", action="store_true", help="Also run benchmark scripts.")
    parser.add_argument("--include-runtime", action="store_true", help="When benchmarks are enabled, include the live runtime benchmark.")
    parser.add_argument("--include-web", action="store_true", help="When runtime benchmark is enabled, include web research.")
    args = parser.parse_args(argv)

    steps = [
        ("event-embedded-value-tests", [sys.executable, "-m", "unittest", "tests.test_event_embedded_value"]),
        ("runtime-benchmark-tests", [sys.executable, "-m", "unittest", "tests.test_codette_runtime_benchmark"]),
    ]

    if args.include_benchmarks:
        bench_cmd = [sys.executable, "scripts/run_all_benchmarks.py"]
        if args.include_runtime:
            bench_cmd.append("--include-runtime")
        if args.include_web:
            bench_cmd.append("--include-web")
        steps.append(("benchmarks", bench_cmd))

    failed = 0
    for label, cmd in steps:
        code = run_step(label, cmd)
        if code != 0:
            failed = code
            break

    if failed == 0:
        print("[verify] verification completed")
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
