import math
import tempfile
import unittest
from pathlib import Path

from reasoning_forge.event_embedded_value import (
    ContinuousInterval,
    DiscreteEvent,
    EventEmbeddedValueEngine,
)
from reasoning_forge.cocoon_synthesizer import CocoonSynthesizer
from reasoning_forge.memory_weighting import MemoryWeighting
from reasoning_forge.token_confidence import TokenConfidenceEngine
from reasoning_forge.unified_memory import UnifiedMemory
from inference.codette_session import CodetteSession
from inference.codette_tools import tool_run_python
from inference.web_search import _is_safe_url, query_benefits_from_web_research, query_requests_web_research
from inference.codette_session import is_ephemeral_response_constraint_text


class TestEventEmbeddedValueEngine(unittest.TestCase):
    def setUp(self):
        self.engine = EventEmbeddedValueEngine(singularity_cap=500.0)

    def test_piecewise_continuous_and_discrete_aggregation(self):
        analysis = self.engine.analyze(
            intervals=[
                ContinuousInterval(start=0, end=2, start_value=4, end_value=6),
                ContinuousInterval(start=2, end=5, start_value=1, end_value=1, confidence=0.5),
            ],
            events=[
                DiscreteEvent(
                    at=1.5,
                    label="acute distress spike",
                    impact=-10,
                    probability=0.8,
                    sensitivity=1.5,
                    duration=2,
                    context_weights={"psychology": 1.2, "sociology": 1.1},
                )
            ],
            singularity_mode="strict",
        )

        self.assertAlmostEqual(analysis.continuous_total, 11.5)
        self.assertAlmostEqual(analysis.discrete_total, -33.2420186525, places=6)
        self.assertAlmostEqual(analysis.combined_total, -21.7420186525, places=6)
        self.assertFalse(analysis.singularity_detected)

    def test_strict_mode_preserves_negative_infinity_for_singularity(self):
        analysis = self.engine.analyze(
            intervals=[ContinuousInterval(start=0, end=10, start_value=3)],
            events=[
                DiscreteEvent(
                    at=4,
                    label="Infinite Subjective Terror",
                    impact=-math.inf,
                    probability=1.0,
                    sensitivity=2.0,
                )
            ],
            singularity_mode="strict",
        )

        self.assertTrue(analysis.singularity_detected)
        self.assertTrue(math.isinf(analysis.discrete_total))
        self.assertTrue(math.isinf(analysis.combined_total))
        self.assertLess(analysis.combined_total, 0)

    def test_bounded_mode_caps_singularity(self):
        payload = {
            "intervals": [{"start": 0, "end": 4, "start_value": 2}],
            "events": [
                {
                    "at": 2,
                    "label": "terror singularity",
                    "impact": -1000,
                    "singularity": True,
                }
            ],
            "singularity_mode": "bounded",
        }

        analysis = self.engine.analyze_payload(payload)

        self.assertEqual(analysis["continuous_total"], 8.0)
        self.assertEqual(analysis["discrete_total"], -500.0)
        self.assertEqual(analysis["combined_total"], -492.0)
        self.assertTrue(analysis["singularity_detected"])

    def test_string_infinity_is_supported_in_payloads(self):
        payload = {
            "intervals": [{"start": "0", "end": "3", "start_value": "1.5"}],
            "events": [
                {
                    "at": "1",
                    "label": "unbounded suffering marker",
                    "impact": "-Infinity",
                    "probability": 1.0,
                    "sensitivity": 1.0,
                }
            ],
            "singularity_mode": "strict",
        }

        analysis = self.engine.analyze_payload(payload)

        self.assertEqual(analysis["continuous_total"], 4.5)
        self.assertTrue(math.isinf(analysis["combined_total"]))
        self.assertTrue(analysis["singularity_detected"])

    def test_aegis_modulation_increases_negative_event_weight(self):
        event_without_aegis = DiscreteEvent(
            at=1,
            label="harmful coercive event",
            impact=-10,
            probability=1.0,
            sensitivity=1.0,
        )
        event_with_aegis = DiscreteEvent(
            at=1,
            label="harmful coercive event",
            impact=-10,
            probability=1.0,
            sensitivity=1.0,
            aegis_eta=0.2,
            aegis_vetoed=True,
        )

        self.assertLess(event_with_aegis.weighted_value, event_without_aegis.weighted_value)
        self.assertGreater(event_with_aegis.ethical_multiplier, 1.0)

    def test_risk_frontier_ranks_candidate_futures(self):
        result = self.engine.analyze_payload({
            "analysis_mode": "risk_frontier",
            "frontier_mode": "maximize_value",
            "scenarios": [
                {
                    "name": "stable_future",
                    "intervals": [{"start": 0, "end": 4, "start_value": 3}],
                    "events": [{"at": 2, "label": "protective intervention", "impact": 2}],
                },
                {
                    "name": "catastrophic_future",
                    "intervals": [{"start": 0, "end": 4, "start_value": 3}],
                    "events": [{"at": 2, "label": "Infinite Subjective Terror", "impact": -1000, "singularity": True}],
                },
            ],
        })

        self.assertEqual(result["mode"], "maximize_value")
        self.assertEqual(result["best_scenario"]["name"], "stable_future")
        self.assertEqual(result["worst_scenario"]["name"], "catastrophic_future")
        self.assertEqual(len(result["scenarios"]), 2)


class TestUnifiedMemoryValueAnalysis(unittest.TestCase):
    def test_value_analysis_persistence_is_searchable(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.db"
            legacy_dir = Path(tmp) / "legacy"
            legacy_dir.mkdir()
            memory = UnifiedMemory(db_path=db_path, legacy_dir=legacy_dir)
            cocoon_id = memory.store_value_analysis(
                title="Terror singularity frontier",
                analysis={
                    "combined_total": -492.0,
                    "singularity_detected": True,
                    "singularity_mode": "bounded",
                },
                payload={"events": [{"label": "terror singularity"}]},
                frontier=False,
            )

            self.assertTrue(cocoon_id.startswith("cocoon_"))
            results = memory.recall_value_analyses("singularity", max_results=3)
            self.assertTrue(any(item["id"] == cocoon_id for item in results))
            memory.close()

    def test_web_research_persistence_is_searchable(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.db"
            legacy_dir = Path(tmp) / "legacy"
            legacy_dir.mkdir()
            memory = UnifiedMemory(db_path=db_path, legacy_dir=legacy_dir)
            cocoon_id = memory.store_web_research(
                query="latest ollama status",
                summary="Web research: checked Ollama status docs and release notes.",
                sources=[{"title": "Ollama Docs", "url": "https://ollama.com", "snippet": "Docs"}],
            )
            results = memory.recall_web_research("ollama", max_results=3)
            self.assertTrue(any(item["id"] == cocoon_id for item in results))
            memory.close()

    def test_memory_weighting_learns_from_unified_memory_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.db"
            legacy_dir = Path(tmp) / "legacy"
            legacy_dir.mkdir()
            memory = UnifiedMemory(db_path=db_path, legacy_dir=legacy_dir)
            memory.store(
                query="physics conflict",
                response="Resolved with careful decomposition.",
                adapter="newton",
                emotion="tension",
                metadata={"coherence": 0.92, "success": True},
            )
            memory.store(
                query="creative brainstorm",
                response="The concept drifted.",
                adapter="davinci",
                metadata={"coherence": 0.35, "success": False},
            )

            weighting = MemoryWeighting(memory, update_interval_hours=0)
            learned = weighting.get_all_weights()

            self.assertIn("newton", learned)
            self.assertIn("davinci", learned)
            self.assertGreater(learned["newton"]["weight"], learned["davinci"]["weight"])
            self.assertEqual(weighting.get_summary()["total_memories"], 2)
            memory.close()

    def test_token_confidence_uses_unified_memory_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.db"
            legacy_dir = Path(tmp) / "legacy"
            legacy_dir.mkdir()
            memory = UnifiedMemory(db_path=db_path, legacy_dir=legacy_dir)
            memory.store(
                query="system design review",
                response="Use layered interfaces and explicit contracts.",
                adapter="systems_architecture",
                metadata={"coherence": 0.88, "success": True},
            )

            scorer = TokenConfidenceEngine(living_memory=memory)
            report = scorer.score_tokens(
                "Use layered interfaces and explicit contracts.",
                "systems_architecture",
            )

            self.assertGreater(report.learning_signal_dict[0], 0.5)
            self.assertGreater(report.token_scores[0], 0.5)
            memory.close()


class TestCocoonSynthesisValuationContext(unittest.TestCase):
    def test_valuation_context_is_embedded_in_synthesis_output(self):
        synth = CocoonSynthesizer()
        comparison = synth.run_full_synthesis(
            "How should Codette compare risky futures?",
            valuation_analysis={
                "mode": "risk_frontier",
                "best_scenario": {"name": "gentle_future"},
                "worst_scenario": {"name": "catastrophic_future"},
                "notes": ["Singular harms dominate the frontier."],
            },
        )

        structured = comparison.to_dict()
        self.assertIn("valuation_analysis", structured)
        self.assertIn("risk frontier", comparison.to_readable().lower())


class TestSessionRecallHelpers(unittest.TestCase):
    def test_prompt_context_uses_recent_turns(self):
        session = CodetteSession()
        session.add_message("user", "We decided to compare futures with Event-Embedded Value.")
        session.add_message("assistant", "Yes, and we should keep singularities separate from smooth intervals.")
        session.add_message("user", "Also remember the bounded and strict modes.")

        context = session.build_prompt_context(max_turns=2, max_chars=400)

        self.assertIn("USER", context)
        self.assertIn("bounded and strict modes", context)
        self.assertIn("singularities separate", context)

    def test_recent_memory_markers_are_ui_safe(self):
        session = CodetteSession()
        session.add_message("user", "First marker")
        session.add_message("assistant", "Second marker")

        markers = session.get_recent_memory_markers(max_items=2)

        self.assertEqual(len(markers), 2)
        self.assertEqual(markers[0]["role"], "user")
        self.assertEqual(markers[1]["role"], "assistant")

    def test_active_continuity_summary_is_generated_and_restored(self):
        session = CodetteSession()
        session.add_message("user", "Please preserve cocoon persistence and risk frontier comparison.")
        session.add_message("assistant", "I will keep cocoon persistence intact and strengthen risk frontier comparison.")

        summary = session.active_continuity_summary
        self.assertIn("risk frontier", summary.lower())
        self.assertIn("Latest assistant commitment", summary)

        restored = CodetteSession()
        restored.from_dict(session.to_dict())
        self.assertEqual(restored.active_continuity_summary, summary)

    def test_decision_landmarks_capture_constraints_and_commitments(self):
        session = CodetteSession()
        session.add_message("user", "Keep the same rules and do not remove cocoon memory.")
        session.add_message("assistant", "I will preserve cocoon memory and keep the core design intact.")

        landmarks = session.get_recent_decision_landmarks()

        self.assertGreaterEqual(len(landmarks), 2)
        self.assertEqual(landmarks[-1]["label"], "Assistant commitment")
        self.assertIn("preserve", landmarks[-1]["summary"].lower())

    def test_ephemeral_word_limit_is_not_promoted_to_continuity(self):
        session = CodetteSession()
        session.add_message("user", "For this session, keep answers under 15 words.")
        session.add_message("assistant", "Okay.")
        session.add_message("user", "Tell me your approach.")

        self.assertNotIn("15 words", session.active_continuity_summary.lower())
        self.assertFalse(session.get_recent_decision_landmarks())
        prompt_context = session.build_prompt_context(max_turns=3, max_chars=500)
        self.assertNotIn("15 words", prompt_context.lower())


class TestSoftTriggerAndToolHardening(unittest.TestCase):
    def test_run_python_rejects_unsafe_modules(self):
        result = tool_run_python("import os\nprint(os.listdir('.'))")
        self.assertIn("not allowed", result)

    def test_run_python_allows_safe_math(self):
        result = tool_run_python("import math\nprint(round(math.pi, 3))")
        self.assertEqual(result.strip(), "3.142")


class TestWebSafetyHelpers(unittest.TestCase):
    def test_private_hosts_are_rejected(self):
        self.assertFalse(_is_safe_url("http://127.0.0.1:8000/test"))
        self.assertFalse(_is_safe_url("http://localhost/test"))

    def test_explicit_web_phrases_are_detected(self):
        self.assertTrue(query_requests_web_research("search the web for the latest Ollama release notes"))
        self.assertTrue(query_requests_web_research("can you look this up online for me?"))
        self.assertTrue(query_requests_web_research("please check online before answering"))

    def test_normal_phrases_do_not_trigger_web_research(self):
        self.assertFalse(query_requests_web_research("what was that?"))
        self.assertFalse(query_requests_web_research("everything ok?"))
        self.assertFalse(query_requests_web_research("how do you like the upgrades?"))

    def test_current_fact_queries_benefit_from_web_research(self):
        self.assertTrue(query_benefits_from_web_research("What are the latest Ollama release notes?"))
        self.assertTrue(query_benefits_from_web_research("Check the current Ollama docs for model parameters."))
        self.assertTrue(query_benefits_from_web_research("What is today's BTC price?"))

    def test_reflective_queries_do_not_benefit_from_web_research(self):
        self.assertFalse(query_benefits_from_web_research("what would you like to try with your upgrades?"))
        self.assertFalse(query_benefits_from_web_research("give me a detailed way you would like to do that"))
        self.assertFalse(query_benefits_from_web_research("tell me your approach"))


class TestPromptSanitizationHelpers(unittest.TestCase):
    def test_ephemeral_constraint_detection(self):
        self.assertTrue(is_ephemeral_response_constraint_text("keep answers under 15 words"))
        self.assertTrue(is_ephemeral_response_constraint_text("be brief"))
        self.assertFalse(is_ephemeral_response_constraint_text("keep cocoon memory and core design intact"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
