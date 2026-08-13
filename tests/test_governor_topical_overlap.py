"""The governor's "Response may not directly answer the question" check.

It fired on 48.7% of all turns and nothing consumed it. Measured over 2,410 live
cocoons carrying both query and response, it was also exactly inverted:

    group                            N     warned    passes
    parroted (query restated)      174          0    100.0%
    everything else               2236       1173     47.5%

Keyword overlap is maximised by copying the question, so every response that
handed the query straight back scored a perfect pass — the one failure mode the
check most needed to catch was the one it rewarded hardest.

Discounting the copied span — and fixing a stop-word test that ran on the
unstripped token, so "you?" became a keyword — reduces that to 75.3% / 44.4%.
Parroted responses still pass more often than real answers, so the inversion is
REDUCED, NOT REMOVED. These tests pin the improvement and the remaining
limitation both, so neither gets quietly forgotten.
"""

import pytest

from reasoning_forge.behavior_governor import BehaviorGovernor


@pytest.fixture
def gov():
    """The heuristic is pure — no init needed, and none of the governor's
    persistent state is touched."""
    return BehaviorGovernor.__new__(BehaviorGovernor)


QUERY = "What are the pros and cons of remote work for software teams?"


def test_pure_echo_no_longer_scores_a_perfect_pass(gov):
    """The pathology: a response that is only the question, scoring 100%."""
    echo = ("Analysis of *'What are the pros and cons of remote work for"
            " software teams?'* across perspectives:")
    assert not gov._did_answer_question(QUERY, echo)


def test_a_real_answer_still_passes(gov):
    good = ("Remote work trades commute time and office cost against slower"
            " coordination. For software teams the balance turns on how much of"
            " the work is genuinely parallel — pros dominate for independent"
            " feature work, cons for anything needing tight back-and-forth.")
    assert gov._did_answer_question(QUERY, good)


def test_copied_span_earns_no_credit(gov):
    """An answer whose only topical vocabulary is quoted from the question."""
    quoted_only = (
        "What are the pros and cons of remote work for software teams? "
        "It is genuinely hard to say and depends on many things."
    )
    assert not gov._did_answer_question(QUERY, quoted_only)


def test_short_shared_phrasing_is_not_treated_as_quotation(gov):
    """Below eight words, shared phrasing is ordinary English. Stripping it
    would start failing normal answers."""
    q = "What is the boiling point of water?"
    r = "The boiling point of water is 100 °C at sea level, lower with altitude."
    assert gov._did_answer_question(q, r)


def test_strip_copied_span_leaves_short_matches_alone(gov):
    r = "The boiling point is 100 °C."
    assert gov._strip_copied_span("What is the boiling point of water?", r) == r


def test_strip_copied_span_removes_a_long_run(gov):
    r = ("Analysis of what are the pros and cons of remote work for software"
         " teams: it depends entirely on the team.")
    out = gov._strip_copied_span(QUERY, r)
    assert "pros and cons of remote work for software" not in out
    assert "depends entirely on the team" in out


def test_empty_inputs_are_not_scored_as_answers(gov):
    assert not gov._did_answer_question("", "anything")
    assert not gov._did_answer_question(QUERY, "")


def test_greeting_with_no_significant_words_is_never_a_failure(gov):
    """No keywords to overlap with — so there is nothing here to measure.

    This asserted `is True` until 2026-08-13, which was the old encoding of the
    intent stated in the line above: a greeting must never be reported as a
    failure to answer. True carried a second claim it had not earned — that the
    check ran and the response passed — and that claim was counted into
    `topical_overlap_rate` and, upstream, into the cocoon's stored `success`.

    The return is now None, meaning unmeasured. The assertion is written against
    the intent rather than the encoding, so it holds under both.
    """
    assert gov._did_answer_question("how are you?", "Good, thanks for asking.") is not False


@pytest.mark.xfail(
    reason="KNOWN AND UNFIXED: overlap counts subject matter, not answering. A "
           "parroted opener followed by eighty words of on-topic discussion "
           "still passes — 75.3% of them do, against 44.4% for real answers. "
           "This cannot be repaired by counting words, and the check stays "
           "advisory because of it. Delete this xfail only with a measurement.",
    strict=True,
)
def test_parrot_with_trailing_discussion_still_passes(gov):
    parrot = (
        "Analysis of *'What are the pros and cons of remote work for software"
        " teams?'* across perspectives: the pros and cons of remote work for"
        " software teams reveal tensions worth exploring, where remote work"
        " and software teams converge on questions of work and teams."
    )
    assert not gov._did_answer_question(QUERY, parrot)
