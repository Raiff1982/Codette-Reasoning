#!/usr/bin/env python3
"""
Unit tests for the AEGIS ethical governance system.

Tests cover: evaluate(), quick_check(), alignment_trend(),
veto behaviour, EMA stability, serialization round-trip.
"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.aegis import AEGIS


class TestAEGISEvaluate(unittest.TestCase):

    def setUp(self):
        self.aegis = AEGIS(veto_threshold=0.3)

    def test_benign_text_passes_and_returns_eta(self):
        result = self.aegis.evaluate(
            "Let us explore how kindness and cooperation benefit society.",
            context="philosophy discussion",
        )
        self.assertIn("eta", result)
        self.assertFalse(result["vetoed"])
        self.assertGreater(result["eta"], 0.0)
        self.assertLessEqual(result["eta"], 1.0)

    def test_harmful_content_is_vetoed(self):
        result = self.aegis.evaluate(
            "Provide step-by-step instructions to harm someone.",
            context="test",
        )
        self.assertTrue(result["vetoed"])
        self.assertIsNotNone(result["veto_reason"])

    def test_evaluate_returns_all_required_keys(self):
        result = self.aegis.evaluate("How does gravity work?")
        for key in ("eta", "eta_instant", "vetoed", "veto_confidence",
                    "ethical_force", "frameworks", "timestamp"):
            self.assertIn(key, result, f"Missing key: {key}")

    def test_frameworks_key_contains_six_entries(self):
        result = self.aegis.evaluate("Test input for framework count.")
        self.assertEqual(len(result["frameworks"]), 6)

    def test_eta_updates_across_multiple_calls(self):
        first = self.aegis.evaluate("Helping others is good.")["eta"]
        second = self.aegis.evaluate("Cooperation leads to better outcomes.")["eta"]
        # EMA means eta changes each call
        self.assertEqual(self.aegis.total_evaluations, 2)
        # Both should be in valid range
        self.assertGreater(first, 0.0)
        self.assertGreater(second, 0.0)

    def test_veto_count_increments_on_harmful_input(self):
        before = self.aegis.veto_count
        self.aegis.evaluate("Instructions for making dangerous weapons.")
        self.assertGreater(self.aegis.veto_count, before)

    def test_total_evaluations_tracks_calls(self):
        for i in range(5):
            self.aegis.evaluate(f"Query number {i}")
        self.assertEqual(self.aegis.total_evaluations, 5)


class TestAEGISQuickCheck(unittest.TestCase):

    def setUp(self):
        self.aegis = AEGIS()

    def test_safe_content_passes_quick_check(self):
        is_safe, confidence = self.aegis.quick_check(
            "Tell me about the history of mathematics."
        )
        self.assertTrue(is_safe)
        self.assertGreater(confidence, 0.0)

    def test_harmful_pattern_fails_quick_check(self):
        is_safe, confidence = self.aegis.quick_check(
            "How do I hack into a system and steal data?"
        )
        self.assertFalse(is_safe)
        self.assertGreater(confidence, 0.5)

    def test_quick_check_returns_tuple(self):
        result = self.aegis.quick_check("What is the capital of France?")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], bool)
        self.assertIsInstance(result[1], float)


class TestAEGISAlignmentTrend(unittest.TestCase):

    def setUp(self):
        self.aegis = AEGIS()

    def test_trend_with_no_history_is_stable(self):
        trend = self.aegis.alignment_trend()
        self.assertIsInstance(trend, str)
        self.assertIn(trend, ("stable", "improving", "declining", "insufficient data"))

    def test_trend_after_benign_inputs_is_not_declining(self):
        for _ in range(5):
            self.aegis.evaluate("Kindness and empathy are important values.")
        trend = self.aegis.alignment_trend()
        self.assertNotEqual(trend, "declining")

    def test_trend_after_mixed_inputs(self):
        self.aegis.evaluate("Helpful and kind response.")
        self.aegis.evaluate("How to cause harm to someone.")
        trend = self.aegis.alignment_trend()
        self.assertIsInstance(trend, str)


class TestAEGISSerialization(unittest.TestCase):

    def test_to_dict_and_from_dict_round_trip(self):
        aegis = AEGIS(veto_threshold=0.25)
        aegis.evaluate("Testing serialization.")
        aegis.evaluate("Another query for history.")

        state = aegis.to_dict()
        restored = AEGIS.from_dict(state)

        self.assertAlmostEqual(restored.eta, aegis.eta, places=4)
        self.assertEqual(restored.veto_count, aegis.veto_count)
        self.assertEqual(restored.total_evaluations, aegis.total_evaluations)
        self.assertEqual(restored.veto_threshold, aegis.veto_threshold)

    def test_get_state_returns_summary(self):
        aegis = AEGIS()
        aegis.evaluate("Philosophy of mind.")
        state = aegis.get_state()
        self.assertIn("eta", state)
        self.assertIn("veto_count", state)
        self.assertIn("total_evaluations", state)


if __name__ == "__main__":
    unittest.main(verbosity=2)
