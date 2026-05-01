"""
DriftDetector unit tests.

Uses a synthetic kernel stub — no real LLM or disk I/O required.
"""

import sys
import os
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from reasoning_forge.drift_detector import (
    DriftDetector, DriftReport, InterventionPlan, LOCK_THRESHOLD, CONSECUTIVE_RISING
)


# ── Synthetic memory objects ──────────────────────────────────────────────────

class _FakeCocoon:
    def __init__(self, epsilon_band="medium", perspectives=None,
                 tensions=None, hooks=None, psi_r=0.5):
        self.epsilon_band = epsilon_band
        self.perspectives_active = perspectives or []
        self.unresolved_tensions = tensions or []
        self.follow_up_hooks = hooks or []
        self.psi_r = psi_r
        self.importance = 7
        self.emotional_tag = "insight"
        self.active_project = "Codette-Reasoning"
        self.user_facts = {}
        self.timestamp = time.time()


class _FakeKernel:
    def __init__(self, memories):
        self.memories = memories

    def continuity_profile(self):
        perspective_usage = {}
        epsilon_distribution = {"low": 0, "medium": 0, "high": 0, "max": 0}
        open_hooks = []
        open_tensions = []

        for m in self.memories:
            if m.epsilon_band in epsilon_distribution:
                epsilon_distribution[m.epsilon_band] += 1
            for p in m.perspectives_active:
                perspective_usage[p] = perspective_usage.get(p, 0) + 1
            open_hooks.extend(m.follow_up_hooks)
            open_tensions.extend(m.unresolved_tensions)

        dominant = max(perspective_usage, key=perspective_usage.get) if perspective_usage else ""
        return {
            "total_cocoons": len(self.memories),
            "open_hooks": list(dict.fromkeys(open_hooks))[:20],
            "open_tensions": list(dict.fromkeys(open_tensions))[:20],
            "user_facts": {},
            "dominant_project": "Codette-Reasoning",
            "dominant_perspective": dominant,
            "perspective_usage": perspective_usage,
            "epsilon_distribution": epsilon_distribution,
            "emotional_profile": {},
        }

    def recall_with_hooks(self, limit=20):
        return [m for m in self.memories if m.follow_up_hooks][:limit]

    def recall_recent(self, limit=10):
        return sorted(self.memories, key=lambda m: m.timestamp, reverse=True)[:limit]


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestDriftDetector(unittest.TestCase):

    def _detector(self):
        return DriftDetector()

    # Null safety

    def test_none_kernel_returns_empty_report(self):
        report = self._detector().detect(None)
        self.assertIsInstance(report, DriftReport)
        self.assertEqual(report.total_cocoons, 0)
        self.assertEqual(report.epsilon_trend, "unknown")

    def test_empty_kernel_stable_trend(self):
        kernel = _FakeKernel([])
        report = self._detector().detect(kernel)
        self.assertEqual(report.total_cocoons, 0)
        self.assertIn(report.epsilon_trend, ("stable", "unknown"))

    # Epsilon trend detection

    def test_rising_epsilon(self):
        cocoons = [
            _FakeCocoon("low"), _FakeCocoon("low"),
            _FakeCocoon("medium"), _FakeCocoon("medium"),
            _FakeCocoon("high"), _FakeCocoon("high"),
            _FakeCocoon("max"), _FakeCocoon("max"),
        ]
        report = self._detector().detect(_FakeKernel(cocoons))
        self.assertEqual(report.epsilon_trend, "rising",
                         f"Expected rising, slope={report.epsilon_slope:.4f}")
        self.assertGreater(report.epsilon_slope, 0)

    def test_falling_epsilon(self):
        cocoons = [
            _FakeCocoon("max"), _FakeCocoon("max"),
            _FakeCocoon("high"), _FakeCocoon("high"),
            _FakeCocoon("medium"), _FakeCocoon("medium"),
            _FakeCocoon("low"), _FakeCocoon("low"),
        ]
        report = self._detector().detect(_FakeKernel(cocoons))
        self.assertEqual(report.epsilon_trend, "falling",
                         f"Expected falling, slope={report.epsilon_slope:.4f}")
        self.assertLess(report.epsilon_slope, 0)

    def test_stable_epsilon(self):
        cocoons = [_FakeCocoon("medium")] * 10
        report = self._detector().detect(_FakeKernel(cocoons))
        self.assertEqual(report.epsilon_trend, "stable")
        self.assertAlmostEqual(report.epsilon_slope, 0.0, places=4)

    # Perspective lock

    def test_perspective_lock_detected(self):
        physics = _FakeCocoon(perspectives=["physics_agent"])
        ethics  = _FakeCocoon(perspectives=["ethics_agent"])
        cocoons = [physics] * 8 + [ethics] * 2
        report = self._detector().detect(_FakeKernel(cocoons))
        self.assertTrue(report.perspective_lock,
                        f"Expected lock at ratio={report.perspective_lock_ratio:.2f}")
        self.assertEqual(report.dominant_perspective, "physics_agent")
        self.assertGreater(report.perspective_lock_ratio, LOCK_THRESHOLD)

    def test_balanced_perspectives_no_lock(self):
        cocoons = [
            _FakeCocoon(perspectives=["physics_agent"]),
            _FakeCocoon(perspectives=["ethics_agent"]),
            _FakeCocoon(perspectives=["consciousness_agent"]),
            _FakeCocoon(perspectives=["creativity_agent"]),
        ]
        report = self._detector().detect(_FakeKernel(cocoons))
        self.assertFalse(report.perspective_lock)

    # Recurring tensions

    def test_recurring_tension_detected(self):
        tension = "privacy vs safety"
        cocoons = [_FakeCocoon(tensions=[tension])] * 5
        report = self._detector().detect(_FakeKernel(cocoons))
        self.assertTrue(report.recurring_tensions,
                        "Expected at least one recurring tension")
        labels = [t for t, _ in report.recurring_tensions]
        self.assertIn(tension, labels)
        count = dict(report.recurring_tensions)[tension]
        self.assertGreaterEqual(count, 3)

    def test_rare_tension_not_recurring(self):
        cocoons = [_FakeCocoon(tensions=["unique issue"])] * 2
        report = self._detector().detect(_FakeKernel(cocoons))
        # Count=2 < RECURRING_MIN=3, should not appear
        labels = [t for t, _ in report.recurring_tensions]
        self.assertNotIn("unique issue", labels)

    # Open hooks

    def test_open_hooks_counted(self):
        cocoons = [
            _FakeCocoon(hooks=["Follow up on X", "Revisit Y"]),
            _FakeCocoon(hooks=["Explore Z"]),
            _FakeCocoon(hooks=[]),
        ]
        report = self._detector().detect(_FakeKernel(cocoons))
        self.assertEqual(report.open_hook_count, 3)
        self.assertLessEqual(len(report.hooks_sample), 5)

    def test_no_hooks_zero_count(self):
        cocoons = [_FakeCocoon(hooks=[])] * 5
        report = self._detector().detect(_FakeKernel(cocoons))
        self.assertEqual(report.open_hook_count, 0)

    # Output methods

    def test_summary_returns_string(self):
        cocoons = [_FakeCocoon("high", ["physics_agent"], ["x vs y"], ["follow up"])]
        report = self._detector().detect(_FakeKernel(cocoons))
        s = report.summary()
        self.assertIsInstance(s, str)
        self.assertIn("ε trend", s)

    def test_to_dict_is_serializable(self):
        import json
        cocoons = [_FakeCocoon("high", ["physics_agent"], ["x vs y"])]
        report = self._detector().detect(_FakeKernel(cocoons))
        d = report.to_dict()
        json.dumps(d)  # should not raise

    def test_to_dict_keys(self):
        report = self._detector().detect(_FakeKernel([]))
        d = report.to_dict()
        for key in ("epsilon_trend", "epsilon_slope", "epsilon_mean",
                    "perspective_lock", "recurring_tensions",
                    "open_hook_count", "total_cocoons", "psi_r_history"):
            self.assertIn(key, d)


class TestInterventionPlan(unittest.TestCase):

    def _detector(self):
        return DriftDetector()

    def test_no_intervention_on_balanced(self):
        cocoons = [
            _FakeCocoon(perspectives=["physics_agent"]),
            _FakeCocoon(perspectives=["ethics_agent"]),
            _FakeCocoon(perspectives=["creativity_agent"]),
        ]
        report = self._detector().detect(_FakeKernel(cocoons))
        plan = self._detector().should_intervene(report, [])
        self.assertFalse(plan.active)
        self.assertIsNone(plan.inject_perspective)
        self.assertFalse(plan.calibration_warning)

    def test_perspective_lock_triggers_injection(self):
        physics = _FakeCocoon(perspectives=["physics_agent"])
        ethics  = _FakeCocoon(perspectives=["ethics_agent"])
        cocoons = [physics] * 8 + [ethics] * 2
        report = self._detector().detect(_FakeKernel(cocoons))
        plan = self._detector().should_intervene(report, [])
        self.assertTrue(plan.active)
        self.assertEqual(plan.inject_perspective, "ethics_agent")
        self.assertTrue(plan.reasons)

    def test_calibration_warning_after_consecutive_rising(self):
        trend_history = ["rising"] * CONSECUTIVE_RISING
        report = DriftReport()  # empty report — only trend_history matters here
        plan = self._detector().should_intervene(report, trend_history)
        self.assertTrue(plan.calibration_warning)
        self.assertTrue(plan.reasons)

    def test_no_calibration_warning_below_threshold(self):
        trend_history = ["rising"] * (CONSECUTIVE_RISING - 1)
        report = DriftReport()
        plan = self._detector().should_intervene(report, trend_history)
        self.assertFalse(plan.calibration_warning)

    def test_psi_r_history_populated(self):
        psi_vals = [0.3, 0.45, 0.6, 0.72, 0.81]
        cocoons = [_FakeCocoon(psi_r=v) for v in psi_vals]
        report = self._detector().detect(_FakeKernel(cocoons))
        self.assertEqual(len(report.psi_r_history), len(psi_vals))
        self.assertAlmostEqual(report.psi_r_history[-1], psi_vals[-1], places=3)

    def test_psi_r_history_in_to_dict(self):
        import json
        psi_vals = [0.4, 0.55, 0.7]
        cocoons = [_FakeCocoon(psi_r=v) for v in psi_vals]
        report = self._detector().detect(_FakeKernel(cocoons))
        d = report.to_dict()
        self.assertIn("psi_r_history", d)
        json.dumps(d)  # must be serializable


if __name__ == "__main__":
    unittest.main(verbosity=2)
