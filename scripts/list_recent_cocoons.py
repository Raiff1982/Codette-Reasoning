#!/usr/bin/env python3
"""List the most recent cocoons with key fields at a glance.

Usage:
    python scripts/list_recent_cocoons.py
    python scripts/list_recent_cocoons.py --n 30
    python scripts/list_recent_cocoons.py --store dev_cocoons/ --n 10
    python scripts/list_recent_cocoons.py --filter high-echo
    python scripts/list_recent_cocoons.py --filter low-integrity
"""
import argparse
import json
import sys
from pathlib import Path


INTEGRITY_COLORS = {
    "complete": "OK  ",
    "partial":  "WARN",
    "failed":   "FAIL",
}

ECHO_MARKERS = {
    "low":     "ok  ",
    "medium":  "warn",
    "high":    "HIGH",
    "unknown": "?   ",
}

PATH_WIDTH = 20


def load_summary(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        v3 = data.get("v3", {})
        if data.get("type") == "reasoning_v3" and v3:
            return {
                "id":         path.stem,
                "mtime":      path.stat().st_mtime,
                "type":       "v3",
                "exec_path":  v3.get("execution_path", "unknown"),
                "integrity":  v3.get("cocoon_integrity", "?"),
                "score":      v3.get("cocoon_integrity_score", 0.0),
                "echo_risk":  v3.get("echo_risk", "unknown"),
                "collapse":   v3.get("perspective_collapse_detected", False),
                "query":      v3.get("query", "")[:60],
                "missing":    v3.get("missing_fields", []),
            }
        else:
            wrapped = data.get("wrapped", data)
            return {
                "id":         path.stem,
                "mtime":      path.stat().st_mtime,
                "type":       "legacy",
                "exec_path":  "unknown",
                "integrity":  "legacy",
                "score":      0.0,
                "echo_risk":  "unknown",
                "collapse":   False,
                "query":      str(wrapped.get("query", ""))[:60],
                "missing":    [],
            }
    except Exception as e:
        return {
            "id":        path.stem,
            "mtime":     path.stat().st_mtime,
            "type":      "error",
            "exec_path": "error",
            "integrity": "error",
            "score":     0.0,
            "echo_risk": "unknown",
            "collapse":  False,
            "query":     f"[parse error: {e}]",
            "missing":   [],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="List recent Codette cocoons.")
    parser.add_argument("--n", type=int, default=20, help="How many cocoons to show (default: 20)")
    parser.add_argument("--store", default="cocoons", help="Cocoon store directory (default: cocoons/)")
    parser.add_argument(
        "--filter",
        choices=["high-echo", "low-integrity", "legacy", "quarantined"],
        help="Show only cocoons matching a condition",
    )
    args = parser.parse_args()

    store = Path(args.store)
    quarantine = store / "quarantine"

    paths = sorted(store.glob("cocoon_*.json"), key=lambda p: p.stat().st_mtime)
    if args.filter == "quarantined":
        paths = sorted(quarantine.glob("cocoon_*.json"), key=lambda p: p.stat().st_mtime) if quarantine.exists() else []

    if not paths:
        print(f"No cocoons found in {store}/")
        sys.exit(0)

    summaries = [load_summary(p) for p in paths]

    # Apply filter
    if args.filter == "high-echo":
        summaries = [s for s in summaries if s["echo_risk"] == "high"]
    elif args.filter == "low-integrity":
        summaries = [s for s in summaries if s["score"] < 0.5]
    elif args.filter == "legacy":
        summaries = [s for s in summaries if s["type"] == "legacy"]

    # Most recent first, capped at --n
    summaries = list(reversed(summaries))[:args.n]

    if not summaries:
        print(f"No cocoons match filter={args.filter!r}")
        sys.exit(0)

    # Header
    header = (
        f"{'#':<4} "
        f"{'ID (stem)':<36} "
        f"{'exec_path':<20} "
        f"{'integ':<8} "
        f"{'score':<6} "
        f"{'echo':<6} "
        f"{'query'}"
    )
    print(f"\n{header}")
    print("─" * len(header))

    for i, s in enumerate(summaries, 1):
        integ_marker = INTEGRITY_COLORS.get(s["integrity"], s["integrity"][:4])
        echo_marker  = ECHO_MARKERS.get(s["echo_risk"], "?   ")
        score_str    = f"{s['score']:.2f}"
        flags = ""
        if s["collapse"]:
            flags += " [COLLAPSE]"
        if s["missing"]:
            flags += f" [MISSING:{len(s['missing'])}]"

        print(
            f"{i:<4} "
            f"{s['id']:<36} "
            f"{s['exec_path']:<20} "
            f"{integ_marker:<8} "
            f"{score_str:<6} "
            f"{echo_marker:<6} "
            f"{s['query']}{flags}"
        )

    print(f"\n  Showing {len(summaries)} of {len(paths)} cocoon(s) in {store}/")
    legacy_count = sum(1 for s in summaries if s["type"] == "legacy")
    if legacy_count:
        print(f"  WARNING: {legacy_count} legacy (pre-v3) cocoon(s) in this view.")
    print()


if __name__ == "__main__":
    main()
