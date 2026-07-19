"""Tests for the substrate degradation composition policy.

The policy decides WHICH perspective survives when substrate pressure forces
an adapter-count cut. See HealthAwareRouter.apply_degradation_policy.

The core is a pure classmethod, so these run without hardware or an LLM.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from inference.substrate_awareness import HealthAwareRouter as R


class FakeMonitor:
    """Stand-in for SubstrateMonitor with a fixed pressure level."""

    def __init__(self, level="critical"):
        self.level = level

    def snapshot(self):
        return {"level": self.level}


def make_router(level="critical"):
    """Build a router without running __init__ (no psutil / hardware needed)."""
    r = R.__new__(R)
    r.monitor = FakeMonitor(level)
    return r


class TestDegradationPolicyNoOps(unittest.TestCase):
    """Conditions under which the policy must leave routing untouched."""

    def test_noop_under_low_pressure(self):
        ranked = [("empathy", 1.0), ("newton", 0.9)]
        for level in ("idle", "low", "moderate"):
            out, notes = R.apply_degradation_policy(ranked, level, max_adapters=1)
            self.assertEqual(out, ranked, f"reordered at level={level}")
            self.assertEqual(notes, [])

    def test_noop_when_no_cut_is_happening(self):
        """If max_adapters covers every candidate, nothing is being dropped."""
        ranked = [("empathy", 1.0), ("newton", 0.95)]
        out, notes = R.apply_degradation_policy(ranked, "critical", max_adapters=2)
        self.assertEqual(out, ranked)
        self.assertEqual(notes, [])

    def test_noop_on_decisive_winner(self):
        """A clear keyword match must survive pressure untouched.

        This is the guard against an emotional query getting hijacked by an
        analytical adapter just because the machine is busy.
        """
        ranked = [("empathy", 1.0), ("newton", 0.2)]
        out, notes = R.apply_degradation_policy(ranked, "critical", max_adapters=1)
        self.assertEqual(out[0][0], "empathy")
        self.assertEqual(notes, [])

    def test_noop_on_empty_or_single(self):
        self.assertEqual(R.apply_degradation_policy([], "critical", 1), ([], []))
        one = [("newton", 1.0)]
        self.assertEqual(R.apply_degradation_policy(one, "critical", 1), (one, []))

    def test_noop_on_zero_scores(self):
        """Degenerate all-zero scores must not divide by zero or reorder."""
        ranked = [("empathy", 0.0), ("newton", 0.0)]
        out, notes = R.apply_degradation_policy(ranked, "critical", max_adapters=1)
        self.assertEqual(out, ranked)
        self.assertEqual(notes, [])


class TestDegradationPolicyReordering(unittest.TestCase):
    """Conditions under which the policy should actively change the survivor."""

    def test_near_tie_breaks_toward_priority(self):
        ranked = [("empathy", 1.0), ("newton", 0.95), ("davinci", 0.9)]
        out, notes = R.apply_degradation_policy(ranked, "critical", max_adapters=1)
        self.assertEqual(out[0][0], "newton")
        self.assertEqual(len(notes), 1)
        self.assertIn("empathy -> newton", notes[0])

    def test_high_pressure_also_engages(self):
        ranked = [("davinci", 1.0), ("systems_architecture", 0.95)]
        out, _ = R.apply_degradation_policy(ranked, "high", max_adapters=1)
        self.assertEqual(out[0][0], "systems_architecture")

    def test_below_band_candidates_are_not_promoted(self):
        """A low scorer stays below the band even with top priority."""
        ranked = [("empathy", 1.0), ("davinci", 0.85), ("newton", 0.1)]
        out, _ = R.apply_degradation_policy(ranked, "critical", max_adapters=1)
        self.assertNotEqual(out[0][0], "newton")
        self.assertEqual(out[-1][0], "newton", "sub-band candidate must stay last")

    def test_unknown_adapters_sort_last_but_are_preserved(self):
        """An adapter absent from the priority list must not be dropped."""
        ranked = [("mystery_adapter", 1.0), ("newton", 0.95)]
        out, _ = R.apply_degradation_policy(ranked, "critical", max_adapters=1)
        self.assertEqual(out[0][0], "newton")
        self.assertIn("mystery_adapter", [a for a, _ in out])
        self.assertEqual(len(out), 2)

    def test_no_candidates_are_lost_or_duplicated(self):
        """Reordering must be a permutation — nothing invented, nothing dropped."""
        ranked = [("empathy", 1.0), ("newton", 0.95),
                  ("davinci", 0.9), ("quantum", 0.1)]
        out, _ = R.apply_degradation_policy(ranked, "critical", max_adapters=1)
        self.assertEqual(sorted(out), sorted(ranked))

    def test_equal_priority_preserves_router_order(self):
        """Stable sort: unknown-priority ties keep the router's ranking."""
        ranked = [("alpha_x", 1.0), ("beta_y", 0.95)]
        out, _ = R.apply_degradation_policy(ranked, "critical", max_adapters=1)
        self.assertEqual([a for a, _ in out], ["alpha_x", "beta_y"])

    def test_band_is_tunable(self):
        """A narrower band should stop treating 0.8 as a contender."""
        ranked = [("empathy", 1.0), ("newton", 0.8)]
        wide, _ = R.apply_degradation_policy(
            ranked, "critical", max_adapters=1, band=0.7)
        narrow, notes_narrow = R.apply_degradation_policy(
            ranked, "critical", max_adapters=1, band=0.9)
        self.assertEqual(wide[0][0], "newton")
        self.assertEqual(narrow[0][0], "empathy")
        self.assertEqual(notes_narrow, [])

    def test_priority_list_matches_adapter_names(self):
        """Guard against drift between the policy list and real adapter names."""
        from inference.codette_shared import ADAPTER_PROMPTS
        known = set(ADAPTER_PROMPTS)
        unknown = [a for a in R.DEGRADATION_PRIORITY if a not in known]
        self.assertEqual(
            unknown, [],
            f"priority list names no real adapter: {unknown}")


class TestDegradationPolicyModeGating(unittest.TestCase):
    """The env-var gate — the thing standing between this and production."""

    def test_mode_defaults_to_off(self):
        os.environ.pop("CODETTE_DEGRADATION_POLICY", None)
        self.assertEqual(make_router().degradation_policy_mode(), "off")

    def test_mode_rejects_garbage(self):
        r = make_router()
        for bad in ("yes", "1", "true", "", "ON!"):
            os.environ["CODETTE_DEGRADATION_POLICY"] = bad
            self.assertEqual(r.degradation_policy_mode(), "off",
                             f"accepted {bad!r}")

    def test_mode_accepts_valid_values_case_insensitively(self):
        r = make_router()
        for val, expected in (("on", "on"), ("ON", "on"),
                              (" shadow ", "shadow"), ("off", "off")):
            os.environ["CODETTE_DEGRADATION_POLICY"] = val
            self.assertEqual(r.degradation_policy_mode(), expected)

    def test_shadow_mode_logs_but_does_not_apply(self):
        os.environ["CODETTE_DEGRADATION_POLICY"] = "shadow"
        ranked = [("empathy", 1.0), ("newton", 0.95)]
        out, notes = make_router().select_under_pressure(ranked, max_adapters=1)
        self.assertEqual(out, ranked, "shadow mode must not change routing")
        self.assertTrue(notes and notes[0].startswith("[SHADOW]"))

    def test_on_mode_applies(self):
        os.environ["CODETTE_DEGRADATION_POLICY"] = "on"
        ranked = [("empathy", 1.0), ("newton", 0.95)]
        out, notes = make_router().select_under_pressure(ranked, max_adapters=1)
        self.assertEqual(out[0][0], "newton")
        self.assertTrue(notes)

    def test_off_mode_skips_monitor_entirely(self):
        """With the policy off, no snapshot should be taken (zero overhead)."""
        class ExplodingMonitor:
            def snapshot(self):
                raise AssertionError("monitor queried while policy is off")

        os.environ["CODETTE_DEGRADATION_POLICY"] = "off"
        r = R.__new__(R)
        r.monitor = ExplodingMonitor()
        ranked = [("empathy", 1.0), ("newton", 0.95)]
        out, notes = r.select_under_pressure(ranked, max_adapters=1)
        self.assertEqual(out, ranked)
        self.assertEqual(notes, [])

    def test_low_pressure_is_noop_even_when_mode_is_on(self):
        """Mode 'on' must still respect the pressure gate."""
        os.environ["CODETTE_DEGRADATION_POLICY"] = "on"
        ranked = [("empathy", 1.0), ("newton", 0.95)]
        out, notes = make_router(level="low").select_under_pressure(
            ranked, max_adapters=1)
        self.assertEqual(out, ranked)
        self.assertEqual(notes, [])

    def tearDown(self):
        os.environ.pop("CODETTE_DEGRADATION_POLICY", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
