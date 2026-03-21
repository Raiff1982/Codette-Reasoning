"""
Dashboard - ASCII-formatted system status display for the Codette training lab.

Shows:
- Latest training run stats
- Best adapter scores
- Dataset sizes and quality
- Failure rates
- Improvement trends

No web framework required; pure terminal output.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from observatory.metrics_logger import MetricsLogger
from observatory.performance_tracker import PerformanceTracker
from observatory.dataset_quality_monitor import DatasetQualityMonitor


class Dashboard:
    """ASCII dashboard for the Codette training lab."""

    WIDTH = 76

    def __init__(
        self,
        metrics_log: Optional[str] = None,
        quality_log: Optional[str] = None,
        eval_results: Optional[str] = None,
    ):
        self.logger = MetricsLogger(log_file=metrics_log)
        self.tracker = PerformanceTracker(logger=self.logger)
        self.quality_monitor = DatasetQualityMonitor(quality_file=quality_log)
        self.eval_results_path = eval_results

    # -- sections ----------------------------------------------------------

    def _header(self) -> List[str]:
        lines = []
        lines.append("")
        lines.append("+" + "=" * (self.WIDTH - 2) + "+")
        lines.append("|" + " CODETTE TRAINING LAB OBSERVATORY ".center(self.WIDTH - 2) + "|")
        lines.append("|" + f" {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} ".center(self.WIDTH - 2) + "|")
        lines.append("+" + "=" * (self.WIDTH - 2) + "+")
        return lines

    def _section(self, title: str) -> List[str]:
        lines = []
        lines.append("")
        lines.append("+" + "-" * (self.WIDTH - 2) + "+")
        lines.append("|" + f" {title} ".ljust(self.WIDTH - 2) + "|")
        lines.append("+" + "-" * (self.WIDTH - 2) + "+")
        return lines

    def _row(self, label: str, value: str) -> str:
        """Single label: value row."""
        content = f"  {label:<30s} {value}"
        return "|" + content.ljust(self.WIDTH - 2) + "|"

    def _bar_row(self, label: str, value: float, max_width: int = 30) -> str:
        """Row with ASCII progress bar."""
        filled = int(value * max_width)
        bar = "[" + "#" * filled + "." * (max_width - filled) + "]"
        content = f"  {label:<22s} {value:>6.3f} {bar}"
        return "|" + content.ljust(self.WIDTH - 2) + "|"

    def _empty_row(self) -> str:
        return "|" + " " * (self.WIDTH - 2) + "|"

    def _footer(self) -> List[str]:
        return ["+" + "=" * (self.WIDTH - 2) + "+", ""]

    # -- sections ----------------------------------------------------------

    def _latest_training_section(self) -> List[str]:
        lines = self._section("LATEST TRAINING RUN")

        latest = self.logger.get_latest()
        if not latest:
            lines.append(self._row("Status", "No training runs logged yet"))
            return lines

        lines.append(self._row("Adapter", latest.get("adapter", "N/A")))
        lines.append(self._row("Timestamp", latest.get("timestamp", "N/A")))
        lines.append(self._row("Dataset Version", latest.get("dataset_version", "N/A")))
        lines.append(self._row("Dataset Size", str(latest.get("dataset_size", 0))))
        lines.append(self._row("Epoch", str(latest.get("epoch", 0))))
        lines.append(self._bar_row("Reasoning Score", latest.get("reasoning_score", 0)))
        lines.append(self._row("Loss", f"{latest.get('loss', 0):.6f}"))

        params = latest.get("training_params", {})
        if params:
            lines.append(self._empty_row())
            lines.append(self._row("Training Parameters", ""))
            for k, v in list(params.items())[:6]:
                lines.append(self._row(f"  {k}", str(v)))

        return lines

    def _best_adapters_section(self) -> List[str]:
        lines = self._section("TOP ADAPTERS")

        best = self.tracker.best_adapters(top_n=5)
        if not best:
            lines.append(self._row("Status", "No adapter data available"))
            return lines

        # Table header
        hdr = f"  {'#':<3} {'Adapter':<26} {'Score':>7} {'Loss':>7} {'Epoch':>5}"
        lines.append("|" + hdr.ljust(self.WIDTH - 2) + "|")
        sep = f"  {'--':<3} {'------':<26} {'-----':>7} {'----':>7} {'-----':>5}"
        lines.append("|" + sep.ljust(self.WIDTH - 2) + "|")

        for i, entry in enumerate(best, 1):
            name = entry.get("adapter", "?")[:25]
            score = entry.get("reasoning_score", 0)
            loss = entry.get("loss", 0)
            epoch = entry.get("epoch", 0)
            row = f"  {i:<3} {name:<26} {score:>7.4f} {loss:>7.4f} {epoch:>5}"
            lines.append("|" + row.ljust(self.WIDTH - 2) + "|")

        return lines

    def _dataset_quality_section(self) -> List[str]:
        lines = self._section("DATASET QUALITY")

        latest = self.quality_monitor.get_latest()
        if not latest:
            lines.append(self._row("Status", "No quality data recorded"))
            return lines

        lines.append(self._row("Dataset Version", latest.get("dataset_version", "N/A")))
        lines.append(self._row("Total Examples", str(latest.get("total_examples", 0))))
        lines.append(self._row("Valid Examples", str(latest.get("valid_examples", 0))))
        lines.append(self._bar_row("Validity Rate", latest.get("validity_rate", 0)))
        lines.append(self._row("Avg Response Length", f"{latest.get('avg_response_length', 0):.1f} words"))
        lines.append(self._row("Duplicate Rate", f"{latest.get('duplicate_rate', 0):.2%}"))
        lines.append(self._row("Near-Duplicate Rate", f"{latest.get('near_duplicate_rate', 0):.2%}"))
        lines.append(self._bar_row("Topic Diversity", min(latest.get("topic_diversity", 0) * 10, 1.0)))
        lines.append(self._row("Topic Concentration", f"{latest.get('topic_concentration', 0):.2%}"))

        # Regressions
        regressions = self.quality_monitor.check_latest_regressions()
        if regressions:
            lines.append(self._empty_row())
            for r in regressions:
                sev = r["severity"].upper()
                msg = f"  [{sev}] {r['metric']}: {r['percent_change']:+.1f}%"
                lines.append("|" + msg.ljust(self.WIDTH - 2) + "|")

        return lines

    def _improvement_trends_section(self) -> List[str]:
        lines = self._section("IMPROVEMENT TRENDS")

        trends = self.tracker.improvement_trends()
        if not trends:
            lines.append(self._row("Status", "Insufficient data for trends"))
            return lines

        for t in trends[:5]:
            name = t["adapter"][:22]
            delta = t["delta"]
            pct = t["percent_change"]
            runs = t["num_runs"]
            sign = "+" if delta >= 0 else ""
            indicator = "^" if delta > 0.01 else ("v" if delta < -0.01 else "=")

            row = (f"  {indicator} {name:<22} "
                   f"delta: {sign}{delta:.4f}  "
                   f"({sign}{pct:.1f}%)  "
                   f"[{runs} runs]")
            lines.append("|" + row.ljust(self.WIDTH - 2) + "|")

        return lines

    def _failure_rates_section(self) -> List[str]:
        lines = self._section("EVALUATION FAILURE RATES")

        if not self.eval_results_path or not os.path.exists(self.eval_results_path):
            lines.append(self._row("Status", "No evaluation results file specified"))
            return lines

        try:
            with open(self.eval_results_path, "r", encoding="utf-8") as f:
                results = json.load(f)
        except (json.JSONDecodeError, OSError):
            lines.append(self._row("Status", "Could not load evaluation results"))
            return lines

        # Overall score
        overall = results.get("overall", {})
        if overall:
            overall_score = overall.get("overall", 0)
            lines.append(self._bar_row("Overall Score", overall_score))
            lines.append(self._empty_row())

        # Per-category scores
        categories = results.get("categories", {})
        if categories:
            hdr = f"  {'Category':<20} {'Score':>7} {'Prompts':>8}"
            lines.append("|" + hdr.ljust(self.WIDTH - 2) + "|")
            sep = f"  {'--------':<20} {'-----':>7} {'-------':>8}"
            lines.append("|" + sep.ljust(self.WIDTH - 2) + "|")

            for cat, data in sorted(categories.items()):
                avg = data.get("average_scores", {}).get("overall", 0)
                n = data.get("prompts_scored", 0)
                status = "*" if avg < 0.4 else ("~" if avg < 0.55 else " ")
                row = f"  {status}{cat:<19} {avg:>7.4f} {n:>8}"
                lines.append("|" + row.ljust(self.WIDTH - 2) + "|")

            lines.append(self._empty_row())
            lines.append("|" + "  * = failing, ~ = weak".ljust(self.WIDTH - 2) + "|")

        return lines

    def _sparkline_section(self) -> List[str]:
        lines = self._section("SCORE HISTORY")

        adapters = self.logger.get_unique_adapters()
        if not adapters:
            lines.append(self._row("Status", "No history data"))
            return lines

        for adapter in adapters[:6]:
            progression = self.tracker.score_progression(adapter)
            if not progression:
                continue
            scores = [p["reasoning_score"] for p in progression]
            spark = PerformanceTracker._sparkline(scores, width=30)
            name = adapter[:20]
            row = f"  {name:<21} {spark} [{scores[0]:.3f}->{scores[-1]:.3f}]"
            lines.append("|" + row.ljust(self.WIDTH - 2) + "|")

        return lines

    # -- main render -------------------------------------------------------

    def render(self) -> str:
        """Render the complete dashboard."""
        all_lines: List[str] = []
        all_lines.extend(self._header())
        all_lines.extend(self._latest_training_section())
        all_lines.extend(self._best_adapters_section())
        all_lines.extend(self._dataset_quality_section())
        all_lines.extend(self._improvement_trends_section())
        all_lines.extend(self._failure_rates_section())
        all_lines.extend(self._sparkline_section())
        all_lines.extend(self._footer())
        return "\n".join(all_lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Codette Observatory Dashboard - ASCII system status display"
    )
    parser.add_argument(
        "--metrics-log", "-m",
        default=None,
        help="Path to observatory_metrics.json",
    )
    parser.add_argument(
        "--quality-log", "-q",
        default=None,
        help="Path to dataset_quality_log.json",
    )
    parser.add_argument(
        "--eval-results", "-e",
        default=None,
        help="Path to benchmark evaluation results JSON",
    )
    parser.add_argument(
        "--section", "-s",
        choices=["training", "adapters", "quality", "trends", "failures", "history", "all"],
        default="all",
        help="Show only a specific section (default: all)",
    )

    args = parser.parse_args()

    dashboard = Dashboard(
        metrics_log=args.metrics_log,
        quality_log=args.quality_log,
        eval_results=args.eval_results,
    )

    if args.section == "all":
        print(dashboard.render())
    else:
        section_map = {
            "training": dashboard._latest_training_section,
            "adapters": dashboard._best_adapters_section,
            "quality": dashboard._dataset_quality_section,
            "trends": dashboard._improvement_trends_section,
            "failures": dashboard._failure_rates_section,
            "history": dashboard._sparkline_section,
        }
        func = section_map.get(args.section)
        if func:
            lines = dashboard._header()
            lines.extend(func())
            lines.extend(dashboard._footer())
            print("\n".join(lines))


if __name__ == "__main__":
    main()
