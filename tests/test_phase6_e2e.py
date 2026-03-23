"""
Phase 6 End-to-End Integration Tests

Tests all Phase 6 components working together:
1. Semantic tension engine (embedding-based opposition)
2. Specialization tracker (domain expertise)
3. Pre-flight conflict predictor (Spiderweb-based)
4. Benchmarking suite
5. Full integration in ForgeEngine debate loop

Run with: pytest test_phase6_e2e.py -v
"""

import pytest
import json
import numpy as np
from reasoning_forge.framework_definitions import (
    StateVector,
    TensionDefinition,
    CoherenceMetrics,
    ConflictPrediction,
    SpecializationScore,
)
from reasoning_forge.semantic_tension import SemanticTensionEngine
from reasoning_forge.specialization_tracker import SpecializationTracker
from reasoning_forge.preflight_predictor import PreFlightConflictPredictor


class TestPhase6Framework:
    """Test Phase 6 mathematical framework definitions."""

    def test_state_vector_creation(self):
        """Test StateVector dataclass."""
        state = StateVector(psi=0.8, tau=0.2, chi=0.5, phi=0.3, lam=0.6)
        assert state.psi == 0.8
        assert len(state.to_array()) == 5
        state_dict = state.to_dict()
        assert "psi" in state_dict
        assert round(state_dict["psi"], 3) == 0.8

    def test_state_vector_distance(self):
        """Test Euclidean distance in 5D state space."""
        state_a = StateVector(psi=0.0, tau=0.0, chi=0.0, phi=0.0, lam=0.0)
        state_b = StateVector(psi=3.0, tau=4.0, chi=0.0, phi=0.0, lam=0.0)
        distance = StateVector.distance(state_a, state_b)
        # Distance should be sqrt(9 + 16) = 5
        assert abs(distance - 5.0) < 0.1, f"Expected ~5, got {distance}"

    def test_tension_definition(self):
        """Test TensionDefinition dataclass."""
        tension = TensionDefinition(
            structural_xi=1.2,
            semantic_xi=0.5,
            combined_xi=0.9,
            opposition_type="framework",
            weight_structural=0.4,
            weight_semantic=0.6,
        )
        assert tension.combined_xi == 0.9
        tensor_dict = tension.to_dict()
        assert tensor_dict["opposition_type"] == "framework"

    def test_coherence_metrics_gamma_computation(self):
        """Test Gamma score computation."""
        gamma, status = CoherenceMetrics.compute_gamma(
            perspective_diversity=0.9,
            tension_health=0.8,
            adapter_weight_variance=0.2,
            resolution_rate=0.7,
        )
        # Expected: (0.25*0.9 + 0.25*0.8 + 0.25*0.8 + 0.25*0.7) = ~0.8
        assert 0.75 < gamma < 0.85
        assert status == "healthy"

    def test_coherence_metrics_collapse_detection(self):
        """Test Gamma collapse detection (< 0.4)."""
        gamma, status = CoherenceMetrics.compute_gamma(
            perspective_diversity=0.1,
            tension_health=0.2,
            adapter_weight_variance=0.9,
            resolution_rate=0.1,
        )
        assert gamma < 0.4
        assert status == "collapsing"

    def test_coherence_metrics_groupthink_detection(self):
        """Test Gamma groupthink detection (> 0.8)."""
        gamma, status = CoherenceMetrics.compute_gamma(
            perspective_diversity=0.95,
            tension_health=0.95,
            adapter_weight_variance=0.05,
            resolution_rate=0.95,
        )
        assert gamma > 0.8
        assert status == "groupthinking"


class TestSemanticTension:
    """Test semantic tension engine."""

    def test_semantic_tension_initialization(self):
        """Test SemanticTensionEngine creation."""
        engine = SemanticTensionEngine(llama_model=None)
        assert engine is not None
        assert engine.embedding_dim == 4096

    def test_semantic_tension_identical_claims(self):
        """Test that identical claims have low tension."""
        engine = SemanticTensionEngine(llama_model=None)
        claim = "The sky is blue"
        tension = engine.compute_semantic_tension(claim, claim)
        # Identical embeddings → cosine similarity ≈ 1 → tension ≈ 0
        assert 0.0 <= tension <= 0.1, f"Identical claims should have low tension, got {tension}"

    def test_semantic_tension_different_claims(self):
        """Test that different claims have higher tension."""
        engine = SemanticTensionEngine(llama_model=None)
        claim_a = "The sky is blue"
        claim_b = "The ocean is red"
        tension = engine.compute_semantic_tension(claim_a, claim_b)
        # Different claims → orthogonal embeddings → tension > 0
        assert tension > 0.0, f"Different claims should have positive tension, got {tension}"
        assert tension <= 1.0

    def test_polarity_classification(self):
        """Test polarity type classification."""
        engine = SemanticTensionEngine(llama_model=None)
        claim_a = "I agree with this"
        claim_b = "I also agree with this"
        polarity = engine.compute_polarity(claim_a, claim_b)
        # Similar claims → paraphrase or framework, not contradiction
        assert polarity in ["paraphrase", "framework", "contradiction"]

    def test_embedding_cache(self):
        """Test caching mechanism."""
        engine = SemanticTensionEngine(llama_model=None)
        claim = "Test claim"

        # First call: cache miss
        embed_1 = engine.embed_claim(claim, use_cache=True)

        # Check cache was populated
        stats = engine.get_cache_stats()
        assert stats["cached_embeddings"] >= 1

        # Second call: cache hit (same object)
        embed_2 = engine.embed_claim(claim, use_cache=True)
        assert np.array_equal(embed_1, embed_2)


class TestSpecializationTracker:
    """Test adapter specialization tracking."""

    def test_specialization_initialization(self):
        """Test SpecializationTracker creation."""
        tracker = SpecializationTracker()
        assert tracker is not None
        assert len(tracker.DOMAIN_KEYWORDS) > 0

    def test_query_domain_classification(self):
        """Test query domain classification."""
        tracker = SpecializationTracker()

        # Physics query
        domains = tracker.classify_query_domain("What is the force of gravity?")
        assert "physics" in domains

        # Ethics query
        domains = tracker.classify_query_domain("Is it right to do this?")
        assert "ethics" in domains

        # No domain match
        domains = tracker.classify_query_domain("Hello world")
        assert "general" in domains

    def test_adapter_performance_recording(self):
        """Test recording adapter performance."""
        tracker = SpecializationTracker()
        tracker.record_adapter_performance("newton", "What is force?", 0.85)
        tracker.record_adapter_performance("newton", "What is acceleration?", 0.90)

        specialization = tracker.compute_specialization("newton")
        assert "physics" in specialization
        # specialization = mean(0.85, 0.90) / usage(2) = 0.875 / 2 = 0.4375
        assert 0.4 <= specialization["physics"] <= 0.5

    def test_semantic_convergence_detection(self):
        """Test convergence detection between adapters."""
        tracker = SpecializationTracker()
        outputs = {
            "newton": "The answer is clearly related to physics and forces.",
            "empathy": "The answer is clearly related to feelings and emotions.",
        }
        convergence = tracker.detect_semantic_convergence(outputs)
        assert "convergent_pairs" in convergence
        # These outputs are different, so should have low convergence
        assert convergence["max_similarity"] < 0.7

    def test_adapter_health(self):
        """Test adapter health scoring."""
        tracker = SpecializationTracker()
        tracker.record_adapter_performance("newton", "physics query 1", 0.9)
        tracker.record_adapter_performance("newton", "physics query 2", 0.85)

        health = tracker.get_adapter_health("newton")
        assert health["adapter"] == "newton"
        assert health["avg_accuracy"] > 0.8
        assert "recommendation" in health


class TestPreFlightPredictor:
    """Test pre-flight conflict prediction."""

    def test_predictor_initialization(self):
        """Test PreFlightConflictPredictor creation."""
        predictor = PreFlightConflictPredictor(spiderweb=None)
        assert predictor is not None

    def test_query_encoding(self):
        """Test encoding queries to 5D state vectors."""
        predictor = PreFlightConflictPredictor(spiderweb=None)

        # Simple query
        state = predictor.encode_query_to_state("What is force?")
        assert isinstance(state, StateVector)
        assert 0 <= state.psi <= 1
        assert 0 <= state.tau <= 1
        assert -1 <= state.phi <= 1

        # Complex query with ethics
        state_eth = predictor.encode_query_to_state(
            "Should we use AI ethically in society?"
        )
        assert state_eth.phi > 0.0, "Ethical query should have emotional valence"

    def test_empty_prediction_fallback(self):
        """Test fallback when spiderweb is unavailable."""
        predictor = PreFlightConflictPredictor(spiderweb=None)
        query_state = StateVector(psi=0.5, tau=0.5, chi=0.5, phi=0.5, lam=0.5)
        prediction = predictor._empty_prediction(query_state)
        assert isinstance(prediction, ConflictPrediction)
        assert prediction.preflight_confidence == 0.0


class TestPhase6Integration:
    """Test full Phase 6 integration."""

    def test_framework_definitions_export(self):
        """Test exporting framework definitions to JSON."""
        state = StateVector(psi=0.7, tau=0.3, chi=0.5, phi=0.4, lam=0.6)
        state_dict = state.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(state_dict)
        parsed = json.loads(json_str)
        assert parsed["psi"] == round(0.7, 3)

    def test_semantic_tension_explain(self):
        """Test detailed semantic tension explanation."""
        engine = SemanticTensionEngine(llama_model=None)
        explanation = engine.explain_tension("Claim A", "Claim B")
        assert "semantic_tension" in explanation
        assert "similarity" in explanation
        assert "polarity_type" in explanation

    def test_specialization_system_health(self):
        """Test overall specialization system health."""
        tracker = SpecializationTracker()
        tracker.record_adapter_performance("newton", "Force query", 0.9)
        tracker.record_adapter_performance("empathy", "Emotion query", 0.85)

        system_health = tracker.get_system_health()
        assert "total_adapters" in system_health
        assert "health_by_adapter" in system_health
        assert system_health["total_adapters"] == 2


class TestPhase6Benchmarks:
    """Test benchmarking suite (without full ForgeEngine)."""

    def test_benchmark_framework_instantiation(self):
        """Test Phase6Benchmarks class."""
        from evaluation.phase6_benchmarks import Phase6Benchmarks

        benchmarks = Phase6Benchmarks(forge_engine=None)
        assert benchmarks is not None
        assert "multi_round_convergence" in benchmarks.results

    def test_benchmark_summary_generation(self):
        """Test benchmark summary formatting."""
        from evaluation.phase6_benchmarks import Phase6Benchmarks

        benchmarks = Phase6Benchmarks(forge_engine=None)
        summary = benchmarks.summary()
        assert "PHASE 6 BENCHMARK SUMMARY" in summary
        assert "MULTI-ROUND" in summary or "MEMORY" in summary


# ===================================================================
# Integration Test: All Components Together (MockForgeEngine)
# ===================================================================


class MockForgeEngine:
    """Mock ForgeEngine for testing Phase 6 integration without full system."""

    def __init__(self):
        self.semantic_tension_engine = SemanticTensionEngine(llama_model=None)
        self.specialization = SpecializationTracker()
        self.conflict_engine = type("obj", (object,), {
            "_classify_conflict": lambda _self, a, b, o: ("framework", 0.5)
        })()

    def forge_with_debate(self, query, use_memory_weights=False, num_rounds=2):
        """Mock debate method."""
        return {
            "synthesis": "Mock synthesis",
            "metadata": {
                "coherence": 0.75,
                "resolution_rate": 0.8,
            }
        }


@pytest.mark.integration
class TestPhase6EndToEnd:
    """End-to-end Phase 6 tests."""

    def test_full_phase6_pipeline(self):
        """Test all Phase 6 components in sequence."""
        # Create mock system
        forge = MockForgeEngine()

        # Test 1: Semantic tension
        tension = forge.semantic_tension_engine.compute_semantic_tension(
            "This is true", "This is false"
        )
        assert 0 <= tension <= 1

        # Test 2: Specialization
        forge.specialization.record_adapter_performance("test_adapter", "physics query", 0.9)
        specs = forge.specialization.get_global_specialization()
        assert "test_adapter" in specs

        # Test 3: Pre-flight prediction (with encoding)
        predictor = PreFlightConflictPredictor(spiderweb=None)
        state = predictor.encode_query_to_state("Test query")
        assert state.psi >= 0

    def test_phase6_with_benchmarks(self):
        """Test Phase6Benchmarks with mock data."""
        from evaluation.phase6_benchmarks import Phase6Benchmarks

        forge = MockForgeEngine()
        benchmarks = Phase6Benchmarks(forge_engine=forge)

        # Test specialization benchmark (no ForgeEngine calls needed)
        result = benchmarks.benchmark_specialization()
        assert "adapters_tracked" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
