"""Tests for the adapter-boost ratchet fix (2026-07-24).

The old rule only ever ADDED to the most-used adapter -> boosts climbed to the cap
and never came down (clean-traffic shadow review: 26 up / 2 down). These tests pin
the fixed behavior: bounded equilibrium, real down-moves, and no reward for a
single-adapter window (the benchmark-contamination pattern).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.quantum_optimizer import QuantumOptimizer, QualitySignal


def sig(adapter, coherence):
    return QualitySignal(
        timestamp=0.0, adapter=adapter, coherence=coherence, tension=0.4,
        productivity=0.9, response_length=100, multi_perspective=False,
    )


def test_single_adapter_window_gets_no_reward():
    # The benchmark pattern: one adapter dominates the window. Must NOT be rewarded.
    opt = QuantumOptimizer()
    opt._tune_adapter_boosts([sig("newton", 0.95)] * 10, current_quality=0.9, momentum_factor=1.0)
    assert opt.state.adapter_boosts.get("newton", 0.0) == 0.0


def test_best_adapter_rewarded_only_if_it_beats_peers():
    opt = QuantumOptimizer()
    recent = [sig("newton", 0.95)] * 5 + [sig("empathy", 0.5)] * 5
    opt._tune_adapter_boosts(recent, current_quality=0.9, momentum_factor=1.0)
    assert opt.state.adapter_boosts.get("newton", 0.0) > 0.0     # winner rewarded
    assert opt.state.adapter_boosts.get("empathy", 0.0) == 0.0   # below-mean: nothing


def test_boost_is_bounded_not_a_ratchet():
    # A consistent winner should settle at a bounded equilibrium BELOW the cap,
    # not climb to 0.3 and pin there.
    opt = QuantumOptimizer()
    opt.learning_rate = 0.02
    for _ in range(200):
        opt._tune_adapter_boosts(
            [sig("newton", 0.95)] * 3 + [sig("empathy", 0.4)] * 3,
            current_quality=0.9, momentum_factor=1.0,
        )
    b = opt.state.adapter_boosts.get("newton", 0.0)
    assert 0.0 < b < 0.3    # bounded equilibrium, not pinned at the cap


def test_unreinforced_boost_decays_down():
    opt = QuantumOptimizer()
    opt.state.adapter_boosts["davinci"] = 0.2   # pre-existing boost
    # davinci is NOT in this window -> it should decay.
    opt._tune_adapter_boosts(
        [sig("newton", 0.9)] * 3 + [sig("empathy", 0.8)] * 3,
        current_quality=0.9, momentum_factor=1.0,
    )
    assert opt.state.adapter_boosts.get("davinci", 0.0) < 0.2    # decayed downward


def test_down_moves_are_recorded():
    # The ratchet is broken only if DOWN steps actually appear in history.
    opt = QuantumOptimizer()
    opt.state.adapter_boosts["davinci"] = 0.2
    opt._tune_adapter_boosts(
        [sig("newton", 0.9)] * 3 + [sig("empathy", 0.8)] * 3,
        current_quality=0.9, momentum_factor=1.0,
    )
    downs = [h for h in opt.history if h.new_value < h.old_value]
    assert downs, "no down-moves recorded — ratchet not broken"
    assert any("decay" in h.reason for h in downs)


def test_boost_never_exceeds_cap():
    opt = QuantumOptimizer()
    opt.learning_rate = 0.5   # deliberately large
    for _ in range(50):
        opt._tune_adapter_boosts(
            [sig("newton", 0.95)] * 3 + [sig("empathy", 0.4)] * 3,
            current_quality=0.9, momentum_factor=1.0,
        )
    assert opt.state.adapter_boosts.get("newton", 0.0) <= 0.3


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call(["pytest", "-q", __file__]))
