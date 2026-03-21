"""Memory-Weighted Adapter Selection for Phase 2

Learns which adapters perform best from historical memory data,
then weights adapter selection based on coherence, conflict success,
and recency of past interactions.

Author: Claude Code
Phase: 2 (Closed-Loop Learning)
"""

import time
import math
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple


# ================================================================
# Shared Utility Functions
# ================================================================

def clamp_adapter_weight(weight: float, min_val: float = 0.0, max_val: float = 2.0) -> float:
    """Clamp adapter weight to valid range.

    Prevents unbounded amplification and ensures all weights stay within
    [min_val, max_val] bounds, typically [0, 2.0].

    Args:
        weight: Weight value to clamp
        min_val: Minimum allowed weight (default 0.0)
        max_val: Maximum allowed weight (default 2.0)

    Returns:
        Clamped weight in [min_val, max_val]
    """
    return max(min_val, min(max_val, weight))


@dataclass
class ReinforcementConfig:
    """Tunable coefficients for adapter reinforcement learning (Phase 4).

    These control how much adapter weights are boosted/penalized based on
    conflict resolution performance during debate rounds.
    """
    boost_successful: float = 0.08        # Boost when resolution_rate > 40%
    penalize_failed: float = 0.08         # Penalize when resolution_type == "worsened"
    reward_soft_consensus: float = 0.03   # Partial reward for soft_consensus

    @classmethod
    def from_dict(cls, d: Dict) -> "ReinforcementConfig":
        """Create from config dict with defaults for missing keys."""
        return cls(**{k: v for k, v in d.items()
                     if k in cls.__dataclass_fields__})

    def to_dict(self) -> Dict:
        """Export as dict for serialization."""
        return asdict(self)


@dataclass
class AdapterWeight:
    """Performance metrics for a single adapter based on historical memory."""

    adapter: str                    # Adapter name (e.g., "newton", "davinci")
    base_coherence: float          # Mean coherence [0, 1] from all past uses
    conflict_success_rate: float   # % of "tension"-tagged memories with coherence > 0.7
    interaction_count: int         # How many memories for this adapter
    recency_score: float           # Recent memories weighted higher [0.1, 1.0]
    weight: float                  # Final composite weight [0, 2.0]

    def __str__(self) -> str:
        return (f"AdapterWeight(adapter={self.adapter}, "
                f"coherence={self.base_coherence:.3f}, "
                f"conflict_success={self.conflict_success_rate:.1%}, "
                f"interactions={self.interaction_count}, "
                f"weight={self.weight:.3f})")


class MemoryWeighting:
    """
    Score adapter performance and weight selection decisions.

    Aggregates memory cocoons per adapter, computes weights based on:
    - base_coherence: Mean coherence across all uses
    - conflict_success_rate: % of high-tension memories → resolved well
    - recency: Recent memories weighted higher (exponential decay, ~7 day half-life)

    Weight range [0, 2.0]:
      - 0.5: Adapter performs poorly (suppress by 50%)
      - 1.0: Average performance (neutral)
      - 2.0: Excellent adapter (boost by 100%)
    """

    def __init__(self, living_memory, update_interval_hours: float = 1.0,
                 reinforcement_config: Optional[ReinforcementConfig] = None):
        """
        Initialize memory weighting engine.

        Args:
            living_memory: LivingMemoryKernel instance with cocoons
            update_interval_hours: Recompute weights every N hours
            reinforcement_config: Phase 4 tunable coefficients (boost/penalize amounts)
        """
        self.memory = living_memory
        self.update_interval_hours = update_interval_hours
        self.reinforcement_config = reinforcement_config or ReinforcementConfig()

        self.adapter_weights: Dict[str, AdapterWeight] = {}
        self.last_updated: float = 0.0
        self._compute_weights(force_recompute=True)

    def get_reinforcement_config(self) -> Dict:
        """Return current reinforcement coefficient values for tuning."""
        return self.reinforcement_config.to_dict()

    def set_reinforcement_config(self, config_dict: Dict) -> None:
        """Update reinforcement coefficients from dict. Useful for fine-tuning."""
        self.reinforcement_config = ReinforcementConfig.from_dict(config_dict)

    def compute_weights(self, force_recompute: bool = False) -> Dict[str, float]:
        """
        Aggregate memory cocoons per adapter and compute weights.

        Weights can be used to:
        1. Boost/suppress keyword router confidence
        2. Rerank adapters during selection
        3. Explain adapter decisions

        Returns:
            Dict[adapter_name: weight_float] where weight ∈ [0, 2.0]
        """
        return self._compute_weights(force_recompute)

    def _compute_weights(self, force_recompute: bool = False) -> Dict[str, float]:
        """Compute weights for all adapters in memory."""
        # Skip if already computed recently (unless forced)
        now = time.time()
        if not force_recompute and (now - self.last_updated) < (self.update_interval_hours * 3600):
            return {a: w.weight for a, w in self.adapter_weights.items()}

        # Group cocoons by adapter
        adapter_cocoons: Dict[str, List] = {}
        if self.memory and self.memory.memories:
            for cocoon in self.memory.memories:
                if cocoon.adapter_used:
                    # Handle compound adapter names like "Newton,DaVinci"
                    adapters = [a.strip().lower() for a in cocoon.adapter_used.split(",")]
                    for adapter in adapters:
                        if adapter:
                            adapter_cocoons.setdefault(adapter, []).append(cocoon)

        # Compute weights for each adapter
        self.adapter_weights = {}

        if not adapter_cocoons:
            # No memories yet - return neutral weights
            return {}

        adapter_names = list(adapter_cocoons.keys())

        for adapter in adapter_names:
            cocoons = adapter_cocoons[adapter]

            # 1. Base coherence: mean coherence from all uses
            coherences = [c.coherence for c in cocoons if c.coherence > 0]
            base_coherence = sum(coherences) / len(coherences) if coherences else 0.5

            # 2. Conflict success rate: % of tension memories with coherence > 0.7
            tension_memories = [c for c in cocoons if c.emotional_tag == "tension"]
            if tension_memories:
                successful = sum(1 for c in tension_memories if c.coherence > 0.7)
                conflict_success_rate = successful / len(tension_memories)
            else:
                conflict_success_rate = 0.5  # No conflict history yet

            # 3. Recency score: weight recent memories higher
            #    Using exponential decay with ~7 day half-life
            recency_weights = []
            for cocoon in cocoons:
                age_hours = cocoon.age_hours()
                # exp(-age_hours / 168) = 0.5 after 1 week
                recency = math.exp(-age_hours / 168.0)
                recency_weights.append(recency)

            avg_recency = sum(recency_weights) / len(recency_weights) if recency_weights else 0.5
            recency_score = 0.1 + 0.9 * avg_recency  # Map to [0.1, 1.0]

            # 4. Composite weight: [0, 2.0]
            #    weight = 1.0 + contributions from each signal
            #    - base_coherence contributes ±0.5
            #    - conflict_success contributes ±0.3
            #    - recency contributes ±0.2
            weight = (
                1.0 +
                0.5 * (base_coherence - 0.5) * 2.0 +  # Normalize to [-0.5, 0.5]
                0.3 * (conflict_success_rate - 0.5) * 2.0 +
                0.2 * (recency_score - 0.5) * 2.0
            )

            # Clamp to [0, 2.0]
            weight = clamp_adapter_weight(weight)

            self.adapter_weights[adapter] = AdapterWeight(
                adapter=adapter,
                base_coherence=base_coherence,
                conflict_success_rate=conflict_success_rate,
                interaction_count=len(cocoons),
                recency_score=recency_score,
                weight=weight,
            )

        self.last_updated = now
        return {a: w.weight for a, w in self.adapter_weights.items()}

    def select_primary(self, conflict_type: str = "", query: str = "") -> Tuple[str, float]:
        """
        Select primary adapter for a conflict context.

        Strategy:
        1. Find adapters that historically handled this conflict_type well
           (Search memories with emotional_tag="tension" AND conflict_type in content)
        2. Rank by AdapterWeight.conflict_success_rate descending
        3. Return (adapter_name, weight)

        Args:
            conflict_type: e.g., "contradiction", "emphasis", "framework"
            query: Optional query context for semantic matching

        Returns:
            (best_adapter_name, weight_score)
        """
        if not self.adapter_weights:
            return ("", 1.0)  # No history yet

        # Find tension cocoons matching conflict_type if provided
        if conflict_type and self.memory and self.memory.memories:
            conflict_type_lower = conflict_type.lower()
            tension_cocoons = [
                c for c in self.memory.memories
                if c.emotional_tag == "tension" and conflict_type_lower in c.content.lower()
            ]

            # Score adapters by conflict success on matching memories
            if tension_cocoons:
                adapter_conflict_success = {}
                for cocoon in tension_cocoons:
                    for adapter_str in cocoon.adapter_used.split(","):
                        adapter = adapter_str.strip().lower()
                        if adapter:
                            success = cocoon.coherence > 0.7
                            adapter_conflict_success.setdefault(adapter, []).append(success)

                # Rank by success rate
                best_adapter = None
                best_score = 0.0
                for adapter, successes in adapter_conflict_success.items():
                    success_rate = sum(successes) / len(successes) if successes else 0.5
                    if success_rate > best_score:
                        best_adapter = adapter
                        best_score = success_rate

                if best_adapter and best_adapter in self.adapter_weights:
                    return (best_adapter, self.adapter_weights[best_adapter].weight)

        # Fallback: return adapter with highest overall weight
        if self.adapter_weights:
            best = max(self.adapter_weights.items(), key=lambda x: x[1].weight)
            return (best[0], best[1].weight)

        return ("", 1.0)

    def get_boosted_confidence(self, adapter: str, base_confidence: float) -> float:
        """
        Modulate keyword router confidence based on memory history.

        Formula:
            boosted = base_confidence * (1.0 + weight_modifier)
            where weight_modifier = (weight - 1.0) / 2.0  → [-0.5, +0.5]

        High-performing adapters (weight=2.0) get +50% confidence boost.
        Low-performing adapters (weight=0.0) get -50% confidence reduction.

        Args:
            adapter: Adapter name
            base_confidence: Original confidence from keyword router [0, 1]

        Returns:
            Boosted confidence, clamped to [0, 1]
        """
        if adapter not in self.adapter_weights:
            return base_confidence  # No history for this adapter

        weight = self.adapter_weights[adapter].weight

        # Convert weight [0, 2] to modifier [-0.5, +0.5]
        weight_modifier = (weight - 1.0) / 2.0

        # Apply modifier
        boosted = base_confidence * (1.0 + weight_modifier)

        # Clamp to [0, 1]
        return max(0.0, min(1.0, boosted))

    def explain_weight(self, adapter: str) -> Dict[str, float]:
        """
        Explain how weight was computed for debugging/transparency.

        Returns breakdown of coherence, conflict success, recency components.
        """
        if adapter not in self.adapter_weights:
            return {"error": f"No history for adapter '{adapter}'"}

        w = self.adapter_weights[adapter]
        return {
            "adapter": w.adapter,
            "base_coherence": w.base_coherence,
            "conflict_success_rate": w.conflict_success_rate,
            "recency_score": w.recency_score,
            "interaction_count": w.interaction_count,
            "final_weight": w.weight,
            "explanation": (
                f"Adapter '{w.adapter}' has used {w.interaction_count} times with "
                f"{w.base_coherence:.1%} avg coherence, {w.conflict_success_rate:.0%} "
                f"conflict resolution rate, and {w.recency_score:.1%} recency score. "
                f"Final weight: {w.weight:.3f} (range [0, 2.0])"
            )
        }

    def get_all_weights(self) -> Dict[str, Dict]:
        """Get detailed weight breakdown for all adapters."""
        result = {}
        for adapter, weight in self.adapter_weights.items():
            result[adapter] = {
                "weight": weight.weight,
                "coherence": weight.base_coherence,
                "conflict_success": weight.conflict_success_rate,
                "recency": weight.recency_score,
                "uses": weight.interaction_count,
            }
        return result

    def get_summary(self) -> Dict:
        """Get summary stats of adapter weighting engine."""
        if not self.adapter_weights:
            return {"message": "No memories yet, weights will initialize on first use"}

        weights = [w.weight for w in self.adapter_weights.values()]
        coherences = [w.base_coherence for w in self.adapter_weights.values()]

        return {
            "total_adapters": len(self.adapter_weights),
            "total_memories": len(self.memory.memories) if self.memory else 0,
            "avg_weight": sum(weights) / len(weights) if weights else 1.0,
            "best_adapter": max(self.adapter_weights.items(), key=lambda x: x[1].weight)[0] if self.adapter_weights else "none",
            "avg_coherence": sum(coherences) / len(coherences) if coherences else 0.0,
            "last_updated": self.last_updated,
        }

    # ========================================================================
    # Phase 4: Self-Correcting Feedback Loop
    # ========================================================================

    def boost(self, adapter: str, amount: float = 0.05):
        """Boost adapter weight for successful resolution."""
        adapter_lower = adapter.lower()
        if adapter_lower in self.adapter_weights:
            self.adapter_weights[adapter_lower].weight += amount
            # Clamp to [0, 2.0]
            self.adapter_weights[adapter_lower].weight = clamp_adapter_weight(
                self.adapter_weights[adapter_lower].weight
            )

    def penalize(self, adapter: str, amount: float = 0.05):
        """Penalize adapter weight for failed resolution."""
        adapter_lower = adapter.lower()
        if adapter_lower in self.adapter_weights:
            self.adapter_weights[adapter_lower].weight -= amount
            # Clamp to [0, 2.0]
            self.adapter_weights[adapter_lower].weight = max(
                0.0, min(2.0, self.adapter_weights[adapter_lower].weight)
            )

    def update_from_evolution(self, evolution) -> Dict[str, float]:
        """
        Update adapter weights based on conflict resolution performance.

        Reinforcement learning: boost adapters that resolved conflicts well,
        penalize those that made things worse.

        Uses coefficients from self.reinforcement_config for tuning.

        Args:
            evolution: ConflictEvolution object with resolution_rate and type

        Returns:
            Dict with boost/penalize actions taken
        """
        agents = [
            evolution.original_conflict.agent_a.lower(),
            evolution.original_conflict.agent_b.lower(),
        ]

        actions = {"boosts": [], "penalties": []}

        # Reward successful resolution (configurable threshold and amount)
        if evolution.resolution_rate > 0.4:
            for agent in agents:
                self.boost(agent, amount=self.reinforcement_config.boost_successful)
                actions["boosts"].append(agent)

        # Penalize failure (configurable)
        elif evolution.resolution_type == "worsened":
            for agent in agents:
                self.penalize(agent, amount=self.reinforcement_config.penalize_failed)
                actions["penalties"].append(agent)

        # Slight reward for soft consensus (configurable)
        elif evolution.resolution_type == "soft_consensus":
            for agent in agents:
                self.boost(agent, amount=self.reinforcement_config.reward_soft_consensus)
                actions["boosts"].append(agent)

        return actions
