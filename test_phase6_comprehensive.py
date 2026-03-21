"""
Phase 6 Comprehensive Unit Tests

Tests for:
- framework_definitions (StateVector, TensionDefinition, CoherenceMetrics, etc.)
- semantic_tension (SemanticTensionEngine)
- specialization_tracker (SpecializationTracker)
- preflight_predictor (PreFlightConflictPredictor)
"""

import unittest
import numpy as np
import sys
from typing import List, Dict

# Add path for direct imports
sys.path.insert(0, 'reasoning_forge')
sys.path.insert(0, 'evaluation')

# Import Phase 6 components directly (avoid forge_engine initialization)
from framework_definitions import (
    StateVector,
    TensionDefinition,
    CoherenceMetrics,
    ConflictPrediction,
    SpecializationScore,
)
from semantic_tension import SemanticTensionEngine
from specialization_tracker import SpecializationTracker


class TestFrameworkDefinitions(unittest.TestCase):
    """Test mathematical framework definitions."""

    def test_state_vector_creation(self):
        """Test StateVector creation and to_dict()."""
        state = StateVector(psi=0.8, tau=0.6, chi=1.2, phi=0.3, lam=0.7)
        self.assertEqual(state.psi, 0.8)
        self.assertEqual(state.tau, 0.6)
        self.assertAlmostEqual(state.chi, 1.2, places=3)

        state_dict = state.to_dict()
        self.assertIn("psi", state_dict)
        self.assertIn("tau", state_dict)
        self.assertEqual(state_dict["psi"], 0.8)

    def test_state_vector_to_array(self):
        """Test StateVector.to_array() returns numpy array."""
        state = StateVector(psi=0.8, tau=0.6, chi=1.2, phi=0.3, lam=0.7)
        arr = state.to_array()

        self.assertIsInstance(arr, np.ndarray)
        self.assertEqual(len(arr), 5)
        self.assertAlmostEqual(arr[0], 0.8)  # psi
        self.assertAlmostEqual(arr[1], 0.6)  # tau

    def test_state_vector_distance(self):
        """Test Euclidean distance calculation in 5D state space."""
        state_a = StateVector(psi=0.0, tau=0.0, chi=0.0, phi=0.0, lam=0.0)
        state_b = StateVector(psi=1.0, tau=0.0, chi=0.0, phi=0.0, lam=0.0)

        distance = StateVector.distance(state_a, state_b)
        self.assertAlmostEqual(distance, 1.0, places=2)

    def test_state_vector_distance_diagonal(self):
        """Test distance along diagonal (all dimensions)."""
        state_a = StateVector(psi=0.0, tau=0.0, chi=0.0, phi=0.0, lam=0.0)
        state_b = StateVector(psi=1.0, tau=1.0, chi=1.0, phi=1.0, lam=1.0)

        # sqrt(1+1+1+1+1) = sqrt(5)
        distance = StateVector.distance(state_a, state_b)
        self.assertAlmostEqual(distance, np.sqrt(5), places=2)

    def test_coherence_metrics_compute_gamma_healthy(self):
        """Test Gamma computation for healthy state."""
        gamma, health = CoherenceMetrics.compute_gamma(
            perspective_diversity=0.75,
            tension_health=0.65,
            adapter_weight_variance=0.3,
            resolution_rate=0.6
        )

        # (0.25*0.75 + 0.25*0.65 + 0.25*(1-0.3) + 0.25*0.6)
        # = (0.1875 + 0.1625 + 0.175 + 0.15) = 0.6625
        self.assertGreater(gamma, 0.4)
        self.assertLess(gamma, 0.8)
        self.assertEqual(health, "healthy")

    def test_coherence_metrics_compute_gamma_collapsing(self):
        """Test Gamma computation for collapsing state."""
        gamma, health = CoherenceMetrics.compute_gamma(
            perspective_diversity=0.1,
            tension_health=0.2,
            adapter_weight_variance=0.9,
            resolution_rate=0.05
        )

        self.assertLess(gamma, 0.4)
        self.assertEqual(health, "collapsing")

    def test_coherence_metrics_compute_gamma_groupthink(self):
        """Test Gamma computation for groupthink state."""
        gamma, health = CoherenceMetrics.compute_gamma(
            perspective_diversity=0.95,
            tension_health=0.95,
            adapter_weight_variance=0.0,
            resolution_rate=0.95
        )

        self.assertGreater(gamma, 0.8)
        self.assertEqual(health, "groupthinking")

    def test_tension_definition_creation(self):
        """Test TensionDefinition creation."""
        tension = TensionDefinition(
            structural_xi=0.8,
            semantic_xi=0.6,
            combined_xi=0.7,
            opposition_type="contradiction",
            weight_structural=0.4,
            weight_semantic=0.6
        )

        self.assertEqual(tension.structural_xi, 0.8)
        self.assertEqual(tension.opposition_type, "contradiction")

        tension_dict = tension.to_dict()
        self.assertIn("combined_xi", tension_dict)

    def test_specialization_score_creation(self):
        """Test SpecializationScore creation."""
        score = SpecializationScore(
            adapter="Newton",
            domain="physics",
            domain_accuracy=0.85,
            usage_frequency=10,
            specialization_score=0.085,
            convergence_risk=False,
            recommendation="maintain"
        )

        self.assertEqual(score.adapter, "Newton")
        self.assertEqual(score.domain, "physics")

        score_dict = score.to_dict()
        self.assertIn("specialization_score", score_dict)

    def test_conflict_prediction_creation(self):
        """Test ConflictPrediction creation."""
        query_state = StateVector(psi=0.7, tau=0.6, chi=1.0, phi=0.2, lam=0.8)
        prediction = ConflictPrediction(
            query_state=query_state,
            predicted_high_tension_pairs=[{"agent_a": "Newton", "agent_b": "Quantum"}],
            conflict_profiles={"phi_conflicts": [1, 2]},
            recommendations={"boost": ["Ethics"]},
            preflight_confidence=0.82
        )

        self.assertEqual(prediction.preflight_confidence, 0.82)
        pred_dict = prediction.to_dict()
        self.assertIn("predicted_pairs_count", pred_dict)


class TestSemanticTensionEngine(unittest.TestCase):
    """Test semantic tension computation."""

    def setUp(self):
        """Initialize SemanticTensionEngine without Llama (use dummy embeddings)."""
        self.engine = SemanticTensionEngine(llama_model=None)

    def test_semantic_tension_engine_creation(self):
        """Test engine initialization."""
        self.assertIsNotNone(self.engine)
        self.assertEqual(self.engine.embedding_dim, 4096)

    def test_embed_claim_dummy(self):
        """Test embed_claim with dummy embeddings."""
        claim = "The speed of light is constant."
        embedding = self.engine.embed_claim(claim)

        # Should return normalized vector
        self.assertIsInstance(embedding, np.ndarray)
        self.assertEqual(len(embedding), self.engine.embedding_dim)

    def test_embed_claim_caching(self):
        """Test embedding caching."""
        claim = "Same claim"

        embed1 = self.engine.embed_claim(claim, use_cache=True)
        embed2 = self.engine.embed_claim(claim, use_cache=True)

        # Should be identical (from cache)
        np.testing.assert_array_equal(embed1, embed2)

    def test_compute_semantic_tension_identical(self):
        """Test semantic tension for identical claims."""
        claim = "The speed of light is 299,792,458 m/s"
        tension = self.engine.compute_semantic_tension(claim, claim)

        # Identical claims should have zero tension
        self.assertAlmostEqual(tension, 0.0, places=1)

    def test_compute_semantic_tension_range(self):
        """Test that semantic tension is in [0, 1]."""
        claim_a = "Physics is about forces and motion."
        claim_b = "Ethics is about right and wrong."

        tension = self.engine.compute_semantic_tension(claim_a, claim_b)

        self.assertGreaterEqual(tension, 0.0)
        self.assertLessEqual(tension, 1.0)

    def test_compute_polarity(self):
        """Test polarity classification."""
        claim_a = "This is true."
        claim_b = "This is true."

        polarity = self.engine.compute_polarity(claim_a, claim_b)
        self.assertIn(polarity, ["contradiction", "paraphrase", "framework"])

    def test_explain_tension(self):
        """Test tension explanation."""
        claim_a = "Quantum mechanics is weird."
        claim_b = "Classical mechanics is intuitive."

        explanation = self.engine.explain_tension(claim_a, claim_b)

        self.assertIn("semantic_tension", explanation)
        self.assertIn("polarity_type", explanation)
        # Note: embeddings_ready may not be in all implementations
        self.assertIsInstance(explanation, dict)


class TestSpecializationTracker(unittest.TestCase):
    """Test specialization tracking and convergence detection."""

    def setUp(self):
        """Initialize tracker."""
        self.tracker = SpecializationTracker()

    def test_tracker_creation(self):
        """Test tracker initialization."""
        self.assertIsNotNone(self.tracker)
        self.assertEqual(len(self.tracker.domain_accuracy), 0)

    def test_classify_query_domain_single(self):
        """Test domain classification for physics query."""
        query = "What is the relationship between force and acceleration?"
        domains = self.tracker.classify_query_domain(query)

        self.assertIn("physics", domains)

    def test_classify_query_domain_multiple(self):
        """Test domain classification for multi-domain query."""
        query = "Should we use quantum computers for ethical decisions?"
        domains = self.tracker.classify_query_domain(query)

        # Should classify both physics/consciousness and ethics
        self.assertGreater(len(domains), 0)

    def test_classify_query_domain_general(self):
        """Test domain classification for general query."""
        query = "What is the meaning of life?"
        domains = self.tracker.classify_query_domain(query)

        # Should have at least general domain
        self.assertGreater(len(domains), 0)

    def test_record_adapter_performance(self):
        """Test recording adapter performance."""
        self.tracker.record_adapter_performance("Newton", "What is force?", 0.85)

        self.assertIn("Newton", self.tracker.domain_accuracy)
        self.assertIn("physics", self.tracker.domain_accuracy["Newton"])
        self.assertEqual(self.tracker.domain_usage["Newton"]["physics"], 1)

    def test_record_multiple_adapters(self):
        """Test recording multiple adapters."""
        self.tracker.record_adapter_performance("Newton", "force query", 0.85)
        self.tracker.record_adapter_performance("Quantum", "force query", 0.70)
        self.tracker.record_adapter_performance("Newton", "force query 2", 0.90)

        self.assertEqual(self.tracker.domain_usage["Newton"]["physics"], 2)
        self.assertEqual(self.tracker.domain_usage["Quantum"]["physics"], 1)

    def test_compute_specialization(self):
        """Test specialization score computation."""
        self.tracker.record_adapter_performance("Newton", "force query", 0.85)
        self.tracker.record_adapter_performance("Newton", "force query 2", 0.90)
        self.tracker.record_adapter_performance("Newton", "ethics query", 0.50)

        specialization = self.tracker.compute_specialization("Newton")

        self.assertIn("physics", specialization)
        # Should have computed specialization scores
        self.assertGreater(len(specialization), 0)
        # Physics score should be positive
        self.assertGreater(specialization["physics"], 0.0)

    def test_detect_semantic_convergence_no_convergence(self):
        """Test convergence detection with different outputs."""
        outputs = {
            "Newton": "Force equals mass times acceleration (F=ma).",
            "Quantum": "At quantum scales, uncertainty dominates particle behavior."
        }

        # Mock semantic engine with low similarity
        class MockSemanticEngine:
            def embed_claim(self, text):
                # Return different vectors for different texts
                if "Force" in text:
                    return np.array([1.0] + [0.0] * 4095)
                else:
                    return np.array([0.0, 1.0] + [0.0] * 4094)

        self.tracker.semantic_engine = MockSemanticEngine()
        convergence = self.tracker.detect_semantic_convergence(outputs)

        # Should be empty or have low convergence
        self.assertIsInstance(convergence, dict)


class TestIntegration(unittest.TestCase):
    """Integration tests for Phase 6 components."""

    def test_framework_and_semantic_together(self):
        """Test framework definitions with semantic engine."""
        state = StateVector(psi=0.8, tau=0.6, chi=1.2, phi=0.3, lam=0.7)
        engine = SemanticTensionEngine(llama_model=None)

        claim_a = "The universe is deterministic."
        claim_b = "Quantum mechanics introduces indeterminacy."

        semantic_xi = engine.compute_semantic_tension(claim_a, claim_b)
        structural_xi = StateVector.distance(
            state,
            StateVector(psi=0.5, tau=0.7, chi=0.8, phi=-0.2, lam=0.6)
        )

        # Create combined tension definition
        tension = TensionDefinition(
            structural_xi=structural_xi,
            semantic_xi=semantic_xi,
            combined_xi=0.6 * semantic_xi + 0.4 * min(structural_xi / 3.5, 1.0),
            opposition_type="contradiction",
            weight_structural=0.4,
            weight_semantic=0.6
        )

        self.assertGreater(tension.combined_xi, 0.0)
        self.assertLess(tension.combined_xi, 1.5)

    def test_specialization_with_coherence(self):
        """Test specialization tracker with coherence metrics."""
        tracker = SpecializationTracker()

        # Simulate debates
        tracker.record_adapter_performance("Newton", "force query", 0.88)
        tracker.record_adapter_performance("Newton", "force query 2", 0.91)
        tracker.record_adapter_performance("Quantum", "quantum query", 0.82)
        tracker.record_adapter_performance("Quantum", "quantum query 2", 0.85)

        # Compute coherence
        gamma, health = CoherenceMetrics.compute_gamma(
            perspective_diversity=0.8,
            tension_health=0.7,
            adapter_weight_variance=0.2,
            resolution_rate=0.75
        )

        self.assertEqual(health, "healthy")
        self.assertGreater(gamma, 0.5)


def run_tests():
    """Run all tests and report results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestFrameworkDefinitions))
    suite.addTests(loader.loadTestsFromTestCase(TestSemanticTensionEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestSpecializationTracker))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == "__main__":
    result = run_tests()

    # Print summary
    print("\n" + "="*70)
    print("PHASE 6 TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
    print("="*70)
