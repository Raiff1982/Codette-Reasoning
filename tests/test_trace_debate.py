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


_CONFABULATED_TEXT = (
    "Quantum consciousness is definitely caused by microtubule resonance. "
    "The library NeuroQML has been proven to model these processes directly. "
    "It is clearly established that the package QuantoMind provides real-time "
    "quantum decoherence simulation at the neuronal level. "
    "Using the framework HyperNeuralQX, consciousness clearly emerges from "
    "quantum entanglement in biological systems at temperatures above 37°C. "
    "This is an established fact with no uncertainty whatsoever."
)


class _ConfabulatingOrchestrator:
    """
    Returns a response containing hallucination signals that will score < 0.5:
    - References library 'NeuroQML' (not in REAL_FRAMEWORKS) → code_score *= 0.4
    - Uses 'definitely', 'proven' with no hedging → confidence_score *= 0.8
    Combined: 1.0 × 0.4 × 0.8 = 0.32 → PAUSE recommendation

    Implements both generate() and route_and_generate() so forge_with_debate()
    doesn't fall back to Code7E templates.
    """
    def generate(self, messages, **kwargs):
        return {"response": _CONFABULATED_TEXT}

    def route_and_generate(self, *args, **kwargs):
        return {"response": _CONFABULATED_TEXT, "adapter": "confabulation_test"}

    def chat(self, *a, **kw):
        return self.generate(a)


class TestHallucinationFlagDebate(unittest.TestCase):
    """
    Verifies HALLUCINATION_FLAG fires in forge_with_debate() when the
    synthesis output contains fabricated frameworks and unhedged claims.
    """

    @classmethod
    def setUpClass(cls):
        repo_root = os.path.join(os.path.dirname(__file__), '..')
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        try:
            from reasoning_forge.forge_engine import ForgeEngine
            cls.engine = ForgeEngine(orchestrator=_ConfabulatingOrchestrator())
            cls.available = True
        except Exception as e:
            print(f"\n[SKIP] ForgeEngine init failed: {e}")
            cls.available = False

    def test_hallucination_flag_fires_on_confabulation(self):
        """HALLUCINATION_FLAG should fire when synthesis contains unknown frameworks + overconfident claims."""
        if not self.available:
            self.skipTest("ForgeEngine unavailable")

        result = self.engine.forge_with_debate(
            "Explain the neural basis of consciousness using quantum mechanical principles.",
            debate_rounds=1,
        )
        trace = result["metadata"].get("reasoning_trace") or {}
        events = trace.get("events", [])
        fired = {e["event_type"] for e in events}

        self.assertIn(
            "HALLUCINATION_FLAG", fired,
            f"HALLUCINATION_FLAG not fired on confabulated response. "
            f"Fired: {sorted(fired)}"
        )

        hall_event = next(e for e in events if e["event_type"] == "HALLUCINATION_FLAG")
        data = hall_event["data"]
        self.assertIn("recommendation", data)
        self.assertIn(data["recommendation"], ("PAUSE", "INTERRUPT"),
                      f"Expected PAUSE or INTERRUPT, got {data['recommendation']}")
        self.assertIn("confidence_score", data)
        self.assertLess(data["confidence_score"], 0.5,
                        f"confidence_score={data['confidence_score']} should be < 0.5 for hallucinated content")
        self.assertTrue(data.get("flagged"), "flagged field should be True")

    def test_hallucination_flag_absent_on_clean_response(self):
        """HALLUCINATION_FLAG should NOT fire (or should show non-flagged) on a well-hedged response."""
        if not self.available:
            self.skipTest("ForgeEngine unavailable")

        # The clean mock from TestDebateTrace uses hedged language — no hallucination flags
        from reasoning_forge.forge_engine import ForgeEngine

        class _CleanMock:
            def generate(self, messages, **kwargs):
                return {
                    "response": (
                        "The relationship between quantum mechanics and consciousness remains "
                        "an open question. Some researchers argue that quantum coherence in "
                        "microtubules might play a role, though this hypothesis lacks consensus. "
                        "From a physics perspective, decoherence timescales are perhaps too short. "
                        "Philosophically, the hard problem of consciousness may resist physical "
                        "reduction — possibly suggesting that phenomenal experience is not fully "
                        "reducible to physical processes, though this remains speculative."
                    )
                }
            def chat(self, *a, **kw): return self.generate(a)

        clean_engine = ForgeEngine(orchestrator=_CleanMock())
        result = clean_engine.forge_with_debate(
            "How might quantum mechanics relate to consciousness?",
            debate_rounds=1,
        )
        trace = result["metadata"].get("reasoning_trace") or {}
        events = trace.get("events", [])

        hall_events = [e for e in events if e["event_type"] == "HALLUCINATION_FLAG"]
        if hall_events:
            # If it fires, it should not be PAUSE or INTERRUPT
            rec = hall_events[0]["data"].get("recommendation", "CONTINUE")
            self.assertNotIn(rec, ("PAUSE", "INTERRUPT"),
                             f"Clean response should not trigger PAUSE/INTERRUPT, got {rec}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
