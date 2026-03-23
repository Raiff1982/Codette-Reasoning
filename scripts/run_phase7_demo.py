#!/usr/bin/env python3
"""Phase 7 Executive Controller - Quick Local Testing Demo

Run this to test Phase 7 routing in real time without launching the full web server.
Shows which components activate for different query complexities.

Usage:
    python run_phase7_demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.query_classifier import QueryClassifier, QueryComplexity
from reasoning_forge.executive_controller import ExecutiveController


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def demo_query(ctrl, classifier, query: str):
    """Demonstrate Phase 7 routing for a single query."""
    print(f"Query: {query}")

    # Classify
    complexity = classifier.classify(query)
    print(f"  Complexity: {complexity.value.upper()}")

    # Route
    decision = ctrl.route_query(query, complexity)

    # Show routing decision
    print(f"  Routing Decision:")
    print(f"    - Estimated Latency: {decision.estimated_latency_ms:.0f}ms")
    print(f"    - Estimated Correctness: {decision.estimated_correctness:.1%}")
    print(f"    - Compute Cost: {decision.estimated_compute_cost:.0f} units")
    print(f"    - Reasoning: {decision.reasoning}")

    # Show component activation
    active_components = [k for k, v in decision.component_activation.items() if v]
    inactive_components = [k for k, v in decision.component_activation.items() if not v]

    if active_components:
        print(f"  Components ACTIVATED: {', '.join(active_components)}")
    if inactive_components:
        print(f"  Components SKIPPED: {', '.join(inactive_components)}")

    print()


def main():
    """Run Phase 7 demo."""
    print_section("Phase 7 Executive Controller - Local Testing Demo")

    # Initialize
    print("Initializing Executive Controller and Query Classifier...")
    ctrl = ExecutiveController(verbose=False)
    classifier = QueryClassifier()
    print("OK - Ready for demo\n")

    # SIMPLE queries
    print_section("SIMPLE Queries (Factual - Fast Routing)")
    print("These should skip heavy machinery and run direct orchestrator\n")

    simple_queries = [
        "What is the speed of light?",
        "Define entropy",
        "Who is Albert Einstein?",
        "What year was the Internet invented?",
        "Calculate 2^10",
    ]

    for query in simple_queries:
        demo_query(ctrl, classifier, query)

    # MEDIUM queries
    print_section("MEDIUM Queries (Conceptual - Balanced Routing)")
    print("These should use 1-round debate with selective components\n")

    medium_queries = [
        "How does quantum mechanics relate to reality?",
        "What are the implications of artificial intelligence?",
        "Compare classical and quantum computing",
        "How do neural networks learn?",
    ]

    for query in medium_queries:
        demo_query(ctrl, classifier, query)

    # COMPLEX queries
    print_section("COMPLEX Queries (Philosophical - Deep Routing)")
    print("These should use 3-round debate with all Phase 1-6 components\n")

    complex_queries = [
        "Can machines be truly conscious?",
        "What is the nature of free will?",
        "Is artificial intelligence the future of humanity?",
        "How should AI be ethically governed?",
    ]

    for query in complex_queries:
        demo_query(ctrl, classifier, query)

    # Statistics
    print_section("Routing Statistics")
    stats = ctrl.get_routing_statistics()
    print(f"Total queries routed: {stats['total_queries_routed']}")
    print(f"Component activation counts: {stats['component_activation_counts']}")
    print(f"Efficiency gain: {stats['efficiency_gain']}")

    # Summary
    print_section("Next Steps")
    print("1. Launch full web server: run codette_web.bat")
    print("2. Test Phase 7 with actual ForgeEngine in web UI")
    print("3. Measure real latency improvements (target: 50-70% on SIMPLE queries)")
    print("4. Verify correctness preservation on MEDIUM/COMPLEX queries")
    print()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
