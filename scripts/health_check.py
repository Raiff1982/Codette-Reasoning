#!/usr/bin/env python3
"""Lightweight Codette health check — surfaces cocoon integrity metrics at a glance.

Checks:
  - v3_missing_fallback_count  (regression alarm from cognition_cocooner)
  - Recent cocoon average integrity score
  - Execution path distribution over last N cocoons
  - Echo risk distribution
  - Quarantine count

Usage:
    python scripts/health_check.py
    python scripts/health_check.py --store dev_cocoons/ --n 50
    python scripts/health_check.py --strict   # exit 1 if any check fails
"""
import argparse
import json
import sys
from pathlib import Path
from collections import Counter


def _bar(value: float, width: int = 20) -> str:
    if value is None:
        return "n/a"
    filled = int(round(value * width))
    return "[" + "#" * filled + "." * (width - filled) + f"] {value:.3f}"


def load_cocoon_meta(path: Path) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        v3 = data.get("v3", {})
        if data.get("type") == "reasoning_v3" and v3:
            return {
                "exec_path":  v3.get("execution_path", "unknown"),
                "integrity":  v3.get("cocoon_integrity", "?"),
                "score":      float(v3.get("cocoon_integrity_score", 0.0)),
                "echo_risk":  v3.get("echo_risk", "unknown"),
                "collapse":   bool(v3.get("perspective_collapse_detected", False)),
                "type":       "v3",
            }
        return {"exec_path": "unknown", "integrity": "legacy", "score": 0.0,
                "echo_risk": "unknown", "collapse": False, "type": "legacy"}
    except Exception:
        return None


def check_fallback_count() -> tuple[int, bool]:
    """Return (count, is_ok). Imports live counter from this process."""
    try:
        from reasoning_forge.cognition_cocooner import get_v3_fallback_count
        count = get_v3_fallback_count()
        return count, count == 0
    except ImportError:
        return -1, True  # can't check, don't fail


def main() -> None:
    parser = argparse.ArgumentParser(description="Codette cocoon health check.")
    parser.add_argument("--store", default="cocoons", help="Cocoon store directory (default: cocoons/)")
    parser.add_argument("--n", type=int, default=50, help="Scan last N cocoons (default: 50)")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any check fails")
    args = parser.parse_args()

    store = Path(args.store)
    quarantine = store / "quarantine"
    failures = []

    print(f"\nCodette Health Check  —  store: {store}/  sample: last {args.n}")
    print("=" * 56)

    # ── Regression alarm ─────────────────────────────────────────────────────
    fallback_count, fallback_ok = check_fallback_count()
    if fallback_count >= 0:
        marker = "OK  " if fallback_ok else "FAIL"
        print(f"  [{marker}] v3_missing_fallback_count : {fallback_count}")
        if not fallback_ok:
            failures.append(f"v3_missing_fallback_count={fallback_count} (should be 0)")
    else:
        print("  [????] v3_missing_fallback_count : (module not imported yet)")

    # ── Cocoon store scan ─────────────────────────────────────────────────────
    all_paths = sorted(store.glob("cocoon_*.json"), key=lambda p: p.stat().st_mtime)
    total = len(all_paths)
    sample = [load_cocoon_meta(p) for p in all_paths[-args.n:]]
    sample = [s for s in sample if s is not None]

    quarantine_count = len(list(quarantine.glob("cocoon_*.json"))) if quarantine.exists() else 0

    print(f"\n  Total cocoons        : {total}")
    print(f"  Quarantined          : {quarantine_count}")

    if not sample:
        print("  (no cocoons to analyse)")
        print("\n" + "=" * 56)
        sys.exit(0)

    # ── Integrity scores ──────────────────────────────────────────────────────
    v3_cocoons = [s for s in sample if s["type"] == "v3"]
    legacy_cocoons = [s for s in sample if s["type"] == "legacy"]
    scores = [s["score"] for s in v3_cocoons]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    complete = sum(1 for s in v3_cocoons if s["integrity"] == "complete")
    partial  = sum(1 for s in v3_cocoons if s["integrity"] == "partial")
    failed   = sum(1 for s in v3_cocoons if s["integrity"] == "failed")

    score_ok = avg_score >= 0.6
    marker = "OK  " if score_ok else "WARN"
    print(f"\n  [{marker}] Avg integrity score  : {_bar(avg_score)}")
    print(f"         complete/partial/failed : {complete}/{partial}/{failed}  "
          f"(of {len(v3_cocoons)} v3 cocoons in sample)")
    if legacy_cocoons:
        print(f"  [WARN] Legacy (pre-v3) cocoons : {len(legacy_cocoons)}")
        failures.append(f"{len(legacy_cocoons)} legacy cocoons in last {args.n} (should be 0 on new paths)")

    if not score_ok:
        failures.append(f"avg integrity score {avg_score:.3f} below 0.6")

    # ── Execution path distribution ───────────────────────────────────────────
    path_counts = Counter(s["exec_path"] for s in v3_cocoons)
    print(f"\n  Execution path distribution (v3 sample):")
    for ep, count in sorted(path_counts.items(), key=lambda x: -x[1]):
        pct = count / len(v3_cocoons) * 100 if v3_cocoons else 0
        print(f"    {ep:<26} {count:>4}  ({pct:.0f}%)")
    if "unknown" in path_counts:
        failures.append(f"{path_counts['unknown']} cocoons with execution_path=unknown")

    # ── Echo risk distribution ────────────────────────────────────────────────
    echo_counts = Counter(s["echo_risk"] for s in v3_cocoons)
    high_echo = echo_counts.get("high", 0)
    print(f"\n  Echo risk distribution (v3 sample):")
    for er, count in sorted(echo_counts.items(), key=lambda x: -x[1]):
        marker = "HIGH" if er == "high" else "    "
        print(f"    {er:<12} {count:>4}  {marker}")
    if high_echo > 0:
        pct = high_echo / len(v3_cocoons) * 100 if v3_cocoons else 0
        failures.append(f"{high_echo} high-echo cocoons ({pct:.0f}%) in sample — check quarantine")

    collapse_count = sum(1 for s in v3_cocoons if s["collapse"])
    if collapse_count:
        print(f"  [WARN] Perspective collapse detected in {collapse_count} cocoon(s)")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'=' * 56}")
    if failures:
        print(f"  HEALTH: DEGRADED  ({len(failures)} issue(s))")
        for f in failures:
            print(f"    - {f}")
        print()
        if args.strict:
            sys.exit(1)
    else:
        print("  HEALTH: OK\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
