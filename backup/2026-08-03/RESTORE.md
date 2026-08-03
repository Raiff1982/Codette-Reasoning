# Restoring from these text bundles

Three plain-text bundles holding every tracked text file in the repository as of
2026-08-03, plus `MANIFEST.sha256` listing the SHA-256 and byte count of each
original.

| Bundle | Files | Contents |
|---|---|---|
| `CODETTE_SOURCE_BACKUP.txt` | 605 | `.py`, `.cs`, `.ts`, `.tsx`, `.js`, `.sql`, `.ipynb`, config |
| `CODETTE_DOCS_BACKUP.txt` | 238 | `.md`, `.tex`, `.bib`, `.txt` |
| `CODETTE_MEMORY_BACKUP.txt` | 704 | cocoons, `data/`, `models/`, `training/`, all `.json`/`.jsonl` |

Binaries are **not** included — PDFs, PNGs, the `.wav`, the `Archive*.zip`
uploads and anything over 500 KB. Those exist only in git and in the original
archives.

## Why plain text

Text survives what binary formats do not. It opens in anything, it diffs, it
greps, and it can be pasted into a message or a document if that is the only
channel available. Given this project's history — source recovered out of
`.docx`, PDFs, `.txt` files and chat transcripts after a breach — a format that
degrades gracefully is worth more than a compact one.

## Format

Every file is preceded by a banner:

```
==============================================================================
=== FILE: reasoning_forge/nexis_signal_engine.py
=== SHA256: 3f1a...
=== BYTES: 26431
==============================================================================
```

The bytes that follow, up to the next banner, are the file's exact contents.
The hash lets you confirm a restored file matches the original rather than
assuming it does.

## Restore

```bash
python3 backup/2026-08-03/restore.py backup/2026-08-03/CODETTE_SOURCE_BACKUP.txt --out ./restored
```

Add `--verify` to check every restored file against its recorded SHA-256. Run
without `--out` to list what the bundle contains without writing anything.

## Verified

All 1547 files were restored and checked against their recorded SHA-256:
**1547 ok, 0 failed.** A backup nobody has restored is a guess.

## Two things that had to be got right

**CRLF.** Twenty-two files contain `\r\n`, inherited from their Word-document
origin. Python's default universal-newline handling silently rewrites those on
read, which corrupted them on the first attempt while leaving the byte count
identical — the kind of failure that passes a size check and fails a hash. Both
the bundle writer and `restore.py` use `newline=""` to disable that translation.

**Non-UTF-8.** Files are decoded as UTF-8 with replacement, so anything that was
not valid UTF-8 would restore with substitution characters and fail its hash.
`--verify` reports exactly which. None were found here.
