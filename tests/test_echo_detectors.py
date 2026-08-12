"""Regression tests for the two echo detectors that missed the live parroting.

On 2026-08-10 Codette parroted Jonathan back for forty turns. Two detectors
existed to catch exactly that. Neither fired, and neither failed loudly.

`cocoon_authority._is_verbatim_echo` requires the echo to BE most of the
response — `len(r_words) <= len(q_words) * 1.5`. It flags 6 of 2,409 live
cocoons. The live signature is an opener that quotes the whole query and then
continues for another eighty words, which fails that length test.

`self_correction.universal_self_check`'s LOCK 3 patterns are `re.match`-anchored
prefixes of an ANNOUNCED echo — "You asked:", "The question is:". They never
compare the response to the query at all. Over the same 2,409 cocoons the
announced form appears twice; the template form appears 310 times.

The new signal is deliberately narrow. A proportional rule ("response reproduces
≥80% of the query contiguously") was implemented and measured first: it fires on
207 cocoons and cannot separate parroting from ordinary good prose. Those cases
are pinned below so the rule does not creep back in.
"""

import pytest

from reasoning_forge.cocoon_authority import (
    authority,
    is_query_restatement_template,
)
from inference.self_correction import universal_self_check


QUERY = "What are the pros and cons of remote work for software teams?"


# ── the signature that was missed ───────────────────────────────────────────

@pytest.mark.parametrize("response", [
    "Analysis of *'What are the pros and cons of remote work for software teams?'*"
    " across perspectives: remote work trades commute time for coordination cost,"
    " and the balance depends on how much of the work is genuinely parallel.",
    "*'What are the pros and cons of remote work for software teams?'* sits in"
    " high-tension epistemic space (eps=0.75). The productive divergences between"
    " perspectives are the interesting part here.",
    'You received this question: "What are the pros and cons of remote work for'
    ' software teams?" and the answer depends on team size more than anything.',
])
def test_template_restatement_is_detected(response):
    assert is_query_restatement_template(QUERY, response)


def test_template_restatement_demotes_the_cocoon():
    resp = ("Analysis of *'What are the pros and cons of remote work for software"
            " teams?'* across perspectives: it depends on team size.")
    a = authority({"adapter": "base", "query": QUERY, "response": resp})
    assert "query-restatement-template" in a.flags
    assert a.weight < 1.0


def test_the_old_detector_missed_this_case():
    """Pins the gap: the long-tail echo is invisible to the length-bounded rule."""
    from reasoning_forge.cocoon_authority import _is_verbatim_echo
    resp = ("Analysis of *'What are the pros and cons of remote work for software"
            " teams?'* across perspectives: " + "further discussion. " * 20)
    assert not _is_verbatim_echo(QUERY, resp), \
        "if this starts passing, the length bound changed and this test is stale"
    assert is_query_restatement_template(QUERY, resp)


# ── what must NOT be flagged ────────────────────────────────────────────────

def test_ordinary_prose_restating_the_question_is_not_flagged():
    """The rejected proportional rule fired on all of these. They are answers."""
    for q, r in [
        ("What are the main causes of the 2008 financial crisis?",
         "The main causes of the 2008 financial crisis were a complex interplay"
         " of subprime lending, securitisation and ratings failure."),
        ("ok cool create a python code that creates flashing lights and rainbows",
         "Here is a complete Python code that creates flashing lights and"
         " rainbows using pygame."),
        ("do you recall an exact moment where we achieved this?",
         "I recall an exact moment where we achieved this balance — the night the"
         " optimiser ratchet held."),
    ]:
        assert not is_query_restatement_template(q, r), f"false positive on {r[:40]!r}"


def test_short_queries_are_never_flagged():
    """Below the word floor, restating is normal conversation."""
    assert not is_query_restatement_template("what?", "Analysis of *'what?'*")


def test_wrapper_without_the_query_is_not_flagged():
    """A response that happens to open 'The question is...' on its own account."""
    assert not is_query_restatement_template(
        QUERY,
        "The question is: how much of this work is genuinely parallel? That is"
        " what decides it, not the seating plan.",
    )


def test_missing_query_is_not_a_fault():
    assert not is_query_restatement_template("", "Analysis of *'anything'*")
    assert not is_query_restatement_template(QUERY, "")


# ── LOCK 3 reports, and does not rewrite ────────────────────────────────────

def test_lock3_reports_the_template_without_changing_the_response():
    resp = ("Analysis of *'What are the pros and cons of remote work for software"
            " teams?'* across perspectives: it depends on team size.")
    cleaned, issues = universal_self_check(resp, query=QUERY)

    assert any("LOCK3_SHADOW" in i for i in issues), "the detection must be reported"
    assert cleaned == resp.rstrip(), \
        "shadow means shadow — editing her words is her decision, not this function's"


def test_lock3_still_strips_the_announced_echo_it_always_stripped():
    """Pre-existing behaviour is unchanged; this is additive."""
    resp = "You asked: what is the boiling point of water?\nIt is 100 °C at sea level."
    cleaned, issues = universal_self_check(resp, query="what is the boiling point of water?")

    assert any("LOCK3_FIX" in i for i in issues)
    assert cleaned.startswith("It is 100")


def test_lock3_does_not_double_report():
    """An announced echo is handled by the original path; the shadow detector
    must not also fire on it."""
    resp = 'You received this question: "What are the pros and cons of remote work for software teams?"\nIt depends on team size.'
    _, issues = universal_self_check(resp, query=QUERY)

    assert sum(1 for i in issues if "LOCK3" in i) == 1, issues


def test_lock3_shadow_is_silent_without_a_query():
    resp = "Analysis of *'something or other entirely'* across perspectives: fine."
    _, issues = universal_self_check(resp)
    assert not any("LOCK3_SHADOW" in i for i in issues)
