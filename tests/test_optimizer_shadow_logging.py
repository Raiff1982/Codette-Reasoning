"""Regression tests: the shadow log silently dropped every unmeasured-productivity turn.

Root cause, found 2026-08-10 while investigating why `user_continued` was None in
every record: `_log_turn` did `round(float(productivity), 4)`, but `productivity`
is deliberately None when `render_fidelity` was not measured (the 2026-08-03
change that stopped fabricating it as 0.5). `float(None)` raises TypeError, and
`_log_turn`'s `except Exception: pass` — written so logging could never break a
turn — converted that into silent data loss. The whole record was discarded,
taking its `user_continued` measurement with it.

So `user_continued` was not unmeasured. It was measured and thrown away.

The telemetry call had the same bug one line down, except there the TypeError
escaped `observe()` entirely, so `_persist()` never ran either and the
optimizer's own state stopped being saved.

These tests fail against the previous implementation.
"""
import json

import pytest

from reasoning_forge import optimizer_shadow


@pytest.fixture
def shadow(tmp_path, monkeypatch):
    """A ShadowOptimizer writing to a temp log, with telemetry disabled."""
    monkeypatch.setattr(optimizer_shadow, "_LOG_PATH", tmp_path / "shadow.jsonl")
    monkeypatch.setattr(optimizer_shadow, "_STATE_PATH", tmp_path / "state.json")
    s = optimizer_shadow.ShadowOptimizer()
    s._telemetry = None
    return s


def _records(tmp_path):
    p = tmp_path / "shadow.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


class TestUnmeasuredProductivityIsStillRecorded:
    def test_turn_without_render_fidelity_is_not_dropped(self, shadow, tmp_path):
        # THE BUG: this turn vanished entirely.
        shadow.observe(adapter="empathy", coherence=0.75, tension=0.3,
                       multi_perspective=False, render_fidelity=None)
        assert len(_records(tmp_path)) == 1, "turn was silently discarded"

    def test_productivity_is_recorded_as_null_not_fabricated(self, shadow, tmp_path):
        shadow.observe(adapter="empathy", coherence=0.75, tension=0.3,
                       multi_perspective=False, render_fidelity=None)
        sig = _records(tmp_path)[0]["signals"]
        assert sig["productivity"] is None
        assert sig["productivity_measured"] is False

    def test_measured_productivity_still_recorded_normally(self, shadow, tmp_path):
        shadow.observe(adapter="newton", coherence=0.8, tension=0.2,
                       multi_perspective=True, render_fidelity=0.9032)
        sig = _records(tmp_path)[0]["signals"]
        assert sig["productivity"] == pytest.approx(0.9032)
        assert sig["productivity_measured"] is True


class TestEngagementSurvivesTheLoggingPath:
    """The point of the fix: user_continued has to reach the log."""

    @pytest.mark.parametrize("value", [True, False])
    def test_user_continued_survives_when_productivity_unmeasured(
            self, shadow, tmp_path, value):
        shadow.observe(adapter="philosophy", coherence=0.7, tension=None,
                       multi_perspective=False, render_fidelity=None,
                       user_continued=value,
                       engagement_reason="follow-up builds on the answer")
        sig = _records(tmp_path)[0]["signals"]
        assert sig["user_continued"] is value
        assert sig["user_continued_measured"] is True
        assert sig["engagement_reason"] == "follow-up builds on the answer"

    def test_abstention_is_still_recorded_as_absence(self, shadow, tmp_path):
        # None must mean "not measured", never be fabricated into False.
        shadow.observe(adapter="philosophy", coherence=0.7, tension=None,
                       multi_perspective=False, render_fidelity=None,
                       user_continued=None, engagement_reason="topic change")
        sig = _records(tmp_path)[0]["signals"]
        assert sig["user_continued"] is None
        assert sig["user_continued_measured"] is False


class TestObserveDoesNotRaise:
    def test_observe_completes_so_persist_is_reached(self, shadow, tmp_path):
        # The telemetry line raised OUT of observe(), so _persist() never ran.
        # Re-enable a recording telemetry stub and prove observe() returns.
        calls = []

        class _Tel:
            def record(self, **kw):
                calls.append(kw)

        shadow._telemetry = _Tel()
        shadow.observe(adapter="davinci", coherence=0.66, tension=None,
                       multi_perspective=False, render_fidelity=None)
        assert calls, "telemetry never reached — observe() raised before it"
        assert calls[0]["productivity"] == -1.0, "sentinel for 'not measured'"
        assert (tmp_path / "state.json").exists(), "_persist() never ran"


class TestBenchmarkTurnsStillExcluded:
    def test_benchmark_traffic_is_still_dropped(self, shadow, tmp_path):
        # Pre-existing behaviour that must not regress: exam traffic is not
        # evidence about conversational routing.
        shadow.observe(adapter="newton", coherence=0.9, tension=0.1,
                       multi_perspective=False, render_fidelity=0.8,
                       is_benchmark=True)
        assert _records(tmp_path) == []

    def test_missing_coherence_is_still_dropped(self, shadow, tmp_path):
        shadow.observe(adapter="newton", coherence=None, tension=0.1,
                       multi_perspective=False, render_fidelity=0.8)
        assert _records(tmp_path) == []
