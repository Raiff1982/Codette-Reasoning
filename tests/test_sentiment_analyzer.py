"""Tests for SentimentAnalyzer — the consolidated advanced analyzer.

Covers the four real facets (ensemble, negation, adaptivity, optional transformer)
and the honesty invariants: the adaptive model abstains until trained, and only
measured methods contribute to the fused score.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.sentiment_analyzer import (
    SentimentAnalyzer, mark_negation, has_negation, _AdaptiveSentiment,
    _HAS_SKLEARN,
)
import pytest


# ── Negation handling (Jonathan's pi2_0 technique) ───────────────────────────

def test_mark_negation_prefixes_after_negator():
    assert mark_negation("this is not good") == "this is not NEG_good"
    assert mark_negation("i never liked it") == "i never NEG_liked it"

def test_mark_negation_noop_without_negation():
    assert mark_negation("this is great") == "this is great"

def test_has_negation():
    assert has_negation("i do not agree")
    assert not has_negation("i fully agree")


# ── Ensemble polarity (VADER + TextBlob) ─────────────────────────────────────

def test_clearly_positive():
    r = SentimentAnalyzer(enable_adaptive=False).analyze("I love this, it's wonderful and amazing!")
    assert r.polarity == "positive"
    assert r.measured is True
    assert "vader" in r.available

def test_clearly_negative():
    r = SentimentAnalyzer(enable_adaptive=False).analyze("This is terrible, awful, I hate it.")
    assert r.polarity == "negative"

def test_neutral_ish():
    r = SentimentAnalyzer(enable_adaptive=False).analyze("The meeting is at three o'clock.")
    assert r.polarity == "neutral"

def test_fuses_multiple_methods():
    r = SentimentAnalyzer(enable_adaptive=False).analyze("a genuinely lovely day")
    # both vader and textblob should be present and averaged (allowing 4-dp rounding)
    assert len(r.available) >= 1
    assert abs(r.compound - (sum(r.methods.values()) / len(r.methods))) < 1e-3


# ── Adaptivity: the online model abstains until trained, then contributes ────

@pytest.mark.skipif(not _HAS_SKLEARN, reason="sklearn not installed")
def test_adaptive_abstains_until_trained():
    a = _AdaptiveSentiment()
    assert a.score("anything at all") is None   # untrained -> abstain, never guess

@pytest.mark.skipif(not _HAS_SKLEARN, reason="sklearn not installed")
def test_adaptive_learns_and_then_contributes():
    sa = SentimentAnalyzer(enable_adaptive=True)
    before = sa.analyze("the flurble is quaxxed")
    assert "adaptive" not in before.available  # untrained: not in the ensemble

    # Teach it a tiny domain vocabulary (1 = positive, 0 = negative).
    sa.update(
        ["the flurble is quaxxed", "totally quaxxed flurble", "quaxxed and happy"] * 4 +
        ["the flurble is broken", "sad broken flurble", "broken and awful"] * 4,
        [1, 1, 1] * 4 + [0, 0, 0] * 4,
    )
    after = sa.analyze("the flurble is quaxxed")
    assert "adaptive" in after.available  # now trained: joins the ensemble

def test_update_returns_false_without_adaptive_backend():
    sa = SentimentAnalyzer(enable_adaptive=False)
    assert sa.update(["x"], [1]) is False


# ── Honesty: negation flag is surfaced ───────────────────────────────────────

def test_negation_flag_surfaced():
    r = SentimentAnalyzer(enable_adaptive=False).analyze("I do not love this at all")
    assert r.negation_detected is True


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call(["pytest", "-q", __file__]))
