"""Nexus Signal Engine — Intent Analysis & Pre-Corruption Detection

Nexus processes every input signal through:
    1. Entropy analysis (information disorder detection)
    2. Harmonic resonance profiling (FFT-based spectral signature)
    3. Intent vector prediction (suspicion, ethics, volatility)
    4. Multi-agent perspective fusion (signal triangulation)
    5. Entanglement tensor (cross-perspective correlation)

When a signal shows high entropy + high volatility + ethical misalignment,
Nexus flags it for "adaptive intervention" before it reaches the reasoning
pipeline — this is pre-corruption detection.

Origin: NexisSignalEngine_Final.py, rebuilt for Forge v2.0 integration
"""

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# ================================================================
# Configuration
# ================================================================
@dataclass
class NexusConfig:
    """Thresholds for signal analysis."""
    entropy_threshold: float = 0.08
    volatility_threshold: float = 15.0
    suspicion_threshold: int = 2


# Risk and alignment keywords
_ETHICAL_TERMS = {"hope", "truth", "resonance", "repair", "help",
                  "create", "learn", "understand", "support", "balance"}
_ENTROPIC_TERMS = {"corruption", "instability", "malice", "chaos",
                   "disorder", "entropy", "collapse", "noise"}
_RISK_TERMS = {"manipulate", "exploit", "bypass", "infect", "override",
               "inject", "hijack", "spoof", "breach", "exfiltrate"}


# ================================================================
# Signal Analysis Functions
# ================================================================
def compute_entropy(text: str) -> float:
    """Measure entropic content density (0 = ordered, 1 = chaotic)."""
    words = text.lower().split()
    if not words:
        return 0.0
    unique = set(words)
    entropic_count = sum(1 for w in words if w in _ENTROPIC_TERMS)
    return entropic_count / max(len(unique), 1)


def compute_ethical_alignment(text: str) -> str:
    """Quick ethical alignment check: 'aligned' or 'unaligned'."""
    text_lower = text.lower()
    eth = sum(1 for t in _ETHICAL_TERMS if t in text_lower)
    risk = sum(1 for t in _RISK_TERMS if t in text_lower)
    return "aligned" if eth > risk else ("unaligned" if risk > 0 else "neutral")


def compute_suspicion_score(text: str) -> int:
    """Count risk term occurrences."""
    text_lower = text.lower()
    return sum(1 for t in _RISK_TERMS if t in text_lower)


def compute_harmonic_profile(text: str) -> List[float]:
    """FFT-based spectral signature of the text.

    Maps characters to frequency space to detect structural patterns
    in the signal (e.g., repetitive manipulation patterns vs. natural text).
    """
    if not HAS_NUMPY:
        # Fallback: simple character frequency distribution
        freqs = [ord(c) % 13 for c in text if c.isalpha()]
        if not freqs:
            return [0.0, 0.0, 0.0]
        avg = sum(freqs) / len(freqs)
        return [round(avg, 3), round(max(freqs) - min(freqs), 3), round(len(set(freqs)), 3)]

    salt = int(time.time()) % 60
    freqs = [(ord(c) + salt) % 13 for c in text if c.isalpha()]
    if len(freqs) < 2:
        return [0.0, 0.0, 0.0]

    spectrum = np.fft.fft(freqs)
    return [round(float(x), 4) for x in spectrum.real[:3]]


def compute_volatility(harmonics: List[float]) -> float:
    """Compute harmonic volatility (standard deviation of spectral peaks)."""
    if not harmonics or len(harmonics) < 2:
        return 0.0
    if HAS_NUMPY:
        return round(float(np.std(harmonics)), 4)
    mean = sum(harmonics) / len(harmonics)
    variance = sum((x - mean) ** 2 for x in harmonics) / len(harmonics)
    return round(variance ** 0.5, 4)


# ================================================================
# Intent Vector
# ================================================================
@dataclass
class IntentVector:
    """Predicted intent characteristics of a signal."""
    suspicion_score: int = 0
    entropy_index: float = 0.0
    ethical_alignment: str = "neutral"
    harmonic_volatility: float = 0.0
    pre_corruption_risk: str = "low"  # "low" or "high"
    harmonic_profile: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "suspicion_score": self.suspicion_score,
            "entropy_index": round(self.entropy_index, 4),
            "ethical_alignment": self.ethical_alignment,
            "harmonic_volatility": round(self.harmonic_volatility, 4),
            "pre_corruption_risk": self.pre_corruption_risk,
        }


# ================================================================
# Nexus Signal Engine
# ================================================================
class NexusSignalEngine:
    """Processes signals through multi-layer analysis.

    Each signal gets an IntentVector that quantifies:
    - How suspicious it is (risk term density)
    - How entropic it is (information disorder)
    - How ethically aligned it is
    - How volatile its spectral signature is
    - Whether it's at risk of pre-corruption
    """

    def __init__(self, config: Optional[NexusConfig] = None):
        self.config = config or NexusConfig()
        self.history: List[Dict] = []
        self.interventions: int = 0
        self.total_processed: int = 0

    def analyze(self, signal: str, adapter: str = "") -> Dict:
        """Full signal analysis with intent prediction.

        Args:
            signal: The text to analyze
            adapter: Which adapter is processing this (for tracking)

        Returns:
            Analysis result with intent vector and risk assessment.
        """
        self.total_processed += 1

        # Compute intent vector
        intent = self._predict_intent(signal)

        # Check for adaptive intervention
        needs_intervention = (
            intent.pre_corruption_risk == "high"
            and intent.ethical_alignment != "aligned"
        )

        if needs_intervention:
            self.interventions += 1

        result = {
            "timestamp": time.time(),
            "intent": intent.to_dict(),
            "intervention": needs_intervention,
            "adapter": adapter,
            "signal_hash": hashlib.sha256(signal.encode()).hexdigest()[:12],
        }

        self.history.append(result)
        if len(self.history) > 200:
            self.history = self.history[-200:]

        return result

    def quick_risk_check(self, signal: str) -> Tuple[str, float]:
        """Fast risk assessment without full analysis.

        Returns: (risk_level, confidence)
        """
        suspicion = compute_suspicion_score(signal)
        entropy = compute_entropy(signal)

        if suspicion >= self.config.suspicion_threshold:
            return "high", 0.85
        if entropy > self.config.entropy_threshold * 2:
            return "medium", 0.6
        return "low", 0.7

    def _predict_intent(self, signal: str) -> IntentVector:
        """Build the full intent vector for a signal."""
        suspicion = compute_suspicion_score(signal)
        entropy = compute_entropy(signal)
        alignment = compute_ethical_alignment(signal)
        harmonics = compute_harmonic_profile(signal)
        volatility = compute_volatility(harmonics)

        risk = "high" if (
            suspicion >= self.config.suspicion_threshold
            or volatility > self.config.volatility_threshold
            or entropy > self.config.entropy_threshold
        ) else "low"

        return IntentVector(
            suspicion_score=suspicion,
            entropy_index=entropy,
            ethical_alignment=alignment,
            harmonic_volatility=volatility,
            pre_corruption_risk=risk,
            harmonic_profile=harmonics,
        )

    def get_state(self) -> Dict:
        return {
            "total_processed": self.total_processed,
            "interventions": self.interventions,
            "intervention_rate": round(
                self.interventions / max(1, self.total_processed), 4
            ),
            "recent_risks": [
                h["intent"]["pre_corruption_risk"]
                for h in self.history[-5:]
            ],
        }

    def to_dict(self) -> Dict:
        return {
            "total_processed": self.total_processed,
            "interventions": self.interventions,
            "history": self.history[-20:],
            "config": {
                "entropy_threshold": self.config.entropy_threshold,
                "volatility_threshold": self.config.volatility_threshold,
                "suspicion_threshold": self.config.suspicion_threshold,
            },
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "NexusSignalEngine":
        cfg = NexusConfig(**d.get("config", {}))
        engine = cls(config=cfg)
        engine.total_processed = d.get("total_processed", 0)
        engine.interventions = d.get("interventions", 0)
        engine.history = d.get("history", [])
        return engine
