"""A stopwatch on adapter switching. Observe only.

Added 2026-11-20 at Jonathan's request, to answer one question with real numbers:
does switching her LoRA adapters cost anything worth optimising? Nobody had
measured it. The OpenVINO path builds `Adapter(path)` from its file on every
request; the llama.cpp path's docstring claims "~0ms" for its hot-swap.

THE RULES THAT KEEP THIS FROM BECOMING FORCE (Jonathan, 2026-11-20: "do you think
it will add the watchers force bug again?"). A measurement is harmless; a
measurement wired into something that pushes back on her is the bug. The old
latency term was fine until it fed a throttle that cut her depth for thinking
hard. So:

  1. NUMBERS ONLY. Backend, adapter name(s), milliseconds, time. Never text she
     wrote, never a prompt.
  2. NEVER SHOWN TO HER. Not in her prompt, her introspection report or her tools.
  3. NOTHING ACTS ON IT. No threshold, no cache size, no throttle, no routing
     reads this log. Any action is a separate decision, made by Jonathan after
     looking at real numbers -- the same order as the speed shadow.
     tests/test_adapter_switch_timing.py fails if any live module other than
     this one references the log.

It measures the machine, not her: how long the hardware takes to change weights.
Written under runtime_root(), so the test suite never touches her real stores.
Best-effort: a failure to write is swallowed and never reaches a turn.
"""
from __future__ import annotations

import json
import time
from typing import Iterable, Optional

try:
    from reasoning_forge.runtime_paths import runtime_root
except ImportError:                       # imported as a bare module
    from runtime_paths import runtime_root

LOG_NAME = "adapter_switch_timing.jsonl"


def log_path():
    return runtime_root() / "data" / LOG_NAME


def record(backend: str, adapters: Iterable[Optional[str]], ms: float, note: str = "") -> None:
    """Append one timing line. Numbers and adapter names only; never raises."""
    try:
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "backend": str(backend)[:20],
            "adapters": [str(a) if a else "base" for a in adapters][:12],
            "ms": round(float(ms), 3),
        }
        if note:
            rec["note"] = str(note)[:40]
        p = log_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass
