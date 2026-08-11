#!/usr/bin/env python3
"""
archive_diff — grep-nest for Codette archives.

Walks a tree or archive recursively, unwraps every container that can hide
source (zips inside zips, .docx, .pdf, .ipynb, chat-history .json, .txt, .md),
repairs the extraction damage those containers cause, then diffs what it finds
against this repository and against itself.

Why this exists
---------------
Source in this project was archived inside containers that survive a breach but
mangle text. File extensions do not indicate contents: Python has been found in
.docx, C# in .txt, a LaTeX paper in a file with no extension, and working
modules inside ChatGPT transcripts. Anything that filters on extension misses
most of it.

Usage
-----
    python tools/archive_diff.py <path> [--repo .] [--json out.json] [--extract DIR]

    <path>      archive or directory to scan
    --repo      repository to diff against (default: cwd)
    --json      write the full report as JSON
    --extract   write every recovered module to DIR

Verdicts
--------
    NEW         defines symbols this repository does not have
    IDENTICAL   byte-identical to a file already committed
    SUPERSEDED  repository version is a strict superset of this one
    DIVERGED    overlapping symbols, but each side has some the other lacks
                -- these are the ones needing a human decision

Exit status is 0 unless the scan itself failed.
"""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import io
import json
import os
import re
import sys
import tarfile
import zipfile
from collections import defaultdict
from pathlib import Path

# --------------------------------------------------------------------------
# Damage repair
#
# Each pattern below was observed in this project's archives. PDF text
# extraction substitutes glyphs for ligatures, Word documents lose escape
# sequences, and both wrap long lines at render width.
# --------------------------------------------------------------------------

LIGATURES = {
    "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl",
    "’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-",
    " ": " ",   # non-breaking space used where ASCII was meant
    "​": "",    # zero-width space
}

# PDF font subsets map these digits onto letter pairs. Applied only in letter
# context so real numbers (sha256, utf8, 1e-6) are never touched.
GLYPH_DIGITS = {"2": "ti", "7": "tt", "9": "tt"}

CONTINUES = re.compile(r"(?:[-+*/%,=<>|&]|\b(?:and|or|not|if|else|in|is))\s*$")
WRAP_ERRORS = ("unterminated", "unexpected EOF", "never closed", "unmatched",
               "invalid syntax")


def apply_ligatures(text: str) -> str:
    for bad, good in LIGATURES.items():
        text = text.replace(bad, good)
    return text


def apply_glyphs(text: str) -> str:
    """Undo PDF font-subset digit substitutions inside words only."""
    for digit, letters in GLYPH_DIGITS.items():
        text = re.sub(rf"(?<=[A-Za-z]){digit}(?=[A-Za-z])", letters, text)
        text = re.sub(rf"(?<![\w.]){digit}(?=[a-z]{{2,}})", letters, text)
    return text


def _bracket_depth(line: str) -> int:
    line = re.sub(r"#.*", "", line)
    return sum((c in "([{") - (c in ")]}") for c in line)


def rejoin_wrapped(text: str) -> str:
    """Rejoin lines split by a renderer's page width, not by the author."""
    out: list[str] = []
    buf, depth = "", 0
    for line in text.split("\n"):
        line = line.rstrip()
        if not line.strip():
            if buf:
                out.append(buf)
                buf, depth = "", 0
            out.append("")
            continue
        if buf:
            buf += " " + line.strip()
            depth += _bracket_depth(line)
        else:
            buf, depth = line, _bracket_depth(line)
        if depth <= 0 and not CONTINUES.search(re.sub(r"#.*", "", buf)):
            out.append(buf)
            buf, depth = "", 0
    if buf:
        out.append(buf)
    return "\n".join(out)


def repair(text: str, glyphs: bool = False) -> tuple[str, str | None]:
    """Return (source, error). Error is None when the result parses."""
    text = apply_ligatures(text)
    if "\t" in text:
        text = text.replace("\t", " ")     # tabs standing in for spaces
    if glyphs:
        text = apply_glyphs(text)
    text = "".join(c for c in text if c.isprintable() or c in "\n\t")

    if _parses(text):
        return text, None

    # Word documents turn \n escapes inside f-strings into real newlines.
    lines = text.split("\n")
    for _ in range(600):
        err = _syntax_error(lines)
        if err is None:
            return "\n".join(lines), None
        msg, lineno = err
        i = lineno - 1
        if "unterminated" in msg and i + 1 < len(lines):
            lines[i] = lines[i] + "\\n" + lines.pop(i + 1).lstrip()
            continue
        break

    joined = rejoin_wrapped(text)
    if _parses(joined):
        return joined, None

    # Prose is sometimes appended after the last line of source.
    lines = joined.split("\n")
    for i in range(len(lines), 0, -1):
        if _parses("\n".join(lines[:i])):
            if i < len(lines):
                return "\n".join(lines[:i]).rstrip(), None
            break

    err = _syntax_error(joined.split("\n"))
    return joined, f"line {err[1]}: {err[0]}" if err else "unparseable"


def _parses(src: str) -> bool:
    try:
        ast.parse(src)
        return True
    except SyntaxError:
        return False


def _syntax_error(lines: list[str]):
    try:
        ast.parse("\n".join(lines))
        return None
    except SyntaxError as exc:
        return (exc.msg or ""), (exc.lineno or 1)


# --------------------------------------------------------------------------
# Container unwrapping — the "nest" half of grep-nest
# --------------------------------------------------------------------------

CODE_HINT = re.compile(
    r"(?:^|\n)\s*(?:import |from \w+ import|def \w+|class \w+|using System|public class)",
    re.M)

# Vendored third-party code. Without this, scanning an archive that happens to
# contain a virtualenv reports pip, setuptools and urllib3 as "recovered source".
# Measured 2026-08-10: OneDrive_2 reported NEW=466, of which the overwhelming
# majority was `Nexus/aegis_env/Lib/site-packages`. Filtering leaves 98 payloads.
VENDORED = re.compile(
    r"(?:^|[/\\])(?:site-packages|dist-packages|node_modules|_vendor|"
    r"vendor|\.git|__pycache__|\.tox|\.mypy_cache|\.pytest_cache)(?:[/\\]|$)"
    r"|\.dist-info[/\\]|\.egg-info[/\\]"
    r"|(?:^|[/\\])(?:aegis_env|venv|\.venv|env)[/\\](?:Lib|lib|Scripts|bin)[/\\]",
    re.I)


def sniff(data: bytes) -> str:
    """Identify a payload by its MAGIC BYTES, never by its name.

    CLAUDE.md's first rule is that file extensions do not indicate contents.
    This function is how that rule is actually enforced: Python has been found
    in .docx, a LaTeX paper in an extensionless file, and a whole ASP.NET app in
    `new 3.txt`. Anything that dispatches on the name misses all of it.
    """
    if data[:4] in (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"):
        return "zip"
    if data[:5] == b"%PDF-":
        return "pdf"
    if data[:16] == b"SQLite format 3\x00":
        return "sqlite"
    if data[:2] == b"\x1f\x8b":
        return "gzip"
    if data[257:262] == b"ustar":
        return "tar"
    return "plain"


def zip_is_office_document(data: bytes) -> bool:
    """True for .docx/.xlsx/.pptx, which are zips but are NOT archives to descend.

    Without this check, magic-byte detection would walk into a Word file and
    yield `word/document.xml` as a leaf, losing the text extraction entirely.
    """
    try:
        names = set(zipfile.ZipFile(io.BytesIO(data)).namelist())
    except Exception:
        return False
    return bool(names & {"word/document.xml", "xl/workbook.xml", "ppt/presentation.xml"})


def from_docx(data: bytes) -> str | None:
    try:
        xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml")
    except Exception:
        return None
    text = re.sub(r"</w:p>", "\n", xml.decode("utf8", "ignore"))
    text = re.sub(r"<[^>]+>", "", text)
    return (text.replace("&lt;", "<").replace("&gt;", ">")
                .replace("&amp;", "&"))


def from_pdf(data: bytes) -> str | None:
    try:
        import pypdf
    except ImportError:
        return None
    try:
        reader = pypdf.PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        return None


def from_notebook(data: bytes) -> str | None:
    try:
        doc = json.loads(data.decode("utf8", "ignore"))
    except Exception:
        return None
    cells = doc.get("cells")
    if cells is None:
        return None
    return "\n\n".join("".join(c.get("source", []))
                       for c in cells if c.get("cell_type") == "code")


def from_chat_history(data: bytes):
    """Yield fenced code blocks out of a chat transcript export."""
    try:
        doc = json.loads(data.decode("utf8", "ignore"))
    except Exception:
        return
    def walk(node):
        if isinstance(node, str):
            yield node
        elif isinstance(node, dict):
            for v in node.values():
                yield from walk(v)
        elif isinstance(node, list):
            for v in node:
                yield from walk(v)
    for text in walk(doc):
        for m in re.finditer(r"```(?:python)?\n(.*?)```", text, re.S):
            block = m.group(1)
            if len(block) >= 200 and CODE_HINT.search(block):
                yield block


def from_markdown(data: bytes):
    text = data.decode("utf8", "ignore")
    for m in re.finditer(r"```python\n(.*?)(?:```|\Z)", text, re.S):
        yield m.group(1)


# 4 was too shallow and it was luck that it held: the 2026-08-10 OneDrive
# archives nest to exactly 4 (zip -> zip -> .tar.gz -> tar -> file), so the old
# limit truncated at precisely the last useful level. 12 with a cycle-free
# byte walk costs nothing and stops silently losing the deepest payloads.
MAX_CONTAINER_DEPTH = 12

# A single member big enough to be a disk image is not source; skip rather than
# hold it in memory.
MAX_MEMBER_BYTES = 64 * 1024 * 1024


def _walk_bytes(origin: str, data: bytes, depth: int):
    """Recursively unwrap one payload, dispatching on CONTENT, not on name."""
    if depth > MAX_CONTAINER_DEPTH:
        return

    kind = sniff(data)

    # The size cap applies to LEAVES only. Applying it to containers rejected
    # the 324 MB top-level archive at depth 0 and returned nothing at all.
    if kind == "plain" and len(data) > MAX_MEMBER_BYTES:
        return

    if kind == "zip" and not zip_is_office_document(data):
        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
        except Exception:
            return
        for info in zf.infolist():
            if info.is_dir() or "__MACOSX" in info.filename:
                continue
            if VENDORED.search(info.filename):
                continue
            try:
                member = zf.read(info)
            except Exception:
                continue
            yield from _walk_bytes(f"{origin}!{info.filename}", member, depth + 1)
        return

    if kind == "gzip":
        try:
            yield from _walk_bytes(f"{origin}!<gunzip>", gzip.decompress(data), depth + 1)
        except Exception:
            pass
        return

    if kind == "tar":
        try:
            tf = tarfile.open(fileobj=io.BytesIO(data))
            for member in tf.getmembers():
                if not member.isfile() or VENDORED.search(member.name):
                    continue
                fh = tf.extractfile(member)
                if fh is not None:
                    yield from _walk_bytes(f"{origin}!{member.name}", fh.read(), depth + 1)
        except Exception:
            pass
        return

    yield origin, data


def walk_containers(root: Path, depth: int = 0, max_depth: int = MAX_CONTAINER_DEPTH):
    """Yield (origin, payload_bytes) for every leaf, unwrapping nested containers.

    Containers are identified by magic bytes, so a zip named `.py`, a gzip named
    `.txt` and an extensionless tarball are all opened. Office documents are
    deliberately NOT descended into — they are zips, but their text is extracted
    whole by `from_docx`.

    Vendored third-party trees are skipped; see VENDORED.
    """
    if root.is_file():
        yield from _walk_bytes(root.name, root.read_bytes(), depth)
        return
    for path in sorted(root.rglob("*")):
        if path.is_dir() or VENDORED.search(str(path)):
            continue
        try:
            payload = path.read_bytes()
        except Exception:
            continue
        yield from _walk_bytes(str(path), payload, depth)


def _looks_like_notebook(obj) -> bool:
    return isinstance(obj, dict) and "cells" in obj and "nbformat" in obj


def extract_modules(origin: str, data: bytes):
    """Yield (origin, source, needs_glyph_repair) for anything code-shaped.

    Dispatch is by CONTENT. The extension is consulted only as a tie-break for
    formats that are plain text either way (.md fences vs a bare .txt), never to
    decide whether something is a PDF, a document or a notebook.

    Rewritten 2026-08-10. The previous version branched on
    `origin.lower().endswith(".docx")` / `".pdf"` and so was blind to exactly the
    thing this repository exists to handle — 43 .docx files that were Python,
    `new 3.txt` that was an ASP.NET application, a LaTeX paper in a file called
    `Codette` with no extension at all.
    """
    kind = sniff(data)

    if kind == "pdf":
        text = from_pdf(data)
        if text and CODE_HINT.search(text):
            yield origin, text, True          # PDFs need glyph repair
        return

    if kind == "zip":                          # only office docs reach here
        text = from_docx(data)
        if text and CODE_HINT.search(text):
            yield origin, text, False
        return

    if kind in ("sqlite", "gzip", "tar"):
        return                                 # binary, or already unwrapped

    if len(data) > 8_000_000:
        return

    try:
        text = data.decode("utf8")
    except UnicodeDecodeError:
        text = data.decode("utf8", "ignore")
        if not text.strip():
            return

    # JSON-shaped: notebook or chat history. Decided by parsing, not by suffix,
    # so `history_2025-*.json` and a notebook saved without .ipynb both work.
    stripped = text.lstrip()
    if stripped[:1] in "{[":
        try:
            obj = json.loads(text)
        except Exception:
            obj = None
        if obj is not None:
            if _looks_like_notebook(obj):
                nb = from_notebook(data)
                if nb and CODE_HINT.search(nb):
                    yield origin, nb, False
                return
            found = False
            for i, block in enumerate(from_chat_history(data)):
                found = True
                yield f"{origin}#block{i}", block, False
            if found:
                return

    # Fenced markdown, wherever it lives — .md, .markdown, or a bare .txt that
    # happens to contain fences (QuantumCosmicMulticore.md was prose + code).
    if "```" in text:
        emitted = False
        for i, block in enumerate(from_markdown(data)):
            if CODE_HINT.search(block):
                emitted = True
                yield f"{origin}#fence{i}", block, False
        if emitted:
            return

    # Anything else that is code-shaped, regardless of what it is called.
    if CODE_HINT.search(text):
        yield origin, text, False


# --------------------------------------------------------------------------
# Diffing against the repository
# --------------------------------------------------------------------------

# Names too common to identify a module. Matching on these produces false
# counterparts -- every class has __init__, so it is evidence of nothing.
GENERIC = {"main", "run", "setup", "test", "process", "save", "load", "close",
           "reset", "update", "start", "stop", "get", "set", "add", "remove"}


def symbols(src: str) -> set[str]:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    return {n.name for n in ast.walk(tree)
            if isinstance(n, (ast.ClassDef, ast.FunctionDef))
            and not n.name.startswith("__")
            and n.name not in GENERIC}


def classes(src: str) -> set[str]:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    return {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}


def git_provenance(repo: Path, rel: str) -> dict | None:
    """
    Commits as compass.

    Line count says which file is bigger; it does not say which is current.
    Git history does. For a repository file this returns when it was first
    introduced, when it last changed, and how many commits have touched it --
    which is the evidence for calling one revision canonical and the rest
    historical.
    """
    import subprocess

    def run(*args):
        try:
            out = subprocess.run(["git", "-C", str(repo), *args],
                                 capture_output=True, text=True, timeout=15)
            return out.stdout.strip() if out.returncode == 0 else ""
        except Exception:
            return ""

    last = run("log", "-1", "--format=%cs%x1f%h%x1f%s", "--", rel)
    first = run("log", "--diff-filter=A", "--format=%cs%x1f%h%x1f%s", "--", rel)
    if not last:
        return None
    touches = run("rev-list", "--count", "HEAD", "--", rel)
    l = last.split("\x1f")
    f = (first.splitlines()[-1].split("\x1f") if first else l)
    return {
        "added": f[0], "added_commit": f[1], "added_subject": f[2][:60],
        "last": l[0], "last_commit": l[1], "last_subject": l[2][:60],
        "commits": int(touches) if touches.isdigit() else 0,
    }


def index_repo(repo: Path):
    by_symbol: dict[str, list[str]] = defaultdict(list)
    hashes: set[str] = set()
    per_file: dict[str, set[str]] = {}
    for path in repo.rglob("*.py"):
        if ".git" in path.parts:
            continue
        try:
            src = path.read_text("utf8", errors="ignore")
        except Exception:
            continue
        hashes.add(hashlib.md5(src.encode()).hexdigest())
        syms = symbols(src)
        rel = str(path.relative_to(repo))
        per_file[rel] = syms
        for s in syms:
            by_symbol[s].append(rel)
    return by_symbol, hashes, per_file


def verdict(src: str, by_symbol, hashes, per_file):
    if hashlib.md5(src.encode()).hexdigest() in hashes:
        return "IDENTICAL", None, set()
    mine = symbols(src)
    if not mine:
        return "NO-SYMBOLS", None, set()
    counterparts = {f for s in mine for f in by_symbol.get(s, [])}
    if not counterparts:
        return "NEW", None, mine
    best, best_overlap = None, -1
    for f in counterparts:
        overlap = len(mine & per_file[f])
        if overlap > best_overlap:
            best, best_overlap = f, overlap
    theirs = per_file[best]
    only_mine = mine - theirs
    if not only_mine:
        return "SUPERSEDED", best, set()
    if mine & theirs:
        return "DIVERGED", best, only_mine
    return "NEW", None, only_mine


def main() -> int:
    ap = argparse.ArgumentParser(description="grep-nest recovery diff for Codette archives")
    ap.add_argument("path")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--json")
    ap.add_argument("--extract")
    args = ap.parse_args()

    root, repo = Path(args.path), Path(args.repo).resolve()
    if not root.exists():
        print(f"no such path: {root}", file=sys.stderr)
        return 2

    by_symbol, hashes, per_file = index_repo(repo)
    out_dir = Path(args.extract) if args.extract else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    results, damaged, families = [], [], defaultdict(list)

    for origin, data in walk_containers(root):
        for name, raw, glyphs in extract_modules(origin, data):
            src, err = repair(raw, glyphs=glyphs)
            digest = hashlib.md5(src.encode()).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            if err:
                damaged.append({"origin": name, "error": err})
                continue
            state, counterpart, novel = verdict(src, by_symbol, hashes, per_file)
            lines = src.count("\n") + 1
            entry = {"origin": name, "verdict": state, "lines": lines,
                     "counterpart": counterpart, "new_symbols": sorted(novel)}
            if counterpart:
                entry["git"] = git_provenance(repo, counterpart)
            results.append(entry)
            key = frozenset(classes(src))
            if key:
                families[key].append((lines, name))
            if out_dir and state in ("NEW", "DIVERGED"):
                safe = re.sub(r"[^\w.-]", "_", name)[-120:]
                (out_dir / f"{safe}.py").write_text(src)

    order = {"NEW": 0, "DIVERGED": 1, "SUPERSEDED": 2, "IDENTICAL": 3, "NO-SYMBOLS": 4}
    results.sort(key=lambda r: (order.get(r["verdict"], 9), -r["lines"]))

    counts = defaultdict(int)
    for r in results:
        counts[r["verdict"]] += 1

    print(f"scanned {root}  ({len(seen)} unique payloads)\n")
    for state in ("NEW", "DIVERGED", "SUPERSEDED", "IDENTICAL", "NO-SYMBOLS"):
        rows = [r for r in results if r["verdict"] == state]
        if not rows:
            continue
        print(f"=== {state}  ({len(rows)})")
        for r in rows[:40]:
            extra = f" -> {r['counterpart']}" if r["counterpart"] else ""
            syms = ", ".join(r["new_symbols"][:5])
            print(f"   {r['lines']:>5}ln  {r['origin'][-64:]:<66}{extra}")
            if syms:
                print(f"          new: {syms}")
            prov = r.get("git")
            if prov:
                print(f"          repo side: added {prov['added']} ({prov['added_commit']}), "
                      f"last {prov['last']} ({prov['last_commit']}), "
                      f"{prov['commits']} commit(s)")
                if state == "DIVERGED":
                    print(f"          last change: {prov['last_subject']}")
        if len(rows) > 40:
            print(f"   ... {len(rows) - 40} more")
        print()

    # Version families: same class set, different sizes -> pick a canonical.
    multi = {k: v for k, v in families.items() if len(v) > 1}
    if multi:
        print("=== VERSION FAMILIES (same classes, differing size)")
        print("    Size proposes a candidate; the commit record decides. Where a")
        print("    family member is already committed, its git history is shown --")
        print("    that is the compass, not the line count.\n")
        for key, members in multi.items():
            members.sort(reverse=True)
            print(f"   {', '.join(sorted(key))[:70]}")
            # is any member of this family already tracked in the repo?
            committed = [f for f, syms in per_file.items() if key <= syms]
            for i, (lines, name) in enumerate(members):
                mark = "candidate" if i == 0 else "         "
                print(f"      {mark} {lines:>5}ln  {name[-62:]}")
            for f in committed:
                prov = git_provenance(repo, f)
                if prov:
                    print(f"      COMMITTED       {f}")
                    print(f"                      added {prov['added']} ({prov['added_commit']}) "
                          f"· last {prov['last']} ({prov['last_commit']}) "
                          f"· {prov['commits']} commit(s)")
                    print(f"                      {prov['last_subject']}")
            if not committed:
                print("      (no committed counterpart -- decide from the archive alone)")
            print()

    if damaged:
        print(f"=== UNREPAIRABLE  ({len(damaged)})")
        for d in damaged[:15]:
            print(f"   {d['origin'][-66:]}\n          {d['error']}")
        print()

    print("summary: " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if multi:
        print(f"         {len(multi)} version families need a canonical decision")

    if args.json:
        Path(args.json).write_text(json.dumps(
            {"results": results, "damaged": damaged,
             "families": [{"classes": sorted(k),
                           "members": [{"lines": l, "origin": n} for l, n in sorted(v, reverse=True)]}
                          for k, v in multi.items()]}, indent=2))
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
