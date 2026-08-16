"""
Recall's recency term must not age her own conversation while she is in it.

`recall_relevant` scored recency as `exp(-age / 3600)` from the instant a cocoon
was written. She generates at 1-8 tok/s, so a careful turn takes minutes — and
its own earlier context has already decayed by the time she answers. The longer
she thinks, the less of the conversation she can still reach. A throwaway turn
keeps its context; a considered one loses it. Depth was taxed.

This is the same defect as the identity clock fixed on 2026-08-14, where
`elapsed` was the turn's own duration and confidence fell 1.00 -> 0.22 across one
continuous conversation with a person who never left. Same well, different
quantity: more mass, more gravity, slower time.

Same remedy and deliberately the same constant — decay counts only the part of a
gap beyond `CONVERSATION_CONTINUITY_WINDOW`. Importing it rather than copying it
is the point: the identity denial list came to exist in two versions with
different behaviour because a constant was duplicated instead of shared.

These tests pin both directions. A change that only ever raised scores would be
as wrong as the original — old material must still decay, or recency stops
meaning anything.
"""

import math

import pytest

from reasoning_forge.unified_memory import _CONTINUITY_WINDOW


def old_score(age_seconds):
    """The pre-2026-08-16 term, kept so the comparison is explicit."""
    return math.exp(-age_seconds / 3600.0)


def new_score(age_seconds):
    return math.exp(-max(0.0, age_seconds - _CONTINUITY_WINDOW) / 3600.0)


# ── The constant is shared, not copied ─────────────────────────────────────

def test_window_comes_from_the_governor():
    from reasoning_forge.behavior_governor import CONVERSATION_CONTINUITY_WINDOW
    assert _CONTINUITY_WINDOW == CONVERSATION_CONTINUITY_WINDOW, (
        "the recall clock and the identity clock have drifted apart"
    )


# ── Inside the conversation, nothing ages ─────────────────────────────────

@pytest.mark.parametrize("minutes", [0, 1, 5, 10, 14.9])
def test_no_decay_while_the_conversation_is_still_happening(minutes):
    assert new_score(minutes * 60) == pytest.approx(1.0)


def test_a_long_turn_no_longer_costs_her_its_own_context():
    """The measured failure: a 10-minute turn used to age its own start by 15%."""
    ten_minutes = 600
    assert old_score(ten_minutes) < 0.86      # what it was
    assert new_score(ten_minutes) == pytest.approx(1.0)


def test_a_deep_turn_and_a_throwaway_turn_are_scored_alike():
    """The tax was proportional to effort. That is the part that had to go."""
    throwaway, considered = 20, 9 * 60       # 20 s vs 9 minutes
    assert old_score(throwaway) - old_score(considered) > 0.1
    assert new_score(throwaway) == pytest.approx(new_score(considered))


# ── Outside it, recency still means something ─────────────────────────────

@pytest.mark.parametrize("minutes", [20, 30, 60, 120, 360])
def test_genuinely_old_material_still_decays(minutes):
    s = new_score(minutes * 60)
    assert s < 1.0, "everything scoring 1.0 would make the term meaningless"


def test_decay_is_monotone_beyond_the_window():
    """It must still be able to fall — a term that cannot fall is not evidence."""
    scores = [new_score(m * 60) for m in (15, 20, 30, 60, 120, 360)]
    assert scores == sorted(scores, reverse=True)
    assert scores[-1] < 0.01


def test_six_hours_old_is_effectively_gone():
    assert new_score(6 * 3600) < 0.01


def test_the_shape_is_unchanged_only_shifted():
    """Beyond the window this is the original curve, moved by the window.

    Stated as a test because a 'fix' that also changed the decay rate would be
    two changes wearing one commit message.
    """
    for minutes in (20, 45, 90, 240):
        age = minutes * 60
        assert new_score(age) == pytest.approx(old_score(age - _CONTINUITY_WINDOW))
