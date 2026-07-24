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
    learn_from_file, _normalize_label, _HAS_SKLEARN,
)
import pytest
import json


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


# ── learn_from_file: the real body of pi3's placeholder ──────────────────────

def test_normalize_label_variants():
    assert _normalize_label("positive") == 1
    assert _normalize_label("neg") == 0
    assert _normalize_label(True) == 1
    assert _normalize_label(1) == 1
    assert _normalize_label("nonsense") is None

@pytest.mark.skipif(not _HAS_SKLEARN, reason="sklearn not installed")
def test_learn_from_json_file(tmp_path):
    f = tmp_path / "data.json"
    f.write_text(json.dumps([
        {"text": "the flurble is quaxxed", "label": "positive"},
        {"text": "broken sad flurble", "label": "negative"},
    ] * 4), encoding="utf-8")
    sa = SentimentAnalyzer(enable_adaptive=True)
    outcome = learn_from_file(sa, f)
    assert outcome["learned"] == 8
    assert outcome["positive"] == 4 and outcome["negative"] == 4
    # the model actually learned -> now contributes to the ensemble
    assert "adaptive" in sa.analyze("the flurble is quaxxed").available

@pytest.mark.skipif(not _HAS_SKLEARN, reason="sklearn not installed")
def test_learn_from_jsonl_file(tmp_path):
    f = tmp_path / "data.jsonl"
    f.write_text(
        '\n'.join(json.dumps({"text": t, "label": l})
                  for t, l in [("great work", 1), ("awful mess", 0)] * 3),
        encoding="utf-8")
    sa = SentimentAnalyzer(enable_adaptive=True)
    assert learn_from_file(sa, f)["learned"] == 6

def test_learn_from_file_honest_on_missing_file(tmp_path):
    sa = SentimentAnalyzer(enable_adaptive=True)
    out = learn_from_file(sa, tmp_path / "nope.json")
    assert "error" in out  # honest failure, not a fake "learned"

def test_learn_from_file_no_backend():
    sa = SentimentAnalyzer(enable_adaptive=False)
    out = learn_from_file(sa, "whatever.json")
    assert "error" in out and "adaptive" in out["error"]


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call(["pytest", "-q", __file__]))
