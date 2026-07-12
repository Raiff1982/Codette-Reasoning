"""
Codette RC+xi Framework — Router Self-Tuning Optimizer.

Online hill-climb-with-noise over the router's own thresholds and per-adapter
boosts, driven by a per-response quality score built from MEASURED signals
(coherence Gamma and epistemic tension Xi, which the server already emits per
turn via LiveCognitionState). Keeps the best-known configuration, occasionally
reverts, and perturbs one parameter per step. Fully reversible and serializable.

Honest-naming note: this is a stochastic hill-climber with a temperature-decayed
revert probability — NOT textbook Metropolis simulated annealing (it never
accepts a strictly-worse candidate to escape a local optimum; it only reverts).
The behavior is deliberate for gentle live nudging. See optimizer_shadow.py for
the shadow-mode harness that observes proposed tunings without applying them.

Created by Jonathan Harrison (Raiff1982) / Raiff's Bits LLC.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

# ---------------------------------------------------------------------------
# High-Integrity Telemetry & Parametric Abstractions
# ---------------------------------------------------------------------------

@dataclass
class QualitySignal:
    """
    A telemetry evaluation window packet capturing performance metrics from a Codette response.
    Maps localized convergence outcomes directly against the 128D semantic space.
    """
    timestamp: float
    adapter: str
    coherence: float          # Phase coherence at response time (Gamma Index)
    tension: float            # Epistemic tension at response time (Xi Index)
    productivity: float       # Tension productivity score (gradient trajectory alignment)
    response_length: int      # Measured size in tokens/characters
    multi_perspective: bool    # Boolean flag indicating multi-perspective LoRA routing activation
    user_continued: bool = True  # Binary engagement indicator tracking continuous context flow


@dataclass
class TuningState:
    """
    Current operating bounds for the RC+xi Dynamic Core Framework.
    Tracks state transitions safely across reversible parameters.
    """
    # Router Threshold Metrics
    confidence_threshold: float = 0.4
    multi_perspective_threshold: float = 0.6

    # Spiderweb Topology Matrix Configurations
    contraction_ratio: float = 0.85
    tension_threshold: float = 0.15
    entanglement_alpha: float = 0.9

    # Dynamic Weight Allocations (0.0 to 0.3 bonus matrix space)
    adapter_boosts: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes current operational bounds into standard system primitives."""
        return {
            "confidence_threshold": self.confidence_threshold,
            "multi_perspective_threshold": self.multi_perspective_threshold,
            "contraction_ratio": self.contraction_ratio,
            "tension_threshold": self.tension_threshold,
            "entanglement_alpha": self.entanglement_alpha,
            "adapter_boosts": dict(self.adapter_boosts),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TuningState:
        """Hydrates structural configuration limits safely from historical files."""
        state = cls()
        state.confidence_threshold = float(data.get("confidence_threshold", 0.4))
        state.multi_perspective_threshold = float(data.get("multi_perspective_threshold", 0.6))
        state.contraction_ratio = float(data.get("contraction_ratio", 0.85))
        state.tension_threshold = float(data.get("tension_threshold", 0.15))
        state.entanglement_alpha = float(data.get("entanglement_alpha", 0.9))
        
        boosts = data.get("adapter_boosts", {})
        state.adapter_boosts = {str(k): float(v) for k, v in boosts.items()}
        return state

    def clone(self) -> TuningState:
        """Performs deep field allocations to prevent pointer crossover errors during mutation loops."""
        return TuningState(
            confidence_threshold=self.confidence_threshold,
            multi_perspective_threshold=self.multi_perspective_threshold,
            contraction_ratio=self.contraction_ratio,
            tension_threshold=self.tension_threshold,
            entanglement_alpha=self.entanglement_alpha,
            adapter_boosts=dict(self.adapter_boosts)
        )


@dataclass
class OptimizationStep:
    """A concrete ledger tracking structural parameters altered by the self-tuning engine."""
    timestamp: float
    parameter: str
    old_value: float
    new_value: float
    reason: str
    quality_score: float


# ---------------------------------------------------------------------------
# QuantumOptimizer Core Execution Framework
# ---------------------------------------------------------------------------

class QuantumOptimizer:
    """
    Stochastic Optimization Engine running Simulated Annealing with parameter momentum
    to adaptively stabilize multi-perspective integration arrays across response cycles.
    """

    def __init__(
        self,
        learning_rate: float = 0.02,
        temperature: float = 0.5,
        cooling_rate: float = 0.995,
        min_signals_before_tuning: int = 5,
    ):
        self.learning_rate: float = learning_rate
        self.temperature: float = temperature
        self.cooling_rate: float = cooling_rate
        self.min_signals: int = min_signals_before_tuning

        self.state: TuningState = TuningState()
        self.best_state: TuningState = TuningState()
        self.best_score: float = 0.0

        self.signals: List[QualitySignal] = []
        self.history: List[OptimizationStep] = []

        self._quality_window: List[float] = []
        self._window_size: int = 20

    def record_signal(self, signal: QualitySignal) -> None:
        """Appends active runtime diagnostics to evaluation horizons, evaluating optimization loops."""
        self.signals.append(signal)

        # Calculate composite objective quality scalar
        quality = self._compute_quality(signal)
        self._quality_window.append(quality)
        if len(self._quality_window) > self._window_size:
            self._quality_window.pop(0)

        # Trigger self-tuning optimization logic gates once buffer bounds are met
        if len(self.signals) >= self.min_signals:
            self._maybe_tune()

    def _compute_quality(self, signal: QualitySignal) -> float:
        """
        Computes the composite objective metric score (Bounded [0.0, 1.0]).
        Weights Profile:
          - Phase Coherence (Γ): 30% (Measures structural framework parsing)
          - Tension Productivity Index: 30% (Tracks efficient state convergence solutions)
          - Ideal Epistemic Tension Band (Sweet Spot ~0.4): 20%
          - Dialogue Continuation Variable: 20%
        """
        # Formulate non-linear penalty for systemic divergence outside target 0.4 zone
        tension_error = abs(signal.tension - 0.4)
        tension_score = 1.0 - (2.0 * tension_error)
        tension_score = max(0.0, tension_score)

        continuation_bonus = 1.0 if signal.user_continued else 0.0

        composite = (
            (0.30 * signal.coherence) +
            (0.30 * signal.productivity) +
            (0.20 * tension_score) +
            (0.20 * continuation_bonus)
        )
        return float(min(max(composite, 0.0), 1.0))

    def _maybe_tune(self) -> None:
        """Executes a stochastic exploration step using standard simulated annealing transitions."""
        if len(self._quality_window) < 3:
            return

        current_quality = float(sum(self._quality_window) / len(self._quality_window))

        # Update absolute best matrix configuration bounds if performance improves
        if current_quality > self.best_score:
            self.best_score = current_quality
            self.best_state = self.state.clone()
        elif self.temperature > 0.01:
            # Temperature-decayed revert probability (NOT true Metropolis accept:
            # we only ever revert toward best, never accept a worse candidate).
            delta = self.best_score - current_quality
            accept_prob = math.exp(-delta / max(self.temperature, 0.001))
            
            if random.random() > accept_prob:
                # Reject poor paths and revert properties back to best known matrix positions
                self._revert_to_best()
                return

        # Decay temperature fields uniformly across iterations
        self.temperature *= self.cooling_rate

        # Execute single parameter modulation path adjustments
        self._tune_one_parameter(current_quality)

    def _tune_one_parameter(self, current_quality: float) -> None:
        """Alters a single targeting coefficient base determined by diagnostic historical metrics."""
        recent = self.signals[-10:]
        if not recent:
            return

        avg_coherence = sum(s.coherence for s in recent) / len(recent)
        avg_tension = sum(s.tension for s in recent) / len(recent)
        avg_productivity = sum(s.productivity for s in recent) / len(recent)
        multi_ratio = sum(1 for s in recent if s.multi_perspective) / len(recent)

        param = ""
        old_val = 0.0
        new_val = 0.0
        reason = ""

        if avg_coherence < 0.5:
            # Low coherence structural trend -> scale contraction dampening higher
            param = "contraction_ratio"
            old_val = self.state.contraction_ratio
            delta = self.learning_rate * (0.7 - avg_coherence)
            new_val = min(0.98, max(0.5, old_val + delta))
            reason = f"Low coherence ({avg_coherence:.2f}), tightening propagation bounds"
            self.state.contraction_ratio = new_val

        elif avg_tension < 0.2 and avg_productivity < 0.3:
            # Inactive tension systems -> expand processing space limits to multi-agent layers
            param = "multi_perspective_threshold"
            old_val = self.state.multi_perspective_threshold
            new_val = max(0.3, old_val - self.learning_rate)
            reason = f"Low tension/productivity ({avg_tension:.2f}/{avg_productivity:.2f}), broadening adapter layers"
            self.state.multi_perspective_threshold = new_val

        elif avg_tension > 0.7:
            # Destabilizing tension overheads detected -> step up acceptance boundaries
            param = "tension_threshold"
            old_val = self.state.tension_threshold
            new_val = min(0.5, old_val + (self.learning_rate * 0.5))
            reason = f"High tension ({avg_tension:.2f}), relaxing convergence constraints"
            self.state.tension_threshold = new_val

        elif multi_ratio > 0.8 and avg_productivity < 0.4:
            # Over-routing agents without productive convergence outcomes -> restrict threshold barriers
            param = "multi_perspective_threshold"
            old_val = self.state.multi_perspective_threshold
            new_val = min(0.8, old_val + self.learning_rate)
            reason = f"Multi-perspective saturation ({multi_ratio:.0%}) with sub-optimal alignment"
            self.state.multi_perspective_threshold = new_val

        elif len(recent) >= 5:
            # Award incremental boosts only to ATTRIBUTABLE adapters. Synthesis
            # turns aren't produced by one adapter, so they carry a non-
            # attributable label ("synthesis"/"unknown") and are excluded — else
            # the optimizer boosts a phantom channel (caught in shadow review).
            _NON_ATTRIBUTABLE = {"synthesis", "unknown", ""}
            adapter_scores: Dict[str, List[float]] = {}
            for s in recent:
                if s.adapter in _NON_ATTRIBUTABLE:
                    continue
                q = self._compute_quality(s)
                adapter_scores.setdefault(s.adapter, []).append(q)

            if adapter_scores:
                best_adapter = max(
                    adapter_scores,
                    key=lambda k: sum(adapter_scores[k]) / len(adapter_scores[k])
                )
                param = f"adapter_boost_{best_adapter}"
                old_val = self.state.adapter_boosts.get(best_adapter, 0.0)
                new_val = min(0.3, old_val + (self.learning_rate * 0.5))
                self.state.adapter_boosts[best_adapter] = new_val
                reason = f"Boosting high-integrity adapter vector channel: {best_adapter}"

        # If an explicit structural parameter update was committed, update the operational history tracking ledgers
        if param:
            self.history.append(OptimizationStep(
                timestamp=time.time(),
                parameter=param,
                old_value=float(old_val),
                new_value=float(new_val),
                reason=reason,
                quality_score=current_quality
            ))

    def _revert_to_best(self) -> None:
        """Restores network operations back to the verified optimal tuning boundaries configuration."""
        self.state = self.best_state.clone()

    def get_adapter_boost(self, adapter_name: str) -> float:
        """Fetches dynamic scalar adjustments assigned to individual perspective paths."""
        return float(self.state.adapter_boosts.get(adapter_name, 0.0))

    def get_tuning_report(self) -> Dict[str, Any]:
        """Provides high-resolution telemetry status for configuration oversight logs."""
        recent_quality = (
            sum(self._quality_window) / len(self._quality_window)
            if self._quality_window else 0.0
        )
        return {
            "current_state": self.state.to_dict(),
            "best_score": float(round(self.best_score, 4)),
            "current_quality": float(round(recent_quality, 4)),
            "temperature": float(round(self.temperature, 4)),
            "total_signals": len(self.signals),
            "recent_adjustments": [
                {
                    "param": h.parameter,
                    "old": float(round(h.old_value, 4)),
                    "new": float(round(h.new_value, 4)),
                    "reason": h.reason,
                }
                for h in self.history[-5:]
            ],
        }

    # -- Persistence & System State Hydration Layers -----------------------

    def to_dict(self) -> Dict[str, Any]:
        """Packages critical system matrix tuning trends securely for framework database writing."""
        return {
            "state": self.state.to_dict(),
            "best_score": self.best_score,
            "temperature": self.temperature,
            "quality_window": list(self._quality_window),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> QuantumOptimizer:
        """Restores framework parameters cleanly back to active execution loops."""
        opt = cls()
        if "state" in data:
            opt.state = TuningState.from_dict(data["state"])
            opt.best_state = TuningState.from_dict(data["state"])
        opt.best_score = float(data.get("best_score", 0.0))
        opt.temperature = float(data.get("temperature", 0.5))
        opt._quality_window = [float(v) for v in data.get("quality_window", [])]
        return opt