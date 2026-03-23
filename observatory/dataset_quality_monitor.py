"""
Dataset Quality Monitor - tracks dataset quality metrics across versions,
compares quality between iterations, and flags regressions.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


_DEFAULT_QUALITY_FILE = Path(__file__).resolve().parent.parent / "data" / "results" / "dataset_quality_log.json"


class DatasetQualityMonitor:
    """Monitor dataset quality metrics across versions."""

    # Thresholds for regression detection
    REGRESSION_THRESHOLDS = {
        "total_examples": -0.10,         # >10% decrease in size
        "avg_response_length": -0.15,     # >15% decrease in avg length
        "duplicate_rate": 0.05,           # >5% absolute increase in duplicates
        "topic_diversity": -0.10,         # >10% decrease in diversity
    }

    def __init__(self, quality_file: Optional[str] = None):
        self.quality_file = Path(quality_file) if quality_file else _DEFAULT_QUALITY_FILE
        self._lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self.quality_file.exists():
            os.makedirs(self.quality_file.parent, exist_ok=True)
            with open(self.quality_file, "w", encoding="utf-8") as f:
                json.dump([], f)

    def _read_all(self) -> List[Dict[str, Any]]:
        with open(self.quality_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
        return data if isinstance(data, list) else []

    def _write_all(self, entries: List[Dict[str, Any]]) -> None:
        with open(self.quality_file, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, default=str)

    # -- recording ---------------------------------------------------------

    def record_quality(
        self,
        dataset_version: str,
        total_examples: int,
        valid_examples: int,
        avg_response_length: float,
        duplicate_rate: float,
        near_duplicate_rate: float,
        topic_diversity: float,
        topic_concentration: float,
        min_length: int = 0,
        max_length: int = 0,
        too_short: int = 0,
        too_long: int = 0,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record quality metrics for a dataset version.

        Returns the recorded entry.
        """
        entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "dataset_version": dataset_version,
            "total_examples": total_examples,
            "valid_examples": valid_examples,
            "invalid_examples": total_examples - valid_examples,
            "validity_rate": round(valid_examples / max(total_examples, 1), 4),
            "avg_response_length": round(avg_response_length, 1),
            "duplicate_rate": round(duplicate_rate, 4),
            "near_duplicate_rate": round(near_duplicate_rate, 4),
            "topic_diversity": round(topic_diversity, 4),
            "topic_concentration": round(topic_concentration, 4),
            "min_length": min_length,
            "max_length": max_length,
            "too_short": too_short,
            "too_long": too_long,
        }
        if extra:
            entry["extra"] = extra

        with self._lock:
            entries = self._read_all()
            entries.append(entry)
            self._write_all(entries)

        return entry

    def record_from_validation_report(
        self,
        dataset_version: str,
        report: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Record quality from a DatasetValidator report dict."""
        ls = report.get("response_length_stats", {})
        total = report.get("total_lines", 0)
        valid = report.get("valid", 0)
        exact_dup = report.get("exact_duplicates", 0)
        near_dup = report.get("near_duplicates", 0)

        return self.record_quality(
            dataset_version=dataset_version,
            total_examples=total,
            valid_examples=valid,
            avg_response_length=ls.get("mean", 0),
            duplicate_rate=exact_dup / max(total, 1),
            near_duplicate_rate=near_dup / max(total, 1),
            topic_diversity=report.get("unique_topics", 0) / max(total, 1),
            topic_concentration=report.get("topic_concentration", 0),
            min_length=ls.get("min", 0),
            max_length=ls.get("max", 0),
            too_short=report.get("too_short", 0),
            too_long=report.get("too_long", 0),
        )

    # -- querying ----------------------------------------------------------

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all quality records."""
        with self._lock:
            return self._read_all()

    def get_by_version(self, version: str) -> Optional[Dict[str, Any]]:
        """Get the latest quality record for a specific version."""
        entries = self.get_all()
        matches = [e for e in entries if e.get("dataset_version") == version]
        if not matches:
            return None
        return max(matches, key=lambda e: e.get("timestamp", ""))

    def get_latest(self) -> Optional[Dict[str, Any]]:
        """Get the most recent quality record."""
        entries = self.get_all()
        if not entries:
            return None
        return max(entries, key=lambda e: e.get("timestamp", ""))

    def get_versions(self) -> List[str]:
        """Get all unique dataset versions, in chronological order."""
        entries = sorted(self.get_all(), key=lambda e: e.get("timestamp", ""))
        seen = set()
        versions = []
        for e in entries:
            v = e.get("dataset_version", "unknown")
            if v not in seen:
                seen.add(v)
                versions.append(v)
        return versions

    # -- comparison --------------------------------------------------------

    def compare_versions(
        self,
        version_a: str,
        version_b: str,
    ) -> Dict[str, Any]:
        """Compare quality metrics between two dataset versions.

        Returns dict with metrics from each version and deltas.
        """
        a = self.get_by_version(version_a)
        b = self.get_by_version(version_b)

        if not a or not b:
            return {
                "error": f"Missing version data: "
                         f"{'version_a' if not a else 'version_b'} not found",
                "version_a": version_a,
                "version_b": version_b,
            }

        compare_keys = [
            "total_examples", "valid_examples", "validity_rate",
            "avg_response_length", "duplicate_rate", "near_duplicate_rate",
            "topic_diversity", "topic_concentration", "too_short", "too_long",
        ]

        delta = {}
        pct_change = {}
        for k in compare_keys:
            va = a.get(k, 0)
            vb = b.get(k, 0)
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                delta[k] = round(vb - va, 4)
                if va != 0:
                    pct_change[k] = round((vb - va) / abs(va) * 100, 2)
                else:
                    pct_change[k] = 0.0

        return {
            "version_a": version_a,
            "version_b": version_b,
            "metrics_a": {k: a.get(k) for k in compare_keys},
            "metrics_b": {k: b.get(k) for k in compare_keys},
            "delta": delta,
            "percent_change": pct_change,
        }

    # -- regression detection ----------------------------------------------

    def detect_regressions(
        self,
        version_a: str,
        version_b: str,
    ) -> List[Dict[str, Any]]:
        """Detect quality regressions between version_a and version_b.

        Returns list of regression dicts, each with:
        - metric, old_value, new_value, change, threshold, severity
        """
        comparison = self.compare_versions(version_a, version_b)
        if "error" in comparison:
            return []

        regressions: List[Dict[str, Any]] = []

        for metric, threshold in self.REGRESSION_THRESHOLDS.items():
            pct = comparison.get("percent_change", {}).get(metric, 0)
            delta = comparison.get("delta", {}).get(metric, 0)
            old_val = comparison.get("metrics_a", {}).get(metric, 0)
            new_val = comparison.get("metrics_b", {}).get(metric, 0)

            is_regression = False
            if metric == "duplicate_rate":
                # For duplicate_rate, regression is an absolute increase
                if delta > threshold:
                    is_regression = True
            else:
                # For others, regression is a percentage decrease
                if old_val != 0 and (pct / 100) < threshold:
                    is_regression = True

            if is_regression:
                severity = "critical" if abs(pct) > abs(threshold * 100 * 2) else "warning"
                regressions.append({
                    "metric": metric,
                    "old_value": old_val,
                    "new_value": new_val,
                    "change": delta,
                    "percent_change": pct,
                    "threshold": threshold,
                    "severity": severity,
                })

        return regressions

    def check_latest_regressions(self) -> List[Dict[str, Any]]:
        """Compare the two most recent versions and check for regressions."""
        versions = self.get_versions()
        if len(versions) < 2:
            return []
        return self.detect_regressions(versions[-2], versions[-1])

    # -- formatting --------------------------------------------------------

    def format_quality_summary(self) -> str:
        """Format a summary of all dataset quality records."""
        entries = sorted(self.get_all(), key=lambda e: e.get("timestamp", ""))
        if not entries:
            return "No dataset quality records found."

        lines: List[str] = []
        lines.append("=" * 74)
        lines.append("  DATASET QUALITY MONITOR")
        lines.append("=" * 74)
        lines.append(f"  Total records: {len(entries)}")
        lines.append(f"  Versions tracked: {len(self.get_versions())}")
        lines.append("")

        # Table header
        lines.append("-" * 74)
        lines.append(
            f"  {'Version':<16} {'Total':>6} {'Valid':>6} {'AvgLen':>7} "
            f"{'Dup%':>6} {'Divers':>7} {'Conc%':>6}"
        )
        lines.append(
            f"  {'-------':<16} {'-----':>6} {'-----':>6} {'------':>7} "
            f"{'----':>6} {'------':>7} {'-----':>6}"
        )

        for e in entries:
            ver = e.get("dataset_version", "?")[:15]
            total = e.get("total_examples", 0)
            valid = e.get("valid_examples", 0)
            avg_len = e.get("avg_response_length", 0)
            dup = e.get("duplicate_rate", 0) * 100
            div = e.get("topic_diversity", 0)
            conc = e.get("topic_concentration", 0) * 100
            lines.append(
                f"  {ver:<16} {total:>6} {valid:>6} {avg_len:>7.1f} "
                f"{dup:>5.1f}% {div:>7.4f} {conc:>5.1f}%"
            )

        # Regressions
        regressions = self.check_latest_regressions()
        if regressions:
            lines.append("")
            lines.append("-" * 74)
            lines.append("  QUALITY REGRESSIONS DETECTED")
            lines.append("-" * 74)
            for r in regressions:
                sev = r["severity"].upper()
                lines.append(
                    f"  [{sev}] {r['metric']}: "
                    f"{r['old_value']} -> {r['new_value']} "
                    f"({r['percent_change']:+.1f}%)"
                )

        lines.append("")
        lines.append("=" * 74)
        return "\n".join(lines)
