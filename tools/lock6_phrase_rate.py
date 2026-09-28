#!/usr/bin/env python3
"""Measure the LOCK 6 template-phrase rate in a cocoon store, dating BOTH the
hits and the sample.

Why this exists
---------------
On 2026-08-12 a recommendation to remove LOCK 6 was withdrawn (commit d869db9)
because the hits had been dated and the *sample* had not. The rate looked like it
fell to zero after the v4 retraining; in fact the corpus effectively ended in May,
so "zero after retraining" described a sample of one. The fix for that class of
error is to report N alongside every hit count, always. This script does that and
nothing else.

What the numbers mean — read this before quoting them
-----------------------------------------------------
LOCK 6 exists in two places, and they are not the same mechanism:

1. As prompt text, in ``inference/codette_orchestrator.py`` and
   ``inference/codette_shared.py`` — eight forbidden phrases, added 2026-05-26
   in ``f02c9b4``.
2. As a regex scrubber, in ``CodetteForgeBridge._apply_directness``
   (``inference/codette_forge_bridge.py``) — the ``_boilerplate`` list, added the
   same day in ``f02c9b4`` / ``3f96efc``.

The scrubber runs at step 8 of the bridge, at line ~1094. The cocoon is built and
written at lines ~1025-1077, *before* it. So **cocoons record the pre-scrub text**:
what the model actually generated, not what the user was shown.

That makes this a valid measurement of the model's raw behaviour, and it is
readable in both directions:

* a HIGH rate after 2026-05-26 means the prompt lock is not changing generation,
  and only the regex is keeping the output clean;
* a LOW rate means the prompt lock and/or the v4 retraining is doing real work.

It does NOT measure what the user saw. The regex strips these phrases from the
visible answer either way.

Usage
-----
    python tools/lock6_phrase_rate.py [STORE ...] [--split 2026-05-26] [--json out.json]

With no STORE, scans ./cocoons.  Read-only; it never writes to the store.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

# ── The eight phrases LOCK 6 forbids, transcribed from the prompt block in
#    inference/codette_shared.py.  Case-insensitive; "X" placeholders in the
#    prompt become bounded wildcards.  Whitespace is normalised before matching
#    so a line-wrapped hit still counts.
STRICT_PATTERNS: dict[str, str] = {
    "several key insights emerge":
        r"several key insights? emerge",
    "core insight is that precise understanding":
        r"the core insight is that precise understanding requires? careful analysis",
    "understanding X requires careful analysis of its core principles":
        r"understanding .{0,80}?requires? careful analysis of its core principles",
    "emotional intelligence enhances rather than replaces":
        r"emotional intelligence enhances? rather than replaces? analytical thinking",
    "key takeaway is that X rewards careful, multi-layered analysis":
        r"the key takeaway is that .{0,120}?rewards? careful,? multi-?layered analysis",
    "this analysis demonstrates how X connects to broader patterns":
        r"this analysis demonstrates how .{0,120}?connects to broader patterns of understanding",
    "bridges gaps between expert and novice understanding":
        r"bridges gaps between expert and novice understanding",
    "answering your question requires careful analysis":
        r"answering (?:your question|this) requires? careful analysis",
}

_STRICT = {k: re.compile(v, re.IGNORECASE) for k, v in STRICT_PATTERNS.items()}


def _broad_markers() -> list[str]:
    """The wider template-filler family, taken from the in-repo definition rather
    than reinvented here, so the two cannot drift apart."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from benchmarks.adapter_voice_eval import _TEMPLATE_MARKERS  # type: ignore
        return list(_TEMPLATE_MARKERS)
    except Exception:
        return []


_WS = re.compile(r"\s+")


def normalise(text: str) -> str:
    return _WS.sub(" ", text or "")


def extract_text(obj: dict) -> tuple[str, str]:
    """Return (text, source-field). Prefers the fullest recorded response."""
    for path, label in (
        (("wrapped", "response"), "wrapped.response"),
        (("v3", "user_response_text"), "v3.user_response_text"),
        (("response",), "response"),
        (("v3", "response_summary"), "v3.response_summary"),
    ):
        cur: object = obj
        for key in path:
            if not isinstance(cur, dict):
                cur = None
                break
            cur = cur.get(key)
        if isinstance(cur, str) and cur.strip():
            return cur, label
    return "", "<none>"


def extract_ts(obj: dict) -> float | None:
    """Unix timestamp, from whichever field carries one."""
    for path in (
        ("timestamp",), ("timestamp_unix",),
        ("wrapped", "timestamp"), ("v3", "timestamp"),
    ):
        cur: object = obj
        for key in path:
            if not isinstance(cur, dict):
                cur = None
                break
            cur = cur.get(key)
        if isinstance(cur, (int, float)) and cur > 0:
            return float(cur)
    iso = obj.get("timestamp_iso")
    if isinstance(iso, str):
        try:
            return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
        except ValueError:
            pass
    return None


def scan(store: str, split_ts: float, broad: list[str]) -> dict:
    per_month_n: Counter[str] = Counter()
    per_month_hits: Counter[str] = Counter()
    per_month_broad: Counter[str] = Counter()
    phrase_hits: Counter[str] = Counter()
    broad_hits: Counter[str] = Counter()
    sides = {"before": {"n": 0, "strict": 0, "broad": 0},
             "after": {"n": 0, "strict": 0, "broad": 0},
             "undated": {"n": 0, "strict": 0, "broad": 0}}
    examples: dict[str, list[str]] = defaultdict(list)
    unparseable: list[str] = []
    no_text = 0
    total_files = 0

    for name in sorted(os.listdir(store)):
        path = os.path.join(store, name)
        if not os.path.isfile(path):
            continue
        total_files += 1
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                obj = json.load(fh)
        except Exception:
            unparseable.append(name)
            continue
        if not isinstance(obj, dict):
            unparseable.append(name)
            continue

        text, _src = extract_text(obj)
        if not text:
            no_text += 1
            continue
        flat = normalise(text)
        low = flat.lower()

        struck = [label for label, rx in _STRICT.items() if rx.search(flat)]
        broad_struck = [m for m in broad if m in low]

        ts = extract_ts(obj)
        if ts is None:
            month, side = "no-timestamp", "undated"
        else:
            month = datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m")
            side = "before" if ts < split_ts else "after"

        per_month_n[month] += 1
        sides[side]["n"] += 1
        if struck:
            per_month_hits[month] += 1
            sides[side]["strict"] += 1
            for label in struck:
                phrase_hits[label] += 1
                if len(examples[label]) < 3:
                    examples[label].append(f"{name} [{month}]")
        if broad_struck:
            per_month_broad[month] += 1
            sides[side]["broad"] += 1
            for m in broad_struck:
                broad_hits[m] += 1

    return {
        "store": store,
        "files_seen": total_files,
        "unparseable": unparseable,
        "no_text": no_text,
        "per_month_n": dict(per_month_n),
        "per_month_strict": dict(per_month_hits),
        "per_month_broad": dict(per_month_broad),
        "phrase_hits": dict(phrase_hits),
        "broad_hits": dict(broad_hits),
        "sides": sides,
        "examples": {k: v for k, v in examples.items()},
    }


def _pct(hits: int, n: int) -> str:
    return "—" if not n else f"{100.0 * hits / n:.2f}%"


def report(res: dict, split: str) -> None:
    print(f"\n=== {res['store']} ===")
    print(f"files seen        : {res['files_seen']}")
    print(f"unparseable       : {len(res['unparseable'])}"
          + (f"  {res['unparseable'][:5]}" if res["unparseable"] else ""))
    print(f"no response text  : {res['no_text']}")

    n_scanned = sum(res["per_month_n"].values())
    print(f"scanned (has text): {n_scanned}")

    print(f"\n{'month':<14}{'cocoons':>9}{'strict':>9}{'rate':>9}{'broad':>9}{'rate':>9}")
    for month in sorted(res["per_month_n"]):
        n = res["per_month_n"][month]
        s = res["per_month_strict"].get(month, 0)
        b = res["per_month_broad"].get(month, 0)
        print(f"{month:<14}{n:>9}{s:>9}{_pct(s, n):>9}{b:>9}{_pct(b, n):>9}")

    print(f"\nsplit at {split} (f02c9b4 — LOCK 6 prompt text AND the regex scrubber)")
    print(f"{'side':<14}{'cocoons':>9}{'strict':>9}{'rate':>9}{'broad':>9}{'rate':>9}")
    for side in ("before", "after", "undated"):
        d = res["sides"][side]
        print(f"{side:<14}{d['n']:>9}{d['strict']:>9}{_pct(d['strict'], d['n']):>9}"
              f"{d['broad']:>9}{_pct(d['broad'], d['n']):>9}")

    if res["phrase_hits"]:
        print("\nstrict hits by phrase:")
        for label, count in sorted(res["phrase_hits"].items(), key=lambda kv: -kv[1]):
            print(f"  {count:>5}  {label}")
            for ex in res["examples"].get(label, []):
                print(f"         e.g. {ex}")
    else:
        print("\nstrict hits by phrase: none")

    if res["broad_hits"]:
        print("\nbroad markers (top 12):")
        for marker, count in sorted(res["broad_hits"].items(), key=lambda kv: -kv[1])[:12]:
            print(f"  {count:>5}  {marker!r}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stores", nargs="*", default=None,
                    help="cocoon directories (default: ./cocoons)")
    ap.add_argument("--split", default="2026-05-26",
                    help="ISO date dividing before/after (default: LOCK 6's landing, f02c9b4)")
    ap.add_argument("--json", dest="json_out", default=None,
                    help="write the full result to this path")
    args = ap.parse_args()

    stores = args.stores or [os.path.join(os.getcwd(), "cocoons")]
    split_ts = datetime.fromisoformat(args.split).replace(tzinfo=timezone.utc).timestamp()

    broad = _broad_markers()
    if not broad:
        print("warning: could not import _TEMPLATE_MARKERS; broad columns will read 0",
              file=sys.stderr)

    results = []
    for store in stores:
        if not os.path.isdir(store):
            print(f"skip (not a directory): {store}", file=sys.stderr)
            continue
        res = scan(store, split_ts, broad)
        results.append(res)
        report(res, args.split)

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump({"split": args.split, "results": results}, fh, indent=1)
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
