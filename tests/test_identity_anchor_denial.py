"""
Regression tests for identity denial detection in the anchor.

This is the second copy of the bug found in the governor on 2026-08-11, and the
more serious one. The governor's gate decides how much identity context to
inject for a single turn and recovers on the next. This path calls

    identity.recognition_confidence = 0.0
    self._save(self.current_user)
    self.current_user = None

so a false positive does not thin one answer — it zeroes stored recognition
confidence, writes it to disk, and forgets the person.

Both copies matched their pattern list as bare substrings, so "do you remember
the first time you met Daniel?" and "i'm not sure what you mean" both counted
as the user denying their identity.

Every test here uses a temp identity_dir. Codette's real encrypted identity
store under data/identities/ is never opened.
"""

import pytest

from inference.identity_anchor import IdentityAnchor


@pytest.fixture
def anchor(tmp_path):
    """An anchor with an isolated, throwaway identity directory."""
    a = IdentityAnchor(identity_dir=tmp_path / "identities")
    a.current_user = "jonathan"
    a.identities["jonathan"].recognition_confidence = 0.9
    return a


def _remembered(anchor):
    return (
        anchor.current_user == "jonathan"
        and anchor.identities["jonathan"].recognition_confidence > 0.0
    )


# ── False positives that were wiping her memory of the user ───────────────

def test_question_about_a_third_partys_first_time_does_not_forget_the_user(anchor):
    """The live failure of 2026-08-11, at the destructive layer."""
    anchor.recognize("do you remember the first time you met daniel?")
    assert _remembered(anchor)


def test_im_not_sure_does_not_forget_the_user(anchor):
    """"i'm not " matched ordinary hedging."""
    anchor.recognize("i'm not sure what you mean by coherence here")
    assert _remembered(anchor)


def test_being_confused_by_an_explanation_is_not_being_mistaken_for_someone(anchor):
    """
    "you're confusing me" was in the list. It is what someone says when an
    explanation lost them; the intended sense was "confusing me with someone
    else", which is what the pattern now requires.
    """
    anchor.recognize("you're confusing me, can you say that more simply?")
    assert _remembered(anchor)


# ── Real denials must still be respected — the rule itself is correct ─────

@pytest.mark.parametrize("query", [
    "you don't know me",
    "we haven't met",
    "I think you have the wrong person",
    "that's not me",
    "who do you think i am?",
    "you're confusing me with someone else",
])
def test_real_denial_still_resets(anchor, query):
    assert anchor.recognize(query) is None
    assert anchor.current_user is None
    assert anchor.identities["jonathan"].recognition_confidence == 0.0


# ── Shared history outweighs, per her own rule ────────────────────────────

def test_denial_quoted_inside_a_question_about_shared_history_does_not_reset(anchor):
    anchor.recognize("remember when you said you don't know me?")
    assert _remembered(anchor)


# ── The deliberate asymmetry with the governor ────────────────────────────

def test_an_introduction_does_not_erase_the_stored_relationship(anchor):
    """
    The governor treats an introduction with no shared history as a stranger
    and withholds familiarity for that turn — that is Codette's own rule.

    This layer deliberately does NOT act on introductions. Someone saying
    "hi, my name is John" is telling us who is speaking now; they are not
    asserting that the stored record is wrong. Withholding familiarity is
    recoverable, deleting the record is not, so the destructive action is
    reserved for explicit denials.
    """
    anchor.recognize("hi, my name is John")
    assert _remembered(anchor)
