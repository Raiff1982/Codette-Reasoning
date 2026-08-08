"""Tests for EmotionOntology — the consumer of Jonathan's Emotion Ontology.

Honesty invariant: no rule match -> None. It never guesses an emotion it has no
evidence for, and it reports which cues fired (transparency).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.emotion_ontology import EmotionOntology, EmotionMatch

onto = EmotionOntology()


def test_detects_hope_positive_valence():
    m = onto.classify("I'm really looking forward to tomorrow, feeling optimistic")
    assert m is not None
    assert m.emotion_id == "joy_hopeful"
    assert m.valence > 0

def test_detects_grief_negative_valence():
    m = onto.classify("I miss him so much, nothing feels right")
    assert m is not None
    assert m.emotion_id == "sadness_grief"
    assert m.valence < 0

def test_detects_anxiety_pattern():
    m = onto.classify("what if it all goes wrong tomorrow")
    assert m is not None
    assert m.emotion_id == "fear_anxiety"
    assert m.valence < 0
    assert m.arousal > 0.5   # anxiety is high-arousal

def test_no_match_returns_none_not_a_guess():
    # Neutral text with no emotional cue must return None, not a fabricated emotion.
    assert onto.classify("the meeting is scheduled for three o'clock") is None
    assert onto.classify("") is None

def test_match_reports_cues():
    m = onto.classify("looking forward to the bright side")
    assert m is not None
    assert len(m.matched_on) >= 1   # transparency: which cues fired

def test_valence_of_convenience():
    assert onto.valence_of("I feel optimistic") > 0
    assert onto.valence_of("the sky is blue today") is None

def test_from_inference_rules_falls_back_to_seed(tmp_path):
    # Missing file -> seed, never empty/crash.
    o = EmotionOntology.from_inference_rules(tmp_path / "nope.json")
    assert o.classify("I'm so optimistic") is not None

def test_from_inference_rules_loads_real_format(tmp_path):
    import json
    p = tmp_path / "rules.json"
    p.write_text(json.dumps({"rules": [{
        "emotion_id": "anger_rage", "primary_emotion": "Anger",
        "metrics": {"valence": -0.8, "arousal": 0.9},
        "trigger_keywords": ["furious", "livid"], "nlp_patterns": ["i am so angry *"],
    }]}), encoding="utf-8")
    o = EmotionOntology.from_inference_rules(p)
    m = o.classify("I am furious about this")
    assert m is not None and m.emotion_id == "anger_rage" and m.valence < 0


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call(["pytest", "-q", __file__]))
