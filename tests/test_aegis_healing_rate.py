"""AEGIS Layer 5 healing rate: 'never looked' must not read as 'nothing needed healing'.

Before 2026-10-01 healing_rate was healing_applied / total_calls, which is 0.0
both when Layer 5 ran and found nothing and when it was skipped on every call.
generate_v2 has no callers, so it was skipped on every call, and the dashboard
showed a calm 0%.
"""
import time

from Protection_Layer.aegis_metrics_engine import AEGISMetricsEngine


def _call(engine, action, applied=False):
    engine.log_forge_execution({
        "timestamp": time.time(), "concept": "c", "healing_action": action,
        "layer5_healing_applied": applied, "valid": True,
    })


def test_never_looked_is_unmeasured_not_zero(tmp_path):
    e = AEGISMetricsEngine(db_path=tmp_path / "m.db")
    _call(e, None)
    _call(e, "")
    s = e.get_statistics()
    assert s["total_forge_calls"] == 2
    assert s["layer5_ran"] == 0
    assert s["layer5_skipped"] == 2
    assert s["healing_rate"] is None
    assert "did not run" in s["healing_rate_note"]


def test_ran_and_found_nothing_is_a_real_zero(tmp_path):
    e = AEGISMetricsEngine(db_path=tmp_path / "m.db")
    _call(e, "none")
    _call(e, "none")
    s = e.get_statistics()
    assert s["layer5_ran"] == 2
    assert s["healing_rate"] == 0.0
    assert s["healing_rate_note"] is None


def test_rate_is_over_the_calls_where_layer5_looked(tmp_path):
    e = AEGISMetricsEngine(db_path=tmp_path / "m.db")
    _call(e, None)            # skipped: not in the denominator
    _call(e, "none")
    _call(e, "adjust", applied=True)
    s = e.get_statistics()
    assert s["layer5_ran"] == 2
    assert s["layer5_skipped"] == 1
    assert s["healing_rate"] == 50.0


def test_no_calls_is_not_zero_percent_rejected(tmp_path):
    # Same class as healing_rate: "0% rejected" over zero calls reads as a clean record.
    e = AEGISMetricsEngine(db_path=tmp_path / "m.db")
    assert e.get_statistics()["rejection_rate"] is None
    _call(e, "none")
    assert e.get_statistics()["rejection_rate"] == 0.0     # a call that was valid: a real zero
