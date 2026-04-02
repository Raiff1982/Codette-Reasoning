#!/usr/bin/env python3
"""Codette Tool System — Safe Local Tool Execution

Gives Codette the ability to read files, search code, list directories,
and run safe Python snippets. Tools are sandboxed and read-only by default.

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

    def register(self, name: str, spec: dict):
        self.tools[name] = spec

    def get_descriptions(self) -> str:
        """Format tool descriptions for injection into system prompt."""
        lines = ["Available tools (use <tool>name(args)</tool> to call):"]
        for name, spec in self.tools.items():
            lines.append(f"\n  {name}: {spec['description']}")
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
# Tool-Augmented System Prompt
# ================================================================

TOOL_PROMPT_SUFFIX = """

TOOLS: You can read files, search code, and run calculations. When a user asks about code, files, or the project, you MUST use tools to look things up rather than guessing.

Format: <tool>tool_name("arg1", "arg2")</tool>

{tool_descriptions}

RULES:
1. If the user asks about a file, config, or code: ALWAYS call read_file or search_code FIRST
2. If the user asks "show me" or "what is": call the relevant tool FIRST, then explain
3. For general conversation or reasoning: respond normally without tools
4. Start your response with the tool call on the very first line
"""


def build_tool_system_prompt(base_prompt: str, registry: ToolRegistry) -> str:
    """Augment a system prompt with tool-use instructions."""
    return base_prompt + TOOL_PROMPT_SUFFIX.format(
        tool_descriptions=registry.get_descriptions()
    )


# ================================================================
# Quick Test
# ================================================================
if __name__ == "__main__":
    print("Testing Codette Tools...\n")

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

    print("\n--- Test: project_summary ---")
    print(tool_project_summary())

    print("\n--- Test: parse_tool_calls ---")
    test = 'Let me check that. <tool>read_file("configs/adapter_registry.yaml", 1, 20)</tool> And also <tool>search_code("AEGIS")</tool>'
    calls = parse_tool_calls(test)
    for name, args, kwargs in calls:
        print(f"  Call: {name}({args})")

    print("\nDone!")
