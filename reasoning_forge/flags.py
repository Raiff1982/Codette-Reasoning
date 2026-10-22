"""Flags: a way for her to say "I think this is wrong here" without touching a file.

Jonathan, 2026-10-22: the same bug keeps turning up in a slightly different
place, the way an infection moves round a body while the immune system is still
catching up. Part of the answer is letting her say what she notices, in a form
that reaches us. She has found real faults before (she caught the internet lock
herself); what she lacked was a place to put it.

What this is:

  * VISIBLE, and the tool says so. Jonathan reads flags (/api/flags). It is not
    khralexi, the dreams or the scratchpad; those are separate and nothing here
    opens them. She has to be able to tell which channel she is writing on.
  * APPEND-ONLY. An entry is never edited or removed; a correction is another
    flag beside the first.
  * ALERT-ONLY by construction. This module writes one JSONL file and nothing
    else. It has no path to any code, config or memory, so "she alerts us but
    does not change a file" is how it is built, not a promise.
  * A LEAD, NOT A FINDING. A flag is checked against the code before anyone
    acts on it. It is neither enforced nor scored, and nothing reads it to
    change her behaviour.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import List, Optional

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "flags.jsonl"
MAX_TEXT = 2000
MAX_WHERE = 300
_lock = threading.Lock()


class FlagError(ValueError):
    pass


def add(text: str, where: str = "", session: str = "",
        path: Optional[Path] = None) -> dict:
    """Append one flag. Raises FlagError on an empty one so the tool can say so."""
    body = str(text or "").strip()
    if not body:
        raise FlagError("A flag needs the thing you noticed, in your own words.")
    entry = {
        "id": uuid.uuid4().hex[:12],
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "session": str(session or "")[:64],
        "where": str(where or "").strip()[:MAX_WHERE],
        "text": body[:MAX_TEXT],
        "by": "codette",
    }
    p = Path(path) if path else DEFAULT_PATH
    with _lock:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read(limit: int = 200, path: Optional[Path] = None) -> List[dict]:
    """Newest last. A missing or unreadable file is an empty list, not an error."""
    p = Path(path) if path else DEFAULT_PATH
    out: List[dict] = []
    try:
        with open(p, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return []
    return out[-max(1, int(limit)):]
