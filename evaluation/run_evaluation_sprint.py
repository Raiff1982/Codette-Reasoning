"""
Evaluation Sprint Runner

Executes the evaluation harness against all 4 conditions:
1. Baseline (plain Llama)
2. Phase 1-5 (debate without semantic tension)
3. Phase 6 Full (with semantic tension, specialization, preflight)
4. Phase 6 -PreFlight (without preflight prediction)

Usage:
    python run_evaluation_sprint.py --questions 25 --output results.json
"""

import sys
import argparse
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'reasoning_forge'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'inference'))

from test_suite_evaluation import (
    EvaluationHarness,
    EvaluationAnalyzer,
    EVALUATION_TEST_SUITE,
)


def run_evaluation_sprint(
    num_questions: int = 10,
    output_json: str = "evaluation_results.json",
    output_report: str = "evaluation_report.txt",
):
    """
    Run the complete evaluation sprint.

    Args:
        num_questions: How many test questions to run (1-25)
        output_json: Where to save JSON results
        output_report: Where to save text report
    """

    print("\n" + "=" * 80)
    print("CODETTE PHASE 6 EVALUATION SPRINT")
    print("=" * 80)
    print(f"Test Date: {datetime.now().isoformat()}")
    print(f"Questions to Run: {min(num_questions, len(EVALUATION_TEST_SUITE))}/25")
    print(f"Output: {output_json}, {output_report}")
    print("=" * 80 + "\n")

    # Load ForgeEngine with Phase 6
    print("[1/4] Loading ForgeEngine with Phase 6...")
    try:
        from reasoning_forge.forge_engine import ForgeEngine

        forge = ForgeEngine(living_memory=None, enable_memory_weighting=False)

        print("  OK: ForgeEngine loaded")
        print(f"  - semantic_tension_engine: {'READY' if forge.semantic_tension_engine else 'MISSING'}")
        print(f"  - specialization tracker: {'READY' if forge.specialization else 'MISSING'}")
        print(f"  - preflight_predictor: {'READY' if forge.preflight_predictor else 'MISSING'}")

        # Check GPU status from orchestrator
        if forge.newton.orchestrator:
            print(f"  - GPU acceleration: ✓ ENABLED ({forge.newton.orchestrator.n_gpu_layers} layers)")

    except Exception as e:
        print(f"  ERROR: {e}")
        return False

    # Create evaluation harness
    print("\n[2/4] Creating evaluation harness...")
    try:
        harness = EvaluationHarness(forge)
        print("  OK: Harness created")
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

    # Run evaluation suite
    print(f"\n[3/4] Running evaluation on {min(num_questions, len(EVALUATION_TEST_SUITE))} questions...")
    print("  This will take several minutes...\n")

    try:
        test_questions = EVALUATION_TEST_SUITE[:num_questions]
        results = harness.run_evaluation_suite(test_questions)
        print(f"\n  OK: Evaluation complete")
        print(f"    - Baseline: {len(results['baseline_llama'])} results")
        print(f"    - Phase 1-5: {len(results['phase_1_5'])} results")
        print(f"    - Phase 6 Full: {len(results['phase_6_full'])} results")
        print(f"    - Phase 6 -PreFlight: {len(results['phase_6_no_preflight'])} results")
    except Exception as e:
        print(f"  ERROR during evaluation: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Analyze results
    print(f"\n[4/4] Analyzing results...")
    try:
        analyzer = EvaluationAnalyzer(results)
        report = analyzer.report()

        # Save JSON results
        harness.export_results(output_json)

        # Save text report (with UTF-8 encoding for Unicode characters like Γ)
        with open(output_report, 'w', encoding='utf-8') as f:
            f.write(report)

        print("  OK: Analysis complete")
        print(f"    - JSON saved: {output_json}")
        print(f"    - Report saved: {output_report}")

        # Print summary to console (skip full report due to Unicode encoding)
        try:
            # Try to print the report
            print("\n" + report)
        except UnicodeEncodeError:
            # Windows terminal encoding issue—just note that report was saved
            print("    - Full report saved to file (Unicode summary unavailable in terminal)")

        return True

    except Exception as e:
        print(f"  ERROR during analysis: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run Codette Phase 6 evaluation sprint"
    )
    parser.add_argument(
        "--questions",
        type=int,
        default=5,
        help="Number of test questions to run (1-25, default 5)",
    )
    parser.add_argument(
        "--output-json",
        default="evaluation_results.json",
        help="Output JSON file for results",
    )
    parser.add_argument(
        "--output-report",
        default="evaluation_report.txt",
        help="Output text file for report",
    )

    args = parser.parse_args()

    # Validate num_questions
    if args.questions < 1 or args.questions > 25:
        print("ERROR: --questions must be between 1 and 25")
        return 1

    # Run sprint
    success = run_evaluation_sprint(
        num_questions=args.questions,
        output_json=args.output_json,
        output_report=args.output_report,
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
