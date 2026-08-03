#!/usr/bin/env python3
"""
Split a Codette text backup bundle back into files, and verify each one.

    python3 restore.py CODETTE_SOURCE_BACKUP.txt              # list contents
    python3 restore.py CODETTE_SOURCE_BACKUP.txt --out DIR    # write files
    python3 restore.py CODETTE_SOURCE_BACKUP.txt --out DIR --verify

A backup nobody has restored is a guess, so --verify recomputes the SHA-256 of
every extracted file and compares it with the hash recorded in the banner.
Exit status is non-zero if any file fails verification.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys

BANNER = re.compile(
    r"^={78}\n=== FILE: (?P<path>.+?)\n=== SHA256: (?P<sha>[0-9a-f]{64})\n"
    r"=== BYTES: (?P<size>\d+)\n={78}\n",
    re.M,
)


def parse(text: str):
    """Yield (path, sha, declared_size, content) for each file in the bundle."""
    marks = list(BANNER.finditer(text))
    for i, m in enumerate(marks):
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        yield m.group("path"), m.group("sha"), int(m.group("size")), text[start:end]


def main() -> int:
    ap = argparse.ArgumentParser(description="restore a Codette text backup bundle")
    ap.add_argument("bundle")
    ap.add_argument("--out", help="directory to write files into")
    ap.add_argument("--verify", action="store_true", help="check SHA-256 of each file")
    args = ap.parse_args()

    try:
        # newline="" disables universal-newline translation: several recovered
        # files contain CRLF from their Word-document origin, and translating it
        # silently corrupts them.
        text = open(args.bundle, encoding="utf8", newline="").read()
    except OSError as exc:
        print(f"cannot read {args.bundle}: {exc}", file=sys.stderr)
        return 2

    entries = list(parse(text))
    if not entries:
        print("no file banners found — is this a Codette backup bundle?", file=sys.stderr)
        return 2

    written = ok = bad = 0
    for path, sha, size, content in entries:
        data = content.encode("utf8")
        # the trailing newline before the next banner belongs to the delimiter
        if data.endswith(b"\n") and len(data) == size + 1:
            data = data[:-1]

        if not args.out:
            print(f"  {size:>9}  {path}")
            continue

        target = os.path.normpath(os.path.join(args.out, path))
        # refuse to write outside the output directory
        if not os.path.abspath(target).startswith(os.path.abspath(args.out)):
            print(f"  REFUSED (path escape): {path}", file=sys.stderr)
            bad += 1
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as fh:
            fh.write(data)
        written += 1

        if args.verify:
            got = hashlib.sha256(data).hexdigest()
            if got == sha:
                ok += 1
            else:
                bad += 1
                print(f"  MISMATCH  {path}\n            expected {sha}\n            got      {got}",
                      file=sys.stderr)

    if not args.out:
        print(f"\n{len(entries)} files in bundle")
        return 0

    print(f"\nwrote {written} files to {args.out}")
    if args.verify:
        print(f"verified {ok} ok, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
