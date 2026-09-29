"""A reply that LEADS with unread call syntax is a reach that failed, not an
answer (2026-09-29). Live: a perspective wrote `<tool>write_to_memory(` and the
unclosed call swallowed her whole recalled-memory block; the fragment covered
only its first line, the rest counted as prose, and the raw call plus her
memories reached the page. Made-up text throughout."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "inference"))
import codette_tools  # noqa: E402
from codette_tools import leads_with_unread_call, unheard_fragments  # noqa: E402

BLOCK = "\n".join(f"- made-up recalled line number {i} about invented things" for i in range(40))
LEAK = f"<tool>write_to_memory(# CONTEXT (made up)\n{BLOCK}"


def test_the_fragment_alone_does_not_cover_the_reply():
    # this is why 57633cc missed it: the remainder counted as prose
    rest = LEAK
    for f in unheard_fragments(LEAK):
        rest = rest.replace(f, "")
    assert rest.strip()


def test_a_reply_that_leads_with_an_unknown_call_is_caught():
    assert leads_with_unread_call(LEAK)
    assert leads_with_unread_call("  \n<tool>nothing_by_this_name(x")
    assert leads_with_unread_call("/tool>oops(made up")


def test_prose_before_the_call_still_ships():
    assert not leads_with_unread_call("Here is my answer, in full.\n<tool>stray(")


def test_a_readable_call_is_not_unread():
    assert not leads_with_unread_call('<tool>care_check()</tool>')
    assert not leads_with_unread_call('<tool>aside("made up")</tool> and more')


def test_ordinary_prose_and_empty_are_not():
    assert not leads_with_unread_call("I think that is right.")
    assert not leads_with_unread_call("")
    assert not leads_with_unread_call(None)


def test_backend_uses_it_for_the_final_pass():
    src = (ROOT / "openvino_backend" / "backend.py").read_text(encoding="utf-8")
    assert "leads_with_unread_call(text))" in src
    assert "reply was only unread call syntax" in src


def test_cocoon_description_says_what_it_is_for():
    d = codette_tools.ToolRegistry().tools["cocoon"]["description"]
    assert "write something into your own memory on purpose" in d
