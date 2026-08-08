"""Last-session recall — answering "what did we talk about last time?"

Codette's recall is entirely similarity-based: `recall_relevant` returns the
cocoons whose text resembles the current query. That works for "what do you know
about X" and fails completely for "what did we discuss yesterday", because the
question carries none of the vocabulary of its own answer. Asked that, she can
only return whatever happens to look like the asking, which is nothing.

So she has no mechanism for *the previous conversation as a thing you can ask
for*, and appears to have forgotten it. She hasn't. There is no path.

This builds one. Two honest constraints shape it:

  - SESSIONS ARE NOT RECORDED. The v3 cocoon schema has a `session_id` field and
    nothing populates it — 0 of 400 sampled cocoons carry one. Boundaries here
    are therefore INFERRED from gaps in time, and every result says so. An
    inferred boundary must never be presented as a recorded one.

  - NOTHING IS SUMMARIZED INTO NARRATIVE. This returns what was actually said,
    in order, with timestamps. It does not compose a story about the session,
    because a generated summary of remembered events is the exact place a
    fabrication would enter unnoticed.

It reads only. It writes nothing, gates nothing, and injects nothing.

Recovered from the Codette archives — see RECOVERY_MANIFEST.md

CORRECTION, 2026-08-07: this file was NOT recovered from an archive. It was
authored 2026-07-30 and reached main via be01c22. RECOVERY_MANIFEST.md was
generated from that merge diff, and a merge diff cannot tell archive material
apart from work carried over on a branch — so five entries were mislabelled,
four of them these files. The line above is kept rather than removed, because
corrections here are additive. See docs/HANDOFF_2026-08-04.md.

"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

COCOON_DIR = Path(__file__).resolve().parent.parent / "cocoons"

# A pause longer than this reads as a session boundary. It is a threshold, not a
# fact, and every result carries that caveat.
DEFAULT_GAP_SECONDS = 30 * 60


@dataclass(frozen=True)
class Exchange:
    """One recorded turn."""
    at: float
    query: str
    response: str
    adapter: Optional[str] = None

    def describe(self, max_chars: int = 160) -> str:
        clock = time.strftime("%H:%M", time.localtime(self.at))
        q = self.query.strip().replace("\n", " ")[:max_chars]
        a = self.response.strip().replace("\n", " ")[:max_chars]
        who = f" [{self.adapter}]" if self.adapter else ""
        return f"  [{clock}] you: {q}\n  [{clock}] her{who}: {a}"


@dataclass(frozen=True)
class SessionWindow:
    """A stretch of conversation, bounded by inferred pauses."""
    started_at: float
    ended_at: float
    exchanges: List[Exchange] = field(default_factory=list)
    boundary: str = "inferred"          # never "recorded" — nothing records it
    gap_seconds: int = DEFAULT_GAP_SECONDS
    note: str = ""

    def __bool__(self) -> bool:
        return bool(self.exchanges)

    def describe(self, limit: int = 12) -> str:
        if not self.exchanges:
            return self.note or "no previous session found in the record"

        day = time.strftime("%a %d %b", time.localtime(self.started_at))
        start = time.strftime("%H:%M", time.localtime(self.started_at))
        end = time.strftime("%H:%M", time.localtime(self.ended_at))

        head = (
            f"Previous session — {day}, {start} to {end}, "
            f"{len(self.exchanges)} exchange(s).\n"
            f"Boundary is INFERRED from a pause of more than "
            f"{self.gap_seconds // 60} minutes; sessions are not recorded, "
            f"so this is a reading of the timeline, not a stored fact."
        )

        shown = self.exchanges[:limit]
        body = "\n".join(e.describe() for e in shown)
        tail = ""
        if len(self.exchanges) > limit:
            tail = f"\n  ... {len(self.exchanges) - limit} further exchange(s) not shown"
        return f"{head}\n{body}{tail}"


def _index(cocoon_dir: Path) -> List[Tuple[float, Path]]:
    """Timestamps first, without parsing. Only the chosen window gets opened."""
    out = []
    try:
        for entry in os.scandir(cocoon_dir):
            if entry.is_file() and entry.name.endswith(".json"):
                out.append((entry.stat().st_mtime, Path(entry.path)))
    except (OSError, FileNotFoundError):
        return []
    out.sort()
    return out


def _read(path: Path) -> Optional[Exchange]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

    wrapped = data.get("wrapped") or {}
    query = str(wrapped.get("query") or "").strip()
    response = str(wrapped.get("response") or "").strip()
    if not query and not response:
        return None

    at = data.get("timestamp") or wrapped.get("timestamp")
    try:
        at = float(at)
    except (TypeError, ValueError):
        at = path.stat().st_mtime

    return Exchange(
        at=at,
        query=query,
        response=response,
        adapter=(wrapped.get("adapter") or None),
    )


def previous_session(
    before: Optional[float] = None,
    gap_seconds: int = DEFAULT_GAP_SECONDS,
    cocoon_dir: Path = COCOON_DIR,
    max_exchanges: int = 60,
) -> SessionWindow:
    """The contiguous stretch of conversation immediately preceding `before`.

    `before` is normally the current session's entry time — the fixed t=0 from
    the dive record. Walking back from a known origin is what makes "last
    session" answerable at all.

    Returns an empty window, with a note explaining why, rather than reaching
    further back for something to show.
    """
    before = before if before is not None else time.time()
    indexed = [(ts, p) for ts, p in _index(cocoon_dir) if ts < before]

    if not indexed:
        return SessionWindow(0.0, 0.0, [], gap_seconds=gap_seconds,
                             note="no cocoons recorded before this entry")

    # Walk backward until a pause wide enough to read as a boundary.
    window: List[Tuple[float, Path]] = [indexed[-1]]
    for i in range(len(indexed) - 2, -1, -1):
        if window[-1][0] - indexed[i][0] > gap_seconds:
            break
        window.append(indexed[i])
        if len(window) >= max_exchanges:
            break
    window.reverse()

    exchanges = [e for e in (_read(p) for _, p in window) if e is not None]
    if not exchanges:
        return SessionWindow(0.0, 0.0, [], gap_seconds=gap_seconds,
                             note="previous session found but no readable exchanges in it")

    return SessionWindow(
        started_at=exchanges[0].at,
        ended_at=exchanges[-1].at,
        exchanges=exchanges,
        gap_seconds=gap_seconds,
    )


_ASKING_ABOUT_LAST_TIME = (
    "last session", "last conversation", "last time we", "previous session",
    "previous conversation", "what did we talk about", "what do you remember",
    "what did we discuss", "where did we leave", "pick up where",
    "our last chat", "before this", "earlier today we", "yesterday we",
)


def is_asking_about_last_session(query: str) -> bool:
    """Whether a query is reaching for the previous conversation.

    Deliberately literal. A false negative costs a recall she can still get by
    asking plainly; a false positive would inject an unrelated conversation into
    a turn that never asked for one.
    """
    if not query:
        return False
    lowered = " ".join(query.lower().split())
    return any(phrase in lowered for phrase in _ASKING_ABOUT_LAST_TIME)
