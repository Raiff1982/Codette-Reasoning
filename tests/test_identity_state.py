"""'none' used to mean both 'they said they are a stranger' and 'no signal yet'."""
import pytest

from reasoning_forge.behavior_governor import BehaviorGovernor


def _g():
    return BehaviorGovernor()


def _decide(conf, query):
    return _g().pre_evaluate(query, {"complexity": "MEDIUM", "domain": "general"},
                             identity_confidence=conf, substrate_pressure=0.0)


def test_no_signal_is_unknown_not_stranger():
    d = _decide(0.0, "what do you think about tides and the moon today?")
    assert d.identity_budget == "none"          # context still withheld
    assert d.identity_state == "unknown"


def test_claiming_to_be_a_stranger_is_stranger_claimed():
    d = _decide(0.95, "hi, we haven't met, I'm John")
    assert d.identity_budget == "none"
    assert d.identity_state == "stranger_claimed"


def test_recognised_speaker_is_recognized():
    assert _decide(0.95, "what do you think about tides today?").identity_state == "recognized"
    assert _decide(0.5, "what do you think about tides today?").identity_state == "recognized"


def test_shared_history_overrides_the_stranger_reading():
    d = _decide(0.95, "do you remember the first time you met daniel?")
    assert d.identity_state == "recognized"


def test_continuity_is_not_called_a_leak_when_nothing_was_established():
    g = _g()
    d = _decide(0.0, "what do you think about tides today?")
    r = g.post_validate("what do you think about tides today?",
                        "As you know, we've discussed this before.", d)
    assert "identity_leak" not in r.get("corrections", [])


def test_continuity_is_still_a_leak_after_a_stranger_claim():
    g = _g()
    d = _decide(0.95, "hi, we haven't met, I'm John")
    r = g.post_validate("hi, we haven't met, I'm John",
                        "As you know, we've discussed this before.", d)
    assert "identity_leak" in r.get("corrections", [])


@pytest.mark.parametrize("q", ["its jonathan btw", "why not?", "what was that?",
                               "everything ok?", "What should you remember?"])
def test_short_context_dependent_queries_keep_one_memory(q):
    assert _g()._evaluate_memory_budget("SIMPLE", "general", q, 0.0) == 1


@pytest.mark.parametrize("q", ["hi", "hello there", "good morning", "thanks!",
                               "hey codette", "how are you doing"])
def test_pure_greetings_still_get_none(q):
    assert _g()._evaluate_memory_budget("SIMPLE", "general", q, 0.0) == 0
