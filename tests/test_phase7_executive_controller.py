"""Tests for Phase 7 Executive Controller

Validates:
1. Routing decisions for SIMPLE/MEDIUM/COMPLEX queries
2. Component activation correctness
3. Transparency metadata generation
4. Latency and correctness estimates
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from reasoning_forge.query_classifier import QueryComplexity
from reasoning_forge.executive_controller import (
    ExecutiveController,
    ExecutiveControllerWithLearning,
    ComponentDecision,
)


def test_simple_routing():
    """Test that SIMPLE queries skip heavy machinery."""
    ctrl = ExecutiveController(verbose=True)
    decision = ctrl.route_query("What is the speed of light?", QueryComplexity.SIMPLE)

    assert decision.query_complexity == QueryComplexity.SIMPLE
    assert decision.component_activation['debate'] == False
    assert decision.component_activation['semantic_tension'] == False
    assert decision.component_activation['preflight_predictor'] == False
    assert decision.estimated_latency_ms < 200  # Fast
    assert decision.estimated_correctness > 0.90
    assert decision.estimated_compute_cost < 10  # Low cost
    print("[OK] SIMPLE routing correct")


def test_medium_routing():
    """Test that MEDIUM queries use selective components."""
    ctrl = ExecutiveController(verbose=True)
    decision = ctrl.route_query(
        "How does quantum mechanics relate to consciousness?",
        QueryComplexity.MEDIUM
    )

    assert decision.query_complexity == QueryComplexity.MEDIUM
    assert decision.component_activation['debate'] == True
    assert decision.component_activation['semantic_tension'] == True
    assert decision.component_activation['specialization_tracking'] == True
    assert decision.component_activation['preflight_predictor'] == False  # Skipped
    assert decision.component_config.get('debate_rounds') == 1
    assert 800 < decision.estimated_latency_ms < 1000  # Medium latency
    assert decision.estimated_correctness > 0.70
    assert 20 < decision.estimated_compute_cost < 30
    print("[OK] MEDIUM routing correct")


def test_complex_routing():
    """Test that COMPLEX queries use full machinery."""
    ctrl = ExecutiveController(verbose=True)
    decision = ctrl.route_query(
        "Can machines be truly conscious?",
        QueryComplexity.COMPLEX
    )

    assert decision.query_complexity == QueryComplexity.COMPLEX
    assert decision.component_activation['debate'] == True
    assert decision.component_activation['semantic_tension'] == True
    assert decision.component_activation['preflight_predictor'] == True
    assert decision.component_activation['specialization_tracking'] == True
    assert decision.component_config.get('debate_rounds') == 3
    assert decision.estimated_latency_ms > 2000  # Slow but thorough
    assert 40 < decision.estimated_compute_cost < 60
    print("[OK] COMPLEX routing correct")


def test_route_transparency_metadata():
    """Test that routing transparency metadata is generated correctly."""
    ctrl = ExecutiveController()
    decision = ctrl.route_query(
        "What is entropy?",
        QueryComplexity.SIMPLE
    )

    # Simulate execution with measured latency
    metadata = ExecutiveController.create_route_metadata(
        decision=decision,
        actual_latency_ms=145,  # Slightly faster than estimated
        actual_conflicts=0,
        gamma=0.95
    )

    assert 'phase7_routing' in metadata
    routing = metadata['phase7_routing']

    assert routing['query_complexity'] == 'simple'
    assert 'components_activated' in routing
    assert routing['components_activated']['debate'] == False
    assert routing['components_activated']['semantic_tension'] == False

    # Check latency analysis
    assert routing['latency_analysis']['estimated_ms'] == decision.estimated_latency_ms
    assert routing['latency_analysis']['actual_ms'] == 145
    assert routing['latency_analysis']['savings_ms'] > 0  # Faster than estimated

    # Check metrics
    assert routing['metrics']['conflicts_detected'] == 0
    assert routing['metrics']['gamma_coherence'] == 0.95

    print("[OK] Transparency metadata correct")


def test_routing_statistics():
    """Test that controller tracks routing statistics."""
    ctrl = ExecutiveController()

    # Simulate several queries
    ctrl.route_query("What is light?", QueryComplexity.SIMPLE)
    ctrl.route_query("What is light?", QueryComplexity.SIMPLE)
    ctrl.route_query("How does light work?", QueryComplexity.MEDIUM)
    ctrl.route_query("Can light be conscious?", QueryComplexity.COMPLEX)

    stats = ctrl.get_routing_statistics()

    assert stats['total_queries_routed'] == 4
    assert 'component_activation_counts' in stats
    print(f"  Stats: {stats}")
    print("[OK] Routing statistics tracked")


def test_component_activation_counts():
    """Test that component activation counts are accurate."""
    ctrl = ExecutiveController()

    # Route several queries
    for _ in range(3):
        ctrl.route_query("What?", QueryComplexity.SIMPLE)
    for _ in range(2):
        ctrl.route_query("How?", QueryComplexity.MEDIUM)
    for _ in range(1):
        ctrl.route_query("Why?", QueryComplexity.COMPLEX)

    stats = ctrl.get_routing_statistics()
    counts = stats['component_activation_counts']

    # SIMPLE queries (3): only synthesis should be False
    # MEDIUM/COMPLEX queries (3): debate should be activated 3 times
    assert counts.get('debate', 0) == 3  # MEDIUM (2) + COMPLEX (1)
    assert counts.get('semantic_tension', 0) == 3
    assert counts.get('specialization_tracking', 0) == 3

    print(f"  Component activation counts: {counts}")
    print("[OK] Component activation counts correct")


def test_learning_routing():
    """Test that learning router initializes and learns."""
    ctrl = ExecutiveControllerWithLearning(verbose=False)  # Quieter for test

    # Initial route (no learned patterns yet)
    decision = ctrl.route_query("What's the speed?", QueryComplexity.SIMPLE)
    assert decision.query_complexity == QueryComplexity.SIMPLE

    # Directly set learned routes (simulating what update_routes_from_history would do)
    ctrl.learned_routes = {
        'simple': 0.95,   # Use lowercase to match QueryComplexity.value
        'medium': 0.80,
        'complex': 0.85,
    }

    # Check that learned routes were set
    assert 'simple' in ctrl.learned_routes
    assert 'medium' in ctrl.learned_routes
    assert 'complex' in ctrl.learned_routes

    # Simple routes should have highest confidence
    assert ctrl.learned_routes['simple'] >= ctrl.learned_routes['medium']

    # Test get_route_confidence
    simple_confidence = ctrl.get_route_confidence(QueryComplexity.SIMPLE)
    assert simple_confidence == 0.95, f"Expected 0.95, got {simple_confidence}"

    print(f"  Learned routes: {ctrl.learned_routes}")
    print("[OK] Learning router works")


def test_compute_cost_ranking():
    """Test that compute costs are ranked correctly: SIMPLE < MEDIUM < COMPLEX."""
    ctrl = ExecutiveController()

    simple_decision = ctrl.route_query("Q1?", QueryComplexity.SIMPLE)
    medium_decision = ctrl.route_query("Q2?", QueryComplexity.MEDIUM)
    complex_decision = ctrl.route_query("Q3?", QueryComplexity.COMPLEX)

    # Reset counts
    ctrl.route_activation_counts = {}

    assert simple_decision.estimated_compute_cost < medium_decision.estimated_compute_cost
    assert medium_decision.estimated_compute_cost < complex_decision.estimated_compute_cost

    print(f"  Cost ranking: {simple_decision.estimated_compute_cost} < "
          f"{medium_decision.estimated_compute_cost} < "
          f"{complex_decision.estimated_compute_cost}")
    print("[OK] Compute cost ranking correct")


def test_latency_ranking():
    """Test that latencies are ranked correctly: SIMPLE < MEDIUM < COMPLEX."""
    ctrl = ExecutiveController()

    simple = ctrl.route_query("Q1?", QueryComplexity.SIMPLE)
    medium = ctrl.route_query("Q2?", QueryComplexity.MEDIUM)
    complex = ctrl.route_query("Q3?", QueryComplexity.COMPLEX)

    assert simple.estimated_latency_ms < medium.estimated_latency_ms
    assert medium.estimated_latency_ms < complex.estimated_latency_ms

    print(f"  Latency ranking: {simple.estimated_latency_ms}ms < "
          f"{medium.estimated_latency_ms}ms < "
          f"{complex.estimated_latency_ms}ms")
    print("[OK] Latency ranking correct")


def test_component_decision_asdict():
    """Test that ComponentDecision can be serialized."""
    ctrl = ExecutiveController()
    decision = ctrl.route_query("Test query", QueryComplexity.SIMPLE)

    # Should be able to convert to dict
    decision_dict = {
        'query_complexity': decision.query_complexity.value,
        'component_activation': decision.component_activation,
        'reasoning': decision.reasoning,
        'estimated_latency_ms': decision.estimated_latency_ms,
        'estimated_correctness': decision.estimated_correctness,
        'estimated_compute_cost': decision.estimated_compute_cost,
    }

    assert decision_dict['query_complexity'] == 'simple'
    assert decision_dict['reasoning'] != ""
    print("[OK] ComponentDecision serializable")


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("Phase 7 Executive Controller Tests")
    print("=" * 70 + "\n")

    test_simple_routing()
    test_medium_routing()
    test_complex_routing()
    test_route_transparency_metadata()
    test_routing_statistics()
    test_component_activation_counts()
    test_learning_routing()
    test_compute_cost_ranking()
    test_latency_ranking()
    test_component_decision_asdict()

    print("\n" + "=" * 70)
    print("PASS: All Phase 7 Executive Controller tests passed!")
    print("=" * 70 + "\n")
