"""
Codette Training Lab - Observatory System

Provides metrics logging, performance tracking, dataset quality monitoring,
and an ASCII dashboard for the Codette AI training pipeline.
"""

from observatory.metrics_logger import MetricsLogger
from observatory.performance_tracker import PerformanceTracker
from observatory.dataset_quality_monitor import DatasetQualityMonitor
from observatory.dashboard import Dashboard

__all__ = [
    "MetricsLogger",
    "PerformanceTracker",
    "DatasetQualityMonitor",
    "Dashboard",
]
