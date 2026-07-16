#!/usr/bin/env python3
"""Batched full-framework GPQA runner.

Runs gpqa_codette.py in batches of BATCH_SIZE questions, restarting the
Codette server between batches to clear RAM pressure. Merges all batch
results into a single output file at the end.

Usage:
    python benchmarks/gpqa_codette_batched.py
    python benchmarks/gpqa_codette_batched.py --mode sc3 --batch-size 30
    python benchmarks/gpqa_codette_batched.py --resume   # skip already-done batches
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

RESULTS_DIR  = Path("data/results")
SERVER_SCRIPT = "inference/codette_server.py"
BENCH_SCRIPT  = "benchmarks/gpqa_codette.py"
TOTAL_Q      = 198
SERVER_URL   = "http://localhost:7860/"

# ── server helpers ────────────────────────────────────────────────────────────

def kill_server():
    # Kill only the process holding port 7860 — not every python process
    subprocess.run(
        ["powershell", "-Command",
         "$p = (Get-NetTCPConnection -LocalPort 7860 -ErrorAction SilentlyContinue).OwningProcess;"
         " if ($p) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }"],
        capture_output=True)
    time.sleep(3)


def start_server():
    subprocess.Popen(
        [sys.executable, SERVER_SCRIPT],
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
    )
    print("  Server starting...", end="", flush=True)
    import urllib.request
    for _ in range(40):
        time.sleep(5)
        try:
            r = urllib.request.urlopen(SERVER_URL + "api/health", timeout=4)
            data = json.loads(r.read())
            if data["systems"]["model"]["status"] == "OK":
                print(f" ready ({data['score']})")
                return True
        except Exception:
            print(".", end="", flush=True)
    print(" TIMEOUT — giving up")
    return False


# ── batch runner ──────────────────────────────────────────────────────────────

def run_batch(offset: int, limit: int, mode: str, dataset: str,
              max_adapters: int) -> Path | None:
    ts = time.strftime("%Y%m%d_%H%M%S")
    # gpqa_codette.py saves with its own timestamp; we'll find it after
    before = set(RESULTS_DIR.glob("gpqa_codette_*.json"))

    cmd = [
        sys.executable, BENCH_SCRIPT,
        "--dataset", dataset,
        "--mode", mode,
        "--offset", str(offset),
        "--limit", str(limit),
        "--max-adapters", str(max_adapters),
    ]
    print(f"\n  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)  # live output

    if result.returncode != 0:
        print(f"  [WARN] batch returned code {result.returncode}")

    after = set(RESULTS_DIR.glob("gpqa_codette_*.json"))
    new_files = after - before
    if new_files:
        f = sorted(new_files)[-1]
        print(f"  Batch saved: {f.name}")
        return f
    print("  [WARN] No output file found for this batch")
    return None


# ── merge ─────────────────────────────────────────────────────────────────────

def merge_batches(batch_files: list[Path], mode: str, dataset: str) -> Path:
    all_results = []
    for bf in batch_files:
        data = json.loads(bf.read_text(encoding="utf-8"))
        all_results.extend(data.get("results", []))

    correct = sum(r["correct"] for r in all_results)
    total   = len(all_results)
    acc     = correct / total if total else 0.0

    payload = {
        "model": "codette/full-framework",
        "dataset": dataset,
        "mode": mode,
        "accuracy": round(acc, 4),
        "correct": correct,
        "total": total,
        "parse_failures": sum(1 for r in all_results if r.get("answer_index") is None),
        "batches": len(batch_files),
        "baselines": {"random": 0.25, "gpt4_zero_shot": 0.39,
                      "claude_opus_3": 0.50, "human_expert": 0.65},
        "results": all_results,
    }

    if mode == "sc3":
        from collections import Counter
        counts = Counter(r.get("consensus", "?") for r in all_results)
        unanimous = counts.get("3/3", 0)
        payload["sc3_stats"] = {
            "unanimous_3_3": unanimous,
            "majority_2_3": counts.get("2/3", 0),
            "unanimous_pct": round(unanimous / total, 3) if total else 0,
        }

    ts = time.strftime("%Y%m%d_%H%M%S")
    out = RESULTS_DIR / f"gpqa_codette_{mode}_diamond_full_framework_{ts}.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"  Codette FULL FRAMEWORK  [{mode.upper()}]  diamond")
    print(f"{'='*60}")
    print(f"  Questions:  {total}")
    print(f"  Correct:    {correct}")
    print(f"  Accuracy:   {acc:.1%}")
    print(f"  vs Random:  +{acc-0.25:.1%}")
    print(f"  vs GPT-4:   {acc-0.39:+.1%}")
    print(f"  Merged from {len(batch_files)} batch files")
    print(f"  Saved:      {out}")
    print(f"{'='*60}")
    return out


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["0shot", "sc3"], default="0shot")
    ap.add_argument("--dataset", default="gpqa_diamond.csv")
    ap.add_argument("--batch-size", type=int, default=40)
    ap.add_argument("--max-adapters", type=int, default=2)
    ap.add_argument("--resume", action="store_true",
                    help="Skip batches that already have a result file")
    args = ap.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    offsets = list(range(0, TOTAL_Q, args.batch_size))
    print(f"Full-framework GPQA  [{args.mode}]  {TOTAL_Q}q  "
          f"in {len(offsets)} batches of {args.batch_size}")

    batch_files: list[Path] = []

    for i, offset in enumerate(offsets):
        limit = min(args.batch_size, TOTAL_Q - offset)
        batch_tag = f"batch{i+1}of{len(offsets)}_q{offset}-{offset+limit-1}"

        # Resume: check if already done
        if args.resume:
            existing = sorted(RESULTS_DIR.glob(f"gpqa_codette_{args.mode}_*{offset}*.json"))
            # Simpler check: look for any batch file with the right question count
            existing = [f for f in RESULTS_DIR.glob(f"gpqa_codette_{args.mode}_*.json")
                        if not "full_framework" in f.name]
            # Just warn and let the user decide
            if existing:
                print(f"\n[{i+1}/{len(offsets)}] Batch offset={offset}: "
                      f"{len(existing)} result files found — skipping. "
                      f"(Add manually to batch_files if needed)")
                continue

        print(f"\n{'='*50}")
        print(f"[{i+1}/{len(offsets)}] offset={offset}  limit={limit}  ({batch_tag})")
        print(f"{'='*50}")

        # Restart server before each batch to clear RAM pressure.
        # Skip restart on first batch if server is already up.
        import urllib.request as _ur
        server_up = False
        if i == 0:
            try:
                _r = _ur.urlopen(SERVER_URL + "api/health", timeout=4)
                _d = json.loads(_r.read())
                server_up = _d.get("systems", {}).get("model", {}).get("status") == "OK"
            except Exception:
                pass

        if server_up:
            print("  Server already healthy — skipping restart for first batch.")
        else:
            print("  Restarting server to clear RAM...")
            kill_server()
            if not start_server():
                print("  Server failed to start — aborting")
                sys.exit(1)

        bf = run_batch(offset, limit, args.mode, args.dataset, args.max_adapters)
        if bf:
            batch_files.append(bf)
        else:
            print(f"  [WARN] Batch {i+1} produced no output — continuing")

    if len(batch_files) < 2:
        print(f"\nOnly {len(batch_files)} batch file(s) — nothing to merge")
        return

    print(f"\nMerging {len(batch_files)} batches...")
    merge_batches(batch_files, args.mode, args.dataset)


if __name__ == "__main__":
    main()
