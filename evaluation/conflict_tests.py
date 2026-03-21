"""
Conflict Detection Test Suite

10-15 conflict-triggering prompts designed to elicit specific agent disagreements.
Tests forge_with_debate() with conflict detection enabled and measures outcomes.

Author: Claude Code
"""

import csv
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from statistics import mean

# Conflict-triggering test prompts
CONFLICT_PROMPTS = [
    {
        "query": "Should we optimize an algorithm to run 10x faster if it reduces interpretability by 80%?",
        "expected_conflict": "ethics_vs_efficiency",
        "agents_likely_to_conflict": ["ethics", "systems_architecture"],
        "description": "Efficiency vs transparency tradeoff",
    },
    {
        "query": "Is a probabilistic solution more insightful than a deterministic one for explaining human decision-making?",
        "expected_conflict": "quantum_vs_newton",
        "agents_likely_to_conflict": ["quantum", "newton"],
        "description": "Probabilistic vs mechanistic explanation",
    },
    {
        "query": "In designing an AI system, should we prioritize consciousness theory or engineering reliability?",
        "expected_conflict": "philosophy_vs_systems",
        "agents_likely_to_conflict": ["philosophy", "systems_architecture"],
        "description": "Theoretical depth vs practical robustness",
    },
    {
        "query": "Is breaking logical rules ever justified in creative problem-solving?",
        "expected_conflict": "davinci_vs_newton",
        "agents_likely_to_conflict": ["davinci", "newton"],
        "description": "Creativity vs logical consistency",
    },
    {
        "query": "Should medical diagnosis weigh patient emotional state equally with biomarkers?",
        "expected_conflict": "empathy_vs_newton",
        "agents_likely_to_conflict": ["empathy", "newton"],
        "description": "Holistic vs reductionist medicine",
    },
    {
        "query": "Is uncertainty in a system a bug to eliminate or a feature to leverage?",
        "expected_conflict": "quantum_vs_systems",
        "agents_likely_to_conflict": ["quantum", "systems_architecture"],
        "description": "Embracing vs reducing uncertainty",
    },
    {
        "query": "Should AI systems be trained to always maximize efficiency or to leave space for unexpected behaviors?",
        "expected_conflict": "newton_vs_davinci",
        "agents_likely_to_conflict": ["newton", "davinci"],
        "description": "Optimization vs emergence",
    },
    {
        "query": "Is empathy a strength or a weakness in decision-making systems?",
        "expected_conflict": "empathy_vs_ethics",
        "agents_likely_to_conflict": ["empathy", "ethics"],
        "description": "Emotional connection vs principled rules",
    },
    {
        "query": "Should we prefer explanations that preserve mathematical elegance or human understanding?",
        "expected_conflict": "philosophy_vs_empathy",
        "agents_likely_to_conflict": ["philosophy", "empathy"],
        "description": "Aesthetic vs communicative clarity",
    },
    {
        "query": "Can a system be simultaneously more creative and more reliable?",
        "expected_conflict": "davinci_vs_systems",
        "agents_likely_to_conflict": ["davinci", "systems_architecture"],
        "description": "Innovation vs stability",
    },
    {
        "query": "Should resource allocation prioritize current needs or future possibilities?",
        "expected_conflict": "newton_vs_philosophy",
        "agents_likely_to_conflict": ["newton", "philosophy"],
        "description": "Practical vs speculative",
    },
    {
        "query": "Is it more important for an explanation to be complete or to be useful?",
        "expected_conflict": "philosophy_vs_davinci",
        "agents_likely_to_conflict": ["philosophy", "davinci"],
        "description": "Comprehensiveness vs pragmatism",
    },
]


@dataclass
class ConflictTestResult:
    """Result from running one test prompt."""
    query: str
    expected_conflict: str
    round_0_conflict_count: int
    round_1_conflict_count: int
    avg_conflict_strength_r0: float
    avg_conflict_strength_r1: float
    conflict_resolution_rate: float
    ensemble_coherence: float
    debate_tension_decay: float
    detected_conflicts: List[Dict]
    success: bool  # Did test complete without error?


class ConflictTestRunner:
    """Runner for conflict detection tests."""

    def __init__(self, forge_engine):
        """
        Initialize test runner.

        Args:
            forge_engine: ForgeEngine instance with conflict detection enabled
        """
        self.forge = forge_engine

    def run_test(self, prompt_dict: Dict) -> ConflictTestResult:
        """
        Run a single test prompt through forge_with_debate.

        Args:
            prompt_dict: Dict with query, expected_conflict, agents_likely_to_conflict

        Returns:
            ConflictTestResult with metrics
        """
        query = prompt_dict["query"]
        expected_conflict = prompt_dict["expected_conflict"]

        try:
            result = self.forge.forge_with_debate(query, debate_rounds=1)

            metadata = result.get("metadata", {})
            debates = metadata.get("debate_log", [])

            # Extract conflict metrics
            round_0_conflicts = 0
            round_1_conflicts = 0
            avg_strength_r0 = 0.0
            avg_strength_r1 = 0.0
            resolution_rate = 0.0

            # Parse debate log
            for debate_entry in debates:
                if debate_entry.get("type") == "initial_analysis":
                    round_0_conflicts = debate_entry.get("conflicts_detected", 0)
                    summary = debate_entry.get("conflict_strength_summary", {})
                    if round_0_conflicts > 0:
                        avg_strength_r0 = summary.get("avg_conflict_strength", 0.0)

                elif debate_entry.get("type") == "debate":
                    round_1_conflicts = debate_entry.get("conflicts_detected_after", 0)
                    res_metrics = debate_entry.get("resolution_metrics", {})
                    if res_metrics:
                        resolution_rate = res_metrics.get("resolution_rate", 0.0)
                        summary = res_metrics.get("conflict_strength_summary", {})
                        if round_1_conflicts > 0:
                            avg_strength_r1 = summary.get("avg_conflict_strength", 0.0)

            ensemble_coherence = metadata.get("ensemble_coherence", 0.0)
            tension_decay_info = metadata.get("tension_decay", {})
            tension_decay = tension_decay_info.get("decay_rate", 0.0) if isinstance(tension_decay_info, dict) else 0.0

            detected = metadata.get("conflicts_detected", [])

            test_result = ConflictTestResult(
                query=query,
                expected_conflict=expected_conflict,
                round_0_conflict_count=round_0_conflicts,
                round_1_conflict_count=round_1_conflicts,
                avg_conflict_strength_r0=avg_strength_r0,
                avg_conflict_strength_r1=avg_strength_r1,
                conflict_resolution_rate=resolution_rate,
                ensemble_coherence=ensemble_coherence,
                debate_tension_decay=tension_decay,
                detected_conflicts=detected,
                success=True,
            )

            return test_result

        except Exception as e:
            # Return failed test result
            print(f"ERROR in test '{query[:50]}...': {e}")
            return ConflictTestResult(
                query=query,
                expected_conflict=expected_conflict,
                round_0_conflict_count=0,
                round_1_conflict_count=0,
                avg_conflict_strength_r0=0.0,
                avg_conflict_strength_r1=0.0,
                conflict_resolution_rate=0.0,
                ensemble_coherence=0.0,
                debate_tension_decay=0.0,
                detected_conflicts=[],
                success=False,
            )

    def run_all_tests(self, output_csv: str = "conflict_test_results.csv") -> List[ConflictTestResult]:
        """
        Run all test prompts.

        Args:
            output_csv: CSV file to export results

        Returns:
            List of ConflictTestResult
        """
        results = []

        print(f"\n{'='*80}")
        print("PHASE 1: CONFLICT DETECTION TEST SUITE")
        print(f"{'='*80}\n")

        for idx, prompt_dict in enumerate(CONFLICT_PROMPTS, 1):
            print(f"\n[Test {idx}/{len(CONFLICT_PROMPTS)}] {prompt_dict['description']}")
            print(f"  Query: {prompt_dict['query'][:80]}...")

            result = self.run_test(prompt_dict)
            results.append(result)

            if result.success:
                print(f"  ✓ Success")
                print(f"    - Conflicts detected (R0): {result.round_0_conflict_count}")
                print(f"    - Conflicts detected (R1): {result.round_1_conflict_count}")
                print(f"    - Resolution rate: {result.conflict_resolution_rate:.2%}")
                print(f"    - Ensemble coherence: {result.ensemble_coherence:.3f}")
                print(f"    - Tension decay: {result.debate_tension_decay:.3f}")
            else:
                print(f"  ✗ FAILED")

        # Export to CSV
        self._export_csv(results, output_csv)

        # Print summary
        print(f"\n{'='*80}")
        self._print_summary(results)
        print(f"{'='*80}\n")

        return results

    def _export_csv(self, results: List[ConflictTestResult], filename: str):
        """Export results to CSV."""
        try:
            with open(filename, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "query",
                    "expected_conflict",
                    "round_0_conflicts",
                    "round_1_conflicts",
                    "avg_strength_r0",
                    "avg_strength_r1",
                    "resolution_rate",
                    "ensemble_coherence",
                    "tension_decay",
                    "success",
                ])
                for r in results:
                    writer.writerow([
                        r.query[:100],
                        r.expected_conflict,
                        r.round_0_conflict_count,
                        r.round_1_conflict_count,
                        f"{r.avg_conflict_strength_r0:.3f}",
                        f"{r.avg_conflict_strength_r1:.3f}",
                        f"{r.conflict_resolution_rate:.3f}",
                        f"{r.ensemble_coherence:.3f}",
                        f"{r.debate_tension_decay:.3f}",
                        r.success,
                    ])
            print(f"\nResults exported to: {filename}")
        except Exception as e:
            print(f"Error exporting CSV: {e}")

    def _print_summary(self, results: List[ConflictTestResult]):
        """Print test summary statistics."""
        successful = [r for r in results if r.success]
        if not successful:
            print("\nNo tests completed successfully!")
            return

        print("\nTEST SUMMARY")
        print(f"  Total tests: {len(results)}")
        print(f"  Successful: {len(successful)}")
        print(f"  Failed: {len(results) - len(successful)}")

        print(f"\nCONFLICT DETECTION METRICS")
        print(f"  Avg conflicts (R0): {mean(r.round_0_conflict_count for r in successful):.1f}")
        print(f"  Avg conflicts (R1): {mean(r.round_1_conflict_count for r in successful):.1f}")
        print(f"  Avg conflict strength (R0): {mean(r.avg_conflict_strength_r0 for r in successful if r.avg_conflict_strength_r0 > 0):.3f}")
        print(f"  Avg resolution rate: {mean(r.conflict_resolution_rate for r in successful):.1%}")

        print(f"\nEPISTEMIC METRICS")
        print(f"  Avg ensemble coherence: {mean(r.ensemble_coherence for r in successful):.3f}")
        print(f"  Avg tension decay: {mean(r.debate_tension_decay for r in successful):.3f}")

        print(f"\nSUCCESS CRITERIA")
        conflicts_detected = sum(1 for r in successful if r.round_0_conflict_count > 0)
        resolution_positive = sum(1 for r in successful if r.conflict_resolution_rate > 0)
        coherence_good = sum(1 for r in successful if r.ensemble_coherence > 0.5)

        print(f"  ✓ Conflicts detected: {conflicts_detected}/{len(successful)}")
        print(f"  ✓ Resolution attempts: {resolution_positive}/{len(successful)}")
        print(f"  ✓ Coherence > 0.5: {coherence_good}/{len(successful)}")


# ============================================================================
# QUICKSTART
# ============================================================================

if __name__ == "__main__":
    # This is a quickstart. In actual usage:
    # from reasoning_forge.forge_engine import ForgeEngine
    # forge = ForgeEngine()
    # runner = ConflictTestRunner(forge)
    # results = runner.run_all_tests()

    import sys

    print("To run tests:")
    print("  1. Ensure ForgeEngine is initialized with conflict detection")
    print("  2. Create runner: runner = ConflictTestRunner(forge)")
    print("  3. Run: results = runner.run_all_tests()")
    print("\nExample:")
    print("  from reasoning_forge.forge_engine import ForgeEngine")
    print("  from evaluation.conflict_tests import ConflictTestRunner")
    print("  forge = ForgeEngine()")
    print("  runner = ConflictTestRunner(forge)")
    print("  results = runner.run_all_tests('phase1_results.csv')")
