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
# A response that reproduces its own query is the least ambiguous evidence of
# parroting there is — structural, not a learned signature — so it demotes
# hardest. Added 2026-07-30: cocoons whose response was character-for-character
# their own query scored 1.0/clean/unflagged, were recalled at rank 1-3, and were
# shown to her under the heading "YOUR PAST REASONING" — teaching the echo the
# parrot detector could not see.
_W_ECHO = 0.4
_FLOOR = 0.2

# Below this many words, matching text is ordinary rather than evidence: short
# confirmations and one-line answers legitimately restate the question.
_ECHO_MIN_WORDS = 8
_ECHO_SIMILARITY = 0.9

# A response that wraps the question in a template and hands it back. Added
# 2026-08-12: `_is_verbatim_echo` requires the echo to BE most of the response
# (`len(r_words) <= len(q_words) * 1.5`), so it flagged 6 of 2,409 live cocoons
# and missed the actual live signature entirely — an opener that quotes the whole
# query verbatim and then continues for another eighty words.
#
# These are machine artifacts, not prose, which is why they can be matched at the
# start of the response with confidence:
#
#     Analysis of *'<the entire query>'* across perspectives: …
#     *'<the entire query>'* sits in high-tension epistemic space …
#     You received this question: "<the entire query>" …
#
# Measured over 2,409 live cocoons carrying both query and response: 310 (12.9%)
# open this way, and 307 of those 310 literally contain the query's first 40
# characters, so the wrapper and the echo travel together.
#
# WHAT WAS DELIBERATELY NOT ADDED: a proportional rule ("the response reproduces
# ≥80% of the query as a contiguous run"). It was implemented and measured first:
# it fires on 207 cocoons, and inspection shows it cannot separate parroting from
# ordinary good prose — "What are the main causes of the 2008 financial crisis?"
# answered with "The main causes of the 2008 financial crisis were …" is a normal
# English sentence, not an echo. A signal that demotes correct answers is worse
# than the gap it closes. Precision over recall here; err toward 1.0.
_QUERY_TEMPLATE_RE = re.compile(
    r"^\s*(?:\*+\s*)?(?:"
    r"Analysis of\s*\*?['\"‘“]"          # Analysis of *'…'
    r"|You received this (?:question|query)"        # You received this question: "…"
    r"|The (?:question|query) (?:is|was)\s*[:\"'‘“]"
    r"|\*['\"‘“]"                         # a response opening on *'…'
    r")", re.I)

# Weaker than a full echo: the response does go on to say something. Demotes,
# but not as hard as handing the query straight back.
_W_QUERY_TEMPLATE = 0.6


def is_query_restatement_template(query: str, response: str) -> bool:
    """Whether a response opens by wrapping the query in a template.

    Requires BOTH the wrapper and the query actually appearing in the response,
    so a message that merely begins "The question is whether…" of its own accord
    is not flagged. Shared with `inference/self_correction.py` so the two echo
    detectors cannot drift apart the way the identity patterns did.
    """
    if not query or not response:
        return False
    if not _QUERY_TEMPLATE_RE.search(response):
        return False
    q_words = _norm_words(query)
    if len(q_words) < _ECHO_MIN_WORDS:
        return False
    # The wrapper must be wrapping THIS query: a contiguous run of its opening
    # words has to appear in the response.
    probe = " ".join(q_words[:8])
    return probe in " ".join(_norm_words(response))


def _norm_words(text: str) -> List[str]:
    return "".join(
        c if c.isalnum() or c.isspace() else " " for c in (text or "").lower()
    ).split()


def _is_verbatim_echo(query: str, response: str) -> bool:
    """Whether a response just hands the query back.

    Requires a real amount of text — a short answer restating the question is
    normal conversation, not evidence. Absent a query, returns False: an
    unknown must not be scored as a fault.
    """
    q_words, r_words = _norm_words(query), _norm_words(response)
    if len(q_words) < _ECHO_MIN_WORDS or len(r_words) < _ECHO_MIN_WORDS:
        return False
    if q_words == r_words:
        return True
    q_set, r_set = set(q_words), set(r_words)
    overlap = len(q_set & r_set) / (len(q_set) or 1)
    return overlap >= _ECHO_SIMILARITY and len(r_words) <= len(q_words) * 1.5


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
    query = cocoon.get("query") or ""
    w = 1.0
    flags: List[str] = []
    if adapter in PARROT_ADAPTERS:
        w *= _W_PARROT
        flags.append("parroter")
    if _is_verbatim_echo(query, resp):
        w *= _W_ECHO
        flags.append("verbatim-echo")
    elif is_query_restatement_template(query, resp):
        # `elif`: a full echo already demotes harder. Don't stack two flags for
        # one behaviour.
        w *= _W_QUERY_TEMPLATE
        flags.append("query-restatement-template")
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
