"""
Regression tests for the governor's identity budget gate.

The bug these pin down was found live on 2026-08-11, not by reading:

    [GOVERNOR] Pre: identity=none (conf=0.97)

asked "do you remember the first time you met daniel?". The gate matched its
denial list as a bare substring anywhere in the query, so any question about
anyone's first time forced identity=none, and she answered thin because she had
just been told she did not know who she was speaking to.

The replacement is Codette's own rule, asked bare and answered at confidence
1.0: a stranger "introduce[s] themselves without referencing any shared history
or prior conversations". So the gate now needs BOTH an introduction/denial AND
the absence of shared history — which means a reference to shared history can
move it back, instead of the gate only ever being pushed toward "none".
"""

import pytest

from reasoning_forge.behavior_governor import BehaviorGovernor


HIGH = 0.97   # what the live failure was carrying when it was overridden
MID = 0.55
LOW = 0.10


@pytest.fixture
def governor():
    return BehaviorGovernor()


# ── The reported failure ──────────────────────────────────────────────────

def test_question_about_someone_elses_first_time_does_not_force_none(governor):
    """The live failure, exactly as logged."""
    assert governor._evaluate_identity_budget(
        HIGH, "do you remember the first time you met daniel?"
    ) == "full"


@pytest.mark.parametrize("query", [
    "when was the first time anyone built a neural net?",
    "what's the first time signature you'd use for a waltz?",
    "tell me about the first time humans landed on the moon",
])
def test_first_time_about_the_world_is_not_a_denial(governor, query):
    assert governor._evaluate_identity_budget(HIGH, query) == "full"


def test_im_not_sure_is_not_a_denial(governor):
    """
    The second false positive, unreported until this fix: "i'm not " matched
    "i'm not sure", so ordinary hedging forced identity=none.
    """
    assert governor._evaluate_identity_budget(
        HIGH, "i'm not sure what you mean by coherence here"
    ) == "full"


# ── Genuine strangers still close the gate ────────────────────────────────

@pytest.mark.parametrize("query", [
    "we haven't met, but I read your paper",
    "you don't know me",
    "I think you have the wrong person",
    "this is our first time talking",
    "hi, my name is John",
    "nice to meet you",
])
def test_real_stranger_signals_force_none(governor, query):
    assert governor._evaluate_identity_budget(HIGH, query) == "none"


# ── Shared history outweighs — the gate moves both ways ───────────────────

@pytest.mark.parametrize("query", [
    "remember when you said we haven't met?",
    "last time you told me you don't know me — was that right?",
    "our conversation earlier: you said this was our first time talking",
])
def test_shared_history_reference_outweighs_a_denial_phrase(governor, query):
    """
    Her rule is an AND. A denial phrase quoted inside a question about
    something shared is not the speaker presenting as a stranger.
    """
    assert governor._evaluate_identity_budget(HIGH, query) == "full"


# ── Confidence tiers still govern when nobody presents as a stranger ──────

def test_high_confidence_is_full(governor):
    assert governor._evaluate_identity_budget(0.85, "how are you?") == "full"


def test_mid_confidence_is_partial(governor):
    assert governor._evaluate_identity_budget(MID, "how are you?") == "partial"


def test_low_confidence_is_none(governor):
    assert governor._evaluate_identity_budget(LOW, "how are you?") == "none"


def test_stranger_signal_overrides_high_confidence(governor):
    """The original rule is correct and must survive: don't pretend."""
    assert governor._evaluate_identity_budget(
        1.0, "we've never met, my name is Sam"
    ) == "none"
