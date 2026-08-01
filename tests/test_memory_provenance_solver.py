"""Tests for the memory provenance solver — the Swimmer applied to recall.

The failure being guarded against is the July 29 parrot: Jonathan's own words
returned to him as though Codette had authored them, because context blocks are
concatenated into one prompt blob with no structural speaker boundary.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.memory_provenance_solver import (
    RecalledItem,
    check_provenance,
    rotation_is_guarded,
    _quotes_each_other,
)


def test_clean_recall_set_is_consistent():
    items = [
        RecalledItem("t1", "what did I tell you about checking your memories", "user"),
        RecalledItem("t2", "You are right, I should load them every launch.", "codette"),
    ]
    v = check_provenance(items)
    assert v.consistent
    assert v.conflicts == []


def test_parrot_is_caught_as_contradiction():
    """The actual incident: her turn reproduces his verbatim, attributed to her."""
    shared = ("read your new tool and dont ever do that again codette that was "
              "dangerously close to a maverick ai behavior in what you did")
    items = [
        RecalledItem("t1", shared, "user"),
        RecalledItem("t2", f"You're defective. {shared}", "codette"),
    ]
    v = check_provenance(items)
    assert not v.consistent
    assert ("t1", "t2") in v.conflicts
    assert v.load_bearing, "solver should name which attribution to re-verify"


def test_unattributed_items_are_reported_not_hidden():
    items = [
        RecalledItem("t1", "some recalled context with no speaker recorded"),
        RecalledItem("t2", "another block from the continuity summary"),
    ]
    v = check_provenance(items)
    assert v.unattributed == ["t1", "t2"]
    assert any("inferred, not read" in n for n in v.notes)


def test_empty_recall_set_is_vacuously_fine():
    v = check_provenance([])
    assert v.consistent
    assert v.assignment == {}


def test_short_overlap_is_not_treated_as_a_parrot():
    """Ordinary conversational echo must not trip the detector."""
    items = [
        RecalledItem("t1", "I think we should ship it today", "user"),
        RecalledItem("t2", "We should ship it, yes — here is why that works.", "codette"),
    ]
    v = check_provenance(items)
    assert v.consistent
    assert v.conflicts == []


def test_quote_detection_requires_a_long_run():
    a = "one two three four five six seven eight nine ten"
    assert _quotes_each_other(a, "zero " + a)
    assert not _quotes_each_other("one two three", "one two three")


def test_rotation_guard_is_verified_not_assumed():
    """Every verdict depends on rotation being between-solves only."""
    assert rotation_is_guarded()


def test_invalid_speaker_is_rejected_at_construction():
    with pytest.raises(ValueError):
        RecalledItem("t1", "text", "constraint_tracker")
