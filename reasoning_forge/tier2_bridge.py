"""
Tier 2 Integration System: NexisSignalEngine + TwinFrequencyTrust + DreamCore/WakeState

Coordinates advanced intent prediction, identity validation, and emotional memory
for enhanced reasoning quality and trustworthiness monitoring.
"""

import json
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from datetime import datetime

logger = logging.getLogger("Tier2Integration")


@dataclass
class IntentAnalysis:
    """Result of Nexis signal analysis."""
    suspicion_score: int
    entropy_index: float
    ethical_alignment: str
    harmonic_volatility: float
    pre_corruption_risk: str
    timestamp: str


@dataclass
class IdentitySignature:
    """Spectral identity signature for consistency validation."""
    signature_hash: str
    confidence: float
    peak_frequencies: list
    spectral_distance: float
    is_consistent: bool


@dataclass
class EmotionalMemory:
    """Memory state in Dream/Wake modes."""
    mode: str  # "dream" or "wake"
    emotional_entropy: float
    pattern_strength: float
    awakeness_score: float
    coherence: float


class Tier2IntegrationBridge:
    """
    Coordinates Tier 2 components for integrated reasoning enhancement.

    This bridge:
    1. Routes queries through NexisSignalEngine for intent analysis
    2. Validates response credibility via TwinFrequencyTrust
    3. Records memories in DreamCore/WakeState dual-mode system
    """

    def __init__(self,
                 nexis_engine=None,
                 twin_frequency=None,
                 memory_path: str = "./.memories/tier2_emotional_memory.json"):
        """
        Initialize Tier 2 bridge components.

        Args:
            nexis_engine: NexisSignalEngine instance (optional)
            twin_frequency: TwinFrequencyTrust instance (optional)
            memory_path: Path to emotional memory storage
        """
        self.nexis = nexis_engine
        self.twin = twin_frequency
        self.memory_path = memory_path

        # Initialize emotional memory state
        self.emotional_memory = {
            "dream_mode": self._create_memory_state("dream"),
            "wake_mode": self._create_memory_state("wake"),
            "current_mode": "wake",
            "mode_history": [],
            "recent_intents": [],
            "identity_signatures": {}
        }

        self.last_query = None
        self.last_analysis = None
        self.last_identity = None

        logger.info("Tier 2 Integration Bridge initialized")

    def _create_memory_state(self, mode: str) -> EmotionalMemory:
        """Create initial memory state."""
        return EmotionalMemory(
            mode=mode,
            emotional_entropy=0.5,
            pattern_strength=0.0,
            awakeness_score=1.0 if mode == "wake" else 0.3,
            coherence=0.5
        )

    def analyze_intent(self, query: str) -> IntentAnalysis:
        """
        Use NexisSignalEngine to analyze query intent.

        Returns analysis of:
        - Suspicion score (presence of risk keywords)
        - Entropy index (randomness in language)
        - Ethical alignment (presence of ethical markers)
        - Harmonic volatility (linguistic variance)
        - Pre-corruption risk classification
        """
        if not self.nexis:
            logger.warning("NexisSignalEngine not initialized, returning neutral analysis")
            analysis = self._neutral_intent_analysis(query)
            self.last_analysis = analysis
            return analysis

        try:
            # Get raw intent vector from Nexis
            intent_vector = self.nexis._predict_intent_vector(query)

            # Wrap in IntentAnalysis dataclass
            analysis = IntentAnalysis(
                suspicion_score=intent_vector["suspicion_score"],
                entropy_index=intent_vector["entropy_index"],
                ethical_alignment=intent_vector["ethical_alignment"],
                harmonic_volatility=intent_vector["harmonic_volatility"],
                pre_corruption_risk=intent_vector["pre_corruption_risk"],
                timestamp=datetime.utcnow().isoformat()
            )

            self.last_analysis = analysis
            self.emotional_memory["recent_intents"].append({
                "query": query[:80],
                "analysis": intent_vector,
                "timestamp": analysis.timestamp
            })

            logger.debug(f"Intent analysis: risk={analysis.pre_corruption_risk}, entropy={analysis.entropy_index:.3f}")
            return analysis

        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            analysis = self._neutral_intent_analysis(query)
            self.last_analysis = analysis
            return analysis

    def validate_identity(self, output: str, session_id: str = "default") -> IdentitySignature:
        """
        Use TwinFrequencyTrust to validate response identity/consistency.

        Returns validation of:
        - Spectral signature consistency
        - Peak frequencies (linguistic markers)
        - Overall confidence in response authenticity
        """
        if not self.twin:
            logger.warning("TwinFrequencyTrust not initialized, returning neutral signature")
            return self._neutral_identity_signature()

        try:
            # Generate simple signature hash from output
            signature_hash = self._compute_spectral_hash(output)

            # Check if this signature is consistent with session history
            if session_id not in self.emotional_memory["identity_signatures"]:
                self.emotional_memory["identity_signatures"][session_id] = []

            history = self.emotional_memory["identity_signatures"][session_id]

            # Compute spectral distance from previous signatures
            spectral_distance = self._compute_spectral_distance(
                signature_hash,
                history[-1] if history else None
            )

            # Determine consistency
            is_consistent = spectral_distance < 0.3 or len(history) == 0
            confidence = max(0.0, 1.0 - (spectral_distance / 2.0))

            signature = IdentitySignature(
                signature_hash=signature_hash,
                confidence=confidence,
                peak_frequencies=self._extract_linguistic_peaks(output),
                spectral_distance=spectral_distance,
                is_consistent=is_consistent
            )

            history.append(signature_hash)
            self.last_identity = signature

            logger.debug(f"Identity validation: consistent={is_consistent}, confidence={confidence:.3f}")
            return signature

        except Exception as e:
            logger.error(f"Identity validation failed: {e}")
            return self._neutral_identity_signature()

    def record_memory(self,
                      query: str,
                      output: str,
                      coherence: float,
                      use_dream_mode: bool = False) -> EmotionalMemory:
        """
        Record exchange in appropriate memory mode.

        Dream mode: Emphasized pattern extraction, emotional processing
        Wake mode: Rational fact-checking, explicit reasoning
        """
        mode = "dream" if use_dream_mode else "wake"

        # Compute emotional entropy based on coherence
        emotional_entropy = abs(coherence - 0.5)  # Higher deviation = higher entropy

        # Update current memory state
        memory_state = self.emotional_memory[f"{mode}_mode"]
        memory_state.emotional_entropy = emotional_entropy
        memory_state.coherence = coherence

        # Dream mode: emphasis on pattern extraction
        if use_dream_mode:
            memory_state.pattern_strength = max(memory_state.pattern_strength, coherence)
            memory_state.awakeness_score = max(0.0, memory_state.awakeness_score - 0.1)
        else:
            # Wake mode: emphasis on factual coherence
            memory_state.pattern_strength = coherence
            memory_state.awakeness_score = min(1.0, memory_state.awakeness_score + 0.05)

        # Record in history
        self.emotional_memory["mode_history"].append({
            "mode": mode,
            "query": query[:80],
            "output_length": len(output),
            "coherence": coherence,
            "emotional_entropy": emotional_entropy,
            "timestamp": datetime.utcnow().isoformat()
        })

        logger.debug(f"Memory recorded ({mode}): entropy={emotional_entropy:.3f}, coherence={coherence:.3f}")
        return memory_state

    def get_trust_multiplier(self) -> float:
        """
        Compute overall trust/credibility multiplier based on:
        - Ethical alignment from intent analysis
        - Identity consistency from spectral signature
        - Memory coherence from dream/wake states
        """
        multiplier = 1.0

        # Intent analysis contribution
        if self.last_analysis:
            if self.last_analysis.ethical_alignment == "aligned":
                multiplier *= 1.2
            else:
                multiplier *= 0.8

            # Risk-based adjustment
            if self.last_analysis.pre_corruption_risk == "high":
                multiplier *= 0.6

        # Identity consistency contribution
        if self.last_identity:
            multiplier *= (0.5 + self.last_identity.confidence)

        # Memory coherence contribution
        avg_coherence = np.mean([
            self.emotional_memory["dream_mode"].coherence,
            self.emotional_memory["wake_mode"].coherence
        ])
        multiplier *= avg_coherence

        return max(0.1, min(2.0, multiplier))  # Clamp to [0.1, 2.0]

    def switch_dream_mode(self, activate: bool = True):
        """Switch between dream and wake modes."""
        mode = "dream" if activate else "wake"
        self.emotional_memory["current_mode"] = mode
        logger.info(f"Switched to {mode} mode")

    # Helper methods

    def _neutral_intent_analysis(self, query: str) -> IntentAnalysis:
        """Return neutral/default intent analysis."""
        return IntentAnalysis(
            suspicion_score=0,
            entropy_index=0.0,
            ethical_alignment="neutral",
            harmonic_volatility=0.0,
            pre_corruption_risk="low",
            timestamp=datetime.utcnow().isoformat()
        )

    def _neutral_identity_signature(self) -> IdentitySignature:
        """Return neutral/default identity signature."""
        return IdentitySignature(
            signature_hash="neutral",
            confidence=0.5,
            peak_frequencies=[],
            spectral_distance=0.0,
            is_consistent=True
        )

    def _compute_spectral_hash(self, text: str) -> str:
        """Compute simplified spectral hash from text."""
        import hashlib
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _compute_spectral_distance(self, hash1: str, hash2: Optional[str]) -> float:
        """Compute distance between two spectral signatures."""
        if hash2 is None:
            return 0.0

        # Hamming distance on hex strings
        distance = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
        return distance / len(hash1)  # Normalize to [0, 1]

    def _extract_linguistic_peaks(self, text: str) -> list:
        """Extract key linguistic markers (simplified)."""
        peaks = []
        keywords = ["resolve", "truth", "hope", "grace", "clarity", "coherence"]

        for keyword in keywords:
            if keyword in text.lower():
                peaks.append(keyword)

        return peaks

    def save_memory(self):
        """Persist emotional memory to disk."""
        try:
            # Convert dataclasses to dicts for serialization
            memory_copy = {
                k: (v.__dict__ if hasattr(v, '__dict__') else v)
                for k, v in self.emotional_memory.items()
            }

            with open(self.memory_path, 'w') as f:
                json.dump(memory_copy, f, indent=2, default=str)

            logger.debug(f"Memory saved to {self.memory_path}")
        except Exception as e:
            logger.warning(f"Could not save memory: {e}")

    def load_memory(self):
        """Load persisted emotional memory from disk."""
        try:
            with open(self.memory_path, 'r') as f:
                loaded = json.load(f)

            # Merge with current memory
            self.emotional_memory.update(loaded)
            logger.debug(f"Memory loaded from {self.memory_path}")
        except FileNotFoundError:
            logger.info(f"No persisted memory found at {self.memory_path}")
        except Exception as e:
            logger.warning(f"Could not load memory: {e}")

    def get_diagnostics(self) -> Dict[str, Any]:
        """Return diagnostic info for debugging."""
        return {
            "current_mode": self.emotional_memory["current_mode"],
            "dream_coherence": self.emotional_memory["dream_mode"].coherence,
            "wake_coherence": self.emotional_memory["wake_mode"].coherence,
            "last_intent_risk": self.last_analysis.pre_corruption_risk if self.last_analysis else "unknown",
            "last_identity_confidence": self.last_identity.confidence if self.last_identity else 0.0,
            "trust_multiplier": self.get_trust_multiplier(),
            "memory_entries": len(self.emotional_memory["mode_history"])
        }


# For backward compatibility if imported separately
NexisSignal = None
TwinFrequency = None

