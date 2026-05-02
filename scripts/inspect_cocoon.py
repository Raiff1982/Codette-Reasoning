#!/usr/bin/env python3
"""Human-friendly cocoon inspector.

Usage:
    python scripts/inspect_cocoon.py cocoons/cocoon_1234_5678.json
    python scripts/inspect_cocoon.py cocoon_1234_5678          # resolves from cocoons/
    python scripts/inspect_cocoon.py --latest                  # most recent cocoon
    python scripts/inspect_cocoon.py --latest --store dev_cocoons/
"""
import argparse
import json
import sys
from pathlib import Path


def _bar(value: float, width: int = 20) -> str:
    if value is None:
        return "n/a"
    filled = int(round(value * width))
    return "[" + "#" * filled + "." * (width - filled) + f"] {value:.3f}"


def _section(title: str) -> None:
    print(f"\n  {'─' * 4} {title} {'─' * (40 - len(title))}")


def inspect(path: Path) -> None:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    v3 = data.get("v3", {})
    is_v3 = data.get("type") == "reasoning_v3" and v3

    print(f"\n{'=' * 56}")
    print(f"  Cocoon: {path.name}")
    print(f"  Schema: {data.get('schema_version', data.get('type', 'legacy'))}")
    print(f"{'=' * 56}")

    if not is_v3:
        print("  [LEGACY] No v3 block — this is a shallow pre-v3 cocoon.")
        wrapped = data.get("wrapped", data)
        print(f"  Query    : {str(wrapped.get('query', ''))[:80]}")
        print(f"  Response : {str(wrapped.get('response', ''))[:120]}")
        print(f"  Adapter  : {wrapped.get('adapter', 'unknown')}")
        return

    # ── Identity ─────────────────────────────────────────────────────────────
    _section("Identity")
    print(f"  execution_path         : {v3.get('execution_path', '?')}")
    print(f"  model_inference_invoked: {v3.get('model_inference_invoked', '?')}")
    print(f"  orchestrator_trace_id  : {v3.get('orchestrator_trace_id', '?')[:36]}")

    # ── Integrity ─────────────────────────────────────────────────────────────
    _section("Integrity")
    integrity = v3.get("cocoon_integrity", "?")
    score = v3.get("cocoon_integrity_score")
    marker = "OK" if integrity == "complete" else ("WARN" if integrity == "partial" else "FAIL")
    print(f"  cocoon_integrity       : {integrity}  [{marker}]")
    print(f"  cocoon_integrity_score : {_bar(score)}")
    missing = v3.get("missing_fields", [])
    if missing:
        print(f"  missing_fields         : {', '.join(missing)}")

    # ── Echo / Collapse ───────────────────────────────────────────────────────
    _section("Echo / Collapse")
    echo = v3.get("echo_risk", "unknown")
    collapse = v3.get("perspective_collapse_detected", False)
    echo_marker = {"low": "OK", "medium": "WARN", "high": "FAIL"}.get(echo, "?")
    print(f"  echo_risk              : {echo}  [{echo_marker}]")
    print(f"  perspective_collapse   : {collapse}")

    # ── Cognitive Metrics ─────────────────────────────────────────────────────
    _section("Cognitive Metrics")
    print(f"  epsilon (tension)      : {_bar(v3.get('epsilon_value'))}")
    print(f"  gamma (coherence)      : {_bar(v3.get('gamma_coherence'))}")
    print(f"  psi_r (resonance)      : {_bar(v3.get('psi_r'))}")
    print(f"  eta   (ethics)         : {_bar(v3.get('eta_score'))}")
    print(f"  confidence             : {_bar(v3.get('confidence'))}")

    # ── Perspectives ──────────────────────────────────────────────────────────
    _section("Perspectives")
    active = v3.get("active_perspectives", [])
    dominant = v3.get("dominant_perspective", "")
    print(f"  active   : {', '.join(active) if active else 'none'}")
    print(f"  dominant : {dominant or 'none'}")
    coverage = v3.get("perspective_coverage", {})
    if coverage:
        for name, cov in sorted(coverage.items(), key=lambda x: -x[1]):
            print(f"    {name:<20} {_bar(cov, 12)}")
    tensions = v3.get("pairwise_tensions", {})
    if tensions:
        print(f"  tensions : {', '.join(f'{k}={v:.2f}' for k, v in tensions.items())}")

    # ── AEGIS Ethics ─────────────────────────────────────────────────────────
    _section("AEGIS Ethics")
    fw_scores = v3.get("aegis_framework_scores", {})
    if fw_scores:
        for fw, sc in sorted(fw_scores.items(), key=lambda x: -x[1]):
            print(f"    {fw:<26} {_bar(sc, 12)}")
        print(f"  dominant framework : {v3.get('aegis_dominant_framework', 'none')}")
    else:
        print("  (no AEGIS framework scores)")
    conflicts = v3.get("aegis_ethical_conflict_notes", [])
    if conflicts:
        for note in conflicts:
            print(f"  conflict: {note}")

    # ── Guardian / Nexus ─────────────────────────────────────────────────────
    _section("Guardian / Nexus")
    print(f"  guardian_safety        : {v3.get('guardian_safety_status', 'n/a')}")
    print(f"  guardian_trust         : {v3.get('guardian_trust_calibration', 'n/a')}")
    print(f"  nexus_risk             : {v3.get('nexus_risk_level', 'n/a')}")
    print(f"  nexus_confidence       : {_bar(v3.get('nexus_confidence'))}")

    # ── Synthesis ─────────────────────────────────────────────────────────────
    _section("Synthesis")
    conv = v3.get("synthesis_convergences", [])
    div = v3.get("synthesis_divergences", [])
    trades = v3.get("synthesis_tradeoffs", [])
    pos = v3.get("synthesis_recommended_position", "")
    if conv:
        print(f"  convergences : {'; '.join(conv)}")
    if div:
        print(f"  divergences  : {'; '.join(div)}")
    if trades:
        print(f"  tradeoffs    : {'; '.join(trades)}")
    if pos:
        print(f"  position     : {pos[:100]}")

    # ── Query / Response ──────────────────────────────────────────────────────
    _section("Query / Response")
    print(f"  query    : {v3.get('query', '')[:100]}")
    resp = v3.get("user_response_text") or v3.get("response_summary", "")
    print(f"  response : {resp[:160]}")

    print(f"\n{'=' * 56}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a Codette cocoon file.")
    parser.add_argument("cocoon", nargs="?", help="Cocoon path or ID (without .json)")
    parser.add_argument("--latest", action="store_true", help="Inspect the most recently written cocoon")
    parser.add_argument("--store", default="cocoons", help="Cocoon store directory (default: cocoons/)")
    args = parser.parse_args()

    store = Path(args.store)

    if args.latest:
        candidates = sorted(store.glob("cocoon_*.json"), key=lambda p: p.stat().st_mtime)
        if not candidates:
            print(f"No cocoons found in {store}/", file=sys.stderr)
            sys.exit(1)
        target = candidates[-1]
    elif args.cocoon:
        p = Path(args.cocoon)
        if not p.exists():
            # Try resolving relative to store
            p = store / (args.cocoon if args.cocoon.endswith(".json") else args.cocoon + ".json")
        if not p.exists():
            print(f"Cocoon not found: {args.cocoon}", file=sys.stderr)
            sys.exit(1)
        target = p
    else:
        parser.print_help()
        sys.exit(0)

    inspect(target)


if __name__ == "__main__":
    main()
