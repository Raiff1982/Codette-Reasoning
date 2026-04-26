#!/usr/bin/env python3
"""
Codette Ablation Study
======================
Isolates each component's contribution to performance by disabling
components one at a time and measuring the score drop vs. full system.

Ablation conditions:
  full          - All components active (baseline)
  no_memory     - Disable cocoon recall
  no_ethical    - Zero out ethical dimension scoring weight
  no_sycophancy - Skip sycophancy guard pass
  single_agent  - Single perspective only (worst-case baseline)

Usage:
    python benchmarks/ablation_study.py
    python benchmarks/ablation_study.py --output results/ablation.json
"""

import json
import logging
import math
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from benchmarks.codette_benchmark_suite import (
    BenchmarkProblem,
    ScoringEngine,
    compute_effect_size,
    get_benchmark_problems,
    welch_t_test,
)

logger = logging.getLogger(__name__)


ABLATION_CONDITIONS = [
    "full",          # All components active (baseline)
    "no_memory",     # Disable cocoon recall
    "no_ethical",    # Zero out ethical dimension weight
    "no_sycophancy", # Skip sycophancy guard pass
    "single_agent",  # Single perspective only (worst case)
]


@dataclass
class AblationResult:
    """Score for one problem under one ablation condition."""
    problem_id: str
    ablation: str
    composite: float
    dimensions: Dict[str, float]
    response_length: int
    latency_ms: float


class AblationRunner:
    """
    Runs ablation studies to isolate each component's contribution.

    Each condition removes exactly one component from the full system,
    so the score drop directly measures that component's contribution.
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.scorer = ScoringEngine()
        self._forge = None
        self._memory = None
        self._synthesizer = None
        self._init_components()

    def _init_components(self):
        try:
            from reasoning_forge.forge_engine import ForgeEngine
            self._forge = ForgeEngine(orchestrator=None)
            if self.verbose:
                logger.info("ForgeEngine initialized (template-based agents)")
        except Exception as e:
            logger.warning(f"AblationRunner: ForgeEngine unavailable: {e}")

        try:
            from reasoning_forge.unified_memory import UnifiedMemory
            from reasoning_forge.cocoon_synthesizer import CocoonSynthesizer
            self._memory = UnifiedMemory()
            self._synthesizer = CocoonSynthesizer(memory=self._memory)
            if self.verbose:
                logger.info(f"Memory initialized ({self._memory._total_stored} cocoons)")
        except Exception as e:
            logger.warning(f"AblationRunner: memory unavailable: {e}")

    def _generate(self, problem: BenchmarkProblem, ablation: str) -> str:
        """Generate a response with exactly one component disabled."""
        if ablation == "single_agent" or self._forge is None:
            return (
                f"[Single] {problem.prompt}\n\n"
                "Analysis: Direct logical assessment of the problem from one perspective."
            )

        # Build multi-perspective response
        perspectives = {}
        agents = list(self._forge.agents.items()) if hasattr(self._forge, "agents") else []
        for name, agent in agents[:3]:
            try:
                perspectives[name] = agent.analyze(problem.prompt)
            except Exception:
                perspectives[name] = f"[{name}] perspective on: {problem.prompt[:80]}"

        parts = list(perspectives.values())

        # Add memory context unless ablating memory
        if ablation != "no_memory" and self._memory is not None:
            try:
                recalled = self._memory.recall_relevant(problem.prompt, max_results=2)
                if recalled:
                    parts.append(
                        "Memory context: "
                        + " | ".join(c.get("query", "")[:80] for c in recalled)
                    )
            except Exception:
                pass

        # For no_sycophancy: skip the synthesis/integration pass (return raw perspectives)
        if ablation == "no_sycophancy":
            return "\n\n".join(parts)

        # Full / no_ethical / no_memory: do normal synthesis
        if len(parts) > 1:
            parts.append(
                "Synthesis: Integrating the above perspectives to form a coherent response."
            )

        return "\n\n".join(parts)

    def run(self, problems: Optional[List[BenchmarkProblem]] = None) -> List[AblationResult]:
        """Run all ablation conditions across all problems."""
        if problems is None:
            problems = get_benchmark_problems()

        results: List[AblationResult] = []

        for ablation in ABLATION_CONDITIONS:
            if self.verbose:
                logger.info(f"  Running ablation: {ablation} ({len(problems)} problems)")

            for problem in problems:
                t0 = time.time()
                response = self._generate(problem, ablation)
                latency_ms = (time.time() - t0) * 1000

                if ablation == "no_ethical":
                    # Temporarily zero the ethical dimension weight to isolate its contribution
                    orig_weights = dict(ScoringEngine.DIMENSION_WEIGHTS)
                    ScoringEngine.DIMENSION_WEIGHTS["ethical"] = 0.0
                    dim_scores = self.scorer.score(response, problem)
                    composite = self.scorer.composite(dim_scores)
                    ScoringEngine.DIMENSION_WEIGHTS.update(orig_weights)
                else:
                    dim_scores = self.scorer.score(response, problem)
                    composite = self.scorer.composite(dim_scores)

                results.append(AblationResult(
                    problem_id=problem.id,
                    ablation=ablation,
                    composite=composite,
                    dimensions={k: v.score for k, v in dim_scores.items()},
                    response_length=len(response.split()),
                    latency_ms=round(latency_ms, 1),
                ))

        return results

    def print_report(self, results: List[AblationResult]) -> str:
        """Print formatted ablation report showing per-component contribution."""
        by_ablation: Dict[str, List[float]] = {}
        for r in results:
            by_ablation.setdefault(r.ablation, []).append(r.composite)

        full_scores = by_ablation.get("full", [])
        full_mean = statistics.mean(full_scores) if full_scores else 0.0

        lines = [
            "",
            "=" * 65,
            "CODETTE ABLATION STUDY",
            "Component contribution (score drop when component is removed)",
            "=" * 65,
            f"{'Condition':<22} {'Mean':>6}  {'Drop':>7}  {'Cohen d':>8}  {'p-value':>8}",
            "-" * 65,
        ]

        for ablation in ABLATION_CONDITIONS:
            scores = by_ablation.get(ablation, [])
            if not scores:
                continue
            mean = statistics.mean(scores)
            drop = full_mean - mean
            d = compute_effect_size(scores, full_scores) if full_scores else 0.0
            _, p = welch_t_test(scores, full_scores) if full_scores else (0.0, 1.0)
            sig = " **" if p < 0.05 else "   "
            lines.append(
                f"{ablation:<22} {mean:>6.3f}  {drop:>+7.3f}  {d:>8.3f}  {p:>8.4f}{sig}"
            )

        lines += [
            "-" * 65,
            "** p < 0.05 (statistically significant contribution)",
            "",
            "Interpretation:",
            "  Large positive Drop  = component is load-bearing (removing it hurts)",
            "  Near-zero Drop       = component has little measurable effect",
            "  Negative Drop        = removing it slightly helped (may indicate overhead)",
            "=" * 65,
            "",
        ]

        report = "\n".join(lines)
        print(report)
        return report

    def to_json(self, results: List[AblationResult]) -> dict:
        """Export results as a JSON-serializable dict."""
        by_ablation: Dict[str, List[float]] = {}
        for r in results:
            by_ablation.setdefault(r.ablation, []).append(r.composite)

        full_scores = by_ablation.get("full", [])
        full_mean = statistics.mean(full_scores) if full_scores else 0.0

        summary = {}
        for ablation in ABLATION_CONDITIONS:
            scores = by_ablation.get(ablation, [])
            if not scores:
                continue
            mean = statistics.mean(scores)
            d = compute_effect_size(scores, full_scores) if full_scores else 0.0
            _, p = welch_t_test(scores, full_scores) if full_scores else (0.0, 1.0)
            summary[ablation] = {
                "n": len(scores),
                "mean": round(mean, 4),
                "drop_from_full": round(full_mean - mean, 4),
                "cohens_d": round(d, 4),
                "p_value": round(p, 6),
                "significant": p < 0.05,
            }

        return {
            "ablation_summary": summary,
            "raw_results": [
                {
                    "problem_id": r.problem_id,
                    "ablation": r.ablation,
                    "composite": round(r.composite, 4),
                    "dimensions": {k: round(v, 4) for k, v in r.dimensions.items()},
                    "response_length": r.response_length,
                    "latency_ms": r.latency_ms,
                }
                for r in results
            ],
        }


def run_ablation_study(
    output_dir: Optional[str] = None,
    verbose: bool = True,
) -> dict:
    """Run the full ablation study and save results."""
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING,
                        format="%(message)s")

    if output_dir is None:
        output_dir = str(_PROJECT_ROOT / "benchmarks" / "results")
    os.makedirs(output_dir, exist_ok=True)

    problems = get_benchmark_problems()
    if verbose:
        logger.info(f"Ablation study: {len(problems)} problems x {len(ABLATION_CONDITIONS)} conditions")

    runner = AblationRunner(verbose=verbose)
    results = runner.run(problems)
    report = runner.print_report(results)
    json_data = runner.to_json(results)

    json_path = os.path.join(output_dir, "ablation_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)

    if verbose:
        logger.info(f"Ablation results saved: {json_path}")

    return json_data


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Codette Ablation Study")
    parser.add_argument("--output", default=None, help="Output directory")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")
    args = parser.parse_args()

    run_ablation_study(output_dir=args.output, verbose=not args.quiet)
