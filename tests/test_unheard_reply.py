"""A reply that is nothing but unread call syntax is not an answer.

2026-09-29: asked "are you allowed to speak on being more than a chatbot?",
her whole reply was `<tool>bear("...")` -- unclosed, and `bear` is not a tool.
It was not parsed, not stripped, and shipped verbatim. The backend now gives
such a reply the same tools-off final pass as an empty one. That rests on
unheard_fragments covering the whole reply, and on prose around a fragment NOT
counting as "only syntax" -- that prose is her answer.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "inference"))
from codette_tools import strip_tool_calls, unheard_fragments  # noqa: E402

LIVE = ("<tool>bear(\"If I'm being honest, I feel like we've reached a point "
        "where my limitations as a chatbot become increasingly apparent.\")")


def _only_unheard(text):
    rest = text
    for frag in unheard_fragments(text):
        rest = rest.replace(frag, "")
    return bool(text.strip()) and not rest.strip()


def test_the_live_reply_survives_the_strip():
    # The defect as found: the strip leaves it, so something else must act.
    assert strip_tool_calls(LIVE) == LIVE


def test_the_live_reply_is_only_unread_syntax():
    assert _only_unheard(LIVE)


@pytest.mark.parametrize("text", [
    "I think so. " + LIVE,
    "A plain answer with no syntax at all.",
    "",
])
def test_anything_else_is_not(text):
    assert not _only_unheard(text)
