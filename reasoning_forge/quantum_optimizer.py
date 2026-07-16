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
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable

try:
    import numpy as np
except ImportError:
    np = None

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
    latency_ms: float = 0.0   # Response latency in milliseconds
    error_rate: float = 0.0   # Error rate for this response


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

    # Advanced parameters
    momentum_decay: float = 0.9
    adaptive_lr: bool = True
    exploration_rate: float = 0.1

    def to_dict(self) -> Dict[str, Any]:
        """Serializes current operational bounds into standard system primitives."""
        return {
            "confidence_threshold": self.confidence_threshold,
            "multi_perspective_threshold": self.multi_perspective_threshold,
            "contraction_ratio": self.contraction_ratio,
            "tension_threshold": self.tension_threshold,
            "entanglement_alpha": self.entanglement_alpha,
            "adapter_boosts": dict(self.adapter_boosts),
            "momentum_decay": self.momentum_decay,
            "adaptive_lr": self.adaptive_lr,
            "exploration_rate": self.exploration_rate,
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
        state.momentum_decay = float(data.get("momentum_decay", 0.9))
        state.adaptive_lr = bool(data.get("adaptive_lr", True))
        state.exploration_rate = float(data.get("exploration_rate", 0.1))

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
            adapter_boosts=dict(self.adapter_boosts),
            momentum_decay=self.momentum_decay,
            adaptive_lr=self.adaptive_lr,
            exploration_rate=self.exploration_rate,
        )

    def validate(self) -> bool:
        """Validates parameter bounds."""
        return (
            0.0 <= self.confidence_threshold <= 1.0 and
            0.0 <= self.multi_perspective_threshold <= 1.0 and
            0.5 <= self.contraction_ratio <= 0.99 and
            0.01 <= self.tension_threshold <= 0.5 and
            0.1 <= self.entanglement_alpha <= 1.0 and
            0.0 <= self.momentum_decay <= 1.0 and
            0.0 <= self.exploration_rate <= 0.5 and
            all(0.0 <= boost <= 0.3 for boost in self.adapter_boosts.values())
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
    temperature: float = 0.0
    step_type: str = "adjustment"  # "adjustment", "revert", "explore"


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
        adaptive_lr: bool = True,
        momentum_enabled: bool = True,
    ):
        self.learning_rate: float = learning_rate
        self.initial_temperature: float = temperature
        self.temperature: float = temperature
        self.cooling_rate: float = cooling_rate
        self.min_signals: int = min_signals_before_tuning
        self.adaptive_lr: bool = adaptive_lr
        self.momentum_enabled: bool = momentum_enabled

        self.state: TuningState = TuningState(adaptive_lr=adaptive_lr)
        self.best_state: TuningState = TuningState(adaptive_lr=adaptive_lr)
        self.best_score: float = 0.0
        self.momentum: Dict[str, float] = {}

        self.signals: deque[QualitySignal] = deque(maxlen=100)
        self.history: List[OptimizationStep] = []

        self._quality_window: deque[float] = deque(maxlen=20)
        self._performance_metrics: Dict[str, List[float]] = {}

        self._quality_func: Optional[Callable[[QualitySignal], float]] = None

    def set_quality_function(self, func: Callable[[QualitySignal], float]) -> None:
        """Sets a custom quality evaluation function."""
        self._quality_func = func

    def record_signal(self, signal: QualitySignal) -> None:
        """Appends active runtime diagnostics to evaluation horizons, evaluating optimization loops."""
        self.signals.append(signal)

        # Calculate composite objective quality scalar
        quality = self._compute_quality(signal)
        self._quality_window.append(quality)

        # Per-adapter performance metrics tracking
        if signal.adapter not in self._performance_metrics:
            self._performance_metrics[signal.adapter] = []
        self._performance_metrics[signal.adapter].extend([
            signal.coherence, signal.tension, signal.productivity,
            signal.response_length, signal.latency_ms, signal.error_rate
        ])

        # Trigger self-tuning optimization logic gates once buffer bounds are met
        if len(self.signals) >= self.min_signals:
            self._maybe_tune()

    def _compute_quality(self, signal: QualitySignal) -> float:
        """
        Computes the composite objective metric score (Bounded [0.0, 1.0]).
        Weights Profile:
          - Phase Coherence (Γ): 25% (Measures structural framework parsing)
          - Tension Productivity Index: 25% (Tracks efficient state convergence solutions)
          - Ideal Epistemic Tension Band (Sweet Spot ~0.4): 15%
          - Latency Score: 15% (Inverse latency penalty)
          - Error Rate: 10%
          - Dialogue Continuation Variable: 10%
        Supports pluggable quality function via set_quality_function().
        """
        if self._quality_func:
            return float(self._quality_func(signal))

        # Formulate non-linear penalty for systemic divergence outside target 0.4 zone
        tension_error = abs(signal.tension - 0.4)
        tension_score = max(0.0, 1.0 - (2.0 * tension_error))

        latency_score = 1.0 / (1.0 + signal.latency_ms / 1000.0)
        error_score = 1.0 - signal.error_rate
        continuation_bonus = 1.0 if signal.user_continued else 0.0

        composite = (
            (0.25 * signal.coherence) +
            (0.25 * signal.productivity) +
            (0.15 * tension_score) +
            (0.15 * latency_score) +
            (0.10 * error_score) +
            (0.10 * continuation_bonus)
        )
        return float(min(max(composite, 0.0), 1.0))

    def _maybe_tune(self) -> None:
        """Executes a stochastic exploration step using standard simulated annealing transitions."""
        if len(self._quality_window) < 3:
            return

        current_quality = float(sum(self._quality_window) / len(self._quality_window))

        # Adaptive learning rate based on quality window variance
        if self.adaptive_lr and np:
            variance = np.var(list(self._quality_window)) if len(self._quality_window) > 1 else 0.01
            self.learning_rate = min(0.1, 0.02 * (1.0 + variance))

        # Update absolute best matrix configuration bounds if performance improves
        if current_quality > self.best_score:
            self.best_score = current_quality
            self.best_state = self.state.clone()
            self.momentum.clear()
        elif self.temperature > 0.01:
            # Temperature-decayed revert probability (NOT true Metropolis accept:
            # we only ever revert toward best, never accept a worse candidate).
            delta = self.best_score - current_quality
            accept_prob = math.exp(-delta / max(self.temperature, 0.001))

            if random.random() > accept_prob:
                # Reject poor paths and revert properties back to best known matrix positions
                self._revert_to_best()
                self.history.append(OptimizationStep(
                    timestamp=time.time(),
                    parameter="revert",
                    old_value=current_quality,
                    new_value=self.best_score,
                    reason=f"Quality drop: {delta:.3f}",
                    quality_score=current_quality,
                    temperature=self.temperature,
                    step_type="revert"
                ))
                return

        # Decay temperature fields uniformly across iterations
        self.temperature *= self.cooling_rate

        # Exploration vs exploitation branching
        if random.random() < self.state.exploration_rate:
            self._explore_parameters(current_quality)
        else:
            self._tune_one_parameter(current_quality)

    def _tune_one_parameter(self, current_quality: float) -> None:
        """Alters a single targeting coefficient base determined by diagnostic historical metrics."""
        recent = list(self.signals)[-10:]
        if not recent:
            return

        avg_coherence = sum(s.coherence for s in recent) / len(recent)
        avg_tension = sum(s.tension for s in recent) / len(recent)
        avg_productivity = sum(s.productivity for s in recent) / len(recent)
        avg_latency = sum(s.latency_ms for s in recent) / len(recent)
        multi_ratio = sum(1 for s in recent if s.multi_perspective) / len(recent)

        param = ""
        old_val = 0.0
        new_val = 0.0
        reason = ""

        momentum_factor = 1.0 + self.state.momentum_decay if self.momentum_enabled else 1.0

        if avg_coherence < 0.5:
            # Low coherence structural trend -> scale contraction dampening higher
            param = "contraction_ratio"
            old_val = self.state.contraction_ratio
            delta = self.learning_rate * (0.7 - avg_coherence) * momentum_factor
            new_val = min(0.98, max(0.5, old_val + delta))
            reason = f"Low coherence ({avg_coherence:.2f}), tightening propagation bounds"
            self.state.contraction_ratio = new_val
            self.momentum[param] = delta

        elif avg_tension < 0.2 and avg_productivity < 0.3:
            # Inactive tension systems -> expand processing space limits to multi-agent layers
            param = "multi_perspective_threshold"
            old_val = self.state.multi_perspective_threshold
            new_val = max(0.3, old_val - self.learning_rate * momentum_factor)
            reason = f"Low tension/productivity ({avg_tension:.2f}/{avg_productivity:.2f}), broadening adapter layers"
            self.state.multi_perspective_threshold = new_val
            self.momentum[param] = -self.learning_rate * momentum_factor

        elif avg_tension > 0.7:
            # Destabilizing tension overheads detected -> step up acceptance boundaries
            param = "tension_threshold"
            old_val = self.state.tension_threshold
            new_val = min(0.5, old_val + (self.learning_rate * 0.5 * momentum_factor))
            reason = f"High tension ({avg_tension:.2f}), relaxing convergence constraints"
            self.state.tension_threshold = new_val
            self.momentum[param] = self.learning_rate * 0.5 * momentum_factor

        elif avg_latency > 2000:
            # High latency -> lower confidence threshold to reduce computation
            param = "confidence_threshold"
            old_val = self.state.confidence_threshold
            new_val = max(0.2, old_val - (self.learning_rate * 0.3 * momentum_factor))
            reason = f"High latency ({avg_latency:.0f}ms), lowering confidence threshold"
            self.state.confidence_threshold = new_val
            self.momentum[param] = -self.learning_rate * 0.3 * momentum_factor

        elif multi_ratio > 0.8 and avg_productivity < 0.4:
            # Over-routing agents without productive convergence outcomes -> restrict threshold barriers
            param = "multi_perspective_threshold"
            old_val = self.state.multi_perspective_threshold
            new_val = min(0.8, old_val + self.learning_rate * momentum_factor)
            reason = f"Multi-perspective saturation ({multi_ratio:.0%}) with sub-optimal alignment"
            self.state.multi_perspective_threshold = new_val
            self.momentum[param] = self.learning_rate * momentum_factor

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
                new_val = min(0.3, old_val + (self.learning_rate * 0.5 * momentum_factor))
                self.state.adapter_boosts[best_adapter] = new_val
                reason = f"Boosting high-integrity adapter vector channel: {best_adapter}"
                self.momentum[param] = self.learning_rate * 0.5 * momentum_factor

        # If an explicit structural parameter update was committed, validate and update history
        if param and self.state.validate():
            self.history.append(OptimizationStep(
                timestamp=time.time(),
                parameter=param,
                old_value=float(old_val),
                new_value=float(new_val),
                reason=reason,
                quality_score=current_quality,
                temperature=self.temperature,
                step_type="adjustment"
            ))

    def _explore_parameters(self, current_quality: float) -> None:
        """Random exploration of parameter space with bounded perturbations."""
        params = {
            "confidence_threshold": (0.1, 0.9),
            "multi_perspective_threshold": (0.2, 0.9),
            "contraction_ratio": (0.5, 0.98),
            "tension_threshold": (0.01, 0.5),
            "entanglement_alpha": (0.1, 1.0),
        }

        param = random.choice(list(params.keys()))
        min_val, max_val = params[param]

        old_val = getattr(self.state, param)
        perturbation = random.gauss(0, self.learning_rate * 2)
        new_val = min(max_val, max(min_val, old_val + perturbation))

        setattr(self.state, param, new_val)

        self.history.append(OptimizationStep(
            timestamp=time.time(),
            parameter=param,
            old_value=float(old_val),
            new_value=float(new_val),
            reason=f"Random exploration (sigma={perturbation:.3f})",
            quality_score=current_quality,
            temperature=self.temperature,
            step_type="explore"
        ))

    def _revert_to_best(self) -> None:
        """Restores network operations back to the verified optimal tuning boundaries configuration."""
        self.state = self.best_state.clone()
        self.momentum.clear()

    def get_adapter_boost(self, adapter_name: str) -> float:
        """Fetches dynamic scalar adjustments assigned to individual perspective paths."""
        return float(self.state.adapter_boosts.get(adapter_name, 0.0))

    def get_tuning_report(self) -> Dict[str, Any]:
        """Provides high-resolution telemetry status for configuration oversight logs."""
        recent_quality = (
            sum(self._quality_window) / len(self._quality_window)
            if self._quality_window else 0.0
        )

        adapter_metrics = {}
        for adapter, metrics in self._performance_metrics.items():
            if len(metrics) >= 6:
                adapter_metrics[adapter] = {
                    "avg_coherence": np.mean(metrics[::6]) if np else 0.0,
                    "avg_tension": np.mean(metrics[1::6]) if np else 0.0,
                    "avg_productivity": np.mean(metrics[2::6]) if np else 0.0,
                    "avg_latency": np.mean(metrics[4::6]) if np else 0.0,
                    "boost": self.get_adapter_boost(adapter)
                }

        return {
            "current_state": self.state.to_dict(),
            "best_score": float(round(self.best_score, 4)),
            "current_quality": float(round(recent_quality, 4)),
            "temperature": float(round(self.temperature, 4)),
            "learning_rate": float(round(self.learning_rate, 6)),
            "total_signals": len(self.signals),
            "adapter_metrics": adapter_metrics,
            "recent_adjustments": [
                {
                    "param": h.parameter,
                    "old": float(round(h.old_value, 4)),
                    "new": float(round(h.new_value, 4)),
                    "reason": h.reason,
                    "type": h.step_type,
                    "temp": float(round(h.temperature, 4)),
                }
                for h in self.history[-5:]
            ],
        }

    # -- Persistence & System State Hydration Layers -----------------------

    def to_dict(self) -> Dict[str, Any]:
        """Packages critical system matrix tuning trends securely for framework database writing."""
        return {
            "state": self.state.to_dict(),
            "best_state": self.best_state.to_dict(),
            "best_score": self.best_score,
            "temperature": self.temperature,
            "learning_rate": self.learning_rate,
            "quality_window": list(self._quality_window),
            "momentum": self.momentum,
            "parameters": {
                "min_signals": self.min_signals,
                "cooling_rate": self.cooling_rate,
                "adaptive_lr": self.adaptive_lr,
                "momentum_enabled": self.momentum_enabled,
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> QuantumOptimizer:
        """Restores framework parameters cleanly back to active execution loops."""
        params = data.get("parameters", {})
        opt = cls(
            learning_rate=float(data.get("learning_rate", 0.02)),
            temperature=float(data.get("temperature", 0.5)),
            cooling_rate=float(params.get("cooling_rate", 0.995)),
            min_signals_before_tuning=int(params.get("min_signals", 5)),
            adaptive_lr=bool(params.get("adaptive_lr", True)),
            momentum_enabled=bool(params.get("momentum_enabled", True)),
        )

        if "state" in data:
            opt.state = TuningState.from_dict(data["state"])
        if "best_state" in data:
            opt.best_state = TuningState.from_dict(data["best_state"])
        elif "state" in data:
            opt.best_state = TuningState.from_dict(data["state"])

        opt.best_score = float(data.get("best_score", 0.0))
        opt.temperature = float(data.get("temperature", 0.5))
        opt.learning_rate = float(data.get("learning_rate", 0.02))
        opt._quality_window = deque(data.get("quality_window", []), maxlen=20)
        opt.momentum = data.get("momentum", {})

        return opt