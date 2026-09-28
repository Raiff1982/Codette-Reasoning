#!/usr/bin/env python3
"""Semantic grounding — evidential support for QUALITATIVE thoughts.

The symbolic grounder (grounding.py) verifies arithmetic/logical claims and
returns TRUTH: VERIFIED means the claim is true. But ~100% of what Codette
actually forges is qualitative ("compression-resonance bridging enables emergent
boundary walking"). sympy/z3 reach none of it, so the bridge honestly reports
those thoughts UNGROUNDED. This module gives the bridge something honest to say
about them WITHOUT overclaiming.

THE EPISTEMIC LINE (this is the whole point, and it must not blur):
  Symbolic grounding  -> TRUTH.            "2+2=4" is VERIFIED = true.
  Semantic grounding  -> EVIDENTIAL SUPPORT. "this thought is consistent with
                         what she has actually recorded" — NOT "true".
  A qualitative thought that echoes her stored evidence is SUPPORTED_BY_EVIDENCE.
  It is NEVER "verified". Conflating support with truth would be the exact lie
  this project exists to prevent.

Design invariants (inherited from grounding.py, deliberately):
  1. Never asserts more than it checked. No relevant evidence -> UNADDRESSED,
     never SUPPORTED-by-default. Evidence support is reported AS support, with
     the shared terms shown, never dressed up as proof.
  2. Pure and side-effect-free. ground_claim() computes over evidence handed to
     it; it does not touch the DB, log, or gate. Retrieval (the side-effectful
     part) and shadow logging are separate, opt-in wrappers.
  3. Degrades honestly and NEVER FALSE-FLAGS. Offline lexical overlap only (no
     model — 8GB UMA, models off by default). Weak signal -> UNADDRESSED, not a
     guess. This preserves grounding's prized property: it stays silent rather
     than flag a thought it cannot actually speak to.

DEFERRED (next phase, on purpose): CONTRADICTED_BY_EVIDENCE. Detecting that
stored evidence *conflicts* with a claim needs more than lexical negation, which
false-flags too readily (e.g. intimate/"love" turns). Emitting a hard
"contradicted" from a weak cue would break invariant 3. Contradiction detection
waits for a real semantic/NLI signal, the way z3 was a later phase for symbolic
grounding. See docs/NEUROSYMBOLIC_GROUNDING.md.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence


class SemanticVerdict(str, Enum):
    SUPPORTED_BY_EVIDENCE = "supported_by_evidence"  # consistent with stored evidence — NOT truth
    UNADDRESSED = "unaddressed"                       # no relevant evidence — honest silence


# Content-word extraction. Semantic overlap must be over MEANINGFUL words, so a
# shared "the"/"is" can never manufacture support. Mirrors the stop set the
# memory layer already uses for FTS querying.
_STOP = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "could", "should", "can", "may", "might", "must", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "and", "but", "or", "if",
    "it", "its", "this", "that", "these", "those", "i", "me", "my", "we",
    "you", "your", "he", "she", "they", "them", "their", "what", "how",
    "why", "when", "where", "who", "about", "just", "not", "no", "so",
    "very", "really", "also", "too", "up", "out", "into", "than", "then",
    "there", "here", "which", "while", "such", "each", "any", "all", "both",
}

# Minimum shared content words for support (one shared word is coincidence, not
# grounding) and minimum overlap fraction of the claim's own content words.
_MIN_SHARED = 2
_MIN_OVERLAP = 0.5
# A claim with fewer content words than this cannot be grounded semantically
# without the score being dominated by noise — reported UNADDRESSED, honestly.
_MIN_CLAIM_TERMS = 2


@dataclass
class EvidenceItem:
    """One piece of retrieved evidence and how it overlapped the claim."""
    source_id: str
    snippet: str
    shared_terms: List[str]
    overlap: float          # |claim ∩ evidence| / |claim terms|, 0..1

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SemanticGrounding:
    """Outcome of grounding one qualitative claim against her evidence base."""
    claim: str
    verdict: SemanticVerdict
    support_score: float            # 0..1, best overlap found (0 when UNADDRESSED)
    detail: str                     # human-readable reason, always carries the epistemic caveat
    evidence: List[dict] = field(default_factory=list)   # supporting items (transparency)
    method: str = "lexical_overlap"
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["verdict"] = self.verdict.value
        return d


def _content_terms(text: str) -> List[str]:
    """Lowercased content words (>2 chars, not stopwords), order-preserving unique."""
    seen: Dict[str, None] = {}
    for raw in re.findall(r"[A-Za-z][A-Za-z\-']+", (text or "").lower()):
        w = raw.strip("-'")
        if len(w) > 2 and w not in _STOP and w not in seen:
            seen[w] = None
    return list(seen.keys())


def _evidence_text(item) -> tuple:
    """Extract (source_id, text) from an evidence item (dict cocoon or str)."""
    if isinstance(item, str):
        return "", item
    if isinstance(item, dict):
        sid = str(item.get("id", item.get("source_id", "")))
        # A cocoon carries its content in 'response' (and 'query'); fall back to str.
        text = item.get("response") or item.get("text") or item.get("query") or ""
        return sid, str(text)
    return "", str(item)


def ground_claim(claim: str, evidence: Sequence) -> SemanticGrounding:
    """Ground ONE qualitative claim against already-retrieved evidence. Pure.

    `evidence` is a sequence of cocoon dicts (with 'response'/'query') or plain
    strings — whatever the caller retrieved. This function does no retrieval,
    no logging, no gating: it scores lexical overlap and returns an HONEST,
    support-only verdict. No evidence, thin claim, or weak overlap -> UNADDRESSED.
    """
    claim = (claim or "").strip()
    if not claim:
        return SemanticGrounding(claim, SemanticVerdict.UNADDRESSED, 0.0,
                                 "empty claim — nothing to ground")

    claim_terms = _content_terms(claim)
    if len(claim_terms) < _MIN_CLAIM_TERMS:
        return SemanticGrounding(
            claim, SemanticVerdict.UNADDRESSED, 0.0,
            "claim has too few content words to ground semantically (honest UNADDRESSED, not support)",
        )
    claim_set = set(claim_terms)

    supporting: List[EvidenceItem] = []
    best = 0.0
    for item in evidence or []:
        sid, text = _evidence_text(item)
        ev_terms = set(_content_terms(text))
        shared = [t for t in claim_terms if t in ev_terms]   # ordered by claim
        overlap = len(shared) / len(claim_set)
        if len(shared) >= _MIN_SHARED and overlap >= _MIN_OVERLAP:
            supporting.append(EvidenceItem(
                source_id=sid, snippet=_snippet(text), shared_terms=shared, overlap=round(overlap, 3),
            ))
        best = max(best, overlap if len(shared) >= _MIN_SHARED else 0.0)

    if supporting:
        supporting.sort(key=lambda e: e.overlap, reverse=True)
        n = len(supporting)
        return SemanticGrounding(
            claim, SemanticVerdict.SUPPORTED_BY_EVIDENCE, round(best, 3),
            (f"consistent with {n} stored memor{'y' if n == 1 else 'ies'} "
             f"(shared terms: {', '.join(supporting[0].shared_terms)}). "
             f"Evidence support is NOT proof of truth — only that this thought "
             f"echoes what she has recorded."),
            evidence=[e.to_dict() for e in supporting],
        )

    return SemanticGrounding(
        claim, SemanticVerdict.UNADDRESSED, round(best, 3),
        "no stored evidence overlaps this claim enough to support it — honest "
        "silence, not a pass and not a contradiction",
    )


def ground_claim_via_memory(
    claim: str,
    memory,
    *,
    max_results: int = 5,
    min_importance: int = 0,
) -> SemanticGrounding:
    """Retrieve evidence from a UnifiedMemory-like store, then ground. Retrieval
    is the only side effect; scoring stays pure via ground_claim().

    `memory` need only expose recall_relevant(query, max_results=...). Any
    retrieval failure degrades to UNADDRESSED (never invents support)."""
    try:
        evidence = memory.recall_relevant(claim, max_results=max_results, min_importance=min_importance)
    except Exception:
        evidence = []
    return ground_claim(claim, evidence or [])


def _snippet(text: str, width: int = 160) -> str:
    t = " ".join((text or "").split())
    return t if len(t) <= width else t[: width - 1] + "…"


def log_shadow(result: SemanticGrounding, path: str | Path = None) -> None:
    """Append one semantic verdict to the shadow log. SHADOW ONLY (applied: false).

    Separate from ground_claim() on purpose: grounding is pure; persistence is a
    deliberate, opt-in act. Nothing in the runtime calls this — it only observes.
    """
    path = Path(path) if path else Path(__file__).resolve().parent.parent / "data" / "grounding_shadow.jsonl"
    rec = result.to_dict()
    rec["mode"] = "shadow"
    rec["applied"] = False
    rec["record"] = "semantic_grounding"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass  # logging must never break a turn
