#!/usr/bin/env python3
"""
Unit tests for CocoonSynthesizer.

Tests cover: extract_patterns(), forge_strategy(), apply_and_compare(),
run_full_synthesis(), standalone mode (no memory), serialization.
"""
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.cocoon_synthesizer import (
    CocoonPattern,
    CocoonSynthesizer,
    ReasoningStrategy,
    StrategyComparison,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cocoon(query: str, response: str, domain: str = "general") -> dict:
    return {
        "id": f"cocoon_{hash(query) % 99999}",
        "query": query,
        "response": response,
        "domain": domain,
        "adapter": "test",
        "importance": 7,
    }


def _emotional_cocoons():
    return [
        _make_cocoon("I feel afraid of uncertainty", "Fear arises from uncertainty and lack of control. Compassion helps.", "emotional"),
        _make_cocoon("She cares deeply about human experience", "Empathy and trust anchor our ability to connect.", "emotional"),
        _make_cocoon("The child felt joy at learning", "Joy emerges from discovery and human experience shared.", "emotional"),
    ]


def _analytical_cocoons():
    return [
        _make_cocoon("Analyse the system boundary conditions", "Logic and systematic analysis reveal cause and effect.", "analytical"),
        _make_cocoon("Measure the evidence for this claim", "Evidence-based reasoning requires systematic proof of cause.", "analytical"),
        _make_cocoon("Mathematical proof of convergence", "Convergence is demonstrated by induction and logical evidence.", "analytical"),
    ]


def _creative_cocoons():
    return [
        _make_cocoon("Compose a novel melody", "Creative imagination leads to novel musical design.", "creative"),
        _make_cocoon("Invent a new art form", "Artistic invention requires imagination and creative dreaming.", "creative"),
        _make_cocoon("Generate new ideas for this design", "Novel design emerges from imagination and creative composition.", "creative"),
    ]


# ---------------------------------------------------------------------------
# Tests: extract_patterns
# ---------------------------------------------------------------------------

class TestExtractPatterns(unittest.TestCase):

    def setUp(self):
        self.synth = CocoonSynthesizer()

    def test_returns_list(self):
        domain_cocoons = {
            "emotional": _emotional_cocoons(),
            "analytical": _analytical_cocoons(),
        }
        patterns = self.synth.extract_patterns(domain_cocoons)
        self.assertIsInstance(patterns, list)

    def test_cross_domain_pattern_detected(self):
        domain_cocoons = {
            "emotional": _emotional_cocoons(),
            "analytical": _analytical_cocoons(),
            "creative": _creative_cocoons(),
        }
        patterns = self.synth.extract_patterns(domain_cocoons)
        # With signal-rich cocoons across 3 domains, at least one pattern should emerge
        self.assertGreaterEqual(len(patterns), 1)

    def test_pattern_has_required_fields(self):
        domain_cocoons = {
            "emotional": _emotional_cocoons(),
            "analytical": _analytical_cocoons(),
            "creative": _creative_cocoons(),
        }
        patterns = self.synth.extract_patterns(domain_cocoons)
        if patterns:
            p = patterns[0]
            self.assertIsInstance(p, CocoonPattern)
            self.assertIsInstance(p.name, str)
            self.assertGreater(len(p.name), 0)
            self.assertIsInstance(p.source_domains, list)
            self.assertGreaterEqual(len(p.source_domains), 2)
            self.assertGreaterEqual(p.novelty_score, 0.0)
            self.assertLessEqual(p.novelty_score, 1.0)

    def test_empty_cocoons_returns_empty_patterns(self):
        patterns = self.synth.extract_patterns({})
        self.assertEqual(patterns, [])

    def test_single_domain_produces_no_cross_domain_patterns(self):
        # A pattern requires 2+ domains — one domain can't trigger cross-domain detection
        patterns = self.synth.extract_patterns({"emotional": _emotional_cocoons()})
        self.assertEqual(patterns, [])

    def test_pattern_to_dict_is_serializable(self):
        domain_cocoons = {
            "emotional": _emotional_cocoons(),
            "analytical": _analytical_cocoons(),
            "creative": _creative_cocoons(),
        }
        patterns = self.synth.extract_patterns(domain_cocoons)
        if patterns:
            d = patterns[0].to_dict()
            self.assertIn("name", d)
            self.assertIn("source_domains", d)
            self.assertIn("novelty_score", d)


# ---------------------------------------------------------------------------
# Tests: forge_strategy
# ---------------------------------------------------------------------------

class TestForgeStrategy(unittest.TestCase):

    def setUp(self):
        self.synth = CocoonSynthesizer()

    def _patterns(self):
        return [
            CocoonPattern(
                name="Resonant Tension",
                description="Pattern of oscillation between certainty and doubt.",
                source_domains=["emotional", "analytical"],
                source_cocoon_ids=["c1", "c2"],
                novelty_score=0.75,
                tension_score=0.6,
                evidence=["[emotional] fear and uncertainty...", "[analytical] systematic proof..."],
            )
        ]

    def test_returns_reasoning_strategy(self):
        strategy = self.synth.forge_strategy(self._patterns())
        self.assertIsInstance(strategy, ReasoningStrategy)

    def test_strategy_has_non_empty_name(self):
        strategy = self.synth.forge_strategy(self._patterns())
        self.assertGreater(len(strategy.name), 0)

    def test_strategy_references_source_patterns(self):
        strategy = self.synth.forge_strategy(self._patterns())
        self.assertIn("Resonant Tension", strategy.source_patterns)

    def test_empty_patterns_returns_default_strategy(self):
        strategy = self.synth.forge_strategy([])
        self.assertIsInstance(strategy, ReasoningStrategy)
        self.assertGreater(len(strategy.name), 0)

    def test_strategy_history_grows(self):
        before = len(self.synth._strategy_history)
        self.synth.forge_strategy(self._patterns())
        self.assertEqual(len(self.synth._strategy_history), before + 1)

    def test_strategy_to_dict_is_serializable(self):
        strategy = self.synth.forge_strategy(self._patterns())
        d = strategy.to_dict()
        self.assertIn("name", d)
        self.assertIn("mechanism", d)
        self.assertIn("source_patterns", d)


# ---------------------------------------------------------------------------
# Tests: apply_and_compare
# ---------------------------------------------------------------------------

class TestApplyAndCompare(unittest.TestCase):

    def setUp(self):
        self.synth = CocoonSynthesizer()

    def test_returns_strategy_comparison(self):
        strategy = self.synth.forge_strategy([
            CocoonPattern(
                name="Test Pattern",
                description="desc",
                source_domains=["a", "b"],
                source_cocoon_ids=[],
                novelty_score=0.5,
                tension_score=0.4,
                evidence=[],
            )
        ])
        comparison = self.synth.apply_and_compare(
            "How should we approach complex ethical problems?",
            strategy,
        )
        self.assertIsInstance(comparison, StrategyComparison)

    def test_comparison_has_improvement_delta(self):
        strategy = self.synth.forge_strategy([])
        comparison = self.synth.apply_and_compare(
            "Explain the relationship between emotion and logic.",
            strategy,
        )
        self.assertIsInstance(comparison.improvement_delta, float)

    def test_comparison_to_readable_is_string(self):
        strategy = self.synth.forge_strategy([])
        comparison = self.synth.apply_and_compare("Test problem.", strategy)
        readable = comparison.to_readable()
        self.assertIsInstance(readable, str)
        self.assertGreater(len(readable), 0)

    def test_comparison_to_dict_is_serializable(self):
        strategy = self.synth.forge_strategy([])
        comparison = self.synth.apply_and_compare("Test problem.", strategy)
        d = comparison.to_dict()
        self.assertIn("strategy", d)
        self.assertIn("improvement_delta", d)


# ---------------------------------------------------------------------------
# Tests: run_full_synthesis (standalone mode)
# ---------------------------------------------------------------------------

class TestRunFullSynthesis(unittest.TestCase):

    def setUp(self):
        self.synth = CocoonSynthesizer()  # No memory — standalone mode

    def test_returns_strategy_comparison(self):
        result = self.synth.run_full_synthesis("How do we balance creativity with analytical rigor?")
        self.assertIsInstance(result, StrategyComparison)

    def test_result_to_dict_contains_strategy(self):
        result = self.synth.run_full_synthesis("Explain recursive consciousness.")
        d = result.to_dict()
        self.assertIn("strategy", d)

    def test_valuation_context_is_embedded(self):
        result = self.synth.run_full_synthesis(
            "How should Codette weigh catastrophic futures?",
            valuation_analysis={
                "mode": "risk_frontier",
                "best_scenario": {"name": "cooperative_future"},
                "worst_scenario": {"name": "collapse"},
                "notes": ["Singularities dominate."],
            },
        )
        d = result.to_dict()
        self.assertIn("valuation_analysis", d)
        readable = result.to_readable()
        self.assertIn("risk frontier", readable.lower())

    def test_synthesis_with_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            from reasoning_forge.unified_memory import UnifiedMemory
            db = Path(tmp) / "test.db"
            memory = UnifiedMemory(db_path=db, legacy_dir=Path(tmp) / "legacy")
            memory.store("emotion and empathy in reasoning", "Empathy anchors trust.", adapter="empathy", domain="emotional")
            memory.store("logical proof of convergence", "Evidence and systematic logic.", adapter="newton", domain="analytical")

            synth = CocoonSynthesizer(memory=memory)
            result = synth.run_full_synthesis("Integrate emotion and logic.")
            self.assertIsInstance(result, StrategyComparison)
            memory.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
