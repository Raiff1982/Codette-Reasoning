#!/usr/bin/env python3
"""Phase 0 ablation runner — the audit (roadmap July 5, 2026).

Answers two questions with numbers:
  1. Do the adapters help at all?   (_base vs newton, reason mode)
  2. Do the post-processing layers earn their place?  (LOCK / AAP /
     complexity-matcher toggled off one at a time)

Each arm: start the server with the arm's env flags, wait for health,
run benchmarks/gpqa_codette.py, capture the score, stop the server.
Results land in data/results/phase0/ (one log per arm + summary.json).

Kill-switches used (all default ON in production; this script is the
only thing that turns them off, per the shadow-first rule):
  CODETTE_LOCKS=0                -> strip PERMANENT LOCKS from prompts
  CODETTE_AAP=0                  -> ship substrate response unshaped
  CODETTE_COMPLEXITY_MATCHER=0   -> skip register prefix
  CODETTE_MANIFOLD_STEER=0       -> manifold shadow-only (pre-existing)

Usage:
    python benchmarks/phase0_ablation.py                # full matrix, n=100
    python benchmarks/phase0_ablation.py --limit 20     # quick pass
    python benchmarks/phase0_ablation.py --arms base_vs_newton   # subset
    python benchmarks/phase0_ablation.py --dry-run      # print plan only
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO / "data" / "results" / "phase0"
SERVER_PY = REPO / "inference" / "codette_server.py"
BENCH_PY = REPO / "benchmarks" / "gpqa_codette.py"

# Interpreters (per project convention: OV env serves, 3.14 benchmarks)
SERVER_PYTHON = str(REPO / "openvino_env" / "Scripts" / "python.exe")
BENCH_PYTHON = r"C:\Users\Jonathan\AppData\Local\Programs\Python\Python314\python.exe"

PORT = 7860
HEALTH_URL = f"http://127.0.0.1:{PORT}/api/health"
SERVER_STARTUP_TIMEOUT = 600   # model load can be slow on first arm
PER_QUESTION_BUDGET = 360      # seconds/question upper bound for the bench timeout

# ── The ablation matrix ──────────────────────────────────────────────
# name -> (env_overrides, bench_extra_args, description)
ARMS: dict[str, tuple[dict, list, str]] = {
    # Q1: do adapters help at all?
    "base": ({}, ["--adapter", "_base"], "no adapter — raw merged base"),
    "newton": ({}, ["--adapter", "newton"], "newton adapter forced"),

    # Q2: layer ablation (default routing path, one layer off per arm)
    "layers_all_on": ({}, [], "default path, every layer active (control)"),
    "no_locks": ({"CODETTE_LOCKS": "0"}, [], "PERMANENT LOCKS stripped"),
    "no_aap": ({"CODETTE_AAP": "0"}, [], "AAP disabled — substrate ships"),
    "no_complexity": ({"CODETTE_COMPLEXITY_MATCHER": "0"}, [],
                      "complexity/register prefix skipped"),
    "no_manifold": ({"CODETTE_MANIFOLD_STEER": "0"}, [],
                    "manifold steering shadow-only"),

    # Full immunosuppression — every post-processing layer off at once.
    # If this arm scores the same as layers_all_on, the entire post-
    # processing stack is theater on this benchmark and should be deleted.
    "lobotomy": ({"CODETTE_LOCKS": "0", "CODETTE_AAP": "0",
                  "CODETTE_COMPLEXITY_MATCHER": "0",
                  "CODETTE_MANIFOLD_STEER": "0"}, [],
                 "ALL layers off simultaneously"),
}

ARM_GROUPS = {
    "base_vs_newton": ["base", "newton"],
    "layers": ["layers_all_on", "no_locks", "no_aap", "no_complexity", "no_manifold",
               "lobotomy"],
    "all": list(ARMS.keys()),
}


def wait_for_health(timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=5) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(5)
    return False


def run_arm(name: str, env_overrides: dict, bench_args: list, limit: int,
            mode: str, dataset: str, seed: int) -> dict:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = RESULTS_DIR / f"{name}.log"
    env = os.environ.copy()
    env.update(env_overrides)

    print(f"\n{'=' * 60}\nARM: {name}  env={env_overrides or '(defaults)'}  "
          f"args={bench_args or '(default routing)'}\n{'=' * 60}", flush=True)

    server = None
    record = {"arm": name, "env": env_overrides, "bench_args": bench_args,
              "limit": limit, "mode": mode, "started": datetime.now().isoformat()}
    try:
        with open(log_path, "w", encoding="utf-8") as log:
            server = subprocess.Popen(
                [SERVER_PYTHON, str(SERVER_PY)],
                cwd=str(REPO), env=env,
                stdout=log, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
            print(f"  server pid={server.pid}, waiting for health...", flush=True)
            if not wait_for_health(SERVER_STARTUP_TIMEOUT):
                record["error"] = "server never became healthy"
                return record
            print("  server healthy — running benchmark", flush=True)

            cmd = [BENCH_PYTHON, str(BENCH_PY), "--mode", mode,
                   "--dataset", dataset, "--limit", str(limit),
                   "--seed", str(seed), "--port", str(PORT)] + bench_args
            t0 = time.time()
            bench = subprocess.run(
                cmd, cwd=str(REPO), env=env,
                capture_output=True, text=True, encoding="utf-8",
                timeout=PER_QUESTION_BUDGET * limit,
            )
            record["duration_min"] = round((time.time() - t0) / 60, 1)
            record["bench_stdout_tail"] = bench.stdout[-3000:] if bench.stdout else ""
            record["bench_returncode"] = bench.returncode

            # Parse the score line the benchmark prints (e.g. "Accuracy: 34.00% (34/100)")
            for line in (bench.stdout or "").splitlines():
                if "ccuracy" in line:
                    record["score_line"] = line.strip()
            (RESULTS_DIR / f"{name}.bench.txt").write_text(
                bench.stdout or "", encoding="utf-8")
            if bench.returncode != 0:
                record["error"] = (bench.stderr or "")[-1000:]
    except subprocess.TimeoutExpired:
        record["error"] = "benchmark timed out"
    except Exception as e:
        record["error"] = f"{type(e).__name__}: {e}"
    finally:
        if server is not None:
            try:
                server.send_signal(signal.CTRL_BREAK_EVENT)
                server.wait(timeout=20)
            except Exception:
                server.kill()
            # give the port a moment to free
            time.sleep(10)
    return record


def main() -> None:
    ap = argparse.ArgumentParser(description="Phase 0 ablation runner")
    ap.add_argument("--limit", type=int, default=100, help="questions per arm")
    ap.add_argument("--mode", default="reason", help="benchmark mode (default: reason)")
    ap.add_argument("--dataset", default="gpqa_mini.csv")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--arms", default="all",
                    help="comma list of arm names, or a group: "
                         + ", ".join(ARM_GROUPS))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.arms in ARM_GROUPS:
        selected = ARM_GROUPS[args.arms]
    else:
        selected = [a.strip() for a in args.arms.split(",") if a.strip()]
    unknown = [a for a in selected if a not in ARMS]
    if unknown:
        sys.exit(f"Unknown arms: {unknown}. Available: {list(ARMS)}")

    print(f"Phase 0 ablation — {len(selected)} arms x {args.limit} questions "
          f"({args.mode} mode, {args.dataset}, seed={args.seed})")
    for a in selected:
        env, extra, desc = ARMS[a]
        print(f"  {a:<16} {desc}")
    if args.dry_run:
        return

    summary = []
    for a in selected:
        env, extra, _ = ARMS[a]
        rec = run_arm(a, env, extra, args.limit, args.mode, args.dataset, args.seed)
        summary.append(rec)
        print(f"  -> {rec.get('score_line', rec.get('error', 'no score parsed'))}",
              flush=True)
        # checkpoint the summary after every arm — a crash loses nothing
        (RESULTS_DIR / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'=' * 60}\nPHASE 0 COMPLETE\n{'=' * 60}")
    for rec in summary:
        print(f"  {rec['arm']:<16} {rec.get('score_line', rec.get('error', '?'))}")
    print(f"\nFull logs: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
