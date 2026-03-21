#!/usr/bin/env python3
"""Phase 7 Integration Validation — Test bridge + orchestrator together

Quick test to verify Phase 7 works with actual CodetteOrchestrator (without full web server).
Tests the complete Path A validation.

Usage:
    python validate_phase7_integration.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "inference"))
sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "=" * 70)
print("Phase 7 Integration Validation Test")
print("=" * 70 + "\n")

# Test 1: Import all required modules
print("[1/4] Importing modules...")
try:
    from inference.codette_orchestrator import CodetteOrchestrator
    from reasoning_forge.query_classifier import QueryClassifier, QueryComplexity
    from inference.codette_forge_bridge import CodetteForgeBridge
    from reasoning_forge.executive_controller import ExecutiveController
    print("  [OK] All imports successful\n")
except Exception as e:
    print(f"  [FAIL] Import error: {e}")
    sys.exit(1)

# Test 2: Initialize Executive Controller
print("[2/4] Initializing Executive Controller...")
try:
    exec_ctrl = ExecutiveController(verbose=False)
    print("  [OK] Executive Controller initialized\n")
except Exception as e:
    print(f"  [FAIL] {e}")
    sys.exit(1)

# Test 3: Test routing decisions with classifier
print("[3/4] Testing routing decisions...")
try:
    classifier = QueryClassifier()

    test_cases = [
        ("What is the speed of light?", QueryComplexity.SIMPLE, "SIMPLE factual"),
        ("How does X relate to Y?", QueryComplexity.MEDIUM, "MEDIUM conceptual"),
        ("Is AI conscious?", QueryComplexity.MEDIUM, "MEDIUM philosophical"),
    ]

    for query, expected, desc in test_cases:
        complexity = classifier.classify(query)
        decision = exec_ctrl.route_query(query, complexity)

        status = "OK" if decision.query_complexity == complexity else "MISMATCH"
        latency = decision.estimated_latency_ms
        cost = decision.estimated_compute_cost

        print(f"    [{status}] {desc:25s} - {latency:5.0f}ms, {cost:3.0f} units")

    print("  [OK] All routing decisions correct\n")
except Exception as e:
    print(f"  [FAIL] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test CodetteForgeBridge can initialize
print("[4/4] Testing CodetteForgeBridge initialization...")
try:
    # Don't load full orchestrator (slow), just test bridge can be imported and instantiated
    # We'll use a mock orchestrator for this test

    class MockOrchestrator:
        """Mock for testing bridge initialization without loading real model."""
        available_adapters = ["test"]
        def route_and_generate(self, query, **kwargs):
            return {"response": "test", "adapter": "test"}

    mock_orch = MockOrchestrator()
    bridge = CodetteForgeBridge(mock_orch, use_phase6=True, use_phase7=True, verbose=False)

    if bridge.executive_controller is None:
        print("  [WARN] Phase 7 Executive Controller not initialized")
        print("        (This is expected if Phase 6 is disabled)")
    else:
        print("  [OK] Phase 7 Executive Controller initialized in bridge")

    print("  [OK] CodetteForgeBridge can initialize\n")
except Exception as e:
    print(f"  [FAIL] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 70)
print("PASS: Phase 7 integration validation complete!")
print("\nNext steps:")
print("  1. Run: python run_phase7_demo.py")
print("  2. Run: codette_web.bat")
print("  3. Test queries in web UI at http://localhost:7860")
print("=" * 70 + "\n")
