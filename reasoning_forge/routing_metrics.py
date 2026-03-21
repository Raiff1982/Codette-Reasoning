"""Routing Metrics — Observability for Adaptive Router (Phase 5)

Tracks adapter routing decisions, memory boost application, and performance
metrics to enable monitoring and fine-tuning of the Phase 5 integration.

Exposes metrics for:
- Adapter selection frequency and confidence
- Memory boost hit rate (% of queries with memory boost applied)
- Router strategy selection
- Confidence distribution before/after memory boost
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AdapterSelectionRecord:
    """Record of a single routing decision."""
    timestamp: float
    query_preview: str                    # First 60 chars of query
    primary_adapter: str
    secondary_adapters: List[str]
    strategy: str                         # "keyword", "llm", "hybrid"
    confidence_before_boost: float        # Base confidence from keyword/llm
    confidence_after_boost: float         # After memory weighting applied
    memory_boost_applied: bool
    boost_magnitude: float = 0.0          # How much confidence changed

    def to_dict(self) -> Dict:
        """Serialize to dict for JSON export."""
        return {
            "timestamp": self.timestamp,
            "query_preview": self.query_preview,
            "primary_adapter": self.primary_adapter,
            "secondary_adapters": self.secondary_adapters,
            "strategy": self.strategy,
            "confidence_before_boost": round(self.confidence_before_boost, 3),
            "confidence_after_boost": round(self.confidence_after_boost, 3),
            "memory_boost_applied": self.memory_boost_applied,
            "boost_magnitude": round(self.boost_magnitude, 3),
        }


class RoutingMetrics:
    """Track and report on adapter routing decisions.

    Maintains rolling statistics on:
    - Which adapters are selected (frequency, as primary vs secondary)
    - Confidence scores (average, distribution)
    - Memory boost effectiveness (hit rate, average boost amount)
    - Router strategy usage
    - Cold start scenarios (no memory for adapter)
    """

    # Maximum records to retain (rolling window to prevent memory bloat)
    MAX_SELECTION_RECORDS = 1000

    def __init__(self):
        self.total_queries: int = 0

        # Use deque with maxlen for bounded memory
        from collections import deque
        self.selection_records: deque = deque(maxlen=self.MAX_SELECTION_RECORDS)

        # Per-adapter metrics
        self.adapter_selection_counts: Dict[str, int] = {}
        self.adapter_primary_count: Dict[str, int] = {}
        self.adapter_secondary_count: Dict[str, int] = {}
        self.adapter_avg_confidence: Dict[str, float] = {}
        self.adapter_boost_hits: Dict[str, int] = {}
        self.adapter_avg_boost_magnitude: Dict[str, float] = {}

        # Strategy metrics
        self.strategy_usage: Dict[str, int] = {
            "keyword": 0,
            "llm": 0,
            "hybrid": 0,
            "forced": 0,
        }

        # Memory metrics
        self.memory_boost_count: int = 0
        self.cold_start_queries: int = 0

    def record_route(self, record: AdapterSelectionRecord) -> None:
        """Record a routing decision.

        Args:
            record: AdapterSelectionRecord with all routing details
        """
        self.total_queries += 1
        self.selection_records.append(record)

        # Update adapter selection counts
        self.adapter_selection_counts[record.primary_adapter] = \
            self.adapter_selection_counts.get(record.primary_adapter, 0) + 1
        self.adapter_primary_count[record.primary_adapter] = \
            self.adapter_primary_count.get(record.primary_adapter, 0) + 1

        for secondary in record.secondary_adapters:
            self.adapter_selection_counts[secondary] = \
                self.adapter_selection_counts.get(secondary, 0) + 1
            self.adapter_secondary_count[secondary] = \
                self.adapter_secondary_count.get(secondary, 0) + 1

        # Update confidence metrics
        self._update_adapter_confidence(record.primary_adapter, record.confidence_after_boost)

        # Update memory boost metrics
        if record.memory_boost_applied:
            self.memory_boost_count += 1
            self.adapter_boost_hits[record.primary_adapter] = \
                self.adapter_boost_hits.get(record.primary_adapter, 0) + 1
            self.adapter_avg_boost_magnitude[record.primary_adapter] = \
                record.boost_magnitude

        # Update strategy metrics
        self.strategy_usage[record.strategy] = self.strategy_usage.get(record.strategy, 0) + 1

    def _update_adapter_confidence(self, adapter: str, confidence: float) -> None:
        """Update running average confidence for adapter."""
        if adapter not in self.adapter_avg_confidence:
            self.adapter_avg_confidence[adapter] = confidence
        else:
            current_count = self.adapter_selection_counts.get(adapter, 1)
            old_avg = self.adapter_avg_confidence[adapter]
            new_avg = (old_avg * (current_count - 1) + confidence) / current_count
            self.adapter_avg_confidence[adapter] = new_avg

    def get_adapter_stats(self, adapter: str) -> Dict:
        """Get comprehensive stats for a single adapter.

        Returns:
            Dict with selection count, hit rate, avg confidence, etc.
        """
        selections = self.adapter_selection_counts.get(adapter, 0)
        boosts = self.adapter_boost_hits.get(adapter, 0)

        return {
            "adapter": adapter,
            "total_selections": selections,
            "primary_selections": self.adapter_primary_count.get(adapter, 0),
            "secondary_selections": self.adapter_secondary_count.get(adapter, 0),
            "avg_confidence": round(self.adapter_avg_confidence.get(adapter, 0.0), 3),
            "memory_boost_hits": boosts,
            "memory_boost_rate": round(boosts / max(selections, 1), 3),
            "avg_boost_magnitude": round(self.adapter_avg_boost_magnitude.get(adapter, 0.0), 3),
        }

    def get_summary(self) -> Dict:
        """Return comprehensive summary of routing metrics.

        Returns:
            Dict with overall statistics and per-adapter breakdown
        """
        if self.total_queries == 0:
            return {"total_queries": 0, "status": "no data"}

        # Compute averages
        total_selections = sum(self.adapter_selection_counts.values())
        all_confidences = [r.confidence_after_boost for r in self.selection_records]
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

        # Top adapters
        top_adapters = sorted(
            self.adapter_selection_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        # Memory boost rate
        memory_boost_rate = self.memory_boost_count / max(self.total_queries, 1)

        # Most used strategy
        top_strategy = max(self.strategy_usage.items(), key=lambda x: x[1])[0]

        return {
            "total_queries": self.total_queries,
            "total_adapter_selections": total_selections,
            "avg_confidence": round(avg_confidence, 3),
            "confidence_range": (
                round(min(all_confidences), 3) if all_confidences else 0.0,
                round(max(all_confidences), 3) if all_confidences else 1.0,
            ),
            "top_adapters": [
                {
                    "adapter": name,
                    "count": count,
                    "percentage": round(count / max(total_selections, 1), 3),
                }
                for name, count in top_adapters
            ],
            "memory_boost_rate": round(memory_boost_rate, 3),
            "memory_boosts_applied": self.memory_boost_count,
            "strategy_distribution": dict(self.strategy_usage),
            "primary_strategy": top_strategy,
            "cold_start_queries": self.cold_start_queries,
            "adapter_stats": {
                adapter: self.get_adapter_stats(adapter)
                for adapter in self.adapter_selection_counts.keys()
            },
        }

    def get_recent_routes(self, limit: int = 10) -> List[Dict]:
        """Return recent routing decisions for debugging.

        Args:
            limit: Max records to return

        Returns:
            List of recent routing records (most recent first)
        """
        # Convert deque to list to enable slicing, then reverse for most-recent-first
        records_list = list(self.selection_records)
        return [
            {
                "timestamp": r.timestamp,
                "query": r.query_preview,
                "primary": r.primary_adapter,
                "secondary": r.secondary_adapters,
                "confidence": round(r.confidence_after_boost, 3),
                "strategy": r.strategy,
                "boost_applied": r.memory_boost_applied,
            }
            for r in records_list[-limit:][::-1]  # Most recent first
        ]

    def reset(self) -> None:
        """Clear all metrics (for testing or new session)."""
        self.__init__()

    @staticmethod
    def create_record(
        query: str,
        primary_adapter: str,
        secondary_adapters: List[str],
        strategy: str,
        confidence_before_boost: float,
        confidence_after_boost: float,
        memory_boost_applied: bool,
    ) -> AdapterSelectionRecord:
        """Factory method to create a routing record.

        Args:
            query: The user's query (will be truncated to first 60 chars)
            primary_adapter: Selected primary adapter name
            secondary_adapters: List of secondary adapters
            strategy: Routing strategy used
            confidence_before_boost: Base confidence score
            confidence_after_boost: Confidence after memory boost (if applied)
            memory_boost_applied: Whether memory weighting was applied

        Returns:
            AdapterSelectionRecord ready to log
        """
        boost_magnitude = confidence_after_boost - confidence_before_boost

        return AdapterSelectionRecord(
            timestamp=time.time(),
            query_preview=query[:60] + ("..." if len(query) > 60 else ""),
            primary_adapter=primary_adapter,
            secondary_adapters=secondary_adapters,
            strategy=strategy,
            confidence_before_boost=confidence_before_boost,
            confidence_after_boost=confidence_after_boost,
            memory_boost_applied=memory_boost_applied,
            boost_magnitude=boost_magnitude,
        )
