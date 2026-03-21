"""
Failure Analyzer - examines evaluation logs to find patterns in
low-scoring responses, cluster failures by topic, and recommend
dataset improvements.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Keyword extraction (lightweight, no external deps)
# ---------------------------------------------------------------------------

_STOP_WORDS: Set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "out",
    "off", "over", "under", "again", "further", "then", "once", "here",
    "there", "when", "where", "why", "how", "all", "both", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "just", "don",
    "now", "and", "but", "or", "if", "while", "that", "this", "what",
    "which", "who", "whom", "it", "its", "they", "them", "their",
    "he", "she", "him", "her", "his", "we", "us", "our", "you", "your",
    "i", "me", "my", "about", "up",
}


def _extract_keywords(text: str, top_n: int = 8) -> List[str]:
    """Extract the most frequent meaningful words from text."""
    words = re.findall(r"[a-z]{3,}", text.lower())
    filtered = [w for w in words if w not in _STOP_WORDS]
    counts = Counter(filtered)
    return [w for w, _ in counts.most_common(top_n)]


def _jaccard(set_a: Set[str], set_b: Set[str]) -> float:
    """Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


# ---------------------------------------------------------------------------
# FailureAnalyzer
# ---------------------------------------------------------------------------

class FailureAnalyzer:
    """Analyze evaluation results to identify failure patterns."""

    # Score thresholds
    FAILURE_THRESHOLD = 0.4     # scores below this = failure
    WEAK_THRESHOLD = 0.55       # scores below this = weak

    def __init__(
        self,
        failure_threshold: float = 0.4,
        weak_threshold: float = 0.55,
    ):
        self.failure_threshold = failure_threshold
        self.weak_threshold = weak_threshold

    # -- loading -----------------------------------------------------------

    @staticmethod
    def load_results(filepath: str) -> Dict[str, Any]:
        """Load benchmark results JSON produced by BenchmarkRunner."""
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    # -- analysis ----------------------------------------------------------

    def find_failures(
        self,
        results: Dict[str, Any],
        dimension: str = "overall",
    ) -> List[Dict[str, Any]]:
        """Return entries whose *dimension* score is below failure threshold."""
        failures = []
        for entry in results.get("all_scores", []):
            score = entry.get("scores", {}).get(dimension)
            if score is not None and score < self.failure_threshold:
                failures.append({
                    "prompt": entry["prompt"],
                    "score": score,
                    "all_scores": entry["scores"],
                })
        failures.sort(key=lambda x: x["score"])
        return failures

    def find_weak_areas(
        self,
        results: Dict[str, Any],
    ) -> Dict[str, float]:
        """Identify which scoring dimensions are weakest across all prompts.

        Returns dict of dimension -> average score, sorted ascending.
        """
        dimension_totals: Dict[str, float] = defaultdict(float)
        dimension_counts: Dict[str, int] = defaultdict(int)

        for entry in results.get("all_scores", []):
            for k, v in entry.get("scores", {}).items():
                if isinstance(v, float) and k not in ("word_count", "sentence_count"):
                    dimension_totals[k] += v
                    dimension_counts[k] += 1

        averages = {}
        for k in dimension_totals:
            if dimension_counts[k] > 0:
                averages[k] = round(dimension_totals[k] / dimension_counts[k], 4)

        return dict(sorted(averages.items(), key=lambda x: x[1]))

    def failure_rate_by_category(
        self,
        results: Dict[str, Any],
        dimension: str = "overall",
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate failure rates per category."""
        rates: Dict[str, Dict[str, Any]] = {}

        for cat, data in results.get("categories", {}).items():
            details = data.get("details", [])
            total = len(details)
            if total == 0:
                continue
            failures = sum(
                1 for d in details
                if d.get("scores", {}).get(dimension, 1.0) < self.failure_threshold
            )
            weak = sum(
                1 for d in details
                if self.failure_threshold <= d.get("scores", {}).get(dimension, 1.0) < self.weak_threshold
            )
            rates[cat] = {
                "total": total,
                "failures": failures,
                "weak": weak,
                "failure_rate": round(failures / total, 4),
                "weak_rate": round(weak / total, 4),
                "avg_score": data.get("average_scores", {}).get(dimension, 0),
            }

        return dict(sorted(rates.items(), key=lambda x: -x[1]["failure_rate"]))

    def cluster_failures_by_topic(
        self,
        failures: List[Dict[str, Any]],
        similarity_threshold: float = 0.25,
    ) -> List[Dict[str, Any]]:
        """Cluster failure prompts by keyword overlap.

        Uses a simple greedy clustering: each prompt is assigned to the first
        cluster whose centroid keywords have Jaccard similarity above threshold.
        """
        clusters: List[Dict[str, Any]] = []

        for failure in failures:
            prompt = failure["prompt"]
            keywords = set(_extract_keywords(prompt))

            matched = False
            for cluster in clusters:
                if _jaccard(keywords, cluster["keywords"]) >= similarity_threshold:
                    cluster["prompts"].append(failure)
                    cluster["keywords"] |= keywords
                    matched = True
                    break

            if not matched:
                clusters.append({
                    "keywords": keywords,
                    "prompts": [failure],
                })

        # Format output
        result = []
        for i, c in enumerate(clusters):
            avg_score = sum(p["score"] for p in c["prompts"]) / len(c["prompts"])
            result.append({
                "cluster_id": i,
                "topic_keywords": sorted(c["keywords"])[:10],
                "num_failures": len(c["prompts"]),
                "avg_score": round(avg_score, 4),
                "sample_prompts": [p["prompt"] for p in c["prompts"][:5]],
            })

        result.sort(key=lambda x: -x["num_failures"])
        return result

    def identify_weakest_dimensions(
        self,
        results: Dict[str, Any],
        top_n: int = 3,
    ) -> List[Tuple[str, float]]:
        """Return the top_n weakest scoring dimensions."""
        averages = self.find_weak_areas(results)
        items = [(k, v) for k, v in averages.items() if k != "overall"]
        return items[:top_n]

    # -- recommendations ---------------------------------------------------

    def generate_recommendations(
        self,
        results: Dict[str, Any],
    ) -> List[str]:
        """Generate actionable recommendations for dataset improvement."""
        recommendations: List[str] = []

        # Weakest dimensions
        weakest = self.identify_weakest_dimensions(results, top_n=3)
        for dim, score in weakest:
            if score < self.failure_threshold:
                recommendations.append(
                    f"CRITICAL: Dimension '{dim}' averages {score:.3f} (below failure threshold). "
                    f"Add training examples that emphasise {dim} explicitly."
                )
            elif score < self.weak_threshold:
                recommendations.append(
                    f"IMPROVE: Dimension '{dim}' averages {score:.3f} (weak). "
                    f"Augment dataset with responses demonstrating strong {dim}."
                )

        # Category failure rates
        cat_rates = self.failure_rate_by_category(results)
        for cat, info in cat_rates.items():
            if info["failure_rate"] > 0.3:
                recommendations.append(
                    f"CATEGORY '{cat}': {info['failure_rate']:.0%} failure rate. "
                    f"Add more diverse training examples for {cat} topics."
                )

        # Failure clustering
        failures = self.find_failures(results)
        if failures:
            clusters = self.cluster_failures_by_topic(failures)
            for cluster in clusters[:3]:
                kw = ", ".join(cluster["topic_keywords"][:5])
                recommendations.append(
                    f"TOPIC CLUSTER: {cluster['num_failures']} failures around "
                    f"[{kw}]. Create targeted training data for these concepts."
                )

        # General
        overall = results.get("overall", {})
        overall_score = overall.get("overall", 0)
        if overall_score < 0.5:
            recommendations.append(
                "GENERAL: Overall score is very low. Consider increasing dataset size "
                "and diversity before next training run."
            )
        elif overall_score < 0.65:
            recommendations.append(
                "GENERAL: Overall score is moderate. Focus on the weakest categories "
                "and dimensions for the next dataset iteration."
            )

        if not recommendations:
            recommendations.append(
                "No critical issues detected. Continue monitoring with additional benchmarks."
            )

        return recommendations

    # -- report ------------------------------------------------------------

    def format_report(self, results: Dict[str, Any]) -> str:
        """Generate a full failure analysis report."""
        lines: List[str] = []
        lines.append("=" * 70)
        lines.append("  FAILURE ANALYSIS REPORT")
        lines.append("=" * 70)

        # Weakest dimensions
        lines.append("")
        lines.append("-" * 70)
        lines.append("  WEAKEST SCORING DIMENSIONS")
        lines.append("-" * 70)
        weak_areas = self.find_weak_areas(results)
        for dim, score in list(weak_areas.items())[:6]:
            status = "FAIL" if score < self.failure_threshold else (
                "WEAK" if score < self.weak_threshold else "OK  "
            )
            lines.append(f"    [{status}] {dim:<22s}  {score:.4f}")

        # Category failure rates
        lines.append("")
        lines.append("-" * 70)
        lines.append("  FAILURE RATES BY CATEGORY")
        lines.append("-" * 70)
        cat_rates = self.failure_rate_by_category(results)
        for cat, info in cat_rates.items():
            lines.append(
                f"    {cat:<18s}  fail: {info['failure_rate']:>5.1%}  "
                f"weak: {info['weak_rate']:>5.1%}  "
                f"avg: {info['avg_score']:.4f}"
            )

        # Failure clusters
        failures = self.find_failures(results)
        if failures:
            lines.append("")
            lines.append("-" * 70)
            lines.append(f"  FAILURE CLUSTERS ({len(failures)} total failures)")
            lines.append("-" * 70)
            clusters = self.cluster_failures_by_topic(failures)
            for c in clusters[:5]:
                kw = ", ".join(c["topic_keywords"][:6])
                lines.append(f"    Cluster {c['cluster_id']}: "
                             f"{c['num_failures']} failures, "
                             f"avg score {c['avg_score']:.4f}")
                lines.append(f"      Topics: {kw}")
                for p in c["sample_prompts"][:2]:
                    lines.append(f"      - {p[:70]}...")

        # Recommendations
        lines.append("")
        lines.append("-" * 70)
        lines.append("  RECOMMENDATIONS")
        lines.append("-" * 70)
        recs = self.generate_recommendations(results)
        for i, rec in enumerate(recs, 1):
            lines.append(f"    {i}. {rec}")

        lines.append("")
        lines.append("=" * 70)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Codette Failure Analyzer - identify patterns in evaluation failures"
    )
    parser.add_argument(
        "--results", "-r",
        required=True,
        help="Path to benchmark results JSON",
    )
    parser.add_argument(
        "--failure-threshold", "-f",
        type=float,
        default=0.4,
        help="Score threshold for failure (default: 0.4)",
    )
    parser.add_argument(
        "--weak-threshold", "-w",
        type=float,
        default=0.55,
        help="Score threshold for weak (default: 0.55)",
    )

    args = parser.parse_args()

    analyzer = FailureAnalyzer(
        failure_threshold=args.failure_threshold,
        weak_threshold=args.weak_threshold,
    )
    results = analyzer.load_results(args.results)
    print(analyzer.format_report(results))


if __name__ == "__main__":
    main()
