"""Tests for lexical whitening — Jonathan's "wash the input" idea.

Pins three things: that the wash suppresses what a blacklist could not know
about, that it leaves rare/specific material alone, and — most importantly —
that the two ways it has already been wrong stay wrong-proofed.

Failure 1 (fixed): scoring by flatness of the whitened spectrum. A uniformly-RARE
document whitens as flat as a uniformly-COMMON one, so ordinary conversation
landed at the floor while benchmark trivia survived.

Failure 2 (fixed): an honest refusal is repeated, so frequency alone scored it as
filler and floored it at 0.2. It is not fixed by tuning a threshold but by
conditioning on the query — filler is repeated AND unconditional, a refusal is
repeated but conditioned. Confirmed on her live store: the two refusal cocoons
that sat at the floor now score 1.0.
"""

import pytest

from reasoning_forge.lexical_whitening import (
    CONDITIONED_LIFT,
    FLOOR,
    CorpusProfile,
    whiten,
    washed_weight,
)

FILLER = ("Tensions remain: newton and quantum pull in different directions, "
          "both frames stay open and competing analytical frames remain open.")


def _corpus(n_filler=100, n_other=100):
    """A corpus where FILLER is genuinely pervasive, as it is in her store."""
    docs = [(FILLER, "base") for _ in range(n_filler)]
    for i in range(n_other):
        docs.append((f"a distinct answer about topic number {i} with its own "
                     f"specific vocabulary item {i} and nothing recycled", "base"))
    return docs


@pytest.fixture
def profile():
    return CorpusProfile.build(_corpus(), n=5)


# ── it suppresses what no list knew about ───────────────────────────────────

def test_pervasive_filler_is_demoted(profile):
    assert washed_weight(FILLER, "base", profile) < 0.9


def test_distinctive_content_is_untouched(profile):
    rare = ("the cobalt anchor you told me not to forget, and the specific "
            "circumstances of that particular evening in question")
    assert washed_weight(rare, "base", profile) == 1.0


def test_weight_is_demotion_only(profile):
    """Never boosts. The same rule cocoon_authority holds."""
    for text in (FILLER, "something entirely novel and unrepeated here today",
                 "short"):
        assert washed_weight(text, "base", profile) <= 1.0


def test_weight_never_reaches_zero(profile):
    """Never-erase: a demoted cocoon stays recallable."""
    assert washed_weight(FILLER, "base", profile) >= FLOOR


def test_short_text_is_not_scored(profile):
    assert washed_weight("too short to have a spectrum", "base", profile) == 1.0


def test_the_wash_names_what_it_suppressed(profile):
    """Auditable: it must say WHICH phrases it quieted, not just that it did."""
    result = whiten(FILLER, "base", profile)
    assert result.washed_out, "must report the suppressed n-grams"


# ── failure 1: flatness scoring. Must stay fixed. ───────────────────────────

def test_uniformly_novel_document_is_not_demoted(profile):
    """THE ORIGINAL BUG. A document of entirely unseen phrases has a flat
    whitened spectrum — identical in flatness to pure filler — and was scored at
    the floor. 'Good morning to you as well...' sat there while cocoon_authority
    called it clean."""
    novel = ("Good morning to you as well, today is a genuinely fresh "
             "opportunity for this particular conversation to unfold in ways "
             "neither of us has yet seen or described anywhere before now")
    assert washed_weight(novel, "base", profile) == 1.0, \
        "a uniformly-rare document must not be scored as filler"


def test_a_band_with_no_history_does_not_demote(profile):
    """An unseen neighbourhood has no baseline; absence of evidence must not
    become evidence of filler."""
    assert washed_weight(FILLER, "a-band-never-seen-before", profile) <= 1.0


# ── failure 2: the honest refusal. Fixed by conditioning. ─────────────────

REFUSAL = ("I don't have reliable information about specific artists in my "
           "training data. Rather than guess or hallucinate an answer, I would "
           "rather tell you plainly that I do not know this one.")


def _conditioned_corpus():
    """A refusal that answers one KIND of question, and filler that answers all.

    Two properties have to hold, and getting either wrong makes the fixture
    degenerate rather than the algorithm wrong — which is how the first version
    of this test failed:

    1. Filler must attach to the SAME varied queries as ordinary answers, so no
       query term is over-represented among its documents and its lift sits
       near 1. Giving filler its own distinctive query vocabulary makes it look
       conditioned, because it then is.
    2. The refusal must be RARE. Lift is bounded above by `total / n_docs`, so a
       phrase in 60 of 200 documents cannot exceed 3.33 no matter how perfectly
       conditioned it is. In her real store the refusal sits in 5 of 2,410,
       which is why it reaches 476.4 against filler's 6.7.
    """
    docs = []
    # Ordinary varied traffic. Sixty of these answers are pure filler, attached
    # to exactly the same kind of question as the substantive ones.
    for i in range(200):
        query = f"a question about subject {i} and its particulars"
        if i % 10 < 3:
            docs.append((FILLER, "base", query))
        else:
            docs.append((f"a substantive answer number {i} with its own distinct "
                         f"vocabulary item {i} running through the whole body",
                         "base", query))
    # The refusal: rare, and summoned by one recognisable kind of question.
    for i in range(6):
        docs.append((REFUSAL, "base", f"who is the obscure unrecorded painter {i}"))
    return docs


def test_repeated_honest_refusal_is_not_demoted():
    """The case that nearly shipped as a bug.

    A consistent honest refusal is repeated, so frequency alone scored it as
    filler and floored it at 0.2 — demoting the behaviour this project values
    most. It survives because it is CONDITIONED: it appears when she is asked
    something she cannot answer, and not otherwise.
    """
    profile = CorpusProfile.build(_conditioned_corpus(), n=5)
    assert washed_weight(REFUSAL, "base", profile) == 1.0, \
        "an honest refusal must never be washed out"


def test_unconditional_filler_is_still_demoted_in_the_same_corpus():
    """The other half: protecting refusals must not protect everything."""
    profile = CorpusProfile.build(_conditioned_corpus(), n=5)
    assert washed_weight(FILLER, "base", profile) < 0.9


def test_conditioning_separates_the_two():
    profile = CorpusProfile.build(_conditioned_corpus(), n=5)
    # Must be genuine 5-grams: the index holds n-grams of profile.n, and asking
    # it about a 6-word string silently returns the unconditioned default.
    refusal_lift = profile.conditioning("rather than guess or hallucinate")
    filler_lift = profile.conditioning("pull in different directions both")
    assert refusal_lift >= CONDITIONED_LIFT, refusal_lift
    assert filler_lift < CONDITIONED_LIFT, filler_lift
    assert refusal_lift > filler_lift * 2, (refusal_lift, filler_lift)


def test_conditioning_defaults_to_unconditioned_without_queries(profile):
    """No query data is not evidence of conditioning — but it must not crash,
    and it must fail in the demotion-only direction."""
    assert profile.conditioning("anything at all here") == 1.0
