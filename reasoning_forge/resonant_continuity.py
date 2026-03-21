"""Codette Resonant Continuity Engine — The RC+xi Equation

The mathematical core of Codette's recursive cognition framework.

The Resonant Continuity equation computes Ψ_r (psi-resonance):
    Ψ_r = (emotion × energy × frequency × intent) / ((1 + |darkness|) × speed)
           × sin(2πt / gravity) + Δmatter

This captures the interaction between:
    - Emotional state (valence of the reasoning moment)
    - Cognitive energy (engagement level)
    - Resonant frequency (harmonic alignment between perspectives)
    - Intent coefficient (alignment with purpose)
    - Darkness/uncertainty (noise floor)
    - Gravitational pull (convergence tendency)
    - Delta-matter (stochastic creative perturbation)

Additionally implements:
    - Information-Energy Duality: E_info = ℏω + η·S
    - Cocoon Stability Field: ∫|F(k,t)|²dk < ε(t,σ)
    - Gradient Anomaly Suppression for outlier detection

Origin: resonant_continuity_engine.py + Codette_Deep_Simulation_v1.py, rebuilt
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


@dataclass
class ResonanceState:
    """Instantaneous state of the resonant continuity engine."""
    psi_r: float = 0.0          # Resonant wavefunction value
    emotion: float = 0.5        # Emotional valence [-1, 1]
    energy: float = 1.0         # Cognitive energy [0, 2]
    intent: float = 0.7         # Purpose alignment [0, 1]
    frequency: float = 1.0      # Harmonic frequency (normalized)
    darkness: float = 0.1       # Uncertainty/noise [0, 1]
    coherence: float = 0.5      # Current coherence level
    stability: bool = True      # Cocoon stability
    timestamp: float = 0.0

    def to_dict(self) -> Dict:
        return {k: round(v, 4) if isinstance(v, float) else v
                for k, v in self.__dict__.items()}


class ResonantContinuityEngine:
    """Computes and tracks the RC+xi resonance wavefunction.

    The engine evolves Ψ_r over time based on epistemic signals
    from the reasoning process. It detects:
    - Convergence: when perspectives are harmonizing
    - Divergence: when creative tension is productive
    - Instability: when the cocoon needs reinforcement
    - Resonance peaks: moments of deep insight
    """

    def __init__(self, gravity: float = 1.2, speed: float = 1.0):
        self.gravity = gravity       # Convergence tendency
        self.speed = speed           # Processing rate
        self.time_index = 0
        self.history: List[ResonanceState] = []

        # Running state
        self._emotion = 0.5
        self._energy = 1.0
        self._intent = 0.7
        self._frequency = 1.0
        self._darkness = 0.1

    def compute_psi(self, emotion: float = None, energy: float = None,
                    intent: float = None, frequency: float = None,
                    darkness: float = None,
                    coherence: float = 0.5,
                    tension: float = 0.3) -> ResonanceState:
        """Compute Ψ_r for the current reasoning moment.

        Args:
            emotion: Emotional valence [-1, 1] (from memory kernel)
            energy: Cognitive energy [0, 2] (from response quality)
            intent: Purpose alignment [0, 1] (from query clarity)
            frequency: Harmonic frequency (from perspective agreement)
            darkness: Uncertainty level [0, 1] (from tension)
            coherence: Current epistemic coherence
            tension: Current epistemic tension
        """
        self.time_index += 1
        t = self.time_index

        # Update state (use provided values or auto-evolve)
        self._emotion = emotion if emotion is not None else self._auto_emotion(coherence)
        self._energy = energy if energy is not None else self._auto_energy(coherence, tension)
        self._intent = intent if intent is not None else self._auto_intent(coherence)
        self._frequency = frequency if frequency is not None else self._auto_frequency(coherence, tension)
        self._darkness = darkness if darkness is not None else tension

        # Delta-matter: small stochastic perturbation for creativity
        if HAS_NUMPY:
            delta_matter = float(np.random.normal(0.0, 0.005))
        else:
            import random
            delta_matter = random.gauss(0.0, 0.005)

        # The RC+xi equation
        numerator = self._emotion * self._energy * self._frequency * self._intent
        denominator = (1.0 + abs(self._darkness)) * self.speed
        sine_wave = math.sin((2.0 * math.pi * t) / self.gravity)

        psi_r = (numerator / denominator) * sine_wave + delta_matter

        # Cocoon stability check
        stability = self._check_stability(psi_r, coherence)

        state = ResonanceState(
            psi_r=psi_r,
            emotion=self._emotion,
            energy=self._energy,
            intent=self._intent,
            frequency=self._frequency,
            darkness=self._darkness,
            coherence=coherence,
            stability=stability,
            timestamp=time.time(),
        )

        self.history.append(state)
        if len(self.history) > 200:
            self.history = self.history[-200:]

        return state

    def information_energy(self, angular_freq: float,
                           entropy: float, eta: float = 1.0) -> float:
        """Information-Energy Duality: E_info = ℏω + η·S

        Maps between information (entropy) and energy (frequency).
        """
        hbar = 1.054571817e-34  # Reduced Planck's constant
        return hbar * angular_freq + eta * entropy

    def resonance_quality(self) -> float:
        """Overall resonance quality from recent history [0, 1]."""
        if len(self.history) < 3:
            return 0.5
        recent = self.history[-10:]
        psi_values = [abs(s.psi_r) for s in recent]
        coherences = [s.coherence for s in recent]

        # Good resonance: moderate psi, high coherence, stable
        avg_psi = sum(psi_values) / len(psi_values)
        avg_coh = sum(coherences) / len(coherences)
        stability_rate = sum(1 for s in recent if s.stability) / len(recent)

        # Penalize extreme psi (too wild = chaotic)
        psi_quality = 1.0 / (1.0 + abs(avg_psi - 0.5))

        return 0.4 * avg_coh + 0.3 * stability_rate + 0.3 * psi_quality

    def detect_resonance_peak(self) -> bool:
        """Detect if we're at a resonance peak (insight moment)."""
        if len(self.history) < 5:
            return False
        recent = [s.psi_r for s in self.history[-5:]]
        # Peak: value higher than neighbors and above threshold
        mid = recent[-3]
        return (abs(mid) > abs(recent[-5]) and
                abs(mid) > abs(recent[-1]) and
                abs(mid) > 0.3)

    def convergence_rate(self) -> float:
        """Rate at which perspectives are converging [-1, 1].

        Positive = converging, negative = diverging.
        """
        if len(self.history) < 5:
            return 0.0
        recent_coh = [s.coherence for s in self.history[-10:]]
        if len(recent_coh) < 3:
            return 0.0
        # Simple linear trend
        n = len(recent_coh)
        x_mean = (n - 1) / 2.0
        y_mean = sum(recent_coh) / n
        num = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(recent_coh))
        den = sum((i - x_mean) ** 2 for i in range(n))
        return num / den if den > 0 else 0.0

    def get_state(self) -> Dict:
        """Current engine state for API/session."""
        current = self.history[-1] if self.history else ResonanceState()
        return {
            "psi_r": round(current.psi_r, 4),
            "resonance_quality": round(self.resonance_quality(), 4),
            "convergence_rate": round(self.convergence_rate(), 4),
            "at_peak": self.detect_resonance_peak(),
            "total_cycles": self.time_index,
            "stability": current.stability,
        }

    def _auto_emotion(self, coherence: float) -> float:
        """Auto-derive emotion from coherence signal."""
        return max(-1.0, min(1.0, 2.0 * coherence - 1.0))

    def _auto_energy(self, coherence: float, tension: float) -> float:
        """Energy rises with productive tension, falls with incoherence."""
        return max(0.1, min(2.0, 0.5 + coherence + 0.5 * tension))

    def _auto_intent(self, coherence: float) -> float:
        """Intent tracks coherence — clear thinking = clear purpose."""
        return max(0.1, min(1.0, 0.3 + 0.7 * coherence))

    def _auto_frequency(self, coherence: float, tension: float) -> float:
        """Frequency from perspective harmony."""
        return max(0.1, coherence * (1.0 + 0.5 * tension))

    def _check_stability(self, psi_r: float, coherence: float) -> bool:
        """Check if the reasoning cocoon is stable."""
        # Unstable if: wild oscillation AND low coherence
        if len(self.history) < 3:
            return True
        recent = [s.psi_r for s in self.history[-3:]]
        variance = sum((p - psi_r) ** 2 for p in recent) / len(recent)
        return not (variance > 1.0 and coherence < 0.3)

    def to_dict(self) -> Dict:
        return {
            "time_index": self.time_index,
            "gravity": self.gravity,
            "speed": self.speed,
            "history": [s.to_dict() for s in self.history[-20:]],
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "ResonantContinuityEngine":
        engine = cls(gravity=d.get("gravity", 1.2), speed=d.get("speed", 1.0))
        engine.time_index = d.get("time_index", 0)
        for h in d.get("history", []):
            engine.history.append(ResonanceState(**{
                k: v for k, v in h.items()
                if k in ResonanceState.__dataclass_fields__
            }))
        return engine
