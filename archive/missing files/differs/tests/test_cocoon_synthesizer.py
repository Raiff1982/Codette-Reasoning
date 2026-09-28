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


# 2026-08-03: these fixtures were described in the test as "signal-rich" but
# contained almost none of the signals the synthesizer actually looks for, so
# extract_patterns correctly returned 0 patterns and the test correctly failed.
#
# The synthesizer matches STRUCTURAL archetypes (tension_resolution,
# feedback_loop, layered_emergence, ...), each needing >=2 of its own signal
# words present in a domain, in >=2 domains. The old fixtures used
# domain-flavoured vocabulary (fear, empathy, evidence, imagination) that hit at
# most one signal in any archetype. That is a fixture that never exercised the
# mechanism, not a defect in the mechanism — it finds patterns fine on real
# cocoons (217 -> 4 on its original run).
#
# Rewritten so the `tension_resolution` archetype genuinely spans emotional,
# analytical and creative, in language natural to each domain. The signal words
# are real content here, not keyword stuffing.
def _emotional_cocoons():
    return [
        _make_cocoon("I feel afraid of uncertainty", "Fear arises from the tension between wanting control and lacking it. Compassion helps resolve that conflict.", "emotional"),
        _make_cocoon("She cares deeply about human experience", "Empathy holds opposing needs in balance, and trust lets us reconcile them.", "emotional"),
        _make_cocoon("The child felt joy at learning", "Joy emerges when curiosity and fear find harmony rather than conflict.", "emotional"),
    ]


def _analytical_cocoons():
    return [
        _make_cocoon("Analyse the system boundary conditions", "Logic resolves the tension between competing constraints at the boundary.", "analytical"),
        _make_cocoon("Measure the evidence for this claim", "Systematic proof must balance sensitivity against specificity; the two are opposing.", "analytical"),
        _make_cocoon("Mathematical proof of convergence", "Convergence is the synthesis where opposing error terms reconcile and cancel.", "analytical"),
    ]


def _creative_cocoons():
    return [
        _make_cocoon("Compose a novel melody", "A melody works by holding tension and release in balance.", "creative"),
        _make_cocoon("Invent a new art form", "Invention comes from the conflict between constraint and freedom, and the synthesis that resolves it.", "creative"),
        _make_cocoon("Generate new ideas for this design", "Good design reconciles opposing demands into harmony.", "creative"),
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
        # 2026-08-03: updated to the actual CocoonPattern signature. These
        # tests were written against an older API and had drifted:
        # `source_cocoon_ids` -> `source_cocoons`, `tension_score` ->
        # `tension_signature`, and `structural_similarity` was missing
        # altogether. The dataclass is the source of truth here — the
        # synthesizer is working code (217 cocoons -> 4 patterns on its
        # original run), so the tests were stale, not the implementation.
        return [
            CocoonPattern(
                name="Resonant Tension",
                description="Pattern of oscillation between certainty and doubt.",
                source_cocoons=["c1", "c2"],
                source_domains=["emotional", "analytical"],
                structural_similarity="oscillation between opposed poles",
                tension_signature=0.6,
                novelty_score=0.75,
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

    # 2026-08-03: `apply_and_compare` takes (problem, strategy, patterns).
    # These calls omitted `patterns` entirely, which is a required positional
    # argument, so every one raised TypeError before reaching an assertion.
    def _pattern(self):
        return CocoonPattern(
            name="Test Pattern",
            description="desc",
            source_cocoons=[],
            source_domains=["a", "b"],
            structural_similarity="shared oscillation",
            tension_signature=0.4,
            novelty_score=0.5,
            evidence=[],
        )

    def test_returns_strategy_comparison(self):
        patterns = [self._pattern()]
        strategy = self.synth.forge_strategy(patterns)
        comparison = self.synth.apply_and_compare(
            "How should we approach complex ethical problems?",
            strategy,
            patterns,
        )
        self.assertIsInstance(comparison, StrategyComparison)

    def test_comparison_has_improvement_delta(self):
        # 2026-08-03: there is no `improvement_delta` attribute and there never
        # was on this class. StrategyComparison reports improvement as
        # `improvement_assessment` (prose) plus `differences` (itemised), and
        # the numeric deltas live on the two ReasoningPath objects. Asserting
        # against the real shape, including that the depth delta is genuinely
        # numeric — which is what the original test was reaching for.
        strategy = self.synth.forge_strategy([])
        comparison = self.synth.apply_and_compare(
            "Explain the relationship between emotion and logic.",
            strategy,
            [],
        )
        self.assertIsInstance(comparison.improvement_assessment, str)
        self.assertGreater(len(comparison.improvement_assessment), 0)
        self.assertIsInstance(comparison.differences, list)
        delta = comparison.new_path.depth_score - comparison.original_path.depth_score
        self.assertIsInstance(delta, float)

    def test_comparison_to_readable_is_string(self):
        strategy = self.synth.forge_strategy([])
        comparison = self.synth.apply_and_compare("Test problem.", strategy, [])
        readable = comparison.to_readable()
        self.assertIsInstance(readable, str)
        self.assertGreater(len(readable), 0)

    def test_comparison_to_dict_is_serializable(self):
        # 2026-08-03: keys corrected to what to_dict() actually emits —
        # "new_strategy" not "strategy", "improvement_assessment" not
        # "improvement_delta". Also actually asserts serialisability, which the
        # test's own name claimed but never checked.
        import json
        strategy = self.synth.forge_strategy([])
        comparison = self.synth.apply_and_compare("Test problem.", strategy, [])
        d = comparison.to_dict()
        self.assertIn("new_strategy", d)
        self.assertIn("improvement_assessment", d)
        self.assertIn("evidence_chain", d)
        json.dumps(d)  # raises if any value is not serialisable


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
        # 2026-08-03: key is "new_strategy", not "strategy".
        result = self.synth.run_full_synthesis("Explain recursive consciousness.")
        d = result.to_dict()
        self.assertIn("new_strategy", d)
        self.assertIn("name", d["new_strategy"])

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
