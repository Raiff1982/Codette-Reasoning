#!/usr/bin/env python3
"""Verbose Evaluation Runner — See Real-Time Agent Thinking

Shows exactly what agents are thinking as they reason through each question.

Usage:
    python evaluation/run_evaluation_verbose.py --questions 1
"""

import sys
import os
from pathlib import Path

# Enable verbose mode globally
os.environ['CODETTE_VERBOSE'] = '1'

# Setup logging for real-time visibility
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)-20s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

sys.path.insert(0, str(Path(__file__).parent.parent / 'reasoning_forge'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'inference'))

from evaluation.test_suite_evaluation import (
    EvaluationHarness,
    EVALUATION_TEST_SUITE,
)


def run_verbose_evaluation(num_questions: int = 1):
    """Run evaluation with full real-time agent visibility."""

    print("\n" + "=" * 100)
    print("CODETTE VERBOSE EVALUATION — REAL-TIME AGENT THINKING")
    print("=" * 100)
    print(f"Questions: {num_questions}")
    print(f"Verbose mode: ON (see all agent reasoning)\n")

    # Load ForgeEngine
    print("[1/3] Loading ForgeEngine with real LLM agents...")
    try:
        from reasoning_forge.forge_engine import ForgeEngine

        forge = ForgeEngine(living_memory=None, enable_memory_weighting=False)
        print("  ✓ ForgeEngine loaded")

        if forge.newton.orchestrator:
            print(f"  ✓ Orchestrator ready: {forge.newton.orchestrator.available_adapters}")
            print(f"  ✓ GPU acceleration: {forge.newton.orchestrator.n_gpu_layers} layers")

    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Create harness
    print("\n[2/3] Creating evaluation harness...")
    try:
        harness = EvaluationHarness(forge)
        print("  ✓ Harness ready\n")
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return False

    # Run ONE question in detail
    print("[3/3] Running question with full real-time reasoning output...\n")
    print("=" * 100)

    try:
        test_questions = EVALUATION_TEST_SUITE[:num_questions]

        for i, question in enumerate(test_questions):
            print(f"\n{'='*100}")
            print(f"QUESTION {i+1}: {question.query}")
            print(f"Category: {question.category} | Difficulty: {question.difficulty}")
            print(f"Expected perspectives: {', '.join(question.expected_perspectives)}")
            print(f"{'='*100}\n")

            # This will trigger verbose logging for agent analysis
            print("[RUNNING DEBATE]\n")

            result = forge.forge_with_debate(question.query)

            # Extract synthesis
            synthesis = ""
            if "messages" in result and len(result["messages"]) >= 3:
                synthesis = result["messages"][2].get("content", "")

            print(f"\n{'='*100}")
            print(f"[FINAL SYNTHESIS] ({len(synthesis)} characters)\n")
            print(synthesis)
            print(f"{'='*100}\n")

            # Show metadata
            metadata = result.get("metadata", {})
            print(f"[METADATA]")
            print(f"  Conflicts detected: {len(metadata.get('conflicts', []))}")
            print(f"  Gamma (coherence): {metadata.get('gamma', 0.5):.3f}")
            print(f"  Debate rounds: {metadata.get('debate_round', 0)}")

    except Exception as e:
        print(f"\n✗ ERROR during evaluation: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Verbose evaluation with real-time agent thinking")
    parser.add_argument("--questions", type=int, default=1, help="Number of questions to run (default: 1)")
    args = parser.parse_args()

    success = run_verbose_evaluation(args.questions)
    sys.exit(0 if success else 1)
