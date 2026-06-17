#!/usr/bin/env python3
"""Reality Layer — grounds adapter reasoning in actual artifact facts.

Problem this fixes: when asked "what would you improve in X.py?", adapters
were free-associating off the words in the question ("improve" -> talk about
self-improvement, emotional intelligence) instead of inspecting the file.

This module extracts verifiable facts from a referenced source file (line
count, classes, functions, rough complexity) BEFORE adapters reason, and
provides a cheap post-hoc check for whether a response actually engaged with
those facts. Python-only AST analysis; falls back to line counts for other
text files. No network access, read-only, reuses the same path allowlist as
codette_tools.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

try:
    from .codette_tools import _resolve_path, ALLOWED_ROOTS, READABLE_EXTENSIONS, MAX_FILE_SIZE
except ImportError:
    from codette_tools import _resolve_path, ALLOWED_ROOTS, READABLE_EXTENSIONS, MAX_FILE_SIZE

_SKIP_DIR_PARTS = {".git", "__pycache__", "node_modules", ".venv", "venv"}


@dataclass
class ArtifactFacts:
    path: str
    line_count: int
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    branch_count: int = 0  # rough cyclomatic complexity proxy
    longest_function: Optional[str] = None
    longest_function_lines: int = 0

    def names(self) -> List[str]:
        """All identifiers a grounded response should plausibly reference."""
        return self.classes + self.functions


# Matches things like "universal_reasoning.py", "inference/codette_server.py"
_FILE_REF_RE = re.compile(
    r"\b[\w./\\-]+\.(?:py|js|ts|tsx|jsx|json|yaml|yml|md)\b"
)


def find_referenced_file(query: str) -> Optional[Path]:
    """Look for a file path mentioned in the query and resolve it safely.

    Handles both relative paths ("inference/foo.py") and bare filenames
    ("foo.py") by falling back to a recursive search under the allowed
    roots when a direct join against the project root doesn't exist.
    """
    for match in _FILE_REF_RE.finditer(query):
        candidate = match.group(0)
        resolved = _resolve_path(candidate)
        if resolved is not None and resolved.is_file():
            return resolved

        basename = Path(candidate).name
        for root in ALLOWED_ROOTS:
            try:
                for hit in root.rglob(basename):
                    if any(part in _SKIP_DIR_PARTS for part in hit.parts):
                        continue
                    if hit.is_file():
                        return hit
            except Exception:
                continue
    return None


def extract_artifact_facts(query: str) -> Optional[ArtifactFacts]:
    """If the query references a real local file, extract grounded facts."""
    path = find_referenced_file(query)
    if path is None:
        return None

    if path.suffix.lower() not in READABLE_EXTENSIONS:
        return None
    if path.stat().st_size > MAX_FILE_SIZE:
        return None

    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    line_count = source.count("\n") + 1
    facts = ArtifactFacts(path=str(path.name), line_count=line_count)

    if path.suffix.lower() != ".py":
        return facts  # line count only for non-Python files

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return facts  # unparseable — still return what we know

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            facts.classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            facts.functions.append(node.name)
            fn_lines = (node.end_lineno or node.lineno) - node.lineno
            if fn_lines > facts.longest_function_lines:
                facts.longest_function_lines = fn_lines
                facts.longest_function = node.name
        elif isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.BoolOp, ast.ExceptHandler)):
            facts.branch_count += 1
        elif isinstance(node, ast.Import):
            facts.imports.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            facts.imports.append(node.module)

    return facts


def format_facts_block(facts: ArtifactFacts) -> str:
    """Render facts as a block to inject alongside the query."""
    lines = [
        f"[VERIFIED FACTS about {facts.path} — extracted directly from the file, not assumptions]",
        f"- {facts.line_count} lines total",
    ]
    if facts.classes:
        lines.append(f"- Classes: {', '.join(facts.classes[:20])}")
    if facts.functions:
        lines.append(f"- Functions: {', '.join(facts.functions[:30])}")
    if facts.longest_function:
        lines.append(
            f"- Longest function: {facts.longest_function} "
            f"({facts.longest_function_lines} lines)"
        )
    if facts.branch_count:
        lines.append(f"- Branch/control-flow points: {facts.branch_count} (rough complexity proxy)")
    if facts.imports:
        uniq = sorted(set(facts.imports))[:15]
        lines.append(f"- Imports: {', '.join(uniq)}")
    lines.append(
        "Ground your analysis in these facts. Reference specific class/function "
        "names above when making claims about the code. Do not invent structure "
        "that isn't listed here."
    )
    return "\n".join(lines)


def grounding_score(response_text: str, facts: ArtifactFacts) -> float:
    """Fraction of known identifiers from facts that the response actually names.

    A score of 0.0 with non-trivial facts available means the response never
    engaged with the real artifact — a strong signal it's narrative, not analysis.
    """
    names = facts.names()
    if not names:
        return 1.0  # nothing to ground against (e.g. non-Python file) — don't penalize
    text_lower = response_text.lower()
    hits = sum(1 for name in names if name.lower() in text_lower)
    return hits / len(names)
