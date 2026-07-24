"""Tests for CocoonSelfTrainer — self-learning from first-hand data, drift-guarded.

The load-bearing tests are the GUARDS: it must refuse degenerate data (all one
class, too few examples) and report why, instead of "learning" garbage. That
refusal is the whole safety of the idea.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.cocoon_self_trainer import CocoonSelfTrainer, cocoon_label
from reasoning_forge.sentiment_analyzer import _HAS_SKLEARN
import pytest


def _cocoon(text, emotion=None, valence=None):
    c = {"user_query": text}
    if emotion is not None:
        c["emotional_classification"] = emotion
    if valence is not None:
        c["emotional_valence"] = valence
    return c


# ── Label extraction: only from measured emotional signals ───────────────────

def test_label_from_emotion_category():
    assert cocoon_label(_cocoon("a good day", emotion="JOY")) == ("a good day", 1)
    assert cocoon_label(_cocoon("a hard day", emotion="grief")) == ("a hard day", 0)

def test_label_from_valence():
    assert cocoon_label(_cocoon("nice", valence=0.6))[1] == 1
    assert cocoon_label(_cocoon("bad", valence=-0.6))[1] == 0

def test_neutral_valence_skipped():
    assert cocoon_label(_cocoon("meh", valence=0.0)) is None

def test_unknown_emotion_skipped():
    assert cocoon_label(_cocoon("hmm", emotion="MYSTERY")) is None


# ── THE GUARDS: refuse degenerate data ───────────────────────────────────────

def test_refuses_single_class_data():
    # The real cocoon situation: all positive. Must REFUSE, not "learn".
    trainer = CocoonSelfTrainer(min_examples=5)
    all_positive = [_cocoon(f"good thing {i}", emotion="AWE") for i in range(30)]
    report, shadow = trainer.train_shadow(cocoons=all_positive)
    assert report.trained is False
    assert shadow is None
    assert "single-class" in report.reason

def test_refuses_too_few_examples():
    trainer = CocoonSelfTrainer(min_examples=20)
    tiny = [_cocoon("good", emotion="JOY"), _cocoon("bad", emotion="anger")]
    report, shadow = trainer.train_shadow(cocoons=tiny)
    assert report.trained is False
    assert "too few" in report.reason

def test_refuses_severe_imbalance():
    trainer = CocoonSelfTrainer(min_examples=10, min_minority_frac=0.2)
    skewed = [_cocoon(f"g{i}", emotion="HOPE") for i in range(19)] + [_cocoon("b", emotion="fear")]
    report, shadow = trainer.train_shadow(cocoons=skewed)
    assert report.trained is False
    assert "imbalance" in report.reason


# ── Healthy data: it trains a SHADOW model (nothing live) ────────────────────

@pytest.mark.skipif(not _HAS_SKLEARN, reason="sklearn not installed")
def test_trains_on_balanced_data():
    trainer = CocoonSelfTrainer(min_examples=10, min_minority_frac=0.2)
    balanced = ([_cocoon(f"wonderful moment {i}", emotion="JOY") for i in range(10)] +
                [_cocoon(f"painful moment {i}", emotion="sadness") for i in range(10)])
    report, shadow = trainer.train_shadow(cocoons=balanced)
    assert report.trained is True
    assert report.positive == 10 and report.negative == 10
    assert shadow is not None
    # the shadow model actually learned -> contributes to its ensemble
    assert "adaptive" in shadow.analyze("wonderful moment").available


# ── Shadow logging ───────────────────────────────────────────────────────────

def test_observe_writes_shadow(tmp_path):
    import json
    trainer = CocoonSelfTrainer()
    report, _ = trainer.train_shadow(cocoons=[_cocoon("x", emotion="JOY")])
    p = tmp_path / "st.jsonl"
    trainer.observe(report, path=p)
    rec = json.loads(p.read_text(encoding="utf-8").strip())
    assert rec["applied"] is False
    assert rec["mode"] == "shadow"


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call(["pytest", "-q", __file__]))
