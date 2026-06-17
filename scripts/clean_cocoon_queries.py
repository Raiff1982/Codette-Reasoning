#!/usr/bin/env python3
"""One-shot cleanup: strip injected context blocks from stored cocoon queries.

Bug (fixed 2026-06-10 in codette_forge_bridge.py): cocoons stored the
ENRICHED query — including prepended [COHERENCE ANCHORS] / [SESSION
CONSTRAINTS] blocks and appended "--- # ACTIVE CONTINUITY SUMMARY" sections —
instead of the user's actual words.  Contaminated query fields pollute FTS5
recall and the cocoon synthesizer's pattern mining.

This script applies the same extraction logic the bridge now uses to all
existing cocoon JSON files, rewriting `wrapped.query` and `v3.query` in place.

Usage:
    python scripts/clean_cocoon_queries.py            # dry run — report only
    python scripts/clean_cocoon_queries.py --apply    # clean + write back

Originals of every modified file are copied to cocoons/_backup_query_cleanup/
before writing.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

COCOON_DIR = Path(__file__).parent.parent / "cocoons"
BACKUP_DIR = COCOON_DIR / "_backup_query_cleanup"

_BLOCK_RE = re.compile(
    r"^\[(?:COHERENCE ANCHORS|SESSION CONSTRAINTS)[^\]\n]*\]\s*\n"
    r"(?:- [^\n]*\n)*\n*",
)
_SENTINEL = "\n\n---\n"


def extract_user_query(query: str) -> str:
    """Mirror of CodetteForgeBridge._extract_primary_user_query."""
    if not query:
        return ""
    prev = None
    while prev != query:
        prev = query
        query = _BLOCK_RE.sub("", query, count=1)
    if _SENTINEL in query:
        query = query.split(_SENTINEL, 1)[0]
    return query.strip()


def is_contaminated(query: str) -> bool:
    return bool(query) and (
        query.lstrip().startswith("[COHERENCE ANCHORS")
        or query.lstrip().startswith("[SESSION CONSTRAINTS]")
        or _SENTINEL in query
    )


def clean_cocoon(data: dict) -> tuple[dict, list[str]]:
    """Clean all query fields in one cocoon. Returns (data, changed_fields)."""
    changed = []
    for path in (("wrapped", "query"), ("v3", "query")):
        section = data.get(path[0])
        if not isinstance(section, dict):
            continue
        original = section.get(path[1])
        if isinstance(original, str) and is_contaminated(original):
            cleaned = extract_user_query(original)
            if cleaned and cleaned != original:
                section[path[1]] = cleaned
                changed.append(".".join(path))
    return data, changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean contaminated cocoon query fields")
    parser.add_argument("--apply", action="store_true",
                        help="Write changes (default is dry-run report)")
    args = parser.parse_args()

    if not COCOON_DIR.is_dir():
        print(f"[ERROR] Cocoon dir not found: {COCOON_DIR}")
        return 1

    files = sorted(COCOON_DIR.glob("*.json"))
    print(f"Scanning {len(files)} cocoon JSON files in {COCOON_DIR} ...")

    scanned = contaminated = written = errors = 0
    samples: list[str] = []

    for fp in files:
        scanned += 1
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            errors += 1
            print(f"  [SKIP] {fp.name}: unreadable ({e})")
            continue

        data, changed = clean_cocoon(data)
        if not changed:
            continue

        contaminated += 1
        if len(samples) < 5:
            v3q = (data.get("v3") or {}).get("query", "")
            samples.append(f"  {fp.name}: {', '.join(changed)} -> {v3q[:60]!r}")

        if args.apply:
            try:
                BACKUP_DIR.mkdir(exist_ok=True)
                backup_path = BACKUP_DIR / fp.name
                if not backup_path.exists():
                    shutil.copy2(fp, backup_path)
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                written += 1
            except OSError as e:
                errors += 1
                print(f"  [ERROR] {fp.name}: write failed ({e})")

    print()
    print(f"Scanned:      {scanned}")
    print(f"Contaminated: {contaminated}")
    if samples:
        print("Samples (after cleaning):")
        for s in samples:
            print(s)
    if args.apply:
        print(f"Rewritten:    {written}  (originals in {BACKUP_DIR})")
    else:
        print("\nDry run only. Re-run with --apply to write changes.")
    if errors:
        print(f"Errors:       {errors}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
