"""
Benchmark Runner - loads test prompts, runs/loads responses, scores them,
and produces detailed evaluation reports.

Supports:
- Loading prompts from JSON files in evaluation/prompts/
- Pre-generated response files (JSON mapping prompt -> response)
- Scoring via ReasoningMetrics
- Per-category and overall reports
- Baseline vs trained model comparison
- CLI interface
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Allow running from project root or from evaluation/
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from evaluation.reasoning_metrics import ReasoningMetrics


# ---------------------------------------------------------------------------
# Benchmark Runner
# ---------------------------------------------------------------------------

class BenchmarkRunner:
    """Load prompts, score responses, produce reports."""

    def __init__(
        self,
        prompts_dir: Optional[str] = None,
        metrics: Optional[ReasoningMetrics] = None,
    ):
        self.prompts_dir = Path(prompts_dir) if prompts_dir else _THIS_DIR / "prompts"
        self.metrics = metrics or ReasoningMetrics()
        self._prompts: Dict[str, List[str]] = {}
        self._counterexamples: List[Dict[str, str]] = []

    # -- loading -----------------------------------------------------------

    def load_prompts(self, filename: str = "reasoning_tests.json") -> Dict[str, List[str]]:
        """Load categorised prompts from a JSON file.

        Expected format: {"category": ["prompt1", "prompt2", ...], ...}
        """
        path = self.prompts_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._prompts = data
        return data

    def load_counterexamples(self, filename: str = "counterexample_tests.json") -> List[Dict[str, str]]:
        """Load counterexample test prompts."""
        path = self.prompts_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Counterexample file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._counterexamples = data
        return data

    def load_responses(self, filepath: str) -> Dict[str, str]:
        """Load pre-generated responses from a JSON file.

        Expected format: {"prompt_text": "response_text", ...}
        """
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    # -- scoring -----------------------------------------------------------

    def score_responses(
        self,
        responses: Dict[str, str],
    ) -> Dict[str, Any]:
        """Score all responses and organise results by category.

        Args:
            responses: mapping of prompt text -> response text

        Returns:
            Dict with per-prompt scores, per-category averages, and overall.
        """
        if not self._prompts:
            self.load_prompts()

        results: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_prompts": 0,
            "scored_prompts": 0,
            "missing_responses": 0,
            "categories": {},
            "all_scores": [],
        }

        for category, prompts in self._prompts.items():
            cat_scores: List[Dict[str, Any]] = []
            for prompt in prompts:
                results["total_prompts"] += 1
                response = responses.get(prompt)
                if response is None:
                    results["missing_responses"] += 1
                    continue
                scores = self.metrics.score_reasoning(response)
                results["scored_prompts"] += 1
                entry = {"prompt": prompt, "scores": scores}
                cat_scores.append(entry)
                results["all_scores"].append(entry)

            # Category averages
            if cat_scores:
                avg = self._average_scores([e["scores"] for e in cat_scores])
            else:
                avg = {}
            results["categories"][category] = {
                "prompts_scored": len(cat_scores),
                "average_scores": avg,
                "details": cat_scores,
            }

        # Overall averages
        if results["all_scores"]:
            results["overall"] = self._average_scores(
                [e["scores"] for e in results["all_scores"]]
            )
        else:
            results["overall"] = {}

        return results

    def score_counterexamples(
        self,
        responses: Dict[str, str],
    ) -> Dict[str, Any]:
        """Score counterexample responses (should identify wrong reasoning)."""
        if not self._counterexamples:
            self.load_counterexamples()

        results = []
        refutations = 0
        total = 0

        refutation_markers = [
            "not true", "incorrect", "misconception", "actually",
            "contrary", "doesn't", "does not", "false", "myth",
            "wrong", "mistake", "no,", "in fact", "however",
            "this is a common", "oversimplification", "nuanced",
            "not necessarily", "depends on", "more complex",
        ]

        for item in self._counterexamples:
            prompt = item["prompt"]
            expected = item.get("expected", "refutation")
            response = responses.get(prompt, "")
            total += 1

            if not response:
                results.append({
                    "prompt": prompt,
                    "expected": expected,
                    "responded": False,
                    "contains_refutation": False,
                })
                continue

            resp_lower = response.lower()
            found_refutation = any(m in resp_lower for m in refutation_markers)
            if found_refutation and expected == "refutation":
                refutations += 1

            scores = self.metrics.score_reasoning(response)
            results.append({
                "prompt": prompt,
                "expected": expected,
                "responded": True,
                "contains_refutation": found_refutation,
                "scores": scores,
            })

        return {
            "total": total,
            "refutation_rate": round(refutations / max(total, 1), 4),
            "details": results,
        }

    # -- comparison --------------------------------------------------------

    def compare_models(
        self,
        baseline_responses: Dict[str, str],
        trained_responses: Dict[str, str],
    ) -> Dict[str, Any]:
        """Compare baseline vs trained model responses."""
        baseline_results = self.score_responses(baseline_responses)
        trained_results = self.score_responses(trained_responses)

        comparison: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "baseline_overall": baseline_results.get("overall", {}),
            "trained_overall": trained_results.get("overall", {}),
            "category_comparison": {},
            "improvements": {},
            "regressions": {},
        }

        # Per-category delta
        for cat in baseline_results["categories"]:
            b_avg = baseline_results["categories"][cat]["average_scores"]
            t_avg = trained_results["categories"].get(cat, {}).get("average_scores", {})
            delta = {}
            for k in b_avg:
                if k in t_avg and isinstance(b_avg[k], (int, float)):
                    delta[k] = round(t_avg[k] - b_avg[k], 4)
            comparison["category_comparison"][cat] = {
                "baseline": b_avg,
                "trained": t_avg,
                "delta": delta,
            }

        # Overall delta
        b_ov = comparison["baseline_overall"]
        t_ov = comparison["trained_overall"]
        for k in b_ov:
            if k in t_ov and isinstance(b_ov[k], (int, float)):
                d = round(t_ov[k] - b_ov[k], 4)
                if d > 0.01:
                    comparison["improvements"][k] = d
                elif d < -0.01:
                    comparison["regressions"][k] = d

        return comparison

    # -- report ------------------------------------------------------------

    def format_report(self, results: Dict[str, Any]) -> str:
        """Format evaluation results as a readable text report."""
        lines: List[str] = []
        lines.append("=" * 70)
        lines.append("  CODETTE BENCHMARK EVALUATION REPORT")
        lines.append("=" * 70)
        lines.append(f"  Timestamp:  {results.get('timestamp', 'N/A')}")
        lines.append(f"  Prompts:    {results.get('scored_prompts', 0)} scored / "
                      f"{results.get('total_prompts', 0)} total")
        if results.get("missing_responses"):
            lines.append(f"  Missing:    {results['missing_responses']} responses not found")
        lines.append("")

        # Overall
        overall = results.get("overall", {})
        if overall:
            lines.append("-" * 70)
            lines.append("  OVERALL SCORES")
            lines.append("-" * 70)
            for k, v in sorted(overall.items()):
                if isinstance(v, float):
                    bar = self._bar(v)
                    lines.append(f"    {k:<22s} {v:.4f}  {bar}")
            lines.append("")

        # Per-category
        for cat, data in results.get("categories", {}).items():
            avg = data.get("average_scores", {})
            if not avg:
                continue
            lines.append("-" * 70)
            lines.append(f"  CATEGORY: {cat.upper()}")
            lines.append(f"  Prompts scored: {data.get('prompts_scored', 0)}")
            lines.append("-" * 70)
            for k, v in sorted(avg.items()):
                if isinstance(v, float):
                    bar = self._bar(v)
                    lines.append(f"    {k:<22s} {v:.4f}  {bar}")
            lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    def format_comparison_report(self, comparison: Dict[str, Any]) -> str:
        """Format a comparison report between baseline and trained model."""
        lines: List[str] = []
        lines.append("=" * 70)
        lines.append("  MODEL COMPARISON REPORT")
        lines.append("=" * 70)
        lines.append(f"  Timestamp: {comparison.get('timestamp', 'N/A')}")
        lines.append("")

        # Overall
        lines.append("-" * 70)
        lines.append("  OVERALL SCORES  (baseline -> trained [delta])")
        lines.append("-" * 70)
        b = comparison.get("baseline_overall", {})
        t = comparison.get("trained_overall", {})
        for k in sorted(set(list(b.keys()) + list(t.keys()))):
            bv = b.get(k, 0)
            tv = t.get(k, 0)
            if not isinstance(bv, (int, float)):
                continue
            d = tv - bv
            sign = "+" if d >= 0 else ""
            lines.append(f"    {k:<22s} {bv:.4f} -> {tv:.4f}  [{sign}{d:.4f}]")

        # Improvements / regressions
        imp = comparison.get("improvements", {})
        reg = comparison.get("regressions", {})
        if imp:
            lines.append("")
            lines.append("  IMPROVEMENTS:")
            for k, v in sorted(imp.items(), key=lambda x: -x[1]):
                lines.append(f"    + {k}: +{v:.4f}")
        if reg:
            lines.append("")
            lines.append("  REGRESSIONS:")
            for k, v in sorted(reg.items(), key=lambda x: x[1]):
                lines.append(f"    - {k}: {v:.4f}")

        # Per-category
        lines.append("")
        for cat, data in comparison.get("category_comparison", {}).items():
            delta = data.get("delta", {})
            if not delta:
                continue
            overall_d = delta.get("overall", 0)
            sign = "+" if overall_d >= 0 else ""
            lines.append(f"  {cat:<18s}  overall delta: {sign}{overall_d:.4f}")

        lines.append("")
        lines.append("=" * 70)
        return "\n".join(lines)

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _average_scores(score_list: List[Dict[str, float]]) -> Dict[str, float]:
        """Average numeric values across a list of score dicts."""
        if not score_list:
            return {}
        totals: Dict[str, float] = {}
        counts: Dict[str, int] = {}
        for s in score_list:
            for k, v in s.items():
                if isinstance(v, (int, float)):
                    totals[k] = totals.get(k, 0.0) + v
                    counts[k] = counts.get(k, 0) + 1
        return {k: round(totals[k] / counts[k], 4) for k in sorted(totals)}

    @staticmethod
    def _bar(value: float, width: int = 20) -> str:
        """ASCII progress bar."""
        filled = int(value * width)
        return "[" + "#" * filled + "." * (width - filled) + "]"

    # -- save / load results -----------------------------------------------

    def save_results(self, results: Dict[str, Any], filepath: str) -> None:
        """Save evaluation results to JSON."""
        # Convert non-serialisable types
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)

    @staticmethod
    def load_results(filepath: str) -> Dict[str, Any]:
        """Load evaluation results from JSON."""
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Codette Benchmark Runner - evaluate model reasoning quality"
    )
    parser.add_argument(
        "--responses", "-r",
        required=True,
        help="Path to JSON file with pre-generated responses (prompt -> response)",
    )
    parser.add_argument(
        "--prompts-dir", "-p",
        default=None,
        help="Directory containing prompt JSON files (default: evaluation/prompts/)",
    )
    parser.add_argument(
        "--baseline", "-b",
        default=None,
        help="Path to baseline responses JSON for comparison",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Save results to this JSON file",
    )
    parser.add_argument(
        "--counterexamples", "-c",
        action="store_true",
        help="Also run counterexample tests",
    )
    parser.add_argument(
        "--prompts-file",
        default="reasoning_tests.json",
        help="Prompt file name inside prompts dir (default: reasoning_tests.json)",
    )

    args = parser.parse_args()

    runner = BenchmarkRunner(prompts_dir=args.prompts_dir)
    runner.load_prompts(args.prompts_file)

    print(f"Loading responses from: {args.responses}")
    responses = runner.load_responses(args.responses)
    print(f"  Loaded {len(responses)} responses")

    # Score
    print("\nScoring responses...")
    results = runner.score_responses(responses)
    print(runner.format_report(results))

    # Counterexamples
    if args.counterexamples:
        print("\nRunning counterexample tests...")
        runner.load_counterexamples()
        ce_results = runner.score_counterexamples(responses)
        print(f"  Refutation detection rate: {ce_results['refutation_rate']:.2%}")
        results["counterexamples"] = ce_results

    # Comparison
    if args.baseline:
        print(f"\nLoading baseline from: {args.baseline}")
        baseline = runner.load_responses(args.baseline)
        comparison = runner.compare_models(baseline, responses)
        print(runner.format_comparison_report(comparison))
        results["comparison"] = comparison

    # Save
    if args.output:
        runner.save_results(results, args.output)
        print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
