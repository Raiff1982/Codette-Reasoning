"""
Metrics Logger - thread-safe logging of training metrics to a JSON file.

Each entry records: timestamp, adapter name, dataset size, dataset version,
reasoning score, loss, epoch, and training parameters.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


_DEFAULT_LOG_FILE = Path(__file__).resolve().parent.parent / "data" / "results" / "observatory_metrics.json"


class MetricsLogger:
    """Thread-safe logger for training run metrics."""

    def __init__(self, log_file: Optional[str] = None):
        self.log_file = Path(log_file) if log_file else _DEFAULT_LOG_FILE
        self._lock = threading.Lock()
        self._ensure_file()

    # -- internal ----------------------------------------------------------

    def _ensure_file(self) -> None:
        """Create the log file with an empty list if it doesn't exist."""
        if not self.log_file.exists():
            os.makedirs(self.log_file.parent, exist_ok=True)
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump([], f)

    def _read_all(self) -> List[Dict[str, Any]]:
        """Read all entries from the log file."""
        with open(self.log_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
        if not isinstance(data, list):
            data = []
        return data

    def _write_all(self, entries: List[Dict[str, Any]]) -> None:
        """Write all entries back to the log file."""
        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, default=str)

    # -- public API --------------------------------------------------------

    def log(
        self,
        adapter: str,
        dataset_size: int,
        dataset_version: str,
        reasoning_score: float,
        loss: float,
        epoch: int,
        training_params: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Log a single training run metric entry.

        Returns the logged entry dict.
        """
        entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "adapter": adapter,
            "dataset_size": dataset_size,
            "dataset_version": dataset_version,
            "reasoning_score": round(reasoning_score, 6),
            "loss": round(loss, 6),
            "epoch": epoch,
            "training_params": training_params or {},
        }
        if extra:
            entry["extra"] = extra

        with self._lock:
            entries = self._read_all()
            entries.append(entry)
            self._write_all(entries)

        return entry

    def log_batch(self, entries: List[Dict[str, Any]]) -> int:
        """Log multiple entries at once. Each entry should have the same
        keys as the arguments to log(). Returns number of entries added."""
        formatted: List[Dict[str, Any]] = []
        for e in entries:
            formatted.append({
                "timestamp": e.get("timestamp", datetime.utcnow().isoformat() + "Z"),
                "adapter": e.get("adapter", "unknown"),
                "dataset_size": e.get("dataset_size", 0),
                "dataset_version": e.get("dataset_version", "unknown"),
                "reasoning_score": round(e.get("reasoning_score", 0.0), 6),
                "loss": round(e.get("loss", 0.0), 6),
                "epoch": e.get("epoch", 0),
                "training_params": e.get("training_params", {}),
            })

        with self._lock:
            existing = self._read_all()
            existing.extend(formatted)
            self._write_all(existing)

        return len(formatted)

    def get_all(self) -> List[Dict[str, Any]]:
        """Return all logged entries."""
        with self._lock:
            return self._read_all()

    def get_by_adapter(self, adapter: str) -> List[Dict[str, Any]]:
        """Return entries filtered by adapter name."""
        entries = self.get_all()
        return [e for e in entries if e.get("adapter") == adapter]

    def get_by_date_range(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return entries within a date range (ISO format strings).

        Args:
            start: ISO date/datetime string (inclusive). None = no lower bound.
            end: ISO date/datetime string (inclusive). None = no upper bound.
        """
        entries = self.get_all()
        filtered = []
        for e in entries:
            ts = e.get("timestamp", "")
            if start and ts < start:
                continue
            if end and ts > end:
                continue
            filtered.append(e)
        return filtered

    def get_latest(self, adapter: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Return the most recent entry, optionally filtered by adapter."""
        entries = self.get_by_adapter(adapter) if adapter else self.get_all()
        if not entries:
            return None
        return max(entries, key=lambda e: e.get("timestamp", ""))

    def get_unique_adapters(self) -> List[str]:
        """Return list of unique adapter names in the log."""
        entries = self.get_all()
        seen = set()
        adapters = []
        for e in entries:
            name = e.get("adapter", "unknown")
            if name not in seen:
                seen.add(name)
                adapters.append(name)
        return adapters

    def count(self) -> int:
        """Return total number of logged entries."""
        return len(self.get_all())

    def clear(self) -> int:
        """Clear all entries. Returns number of entries removed."""
        with self._lock:
            entries = self._read_all()
            count = len(entries)
            self._write_all([])
        return count
