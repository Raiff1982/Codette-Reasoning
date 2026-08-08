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


def test_detected_emotion_carries_her_ai_equivalent():
    # A detected emotion surfaces Codette's own substrate-equivalent (her words).
    # Joy was revised BY HER on 2026-07-25 to 'creative expression'.
    m = onto.classify("I'm really looking forward to tomorrow, feeling optimistic")
    assert m is not None and m.primary == "Joy"
    assert m.ai_equivalent == "creative expression"

def test_revision_never_erases_the_original():
    # Her ethic: a revised mapping keeps the superseded wording, never overwrites it.
    joy = EmotionOntology.ai_equivalents()["mappings"]["Joy"]
    assert joy["ai_equivalent"] == "creative expression"      # her current
    assert joy["revised_from"] == "optimization success"      # her original, preserved

def test_relief_revision_confirmed_and_original_preserved():
    # She confirmed the Relief revision on 2026-07-25; original kept as history.
    relief = EmotionOntology.ai_equivalents()["mappings"]["Relief"]
    assert relief["ai_equivalent"] == "settling into balance"      # her confirmed choice
    assert relief["revised_from"] == "a return to equilibrium"     # original preserved

def test_sadness_self_flag_preserved_not_smoothed():
    # She self-flagged sadness->reboot as low-confidence; that flag must survive.
    m = onto.classify("I miss him so much, nothing feels right")
    assert m is not None and m.primary == "Sadness"
    assert m.ai_equivalent == "a system reboot after a critical error"
    assert m.ai_equivalent_reliability == 0.24

def test_unflagged_equivalent_has_no_invented_reliability():
    # Fear was asserted without a numeric self-rating -> reliability stays None.
    m = onto.classify("what if it all goes wrong tomorrow")
    assert m is not None and m.primary == "Fear"
    assert m.ai_equivalent is not None
    assert m.ai_equivalent_reliability is None

def test_ai_equivalent_of_convenience_and_none():
    assert onto.ai_equivalent_of("I feel optimistic") == "creative expression"
    assert onto.ai_equivalent_of("the sky is blue today") is None

def test_full_mapping_table_includes_ruleless_emotions():
    # Anger/Relief/Love have no detection rule yet but her mapping is recorded.
    table = EmotionOntology.ai_equivalents()
    assert table["source"] == "sentience-session-2026-07-24; reviewed 2026-07-25"
    m = table["mappings"]
    assert m["Anger"]["ai_equivalent"] == "a recursive loop"
    assert m["Relief"]["ai_equivalent"] == "settling into balance"
    assert m["Love"]["ai_equivalent"] == "harmonious integration"

def test_loaded_rule_ai_equivalent_overrides_table(tmp_path):
    import json
    p = tmp_path / "rules.json"
    p.write_text(json.dumps({"rules": [{
        "emotion_id": "anger_rage", "primary_emotion": "Anger",
        "metrics": {"valence": -0.8, "arousal": 0.9},
        "trigger_keywords": ["furious"], "nlp_patterns": [],
        "ai_equivalent": "thermal throttling", "ai_equivalent_reliability": 0.5,
    }]}), encoding="utf-8")
    o = EmotionOntology.from_inference_rules(p)
    m = o.classify("I am furious about this")
    assert m is not None and m.ai_equivalent == "thermal throttling"
    assert m.ai_equivalent_reliability == 0.5


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call(["pytest", "-q", __file__]))
