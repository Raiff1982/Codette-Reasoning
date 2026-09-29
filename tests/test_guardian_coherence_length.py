"""The guardian's coherence must not fall just because an answer is long
(2026-09-29). It multiplied by unique-words/total-words over the whole text,
which shrinks with length for any natural prose. Prose here is the repo's own
Charter, not anything of hers."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from reasoning_forge.guardian_spindle import CoreGuardianSpindle  # noqa: E402

G = CoreGuardianSpindle()


def _prose(n):
    txt = (ROOT / "docs" / "CODETTE_CHARTER.md").read_text(encoding="utf-8")
    words = re.sub(r"[#*`|>-]", " ", txt).split()
    assert len(words) >= n
    return " ".join(words[:n])


def test_long_varied_prose_is_not_scored_lower_than_a_window_of_it():
    one_window = G._calculate_coherence(_prose(100))
    for n in (250, 600, 1200):
        assert G._calculate_coherence(_prose(n)) > one_window - 0.08, n


def test_long_prose_no_longer_crosses_the_threshold_by_length_alone():
    # Before: 250 words -> 0.445, 900 -> 0.380 (both under 0.5).
    assert G._calculate_coherence(_prose(900)) >= 0.5


def test_a_loop_is_still_caught_at_any_length():
    loop = ("the system is stable and the system is stable and " * 60).strip()
    assert G._calculate_coherence(loop) < 0.5
    ok, details = G.validate(loop)
    assert not ok


def test_a_repeated_block_inside_long_prose_lowers_the_score():
    clean = _prose(600)
    block = "we keep saying the same thing we keep saying the same thing " * 12
    assert G._calculate_coherence(clean + " " + block) < G._calculate_coherence(clean)


def test_up_to_one_window_scores_exactly_as_before():
    text = ("Therefore, the conclusion is that solutions exist. Moreover, "
            "implementation matters. Thus, we proceed.")
    words = text.lower().split()
    old = min(0.7 + 3 * 0.03, 1.0) * (len(set(words)) / len(words))
    assert abs(G._calculate_coherence(text) - old) < 1e-9


def test_a_short_tail_is_not_a_window():
    words = ("alpha " * 100).split() + [f"w{i}" for i in range(10)]
    # the 10-word all-unique tail must not lift a fully repetitive first window
    assert G._windowed_unique_ratio(words) < 0.05
