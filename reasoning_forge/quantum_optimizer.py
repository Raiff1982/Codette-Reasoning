"""
QuantumOptimizer — Self-Tuning Engine for the Codette RC+xi Framework.

Inspired by VIVARA Genesis-Omega v2.0, rebuilt as a proper self-tuning system.

The optimizer tracks response quality signals (user engagement, coherence
scores, tension productivity) and adjusts:
  - Router confidence thresholds
  - Spiderweb parameters (contraction ratio, tension threshold)
  - Adapter selection weights
  - Multi-perspective synthesis quality

Uses simulated annealing with momentum: explores the parameter space
stochastically but remembers which configurations worked best.

All changes are bounded and reversible. The optimizer logs every
adjustment for full transparency.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class QualitySignal:
    """A quality signal from a Codette response."""
    timestamp: float
    adapter: str
    coherence: float        # Phase coherence at response time
    tension: float          # Epistemic tension at response time
    productivity: float     # Tension productivity score
    response_length: int    # Token count
    multi_perspective: bool  # Was this a multi-perspective response?
    user_continued: bool = True  # Did the user continue the conversation?


@dataclass
class TuningState:
    """Current tuning parameters."""
    # Router
    confidence_threshold: float = 0.4    # Below this, fall back to default
    multi_perspective_threshold: float = 0.6  # Above this, force multi-perspective

    # Spiderweb
    contraction_ratio: float = 0.85
    tension_threshold: float = 0.15
    entanglement_alpha: float = 0.9

    # Adapter weights (0-1 bonus applied to router scores)
    adapter_boosts: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "confidence_threshold": self.confidence_threshold,
            "multi_perspective_threshold": self.multi_perspective_threshold,
            "contraction_ratio": self.contraction_ratio,
            "tension_threshold": self.tension_threshold,
            "entanglement_alpha": self.entanglement_alpha,
            "adapter_boosts": dict(self.adapter_boosts),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TuningState":
        state = cls()
        for k, v in data.items():
            if k == "adapter_boosts":
                state.adapter_boosts = dict(v)
            elif hasattr(state, k):
                setattr(state, k, v)
        return state


@dataclass
class OptimizationStep:
    """Record of a single optimization step."""
    timestamp: float
    parameter: str
    old_value: float
    new_value: float
    reason: str
    quality_score: float


class QuantumOptimizer:
    """Self-tuning engine with simulated annealing."""

    def __init__(
        self,
        learning_rate: float = 0.02,
        temperature: float = 0.5,
        cooling_rate: float = 0.995,
        min_signals_before_tuning: int = 5,
    ):
        self.learning_rate = learning_rate
        self.temperature = temperature
        self.cooling_rate = cooling_rate
        self.min_signals = min_signals_before_tuning

        self.state = TuningState()
        self.best_state = TuningState()
        self.best_score = 0.0

        self.signals: List[QualitySignal] = []
        self.history: List[OptimizationStep] = []

        # Running quality metrics
        self._quality_window: List[float] = []
        self._window_size = 20

    def record_signal(self, signal: QualitySignal):
        """Record a quality signal from a Codette response."""
        self.signals.append(signal)

        # Compute composite quality score
        quality = self._compute_quality(signal)
        self._quality_window.append(quality)
        if len(self._quality_window) > self._window_size:
            self._quality_window.pop(0)

        # Maybe tune parameters
        if len(self.signals) >= self.min_signals:
            self._maybe_tune()

    def _compute_quality(self, signal: QualitySignal) -> float:
        """Composite quality score from a response signal.

        Weights:
          - coherence: 30% (high is good — responses make sense)
          - productivity: 30% (high is good — tension was resolved productively)
          - moderate tension: 20% (sweet spot ~0.3-0.5 is best)
          - user_continued: 20% (binary — did they keep talking?)
        """
        # Tension is best in the 0.3-0.5 range (productive disagreement)
        tension_score = 1.0 - 2.0 * abs(signal.tension - 0.4)
        tension_score = max(0.0, tension_score)

        quality = (
            0.30 * signal.coherence +
            0.30 * signal.productivity +
            0.20 * tension_score +
            0.20 * (1.0 if signal.user_continued else 0.0)
        )
        return min(max(quality, 0.0), 1.0)

    def _maybe_tune(self):
        """Run one optimization step if enough data."""
        if len(self._quality_window) < 3:
            return

        current_quality = sum(self._quality_window) / len(self._quality_window)

        # Simulated annealing: accept worse states with decreasing probability
        if current_quality > self.best_score:
            self.best_score = current_quality
            self.best_state = TuningState(**{
                k: getattr(self.state, k) for k in vars(self.state)
                if not k.startswith('_')
            })
        elif self.temperature > 0.01:
            # Accept worse state with probability exp(-delta/T)
            delta = self.best_score - current_quality
            accept_prob = math.exp(-delta / max(self.temperature, 0.001))
            if random.random() > accept_prob:
                # Revert to best known state
                self._revert_to_best()
                return

        # Cool down
        self.temperature *= self.cooling_rate

        # Pick a parameter to tune based on recent signals
        self._tune_one_parameter(current_quality)

    def _tune_one_parameter(self, current_quality: float):
        """Tune one parameter based on recent quality signals."""
        recent = self.signals[-10:]

        # Analyze what needs tuning
        avg_coherence = sum(s.coherence for s in recent) / len(recent)
        avg_tension = sum(s.tension for s in recent) / len(recent)
        avg_productivity = sum(s.productivity for s in recent) / len(recent)
        multi_ratio = sum(1 for s in recent if s.multi_perspective) / len(recent)

        # Decision: which parameter to adjust
        param = None
        old_val = 0.0
        new_val = 0.0
        reason = ""

        if avg_coherence < 0.5:
            # Low coherence -> increase contraction ratio (tighter belief propagation)
            param = "contraction_ratio"
            old_val = self.state.contraction_ratio
            delta = self.learning_rate * (0.7 - avg_coherence)
            new_val = min(0.98, max(0.5, old_val + delta))
            reason = f"Low coherence ({avg_coherence:.2f}), tightening propagation"

        elif avg_tension < 0.2 and avg_productivity < 0.3:
            # Too little tension AND low productivity -> lower confidence threshold
            # to allow more multi-perspective responses
            param = "multi_perspective_threshold"
            old_val = self.state.multi_perspective_threshold
            new_val = max(0.3, old_val - self.learning_rate)
            reason = f"Low tension+productivity ({avg_tension:.2f}/{avg_productivity:.2f}), encouraging multi-perspective"

        elif avg_tension > 0.7:
            # Too much tension -> increase tension threshold for convergence
            param = "tension_threshold"
            old_val = self.state.tension_threshold
            new_val = min(0.5, old_val + self.learning_rate * 0.5)
            reason = f"High tension ({avg_tension:.2f}), raising convergence threshold"

        elif multi_ratio > 0.8 and avg_productivity < 0.4:
            # Too many multi-perspective responses but low productivity
            param = "multi_perspective_threshold"
            old_val = self.state.multi_perspective_threshold
            new_val = min(0.8, old_val + self.learning_rate)
            reason = f"Multi-perspective overuse ({multi_ratio:.0%}) with low productivity"

        # Tune adapter boosts based on which adapters produce best quality
        elif len(recent) >= 5:
            adapter_quality = {}
            for s in recent:
                q = self._compute_quality(s)
                if s.adapter not in adapter_quality:
                    adapter_quality[s.adapter] = []
                adapter_quality[s.adapter].append(q)

            # Boost the best-performing adapter slightly
            if adapter_quality:
                best_adapter = max(
                    adapter_quality,
                    key=lambda a: sum(adapter_quality[a]) / len(adapter_quality[a])
                )
                param = f"adapter_boost_{best_adapter}"
                old_val = self.state.adapter_boosts.get(best_adapter, 0.0)
                new_val = min(0.3, old_val + self.learning_rate * 0.5)
                self.state.adapter_boosts[best_adapter] = new_val
                reason = f"Boosting high-quality adapter: {best_adapter}"

        if param and param not in ("adapter_boost_" + a for a in self.state.adapter_boosts):
            if hasattr(self.state, param):
                setattr(self.state, param, new_val)

        if param:
            self.history.append(OptimizationStep(
                timestamp=time.time(),
                parameter=param,
                old_value=old_val,
                new_value=new_val,
                reason=reason,
                quality_score=current_quality,
            ))

    def _revert_to_best(self):
        """Revert to the best known tuning state."""
        self.state = TuningState(**{
            k: getattr(self.best_state, k) for k in vars(self.best_state)
            if not k.startswith('_')
        })

    def get_adapter_boost(self, adapter_name: str) -> float:
        """Get the current boost for an adapter (0.0 = no boost)."""
        return self.state.adapter_boosts.get(adapter_name, 0.0)

    def get_tuning_report(self) -> Dict:
        """Get current tuning state and recent history."""
        recent_quality = (
            sum(self._quality_window) / len(self._quality_window)
            if self._quality_window else 0.0
        )
        return {
            "current_state": self.state.to_dict(),
            "best_score": round(self.best_score, 4),
            "current_quality": round(recent_quality, 4),
            "temperature": round(self.temperature, 4),
            "total_signals": len(self.signals),
            "recent_adjustments": [
                {
                    "param": h.parameter,
                    "old": round(h.old_value, 4),
                    "new": round(h.new_value, 4),
                    "reason": h.reason,
                }
                for h in self.history[-5:]
            ],
        }

    def to_dict(self) -> Dict:
        """Serialize for persistence."""
        return {
            "state": self.state.to_dict(),
            "best_score": self.best_score,
            "temperature": self.temperature,
            "quality_window": self._quality_window,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "QuantumOptimizer":
        opt = cls()
        if "state" in data:
            opt.state = TuningState.from_dict(data["state"])
            opt.best_state = TuningState.from_dict(data["state"])
        opt.best_score = data.get("best_score", 0.0)
        opt.temperature = data.get("temperature", 0.5)
        opt._quality_window = data.get("quality_window", [])
        return opt
