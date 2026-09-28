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
import hashlib
import io
import json
import os
import re
import sys
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


def walk_containers(root: Path, depth: int = 0, max_depth: int = 4):
    """Yield (origin, payload_bytes) for every leaf, unwrapping nested zips."""
    if depth > max_depth:
        return
    if root.is_file() and root.suffix.lower() == ".zip":
        try:
            zf = zipfile.ZipFile(root)
        except Exception:
            return
        for info in zf.infolist():
            if info.is_dir() or "__MACOSX" in info.filename:
                continue
            data = zf.read(info)
            name = f"{root.name}!{info.filename}"
            if info.filename.lower().endswith(".zip"):
                tmp = Path(os.environ.get("TMPDIR", "/tmp")) / f".ad_{abs(hash(name))}.zip"
                tmp.write_bytes(data)
                try:
                    yield from walk_containers(tmp, depth + 1, max_depth)
                finally:
                    tmp.unlink(missing_ok=True)
            else:
                yield name, data
        return
    if root.is_file():
        yield str(root), root.read_bytes()
        return
    for path in sorted(root.rglob("*")):
        if path.is_dir() or "node_modules" in path.parts:
            continue
        if path.suffix.lower() == ".zip":
            yield from walk_containers(path, depth + 1, max_depth)
        else:
            yield str(path), path.read_bytes()


def extract_modules(origin: str, data: bytes):
    """Yield (origin, source, needs_glyph_repair) for anything code-shaped."""
    low = origin.lower()
    if low.endswith(".py"):
        yield origin, data.decode("utf8", "ignore"), False
    elif low.endswith(".docx"):
        text = from_docx(data)
        if text and CODE_HINT.search(text):
            yield origin, text, False
    elif low.endswith(".pdf"):
        text = from_pdf(data)
        if text and CODE_HINT.search(text):
            yield origin, text, True          # PDFs need glyph repair
    elif low.endswith(".ipynb"):
        text = from_notebook(data)
        if text and CODE_HINT.search(text):
            yield origin, text, False
    elif low.endswith(".json"):
        for i, block in enumerate(from_chat_history(data)):
            yield f"{origin}#block{i}", block, False
    elif low.endswith(".md"):
        for i, block in enumerate(from_markdown(data)):
            if CODE_HINT.search(block):
                yield f"{origin}#fence{i}", block, False
    elif low.endswith((".txt", "")) and len(data) < 2_000_000:
        text = data.decode("utf8", "ignore")
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
