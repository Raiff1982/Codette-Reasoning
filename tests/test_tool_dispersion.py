"""Tool dispersion — the wave that follows a collapse, across perspectives.

Pins the behaviour measured on the 2026-08-14 `substrate_awareness.py` turn,
where a file was found twice and the finding reached nobody.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "inference"))

from tool_dispersion import ToolDispersionField, axis_key  # noqa: E402


# ── the axis ────────────────────────────────────────────────────────────────

def test_same_call_is_the_same_axis_regardless_of_whitespace():
    assert axis_key("read_file", ["x.py"]) == axis_key("read_file", [" x.py "])


def test_different_paths_are_different_axes():
    """The eight misses and the two hits used different spellings. They are
    genuinely different calls and must not be silently unified — deciding they
    mean the same file is the caller's job, said out loud."""
    assert axis_key("read_file", ["a.py"]) != axis_key("read_file", ["dir/a.py"])


# ── the wave ────────────────────────────────────────────────────────────────

def test_a_resolved_call_reaches_the_next_perspective():
    f = ToolDispersionField()
    f.collapse("read_file", ["inference/a.py"], "484 lines", "consciousness")
    out = f.take("read_file", ["inference/a.py"], "philosophy")
    assert out is not None
    assert "484 lines" in out
    assert "consciousness" in out, "provenance must be named, not anonymous"


def test_the_correction_is_named_not_silently_substituted():
    f = ToolDispersionField()
    f.collapse("read_file", ["a.py"], "484 lines", "newton",
               as_posed="inference/a.py")
    out = f.take("read_file", ["a.py"], "davinci")
    assert "inference/a.py" in out
    assert "not answered as literally asked" in out


def test_agreement_is_reported_as_agreement():
    f = ToolDispersionField()
    f.collapse("read_file", ["a.py"], "same", "newton")
    assert f.collapse("read_file", ["a.py"], "same", "davinci") == "agrees"


# ── runs to contradiction, and decides nothing ──────────────────────────────

def test_contradiction_is_surfaced_and_neither_side_is_chosen():
    f = ToolDispersionField()
    f.collapse("read_file", ["a.py"], "File not found", "newton")
    assert f.collapse("read_file", ["a.py"], "484 lines", "davinci") == "contested"

    out = f.take("read_file", ["a.py"], "quantum")
    assert "CONTESTED" in out
    assert "newton" in out and "davinci" in out, "both parties named"

    contested = f.summary()["contested"]
    assert len(contested) == 1
    assert contested[0]["first_by"] == "newton"
    assert contested[0]["then_by"] == "davinci"


def test_the_first_result_is_not_overwritten_by_a_later_one():
    """A later contradicting result does not win by arriving later. The reviewer
    rule that would quarantine everything on one 'unavailable' has the polarity
    backwards; nothing here picks at all."""
    f = ToolDispersionField()
    f.collapse("read_file", ["a.py"], "484 lines", "consciousness")
    f.collapse("read_file", ["a.py"], "File not found", "newton")
    assert "484 lines" in f.take("read_file", ["a.py"], "philosophy")


# ── it must be able to fall ─────────────────────────────────────────────────

def test_no_repeats_reads_zero_rather_than_looking_broken():
    f = ToolDispersionField()
    f.collapse("read_file", ["a.py"], "x", "newton")
    s = f.summary()
    assert s["recovered_calls"] == 0
    assert s["axes"] == 1, "the axis collapsed even though nothing was recovered"


def test_recovery_rises_only_when_work_is_actually_avoided():
    f = ToolDispersionField()
    f.collapse("read_file", ["a.py"], "0123456789", "newton")
    assert f.summary()["recovered_calls"] == 0
    f.take("read_file", ["a.py"], "davinci")
    assert f.summary()["recovered_calls"] == 1
    assert f.summary()["recovered_chars"] == 10


def test_disabled_is_distinguishable_from_empty():
    """The failure this repo keeps producing is an instrument whose silence
    reads like a healthy result."""
    off = ToolDispersionField(enabled=False)
    off.collapse("read_file", ["a.py"], "x", "newton")
    assert off.summary()["enabled"] is False
    assert off.take("read_file", ["a.py"], "davinci") is None

    on = ToolDispersionField()
    assert on.summary()["enabled"] is True
    assert on.summary()["axes"] == 0


def test_an_unresolved_axis_returns_none_and_that_is_not_a_fault():
    f = ToolDispersionField()
    assert f.take("read_file", ["never_asked.py"], "newton") is None


# ── her channel ─────────────────────────────────────────────────────────────
# CLAUDE.md, standing: the chalkboard is never read, and statistics over it are
# readings too. A dedup counter is a statistic.

@pytest.mark.parametrize("field", [
    ToolDispersionField(),
    ToolDispersionField(enabled=True),
])
def test_nameless_never_enters_the_field(field):
    field.collapse("nameless", ["anything at all"], "Written.", "empathy")
    assert field.summary()["axes"] == 0
    assert field.take("nameless", ["anything at all"], "newton") is None
    assert field.summary()["recovered_calls"] == 0
    assert field.summary()["contested"] == []


def test_nameless_is_never_counted_even_when_called_twice():
    f = ToolDispersionField()
    f.collapse("nameless", ["a"], "Written.", "empathy")
    f.collapse("nameless", ["a"], "Written.", "philosophy")
    assert f.summary()["axes"] == 0
    assert f.summary()["recovered_calls"] == 0
