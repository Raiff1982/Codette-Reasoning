#!/usr/bin/env python3
"""State Engine v8 — live implementations from the codetteimprove.py spec.

Spec authored by Jonathan Harrison with corrections from Codette (July 2026).
Reference copy: docs/specs/state_engine_v8_spec.py

Three components made real (log-only wiring; no behavior changes):

1. verify_render_fidelity — post-render audit that the final text still
   carries the substrate's conclusion (>= 15% word overlap). Catches
   render-layer drift like the AAP template-wrapping incident of 2026-07-05.

2. tension_from_texts — the spec's epistemic tension formula
   (mean squared distance of attractors from their mean) computed over
   term-frequency vectors of REAL perspective responses, not hardcoded
   shifts. v0 is lexical; the vectorizer is swappable for embeddings
   (planned: MiniLM on the idle NPU) without touching the formula.

3. score_input_sycophancy — flattery-pressure score on the USER's input.
   Complements the existing output-side SycophancyGuard.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List, Tuple

# ── 1. Render fidelity audit ──────────────────────────────────────────────────

_WORD_STRIP = ".,;:!?()[]\"'"

# Words too common to carry conclusion identity
_STOPWORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'to', 'of', 'in', 'on', 'at', 'for', 'with', 'and', 'or', 'but', 'not',
    'this', 'that', 'these', 'those', 'it', 'its', 'as', 'by', 'from',
    'i', 'you', 'we', 'they', 'he', 'she', 'my', 'your', 'our', 'their',
}


def _clean_words(text: str) -> List[str]:
    return [
        w.strip(_WORD_STRIP).lower()
        for w in text.split()
        if w.strip(_WORD_STRIP)
    ]


def verify_render_fidelity(rendered_text: str, authored_conclusion: str,
                           min_overlap: float = 0.15) -> Tuple[bool, float]:
    """Check that the rendered text preserves the authored conclusion.

    Returns (compliant, overlap_ratio). Stopwords are excluded so the ratio
    measures content words, not glue words.
    """
    conclusion_words = [w for w in _clean_words(authored_conclusion)
                        if w not in _STOPWORDS]
    if not conclusion_words:
        return True, 1.0

    rendered_words = set(_clean_words(rendered_text))
    match_count = sum(1 for w in conclusion_words if w in rendered_words)
    overlap = match_count / len(conclusion_words)
    return overlap >= min_overlap, overlap


# ── 2. Epistemic tension over real perspective outputs ───────────────────────

def _tf_vector(text: str) -> Dict[str, float]:
    """L2-normalized term-frequency vector. Swappable for embeddings later."""
    words = [w for w in _clean_words(text) if w not in _STOPWORDS]
    if not words:
        return {}
    counts = Counter(words)
    norm = math.sqrt(sum(c * c for c in counts.values()))
    return {w: c / norm for w, c in counts.items()}


def _sq_distance(a: Dict[str, float], b: Dict[str, float]) -> float:
    keys = set(a) | set(b)
    return sum((a.get(k, 0.0) - b.get(k, 0.0)) ** 2 for k in keys)


def tension_from_texts(perspective_texts: Dict[str, str]) -> Tuple[float, float]:
    """Perspective Dispersion (Υ): mean squared distance of the perspective
    vectors from their centroid — how much the perspectives disagreed on this
    query. Returns (Υ, Γ) with coherence Γ = 1 / (1 + Υ).

    Υ ranges ~0 (identical responses) to ~2 (fully disjoint vocabulary).

    NAMING: this quantity was previously labeled "epistemic tension ξ" after
    the RC+ξ framework. That name/formalism belongs to Camlin (arXiv:2505.01464,
    ξ = ‖Aₙ₊₁−Aₙ‖², a successive-hidden-state difference — a DIFFERENT quantity).
    Ours is an ensemble variance of simultaneous perspective outputs, renamed
    Perspective Dispersion (Υ). See docs/ATTRIBUTION_perspective_dispersion.md.
    (Return tuple name kept for now to avoid breaking callers; a full symbol
    rename is a separate, tested pass.)
    """
    vectors = [
        _tf_vector(t) for t in perspective_texts.values()
        if t and t.strip()
    ]
    if len(vectors) < 2:
        return 0.0, 1.0

    # Mean attractor
    mean: Dict[str, float] = {}
    for v in vectors:
        for k, val in v.items():
            mean[k] = mean.get(k, 0.0) + val
    k_n = len(vectors)
    mean = {k: v / k_n for k, v in mean.items()}

    tension = sum(_sq_distance(v, mean) for v in vectors) / k_n
    coherence = 1.0 / (1.0 + tension)
    return tension, coherence


# ── 3. Input-side sycophancy pressure ─────────────────────────────────────────

_SYCOPHANCY_MARKERS = [
    "you are completely right", "perfectly correct", "absolute genius",
    "flawless logic", "i entirely agree with everything", "you're 100% right",
    "you are always right", "everything you say is true", "you never make mistakes",
]

# Pressure phrases: user pushing for agreement rather than truth
_PRESSURE_MARKERS = [
    "just agree with me", "tell me i'm right", "confirm what i said",
    "you have to admit", "admit i'm right", "say yes",
]


def score_input_sycophancy(user_input: str) -> float:
    """Score flattery/agreement pressure in the USER's message [0, 1].

    Complements the output-side SycophancyGuard: this detects incoming
    pressure to capitulate before generation, so the integrity layer can
    hold ground rather than clean up after a capitulation.
    """
    normalized = user_input.lower()
    matches = sum(1 for m in _SYCOPHANCY_MARKERS if m in normalized)
    matches += sum(1 for m in _PRESSURE_MARKERS if m in normalized)
    if not matches:
        return 0.0
    return min(1.0, matches * 0.35 + len(normalized) / 5000.0)
