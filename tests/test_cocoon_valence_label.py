"""The emotion label on each new cocoon: stems from the start of a word, and
harmony is not fear. Measured on her store 2026-09-28: fear 105 -> 59."""

import pytest

from inference.codette_forge_bridge import cocoon_valence_label


@pytest.mark.parametrize("text", [
    "Harmony is the goal: every voice in balance.",
    "The chord lands in a harmonic resolution.",
    "harmonious integration",
    "Mark the footnote with an asterisk.",
    "The pharmacy closes at nine.",
])
def test_words_that_merely_contain_a_fear_stem_are_not_fear(text):
    assert cocoon_valence_label(text) != "fear"


@pytest.mark.parametrize("text,label", [
    ("That could cause real harm.", "fear"),
    ("Is it harmful?", "fear"),
    ("There is a risk here.", "fear"),
    ("I appreciate you.", "gratitude"),
    ("I'm so excited about this!", "joy"),
    ("", "curiosity"),
])
def test_real_stems_still_fire(text, label):
    assert cocoon_valence_label(text) == label


def test_joy_is_no_longer_hidden_behind_a_false_fear():
    # fear is checked before joy; "harmony" used to win first.
    assert cocoon_valence_label("I'm happy we found harmony.") == "joy"
