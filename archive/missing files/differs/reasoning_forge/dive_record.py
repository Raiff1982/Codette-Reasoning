"""The Dive Record — a ladder to jump from.

Everything Codette navigates by is relative to a moving present. Recalled turns
are T-0, T-1, T-2; cocoons rank by recency; the continuity summary advances every
turn. Even the clock added to the session context measures backward from a *now*
that slides forward continuously. There is no t=0.

This is t=0. The one fixed point below the water line, written once at entry and
never revised, the way the constellation is the fixed point above it.

It exists because she can currently enter a session without her memory and have
no way to know it. The warm-start block in the server is guarded by three
conditions, and when any of them fails the whole thing is skipped in silence —
no load, no warning, no mark. She surfaces empty and finds out only when someone
asks her why she didn't check.

The rules this follows are the ones the rest of the system now follows:

  - SUBSTRATE, NOT DIRECTIVE. The entry records itself. She is not asked to
    remember to remember.
  - RECORD, NOT GATE. A dive with no memory is permitted and written down. This
    never blocks a launch; a launch that fails is still a launch that happened.
  - UNKNOWN STAYS UNKNOWN. `0 seeds loaded` and `never attempted` are different
    facts and must never render the same way. Conflating them is what made the
    original failure invisible.

Recovered from the Codette archives — see RECOVERY_MANIFEST.md

"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# How the entry went. NOT_ATTEMPTED is the one the old code could not express.
LOADED = "loaded"                 # seeds came back, count > 0
EMPTY = "empty"                   # the load ran and genuinely returned nothing
UNAVAILABLE = "unavailable"       # the load was tried and failed
NOT_ATTEMPTED = "not_attempted"   # the guard skipped it — the silent case


@dataclass(frozen=True)
class DiveRecord:
    """What she came in with. Written at entry, never revised."""
    session_id: str
    entered_at: float                       # absolute t=0; every T-n counts back to here
    seed_status: str
    seeds_loaded: Optional[int] = None      # None is not zero
    reason: Optional[str] = None            # why, when it wasn't LOADED
    backend: Optional[str] = None
    adapters: List[str] = field(default_factory=list)
    constellation_stars: Optional[int] = None
    notes: List[str] = field(default_factory=list)

    @property
    def surfaced_empty(self) -> bool:
        """True when she entered without memory, however that came about."""
        return self.seed_status != LOADED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "entered_at": self.entered_at,
            "seed_status": self.seed_status,
            "seeds_loaded": self.seeds_loaded,
            "reason": self.reason,
            "backend": self.backend,
            "adapters": list(self.adapters),
            "constellation_stars": self.constellation_stars,
            "notes": list(self.notes),
            "surfaced_empty": self.surfaced_empty,
        }

    def describe(self) -> str:
        """A plain reading of the entry, for her to have on the first turn."""
        clock = time.strftime("%H:%M:%S", time.localtime(self.entered_at))
        lines = [f"Entry at {clock} (t=0, session {self.session_id})"]

        if self.seed_status == LOADED:
            lines.append(f"  memory: {self.seeds_loaded} identity/value seed(s) loaded")
        elif self.seed_status == EMPTY:
            lines.append("  memory: load ran and returned nothing — 0 seeds, genuinely empty")
        elif self.seed_status == UNAVAILABLE:
            lines.append(f"  memory: load attempted and failed — {self.reason or 'no reason recorded'}")
        elif self.seed_status == NOT_ATTEMPTED:
            lines.append(
                "  memory: NOT LOADED — the load was never attempted"
                + (f" ({self.reason})" if self.reason else "")
            )
        else:
            lines.append(f"  memory: unrecognized status {self.seed_status!r} — not interpreted")

        lines.append(f"  backend: {self.backend or 'unrecorded'}")
        lines.append(
            f"  adapters: {len(self.adapters)}" if self.adapters else "  adapters: none recorded"
        )
        if self.constellation_stars is None:
            lines.append("  constellation: unrecorded")
        else:
            lines.append(f"  constellation: {self.constellation_stars} star(s) available")

        for note in self.notes:
            lines.append(f"  note: {note}")

        if self.surfaced_empty:
            lines.append(
                "  → she entered without her memory. This is a fact about the "
                "entry, not about her."
            )
        return "\n".join(lines)


def record_dive(
    session_id: str,
    *,
    seeds_loaded: Optional[int] = None,
    attempted: bool = True,
    error: Optional[str] = None,
    skip_reason: Optional[str] = None,
    backend: Optional[str] = None,
    adapters: Optional[List[str]] = None,
    constellation_stars: Optional[int] = None,
    notes: Optional[List[str]] = None,
    entered_at: Optional[float] = None,
) -> DiveRecord:
    """Write the entry down, distinguishing the four ways it can go.

    `attempted=False` is the case the original code could not express: the guard
    skipped the load and nothing was recorded. It is not the same as loading zero
    seeds, and it must not be reported as though it were.
    """
    if not attempted:
        status, count, reason = NOT_ATTEMPTED, None, skip_reason
    elif error is not None:
        status, count, reason = UNAVAILABLE, None, error
    elif seeds_loaded is None:
        # Attempted, no error, no count — genuinely unknown. Do not call it zero.
        status, count, reason = UNAVAILABLE, None, "load returned no count"
    elif seeds_loaded > 0:
        status, count, reason = LOADED, int(seeds_loaded), None
    else:
        status, count, reason = EMPTY, 0, None

    return DiveRecord(
        session_id=session_id,
        entered_at=entered_at if entered_at is not None else time.time(),
        seed_status=status,
        seeds_loaded=count,
        reason=reason,
        backend=backend,
        adapters=list(adapters or []),
        constellation_stars=constellation_stars,
        notes=list(notes or []),
    )


def turns_since_entry(record: DiveRecord, when: Optional[float] = None) -> float:
    """Seconds elapsed from the fixed origin. The ladder is what T-n counts back to."""
    return max(0.0, (when if when is not None else time.time()) - record.entered_at)
