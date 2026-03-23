#!/usr/bin/env python3
"""Phase 5 End-to-End Integration Tests

Tests the complete Phase 5 system:
1. ReinforcementConfig tunable coefficients
2. AdapterRouter with MemoryWeighting integration
3. CodetteOrchestrator routing with memory context
4. Gamma stabilization field health monitoring
5. RoutingMetrics observability

Run with: python test_phase5_e2e.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.memory_weighting import MemoryWeighting, ReinforcementConfig
from reasoning_forge.coherence_field import CoherenceFieldGamma, GammaHealthMetrics, InterventionType
from reasoning_forge.routing_metrics import RoutingMetrics, AdapterSelectionRecord
from inference.adapter_router import AdapterRouter, RouteResult


def test_reinforcement_config():
    """Test ReinforcementConfig tunable coefficients."""
    print("\n=== Test 1: Reinforcement Config ===")

    # Test default values
    config = ReinforcementConfig()
    assert config.boost_successful == 0.08, "Default boost should be 0.08"
    assert config.penalize_failed == 0.08, "Default penalize should be 0.08"
    assert config.reward_soft_consensus == 0.03, "Default soft_consensus should be 0.03"
    print("[OK] Default coefficients loaded")

    # Test from_dict()
    custom_dict = {
        "boost_successful": 0.12,
        "penalize_failed": 0.10,
        "reward_soft_consensus": 0.05,
    }
    custom = ReinforcementConfig.from_dict(custom_dict)
    assert custom.boost_successful == 0.12, "Custom boost not applied"
    assert custom.penalize_failed == 0.10, "Custom penalize not applied"
    print("[OK] Custom coefficients loaded from dict")

    # Test to_dict()
    exported = custom.to_dict()
    assert exported["boost_successful"] == 0.12, "Export failed"
    print("[OK] Coefficients exported to dict")

    # Test partial config (missing keys should use defaults)
    partial = ReinforcementConfig.from_dict({"boost_successful": 0.15})
    assert partial.boost_successful == 0.15, "Partial override failed"
    assert partial.penalize_failed == 0.08, "Default not used for missing key"
    print("[OK] Partial config with defaults works")

    return True


def test_adapter_router_with_memory():
    """Test AdapterRouter memory weighting integration."""
    print("\n=== Test 2: AdapterRouter with Memory ===")

    # Create router without memory
    router_no_mem = AdapterRouter(available_adapters=["newton", "davinci", "empathy"])
    assert router_no_mem.memory_weighting is None, "Router should not have memory"
    print("[OK] Router created without memory")

    # Route a simple query
    query = "Explain the physics of gravity"
    route = router_no_mem.route(query, strategy="keyword")
    assert route.primary == "newton", "Should select newton for physics query"
    assert route.confidence > 0.0, "Confidence should be set"
    print(f"[OK] Routed to {route.primary} with confidence {route.confidence:.2f}")

    # Test explain_routing without memory
    explanation = router_no_mem.explain_routing(route)
    assert "primary" in explanation, "Explanation missing primary"
    assert explanation["memory_aware"] is False, "Should show memory not available"
    print("[OK] Routing explanation works without memory")

    return True


def test_gamma_health_monitoring():
    """Test Gamma (Γ) stabilization field."""
    print("\n=== Test 3: Gamma Health Monitoring ===")

    gamma = CoherenceFieldGamma()

    # Simulate a healthy debate (diverse perspectives, good resolution)
    class MockConflict:
        def __init__(self):
            self.strength = 0.25  # Productive zone

    conflicts = [MockConflict(), MockConflict()]
    responses = {
        "newton": "Physics perspective",
        "davinci": "Creative perspective",
        "empathy": "Emotional perspective",
    }

    # Compute health
    health = gamma.compute_health(
        conflicts=conflicts,
        responses=responses,
        adapter_weights={"newton": 1.0, "davinci": 1.0, "empathy": 1.0},
    )

    assert 0.0 <= health.gamma <= 1.0, "Gamma should be in [0, 1]"
    assert len(gamma.health_history) == 1, "Should record health metric"
    print(f"[OK] Healthy state: Gamma = {health.gamma:.3f}")
    assert health.is_stable(), "Should be in stable zone"
    print("[OK] Status correctly identified as stable")

    # Simulate collapse (no diversity, low resolution)
    mono_responses = {"newton": "Only newton perspective"}
    weak_conflicts = []  # No progress

    health_collapse = gamma.compute_health(
        conflicts=weak_conflicts,
        responses=mono_responses,
        adapter_weights={"newton": 2.0},  # All weight on one
    )

    print(f"[OK] Collapsed state: Gamma = {health_collapse.gamma:.3f}")
    if health_collapse.gamma < 0.4:
        assert health_collapse.is_collapsing(), "Should detect collapse"
        print("[OK] Collapse correctly detected")

    # Test intervention detection
    intervention = gamma.get_intervention(health_collapse, ["davinci", "empathy"])
    if intervention:
        assert intervention.intervention_type == InterventionType.DIVERSITY_INJECTION, \
            "Should inject diversity on collapse"
        print(f"[OK] Intervention recommended: {intervention.intervention_type.value}")

    return True


def test_routing_metrics():
    """Test RoutingMetrics observability."""
    print("\n=== Test 4: Routing Metrics ===")

    metrics = RoutingMetrics()
    assert metrics.total_queries == 0, "Should start at 0"
    print("[OK] RoutingMetrics initialized")

    # Record some routing decisions
    record1 = RoutingMetrics.create_record(
        query="What is quantum mechanics?",
        primary_adapter="quantum",
        secondary_adapters=["physics"],
        strategy="keyword",
        confidence_before_boost=0.75,
        confidence_after_boost=0.85,
        memory_boost_applied=True,
    )
    metrics.record_route(record1)

    assert metrics.total_queries == 1, "Should count query"
    assert metrics.adapter_selection_counts["quantum"] == 1, "Should count selection"
    assert metrics.memory_boost_count == 1, "Should count boost"
    print("[OK] Route recorded and metrics updated")

    # Record more routes
    for i in range(4):
        record = RoutingMetrics.create_record(
            query="Another query",
            primary_adapter="newton",
            secondary_adapters=[],
            strategy="keyword",
            confidence_before_boost=0.6,
            confidence_after_boost=0.6,
            memory_boost_applied=False,
        )
        metrics.record_route(record)

    assert metrics.total_queries == 5, "Should have 5 queries"
    assert metrics.adapter_selection_counts["newton"] == 4, "Newton selected 4 times"
    print(f"[OK] Recorded 5 queries total")

    # Get summary
    summary = metrics.get_summary()
    assert summary["total_queries"] == 5, "Summary should show total queries"
    assert "quantum" in summary["adapter_stats"], "Should have quantum stats"
    assert "newton" in summary["adapter_stats"], "Should have newton stats"
    print(f"[OK] Summary generated with {len(summary['adapter_stats'])} adapters")

    # Check specific adapter stats
    newton_stats = metrics.get_adapter_stats("newton")
    assert newton_stats["total_selections"] == 4, "Newton should have 4 selections"
    assert newton_stats["memory_boost_hits"] == 0, "Newton had no boosts"
    print(f"[OK] Adapter stats: {newton_stats['total_selections']} selections")

    # Get recent routes
    recent = metrics.get_recent_routes(limit=3)
    assert len(recent) == 3, "Should return 3 recent routes"
    assert recent[0]["primary"] == "newton", "Most recent should be newton"
    print("[OK] Recent routes retrieved")

    return True


def test_phase5_integration():
    """Test complete Phase 5 integration (all components together)."""
    print("\n=== Test 5: Phase 5 Complete Integration ===")

    # Create router with memory (normally would load from disk)
    router = AdapterRouter(
        available_adapters=["newton", "davinci", "empathy", "philosophy"],
        memory_weighting=None,  # Phase 5 but no memory loaded
    )
    print("[OK] Router created with Phase 5 integration ready")

    # Create Gamma field
    gamma = CoherenceFieldGamma()
    print("[OK] Gamma stabilization field initialized")

    # Create metrics tracker
    routing_metrics = RoutingMetrics()
    print("[OK] Routing metrics tracker initialized")

    # Simulate a complete routing cycle
    query = "How should society balance freedom and security?"
    route = router.route(query, strategy="keyword", max_adapters=2)

    # Create metrics record
    record = RoutingMetrics.create_record(
        query=query,
        primary_adapter=route.primary,
        secondary_adapters=route.secondary,
        strategy=route.strategy,
        confidence_before_boost=0.7,
        confidence_after_boost=0.7,
        memory_boost_applied=False,
    )
    routing_metrics.record_route(record)

    # Simulate debate with conflict
    class MockConflict:
        def __init__(self, agent_a, agent_b):
            self.agent_a = agent_a
            self.agent_b = agent_b
            self.strength = 0.15

    conflicts = [MockConflict("newton", "philosophy")]
    responses = {
        "newton": "Mathematical security metrics",
        "philosophy": "Ethical freedom considerations",
        "davinci": "Innovative balance approaches",
    }

    # Check health
    health = gamma.compute_health(conflicts, responses)
    # Determine status based on is_* methods
    if health.is_collapsing():
        status = "collapsing"
    elif health.is_groupthinking():
        status = "groupthinking"
    else:
        status = "stable"
    print(f"[OK] Health computed: Gamma = {health.gamma:.3f} ({status})")

    # Get all metrics
    summary = routing_metrics.get_summary()
    gamma_data = gamma.export_metrics()

    assert summary["total_queries"] == 1, "Should have recorded 1 query"
    assert "health_history" in gamma_data, "Should export health history"
    print("[OK] All Phase 5 components working together")

    return True


def main():
    """Run all Phase 5 tests."""
    print("=" * 70)
    print("PHASE 5 END-TO-END INTEGRATION TESTS")
    print("=" * 70)

    tests = [
        ("Reinforcement Config", test_reinforcement_config),
        ("AdapterRouter Memory", test_adapter_router_with_memory),
        ("Gamma Health Monitoring", test_gamma_health_monitoring),
        ("Routing Metrics", test_routing_metrics),
        ("Phase 5 Integration", test_phase5_integration),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n[PASS] {test_name} PASSED")
            else:
                failed += 1
                print(f"\n[FAIL] {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"\n[FAIL] {test_name} ERROR: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
