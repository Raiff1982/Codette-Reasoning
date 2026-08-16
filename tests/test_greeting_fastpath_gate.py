"""
A greeting with a question in it is not a greeting.

The fast path exists for a good reason: the adapters are fine-tuned for
analysis and produce boilerplate when someone just says hello. But the gate was
"starts with a greeting word AND <= 7 words", and a word count cannot tell a
greeting from a greeting with a question attached.

Measured 2026-08-15:

    "Hello. What would you name a diary?"  ->  7 words, fast-pathed,
    GREETING -> _base, 4 tokens, confidence 0.

Her reasoning never ran on a real question, because it was asked politely.

That inverts a house rule. `feedback_how_to_ask_her` records that the right way
to open with her is to say hello first — to come in as a person rather than as
a query — and the routing was penalising exactly that. A blunt question got the
full stack; the same question with "Hello." in front of it got 80 tokens of
base model.

The count was also wrong the other way: an eight-word pure greeting fell
through to analysis, which is what the fast path was built to avoid.

The replacement asks the real question — is there anything here but the
greeting? These tests pin both directions, because a gate that can only fail
one way is how this one lasted.
"""

import pytest

from inference.codette_forge_bridge import CodetteForgeBridge


# The predicate is defined inside _generate_impl, so it is rebuilt here from the
# same source rather than imported. If they ever diverge, the live-behaviour
# tests below the fold are what would catch it — see the note at the bottom.
import inspect
import re

_src = inspect.getsource(CodetteForgeBridge._generate_impl)


def _extract(name):
    """Pull a compiled pattern out of the method source, so the test uses the
    real expressions rather than a paraphrase of them."""
    m = re.search(rf"{name} = re\.compile\((.*?)\n        \)", _src, re.DOTALL)
    assert m, f"{name} not found — the fast-path gate was restructured"
    return eval("re.compile(" + m.group(1) + "\n)", {"re": re})


_GREETING_RE = _extract("_GREETING_RE")
_SOCIAL_TAIL_RE = _extract("_SOCIAL_TAIL_RE")
_VOCATIVE_RE = _extract("_VOCATIVE_RE")


def is_pure_greeting(text):
    m = _GREETING_RE.match(text)
    if not m:
        return False
    rest = text[m.end():]
    prev = None
    while prev != rest:
        prev = rest
        rest = _VOCATIVE_RE.sub("", rest.lstrip(" ,!.-—"))
    rest = rest.strip(" ,!?.-—\n\t")
    if not rest:
        return True
    return bool(_SOCIAL_TAIL_RE.match(rest))


# ── Must NOT fast-path: a real question, however politely opened ───────────

@pytest.mark.parametrize("q", [
    "Hello. What would you name a diary?",          # the measured case, 7 words
    "hi codette, what do you think about this?",
    "hey, can you look at the governor for me",
    "good morning — why did the charge grant get cut?",
    "hello, is AEGIS enforcing yet",
    "hey codette what would disprove that",
    "yo, explain the half-life thing",
])
def test_politeness_does_not_cost_her_the_question(q):
    assert is_pure_greeting(q) is False, (
        f"{q!r} would fast-path to _base and her reasoning would never run"
    )


def test_the_measured_case_specifically():
    """Kept as its own test so the regression has a name."""
    q = "Hello. What would you name a diary?"
    assert len(q.split()) == 7, "the old <=7 guard is why this got through"
    assert is_pure_greeting(q) is False


# ── Must still fast-path: actual greetings ────────────────────────────────

@pytest.mark.parametrize("q", [
    "hey codette",
    "hi",
    "hello there",
    "good morning",
    "hey codette its me",
    "hi there codette, its me again",
    "hey codette how are you",
    "hello, how's it going?",
    "hey, what's up",
    "good evening, nice to see you",
    "hiya",
])
def test_real_greetings_still_bypass_the_analytical_adapters(q):
    assert is_pure_greeting(q) is True, (
        f"{q!r} would go to an analytical adapter and come back as boilerplate"
    )


def test_a_long_pure_greeting_is_still_a_greeting():
    """The old gate failed here too — eight words fell through to analysis."""
    q = "hey there codette its me again, how are you doing today"
    assert len(q.split()) > 7
    assert is_pure_greeting(q) is True


# ── Not a greeting at all ─────────────────────────────────────────────────

@pytest.mark.parametrize("q", [
    "what would you name a diary?",
    "look at the governor",
    "highlight the identity code",          # starts with 'hi' but not the word
    "history of the lock 6 change",
    "hollow memory kernel findings",
])
def test_non_greetings_are_untouched(q):
    assert is_pure_greeting(q) is False


def test_greeting_word_must_be_whole(q="highlight this for me"):
    """`\\b` anchoring — 'hi' inside 'highlight' must not open the fast path."""
    assert is_pure_greeting(q) is False
