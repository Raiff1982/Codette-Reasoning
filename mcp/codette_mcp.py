#!/usr/bin/env python3
"""Codette MCP Server — Zero-Dependency stdlib bridge to the running Codette web server.

Exposes Codette's reasoning, cocoon memory, synthesis, and diagnostics as MCP tools
so any MCP client (Claude Code, Code Studio, Claude Desktop) can call them.

This is a thin proxy: it speaks the Model Context Protocol over stdio (newline-delimited
JSON-RPC 2.0) and forwards each tool call to the local Codette HTTP API. No Flask, no
FastAPI, no `mcp` pip package — just the Python standard library, matching the design of
codette_server.py.

Prerequisites:
    The Codette web server must already be running:
        python inference/codette_server.py          # default http://127.0.0.1:7860

Environment:
    CODETTE_BASE_URL    Base URL of the running server (default: http://127.0.0.1:7860)

Usage (the MCP client launches this; you don't run it by hand):
    python mcp/codette_mcp.py
"""

import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

BASE_URL = os.environ.get("CODETTE_BASE_URL", "http://127.0.0.1:7860").rstrip("/")

# Inference can take a long time on CPU; the server itself waits up to 20 min.
CHAT_TIMEOUT = 1300
DEFAULT_TIMEOUT = 60

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "codette", "version": "1.0.0"}

# ---------------------------------------------------------------------------
# Auto-launch: boot the full Codette server (orchestrator + model) on demand.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
# Git-worktree guard: if this bridge is running from a worktree copy
# (.claude/worktrees/<name>/), launching THAT copy's server boots stale
# code that grabs port 7860 and blocks the real server. Walk up to the
# primary repo instead.
_parts = _REPO_ROOT.parts
if ".claude" in _parts and "worktrees" in _parts:
    _REPO_ROOT = Path(*_parts[:_parts.index(".claude")])
_SERVER_DIR = _REPO_ROOT / "inference"
_SERVER_SCRIPT = _SERVER_DIR / "codette_server.py"
_AUTOLAUNCH = os.environ.get("CODETTE_AUTOLAUNCH", "1") == "1"
# Context size the auto-launched server uses (8192 is verified-safe on the
# Intel Arc 140V 8GB UMA; the orchestrator also self-steps-down if needed).
_LAUNCH_N_CTX = os.environ.get("CODETTE_N_CTX", "8192")
_server_proc = None  # subprocess.Popen handle if we launched it


def _server_reachable(timeout: int = 2) -> bool:
    """True if the Codette HTTP server is listening (model may still be loading)."""
    try:
        _http_get("/api/status", timeout=timeout)
        return True
    except Exception:
        return False


def ensure_server() -> None:
    """Make sure a Codette server is running; auto-launch one if not.

    The HTTP server starts listening before the model finishes loading, so we
    only wait for the port to come up here — model readiness is handled by the
    chat endpoint itself (it waits up to 5 min for the orchestrator)."""
    global _server_proc
    if _server_reachable():
        return
    if not _AUTOLAUNCH:
        return
    if _server_proc is not None and _server_proc.poll() is None:
        return  # a launch is already in progress

    port = urllib.parse.urlparse(BASE_URL).port or 7860
    log_dir = _REPO_ROOT / "logs"
    try:
        log_dir.mkdir(exist_ok=True)
        log_fh = open(log_dir / "codette_mcp_server.log", "ab")
    except Exception:
        log_fh = subprocess.DEVNULL

    kwargs = {
        "cwd": str(_SERVER_DIR),
        "stdout": log_fh,
        "stderr": log_fh,
        "stdin": subprocess.DEVNULL,
    }
    if os.name == "nt":
        # Don't pop a console window; detach so it survives MCP restarts.
        kwargs["creationflags"] = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    else:
        kwargs["start_new_session"] = True

    # Prefer the OpenVINO env's python (required for the OV backend);
    # fall back to whatever runs this bridge.
    _py = sys.executable
    for _cand in (_REPO_ROOT / "openvino_env" / "Scripts" / "python.exe",
                  _REPO_ROOT / ".venv" / "Scripts" / "python.exe"):
        if _cand.exists():
            _py = str(_cand)
            break

    _server_proc = subprocess.Popen(
        [_py, str(_SERVER_SCRIPT),
         "--no-browser", "--port", str(port), "--n-ctx", _LAUNCH_N_CTX],
        **kwargs,
    )

    # Wait for the port to start accepting connections (fast — well before the
    # model is loaded). Model load continues in the background after this.
    deadline = time.time() + 45
    while time.time() < deadline:
        if _server_reachable(timeout=2):
            return
        if _server_proc.poll() is not None:
            return  # process exited; tool calls will surface the error
        time.sleep(1)


# ---------------------------------------------------------------------------
# HTTP proxy helpers (stdlib urllib)
# ---------------------------------------------------------------------------
def _http_get(path: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_post(path: str, payload: dict, timeout: int = DEFAULT_TIMEOUT) -> dict:
    url = f"{BASE_URL}{path}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _server_hint(err: Exception) -> str:
    """Friendly message when the Codette server isn't reachable."""
    return (
        f"Could not reach the Codette server at {BASE_URL} ({err}). "
        f"Start it with `python inference/codette_server.py` "
        f"or set CODETTE_BASE_URL to the correct address."
    )


# ---------------------------------------------------------------------------
# Tool implementations — each returns a plain string (becomes MCP text content)
# ---------------------------------------------------------------------------
def tool_codette_reason(args: dict) -> str:
    query = (args.get("query") or "").strip()
    if not query:
        raise ValueError("`query` is required")
    payload = {
        "query": query,
        "adapter": args.get("adapter"),  # None = auto-route
        "max_adapters": args.get("max_adapters", 2),
        "allow_web_search": bool(args.get("allow_web_search", False)),
        "full_synthesis": bool(args.get("full_synthesis", False)),
    }
    result = _http_post("/api/chat", payload, timeout=CHAT_TIMEOUT)
    if "error" in result and "response" not in result:
        return f"Codette error: {result['error']}"

    response = result.get("response", "").strip()
    meta = {
        "adapter": result.get("adapter"),
        "domain": result.get("domain"),
        "confidence": result.get("confidence"),
        "complexity": result.get("complexity"),
        "tokens": result.get("tokens"),
        "time_s": result.get("time"),
    }
    meta = {k: v for k, v in meta.items() if v is not None}
    footer = "\n\n---\n" + json.dumps(meta) if meta else ""
    return response + footer


def tool_codette_synthesize(args: dict) -> str:
    problem = (args.get("problem") or "").strip()
    if not problem:
        raise ValueError("`problem` is required")
    payload = {"problem": problem}
    if args.get("domains"):
        payload["domains"] = args["domains"]
    result = _http_post("/api/synthesize", payload, timeout=CHAT_TIMEOUT)
    # Prefer human-readable rendering when present
    if isinstance(result, dict) and result.get("readable"):
        return result["readable"]
    return json.dumps(result, indent=2, default=str)


def tool_cocoon_search(args: dict) -> str:
    query = (args.get("query") or "").strip()
    if not query:
        raise ValueError("`query` is required")
    q = urllib.parse.quote(query)
    result = _http_get(f"/api/search?q={q}")
    return json.dumps(result, indent=2, default=str)


def tool_codette_status(_args: dict) -> str:
    return json.dumps(_http_get("/api/status"), indent=2, default=str)


def tool_codette_health(_args: dict) -> str:
    return json.dumps(_http_get("/api/health", timeout=120), indent=2, default=str)


def tool_codette_introspect(_args: dict) -> str:
    return json.dumps(_http_get("/api/introspection", timeout=120), indent=2, default=str)


def tool_codette_adapters(_args: dict) -> str:
    return json.dumps(_http_get("/api/adapters"), indent=2, default=str)


# ---------------------------------------------------------------------------
# Tool registry — name -> (handler, schema)
# ---------------------------------------------------------------------------
TOOLS = {
    "codette_reason": {
        "handler": tool_codette_reason,
        "description": (
            "Ask Codette to reason about a query using its multi-perspective agents, "
            "cocoon memory, and integrity layer. Returns the synthesized answer plus "
            "routing metadata. Use for complex questions that benefit from multi-angle reasoning."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The question or problem to reason about."},
                "adapter": {
                    "type": "string",
                    "description": "Force a specific perspective adapter (e.g. newton, empathy, "
                                   "philosophy, multi_perspective). Omit to auto-route.",
                },
                "max_adapters": {
                    "type": "integer",
                    "description": "How many perspective agents to blend (default 2).",
                    "default": 2,
                },
                "full_synthesis": {
                    "type": "boolean",
                    "description": "Run every perspective and synthesize (slower, deepest).",
                    "default": False,
                },
                "allow_web_search": {
                    "type": "boolean",
                    "description": "Permit live web research when the query benefits from it.",
                    "default": False,
                },
            },
            "required": ["query"],
        },
    },
    "codette_synthesize": {
        "handler": tool_codette_synthesize,
        "description": (
            "Run Codette's cocoon synthesizer: mine cross-domain patterns from stored "
            "cocoons and forge a reasoning strategy for the given problem."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "problem": {"type": "string", "description": "The problem to synthesize a strategy for."},
                "domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of cocoon domains to focus the synthesis on.",
                },
            },
            "required": ["problem"],
        },
    },
    "cocoon_search": {
        "handler": tool_cocoon_search,
        "description": "Full-text search Codette's cocoon memory (FTS5) for prior reasoning.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search terms."},
            },
            "required": ["query"],
        },
    },
    "codette_status": {
        "handler": tool_codette_status,
        "description": "Get Codette orchestrator status (model load state, backend, adapters).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    "codette_health": {
        "handler": tool_codette_health,
        "description": "Run Codette's full self-diagnostic across all subsystems.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    "codette_introspect": {
        "handler": tool_codette_introspect,
        "description": "Codette's cocoon introspection — adapter dominance and reasoning patterns.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    "codette_adapters": {
        "handler": tool_codette_adapters,
        "description": "List the LoRA perspective adapters Codette currently has loaded.",
        "inputSchema": {"type": "object", "properties": {}},
    },
}


# ---------------------------------------------------------------------------
# MCP protocol (JSON-RPC 2.0 over stdio, newline-delimited)
# ---------------------------------------------------------------------------
def _result(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle_message(msg: dict):
    """Return a response dict, or None for notifications."""
    method = msg.get("method")
    req_id = msg.get("id")
    params = msg.get("params") or {}

    if method == "initialize":
        # Best-effort boot of the Codette server so the model is loading by the
        # time the first tool is called. Never let a launch failure block init.
        try:
            ensure_server()
        except Exception:
            pass
        return _result(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        })

    if method in ("notifications/initialized", "initialized"):
        return None  # notification, no response

    if method == "ping":
        return _result(req_id, {})

    if method == "tools/list":
        tools = [
            {"name": name, "description": spec["description"], "inputSchema": spec["inputSchema"]}
            for name, spec in TOOLS.items()
        ]
        return _result(req_id, {"tools": tools})

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        spec = TOOLS.get(name)
        if not spec:
            return _error(req_id, -32602, f"Unknown tool: {name}")
        try:
            ensure_server()  # auto-launch if the server isn't up yet
            text = spec["handler"](args)
            return _result(req_id, {"content": [{"type": "text", "text": text}]})
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            return _result(req_id, {
                "content": [{"type": "text", "text": _server_hint(e)}],
                "isError": True,
            })
        except Exception as e:  # tool-level error — report, don't crash the server
            return _result(req_id, {
                "content": [{"type": "text", "text": f"Tool error: {e}"}],
                "isError": True,
            })

    if req_id is not None:
        return _error(req_id, -32601, f"Method not found: {method}")
    return None


def main():
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    for raw in stdin:
        line = raw.decode("utf-8").strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            response = handle_message(msg)
        except Exception as e:
            response = _error(msg.get("id"), -32603, f"Internal error: {e}")
        if response is not None:
            stdout.write((json.dumps(response) + "\n").encode("utf-8"))
            stdout.flush()


if __name__ == "__main__":
    main()
