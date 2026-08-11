"""Tests for the recovered Metrics layer on NexisSignalEngine.

`Metrics` was recovered 2026-08-10 from a divergent copy of the engine
(`OneDrive_2_8-10-2026.zip!Nexus/import json.py`). The class itself arrived
verbatim; the instrumentation wrapper around `process()` is new, so it is the
part that most needs covering — particularly that counting a failure does not
swallow it.

See docs/RECOVERY_2026-08-10.md.
"""
import pytest

from reasoning_forge.nexis_signal_engine import Metrics, NexisSignalEngine


class TestMetrics:
    """The recovered class, in isolation. No engine, no I/O."""

    def test_starts_empty(self):
        m = Metrics()
        assert m.get_stats() == {"avg_process_time": 0.0, "error_count": 0}

    def test_avg_process_time(self):
        m = Metrics()
        for d in (1.0, 2.0, 3.0):
            m.record_process_time(d)
        assert m.get_stats()["avg_process_time"] == pytest.approx(2.0)

    def test_empty_average_does_not_divide_by_zero(self):
        # max(len, 1) in get_stats is load-bearing
        assert Metrics().get_stats()["avg_process_time"] == 0.0

    def test_ring_is_bounded_at_1000(self):
        m = Metrics()
        for i in range(1500):
            m.record_process_time(float(i))
        assert len(m.process_times) == 1000
        # the oldest 500 were dropped, so it holds 500..1499
        assert m.process_times[0] == 500.0
        assert m.process_times[-1] == 1499.0

    def test_error_count(self):
        m = Metrics()
        m.record_error()
        m.record_error()
        assert m.get_stats()["error_count"] == 2


class _Stub(NexisSignalEngine):
    """Bypass __init__ so the wrapper can be tested without a database."""

    def __init__(self, blow_up=False):
        self.metrics = Metrics()
        self._blow_up = blow_up
        self.calls = 0

    def _process_impl(self, input_signal):
        self.calls += 1
        if self._blow_up:
            raise RuntimeError("boom")
        return {"input": input_signal, "verdict": "ok"}


class TestProcessInstrumentation:
    """The wrapper added around process(). New code, not recovered."""

    def test_result_is_passed_through_unchanged(self):
        e = _Stub()
        assert e.process("hello") == {"input": "hello", "verdict": "ok"}
        assert e.calls == 1

    def test_success_records_a_timing_and_no_error(self):
        e = _Stub()
        e.process("hello")
        stats = e.get_metrics()
        assert len(e.metrics.process_times) == 1
        assert stats["error_count"] == 0
        assert stats["avg_process_time"] >= 0.0

    def test_failure_is_counted_AND_re_raised(self):
        # The whole point: instrumentation must not swallow the exception.
        e = _Stub(blow_up=True)
        with pytest.raises(RuntimeError, match="boom"):
            e.process("hello")
        assert e.get_metrics()["error_count"] == 1

    def test_failure_still_records_a_timing(self):
        # recorded in `finally`, so a failed call is still measured
        e = _Stub(blow_up=True)
        with pytest.raises(RuntimeError):
            e.process("hello")
        assert len(e.metrics.process_times) == 1

    def test_counts_accumulate_across_calls(self):
        e = _Stub()
        for _ in range(3):
            e.process("x")
        assert len(e.metrics.process_times) == 3
        assert e.get_metrics()["error_count"] == 0
