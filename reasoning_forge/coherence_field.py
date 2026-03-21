"""Coherence Field Gamma (Γ) — System Health Stabilization

Phase 5A Critical Infrastructure: Prevents three failure modes in closed-loop reasoning:

1. Weight Drift: Adapter weights concentrate; diversity collapses
2. False Convergence: System reduces conflict but converges on wrong answer
3. Feedback Lock-in: Early bad runs reinforce themselves via memory

Solution: Γ (Gamma) monitors system coherence field and injects stabilizers when
health drops below safe zones. Works alongside Phase 4 runaway detection.

Health Score:
    γ ∈ [0, 1] where:
    - γ < 0.4: System instability → inject diverse perspective
    - 0.4 ≤ γ ≤ 0.8: Healthy zone (maintain status quo)
    - γ > 0.8: Groupthink risk → force conflict pair to create productive tension

Components:
    1. Conflict Distribution: Are conflicts well-distributed across perspectives?
    2. Diversity Index: Are we using multiple perspectives or just 1-2 favorites?
    3. Tension Health: Is ξ (epistemic tension) in productive zone [0.1, 0.4]?
    4. Coherence Quality: Is coherence maintained while resolving conflicts?
"""

import time
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class InterventionType(Enum):
    """Stabilization intervention types."""
    DIVERSITY_INJECTION = "diversity_injection"    # Inject unused perspective
    CONFLICT_INJECTION = "conflict_injection"      # Force conflict pair for productive tension


@dataclass
class GammaHealthMetrics:
    """Real-time system health snapshot."""
    timestamp: float
    avg_conflict_strength: float          # Mean conflict strength [0, 1]
    perspective_diversity: float          # % unique perspectives used [0, 1]
    resolution_rate: float                # % conflicts resolved this round [0, 1]
    adapter_weight_variance: float        # Variance in adapter weights (0=equal, 1=concentrated)
    epistemic_tension: float              # ξ — productive conflict level [0, 1]
    coherence_score: float                # Ensemble coherence [0, 1]
    gamma: float                          # Composite health score [0, 1]

    def is_stable(self) -> bool:
        """Return True if system is in healthy zone."""
        return 0.4 <= self.gamma <= 0.8

    def is_collapsing(self) -> bool:
        """Return True if system shows instability signs."""
        return self.gamma < 0.4

    def is_groupthinking(self) -> bool:
        """Return True if system shows groupthink signs."""
        return self.gamma > 0.8

    @property
    def status(self) -> str:
        """Return human-readable status string."""
        if self.is_collapsing():
            return "collapsing"
        elif self.is_groupthinking():
            return "groupthinking"
        else:
            return "stable"


@dataclass
class GammaIntervention:
    """Record of stabilization intervention taken."""
    timestamp: float
    intervention_type: InterventionType            # Type-safe enum instead of string
    reason: str                                     # Why intervention was triggered
    gamma_before: float                             # Health score before
    recommended_adapter: Optional[str] = None       # Which adapter to inject
    result: Optional[str] = None                    # Outcome (filled in after execution)


class CoherenceFieldGamma:
    """Real-time system health monitor and stabilizer.

    Tracks epistemic health and intervenes when system drifts toward:
    - Monoculture (weight drift, diversity collapse)
    - False convergence (low conflict, wrong answer)
    - Instability (oscillating weights, conflicting signals)
    """

    # Maximum history size before rolling window cleanup
    MAX_HEALTH_HISTORY = 1000
    MAX_INTERVENTION_LOG = 500

    def __init__(self, memory_weighting=None, target_conflict_range: Tuple[float, float] = (0.1, 0.4)):
        """
        Args:
            memory_weighting: MemoryWeighting instance (for analyzing adapter weights)
            target_conflict_range: Ideal epistemic tension zone [low, high]
        """
        self.memory_weighting = memory_weighting
        self.target_conflict_low, self.target_conflict_high = target_conflict_range

        # Use deques with maxlen for bounded memory growth
        from collections import deque
        self.health_history: deque = deque(maxlen=self.MAX_HEALTH_HISTORY)
        self.interventions: deque = deque(maxlen=self.MAX_INTERVENTION_LOG)
        self.last_health_check = time.time()

    def compute_health(self, conflicts: List, responses: Dict, adapter_weights: Optional[Dict] = None) -> GammaHealthMetrics:
        """Compute Γ (Gamma) health score from current debate state.

        Args:
            conflicts: List of active conflicts from current round
            responses: Dict of {adapter_name: response_text} from debate
            adapter_weights: Dict of {adapter_name: weight_float} from MemoryWeighting

        Returns:
            GammaHealthMetrics with computed gamma and health indicators
        """
        # 1. CONFLICT DISTRIBUTION: Are conflicts well-distributed?
        avg_conflict_strength = 0.0
        conflict_by_adapter = {}
        if conflicts:
            for conflict in conflicts:
                avg_conflict_strength += conflict.strength if hasattr(conflict, 'strength') else 0.5
                # Track which adapters are in conflicts
                if hasattr(conflict, 'agent_a'):
                    agent = conflict.agent_a.lower()
                    conflict_by_adapter[agent] = conflict_by_adapter.get(agent, 0) + 1
                if hasattr(conflict, 'agent_b'):
                    agent = conflict.agent_b.lower()
                    conflict_by_adapter[agent] = conflict_by_adapter.get(agent, 0) + 1

            avg_conflict_strength /= len(conflicts)
        else:
            avg_conflict_strength = 0.5  # Neutral if no conflicts

        # 2. DIVERSITY INDEX: Are we using multiple perspectives?
        unique_perspectives = len(set(responses.keys())) if responses else 0
        max_perspectives = len(responses) if responses else 1
        perspective_diversity = unique_perspectives / max(max_perspectives, 1)

        # 3. RESOLUTION RATE: Did we make progress this round?
        resolution_rate = 0.5  # Default; updated externally if conflict evolution available
        if conflicts:
            resolved = sum(1 for c in conflicts if hasattr(c, 'resolution_rate') and c.resolution_rate > 0.4)
            resolution_rate = resolved / len(conflicts)

        # 4. ADAPTER WEIGHT VARIANCE: Are weights concentrated or distributed?
        adapter_weight_variance = 0.0
        if adapter_weights:
            weights = list(adapter_weights.values())
            if len(weights) > 1:
                mean_weight = sum(weights) / len(weights)
                variance = sum((w - mean_weight) ** 2 for w in weights) / len(weights)
                # Normalize variance to [0, 1] where 1 = all weight on one adapter
                max_variance = 4.0  # Empirical max for [0, 2.0] weight range
                adapter_weight_variance = min(1.0, variance / max_variance)
        else:
            adapter_weight_variance = 0.5  # Unknown = neutral

        # 5. EPISTEMIC TENSION: Is ξ in productive zone?
        # ξ = average conflict strength (should be 0.1-0.4 for productive tension)
        epistemic_tension = avg_conflict_strength
        tension_health = 1.0 - abs(epistemic_tension - 0.25) / 0.15  # Peaked at 0.25
        tension_health = max(0.0, min(1.0, tension_health))

        # 6. COHERENCE QUALITY: Placeholder (usually from ensemble coherence)
        # In integration, this will come from debate metadata
        coherence_score = 0.7  # Default; typically overridden by caller

        # 7. COMPUTE GAMMA: Composite health score
        # γ = w1 * diversity + w2 * tension_health + w3 * (1 - weight_variance) + w4 * resolution_rate
        # Weights: equal contribution from each signal
        gamma = (
            0.25 * perspective_diversity +              # More perspectives = healthier
            0.25 * tension_health +                     # Productive tension = healthier
            0.25 * (1.0 - adapter_weight_variance) +    # Distributed weights = healthier
            0.25 * resolution_rate                      # Making progress = healthier
        )

        metrics = GammaHealthMetrics(
            timestamp=time.time(),
            avg_conflict_strength=avg_conflict_strength,
            perspective_diversity=perspective_diversity,
            resolution_rate=resolution_rate,
            adapter_weight_variance=adapter_weight_variance,
            epistemic_tension=epistemic_tension,
            coherence_score=coherence_score,
            gamma=gamma,
        )

        self.health_history.append(metrics)
        return metrics

    def get_intervention(self, metrics: GammaHealthMetrics,
                        available_adapters: List[str]) -> Optional[GammaIntervention]:
        """Determine if system needs stabilization intervention.

        Args:
            metrics: Current GammaHealthMetrics
            available_adapters: List of adapter names available

        Returns:
            GammaIntervention if action needed, else None
        """
        if metrics.is_stable():
            return None  # Healthy zone — maintain

        intervention = None

        if metrics.is_collapsing():
            # γ < 0.4: System instability detected
            # Likely causes: weight drift, low diversity, unresolved conflicts
            # Fix: Inject a diverse perspective that hasn't been used recently

            unused_adapters = [a for a in available_adapters
                             if self.memory_weighting is None or
                             a not in self.memory_weighting.adapter_weights or
                             self.memory_weighting.adapter_weights[a].interaction_count == 0]

            if not unused_adapters:
                # All adapters have been used; pick lowest-weight one
                if self.memory_weighting and self.memory_weighting.adapter_weights:
                    unused_adapters = [min(self.memory_weighting.adapter_weights.items(),
                                          key=lambda x: x[1].weight)[0]]
                else:
                    unused_adapters = [available_adapters[0]]

            intervention = GammaIntervention(
                timestamp=time.time(),
                intervention_type=InterventionType.DIVERSITY_INJECTION,
                reason=f"System instability detected (γ={metrics.gamma:.2f} < 0.4). "
                       f"Diversity={metrics.perspective_diversity:.1%}, "
                       f"Weight variance={metrics.adapter_weight_variance:.1%}. "
                       f"Injecting diverse perspective to break monoculture.",
                gamma_before=metrics.gamma,
                recommended_adapter=unused_adapters[0],
            )

        elif metrics.is_groupthinking():
            # γ > 0.8: Groupthink risk
            # Too much agreement; system may have converged on wrong answer
            # Fix: Force a conflict pair to create productive tension

            # Select two adapters with highest complementary potential
            if available_adapters and len(available_adapters) >= 2:
                # Pick the two most different adapters (by weight or type)
                sorted_adapters = sorted(available_adapters)
                pair = (sorted_adapters[0], sorted_adapters[-1])  # First and last alphabetically
                intervention = GammaIntervention(
                    timestamp=time.time(),
                    intervention_type=InterventionType.CONFLICT_INJECTION,
                    reason=f"Groupthink risk detected (γ={metrics.gamma:.2f} > 0.8). "
                           f"Low conflict={metrics.epistemic_tension:.2f}, "
                           f"High diversity={metrics.perspective_diversity:.1%}. "
                           f"Forcing debate pair to create productive tension.",
                    gamma_before=metrics.gamma,
                    recommended_adapter=f"{pair[0]};{pair[1]}",  # Semicolon denotes pair
                )

        if intervention:
            self.interventions.append(intervention)

        return intervention

    def get_summary(self) -> Dict:
        """Return summary of system health trends (API-consistent name)."""
        if not self.health_history:
            return {}

        # Convert deque to list to enable slicing
        history_list = list(self.health_history)
        interventions_list = list(self.interventions)

        recent = history_list[-10:]  # Last 10 snapshots
        gammas = [m.gamma for m in recent]
        tensions = [m.epistemic_tension for m in recent]
        diversities = [m.perspective_diversity for m in recent]

        return {
            "current_gamma": recent[-1].gamma if recent else 0.0,
            "avg_gamma": sum(gammas) / len(gammas),
            "gamma_trend": "stable" if len(gammas) < 2 else (
                "improving" if gammas[-1] > gammas[0] else "degrading"
            ),
            "avg_tension": sum(tensions) / len(tensions),
            "avg_diversity": sum(diversities) / len(diversities),
            "interventions_total": len(interventions_list),
            "interventions_recent": sum(1 for i in interventions_list
                                       if time.time() - i.timestamp < 3600),  # Last hour
            "status": (
                "collapsing" if recent[-1].is_collapsing() else
                "groupthinking" if recent[-1].is_groupthinking() else
                "stable"
            ),
        }

    def export_metrics(self) -> Dict:
        """Export all health metrics for monitoring/logging."""
        # Convert deques to lists for serialization (deques can't be directly converted to JSON-safe dicts)
        health_list = list(self.health_history)
        interventions_list = list(self.interventions)

        return {
            "health_history": [
                {
                    "timestamp": m.timestamp,
                    "gamma": m.gamma,
                    "conflict": m.avg_conflict_strength,
                    "diversity": m.perspective_diversity,
                    "resolution": m.resolution_rate,
                    "weight_variance": m.adapter_weight_variance,
                }
                for m in health_list[-50:]  # Last 50 samples
            ],
            "interventions": [
                {
                    "timestamp": i.timestamp,
                    "type": i.intervention_type.value,  # Convert Enum to string for JSON
                    "reason": i.reason,
                    "gamma_before": i.gamma_before,
                    "recommended": i.recommended_adapter,
                    "result": i.result,
                }
                for i in interventions_list[-20:]  # Last 20 interventions
            ],
            "summary": self.get_summary(),
        }
