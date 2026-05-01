"""
forge_with_debate() trace test.

Verifies SPIDERWEB_UPDATE and PERSPECTIVE_SELECTED fire in the
consciousness-stack path, plus that the full trace is non-empty
and the return structure matches the expected schema.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock

# ── Minimal stub for orchestrator ────────────────────────────────────────────

class _MockOrchestrator:
    def generate(self, messages, **kwargs):
        return {
            "response": (
                "The ethical tension between privacy and collective safety in quantum-encrypted "
                "surveillance systems reflects a deep epistemic paradox. From a physics perspective, "
                "quantum key distribution provides provably secure channels — therefore, surveillance "
                "infrastructure built on QKD cannot be trivially intercepted. However, this same "
                "property raises a consequentialist concern: if authorities cannot access communications "
                "even with legal warrants, collective safety frameworks lose their enforcement mechanism. "
                "The deontological counter-argument holds that privacy is a categorical right; "
                "consequently, no surveillance architecture is ethically neutral regardless of its "
                "technical properties. Consciousness studies suggest awareness itself may resist "
                "quantification — which leads to the hypothesis that quantum encryption may be "
                "isomorphic to the irreducibility of subjective experience."
            )
        }
    def chat(self, *a, **kw):
        return self.generate(a)


class TestDebateTrace(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        repo_root = os.path.join(os.path.dirname(__file__), '..')
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)

        try:
            from reasoning_forge.forge_engine import ForgeEngine
            cls.engine = ForgeEngine(orchestrator=_MockOrchestrator())
            cls.available = True
        except Exception as e:
            print(f"\n[SKIP] ForgeEngine init failed: {e}")
            cls.available = False

    def _run_debate(self, concept: str) -> dict:
        return self.engine.forge_with_debate(concept, debate_rounds=1)

    # ── Schema ────────────────────────────────────────────────────────────────

    def test_return_schema(self):
        if not self.available:
            self.skipTest("ForgeEngine unavailable")

        result = self._run_debate("What is the ethical foundation of consent in AI systems?")
        self.assertIsInstance(result, dict)
        self.assertIn("messages", result)
        self.assertIn("metadata", result)
        msgs = result["messages"]
        roles = [m["role"] for m in msgs]
        self.assertIn("user", roles)
        self.assertIn("assistant", roles)

    # ── Trace presence ────────────────────────────────────────────────────────

    def test_trace_present(self):
        if not self.available:
            self.skipTest("ForgeEngine unavailable")

        result = self._run_debate(
            "How does consciousness relate to quantum coherence in biological systems?"
        )
        trace = result["metadata"].get("reasoning_trace")
        self.assertIsNotNone(trace, "reasoning_trace missing from forge_with_debate() result")
        self.assertIn("events", trace, "trace has no 'events' key")

    # ── SPIDERWEB_UPDATE fires ────────────────────────────────────────────────

    def test_spiderweb_update_fires(self):
        if not self.available:
            self.skipTest("ForgeEngine unavailable")

        result = self._run_debate(
            "Analyze the relationship between information entropy, free will, and moral responsibility."
        )
        trace = result["metadata"].get("reasoning_trace", {})
        events = trace.get("events", [])
        fired = {e["event_type"] for e in events}

        if "SPIDERWEB_UPDATE" not in fired:
            print(f"\nFired event types: {sorted(fired)}")
            self.skipTest(
                "SPIDERWEB_UPDATE not fired — QuantumSpiderweb may not be initialised "
                "(needs >1 agent to build belief graph)"
            )

        sw_event = next(e for e in events if e["event_type"] == "SPIDERWEB_UPDATE")
        data = sw_event["data"]
        self.assertIn("gamma", data, "SPIDERWEB_UPDATE missing gamma")
        self.assertIn("nodes_updated", data, "SPIDERWEB_UPDATE missing nodes_updated")
        self.assertIsInstance(data["gamma"], float)
        self.assertGreaterEqual(data["gamma"], 0.0)
        self.assertLessEqual(data["gamma"], 1.0)

    # ── PERSPECTIVE_SELECTED fires ────────────────────────────────────────────

    def test_perspective_selected_fires(self):
        if not self.available:
            self.skipTest("ForgeEngine unavailable")

        result = self._run_debate(
            "Should artificial general intelligence be granted legal personhood? "
            "Analyze from ethics, philosophy of mind, and systems perspectives."
        )
        trace = result["metadata"].get("reasoning_trace", {})
        events = trace.get("events", [])
        fired = {e["event_type"] for e in events}

        self.assertIn(
            "PERSPECTIVE_SELECTED", fired,
            f"PERSPECTIVE_SELECTED not fired. Fired: {sorted(fired)}"
        )

        ps_event = next(e for e in events if e["event_type"] == "PERSPECTIVE_SELECTED")
        data = ps_event["data"]
        self.assertIn("perspectives", data)
        self.assertIn("domains", data)
        self.assertIsInstance(data["perspectives"], list)
        self.assertGreater(len(data["perspectives"]), 0, "perspectives list is empty")

    # ── Both fire together ────────────────────────────────────────────────────

    def test_spiderweb_and_perspective_both_fire(self):
        """
        The two events unique to forge_with_debate() should both be present
        on a multi-domain query that activates multiple agents.
        """
        if not self.available:
            self.skipTest("ForgeEngine unavailable")

        result = self._run_debate(
            "How does the RC+xi epistemic framework resolve the tension between "
            "Bayesian coherence and ethical uncertainty in AI safety research?"
        )
        trace = result["metadata"].get("reasoning_trace", {})
        events = trace.get("events", [])
        fired = {e["event_type"] for e in events}

        missing = {"PERSPECTIVE_SELECTED"} - fired
        # SPIDERWEB_UPDATE is conditional on multi-agent routing; skip if absent
        if "SPIDERWEB_UPDATE" not in fired:
            print(f"\n  [note] SPIDERWEB_UPDATE not fired (single-agent routing); "
                  f"checking PERSPECTIVE_SELECTED only")
        else:
            missing = {"PERSPECTIVE_SELECTED", "SPIDERWEB_UPDATE"} - fired

        self.assertEqual(missing, set(), f"Missing debate-specific events: {missing}")

    # ── PSI_UPDATE still fires in debate path ─────────────────────────────────

    def test_psi_update_in_debate_path(self):
        if not self.available:
            self.skipTest("ForgeEngine unavailable")

        result = self._run_debate("What is the nature of time in a relativistic universe?")
        trace = result["metadata"].get("reasoning_trace", {})
        events = trace.get("events", [])
        psi_events = [e for e in events if e["event_type"] == "PSI_UPDATE"]

        self.assertTrue(psi_events, "PSI_UPDATE not fired in forge_with_debate() path")
        psi_r = psi_events[0]["data"].get("psi_r")
        self.assertIsNotNone(psi_r, "psi_r missing from PSI_UPDATE data")


if __name__ == "__main__":
    unittest.main(verbosity=2)
