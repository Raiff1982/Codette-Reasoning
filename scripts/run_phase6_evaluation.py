#!/usr/bin/env python3
"""
Phase 6 Focus Evaluation Runner

Compares 4 conditions:
1. Baseline (Llama only, no routing)
2. Phase 1-5 (debate, no semantic tension, no specialization)
3. Phase 6 Full (all Phase 6 components: semantic tension, specialization, preflight)
4. Phase 6 -PreFlight (Phase 6 minus preflight prediction)

This isolates the value of individual Phase 6 components.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import time

# Add repo to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.forge_engine import ForgeEngine
from evaluation.test_suite_evaluation import EvaluationHarness, EvaluationAnalyzer, EVALUATION_TEST_SUITE


def main():
    print("\n" + "=" * 80)
    print("PHASE 6 EVALUATION: Component Impact Analysis")
    print("=" * 80 + "\n")

    # Load Forge Engine
    print("[1/4] Initializing ForgeEngine with Phase 6 components...")
    try:
        forge = ForgeEngine()
        print("✓ ForgeEngine loaded")
        print(f"  - Analysis agents: {len(forge.analysis_agents)}")
        print(f"  - Semantic tension engine: {forge.semantic_tension_engine is not None}")
        print(f"  - Specialization tracker: {forge.specialization is not None}")
        print(f"  - Pre-flight predictor: {forge.preflight_predictor is not None}")
    except Exception as e:
        print(f"✗ Failed to load ForgeEngine: {e}")
        return 1

    # Create evaluation harness
    print("\n[2/4] Creating evaluation harness...")
    try:
        harness = EvaluationHarness(forge)
        print("✓ Evaluation harness ready")
    except Exception as e:
        print(f"✗ Failed to create harness: {e}")
        return 1

    # Select subset of questions for focused evaluation (top question from each category + hard ones)
    # This reduces test time while still covering all domains
    focused_questions = [
        EVALUATION_TEST_SUITE[0],   # Speed of light (easy physics)
        EVALUATION_TEST_SUITE[2],   # Entropy & time (hard physics)
        EVALUATION_TEST_SUITE[3],   # Lying to save life (ethics)
        EVALUATION_TEST_SUITE[5],   # AI explanations (hard ethics)
        EVALUATION_TEST_SUITE[7],   # Can machines be conscious? (hard consciousness)
        EVALUATION_TEST_SUITE[9],   # What makes something creative (creativity)
        EVALUATION_TEST_SUITE[11],  # Can AI be truly creative (hard creativity)
        EVALUATION_TEST_SUITE[12],  # What is emergence (systems)
        EVALUATION_TEST_SUITE[14],  # Free will (hard interdisciplinary)
    ]

    print(f"  - Running {len(focused_questions)} focused questions")
    print("  - Questions span: physics (easy, hard), ethics (medium, hard),")
    print("    consciousness, creativity, systems, interdisciplinary\n")

    # Run evaluation
    print("[3/4] Running evaluation (this may take 5-10 minutes)...\n")
    start_time = time.time()

    try:
        results = harness.run_evaluation_suite(focused_questions)
        elapsed = time.time() - start_time

        print(f"\n✓ Evaluation complete ({elapsed:.1f}s)")
        print(f"  - Phase 1-5 results: {len(results['phase_1_5'])} questions")
        print(f"  - Phase 6 Full results: {len(results['phase_6_full'])} questions")
        print(f"  - Phase 6 -PreFlight results: {len(results['phase_6_no_preflight'])} questions")
    except Exception as e:
        print(f"\n✗ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Analyze results
    print("\n[4/4] Analyzing results...\n")
    try:
        analyzer = EvaluationAnalyzer(results)
        report = analyzer.report()
        print(report)

        # Export detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"/j/codette-training-lab/evaluation_results_{timestamp}.json"
        harness.export_results(output_file)
        print(f"✓ Detailed results exported: {output_file}")

    except Exception as e:
        print(f"✗ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
