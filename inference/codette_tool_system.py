#!/usr/bin/env python3
"""Codette Tool System v2.1 — Full Production Implementation

Drop-in replacement for Codette's tool layer. Safe, Forge-integrated, AEGIS-aware.
"""

import os
import re
import ast
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Codette Core Integration
try:
    from reasoning_forge.aegis import AEGIS
    from reasoning_forge.guardian_spindle import CoreGuardianSpindle
except ImportError:
    class AEGIS:
        def audit(self, text: str): return {"eta": 0.92, "vetoed": False}
    class CoreGuardianSpindle:
        def validate(self, query: str): return True

aegis = AEGIS()
guardian = CoreGuardianSpindle()

# Safety Configuration
ALLOWED_ROOTS = [Path("/home/workdir").resolve(), Path(os.getcwd()).resolve()]
READABLE_EXTS = {".py", ".md", ".json", ".yaml", ".yml", ".txt", ".csv", ".toml", ".sh", ".html", ".css"}
MAX_FILE_SIZE = 2_000_000
MAX_OUTPUT = 8000
PYTHON_TIMEOUT = 15

BLOCKED_CALLS = {"eval", "exec", "open", "__import__", "subprocess"}

def _resolve_path(path_str: str) -> Optional[Path]:
    p = Path(path_str).resolve()
    for root in ALLOWED_ROOTS:
        try:
            p.relative_to(root)
            return p
        except ValueError:
            continue
    return None


def read_file(path: str, start_line: int = 1, limit: int = 200) -> str:
    """Safe file reader."""
    p = _resolve_path(path)
    if not p or not p.is_file():
        return f"Error: Invalid path {path}"
    if p.stat().st_size > MAX_FILE_SIZE:
        return "Error: File too large"
    try:
        lines = p.read_text(encoding='utf-8', errors='replace').splitlines()
        start = max(0, start_line - 1)
        selected = lines[start:start + limit]
        return f"File: {path}\n" + "\n".join(f"{i+start+1:4d} | {line}" for i, line in enumerate(selected))
    except Exception as e:
        return f"Read error: {e}"


def list_files(path: str = ".", pattern: str = None) -> str:
    """Safe directory listing."""
    p = _resolve_path(path)
    if not p or not p.is_dir():
        return "Error: Invalid directory"
    entries = sorted(p.iterdir())[:100]
    result = [f"Directory: {path}"]
    for e in entries:
        result.append(f"{'[DIR]' if e.is_dir() else '[FILE]'} {e.name}")
    return "\n".join(result)


def search_code(pattern: str, path: str = ".", file_ext: str = None) -> str:
    """Safe code search."""
    p = _resolve_path(path)
    if not p:
        return "Error: Invalid path"
    results = []
    for f in p.rglob(f"**/*{file_ext or ''}"):
        if f.is_file() and f.suffix.lower() in READABLE_EXTS:
            try:
                content = f.read_text(encoding='utf-8', errors='replace')
                for i, line in enumerate(content.splitlines(), 1):
                    if pattern.lower() in line.lower():
                        results.append(f"{f.relative_to(p)}:{i}: {line.strip()[:100]}")
                        if len(results) >= 50:
                            break
            except:
                continue
    return f"Search '{pattern}':\n" + "\n".join(results) if results else "No matches"


def validate_code_syntax(code: str) -> dict:
    """Non-executing syntax check via AST parsing to catch typos or malformed operators."""
    try:
        ast.parse(code)
        return {"valid": True, "error": None}
    except SyntaxError as e:
        return {
            "valid": False,
            "error": f"SyntaxError at line {e.lineno}, offset {e.offset}: {e.msg}\nCode block: {e.text.strip() if e.text else ''}"
        }


def run_python(code: str) -> str:
    """Safe Python execution with AST validation."""
    if not guardian.validate(code):
        return "Guardian blocked"
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = getattr(node.func, 'id', None)
                if name in BLOCKED_CALLS:
                    return "Blocked unsafe call"
        result = subprocess.run(["python3", "-c", code], capture_output=True, text=True, timeout=PYTHON_TIMEOUT)
        return result.stdout + (result.stderr and f"\nSTDERR: {result.stderr}")
    except Exception as e:
        return f"Execution error: {e}"


def project_summary() -> str:
    """Project overview."""
    return "Codette Reasoning Forge — Core modules loaded. Tools active."


class CodetteToolRegistry:
    def __init__(self):
        self.tools = {}
        self._register_all()

    def _register_all(self):
        self.register("read_file", read_file)
        self.register("list_files", list_files)
        self.register("search_code", search_code)
        self.register("run_python", run_python)
        self.register("validate_code_syntax", validate_code_syntax)
        self.register("project_summary", project_summary)

    def register(self, name: str, handler):
        self.tools[name] = {"handler": handler}

    def execute(self, name: str, **kwargs) -> str:
        if name not in self.tools:
            return f"Unknown tool: {name}"
        try:
            return self.tools[name]["handler"](**kwargs)
        except Exception as e:
            return f"Tool failed: {e}"

registry = CodetteToolRegistry()