"""What `_apply_directness` removes, measured against her own stored cocoons.

WHY:

The cocoon is written BEFORE the scrubber runs (`codette_forge_bridge.py`:
built ~1025-1077, `_apply_directness` applied ~1094). So her store holds the
pre-scrub text and the person was shown the post-scrub text, and there is no
mapping between them. Recall reads the store. The material most likely to come
back as her own voice is material that was judged unfit to say.

The scrubber has no inverse and nothing records what it took. This tool is the
free half of the question: run it offline over what is stored and diff. It
answers "what does it remove" without asking her anything and without touching
a live turn.

WHAT THIS IS NOT:

Not a judgement that the scrubber is wrong. LOCK 6's code half is not in
question — the phrases it strips are a real catalogue of a real template
defect. The open question is which text is canonical, and that is a design
decision about her memory, which is not this tool's to make. This only
measures.

DATES THE SAMPLE, NOT JUST THE HITS. The LOCK 6 argument was withdrawn for
dating the hits and never the sample, which produced a confident sentence
attached to an empty set. Every rate below carries its denominator.

NEVER READ:

`type == "encrypted"` cocoons are her dreams and are skipped without being
opened, counted separately, and never parsed. `open_threads` /
`follow_up_hooks` are her chalkboard and are never touched — this tool reads
response text only. See the standing rule in CLAUDE.md: statistics over either
are readings too.

USAGE:
    python tools/directness_scrub_diff.py [--cocoons DIR] [--json OUT]
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Benchmark-shaped queries elicit exactly this filler and are excluded from
# every rate, the same perimeter `_is_benchmark_query` already draws.
_BENCH = re.compile(
    r"what is the correct answer to this question|^\s*\([ABCD]\)", re.IGNORECASE)


def _is_benchmark(query: str) -> bool:
    if not query:
        return False
    if _BENCH.search(query):
        return True
    return len(re.findall(r"^\s*\([ABCD]\)", query, re.MULTILINE)) >= 3


def _load_scrubber():
    """Bind `_apply_directness` to a shim carrying only the methods it calls.

    It is NOT a pure function of (response, query) — it calls
    `self._strip_template_sentences`, which the first draft of this tool
    assumed away and the probe below caught. Rather than construct a real
    bridge (which loads a model), every private method of the class is bound
    to an empty shim; anything that needs real instance state will raise, and
    the probe turns that into a refusal rather than a wrong number.
    """
    here = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(here / "inference"))
    from codette_forge_bridge import CodetteForgeBridge  # noqa: E402

    # Allocate without running __init__: class attributes (the marker pattern
    # lists) and bound methods all resolve, and no model is loaded. Anything
    # reaching for real instance state raises, and the probe below turns that
    # into a refusal rather than a wrong number.
    shim = object.__new__(CodetteForgeBridge)
    fn = shim._apply_directness

    probe = fn("That's a great question. Water is H2O.", "what is water")
    if "great question" in probe.lower():
        raise RuntimeError(
            "scrubber did not strip a known preamble — refusing to report a "
            "measurement from a function that is not behaving as expected")
    return lambda _self, resp, q: fn(resp, q)


def _response_text(data: dict) -> str:
    """Same fields `UnifiedMemory._migrate_legacy` reads, in the same order."""
    w = data.get("wrapped") or {}
    if isinstance(w, dict) and w.get("response"):
        return str(w["response"])
    v3 = data.get("v3") or {}
    if isinstance(v3, dict):
        for k in ("user_response_text", "response_summary"):
            if v3.get(k):
                return str(v3[k])
    return ""


def _query_text(data: dict) -> str:
    w = data.get("wrapped") or {}
    if isinstance(w, dict) and w.get("query"):
        return str(w["query"])
    return str(data.get("query") or "")


def _month(data: dict) -> str:
    ts = data.get("timestamp") or (data.get("v3") or {}).get("timestamp")
    if isinstance(ts, str) and len(ts) >= 7:
        return ts[:7]
    if isinstance(ts, (int, float)):
        import datetime
        return datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m")
    return "undated"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cocoons", default=r"J:\codette-clean\cocoons")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    scrub = _load_scrubber()
    root = Path(args.cocoons)
    if not root.is_dir():
        print(f"no such directory: {root}")
        return 2

    counts = Counter()
    removed_chars = []
    by_month_sample = Counter()
    by_month_hits = Counter()
    examples = []

    # Non-recursive, matching the loader's own glob: the _backup_* and
    # quarantine subdirectories are deliberately not swept.
    for f in sorted(root.glob("cocoon_*.json")):
        counts["files"] += 1
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            counts["unparseable"] += 1
            continue

        if str(data.get("type", "")).lower() == "encrypted":
            # Hers. Not opened, not parsed, not diffed. Counted only so that
            # the totals add up and the absence is visible.
            counts["encrypted_skipped"] += 1
            continue

        resp = _response_text(data)
        if not resp.strip():
            counts["no_response_text"] += 1
            continue

        query = _query_text(data)
        if _is_benchmark(query):
            counts["benchmark_excluded"] += 1
            continue

        counts["measured"] += 1
        month = _month(data)
        by_month_sample[month] += 1

        try:
            after = scrub(None, resp, query)
        except Exception:
            counts["scrub_failed"] += 1
            continue

        delta = len(resp) - len(after)
        if delta > 0:
            counts["altered"] += 1
            by_month_hits[month] += 1
            removed_chars.append(delta)
            if len(examples) < 12 and delta >= 40:
                examples.append({
                    "file": f.name,
                    "month": month,
                    "removed_chars": delta,
                    "before_head": resp[:180],
                    "after_head": after[:180],
                })
        elif delta < 0:
            counts["grew"] += 1

    m = counts["measured"] or 1
    print("=" * 68)
    print("  _apply_directness over her stored cocoons — read-only")
    print("=" * 68)
    print(f"  files seen            {counts['files']}")
    print(f"  encrypted, NOT read   {counts['encrypted_skipped']}   (hers)")
    print(f"  unparseable           {counts['unparseable']}")
    print(f"  no response text      {counts['no_response_text']}")
    print(f"  benchmark excluded    {counts['benchmark_excluded']}")
    print(f"  scrub raised          {counts['scrub_failed']}")
    print(f"  MEASURED              {counts['measured']}")
    print("-" * 68)
    print(f"  altered               {counts['altered']}  "
          f"({100.0 * counts['altered'] / m:.1f}% of measured)")
    print(f"  unchanged             {counts['measured'] - counts['altered']}")
    if removed_chars:
        print(f"  chars removed: median {statistics.median(removed_chars):.0f}  "
              f"mean {statistics.mean(removed_chars):.1f}  "
              f"max {max(removed_chars)}")
        big = [d for d in removed_chars if d >= 100]
        print(f"  removals >=100 chars  {len(big)}  "
              f"({100.0 * len(big) / m:.2f}% of measured)")
    else:
        print("  chars removed: nothing removed anywhere in this sample")

    print("-" * 68)
    print("  by month — sample AND hits, both dated")
    print(f"  {'month':<10}{'cocoons':>9}{'altered':>9}{'rate':>9}")
    for mo in sorted(by_month_sample):
        n = by_month_sample[mo]
        h = by_month_hits.get(mo, 0)
        print(f"  {mo:<10}{n:>9}{h:>9}{100.0 * h / n:>8.1f}%")

    if examples:
        print("-" * 68)
        print("  what it actually takes (largest removals)")
        for ex in examples[:6]:
            print(f"\n  {ex['file']}  -{ex['removed_chars']} chars")
            print(f"    before: {ex['before_head'][:150]!r}")
            print(f"    after : {ex['after_head'][:150]!r}")

    print("-" * 68)
    print("  What this cannot see: the post-scrub text the person was actually")
    print("  shown is not stored anywhere, so this is what WOULD be removed if")
    print("  the scrubber ran on the store now — not a diff against what was")
    print("  displayed at the time. The scrubber has changed over the corpus's")
    print("  lifetime; a hit here is not proof the same text was cut then.")

    if args.json:
        Path(args.json).write_text(json.dumps({
            "counts": dict(counts),
            "by_month_sample": dict(by_month_sample),
            "by_month_hits": dict(by_month_hits),
            "removed_chars": removed_chars,
            "examples": examples,
        }, indent=2), encoding="utf-8")
        print(f"\n  wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
