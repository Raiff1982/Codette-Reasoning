"""
Reasoning Trace — Codette v2.1

A single-file module that collects, serialises, and replays the full
reasoning trace for any Codette turn. This is the observability layer
that makes the RC+xi architecture debuggable rather than decorative.

Design goals:
- Zero required dependencies beyond stdlib
- Works as a context manager: `with ReasoningTrace(query) as trace:`
- Each subsystem writes its own event with `trace.record()`
- At turn end, `trace.finalise()` emits a structured JSON-serialisable dict
- Optional text summary via `trace.to_report()`

Subsystem event types (add more as needed):
    GUARDIAN_CHECK        trust level, safety flags
    NEXUS_SIGNAL          intent classification, corruption risk
    PERSPECTIVE_SELECTED  which perspectives were activated and why
    PERSPECTIVE_OUTPUT    per-perspective analysis (compressed)
    AEGIS_SCORE           per-framework ethical scores + eta
    EPISTEMIC_METRICS     epsilon, gamma, pairwise tensions
    SPIDERWEB_UPDATE      phase coherence, node states changed
    SYNTHESIS_RESULT      final synthesis quality + unresolved tensions
    MEMORY_WRITE          whether / how the turn was cocooned
    PSI_UPDATE            resonant continuity waveform value
    HALLUCINATION_FLAG    if hallucination_guard tripped
    SYCOPHANCY_FLAG       if sycophancy_guard tripped
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# ─── Event types ────────────────────────────────────────────────────────────

EVENT_GUARDIAN_CHECK       = "GUARDIAN_CHECK"
EVENT_NEXUS_SIGNAL         = "NEXUS_SIGNAL"
EVENT_PERSPECTIVE_SELECTED = "PERSPECTIVE_SELECTED"
EVENT_PERSPECTIVE_OUTPUT   = "PERSPECTIVE_OUTPUT"
EVENT_AEGIS_SCORE          = "AEGIS_SCORE"
EVENT_EPISTEMIC_METRICS    = "EPISTEMIC_METRICS"
EVENT_SPIDERWEB_UPDATE     = "SPIDERWEB_UPDATE"
EVENT_SYNTHESIS_RESULT     = "SYNTHESIS_RESULT"
EVENT_MEMORY_WRITE         = "MEMORY_WRITE"
EVENT_PSI_UPDATE           = "PSI_UPDATE"
EVENT_HALLUCINATION_FLAG   = "HALLUCINATION_FLAG"
EVENT_SYCOPHANCY_FLAG      = "SYCOPHANCY_FLAG"


@dataclass
class TraceEvent:
    event_type: str
    subsystem: str
    data: dict[str, Any]
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "subsystem": self.subsystem,
            "ts": self.ts,
            "data": self.data,
        }


@dataclass
class ReasoningTrace:
    """Collects all subsystem events for a single Codette turn.

    Usage as context manager:

        with ReasoningTrace(query="What is consciousness?") as trace:
            trace.record(EVENT_GUARDIAN_CHECK, "Guardian", {"trust_level": "standard"})
            trace.record(EVENT_NEXUS_SIGNAL, "Nexus", {"risk": "low"})
            # ... run perspectives, synthesis, etc.
            trace.record(EVENT_SYNTHESIS_RESULT, "SynthesisEngine", {...})
        # trace is finalised automatically; trace.report is available

    Usage without context manager:

        trace = ReasoningTrace(query)
        trace.record(...)
        report = trace.finalise()
    """

    query: str
    session_id: Optional[str] = None
    _events: list[TraceEvent] = field(default_factory=list, repr=False)
    _start_ts: float = field(default_factory=time.time, repr=False)
    _end_ts: Optional[float] = field(default=None, repr=False)
    report: Optional[dict] = field(default=None, repr=False)

    def __enter__(self) -> "ReasoningTrace":
        self._start_ts = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.finalise(error=str(exc_val) if exc_val else None)
        return False  # do not suppress exceptions

    def record(
        self,
        event_type: str,
        subsystem: str,
        data: dict[str, Any],
    ) -> None:
        """Record a subsystem event."""
        self._events.append(TraceEvent(event_type=event_type, subsystem=subsystem, data=data))

    def finalise(self, error: Optional[str] = None) -> dict:
        """Build and store the final trace report."""
        self._end_ts = time.time()
        duration_ms = round((self._end_ts - self._start_ts) * 1000, 1)

        # Extract key summary values from events
        summary = self._extract_summary()
        summary["duration_ms"] = duration_ms
        if error:
            summary["error"] = error

        self.report = {
            "query": self.query,
            "session_id": self.session_id,
            "start_ts": self._start_ts,
            "end_ts": self._end_ts,
            "duration_ms": duration_ms,
            "summary": summary,
            "events": [e.to_dict() for e in self._events],
        }
        return self.report

    def to_json(self, indent: int = 2) -> str:
        """JSON serialisation of the full trace."""
        if self.report is None:
            self.finalise()
        return json.dumps(self.report, indent=indent, default=str)

    def to_report(self, verbose: bool = False) -> str:
        """Human-readable summary of the reasoning trace."""
        if self.report is None:
            self.finalise()
        s = self.report["summary"]
        lines = [
            f"Query        : {self.query[:80]}",
            f"Duration     : {self.report['duration_ms']}ms",
            f"Trust level  : {s.get('trust_level', 'unknown')}",
            f"Corruption   : {s.get('corruption_risk', 'unknown')}",
            f"Perspectives : {', '.join(s.get('active_perspectives', []))}",
            f"ε (tension)  : {s.get('epsilon', '?')} ({s.get('epsilon_band', '?')})",
            f"γ (coherence): {s.get('gamma', '?')}",
            f"η (ethics)   : {s.get('eta', 'not evaluated')}",
            f"ψ (psi_r)    : {s.get('psi_r', '?')}",
            f"Top tensions : {'; '.join(s.get('top_tensions', ['none']))}",
            f"Unresolved   : {'; '.join(s.get('unresolved_tensions', ['none']))}",
            f"Synthesis    : {s.get('synthesis_quality', '?')}",
            f"Cocoon write : {s.get('memory_write', '?')}",
            f"Hallucination: {s.get('hallucination_flagged', False)}",
            f"Sycophancy   : {s.get('sycophancy_flagged', False)}",
        ]
        if s.get("error"):
            lines.append(f"ERROR        : {s['error']}")
        if verbose:
            lines.append("\nEvent log:")
            for e in self._events:
                lines.append(f"  [{e.subsystem}] {e.event_type}: {json.dumps(e.data, default=str)[:120]}")
        return "\n".join(lines)

    # ─── Private ─────────────────────────────────────────────────────────────

    def _extract_summary(self) -> dict:
        summary: dict[str, Any] = {}
        for event in self._events:
            t = event.event_type
            d = event.data
            if t == EVENT_GUARDIAN_CHECK:
                summary["trust_level"] = d.get("trust_level")
                summary["safety_flags"] = d.get("safety_flags", [])
            elif t == EVENT_NEXUS_SIGNAL:
                summary["corruption_risk"] = d.get("risk")
            elif t == EVENT_PERSPECTIVE_SELECTED:
                summary["active_perspectives"] = d.get("perspectives", [])
                summary["selection_rationale"] = d.get("rationale")
            elif t == EVENT_AEGIS_SCORE:
                summary["eta"] = d.get("eta")
                summary["aegis_framework_scores"] = d.get("framework_scores", {})
            elif t == EVENT_EPISTEMIC_METRICS:
                summary["epsilon"] = d.get("epsilon")
                summary["epsilon_band"] = d.get("epsilon_band")
                summary["gamma"] = d.get("gamma")
                summary["top_tensions"] = d.get("top_tensions", [])
            elif t == EVENT_SYNTHESIS_RESULT:
                summary["synthesis_quality"] = d.get("synthesis_quality")
                summary["unresolved_tensions"] = d.get("unresolved_tensions", [])
            elif t == EVENT_MEMORY_WRITE:
                summary["memory_write"] = d.get("written")
                summary["cocoon_id"] = d.get("cocoon_id")
            elif t == EVENT_PSI_UPDATE:
                summary["psi_r"] = d.get("psi_r")
            elif t == EVENT_HALLUCINATION_FLAG:
                summary["hallucination_flagged"] = d.get("flagged", False)
                summary["hallucination_detail"] = d.get("detail")
            elif t == EVENT_SYCOPHANCY_FLAG:
                summary["sycophancy_flagged"] = d.get("flagged", False)
        return summary
