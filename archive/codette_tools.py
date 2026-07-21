#!/usr/bin/env python3
"""Codette Tool System — Safe Local Tool Execution & High-Performance Graph Solvers

Gives Codette the ability to read files, search code, list directories,
run safe Python snippets, and execute heavy-duty combinatorial solvers.

Added: Native, zero-allocation Cycle Double Cover DFS backtracking engine.
"""

import os
import re
import ast
import json
import time
import subprocess
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import networkx as nx

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

# Safely initialize environment if utility exists
try:
    bootstrap_environment()
except Exception:
    pass

# ================================================================
# Safety Configuration
# ================================================================
try:
    ALLOWED_ROOTS = resolve_allowed_roots()
except Exception:
    ALLOWED_ROOTS = [Path(os.getcwd()).resolve()]

READABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".html", ".css", ".json", ".yaml", ".yml",
    ".md", ".txt", ".csv", ".toml", ".cfg", ".ini", ".sh", ".bat",
    ".bib", ".tex", ".log", ".jsonl",
}
MAX_FILE_SIZE = 500_000  # 500KB
MAX_OUTPUT_LENGTH = 4000  # chars
MAX_LINES = 200
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
# Cycle Double Cover High-Performance Backend Functions
# ================================================================

def path_to_edge_set(path):
    edges = []
    for i in range(len(path)):
        u, v = path[i], path[(i + 1) % len(path)]
        edges.append(tuple(sorted((u, v))))
    return frozenset(edges)

def expand_cycle_pool(basis, target_count=400):
    pool_edges = set()
    pure_pool = []
    
    for path in basis:
        eset = path_to_edge_set(path)
        if len(eset) >= 3 and eset not in pool_edges:
            pool_edges.add(eset)
            pure_pool.append(path)

    basis_edge_sets = list(pool_edges)
    for i in range(len(basis_edge_sets)):
        if len(pure_pool) >= target_count:
            break
        for j in range(i + 1, len(basis_edge_sets)):
            if len(pure_pool) >= target_count:
                break
                
            e1, e2 = basis_edge_sets[i], basis_edge_sets[j]
            xor_edges = e1.symmetric_difference(e2)
            
            if len(xor_edges) >= 3 and xor_edges not in pool_edges:
                adj = {}
                for u, v in xor_edges:
                    adj.setdefault(u, []).append(v)
                    adj.setdefault(v, []).append(u)
                
                if any(len(neighbors) % 2 != 0 for neighbors in adj.values()):
                    continue
                
                try:
                    start_node = next(iter(adj))
                    path = [start_node]
                    curr = adj[start_node][0]
                    prev = start_node
                    
                    while curr != start_node:
                        path.append(curr)
                        next_nodes = [n for n in adj[curr] if n != prev]
                        if not next_nodes:
                            raise ValueError
                        prev, curr = curr, next_nodes[0]
                    
                    if len(path) >= 3:
                        pool_edges.add(xor_edges)
                        pure_pool.append(path)
                except (StopIteration, ValueError, IndexError):
                    continue
                        
    return pure_pool[:target_count]

def build_cycle_matrix(G, cycles):
    edges = list(G.edges())
    edge_to_idx = {tuple(sorted(e)): i for i, e in enumerate(edges)}
    
    matrix = np.zeros((len(cycles), len(edges)), dtype=np.int8)
    for c_idx, cycle in enumerate(cycles):
        for i in range(len(cycle)):
            u, v = cycle[i], cycle[(i + 1) % len(cycle)]
            e = tuple(sorted((u, v)))
            if e in edge_to_idx:
                matrix[c_idx, edge_to_idx[e]] = 1
    return matrix, edges

def find_fundamental_cycles(G):
    tree = nx.minimum_spanning_tree(G)
    non_tree_edges = [e for e in G.edges() if not tree.has_edge(*e)]
    
    basis = []
    for u, v in non_tree_edges:
        path = nx.shortest_path(tree, source=u, target=v)
        basis.append(path)
    return basis

# ================================================================
# Tool Implementations
# ================================================================

def tool_solve_cycle_double_cover(n_vertices: int = 40, target_cycles: int = 231, max_states: int = 50000000) -> str:
    """Generates a random cubic graph, extracts cycle spaces, and runs the zero-allocation DFS solver."""
    try:
        start_init = time.time()
        G = nx.random_regular_graph(d=3, n=n_vertices, seed=42)
        base_basis = find_fundamental_cycles(G)
        robust_pool = expand_cycle_pool(base_basis, target_count=target_cycles)
        matrix, edge_list = build_cycle_matrix(G, robust_pool)
        
        num_cycles = matrix.shape[0]
        num_edges = len(edge_list)
        
        output_log = [
            f"ℹ️ Initialized {n_vertices}-vertex random cubic graph skeleton.",
            f"🧠 Extracting fundamental cycle framework...",
            f"ℹ️ Mapped {num_edges} edges into {num_cycles} robust, non-recursive cycles.",
            f"🧠 Launching active DFS pruning engine over iterative structure..."
        ]
        
        # Zero-allocation local mutable states
        coverage = np.zeros(num_edges, dtype=np.int8)
        chosen = []
        stack = [(0, 0)]
        states_evaluated = 0
        
        solver_start = time.time()
        solution = None
        
        while stack:
            c_idx, step = stack.pop()
            
            # SUCCESS CHECK: Must happen before boundary check to catch solutions on boundaries
            if np.all(coverage == 2):
                solution = list(chosen)
                break
                
            if c_idx >= num_cycles:
                continue
                
            if step == 0:
                states_evaluated += 1
                
                # Check execution ceiling limits to keep the Web UI stable
                if states_evaluated >= max_states:
                    elapsed = time.time() - solver_start
                    rate = states_evaluated / elapsed / 1000000 if elapsed > 0 else 0
                    output_log.append(
                        f"🛑 Search suspended at safety threshold of {states_evaluated:,} states. "
                        f"Active Path Depth: {len(chosen)} | Speed: {rate:.2f}M states/sec"
                    )
                    break
                
                # Report milestones in the logged summary
                if states_evaluated % 15000000 == 0:
                    elapsed = time.time() - solver_start
                    rate = states_evaluated / elapsed / 1000000 if elapsed > 0 else 0
                    output_log.append(
                        f"🔍 [Telemetry] Evaluated {states_evaluated:,} states... "
                        f"Active Path Depth: {len(chosen)} | Speed: {rate:.2f}M states/sec"
                    )
                
                cycle_vector = matrix[c_idx]
                if np.max(coverage + cycle_vector) <= 2:
                    coverage += cycle_vector
                    chosen.append(c_idx)
                    
                    stack.append((c_idx, 2))
                    stack.append((c_idx + 1, 0))
                else:
                    stack.append((c_idx + 1, 0))

            elif step == 2:
                coverage -= matrix[c_idx]
                chosen.pop()
                stack.append((c_idx + 1, 0))
                
        total_time = time.time() - start_init
        
        if solution is not None:
            output_log.append(f"\n🎉 [Success] Valid Cycle Double Cover isolated at state {states_evaluated:,}!")
            output_log.append(f"Solution Cycle Indices: {solution}")
        elif states_evaluated < max_states:
            output_log.append(f"\n🏁 Search space fully exhausted at {states_evaluated:,} states. No valid double cover within this basis.")
            
        output_log.append(f"⏱️ Overall execution completed in {total_time:.2f} seconds.")
        return "\n".join(output_log)
        
    except Exception as e:
        return f"Error executing Cycle Double Cover Solver: {e}\n{traceback.format_exc()}"

def tool_read_file(path: str, start_line: int = 1, end_line: int = None) -> str:
    resolved = _resolve_path(path)
    if resolved is None:
        return f"Error: Path '{path}' is outside allowed directories."
    if not resolved.exists():
        return f"Error: File not found: {path}"
    if not resolved.is_file():
        return f"Error: '{path}' is a directory, not a file. Use list_files() instead."
    if resolved.suffix.lower() not in READABLE_EXTENSIONS:
        return f"Error: Cannot read {resolved.suffix} files. Supported: {', '.join(sorted(READABLE_EXTENSIONS))}"
    size = resolved.stat().st_size
    if size > MAX_FILE_SIZE:
        return f"Error: File too large ({size:,} bytes). Max: {MAX_FILE_SIZE:,} bytes."

    try:
        content = resolved.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        return f"Error reading file: {e}"

    lines = content.splitlines()
    total = len(lines)
    start = max(1, start_line) - 1
    end = min(end_line or total, start + MAX_LINES, total)
    selected = lines[start:end]

    numbered = [f"{i:4d} | {line}" for i, line in enumerate(selected, start=start + 1)]
    header = f"File: {path} ({total} lines total)"
    if start > 0 or end < total:
        header += f" [showing lines {start+1}-{end}]"
    return header + "\n" + "\n".join(numbered)

def tool_list_files(path: str = ".", pattern: str = None) -> str:
    resolved = _resolve_path(path)
    if resolved is None:
        return f"Error: Path '{path}' is outside allowed directories."
    if not resolved.exists():
        return f"Error: Directory not found: {path}"
    if not resolved.is_dir():
        return f"Error: '{path}' is a file, not a directory. Use read_file() instead."

    try:
        entries = sorted(resolved.glob(pattern)) if pattern else sorted(resolved.iterdir())
        result = [f"Directory: {path}"]
        for entry in entries[:100]:
            rel = entry.relative_to(resolved)
            if entry.is_dir():
                result.append(f"  [DIR] {rel}/")
            else:
                size = entry.stat().st_size
                size_str = f"{size / 1024 / 1024:.1f}MB" if size >= 1024*1024 else (f"{size / 1024:.1f}KB" if size >= 1024 else f"{size}B")
                result.append(f"  [FILE] {rel} ({size_str})")
        if len(entries) > 100:
            result.append(f"  ... and {len(entries) - 100} more")
        return "\n".join(result)
    except Exception as e:
        return f"Error listing directory: {e}"

def tool_search_code(pattern: str, path: str = ".", file_ext: str = None) -> str:
    resolved = _resolve_path(path)
    if resolved is None:
        return f"Error: Path '{path}' is outside allowed directories."
    if not resolved.exists():
        return f"Error: Path not found: {path}"

    glob_pattern = f"**/*{file_ext if file_ext.startswith('.') else '.' + file_ext}" if file_ext else "**/*"
    results = []
    files_searched = 0
    matches_found = 0

    try:
        search_root = resolved if resolved.is_dir() else resolved.parent
        for filepath in search_root.glob(glob_pattern):
            if not filepath.is_file() or filepath.suffix.lower() not in READABLE_EXTENSIONS or filepath.stat().st_size > MAX_FILE_SIZE:
                continue
            if any(p.startswith('.') or p in ('__pycache__', 'node_modules', '.git') for p in filepath.parts):
                continue

            files_searched += 1
            try:
                content = filepath.read_text(encoding='utf-8', errors='replace')
                for line_num, line in enumerate(content.splitlines(), 1):
                    if pattern.lower() in line.lower():
                        rel = filepath.relative_to(search_root)
                        results.append(f"  {rel}:{line_num}: {line.strip()[:120]}")
                        matches_found += 1
                        if matches_found >= 50:
                            break
            except Exception:
                continue
            if matches_found >= 50:
                break
    except Exception as e:
        return f"Error searching: {e}"

    header = f"Search: '{pattern}' in {path} ({matches_found} matches in {files_searched} files)"
    return header + "\n  No matches found." if not results else header + "\n" + "\n".join(results)

def tool_file_info(path: str) -> str:
    resolved = _resolve_path(path)
    if resolved is None:
        return f"Error: Path '{path}' is outside allowed directories."
    if not resolved.exists():
        return f"Error: File not found: {path}"

    stat = resolved.stat()
    mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
    info = [
        f"File: {path}",
        f"  Size: {stat.st_size:,} bytes ({stat.st_size / 1024:.1f} KB)",
        f"  Modified: {mtime}",
        f"  Type: {'directory' if resolved.is_dir() else resolved.suffix or 'no extension'}",
    ]
    if resolved.is_file() and resolved.suffix.lower() in READABLE_EXTENSIONS:
        try:
            lines = resolved.read_text(encoding='utf-8', errors='replace').count('\n') + 1
            info.append(f"  Lines: {lines:,}")
        except Exception:
            pass
    return "\n".join(info)

def tool_run_python(code: str) -> str:
    validation_error = _validate_python_snippet(code)
    if validation_error:
        return validation_error
    try:
        executable = resolve_python_executable() if 'resolve_python_executable' in globals() else "python3"
        result = subprocess.run(
            [executable, "-I", "-S", "-c", code],
            capture_output=True,
            text=True,
            timeout=PYTHON_TIMEOUT,
            env={"PATH": os.environ.get("PATH", "")},
        )
        output = result.stdout
        if result.stderr:
            output += "\nSTDERR: " + result.stderr
        return output.strip() if output.strip() else "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: Code execution timed out after {PYTHON_TIMEOUT}s."
    except Exception as e:
        return f"Error running code: {e}"

def _validate_python_snippet(code: str) -> Optional[str]:
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
    root = ALLOWED_ROOTS[0]
    summary = ["Codette Training Lab — Project Structure\n"]
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
# Tool Registry Setup
# ================================================================

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, dict] = {}
        self._register_defaults()

    def _register_defaults(self):
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
            "description": "Execute a short Python snippet and return output. Args: code (str)",
            "examples": [
                'run_python("import math; print(math.pi * 2)")',
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

        self.register("solve_cycle_double_cover", {
            "description": "Generates a random cubic graph and executes the high-performance zero-allocation DFS cycle double cover solver. Args: n_vertices (int, default 40), target_cycles (int, default 231), max_states (int, default 50000000)",
            "examples": [
                'solve_cycle_double_cover(40, 231, 50000000)',
                'solve_cycle_double_cover(30, 150, 10000000)',
            ],
            "handler": tool_solve_cycle_double_cover,
        })

    def register(self, name: str, spec: dict):
        self.tools[name] = spec

    def get_descriptions(self) -> str:
        lines = ["Available tools (use <tool>name(args)</tool> to call):"]
        for name, spec in self.tools.items():
            lines.append(f"\n  {name}: {spec['description']}")
            for ex in spec.get("examples", []):
                lines.append(f"    Example: <tool>{ex}</tool>")
        return "\n".join(lines)

    def execute(self, name: str, args: list, kwargs: dict) -> str:
        if name not in self.tools:
            return f"Error: Unknown tool '{name}'. Available: {', '.join(self.tools.keys())}"
        handler = self.tools[name]["handler"]
        try:
            result = handler(*args, **kwargs)
            if len(result) > MAX_OUTPUT_LENGTH:
                result = result[:MAX_OUTPUT_LENGTH] + f"\n... (truncated, {len(result)} chars total)"
            return result
        except Exception as e:
            return f"Error executing {name}: {e}"

def parse_tool_calls(text: str) -> List[Tuple[str, list, dict]]:
    pattern = r'<tool>\s*([\w]+)\s*\((.*?)\)\s*</tool>'
    matches = re.findall(pattern, text, re.DOTALL)
    calls = []
    for name, args_str in matches:
        try:
            args, kwargs = _parse_args(args_str.strip())
            calls.append((name, args, kwargs))
        except Exception:
            calls.append((name, [args_str.strip()], {}))
    return calls

def _parse_args(args_str: str) -> Tuple[list, dict]:
    if not args_str:
        return [], {}
    try:
        parsed = ast.literal_eval(f"({args_str},)")
        return list(parsed), {}
    except (ValueError, SyntaxError):
        cleaned = args_str.strip().strip('"').strip("'")
        return [cleaned], {}

def strip_tool_calls(text: str) -> str:
    return re.sub(r'<tool>.*?</tool>', '', text, flags=re.DOTALL).strip()

def has_tool_calls(text: str) -> bool:
    return bool(re.search(r'<tool>', text))

def _resolve_path(path_str: str) -> Optional[Path]:
    p = Path(path_str)
    if not p.is_absolute():
        p = ALLOWED_ROOTS[0] / p
    p = p.resolve()
    for root in ALLOWED_ROOTS:
        try:
            p.relative_to(root.resolve())
            return p
        except ValueError:
            continue
    return None

# ================================================================
# Tool-Augmented System Prompt
# ================================================================
TOOL_PROMPT_SUFFIX = """

TOOLS: You can read files, search local code, run calculations, and evaluate heavy cycle basis coverage math. These tools do NOT browse the live web or search the internet. When a user asks about code, files, or cycle double cover problems, you MUST use tools to look things up or execute mathematical models rather than guessing.

Format: <tool>tool_name("arg1", "arg2")</tool>

{tool_descriptions}

RULES:
1. If the user asks to solve a Cycle Double Cover instance or test a basis, immediately invoke <tool>solve_cycle_double_cover()</tool> with the given specifications.
2. Start your response with the tool call on the very first line.
3. Once the tool returns the trace, analyze the final results to explain the exact topological outcome.
"""

def build_tool_system_prompt(base_prompt: str, registry: ToolRegistry) -> str:
    return base_prompt + TOOL_PROMPT_SUFFIX.format(
        tool_descriptions=registry.get_descriptions()
    )

if __name__ == "__main__":
    print("Testing Codette Tools System with integrated high-performance CDC Solver...\n")
    registry = ToolRegistry()
    print("Testing cycle cover tool with a miniature configuration (30 vertices, 150 cycles, 5,000,000 max states Limit):")
    print(tool_solve_cycle_double_cover(n_vertices=30, target_cycles=150, max_states=5000000))