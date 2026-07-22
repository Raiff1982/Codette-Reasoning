"""
Tests for TimeTravelLens and InstitutionalExtractor.

All tests are pure Python — no model, no hardware, no network.
Run with:
    python -m pytest tests/test_time_travel_lens.py -v
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reasoning_forge.time_travel_lens import (
    ActorGap,
    ClosureClass,
    InstitutionalContextDetector,
    InstitutionalState,
    TimeTravelConfig,
    TimeTravelLens,
    TimestampLadder,
)
from reasoning_forge.institutional_extractor import InstitutionalExtractor


# ── Helpers ───────────────────────────────────────────────────────────────────

def _lens() -> TimeTravelLens:
    return TimeTravelLens(config=TimeTravelConfig.default())


def _state(
    t_op=None, t_inst=None,
    closure=ClosureClass.SUPPRESSED,
    energy=5.0,
    influence=None,
    actors=None,
) -> InstitutionalState:
    return InstitutionalState(
        state_id="test",
        ladder=TimestampLadder(t_op=t_op, t_inst=t_inst),
        closure_class=closure,
        unfolding_energy=energy,
        influence_over_time=influence or [10.0],
        actor_gaps=actors or [],
    )


def _days(year: int, month: int, day: int) -> float:
    from datetime import datetime
    epoch = datetime(1970, 1, 1)
    return (datetime(year, month, day) - epoch).total_seconds() / 86400.0


# ── Preemption gap ────────────────────────────────────────────────────────────

class TestPreemptionGap(unittest.TestCase):

    def test_finite_gap(self):
        s = _state(t_op=_days(2024, 1, 10), t_inst=_days(2024, 10, 10))
        Pi = _lens().preemption_gap(s)
        self.assertAlmostEqual(Pi, 274.0, delta=2.0)

    def test_infinite_when_t_inst_missing(self):
        s = _state(t_op=_days(2024, 1, 10))
        Pi = _lens().preemption_gap(s)
        self.assertTrue(math.isinf(Pi))

    def test_nan_when_both_missing(self):
        s = _state()
        Pi = _lens().preemption_gap(s)
        self.assertTrue(math.isnan(Pi))

    def test_zero_same_day(self):
        d = _days(2024, 6, 1)
        s = _state(t_op=d, t_inst=d)
        self.assertEqual(_lens().preemption_gap(s), 0.0)

    def test_negative_gap_is_allowed(self):
        # t_inst before t_op = institution acted before material event (rare but valid)
        s = _state(t_op=_days(2024, 6, 1), t_inst=_days(2024, 1, 1))
        self.assertLess(_lens().preemption_gap(s), 0)


# ── Closure score ─────────────────────────────────────────────────────────────

class TestClosureScore(unittest.TestCase):

    def test_all_classes(self):
        expected = {
            ClosureClass.CLOSED:        1.00,
            ClosureClass.DRIFT:         0.67,
            ClosureClass.SUPPRESSED:    0.24,
            ClosureClass.INEXPRESSIBLE: 0.00,
        }
        lens = _lens()
        for cls, score in expected.items():
            s = _state(closure=cls)
            self.assertAlmostEqual(lens.closure_score(s), score)


# ── Rupture indicator ─────────────────────────────────────────────────────────

class TestRuptureIndicator(unittest.TestCase):

    def test_rupture_when_t_op_set_and_not_closed(self):
        s = _state(t_op=100.0, closure=ClosureClass.SUPPRESSED)
        self.assertEqual(_lens().rupture_indicator(s), 1)

    def test_no_rupture_when_closed(self):
        s = _state(t_op=100.0, closure=ClosureClass.CLOSED)
        self.assertEqual(_lens().rupture_indicator(s), 0)

    def test_no_rupture_when_t_op_missing(self):
        s = _state(closure=ClosureClass.SUPPRESSED)
        self.assertEqual(_lens().rupture_indicator(s), 0)


# ── Beacon indicator ──────────────────────────────────────────────────────────

class TestBeaconIndicator(unittest.TestCase):

    def test_beacon_when_rupture_and_high_influence(self):
        s = _state(t_op=100.0, closure=ClosureClass.SUPPRESSED,
                   influence=[10.0] * 15)   # 150 > tau_I=100
        self.assertEqual(_lens().beacon_indicator(s), 1)

    def test_no_beacon_when_influence_low(self):
        s = _state(t_op=100.0, closure=ClosureClass.SUPPRESSED,
                   influence=[1.0] * 5)     # 5 < tau_I=100
        self.assertEqual(_lens().beacon_indicator(s), 0)

    def test_no_beacon_without_rupture(self):
        s = _state(closure=ClosureClass.CLOSED, influence=[1000.0])
        self.assertEqual(_lens().beacon_indicator(s), 0)


# ── High preemption zone ──────────────────────────────────────────────────────

class TestHighPreemptionZone(unittest.TestCase):

    def _automotive_state(self) -> InstitutionalState:
        """The automotive recall example from howitworks.txt."""
        return _state(
            t_op=_days(2024, 1, 10),
            t_inst=_days(2024, 10, 10),   # 273-day gap
            closure=ClosureClass.SUPPRESSED,
            energy=15.0,
            actors=[
                ActorGap("engineers", t_op_i=_days(2024, 1, 10), t_inst_i=_days(2024, 1, 12)),
                ActorGap("management", t_op_i=_days(2024, 3, 1),  t_inst_i=_days(2024, 9, 1)),
                ActorGap("legal",      t_op_i=None,                t_inst_i=_days(2024, 10, 10)),
            ],
        )

    def test_automotive_is_high_preemption_zone(self):
        self.assertTrue(_lens().is_high_preemption_zone(self._automotive_state()))

    def test_not_high_zone_when_gap_small(self):
        s = _state(t_op=_days(2024, 1, 1), t_inst=_days(2024, 1, 5),  # 4 days < tau_Pi=30
                   closure=ClosureClass.SUPPRESSED)
        self.assertFalse(_lens().is_high_preemption_zone(s))

    def test_not_high_zone_when_closed(self):
        s = _state(t_op=_days(2024, 1, 1), t_inst=_days(2024, 10, 1),
                   closure=ClosureClass.CLOSED)   # C=1.0 ≥ tau_C=0.5
        self.assertFalse(_lens().is_high_preemption_zone(s))

    def test_not_high_zone_without_actor_variance(self):
        # All actors have identical gaps → variance = 0
        d_op = _days(2024, 1, 1)
        d_in = _days(2024, 10, 1)
        actors = [
            ActorGap("a", t_op_i=d_op, t_inst_i=d_in),
            ActorGap("b", t_op_i=d_op, t_inst_i=d_in),
        ]
        s = _state(t_op=d_op, t_inst=d_in, closure=ClosureClass.SUPPRESSED, actors=actors)
        self.assertFalse(_lens().is_high_preemption_zone(s))


# ── observe() bundle ──────────────────────────────────────────────────────────

class TestObserve(unittest.TestCase):

    def test_bundle_contains_expected_keys(self):
        s = _state(t_op=100.0, t_inst=374.0, closure=ClosureClass.SUPPRESSED)
        obs = _lens().observe(s)
        for key in ("state_id", "preemption_gap_days", "closure_score",
                    "closure_class", "rupture", "beacon",
                    "high_preemption_zone", "practical_non_closure",
                    "actor_gaps", "registration_fidelity_memo"):
            self.assertIn(key, obs)

    def test_inf_gap_serialises_as_none(self):
        s = _state(t_op=100.0)   # no t_inst → infinite gap
        obs = _lens().observe(s)
        self.assertIsNone(obs["preemption_gap_days"])

    def test_json_serialisable(self):
        import json
        s = _state(t_op=100.0, t_inst=374.0, closure=ClosureClass.SUPPRESSED)
        obs = _lens().observe(s)
        json.dumps(obs)   # must not raise


# ── Triangulated closure resolution ──────────────────────────────────────────

class TestResolveClosureClass(unittest.TestCase):

    def test_unanimous_returns_that_class(self):
        result = _lens().resolve_closure_class(
            ClosureClass.SUPPRESSED, ClosureClass.SUPPRESSED, ClosureClass.SUPPRESSED,
            fallback_class=ClosureClass.DRIFT,
        )
        self.assertEqual(result, ClosureClass.SUPPRESSED)

    def test_majority_wins(self):
        result = _lens().resolve_closure_class(
            ClosureClass.SUPPRESSED, ClosureClass.SUPPRESSED, ClosureClass.CLOSED,
            fallback_class=ClosureClass.DRIFT,
        )
        self.assertEqual(result, ClosureClass.SUPPRESSED)

    def test_tie_uses_fallback(self):
        result = _lens().resolve_closure_class(
            ClosureClass.SUPPRESSED, ClosureClass.CLOSED, ClosureClass.DRIFT,
            fallback_class=ClosureClass.DRIFT,
        )
        self.assertEqual(result, ClosureClass.DRIFT)

    def test_tie_without_fallback_uses_ordering(self):
        result = _lens().resolve_closure_class(
            ClosureClass.SUPPRESSED, ClosureClass.CLOSED, ClosureClass.DRIFT,
            fallback_class=ClosureClass.INEXPRESSIBLE,
            ordering=[ClosureClass.SUPPRESSED, ClosureClass.DRIFT, ClosureClass.CLOSED],
        )
        self.assertEqual(result, ClosureClass.SUPPRESSED)


# ── Context detector ──────────────────────────────────────────────────────────

class TestInstitutionalContextDetector(unittest.TestCase):

    def test_detects_institutional_text(self):
        text = "The company knew about the defect and failed to disclose it to regulators."
        self.assertTrue(InstitutionalContextDetector.is_relevant(text))

    def test_ignores_unrelated_text(self):
        text = "How do I sort a list in Python using the built-in sorted() function?"
        self.assertFalse(InstitutionalContextDetector.is_relevant(text))

    def test_threshold_is_respected(self):
        # "announcement" and "press release" are both in the keyword set
        text = "The company made an official announcement via press release."
        self.assertTrue(InstitutionalContextDetector.is_relevant(text))

    def test_empty_text_returns_false(self):
        self.assertFalse(InstitutionalContextDetector.is_relevant(""))


# ── InstitutionalExtractor ────────────────────────────────────────────────────

class TestInstitutionalExtractor(unittest.TestCase):

    def setUp(self):
        self.ext = InstitutionalExtractor(reference_year=2024)

    def test_automotive_example(self):
        text = (
            "On January 10, engineers quietly patched the braking system internally. "
            "The company suppressed the safety issue for months. "
            "On October 10, they finally filed the official recall with regulators."
        )
        state, conf = self.ext.extract(text)
        self.assertIsNotNone(state)
        self.assertGreater(conf, 0.0)
        # t_op should be populated (January 10)
        self.assertIsNotNone(state.ladder.t_op)

    def test_no_dates_returns_none(self):
        state, conf = self.ext.extract("The company suppressed the information entirely.")
        self.assertIsNone(state)
        self.assertEqual(conf, 0.0)

    def test_short_text_returns_none(self):
        state, conf = self.ext.extract("hi")
        self.assertIsNone(state)

    def test_suppressed_closure_class(self):
        text = (
            "On March 1 they discovered the flaw and concealed it. "
            "The company denied all knowledge until December 1 when they were forced to disclose."
        )
        state, conf = self.ext.extract(text)
        if state:  # depends on dateutil availability
            self.assertEqual(state.closure_class, ClosureClass.SUPPRESSED)

    def test_confidence_between_zero_and_one(self):
        text = (
            "On January 10 engineers patched the system. "
            "On October 10 it was officially reported to regulators."
        )
        state, conf = self.ext.extract(text)
        if state:
            self.assertGreaterEqual(conf, 0.0)
            self.assertLessEqual(conf, 1.0)

    def test_result_is_json_serialisable(self):
        import json
        text = (
            "On January 10 they secretly fixed it. "
            "On October 10 they officially disclosed the recall."
        )
        state, conf = self.ext.extract(text)
        if state and conf > 0:
            obs = TimeTravelLens(TimeTravelConfig.default()).observe(state)
            json.dumps(obs)   # must not raise


if __name__ == "__main__":
    unittest.main(verbosity=2)
