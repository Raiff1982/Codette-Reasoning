"""SubstrateMonitor's violation rate is a rate over the inference window.

Before 2026-11-17 it divided the lifetime violation count by at most 20
inferences, so a constant true rate read higher the longer a session ran.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "inference"))

import substrate_awareness as sa  # noqa: E402


def _monitor():
    m = sa.SubstrateMonitor()
    m._cache_ttl = 0          # measure every call
    return m


def _rate_after(turns, every):
    m = _monitor()
    for i in range(turns):
        if i % every == 0:
            m.record_violation("x")
        m.record_inference(1000)
    return m.snapshot()["adapter_violation_rate"]


def test_a_constant_true_rate_reads_the_same_however_long_the_session():
    assert _rate_after(20, 2) == _rate_after(40, 2) == _rate_after(100, 2) == 0.25


def test_the_rate_falls_back_once_violations_leave_the_window():
    m = _monitor()
    for _ in range(30):
        m.record_violation("x")
        m.record_inference(1000)
    assert m.snapshot()["adapter_violation_rate"] == 0.5
    for _ in range(20):
        m.record_inference(1000)
    assert m.snapshot()["adapter_violation_rate"] == 0.0


def test_adapter_health_still_keeps_the_lifetime_history():
    m = _monitor()
    for _ in range(30):
        m.record_violation("x")
        m.record_inference(1000)
    for _ in range(20):
        m.record_inference(1000)
    assert m.get_adapter_health() == {"x": 0.5}
