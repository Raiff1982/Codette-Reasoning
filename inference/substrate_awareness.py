#!/usr/bin/env python3
"""Substrate-Aware Cognition — Codette adjusts reasoning based on her own system state.

Like biological cognition: we don't reason the same way when exhausted.
Codette now modulates her behavior based on real-time resource state.

Three systems:
1. SubstrateMonitor — measures CPU, memory, inference load, adapter health
2. HealthAwareRouter — adjusts Phase 6/7 routing based on system pressure
3. CocoonStateEnricher — stamps system state onto every cocoon memory

Usage:
    monitor = SubstrateMonitor()
    state = monitor.snapshot()
    # state = {"pressure": 0.65, "level": "moderate", ...}

    router = HealthAwareRouter(monitor)
    adjusted = router.adjust_routing(complexity, max_adapters)
    # Under pressure: COMPLEX -> MEDIUM, max_adapters 3 -> 2

    enricher = CocoonStateEnricher(monitor)
    metadata = enricher.enrich(existing_metadata)
    # Adds: {"substrate": {"pressure": 0.65, "memory_pct": 78, ...}}
"""

import os
import time
import psutil
from typing import Dict, Optional, Tuple
from collections import deque


class SubstrateMonitor:
    """Real-time system state measurement.

    Measures actual hardware/software state — not estimates.
    Returns a pressure score (0.0 = idle, 1.0 = maxed out).
    """

    def __init__(self):
        self._history = deque(maxlen=50)  # Last 50 snapshots
        self._inference_times = deque(maxlen=20)  # Last 20 inference durations
        self._adapter_violations = {}  # adapter_name -> violation count
        self._last_snapshot = None
        self._last_snapshot_time = 0
        self._cache_ttl = 2.0  # Don't re-measure more than every 2s

    def snapshot(self) -> Dict:
        """Take a full system state snapshot.

        Returns dict with:
            pressure: float 0-1 (overall system pressure)
            level: str (idle/low/moderate/high/critical)
            memory_pct: float (RAM usage percentage)
            memory_available_gb: float
            cpu_pct: float (CPU usage percentage)
            process_memory_gb: float (this Python process)
            inference_avg_ms: float (recent average inference time)
            adapter_violation_rate: float (0-1, how often adapters violate constraints)
            timestamp: float
        """
        now = time.time()

        # Cache to avoid hammering psutil
        if self._last_snapshot and (now - self._last_snapshot_time) < self._cache_ttl:
            return self._last_snapshot

        try:
            vm = psutil.virtual_memory()
            memory_pct = vm.percent
            memory_available_gb = vm.available / (1024 ** 3)
        except Exception:
            memory_pct = 0.0
            memory_available_gb = 16.0

        try:
            cpu_pct = psutil.cpu_percent(interval=0.1)
        except Exception:
            cpu_pct = 0.0

        try:
            proc = psutil.Process(os.getpid())
            process_memory_gb = proc.memory_info().rss / (1024 ** 3)
        except Exception:
            process_memory_gb = 0.0

        # Inference timing
        if self._inference_times:
            inference_avg_ms = sum(self._inference_times) / len(self._inference_times)
        else:
            inference_avg_ms = 0.0

        # Adapter violation rate
        total_violations = sum(self._adapter_violations.values())
        total_inferences = max(len(self._inference_times), 1)
        violation_rate = min(1.0, total_violations / (total_inferences * 2))

        # Compute composite pressure (0-1)
        pressure = self._compute_pressure(
            memory_pct, cpu_pct, process_memory_gb,
            inference_avg_ms, violation_rate
        )

        # Classify level
        if pressure < 0.2:
            level = "idle"
        elif pressure < 0.4:
            level = "low"
        elif pressure < 0.6:
            level = "moderate"
        elif pressure < 0.8:
            level = "high"
        else:
            level = "critical"

        snapshot = {
            "pressure": round(pressure, 3),
            "level": level,
            "memory_pct": round(memory_pct, 1),
            "memory_available_gb": round(memory_available_gb, 2),
            "cpu_pct": round(cpu_pct, 1),
            "process_memory_gb": round(process_memory_gb, 2),
            "inference_avg_ms": round(inference_avg_ms, 1),
            "adapter_violation_rate": round(violation_rate, 3),
            "timestamp": now,
        }

        self._history.append(snapshot)
        self._last_snapshot = snapshot
        self._last_snapshot_time = now

        return snapshot

    def record_inference(self, duration_ms: float):
        """Record an inference duration for trend tracking."""
        self._inference_times.append(duration_ms)

    def record_violation(self, adapter: str):
        """Record a constraint violation for an adapter."""
        self._adapter_violations[adapter] = self._adapter_violations.get(adapter, 0) + 1

    def get_adapter_health(self) -> Dict[str, float]:
        """Get per-adapter health scores based on violation history.

        Returns: {adapter_name: health_score} where 1.0 = perfect, 0.0 = always violating
        """
        if not self._adapter_violations:
            return {}

        max_v = max(self._adapter_violations.values()) if self._adapter_violations else 1
        return {
            adapter: round(1.0 - (count / max(max_v * 2, 1)), 3)
            for adapter, count in self._adapter_violations.items()
        }

    def trend(self) -> str:
        """Return pressure trend: rising, falling, or stable."""
        if len(self._history) < 3:
            return "stable"

        recent = [s["pressure"] for s in list(self._history)[-5:]]
        if len(recent) < 2:
            return "stable"

        delta = recent[-1] - recent[0]
        if delta > 0.1:
            return "rising"
        elif delta < -0.1:
            return "falling"
        return "stable"

    def _compute_pressure(self, mem_pct, cpu_pct, proc_mem_gb,
                          inference_avg_ms, violation_rate) -> float:
        """Weighted composite pressure score.

        Weights reflect what actually impacts Codette's reasoning quality:
        - Memory is king (model + adapters live in RAM)
        - Inference time indicates GPU/CPU saturation
        - Violation rate indicates adapter instability
        """
        # Memory pressure (0-1): >90% = critical
        mem_p = min(1.0, max(0.0, (mem_pct - 40) / 55))

        # Process memory: >6GB is heavy for 8B model + adapters
        proc_p = min(1.0, max(0.0, (proc_mem_gb - 3.0) / 5.0))

        # CPU pressure
        cpu_p = min(1.0, cpu_pct / 100.0)

        # Inference latency: >60s per query = stressed
        inf_p = min(1.0, max(0.0, (inference_avg_ms - 5000) / 55000))

        # Weighted blend
        pressure = (
            0.35 * mem_p +
            0.20 * proc_p +
            0.15 * cpu_p +
            0.15 * inf_p +
            0.15 * violation_rate
        )

        return min(1.0, max(0.0, pressure))


class HealthAwareRouter:
    """Adjusts Phase 6/7 routing decisions based on system health.

    Under pressure:
    - Downgrade COMPLEX -> MEDIUM (fewer adapters, less memory)
    - Reduce max_adapters
    - Prefer adapters with better health scores
    - Skip debate rounds

    Under low load:
    - Allow full COMPLEX debate
    - Extra adapters welcome
    """

    def __init__(self, monitor: SubstrateMonitor):
        self.monitor = monitor

    def adjust_routing(self, complexity, max_adapters: int) -> Tuple:
        """Adjust routing based on current system pressure.

        Args:
            complexity: QueryComplexity enum
            max_adapters: Requested max adapters

        Returns:
            (adjusted_complexity, adjusted_max_adapters, adjustments_made: list)
        """
        state = self.monitor.snapshot()
        pressure = state["pressure"]
        level = state["level"]
        adjustments = []

        # Import here to avoid circular
        try:
            from reasoning_forge.query_classifier import QueryComplexity
        except ImportError:
            return complexity, max_adapters, []

        adjusted_complexity = complexity
        adjusted_max = max_adapters

        if level == "critical":
            # Emergency mode: everything becomes SIMPLE, 1 adapter
            if complexity != QueryComplexity.SIMPLE:
                adjusted_complexity = QueryComplexity.SIMPLE
                adjustments.append(f"DOWNGRADED {complexity.name}->SIMPLE (pressure={pressure:.2f}, critical)")
            adjusted_max = 1
            adjustments.append("max_adapters->1 (critical pressure)")

        elif level == "high":
            # Stressed: COMPLEX -> MEDIUM, cap at 2
            if complexity == QueryComplexity.COMPLEX:
                adjusted_complexity = QueryComplexity.MEDIUM
                adjustments.append(f"DOWNGRADED COMPLEX->MEDIUM (pressure={pressure:.2f})")
            adjusted_max = min(adjusted_max, 2)
            if adjusted_max < max_adapters:
                adjustments.append(f"max_adapters {max_adapters}->{adjusted_max} (high pressure)")

        elif level == "moderate":
            # Slightly stressed: cap COMPLEX adapters at 2
            if complexity == QueryComplexity.COMPLEX:
                adjusted_max = min(adjusted_max, 2)
                if adjusted_max < max_adapters:
                    adjustments.append(f"max_adapters {max_adapters}->{adjusted_max} (moderate pressure)")

        # Under idle/low: no changes, full capacity available

        return adjusted_complexity, adjusted_max, adjustments

    def rank_adapters(self, candidates: list) -> list:
        """Re-rank adapter candidates based on health scores.

        Adapters with more constraint violations get ranked lower.
        """
        health = self.monitor.get_adapter_health()
        if not health:
            return candidates  # No data yet

        def score(adapter_name):
            return health.get(adapter_name, 1.0)

        return sorted(candidates, key=score, reverse=True)

    def should_skip_debate(self) -> bool:
        """Under high pressure, skip multi-round debate entirely."""
        state = self.monitor.snapshot()
        return state["level"] in ("high", "critical")


class CocoonStateEnricher:
    """Stamps system state onto cocoon memories.

    Every cocoon now knows the conditions under which it was created:
    - pressure level, memory usage, inference speed
    - adapter health at time of storage

    Future sessions can weight cocoons by reliability:
    - Stressed cocoons (high pressure) get less trust
    - Stable cocoons (low pressure, no violations) get more trust
    """

    def __init__(self, monitor: SubstrateMonitor):
        self.monitor = monitor

    def enrich(self, metadata: Optional[Dict] = None) -> Dict:
        """Add substrate state to cocoon metadata.

        Args:
            metadata: Existing metadata dict (will be extended)

        Returns:
            Enriched metadata with 'substrate' key
        """
        if metadata is None:
            metadata = {}

        state = self.monitor.snapshot()

        metadata["substrate"] = {
            "pressure": state["pressure"],
            "level": state["level"],
            "memory_pct": state["memory_pct"],
            "process_memory_gb": state["process_memory_gb"],
            "inference_avg_ms": state["inference_avg_ms"],
            "trend": self.monitor.trend(),
            "timestamp": state["timestamp"],
        }

        return metadata

    @staticmethod
    def cocoon_reliability(cocoon_metadata: Dict) -> float:
        """Score a cocoon's reliability based on substrate conditions when created.

        Returns:
            0.0-1.0 reliability score
            1.0 = created under ideal conditions (low pressure, stable)
            0.0 = created under critical pressure (unreliable)
        """
        substrate = cocoon_metadata.get("substrate", {})
        if not substrate:
            return 0.7  # Unknown conditions, assume moderate

        pressure = substrate.get("pressure", 0.5)
        trend = substrate.get("trend", "stable")

        # Base reliability = inverse of pressure
        reliability = 1.0 - pressure

        # Bonus for stable conditions
        if trend == "stable":
            reliability = min(1.0, reliability + 0.05)
        elif trend == "rising":
            reliability = max(0.0, reliability - 0.1)  # Was getting worse

        return round(reliability, 3)
