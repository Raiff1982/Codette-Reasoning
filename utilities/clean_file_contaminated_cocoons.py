#!/usr/bin/env python3
"""One-off: strip attached-file prefixes from stored cocoon queries.

The dream cycle (July 17 2026) caught cocoons whose `wrapped.query` held
uploaded file content instead of the user's actual message — the same
disease class as the July 5 enriched-query incident, but for file uploads.
The storage path is now fixed (extract_primary_user_query strips file
blocks); this cleans the historical records.

Conservative: only rewrites a cocoon when extraction yields a NON-EMPTY
query that differs from the stored one. File-only uploads (no accompanying
message → empty extraction) are left untouched and reported, not blanked.
Backs up every modified file to cocoons/_backup_file_cleanup/ first.

Usage:
    python utilities/clean_file_contaminated_cocoons.py --dry-run
    python utilities/clean_file_contaminated_cocoons.py
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
COCOON_DIR = _REPO / "cocoons"
BACKUP_DIR = COCOON_DIR / "_backup_file_cleanup"

_FILE_END_MARKER = "--- End of File ---"


def clean_query(q: str) -> str:
    # Anchor on the LAST end marker — an uploaded file can itself contain the
    # marker strings (e.g. a cocoon JSON), so non-greedy peeling breaks.
    if q.lstrip().startswith("--- Attached File:") and _FILE_END_MARKER in q:
        q = q[q.rindex(_FILE_END_MARKER) + len(_FILE_END_MARKER):]
    sentinel = "\n\n---\n"
    if sentinel in q:
        q = q.split(sentinel, 1)[0]
    return q.strip()


def is_contaminated(q: str) -> bool:
    return isinstance(q, str) and (
        "--- Attached File:" in q or "--- End of File ---" in q)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cleaned = skipped_empty = 0
    if not args.dry_run:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    for f in COCOON_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        w = d.get("wrapped")
        if not isinstance(w, dict):
            continue
        q = w.get("query")
        if not is_contaminated(q):
            continue

        new_q = clean_query(q)
        if not new_q:
            skipped_empty += 1
            print(f"  SKIP (file-only, no user msg): {f.name}")
            continue
        if new_q == q:
            continue

        print(f"  CLEAN {f.name}: {new_q[:70]!r}")
        if not args.dry_run:
            shutil.copy2(f, BACKUP_DIR / f.name)
            w["query"] = new_q
            # also fix v3 mirror if it duplicated the contaminated query
            v3 = d.get("v3")
            if isinstance(v3, dict) and is_contaminated(v3.get("query", "")):
                v3["query"] = new_q
            f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        cleaned += 1

    print(f"\n{'DRY-RUN: would clean' if args.dry_run else 'Cleaned'} {cleaned} cocoon(s); "
          f"{skipped_empty} file-only skipped.")
    if not args.dry_run and cleaned:
        print(f"Backups: {BACKUP_DIR}")


if __name__ == "__main__":
    main()
