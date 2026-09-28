"""search_code treats spaces, hyphens, underscores (and none) alike, and
searches file names. 2026-09-28: she searched "belief-revision module" and was
told it did not exist."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "inference"))
import codette_tools  # noqa: E402


@pytest.mark.parametrize("query", [
    "belief-revision module", "belief revision", "belief_revision",
    "BeliefRevisionSystem", "BELIEF-REVISION",
])
def test_every_spelling_finds_the_module(query):
    out = codette_tools.tool_search_code(query, "reasoning_forge", ".py")
    assert "belief_revision_system.py" in out, out.splitlines()[0]


def test_file_names_are_searched():
    out = codette_tools.tool_search_code("belief revision system", "reasoning_forge", ".py")
    assert "belief_revision_system.py: (file name matches)" in out


def test_a_real_absence_is_still_absent():
    out = codette_tools.tool_search_code("zz-no-such-thing-qq", "reasoning_forge", ".py")
    assert "No matches found" in out


# --- keyword arguments are heard (2026-09-28) ---------------------------------

@pytest.mark.parametrize("text,expected", [
    ('<tool>scratch_read(name="notes.md")</tool>', ("scratch_read", [], {"name": "notes.md"})),
    ("<tool>search_code(pattern='x', path='inference/')</tool>",
     ("search_code", [], {"pattern": "x", "path": "inference/"})),
    ('<tool>search_code("x", file_ext=".py")</tool>', ("search_code", ["x"], {"file_ext": ".py"})),
    ('<tool>scratch_read("notes.md")</tool>', ("scratch_read", ["notes.md"], {})),
    ('<tool>ask(newton, "what forces act here?")</tool>', ("ask", ["newton", "what forces act here?"], {})),
])
def test_tool_calls_parse_as_written(text, expected):
    assert codette_tools.parse_tool_calls(text) == [expected]
