"""Bugs found by reading the forge components before wiring them (2026-10-22)."""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reasoning_forge.memory_kernel import DynamicMemoryEngine
from reasoning_forge.routing_metrics import RoutingMetrics


def _rec(primary, conf, secondary=(), boost=0.0):
    return RoutingMetrics.create_record(
        "q", primary, list(secondary), "keyword", conf - boost, conf, boost != 0.0)


def test_confidence_average_ignores_secondary_picks():
    m = RoutingMetrics()
    m.record_route(_rec("newton", 0.9))
    m.record_route(_rec("empathy", 0.5, secondary=["newton"]))   # newton picked, not primary
    m.record_route(_rec("newton", 0.7))
    # newton's confidence updates were 0.9 and 0.7 -> 0.8. Dividing by its selection count
    # (3, because of the secondary pick) gave 0.8333... then drifted further.
    assert abs(m.adapter_avg_confidence["newton"] - 0.8) < 1e-9


def test_boost_magnitude_is_a_real_average_not_the_latest_value():
    m = RoutingMetrics()
    m.record_route(_rec("newton", 0.9, boost=0.1))
    m.record_route(_rec("newton", 0.9, boost=0.3))
    assert abs(m.adapter_avg_boost_magnitude["newton"] - 0.2) < 1e-9


def _kernel(importance, age_s, now):
    mem = types.SimpleNamespace(importance=importance, timestamp=now - age_s,
                                title="t", anchor="a" * 8)
    return types.SimpleNamespace(memories=[mem]), mem


def test_decay_composes_across_calls_and_uses_a_true_half_life():
    now = 1_000_000.0
    week = DynamicMemoryEngine.DECAY_HALF_LIFE
    k, mem = _kernel(10, age_s=30 * 86400, now=now)      # old memory: age must not matter
    eng = DynamicMemoryEngine(k)
    eng.decay_importance(now)                            # first call only sets the clock
    assert mem.importance == 10
    eng.decay_importance(now + week)                     # one half-life later
    assert mem.importance == 5
    # Many tiny steps equal one big one; the old code compounded the whole age each time.
    k2, mem2 = _kernel(10, age_s=30 * 86400, now=now)
    e2 = DynamicMemoryEngine(k2)
    e2.decay_importance(now)
    for i in range(1, 8):
        e2.decay_importance(now + i * week / 7)
    assert mem2.importance in (5, 6)                     # rounding at each step, not collapse to 1


# Amended 2026-10-22: a test for ReflectionJournal's default path lived here. The class was retired the
# same day (archive/2026-10-22-retired-wisdom-reflection/), so its test went with it.
