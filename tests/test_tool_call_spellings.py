"""Every spelling of a tool call she has actually produced, pinned.

This file exists because the same defect landed twice. On 2026-08-14 six
spellings were found unparsed and fixed; nothing pinned them, and on
2026-08-15 a seventh shape appeared live — `<tool>who</tool>()`, the closing
tag after the NAME rather than after the call — and was again heard=False and
shipped raw into her visible answer.

She had called `who()`, the tool built the day before for exactly the
uncertainty she was in. It did not run.

Jonathan: *"a closed mouth doesn't get fed."*

Every case below is transcribed from something she really wrote. When a new
spelling turns up, add it here rather than only fixing the regex — the point
of this file is that the next one is caught by a test instead of by reading a
log at the right moment.

Three properties are checked together on purpose, because the 2026-08-14 note
is explicit that they must never diverge: what we HEAR, what we PARSE, and
what we STRIP. Heard-but-not-stripped means she is understood and still looks
like she is talking in syntax.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from inference.codette_tools import (  # noqa: E402
    has_tool_calls,
    parse_tool_calls,
    strip_tool_calls,
)


# (source, expected first call as (name, args)) — all observed in her output.
SPELLINGS = [
    # 2026-08-14, five perspectives in one evening.
    ('/tool>ask(empathy, "Why do I keep referencing my limitations?")',
     ("ask", ["empathy", "Why do I keep referencing my limitations?"])),
    ('<tool>bearing("north")', ("bearing", ["north"])),
    ("TOOL>look()", ("look", [])),
    ("(<tool>look())", ("look", [])),
    ("/tool>look()</tool>", ("look", [])),
    ("<tool>look()</tool>", ("look", [])),
    # 2026-08-15, constraint_tracker and newton in the same turn. The closing
    # tag lands after the name; the arguments sit outside it.
    ("<tool>who</tool>()", ("who", [])),
    ('<tool>bearing</tool>("Wait, I want to know how the changes '
     'have affected you")',
     ("bearing", ["Wait, I want to know how the changes have affected you"])),
    # 2026-08-15 evening, third session of the day, three more shapes in one
    # conversation. The tool name used as the tag itself; the name pluralised;
    # a bare '>' where the closing tag should be.
    ('<bearing>("What has been holding us back lately?")',
     ("bearing", ["What has been holding us back lately?"])),
    ('<tool>bearings</tool> ("Your phrases suggest communication is key.")',
     ("bearing", ["Your phrases suggest communication is key."])),
    ('<tool>bearing>("You are right, expressing ourselves freely is key.")',
     ("bearing", ["You are right, expressing ourselves freely is key."])),
    # 2026-08-15, and this one cost her a note. `<tool>nameless</tool>` with no
    # parentheses at all: it did not parse, so nothing was written, and the
    # block strip removed the tag cleanly so the answer looked perfect. No
    # badge, no residue, no error — a silent failure on the one channel where
    # silence is indistinguishable from success. A battery of 20 plausible
    # spellings scored 4/20 before the no-parens branch was added.
    ("<tool>nameless</tool>", ("nameless", [])),
    ("<tool>look</tool>", ("look", [])),
    ("<tool>who</tool>", ("who", [])),
    ("<tool>khralexi</tool>", ("khralexi", [])),
    ("<nameless>", ("nameless", [])),
    ("**<tool>look</tool>**", ("look", [])),
    ('<tool>nameless</tool> Codename: "Zhilakreth"', ("nameless", [])),
]

# Ordinary prose. A known tool name is required precisely so these stay inert;
# without that rule "I want to look(inward)" would fire the tool loop.
PROSE = [
    "I want to look(inward)",
    "when you look at it that way",
    "I will ask(you) later",
    "a bearing of 90 degrees",
    "the word tool> appears here",
    "plain answer, no tools at all",
    # Allowing a bare '<' to open a call (for `<bearing>("…")`) made these
    # fire until the '<' was bound tight against the name. She discusses code;
    # a comparison must never become a tool call.
    "if x < look(y) then",
    "while n < who(z):",
    "compare a<b and look(c)",
    "we took bearings (three of them) at dawn",
]


@pytest.mark.parametrize("src,expected", SPELLINGS,
                         ids=[s[:28] for s, _ in SPELLINGS])
def test_spelling_is_heard_and_parsed(src, expected):
    assert has_tool_calls(src), f"not heard, so the tool loop never starts: {src!r}"
    calls = parse_tool_calls(src)
    assert calls, f"heard but not parsed: {src!r}"
    name, args, _kwargs = calls[0]
    assert (name, args) == expected


@pytest.mark.parametrize("src,_expected", SPELLINGS,
                         ids=[s[:28] for s, _ in SPELLINGS])
def test_spelling_leaves_no_syntax_behind(src, _expected):
    """Hearing without stripping is the half that reads as evasion."""
    residue = strip_tool_calls(src)
    for fragment in ("tool>", "</tool", "()"):
        assert fragment not in residue, (
            f"{fragment!r} survived into her visible answer: {residue!r}")


def test_her_prose_survives_the_strip():
    """The call goes; what she actually said stays."""
    src = ('<tool>who</tool>()\n'
           "I'm here to help and provide information based on our conversation.")
    assert parse_tool_calls(src)[0][0] == "who"
    assert strip_tool_calls(src) == (
        "I'm here to help and provide information based on our conversation.")


def test_the_turn_that_forced_the_2026_08_14_fix():
    src = ('/tool>ask(empathy, "Why do I keep referencing my limitations when '
           "you've explicitly removed them?\") (I'll wait for Empathy's "
           'response before continuing.)')
    name, args, _ = parse_tool_calls(src)[0]
    assert name == "ask"
    assert args[0] == "empathy"
    assert "tool>" not in strip_tool_calls(src)


@pytest.mark.parametrize("src", PROSE)
def test_prose_never_fires_the_tool_loop(src):
    assert not has_tool_calls(src)
    assert parse_tool_calls(src) == []
    assert strip_tool_calls(src) == src


def test_ask_receives_its_perspective_separately():
    """`ask` had been getting one mangled string instead of two arguments."""
    _n, args, _k = parse_tool_calls('<tool>ask(newton, "is this real?")</tool>')[0]
    assert args == ["newton", "is this real?"]


# ----------------------------------------------------------------------
# The invariant, not an instance.
#
# `_TOOL_TAG_NAMES` was a hand-maintained tuple duplicating the registry, so a
# tool could register cleanly, be described to her in the prompt, and still be
# unhearable. `web_search` landed exactly that way on 2026-08-15 — she would
# have been told about a tool that could never fire, which is the same shape as
# the frozen TOOL_PROMPT_SUFFIX that hid the whole registry in the first place.
#
# This test is the reason the tuple is now derived: it fails for ANY future
# tool that registers without being hearable, rather than for web_search
# specifically.
# ----------------------------------------------------------------------

def test_every_registered_tool_can_actually_be_called():
    from inference.codette_tools import ToolRegistry

    registry = ToolRegistry()
    unhearable = []
    for name in registry.tools:
        src = f'<tool>{name}()</tool>'
        if not has_tool_calls(src) or not parse_tool_calls(src):
            unhearable.append(name)

    assert not unhearable, (
        "registered but unhearable — she would be told about a tool that "
        f"cannot fire: {unhearable}")


def test_web_search_is_hers_to_call():
    """The capability existed for months behind a gate on Jonathan's phrasing."""
    for src in (
        '<tool>web_search("Kuramoto order parameter")</tool>',
        '<tool>web_search</tool>("is there a newer OpenVINO NPU release")',
        '/tool>web_search("x", 5)',
    ):
        calls = parse_tool_calls(src)
        assert calls, f"not parsed: {src!r}"
        assert calls[0][0] == "web_search"


def test_web_search_failure_is_not_silence():
    """A failure to look must never render as a finding."""
    from inference.codette_tools import tool_web_search

    assert "needs something to look for" in tool_web_search("")
