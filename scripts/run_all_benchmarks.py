#!/usr/bin/env python3
"""Run Codette benchmark suites from one entry point."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def run_step(label: str, cmd: list[str]) -> int:
    print(f"[bench] {label}: {' '.join(cmd)}")
    completed = subprocess.run(cmd, cwd=ROOT)
    if completed.returncode != 0:
        print(f"[bench] {label} failed with code {completed.returncode}")
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Codette benchmark suites from one command.")
    parser.add_argument("--include-runtime", action="store_true", help="Also run the live runtime benchmark against a running local server.")
    parser.add_argument("--include-web", action="store_true", help="When running runtime benchmark, include the web-research case too.")
    parser.add_argument("--base-url", default="http://localhost:7860", help="Base URL for the live runtime benchmark.")
    args = parser.parse_args(argv)

    steps = [
        ("publishable-benchmark", [sys.executable, "benchmarks/codette_benchmark_suite.py"]),
    ]

    if args.include_runtime:
        runtime_cmd = [sys.executable, "benchmarks/codette_runtime_benchmark.py", "--base-url", args.base_url]
        if args.include_web:
            runtime_cmd.append("--include-web")
        steps.append(("runtime-benchmark", runtime_cmd))

    failed = 0
    for label, cmd in steps:
        code = run_step(label, cmd)
        if code != 0:
            failed = code
            break

    if failed == 0:
        print("[bench] all requested benchmarks completed")
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
