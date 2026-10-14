"""A short answer is an answer. Only an empty one is not (her ruling, 2026-08-03)."""
import pytest

from reasoning_forge.guardian_spindle import CoreGuardianSpindle


@pytest.mark.parametrize("text", [
    "No.", "Yes.", "Yes, for the reasons you gave.",
    "I won't help with that, and I'd rather say so plainly.",
])
def test_short_answers_are_not_rejected_for_being_short(text):
    ok, details = CoreGuardianSpindle().validate(text, query="q")
    assert ok, details


@pytest.mark.parametrize("text", ["", "   ", "\n\n"])
def test_empty_is_not_an_answer(text):
    ok, details = CoreGuardianSpindle().validate(text, query="q")
    assert not ok
    assert details["reason"] == "synthesis empty"
