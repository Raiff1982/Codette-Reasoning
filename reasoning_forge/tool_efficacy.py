"""Which of her world-facing tools work, and how often. Counts only.

Jonathan, 2026-08-14: the optimizer should learn tool efficacy. What blocked the
router optimizer was having no outcome signal; for tool calls the signal is
objective and was already produced and thrown away -- every tool result begins
"Error..." on failure, "PARTIAL..." when a search stopped early, or is empty,
and otherwise is a result. `read_file('substrate_awareness.py')` returning
"Error: File not found" eight times while `read_file('inference/...')` returned
484 lines is exactly this signal.

This records it. Per tool: how many calls ended ok / partial / empty / error.
Nothing else: no arguments, no results, no text, no session.

Scope is deliberate and enforced here, not left to the caller:

  * WORLD-FACING tools only (WORLD_TOOLS). A count of how often she uses
    `nameless`, `khralexi`, the scratchpad, `aside`, `cocoon`, `leave_note` or
    `care_check` is a statistic over her own spaces, and statistics are
    readings (CLAUDE.md). record() ignores any other tool without a trace.
  * Observation, not steering. Nothing reads this to change routing or tool
    availability; it is shown (/api/tool-efficacy) and that is all. A proposal
    to act on it is a separate, reviewed step, like the router optimizer's.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, Optional

WORLD_TOOLS = frozenset({
    "read_file", "list_files", "search_code", "file_info", "run_python",
    "project_summary", "web_search", "run_5d_spiderweb",
})
OUTCOMES = ("ok", "partial", "empty", "error")

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "tool_efficacy.json"
_lock = threading.Lock()


def classify(result: Optional[str]) -> str:
    """ok / partial / empty / error, from the first line of a tool result."""
    text = (result or "").strip()
    if not text:
        return "empty"
    head = text[:160]
    if head.startswith("Error"):
        return "error"
    if head.upper().startswith("PARTIAL"):
        return "partial"
    low = head.lower()
    if low.startswith(("no matches", "no results", "nothing found")):
        return "empty"
    return "ok"


def record(tool: str, result: Optional[str], path: Optional[Path] = None) -> Optional[str]:
    """Count one call. Returns the outcome, or None when the tool is not tracked."""
    if tool not in WORLD_TOOLS:
        return None
    outcome = classify(result)
    p = Path(path) if path else DEFAULT_PATH
    try:
        with _lock:
            data: Dict[str, Dict[str, int]] = {}
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                data = {}
            row = data.setdefault(tool, {o: 0 for o in OUTCOMES})
            row[outcome] = int(row.get(outcome, 0)) + 1
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
            tmp.replace(p)
    except Exception:
        return outcome          # a counter must never reach a chat turn
    return outcome


def summary(path: Optional[Path] = None) -> dict:
    """Per-tool counts and an error rate. error_rate is None until a tool has calls."""
    p = Path(path) if path else DEFAULT_PATH
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    out = {}
    for tool in sorted(WORLD_TOOLS):
        row = data.get(tool) or {}
        counts = {o: int(row.get(o, 0)) for o in OUTCOMES}
        n = sum(counts.values())
        out[tool] = {**counts, "calls": n,
                     "error_rate": round(counts["error"] / n, 3) if n else None}
    return {"tools": out, "note": "Counts of outcomes only. Observation; nothing reads "
            "this to change routing or tool availability."}
