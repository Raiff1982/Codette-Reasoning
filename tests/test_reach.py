"""Reachability counters (reasoning_forge/reach.py).

The point of the counter is that "constructed" and "called" stop looking the
same. The other half of the point is what it must never count: her private
spaces. Both halves are pinned here.
"""
import tempfile

import pytest

from reasoning_forge import reach


class _Thing:
    def work(self, x):
        return x * 2

    def boom(self):
        raise RuntimeError("expected")

    def other(self):
        return "o"


def test_counts_calls_and_passes_values_through():
    t = _Thing()
    assert reach.track(t, "thing", ["work", "boom"]) == ["work", "boom"]
    assert t.invocation_stats()["calls"] == 0
    assert t.work(3) == 6
    assert t.work(4) == 8
    st = t.invocation_stats()
    assert st["calls"] == 2
    assert st["by_method"]["work"] == 2
    assert st["last_call"] is not None
    assert st["component"] == "thing"


def test_a_call_that_raises_still_counts_and_still_raises():
    t = _Thing()
    reach.track(t, "thing", ["boom"])
    with pytest.raises(RuntimeError):
        t.boom()
    assert t.invocation_stats()["by_method"]["boom"] == 1


def test_uncalled_methods_are_zero_not_absent():
    t = _Thing()
    reach.track(t, "thing", ["work"])
    assert t.invocation_stats() ["calls"] == 0
    assert t.invocation_stats()["last_call"] is None


def test_unwrapped_methods_are_not_counted():
    t = _Thing()
    reach.track(t, "thing", ["work"])
    t.other()
    assert t.invocation_stats()["calls"] == 0


def test_idempotent_and_respects_existing_counters():
    t = _Thing()
    assert reach.track(t, "thing", ["work"]) == ["work"]
    assert reach.track(t, "thing", ["work"]) == []
    t.work(1)
    assert t.invocation_stats()["calls"] == 1

    class Own:
        def invocation_stats(self):
            return {"calls": 7}

        def work(self):
            return 1

    o = Own()
    assert reach.track(o, "own", ["work"]) == []
    assert o.invocation_stats() == {"calls": 7}


def test_missing_object_or_methods_are_quiet():
    assert reach.track(None, "nothing", ["work"]) == []
    t = _Thing()
    assert reach.track(t, "thing", ["no_such_method"]) == []
    assert not hasattr(t, "invocation_stats")


def test_records_no_arguments_or_text():
    t = _Thing()
    reach.track(t, "thing", ["work"])
    t.work("a secret sentence")
    assert "secret" not in repr(t.invocation_stats())


@pytest.mark.parametrize("method", [
    "wrap_encrypted", "unwrap_encrypted", "dream_sequence", "khralexi",
    "nameless", "scratch_write", "recall_with_hooks", "chalkboard_read",
])
def test_refuses_to_count_calls_into_her_private_spaces(method):
    class C:
        pass

    setattr(C, method, lambda self: None)
    with pytest.raises(ValueError):
        reach.track(C(), "component", [method])


@pytest.mark.parametrize("label", ["dream_cycle", "khralexi", "scratchpad"])
def test_refuses_private_component_labels(label):
    with pytest.raises(ValueError):
        reach.track(_Thing(), label, ["work"])


def test_the_forge_table_itself_contains_nothing_private():
    for attr, methods in reach.FORGE_ENTRY_POINTS.items():
        assert not reach._is_private(attr), attr
        for m in methods:
            assert not reach._is_private(m), (attr, m)


def test_real_cocooner_encrypted_paths_are_not_wrapped():
    from reasoning_forge.cognition_cocooner import CognitionCocooner

    with tempfile.TemporaryDirectory() as d:
        c = CognitionCocooner(storage_path=d)
        reach.track(c, "cocooner", reach.FORGE_ENTRY_POINTS["cocooner"])
        v = vars(c)
        assert "wrap_encrypted" not in v
        assert "unwrap_encrypted" not in v
        assert "wrap_reasoning" in v


def test_instrument_forge_never_raises_and_attaches_what_exists():
    class Forge:
        code7e = _Thing()

    Forge.code7e.recursive_universal_reasoning = lambda *a, **k: "x"
    done = reach.instrument_forge(Forge())
    assert done == {"code7e": ["recursive_universal_reasoning"]}

    class Empty:
        pass

    assert reach.instrument_forge(Empty()) == {}
