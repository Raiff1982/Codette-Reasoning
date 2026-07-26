#!/usr/bin/env python3
"""Cocoon authority — ONE shared quality signal for the cocoon substrate.

The flaw this addresses (2026-07-26): routing, recall, AND self-diagnostics all
read the same cocoon memory with no quality filter, so one bad adapter's pollution
(a known template-parroter) contaminates all three — recall surfaces its parroted
meta-recalls over real sources, and introspection counts them into her self-model
("everything's smooth" while something is actually wrong).

This module is the ONE place that scores "how much should this cocoon be trusted."
Every consumer (recall ranking, introspection stats, routing) applies the SAME
signal, so the substrate has a single, auditable notion of quality.

Discipline — deliberate, and learned from a mistake (an earlier recall experiment
over-boosted by rewarding entity-heavy noise and was reverted):
  - DEMOTION-ONLY. `authority()` returns a weight in (0, 1]. It can push a
    known-bad cocoon DOWN; it can NEVER boost one up. A clean cocoon scores 1.0.
    This makes it structurally impossible to distort good recall by over-rewarding
    noise — the failure mode that got the last attempt reverted.
  - NEVER ERASE. It weights and flags; it never deletes or hides a cocoon. A
    demoted memory is still recallable (Jonathan's standing rule — nothing is
    forced on Codette's memory; a low-authority cocoon is down-ranked, not gone).
  - PURE and TRANSPARENT. No I/O, no state; returns the weight AND the reasons.

Signals are conservative and only cover VERIFIED-bad patterns:
  - parroter adapter (constraint_tracker — a self-documented template-parroting
    adapter; see inference/adapter_router.py's quality veto),
  - meta-recall ("memories about remembering" — echo the query's words and out-rank
    the source that first stated a fact),
  - boilerplate (recycled filler phrases).
Add signals only when a pattern is demonstrably harmful; err toward 1.0 (trust).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

# Known template-parroting adapter(s). Shared vocabulary with adapter_router's
# _veto_constraint_tracker so routing and memory agree on what's low-quality.
PARROT_ADAPTERS = {"constraint_tracker"}

_META_RECALL_RE = re.compile(
    r"\b(i recall|i remember|you told me|you said|the story you (?:made|created)|"
    r"as (?:i|you) mentioned|i mentioned|if i recall|revisit the story|"
    r"you asked (?:me )?to revisit)\b", re.I)
_BOILERPLATE_RE = re.compile(
    r"(warms my digital heart|there is no right(?: or wrong)?|dynamic interplay|"
    r"nuanced emotional feedback loops)", re.I)

# Demotion factors (multiplicative). Conservative; the floor guarantees a demoted
# cocoon is never driven to ~0 (it stays recallable — never-erase).
_W_PARROT = 0.5
_W_META = 0.7
_W_BOILERPLATE = 0.7
_FLOOR = 0.2


@dataclass
class Authority:
    """A cocoon's trust weight and why. weight ∈ [_FLOOR, 1.0]."""
    weight: float
    flags: List[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.flags


def authority(cocoon: dict) -> Authority:
    """Trust weight for one cocoon. DEMOTION-ONLY (≤ 1.0), never erases.

    `cocoon` is a dict with at least 'adapter' and 'response'. A clean cocoon
    returns weight 1.0 and no flags; known-bad patterns multiply it down."""
    adapter = cocoon.get("adapter") or ""
    resp = cocoon.get("response") or ""
    w = 1.0
    flags: List[str] = []
    if adapter in PARROT_ADAPTERS:
        w *= _W_PARROT
        flags.append("parroter")
    if _META_RECALL_RE.search(resp):
        w *= _W_META
        flags.append("meta-recall")
    if _BOILERPLATE_RE.search(resp):
        w *= _W_BOILERPLATE
        flags.append("boilerplate")
    return Authority(weight=max(_FLOOR, w), flags=flags)


def is_low_authority(cocoon: dict, threshold: float = 0.6) -> bool:
    """True if a cocoon is quality-suspect — for FILTERING self-diagnostics so
    pollution doesn't skew her self-model. Threshold 0.6 catches any single
    demotion (parrot 0.5, meta 0.7×… once combined) without touching clean ones."""
    return authority(cocoon).weight < threshold
