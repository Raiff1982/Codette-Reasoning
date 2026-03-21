"""
Performance Tracker - analyses training metrics history to identify
improvement trends, best adapters, and score progression.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from observatory.metrics_logger import MetricsLogger


class PerformanceTracker:
    """Analyse training metrics to track improvement over time."""

    def __init__(self, logger: Optional[MetricsLogger] = None, log_file: Optional[str] = None):
        self.logger = logger or MetricsLogger(log_file=log_file)

    # -- trend analysis ----------------------------------------------------

    def score_progression(self, adapter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get score progression over time for an adapter (or all).

        Returns list of dicts with timestamp, adapter, reasoning_score, loss, epoch.
        """
        if adapter:
            entries = self.logger.get_by_adapter(adapter)
        else:
            entries = self.logger.get_all()

        entries = sorted(entries, key=lambda e: e.get("timestamp", ""))
        return [
            {
                "timestamp": e.get("timestamp"),
                "adapter": e.get("adapter"),
                "reasoning_score": e.get("reasoning_score", 0),
                "loss": e.get("loss", 0),
                "epoch": e.get("epoch", 0),
                "dataset_size": e.get("dataset_size", 0),
            }
            for e in entries
        ]

    def calculate_improvement(self, adapter: str) -> Dict[str, Any]:
        """Calculate improvement between first and last run for an adapter.

        Returns dict with first_score, last_score, delta, percent_change,
        num_runs, first_timestamp, last_timestamp.
        """
        entries = self.logger.get_by_adapter(adapter)
        if len(entries) < 2:
            return {
                "adapter": adapter,
                "num_runs": len(entries),
                "first_score": entries[0]["reasoning_score"] if entries else 0,
                "last_score": entries[-1]["reasoning_score"] if entries else 0,
                "delta": 0.0,
                "percent_change": 0.0,
                "sufficient_data": False,
            }

        entries = sorted(entries, key=lambda e: e.get("timestamp", ""))
        first = entries[0]
        last = entries[-1]
        first_score = first.get("reasoning_score", 0)
        last_score = last.get("reasoning_score", 0)
        delta = last_score - first_score
        pct = (delta / first_score * 100) if first_score > 0 else 0.0

        return {
            "adapter": adapter,
            "num_runs": len(entries),
            "first_score": round(first_score, 6),
            "last_score": round(last_score, 6),
            "delta": round(delta, 6),
            "percent_change": round(pct, 2),
            "first_timestamp": first.get("timestamp"),
            "last_timestamp": last.get("timestamp"),
            "sufficient_data": True,
        }

    def improvement_trends(self) -> List[Dict[str, Any]]:
        """Calculate improvement trends for all adapters."""
        adapters = self.logger.get_unique_adapters()
        trends = []
        for adapter in adapters:
            trend = self.calculate_improvement(adapter)
            trends.append(trend)
        trends.sort(key=lambda t: t.get("delta", 0), reverse=True)
        return trends

    def best_adapters(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """Find the best-performing adapter versions by reasoning score.

        Returns list of entries sorted by highest reasoning_score.
        """
        entries = self.logger.get_all()
        if not entries:
            return []

        # Group by adapter, take best score for each
        best: Dict[str, Dict[str, Any]] = {}
        for e in entries:
            adapter = e.get("adapter", "unknown")
            score = e.get("reasoning_score", 0)
            if adapter not in best or score > best[adapter].get("reasoning_score", 0):
                best[adapter] = e

        ranked = sorted(best.values(), key=lambda e: e.get("reasoning_score", 0), reverse=True)
        return ranked[:top_n]

    def run_to_run_deltas(self, adapter: str) -> List[Dict[str, float]]:
        """Calculate score delta between consecutive runs of an adapter."""
        entries = self.logger.get_by_adapter(adapter)
        entries = sorted(entries, key=lambda e: e.get("timestamp", ""))

        deltas = []
        for i in range(1, len(entries)):
            prev_score = entries[i - 1].get("reasoning_score", 0)
            curr_score = entries[i].get("reasoning_score", 0)
            deltas.append({
                "run": i,
                "from_timestamp": entries[i - 1].get("timestamp"),
                "to_timestamp": entries[i].get("timestamp"),
                "score_delta": round(curr_score - prev_score, 6),
                "loss_delta": round(
                    entries[i].get("loss", 0) - entries[i - 1].get("loss", 0), 6
                ),
            })
        return deltas

    def loss_progression(self, adapter: Optional[str] = None) -> List[Tuple[str, float]]:
        """Get loss values over time."""
        if adapter:
            entries = self.logger.get_by_adapter(adapter)
        else:
            entries = self.logger.get_all()
        entries = sorted(entries, key=lambda e: e.get("timestamp", ""))
        return [(e.get("timestamp", ""), e.get("loss", 0)) for e in entries]

    # -- report ------------------------------------------------------------

    def format_report(self) -> str:
        """Generate a formatted text report of performance tracking."""
        lines: List[str] = []
        lines.append("=" * 74)
        lines.append("  CODETTE PERFORMANCE TRACKING REPORT")
        lines.append("=" * 74)

        entries = self.logger.get_all()
        lines.append(f"  Total logged runs: {len(entries)}")
        lines.append(f"  Unique adapters:   {len(self.logger.get_unique_adapters())}")
        lines.append("")

        # Best adapters table
        best = self.best_adapters(top_n=10)
        if best:
            lines.append("-" * 74)
            lines.append("  TOP ADAPTERS BY REASONING SCORE")
            lines.append("-" * 74)
            lines.append(f"  {'Rank':<5} {'Adapter':<28} {'Score':>8} {'Loss':>8} {'Epoch':>6} {'Data':>6}")
            lines.append(f"  {'----':<5} {'-------':<28} {'-----':>8} {'----':>8} {'-----':>6} {'----':>6}")
            for i, entry in enumerate(best, 1):
                name = entry.get("adapter", "?")[:27]
                score = entry.get("reasoning_score", 0)
                loss = entry.get("loss", 0)
                epoch = entry.get("epoch", 0)
                ds = entry.get("dataset_size", 0)
                lines.append(
                    f"  {i:<5} {name:<28} {score:>8.4f} {loss:>8.4f} {epoch:>6} {ds:>6}"
                )
            lines.append("")

        # Improvement trends
        trends = self.improvement_trends()
        if trends:
            lines.append("-" * 74)
            lines.append("  IMPROVEMENT TRENDS (first run -> last run)")
            lines.append("-" * 74)
            lines.append(
                f"  {'Adapter':<28} {'First':>8} {'Last':>8} {'Delta':>8} {'Change':>8} {'Runs':>5}"
            )
            lines.append(
                f"  {'-------':<28} {'-----':>8} {'----':>8} {'-----':>8} {'------':>8} {'----':>5}"
            )
            for t in trends:
                name = t["adapter"][:27]
                first = t["first_score"]
                last = t["last_score"]
                delta = t["delta"]
                pct = t["percent_change"]
                runs = t["num_runs"]
                sign = "+" if delta >= 0 else ""
                lines.append(
                    f"  {name:<28} {first:>8.4f} {last:>8.4f} "
                    f"{sign}{delta:>7.4f} {sign}{pct:>6.1f}% {runs:>5}"
                )
            lines.append("")

        # Score progression chart (ASCII sparkline per adapter)
        adapters = self.logger.get_unique_adapters()
        if adapters:
            lines.append("-" * 74)
            lines.append("  SCORE PROGRESSION (ASCII sparkline)")
            lines.append("-" * 74)
            for adapter in adapters[:8]:
                progression = self.score_progression(adapter)
                if not progression:
                    continue
                scores = [p["reasoning_score"] for p in progression]
                sparkline = self._sparkline(scores, width=40)
                name = adapter[:24]
                lines.append(f"  {name:<25} {sparkline}  [{scores[0]:.3f} -> {scores[-1]:.3f}]")
            lines.append("")

        lines.append("=" * 74)
        return "\n".join(lines)

    @staticmethod
    def _sparkline(values: List[float], width: int = 40) -> str:
        """Create an ASCII sparkline from a list of values."""
        if not values:
            return ""
        if len(values) == 1:
            return "-"

        min_v = min(values)
        max_v = max(values)
        range_v = max_v - min_v if max_v > min_v else 1.0

        chars = " _.-~^"
        n_chars = len(chars) - 1

        # Resample to fit width
        if len(values) > width:
            step = len(values) / width
            resampled = []
            for i in range(width):
                idx = int(i * step)
                resampled.append(values[min(idx, len(values) - 1)])
            values = resampled
        elif len(values) < width:
            # Pad with last value
            values = values + [values[-1]] * (width - len(values))

        result = ""
        for v in values[:width]:
            normalised = (v - min_v) / range_v
            idx = int(normalised * n_chars)
            idx = max(0, min(idx, n_chars))
            result += chars[idx]

        return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Codette Performance Tracker - analyse training run history"
    )
    parser.add_argument(
        "--log-file", "-l",
        default=None,
        help="Path to observatory_metrics.json (default: auto-detect)",
    )
    parser.add_argument(
        "--adapter", "-a",
        default=None,
        help="Filter to a specific adapter name",
    )
    parser.add_argument(
        "--best", "-b",
        type=int,
        default=None,
        help="Show top N best adapters",
    )
    parser.add_argument(
        "--deltas", "-d",
        default=None,
        help="Show run-to-run deltas for a specific adapter",
    )

    args = parser.parse_args()

    tracker = PerformanceTracker(log_file=args.log_file)

    if args.best:
        best = tracker.best_adapters(top_n=args.best)
        for i, entry in enumerate(best, 1):
            print(f"  {i}. {entry.get('adapter', '?')} - "
                  f"score: {entry.get('reasoning_score', 0):.4f}, "
                  f"loss: {entry.get('loss', 0):.4f}")
        return

    if args.deltas:
        deltas = tracker.run_to_run_deltas(args.deltas)
        if not deltas:
            print(f"No run-to-run data for adapter: {args.deltas}")
            return
        for d in deltas:
            sign = "+" if d["score_delta"] >= 0 else ""
            print(f"  Run {d['run']}: score {sign}{d['score_delta']:.6f}, "
                  f"loss {sign}{d['loss_delta']:.6f}")
        return

    if args.adapter:
        improvement = tracker.calculate_improvement(args.adapter)
        print(f"  Adapter: {improvement['adapter']}")
        print(f"  Runs: {improvement['num_runs']}")
        print(f"  First score: {improvement['first_score']:.6f}")
        print(f"  Last score:  {improvement['last_score']:.6f}")
        print(f"  Delta:       {improvement['delta']:+.6f}")
        print(f"  Change:      {improvement['percent_change']:+.2f}%")
        return

    # Full report
    print(tracker.format_report())


if __name__ == "__main__":
    main()
