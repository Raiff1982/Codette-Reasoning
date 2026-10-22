"""EthicalAnchor, observe-only: trim regret from the post-write checks, M never invented."""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "inference"))

from reasoning_forge import reach, self_check as sc
from reasoning_forge.memory_kernel import EthicalAnchor
from inference.codette_forge_bridge import CodetteForgeBridge


def test_observe_records_regret_and_leaves_the_ethical_state_uncomputed():
    a = EthicalAnchor()
    assert a.observe(1.0, 0.8) == abs(1.0 - 0.8)
    h = a.history[-1]
    assert h["M"] is None and abs(h["regret"] - 0.2) < 1e-9       # not computed, and says so
    assert abs(a.get_regret_signal() - 0.2) < 1e-9


def test_history_is_bounded():
    a = EthicalAnchor()
    for _ in range(EthicalAnchor.MAX_HISTORY + 50):
        a.observe(1.0, 0.9)
    assert len(a.history) == EthicalAnchor.MAX_HISTORY


def _bridge(monkeypatch, tmp_path):
    monkeypatch.setattr(sc, "DEFAULT_COUNTS", tmp_path / "c.json")
    sc._last.clear()
    b = CodetteForgeBridge.__new__(CodetteForgeBridge)
    b.forge = types.SimpleNamespace(ethical_anchor=EthicalAnchor())
    reach.instrument_forge(b.forge)
    return b


def test_the_bridge_feeds_trim_regret_only_when_the_checks_ran_and_measured_both_lengths(monkeypatch, tmp_path):
    b = _bridge(monkeypatch, tmp_path)
    a = b.forge.ethical_anchor
    b._record_self_check({"response": "kept", "self_check_ran": True, "self_check_len": [100, 75]}, "hi")
    assert len(a.history) == 1 and abs(a.history[0]["regret"] - 0.25) < 1e-9    # a quarter was removed
    b._record_self_check({"response": "x", "self_check_ran": True, "self_check_len": [100, 100]}, "hi")
    assert a.history[-1]["regret"] == 0.0 and len(a.history) == 2               # measured, nothing removed
    b._record_self_check({"response": "x", "self_check_ran": False, "self_check_len": [100, 50]}, "hi")
    b._record_self_check({"response": "x", "self_check_ran": True}, "hi")        # lengths not measured
    b._record_self_check({"response": "x", "self_check_ran": True, "self_check_len": [0, 0]}, "hi")
    assert len(a.history) == 2                                                  # none of those invented a reading
    exam = "What is the correct answer to this question?\n(A) a\n(B) b\n(C) c\n(D) d"
    b._record_self_check({"response": "x", "self_check_ran": True, "self_check_len": [100, 10]}, exam)
    assert len(a.history) == 2                                                  # benchmarks are never counted
    assert a.invocation_stats()["calls"] == 2                                   # the health page can see it ran


def test_a_tool_free_forge_cannot_break_the_turn(monkeypatch, tmp_path):
    b = _bridge(monkeypatch, tmp_path)
    b.forge = types.SimpleNamespace()                                           # no ethical_anchor at all
    b._record_self_check({"response": "x", "self_check_ran": True, "self_check_len": [10, 5]}, "hi")
