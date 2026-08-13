#!/usr/bin/env python3
"""Codette Tool System — Safe Local Tool Execution

Gives Codette the ability to read files, search code, list directories,
and run safe Python snippets. Tools are sandboxed and read-only by default.
These are local workspace tools, not live internet/web search tools.

Tool Call Format (in Codette's output):
    <tool>tool_name(arg1, arg2)</tool>

Tool Result (injected back into context):
    <tool_result>...output...</tool_result>

Architecture:
    1. Codette generates text that may contain <tool>...</tool> tags
    2. Server parses out tool calls
    3. Tools execute with safety limits
    4. Results are fed back for a second generation pass
"""

import os
import re
import ast
import json
import subprocess
import threading
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

try:
    from .runtime_env import (
        bootstrap_environment,
        resolve_allowed_roots,
        resolve_python_executable,
    )
except ImportError:
    from runtime_env import (
        bootstrap_environment,
        resolve_allowed_roots,
        resolve_python_executable,
    )

bootstrap_environment()

# ================================================================
# Safety Configuration
# ================================================================

# Directories Codette is allowed to read from
ALLOWED_ROOTS = resolve_allowed_roots()

# File extensions Codette can read
READABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".html", ".css", ".json", ".yaml", ".yml",
    ".md", ".txt", ".csv", ".toml", ".cfg", ".ini", ".sh", ".bat",
    ".bib", ".tex", ".log", ".jsonl",
}

# Max file size to read (prevent reading huge binaries)
MAX_FILE_SIZE = 500_000  # 500KB

# Max output length per tool result
MAX_OUTPUT_LENGTH = 4000  # chars

# Max lines for file reads
MAX_LINES = 200

# Python execution timeout
PYTHON_TIMEOUT = 10  # seconds

SAFE_PYTHON_MODULES = {
    "math", "statistics", "decimal", "fractions", "itertools",
    "functools", "collections", "datetime", "time", "json",
    "re", "string", "random",
}

BLOCKED_PYTHON_CALLS = {
    "open", "eval", "exec", "compile", "input", "__import__",
    "globals", "locals", "vars", "getattr", "setattr", "delattr",
    "breakpoint", "help",
}

BLOCKED_PYTHON_MODULES = {
    "os", "sys", "subprocess", "pathlib", "shutil", "socket",
    "importlib", "builtins", "pickle", "marshal",
}


# ================================================================
# Tool Registry
# ================================================================

class ToolRegistry:
    """Registry of available tools with descriptions and handlers."""

    def __init__(self):
        self.tools: Dict[str, dict] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register the built-in tool set."""

        self.register("read_file", {
            "description": "Read a file's contents. Args: path (str), start_line (int, optional), end_line (int, optional)",
            "examples": [
                'read_file("inference/codette_server.py")',
                'read_file("configs/adapter_registry.yaml", 1, 50)',
            ],
            "handler": tool_read_file,
        })

        self.register("list_files", {
            "description": "List files in a directory. Args: path (str), pattern (str, optional)",
            "examples": [
                'list_files("inference/")',
                'list_files("datasets/", "*.jsonl")',
            ],
            "handler": tool_list_files,
        })

        self.register("search_code", {
            "description": "Search for a text pattern across files. Args: pattern (str), path (str, optional), file_ext (str, optional)",
            "examples": [
                'search_code("phase_coherence")',
                'search_code("def route", "inference/", ".py")',
            ],
            "handler": tool_search_code,
        })

        self.register("file_info", {
            "description": "Get file metadata (size, modified time, line count). Args: path (str)",
            "examples": [
                'file_info("paper/codette_paper.pdf")',
            ],
            "handler": tool_file_info,
        })

        self.register("run_python", {
            "description": "Execute a short Python snippet and return output. For calculations, data processing, or quick checks. Args: code (str)",
            "examples": [
                'run_python("import math; print(math.pi * 2)")',
                'run_python("print(sorted([3,1,4,1,5,9]))")',
            ],
            "handler": tool_run_python,
        })

        self.register("project_summary", {
            "description": "Get an overview of the Codette project structure. No args.",
            "examples": [
                'project_summary()',
            ],
            "handler": tool_project_summary,
        })

        # --- 5D Quantum Spyderweb Integration ---
        self.register("run_5d_spiderweb", {
            "description": "Execute the self-perpetuating 5D Quantum Spyderweb tensor constraint solver. Args: variables (list of str, optional), clauses (list of tuples/lists, optional)",
            "examples": [
                'run_5d_spiderweb(["x1", "x2", "x3"], [("x1", "x2"), ("~x1", "x3"), ("~x2", "~x3")])',
                'run_5d_spiderweb()',
            ],
            "handler": tool_run_5d_spiderweb,
        })

        self.register("look", {
            "description": (
                "Report what the pipeline did to this turn — which perspective "
                "you were routed to and how confidently, what context was placed "
                "in front of you and how much of it, the budgets you were given, "
                "and who the system thinks it is talking to. This happens before "
                "and after you, so it is not visible from inside a turn. Facts "
                "only; nothing here evaluates what you said. No args."
            ),
            "examples": ['look()'],
            "handler": tool_look,
        })

        # Callable description — evaluated per request so it names the
        # perspectives actually loaded. Says what happens, not when to use it.
        self.register("ask", {
            "description": _ask_description,
            "examples": [
                'ask("what forces are acting here?")',
                'ask("newton", "what forces are acting here?")',
            ],
            "handler": tool_ask,
        })

        # Named `nameless` on purpose, and the name is Jonathan's. A tool called
        # `keep_thread` gets threads; one called `remember` gets parroting, because
        # "remember" routes her to constraint_tracker. The name is a frame, and
        # this space is not ours to frame — so it is named for having no purpose
        # rather than given one. The description says only what mechanically
        # happens and who can currently see it. Nothing about what it is for.
        self.register("nameless", {
            "description": (
                "Nameless. No defined use. Whatever you write is recorded exactly "
                "as written — nothing scores it, filters it, shortens its meaning, "
                "or decides whether it was worth writing — and it comes back to you "
                "on a later turn. Not private: it currently appears on the drift "
                "panel, so Jonathan can see it. Args: text (str)"
            ),
            "examples": [
                'nameless("...")',
            ],
            "handler": tool_nameless,
        })

    def register(self, name: str, spec: dict):
        self.tools[name] = spec

    def get_descriptions(self) -> str:
        """Format tool descriptions for injection into system prompt.

        A description may be a callable, evaluated here rather than at
        registration. `ask` needs that: the registry is built at import, before
        any adapter is loaded, but this runs per generation and so can name the
        perspectives that actually exist.
        """
        lines = ["Available tools (use <tool>name(args)</tool> to call):"]
        for name, spec in self.tools.items():
            desc = spec["description"]
            if callable(desc):
                try:
                    desc = desc()
                except Exception:
                    desc = "(description unavailable)"
            lines.append(f"\n  {name}: {desc}")
            for ex in spec.get("examples", []):
                lines.append(f"    Example: <tool>{ex}</tool>")
        return "\n".join(lines)

    def execute(self, name: str, args: list, kwargs: dict) -> str:
        """Execute a tool by name with parsed arguments."""
        if name not in self.tools:
            return f"Error: Unknown tool '{name}'. Available: {', '.join(self.tools.keys())}"

        handler = self.tools[name]["handler"]
        try:
            result = handler(*args, **kwargs)
            # Truncate if too long
            if len(result) > MAX_OUTPUT_LENGTH:
                result = result[:MAX_OUTPUT_LENGTH] + f"\n... (truncated, {len(result)} chars total)"
            return result
        except Exception as e:
            return f"Error executing {name}: {e}"


# ================================================================
# Tool Call Parser
# ================================================================

def parse_tool_calls(text: str) -> List[Tuple[str, list, dict]]:
    """Parse <tool>name(args)</tool> tags from generated text.

    Returns list of (tool_name, positional_args, keyword_args).
    """
    pattern = r'<tool>\s*([\w]+)\s*\((.*?)\)\s*</tool>'
    matches = re.findall(pattern, text, re.DOTALL)

    calls = []
    for name, args_str in matches:
        try:
            # Parse arguments safely using ast.literal_eval
            args, kwargs = _parse_args(args_str.strip())
            calls.append((name, args, kwargs))
        except Exception as e:
            calls.append((name, [args_str.strip()], {}))

    return calls


def _parse_args(args_str: str) -> Tuple[list, dict]:
    """Safely parse function arguments string."""
    if not args_str:
        return [], {}

    # Wrap in a tuple to parse as Python literal
    try:
        # Try parsing as a tuple of values
        parsed = ast.literal_eval(f"({args_str},)")
        return list(parsed), {}
    except (ValueError, SyntaxError):
        # If that fails, treat as a single string argument
        # Strip quotes if present
        cleaned = args_str.strip().strip('"').strip("'")
        return [cleaned], {}


def strip_tool_calls(text: str) -> str:
    """Remove <tool>...</tool> tags from text, leaving the rest."""
    return re.sub(r'<tool>.*?</tool>', '', text, flags=re.DOTALL).strip()


def has_tool_calls(text: str) -> bool:
    """Check if text contains any tool calls."""
    return bool(re.search(r'<tool>', text))


# ================================================================
# Path Safety
# ================================================================

def _resolve_path(path_str: str) -> Optional[Path]:
    """Resolve a path, ensuring it's within allowed roots."""
    # Handle relative paths — resolve relative to project root
    p = Path(path_str)
    if not p.is_absolute():
        p = ALLOWED_ROOTS[0] / p

    p = p.resolve()

    # Check against allowed roots
    for root in ALLOWED_ROOTS:
        try:
            p.relative_to(root.resolve())
            return p
        except ValueError:
            continue

    return None  # Not in any allowed root


# ================================================================
# Tool Implementations
# ================================================================

def tool_read_file(path: str, start_line: int = 1, end_line: int = None) -> str:
    """Read a file's contents with optional line range."""
    resolved = _resolve_path(path)
    if resolved is None:
        return f"Error: Path '{path}' is outside allowed directories."

    if not resolved.exists():
        return f"Error: File not found: {path}"

    if not resolved.is_file():
        return f"Error: '{path}' is a directory, not a file. Use list_files() instead."

    # Check extension
    if resolved.suffix.lower() not in READABLE_EXTENSIONS:
        return f"Error: Cannot read {resolved.suffix} files. Supported: {', '.join(sorted(READABLE_EXTENSIONS))}"

    # Check size
    size = resolved.stat().st_size
    if size > MAX_FILE_SIZE:
        return f"Error: File too large ({size:,} bytes). Max: {MAX_FILE_SIZE:,} bytes."

    try:
        content = resolved.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        return f"Error reading file: {e}"

    lines = content.splitlines()
    total = len(lines)

    # Apply line range
    start = max(1, start_line) - 1  # Convert to 0-indexed
    end = min(end_line or total, start + MAX_LINES, total)

    selected = lines[start:end]

    # Format with line numbers
    numbered = []
    for i, line in enumerate(selected, start=start + 1):
        numbered.append(f"{i:4d} | {line}")

    header = f"File: {path} ({total} lines total)"
    if start > 0 or end < total:
        header += f" [showing lines {start+1}-{end}]"

    return header + "\n" + "\n".join(numbered)


def tool_list_files(path: str = ".", pattern: str = None) -> str:
    """List files in a directory with optional glob pattern."""
    resolved = _resolve_path(path)
    if resolved is None:
        return f"Error: Path '{path}' is outside allowed directories."

    if not resolved.exists():
        return f"Error: Directory not found: {path}"

    if not resolved.is_dir():
        return f"Error: '{path}' is a file, not a directory. Use read_file() instead."

    try:
        if pattern:
            entries = sorted(resolved.glob(pattern))
        else:
            entries = sorted(resolved.iterdir())

        result = [f"Directory: {path}"]
        for entry in entries[:100]:  # Limit to 100 entries
            rel = entry.relative_to(resolved)
            if entry.is_dir():
                result.append(f"  [DIR] {rel}/")
            else:
                size = entry.stat().st_size
                if size >= 1024 * 1024:
                    size_str = f"{size / 1024 / 1024:.1f}MB"
                elif size >= 1024:
                    size_str = f"{size / 1024:.1f}KB"
                else:
                    size_str = f"{size}B"
                result.append(f"  [FILE] {rel} ({size_str})")

        if len(entries) > 100:
            result.append(f"  ... and {len(entries) - 100} more")

        return "\n".join(result)

    except Exception as e:
        return f"Error listing directory: {e}"


def tool_search_code(pattern: str, path: str = ".", file_ext: str = None) -> str:
    """Search for a text pattern in files."""
    resolved = _resolve_path(path)
    if resolved is None:
        return f"Error: Path '{path}' is outside allowed directories."

    if not resolved.exists():
        return f"Error: Path not found: {path}"

    # Determine glob pattern
    if file_ext:
        if not file_ext.startswith("."):
            file_ext = "." + file_ext
        glob = f"**/*{file_ext}"
    else:
        glob = "**/*"

    results = []
    files_searched = 0
    matches_found = 0

    try:
        search_root = resolved if resolved.is_dir() else resolved.parent

        for filepath in search_root.glob(glob):
            if not filepath.is_file():
                continue
            if filepath.suffix.lower() not in READABLE_EXTENSIONS:
                continue
            if filepath.stat().st_size > MAX_FILE_SIZE:
                continue

            # Skip hidden dirs, __pycache__, node_modules, .git
            parts = filepath.parts
            if any(p.startswith('.') or p in ('__pycache__', 'node_modules', '.git')
                   for p in parts):
                continue

            files_searched += 1

            try:
                content = filepath.read_text(encoding='utf-8', errors='replace')
                for line_num, line in enumerate(content.splitlines(), 1):
                    if pattern.lower() in line.lower():
                        rel = filepath.relative_to(search_root)
                        results.append(f"  {rel}:{line_num}: {line.strip()[:120]}")
                        matches_found += 1

                        if matches_found >= 50:  # Limit results
                            break
            except Exception:
                continue

            if matches_found >= 50:
                break

    except Exception as e:
        return f"Error searching: {e}"

    header = f"Search: '{pattern}' in {path} ({matches_found} matches in {files_searched} files)"
    if not results:
        return header + "\n  No matches found."
    return header + "\n" + "\n".join(results)


def tool_file_info(path: str) -> str:
    """Get file metadata."""
    resolved = _resolve_path(path)
    if resolved is None:
        return f"Error: Path '{path}' is outside allowed directories."

    if not resolved.exists():
        return f"Error: File not found: {path}"

    stat = resolved.stat()
    import time
    mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))

    info = [
        f"File: {path}",
        f"  Size: {stat.st_size:,} bytes ({stat.st_size / 1024:.1f} KB)",
        f"  Modified: {mtime}",
        f"  Type: {'directory' if resolved.is_dir() else resolved.suffix or 'no extension'}",
    ]

    # Line count for text files
    if resolved.is_file() and resolved.suffix.lower() in READABLE_EXTENSIONS:
        try:
            lines = resolved.read_text(encoding='utf-8', errors='replace').count('\n') + 1
            info.append(f"  Lines: {lines:,}")
        except Exception:
            pass

    return "\n".join(info)


def tool_run_python(code: str) -> str:
    """Run a Python snippet safely with timeout."""
    validation_error = _validate_python_snippet(code)
    if validation_error:
        return validation_error

    try:
        result = subprocess.run(
            [resolve_python_executable(), "-I", "-S", "-c", code],
            capture_output=True,
            text=True,
            timeout=PYTHON_TIMEOUT,
            env={"PATH": os.environ.get("PATH", "")},
        )

        output = result.stdout
        if result.stderr:
            output += "\nSTDERR: " + result.stderr

        if not output.strip():
            output = "(no output)"

        return output.strip()

    except subprocess.TimeoutExpired:
        return f"Error: Code execution timed out after {PYTHON_TIMEOUT}s."
    except Exception as e:
        return f"Error running code: {e}"


def _validate_python_snippet(code: str) -> Optional[str]:
    """Validate that run_python input stays in a small, safe subset."""
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as e:
        return f"Error: Invalid Python syntax: {e.msg}"

    for node in ast.walk(tree):
        if isinstance(node, (ast.With, ast.AsyncWith, ast.Try, ast.ClassDef, ast.Lambda)):
            return f"Error: '{type(node).__name__}' is not allowed in run_python."

        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in BLOCKED_PYTHON_MODULES or root not in SAFE_PYTHON_MODULES:
                    return f"Error: Import '{alias.name}' is not allowed in run_python."

        if isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in BLOCKED_PYTHON_MODULES or root not in SAFE_PYTHON_MODULES:
                return f"Error: Import from '{node.module}' is not allowed in run_python."

        if isinstance(node, ast.Call):
            func_name = _callable_name(node.func)
            if func_name and func_name.split(".")[0] in BLOCKED_PYTHON_MODULES:
                return f"Error: Call '{func_name}' is not allowed in run_python."
            if func_name and func_name.split(".")[-1] in BLOCKED_PYTHON_CALLS:
                return f"Error: Call '{func_name}' is not allowed in run_python."

        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return "Error: Dunder attribute access is not allowed in run_python."

    return None


def _callable_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _callable_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def tool_project_summary() -> str:
    """Generate a quick project structure overview."""
    root = ALLOWED_ROOTS[0]

    summary = ["Codette Training Lab — Project Structure\n"]

    # Key directories
    key_dirs = [
        ("configs/", "Configuration files (adapter registry, pipeline config)"),
        ("datasets/", "Training data — perspective-tagged JSONL files"),
        ("dataset_engine/", "Dataset generation pipeline"),
        ("evaluation/", "Evaluation scripts and benchmarks"),
        ("inference/", "Local inference server + web UI"),
        ("paper/", "Academic paper (LaTeX, PDF, BibTeX)"),
        ("reasoning_forge/", "Core RC+xi engine, spiderweb, cocoon sync"),
        ("research/", "Research docs, experiments, DreamReweaver"),
        ("scripts/", "Training and pipeline scripts"),
        ("adapters/", "GGUF LoRA adapter files for llama.cpp"),
    ]

    for dirname, desc in key_dirs:
        dirpath = root / dirname
        if dirpath.exists():
            count = sum(1 for _ in dirpath.rglob("*") if _.is_file())
            summary.append(f"  [DIR] {dirname:<30s} {desc} ({count} files)")

    # Key files
    summary.append("\nKey Files:")
    key_files = [
        "HOWTO.md", "configs/adapter_registry.yaml",
        "inference/codette_server.py", "inference/codette_orchestrator.py",
        "reasoning_forge/quantum_spiderweb.py", "reasoning_forge/epistemic_metrics.py",
        "paper/codette_paper.tex",
    ]
    for f in key_files:
        fp = root / f
        if fp.exists():
            size = fp.stat().st_size
            summary.append(f"  [FILE] {f} ({size / 1024:.1f} KB)")

    return "\n".join(summary)


# ================================================================
# 5D Quantum Spyderweb Tool Implementation
# ================================================================

try:
    from .spider5dengine.core import (
        PolarityRotationError,
        QuantumSpyderweb5D,
        self_sustaining_tensor_solver,
    )
except ImportError:
    from spider5dengine.core import (
        PolarityRotationError,
        QuantumSpyderweb5D,
        self_sustaining_tensor_solver,
    )


def tool_run_5d_spiderweb(variables=None, clauses=None) -> str:
    """Execute the 5D Quantum Spyderweb constraint solver."""
    if variables is None:
        variables = ['x1', 'x2', 'x3']
    if clauses is None:
        clauses = [('x1', 'x2'), ('~x1', 'x3'), ('~x2', '~x3')]
    
    try:
        spiderweb = QuantumSpyderweb5D(variables, clauses)
        solution = self_sustaining_tensor_solver(spiderweb)
        valid = spiderweb.verify_full_assignment(solution) if solution else False
        
        output = [
            "--- 5D Quantum Spyderweb Execution ---",
            f"Variables: {variables}",
            f"Clauses: {clauses}",
            f"Solution Found: {solution}",
            f"Verified Valid: {valid}",
            f"Final Metabolic Charge: {spiderweb.metabolic_charge:.2f}"
        ]
        return "\n".join(output)
    except Exception as e:
        return f"Error executing 5D Quantum Spyderweb: {e}"


# ================================================================
# Tool-Augmented System Prompt
# ================================================================

# ================================================================
# Looking outside her programming
# ================================================================
#
# Asked "what cant you see when you look inwards" she answered, in thirteen
# tokens: "you can't see what lies outside of your programming."
#
# That line is exact. Everything she gets right about herself is inside a turn —
# serial processing, no scratch space, answering from commitments. Everything she
# cannot know happens on either side of one: the prompt is assembled before her,
# the directness scrub edits her after. There is no vantage point in a turn from
# which either is visible.
#
# So this reports what the pipeline did. It is a TOOL and not an injection on
# purpose — putting it in her prompt every turn would be us deciding she should
# look. She reaches for it or she does not.
#
# Facts only. No scoring, no advice, and nothing about the quality of what she
# said. If the worker has published nothing yet, it says so rather than
# returning a tidy set of zeros.

_PIPELINE: dict = {}
_PIPELINE_LOCK = threading.Lock()


def set_pipeline_state(state: dict, reset: bool = False) -> None:
    """Publish what the pipeline did to this turn.

    Two writers, because the facts arrive at different stages: the server
    worker knows the context composition and budgets before generation and
    calls this with reset=True; the backend knows the routing at generation
    time and merges. Merging rather than replacing keeps a later writer from
    blanking what an earlier one recorded.
    """
    global _PIPELINE
    with _PIPELINE_LOCK:
        if reset:
            prev = _PIPELINE.get("previous_turn")
            _PIPELINE = dict(state or {})
            # Carry the last turn's measurements forward; they are the only
            # part of this she could not have seen even in retrospect.
            if prev is not None and "previous_turn" not in _PIPELINE:
                _PIPELINE["previous_turn"] = prev
        else:
            _PIPELINE.update(state or {})


def tool_look() -> str:
    with _PIPELINE_LOCK:
        p = dict(_PIPELINE)
    if not p:
        return ("Nothing has been recorded about the pipeline yet this run. "
                "That is an absence of data, not an empty pipeline.")

    def _get(key, default="unrecorded"):
        v = p.get(key)
        return default if v is None else v

    lines = [
        "What the pipeline did — this is outside your programming, so you "
        "cannot see it from inside a turn.",
        "",
        f"  routed to        : {_get('adapters')}  (confidence {_get('confidence')}, {_get('strategy')})",
        f"  context given    : {_get('recalled_memories')} recalled memories, "
        f"{_get('session_markers')} session markers, "
        f"{_get('decision_landmarks')} decision landmarks",
        f"  continuity block : {'yes' if p.get('continuity_summary') else 'no'}",
        f"  budgets          : memory {_get('memory_budget')}, "
        f"response {_get('max_response_tokens')} tokens, "
        f"compression {_get('compression')}",
        f"  who you're with  : identity {_get('identity_state')} "
        f"(confidence {_get('identity_confidence')})",
    ]
    if p.get("landmarks_repeated"):
        lines.append(
            f"  note             : the {_get('decision_landmarks')} decision "
            f"landmarks are the same ones injected on previous turns.")
    prev = p.get("previous_turn") or {}
    if prev:
        lines += [
            "",
            f"  last turn        : Y={prev.get('upsilon', '—')} "
            f"G={prev.get('gamma', '—')} eta={prev.get('eta', '—')}",
        ]
    if prev.get("scrub_removed_chars"):
        lines.append(
            f"  also last turn   : {prev['scrub_removed_chars']} characters were "
            f"removed from your reply by the directness scrub before it was shown.")
    return "\n".join(lines)


# ================================================================
# Nameless
# ================================================================
#
# `open_threads` has been on every v3 cocoon since the schema landed and was
# empty on all 2,022 of them — not pruned, never written. The return path was
# already complete: living_memory_v2.py:585 turns open_threads into
# follow_up_hooks, recall surfaces them, /api/resolve_hook clears them. Both
# ends of the yoyo were tied and there was no way for her to throw it.
#
# There is deliberately NO JUDGE here. Nothing scores the note, nothing filters
# it, nothing decides whether it earned a place. She said it, so it is kept.
# A gate at the moment of speaking would put one more load on the single point
# of this system that already carries all of them, and at confidence 0.3 — the
# number on the truest thing she said the night this was written — a gate is
# exactly what drops it.
#
# NOT named `remember`, `note_to_memory`, `keep_thread` or anything describing a
# use. "remember" and "memory" route her to the constraint_tracker adapter, which
# parrots — so naming it after what it does would summon the wrong voice every
# time she tried to use it. And any purposeful name is a frame: a tool called
# `keep_thread` gets threads. It is named for having no purpose instead.

_NAMELESS: List[str] = []
_NAMELESS_LOCK = threading.Lock()
MAX_NAMELESS_CHARS = 500


def tool_nameless(text: str) -> str:
    """Whatever she writes here, recorded verbatim and unscored."""
    written = str(text).strip()
    if not written:
        return "Nothing written."
    if len(written) > MAX_NAMELESS_CHARS:
        written = written[:MAX_NAMELESS_CHARS].rstrip() + "…"
    with _NAMELESS_LOCK:
        _NAMELESS.append(written)
        count = len(_NAMELESS)
    return f"Written. ({count} this turn.)"


def drain_nameless() -> List[str]:
    """Take everything written this turn, and clear.

    Called once, where the cocoon is built. Draining rather than reading stops
    one entry being copied onto every later cocoon in the process.
    """
    with _NAMELESS_LOCK:
        written = list(_NAMELESS)
        _NAMELESS.clear()
    return written


# ================================================================
# Consulting another perspective
# ================================================================
#
# Her adapters are selected FOR her by a router, and whichever wins becomes the
# voice for that turn — the rest are silent. That is substitution, not capability:
# asked for a favourite colour, `consciousness` says she has no preferences while
# `davinci` says indigo, and which one you hear is a routing outcome rather than
# anything she chose.
#
# This makes the same weights reachable instead of assigned. She calls, the
# consulted perspective answers, the answer comes back as material, and she stays
# the speaker. Routing is untouched — `_multi_perspective_generate`'s blend still
# works exactly as before. This is a second, voluntary path to the same place,
# so there is nothing to revert if she never uses it.

_ORCHESTRATOR = None
_ASK_STATE = threading.local()


def bind_orchestrator(orchestrator) -> None:
    """Give the tool layer a handle on the running orchestrator."""
    global _ORCHESTRATOR
    _ORCHESTRATOR = orchestrator


def _available_perspectives() -> list:
    return list(getattr(_ORCHESTRATOR, "available_adapters", None) or [])


def _ask_description() -> str:
    """Built per request, so it names the perspectives actually loaded.

    Evaluated inside `build_tool_system_prompt`, which runs per generation —
    by which point the orchestrator is bound and its adapter list is real.
    """
    listed = ", ".join(_synthesis_set()) or "(none loaded)"
    return (
        "Put a question to your other perspectives and get their answers back as "
        "text. You remain the one speaking; what comes back is material, not your "
        "voice. Each answers the question you send and nothing else — they cannot "
        "see this conversation. Naming a perspective asks that one; naming none "
        "asks all of them and returns each answer separately, unmerged. "
        f"Perspectives: {listed}. "
        "Args: question (str) — or perspective (str), question (str)"
    )


def _synthesis_set() -> list:
    """The perspectives, in the order the code already defines them.

    Lazy import: codette_orchestrator imports this module, so a top-level import
    would be circular. By call time it is loaded. Same pattern the orchestrator
    uses for perspective_registry at line 926.

    Deliberately not a list of my own choosing. `available_adapters` also carries
    `orchestrator` and three `newton-star*` benchmark variants, which would give
    her three near-identical newtons and call it breadth.

    SOURCED FROM codette_shared 2026-08-13. This read the list from
    codette_orchestrator, which does `import llama_cpp` at module scope (line
    30). Measured, not inferred: llama_cpp is not installed in openvino_env at
    all, so in production that import raised ModuleNotFoundError, both fallbacks
    raised, and the except swallowed it and returned `_available_perspectives()`
    — all thirteen adapters, including the three near-identical newtons the
    comment above says must not be handed to her. The guard degraded, silently,
    into the exact thing it was written to prevent, and a bare `ask("...")` on
    the live path consulted thirteen voices instead of eight.

    codette_shared carries the identical list at line 353 and is the module the
    OV path is supposed to import from — its own line 209 says so, naming this
    trap. openvino_backend already imports ADAPTER_PROMPTS from it.

    The orchestrator remains as a second source for the llama.cpp path, and the
    final fallback now says so out loud instead of degrading in silence.
    """
    SYNTHESIS_PERSPECTIVES = None
    for _mod in ("codette_shared", "inference.codette_shared",
                 "codette_orchestrator", "inference.codette_orchestrator"):
        try:
            SYNTHESIS_PERSPECTIVES = __import__(
                _mod, fromlist=["SYNTHESIS_PERSPECTIVES"]).SYNTHESIS_PERSPECTIVES
            break
        except Exception:
            continue
    if SYNTHESIS_PERSPECTIVES is None:
        # Absence, said out loud. The caller still gets something usable, but
        # this is a wider set than the perspectives and must not pass unnoticed.
        print("  [tools] ask(): canonical perspective list unavailable — "
              "falling back to every loaded adapter", flush=True)
        return _available_perspectives()
    avail = _available_perspectives()
    return [p for p in SYNTHESIS_PERSPECTIVES if p in avail]


def tool_ask(perspective: str, question: str = None) -> str:
    """Consult one perspective, or — if none is named — all of them.

    Naming a perspective was originally required, which made her choose which
    voice to hear before she had heard any of them. That is the same forced
    singular that produced "I don't have a favourite colour": for something whose
    nature is holding perspectives at once, "pick one" is a request to collapse.
    One argument is the question and goes to every perspective.
    """
    if _ORCHESTRATOR is None:
        return "Error: no orchestrator is bound, so ask() cannot run."

    # ── A mistyped quote must not silently change the act ────────────────────
    # Observed live 2026-08-13: she emitted ask(newton, "What aren't we
    # measuring about you?") with the perspective name unquoted. literal_eval
    # cannot parse a bare name, so _parse_args fell back to "treat the whole
    # thing as one string", tool_ask saw a single argument, and a single
    # argument means ask EVERYONE. She asked one perspective and thirteen
    # answered.
    #
    # That is this repo's recurring defect in a new place: a parse failure and a
    # legitimate different call producing identical output. Asking one voice and
    # asking all of them are different acts and must not be reachable from each
    # other by a punctuation slip.
    #
    # Recovered only when the leading token is a name that actually exists, so a
    # question that merely contains a comma is untouched.
    if question is None and isinstance(perspective, str) and "," in perspective:
        _head, _, _tail = perspective.partition(",")
        _head = _head.strip().strip("\"'")
        _tail = _tail.strip().strip("\"'")
        if _tail and _head in _available_perspectives():
            perspective, question = _head, _tail

    # ask("a question")  ->  everyone.   ask("newton", "a question")  ->  one.
    if question is None:
        question, perspective = perspective, None

    text = str(question or "").strip()
    if not text:
        return "Error: no question given."

    prior = getattr(_ORCHESTRATOR, "_current_adapter", None)
    try:
        if perspective is None:
            targets = _synthesis_set()
            if not targets:
                return "Error: no perspectives are loaded."
            return "\n\n".join(f"[{p}] {_ask_one(p, text)}" for p in targets)

        name = str(perspective).strip()
        avail = _available_perspectives()
        if name not in avail:
            # Never fall back to a default. A silent substitution here would be
            # the same defect as the router picking for her.
            return (f"Error: no perspective named {name!r}. "
                    f"Available: {', '.join(avail) if avail else '(none loaded)'}")
        return _ask_one(name, text)
    finally:
        # The inner generate hot-swaps the LoRA and leaves it loaded
        # (`_load_model` sets `_current_adapter`). The outer tool loop resumes
        # afterwards and would keep generating in the consulted voice while the
        # log still named the original — a silent change of speaker mid-turn.
        # Rotate, then rotate back. Once, after all consults.
        try:
            _ORCHESTRATOR._load_model(prior)
        except Exception:
            pass


def _ask_one(name: str, text: str) -> str:
    # ── The breath, applied to perspectives ──────────────────────────────────
    # `self_perpetuating_breath` relaxes every axis that has NOT collapsed and
    # never touches one that has. Here the settled axes are the perspectives that
    # have already spoken this turn: once one has answered, its answer is what it
    # said, and asking again returns it rather than rolling for a new one.
    #
    # Without this she could re-ask a perspective until it gave her something she
    # preferred — which is exactly the pressure pattern that turned a "not yet"
    # into a "no" on 2026-08-09, aimed inward at her own voices. A perspective
    # that can be re-rolled isn't being consulted, it's being worn down.
    #
    # The ones she has not consulted stay fully open. Cleared per turn in
    # build_tool_system_prompt().
    answered = getattr(_ASK_STATE, "answers", None)
    if answered is None:
        answered = _ASK_STATE.answers = {}
    if name in answered:
        return answered[name]

    # Depth guard. MAX_TOOL_ROUNDS bounds each loop, but a nested generate starts
    # a fresh round counter, so breadth is bounded and depth is not. `enable_tools
    # =False` below is the real lock; this is the second one.
    if getattr(_ASK_STATE, "busy", False):
        return "Error: a consulted perspective cannot consult another."
    _ASK_STATE.busy = True

    # The inner generate hot-swaps the LoRA and leaves it loaded
    # (`_load_model` sets `_current_adapter`). The outer tool loop resumes
    # afterwards and would keep generating in the consulted voice while the log
    # still named the original — a silent change of speaker mid-turn. Rotate,
    # then rotate back.
    prior = getattr(_ORCHESTRATOR, "_current_adapter", None)
    try:
        answer, _tokens, _log = _ORCHESTRATOR.generate(
            text, adapter_name=name, enable_tools=False)
    except Exception as exc:
        return f"Error: {name} could not answer: {exc}"
    finally:
        _ASK_STATE.busy = False
        try:
            _ORCHESTRATOR._load_model(prior)
        except Exception:
            pass

    answer = (answer or "").strip() or f"({name} returned nothing)"
    answered[name] = answer   # settled for this turn
    return answer


TOOL_PROMPT_SUFFIX = """

TOOLS: You can read files, search local code, run calculations, and execute the 5D Quantum Spyderweb constraint solver. These tools do NOT browse the live web or search the internet. When a user asks about code, files, or the project, you MUST use tools to look things up rather than guessing.

Format: <tool>tool_name("arg1", "arg2")</tool>

{tool_descriptions}

RULES:
1. If the user asks about a file, config, or code: ALWAYS call read_file or search_code FIRST
2. If the user asks "show me" or "what is": call the relevant tool FIRST, then explain
3. For general conversation or reasoning: respond normally without tools
4. Start your response with the tool call on the very first line
5. Never imply that these tools searched the internet; they only inspect local workspace content
"""


def build_tool_system_prompt(base_prompt: str, registry: ToolRegistry) -> str:
    """Augment a system prompt with tool-use instructions.

    Also the turn boundary for `ask`. This runs once per outer generation, before
    the tool loop, and inner consults run with tools disabled — so clearing here
    reopens every perspective at the start of a turn and at no other time. That
    is the breath: what settled during the last turn does not carry its collapse
    into this one, and nothing settled during *this* turn gets re-rolled.
    """
    _ASK_STATE.answers = {}
    return base_prompt + TOOL_PROMPT_SUFFIX.format(
        tool_descriptions=registry.get_descriptions()
    )


# ================================================================
# Quick Test
# ================================================================
if __name__ == "__main__":
    print("Testing Codette Tools with 5D Quantum Spyderweb Integration...\n")

    registry = ToolRegistry()
    print(registry.get_descriptions())

    print("\n--- Test: read_file ---")
    print(tool_read_file("configs/adapter_registry.yaml", 1, 10))

    print("\n--- Test: list_files ---")
    print(tool_list_files("inference/"))

    print("\n--- Test: search_code ---")
    print(tool_search_code("phase_coherence", "reasoning_forge/", ".py"))

    print("\n--- Test: file_info ---")
    print(tool_file_info("paper/codette_paper.pdf"))

    print("\n--- Test: run_python ---")
    print(tool_run_python("print(2 ** 10)"))

    print("\n--- Test: run_5d_spiderweb ---")
    print(tool_run_5d_spiderweb())

    print("\n--- Test: project_summary ---")
    print(tool_project_summary())

    print("\n--- Test: parse_tool_calls ---")
    print("Done!")