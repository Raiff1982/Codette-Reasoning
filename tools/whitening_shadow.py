#!/usr/bin/env python3
"""Shadow run of lexical whitening over a cocoon store. Read-only, changes nothing.

    python tools/whitening_shadow.py [COCOON_DIR] [--band adapter|month] [--json out.json]

Reports what the wash WOULD demote, and how that compares with the flags
`cocoon_authority` already raises. Nothing here writes to the store, to the
database, or to Codette's ranking — the point is to see what moves before
anything moves.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reasoning_forge.cocoon_authority import authority          # noqa: E402
from reasoning_forge.lexical_whitening import CorpusProfile, whiten  # noqa: E402


def load(store: str):
    out = []
    for name in sorted(os.listdir(store)):
        path = os.path.join(store, name)
        if not os.path.isfile(path) or not name.startswith("cocoon_"):
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                obj = json.load(fh)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        wrapped = obj.get("wrapped") or {}
        v3 = obj.get("v3") or {}
        text = (wrapped.get("response") or v3.get("user_response_text")
                or v3.get("response_summary") or "")
        if not text.strip():
            continue
        ts = obj.get("timestamp") or wrapped.get("timestamp") or 0
        out.append({
            "name": name,
            "response": text,
            "query": wrapped.get("query") or v3.get("query") or "",
            "adapter": wrapped.get("adapter") or v3.get("dominant_perspective") or "unknown",
            "month": (datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m")
                      if ts else "undated"),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("store", nargs="?", default="cocoons")
    ap.add_argument("--band", choices=["adapter", "month"], default="adapter",
                    help="what counts as a neighbourhood for the envelope")
    ap.add_argument("--n", type=int, default=5, help="n-gram size")
    ap.add_argument("--json", dest="json_out", default=None)
    args = ap.parse_args()

    docs = load(args.store)
    if not docs:
        print(f"no readable cocoons in {args.store}", file=sys.stderr)
        return 1
    print(f"cocoons with text: {len(docs)}   band={args.band}   n={args.n}\n")

    profile = CorpusProfile.build(
        ((d["response"], d[args.band], d["query"]) for d in docs), n=args.n)

    rows = []
    for d in docs:
        w = whiten(d["response"], d[args.band], profile)
        a = authority({"adapter": d["adapter"], "response": d["response"],
                       "query": d["query"]})
        rows.append((d, w, a))

    buckets = Counter()
    for _, w, _ in rows:
        buckets[round(w.weight, 1)] += 1
    print("washed weight distribution (1.0 = untouched, 0.2 = floor):")
    for k in sorted(buckets, reverse=True):
        bar = "#" * max(1, round(60 * buckets[k] / len(rows)))
        print(f"  {k:>4} : {buckets[k]:>5}  {bar}")

    demoted = [r for r in rows if r[1].weight < 0.9]
    flagged = [r for r in rows if r[2].flags]
    both = [r for r in rows if r[1].weight < 0.9 and r[2].flags]
    print(f"\n{'wash demotes (<0.9)':<34}{len(demoted):>6}  ({100*len(demoted)/len(rows):.1f}%)")
    print(f"{'cocoon_authority flags':<34}{len(flagged):>6}  ({100*len(flagged)/len(rows):.1f}%)")
    print(f"{'both agree':<34}{len(both):>6}")
    print(f"{'wash ONLY (authority misses)':<34}{len(demoted)-len(both):>6}")
    print(f"{'authority ONLY (wash misses)':<34}{len(flagged)-len(both):>6}")

    print("\nthe wash's own top-suppressed n-grams (most often washed out):")
    washed_terms = Counter()
    for _, w, _ in rows:
        for g, _r in w.washed_out:
            washed_terms[g] += 1
    for g, c in washed_terms.most_common(10):
        print(f"  {c:>5}  {g!r}")

    print("\nsurvives the wash — highest-peak n-grams (what it protects):")
    peak_terms = Counter()
    for _, w, _ in rows:
        for g, _r in w.peaks:
            peak_terms[g] += 1
    for g, c in peak_terms.most_common(10):
        print(f"  {c:>5}  {g!r}")

    worst = sorted(rows, key=lambda r: r[1].weight)[:3]
    print("\nmost-demoted cocoons:")
    for d, w, a in worst:
        print(f"  {d['name']}  weight={w.weight}  flatness={w.flatness}  "
              f"authority={a.flags or 'clean'}")
        print(f"     {d['response'][:100]!r}")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump([{"name": d["name"], "adapter": d["adapter"],
                        "washed_weight": w.weight, "flatness": w.flatness,
                        "authority_weight": a.weight, "authority_flags": a.flags}
                       for d, w, a in rows], fh, indent=1)
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
