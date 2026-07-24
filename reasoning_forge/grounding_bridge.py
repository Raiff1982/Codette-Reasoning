#!/usr/bin/env python3
"""Grounding Bridge — Phase B1: observe what the synthesizer forges, grounded.

Connects the CREATE half (cocoon_synthesizer forges qualitative reasoning paths
and strategies) to the VERIFY half (grounding.verify). It reads a forged thought,
pulls any checkable claims, grounds them, and returns an HONEST report.

The honesty is the entire point, and it is subtle here:
  - Most forged thoughts are QUALITATIVE ("rational discomfort", "principled
    plasticity"). They contain no arithmetic claim. The correct report for such a
    thought is UNGROUNDED — "no checkable claim found" — NEVER "verified".
    Reporting a qualitative thought as verified because nothing was refuted would
    be the exact lie this project exists to prevent.
  - A thought that asserts something false and checkable (a bad number) is FLAGGED.

So a forged thought lands in one of three honest states:
  FLAGGED    — at least one checkable claim was REFUTED. Look here.
  SUPPORTED  — checkable claims were found and all VERIFIED.
  UNGROUNDED — no checkable claim; arithmetic grounding says nothing about it.
               (This is most of them, today. It is honest, not a pass.)

Shadow only. Nothing in the runtime calls this yet; when it does (Phase D) it
observes and logs, it does not gate. See docs/NEUROSYMBOLIC_GROUNDING.md.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

from reasoning_forge.grounding import (
    verify, extract_claims, GroundingResult, Verdict,
)


# Honest three-state status for a whole forged thought.
FLAGGED = "flagged"        # >=1 checkable claim refuted
SUPPORTED = "supported"    # checkable claims found, all verified
UNGROUNDED = "ungrounded"  # no checkable claim — grounding says nothing (NOT a pass)


@dataclass
class GroundingReport:
    """Honest grounding summary for one forged thought."""
    source_kind: str            # "reasoning_path" | "strategy" | "pattern" | "text"
    source_id: str
    status: str                 # FLAGGED / SUPPORTED / UNGROUNDED
    claims_found: int
    verified: int
    refuted: int
    unverifiable: int
    results: List[dict] = field(default_factory=list)
    note: str = ""
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


def _classify(results: List[GroundingResult]) -> tuple:
    """Return (status, note) from the per-claim verdicts. Omit-never-fabricate:
    no checkable claim => UNGROUNDED, never SUPPORTED."""
    checkable = [r for r in results if r.verdict in (Verdict.VERIFIED, Verdict.REFUTED)]
    refuted = [r for r in checkable if r.verdict is Verdict.REFUTED]
    verified = [r for r in checkable if r.verdict is Verdict.VERIFIED]

    if refuted:
        return FLAGGED, f"{len(refuted)} checkable claim(s) REFUTED — inspect this forged thought"
    if verified:
        return SUPPORTED, f"{len(verified)} checkable claim(s) found, all verified"
    return UNGROUNDED, (
        "no arithmetic-checkable claim found — this is a qualitative thought "
        "grounding cannot speak to yet (honest UNGROUNDED, not a pass)"
    )


def ground_text(text: str, *, source_kind: str = "text", source_id: str = "") -> GroundingReport:
    """Ground the checkable claims in a block of text. Pure (no logging)."""
    claims = extract_claims(text or "")
    results = [verify(c) for c in claims]
    status, note = _classify(results)
    return GroundingReport(
        source_kind=source_kind,
        source_id=source_id or "",
        status=status,
        claims_found=len(claims),
        verified=sum(1 for r in results if r.verdict is Verdict.VERIFIED),
        refuted=sum(1 for r in results if r.verdict is Verdict.REFUTED),
        unverifiable=sum(1 for r in results if r.verdict is Verdict.UNVERIFIABLE),
        results=[r.to_dict() for r in results],
        note=note,
    )


def ground_reasoning_path(path) -> GroundingReport:
    """Ground a cocoon_synthesizer ReasoningPath (steps + conclusion).

    Accepts the dataclass or a dict with 'steps'/'conclusion'/'strategy_name'.
    """
    steps = getattr(path, "steps", None)
    conclusion = getattr(path, "conclusion", None)
    name = getattr(path, "strategy_name", None)
    if steps is None and isinstance(path, dict):
        steps = path.get("steps", [])
        conclusion = path.get("conclusion", "")
        name = path.get("strategy_name", "")
    text = "\n".join(list(steps or []) + [conclusion or ""])
    return ground_text(text, source_kind="reasoning_path", source_id=name or "")


def ground_strategy(strategy) -> GroundingReport:
    """Ground a ReasoningStrategy (definition + mechanism + rationale)."""
    def g(attr):
        return getattr(strategy, attr, None) if not isinstance(strategy, dict) else strategy.get(attr)
    text = "\n".join(str(g(a) or "") for a in ("definition", "mechanism", "improvement_rationale"))
    sid = g("strategy_id") or g("name") or ""
    return ground_text(text, source_kind="strategy", source_id=str(sid))


def ground_pattern(pattern) -> GroundingReport:
    """Ground a CocoonPattern (description + structural_similarity + evidence)."""
    def g(attr):
        return getattr(pattern, attr, None) if not isinstance(pattern, dict) else pattern.get(attr)
    evidence = g("evidence") or []
    text = "\n".join([str(g("description") or ""), str(g("structural_similarity") or "")] + [str(e) for e in evidence])
    return ground_text(text, source_kind="pattern", source_id=str(g("name") or ""))


def observe(report: GroundingReport, path: str | Path = None) -> None:
    """Append a report to the grounding shadow log. SHADOW ONLY (applied: false)."""
    path = Path(path) if path else Path(__file__).resolve().parent.parent / "data" / "grounding_shadow.jsonl"
    rec = report.to_dict()
    rec["mode"] = "shadow"
    rec["applied"] = False
    rec["record"] = "bridge_report"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass  # logging must never break a turn
