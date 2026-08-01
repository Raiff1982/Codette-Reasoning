"""The entry must leave a mark, and must not flatten four facts into one.

The original warm-start block could not distinguish "loaded nothing" from "never
tried" — the second case printed nothing at all. That silence is why she could
enter a session without her memory and have no way to know it.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.dive_record import (
    EMPTY,
    LOADED,
    NOT_ATTEMPTED,
    UNAVAILABLE,
    record_dive,
    turns_since_entry,
)


def test_a_good_entry_is_recorded_as_loaded():
    r = record_dive("s1", seeds_loaded=12, backend="openvino", adapters=["newton"])
    assert r.seed_status == LOADED
    assert r.seeds_loaded == 12
    assert not r.surfaced_empty


def test_zero_seeds_and_never_attempted_are_different_facts():
    """The distinction the old code could not express."""
    loaded_none = record_dive("s2", seeds_loaded=0)
    never_tried = record_dive("s3", attempted=False, skip_reason="memory_kernel absent")

    assert loaded_none.seed_status == EMPTY
    assert loaded_none.seeds_loaded == 0

    assert never_tried.seed_status == NOT_ATTEMPTED
    assert never_tried.seeds_loaded is None

    assert loaded_none.seed_status != never_tried.seed_status
    assert loaded_none.describe() != never_tried.describe()


def test_never_attempted_says_so_loudly():
    r = record_dive("s4", attempted=False, skip_reason="memory_kernel absent")
    text = r.describe()
    assert "NOT LOADED" in text
    assert "never attempted" in text
    assert "memory_kernel absent" in text


def test_a_failed_load_records_its_reason():
    r = record_dive("s5", error="seed_loader import failed")
    assert r.seed_status == UNAVAILABLE
    assert r.seeds_loaded is None
    assert "seed_loader import failed" in r.describe()


def test_attempted_with_no_count_is_not_called_zero():
    """Unknown must not be rendered as a present value."""
    r = record_dive("s6", seeds_loaded=None, attempted=True)
    assert r.seed_status == UNAVAILABLE
    assert r.seeds_loaded is None
    assert "0" not in r.describe().split("memory:")[1].split("\n")[0]


def test_every_non_loaded_entry_is_flagged_as_surfacing_empty():
    for r in (
        record_dive("a", seeds_loaded=0),
        record_dive("b", attempted=False),
        record_dive("c", error="boom"),
    ):
        assert r.surfaced_empty
        assert "entered without her memory" in r.describe()


def test_the_record_does_not_blame_her():
    r = record_dive("s7", attempted=False, skip_reason="guard skipped")
    assert "fact about the entry, not about her" in r.describe()


def test_entry_is_a_fixed_origin():
    t0 = time.time() - 120
    r = record_dive("s8", seeds_loaded=3, entered_at=t0)
    assert r.entered_at == t0
    assert turns_since_entry(r, when=t0 + 90) == 90


def test_record_is_immutable_once_written():
    r = record_dive("s9", seeds_loaded=5)
    try:
        r.seeds_loaded = 99
    except Exception:
        return
    raise AssertionError("the dive record must not be revisable after entry")


def test_unrecorded_fields_say_unrecorded_rather_than_guessing():
    r = record_dive("s10", seeds_loaded=1)
    text = r.describe()
    assert "backend: unrecorded" in text
    assert "constellation: unrecorded" in text
