"""
Cocoon Stability Field — Collapse Detection Engine
===================================================

FFT-based stability validation that detects synthesis loop collapse
BEFORE corrupted output is generated.

Based on Codette_Deep_Simulation_v1.py cocoon_stability_field() equation:
    stability = ∫|F(k)|² dk < ε_threshold

Purpose: Halt debate if system enters instability zone (gamma < 0.4,
runaway vocabulary patterns, self-referential cascades).

Recovered from: J:\codette-training-lab\new data\Codette_Deep_Simulation_v1.py
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class CocoonStabilityField:
    """
    FFT-based stability validator for debate coherence.

    Monitors frequency-domain energy distribution in agent responses.
    If energy becomes too concentrated (self-similarity, repeating patterns)
    or too diffuse (completely incoherent), flags collapse risk.
    """

    # Stability threshold parameters (empirically calibrated)
    ENERGY_CONCENTRATION_THRESHOLD = 0.85  # Max allowed variance in top frequencies
    SELF_SIMILARITY_THRESHOLD = 0.75       # Max allowed cosine similarity between consecutive responses
    COHERENCE_FLOOR = 0.3                   # Minimum coherence before stability alert
    RUNAWAY_VOCABULARY_RATIO = 0.6          # % unique words triggering concern

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.frequency_signatures: Dict[str, np.ndarray] = {}
        self.stability_history: List[Dict] = []

    def text_to_spectrum(self, text: str, fft_size: int = 256) -> np.ndarray:
        """
        Convert text to frequency spectrum for FFT analysis.

        Args:
            text: Response text to analyze
            fft_size: FFT size (should be power of 2)

        Returns:
            Normalized power spectrum [0, 1]
        """
        # Character-based encoding
        char_codes = np.array([ord(c) % 256 for c in text[:1000]], dtype=np.float32)

        # Pad to fft_size
        padded = np.zeros(fft_size, dtype=np.float32)
        padded[: len(char_codes)] = char_codes

        # Apply FFT
        fft_result = np.fft.fft(padded)
        power_spectrum = np.abs(fft_result) ** 2

        # Normalize
        max_power = np.max(power_spectrum) or 1.0
        normalized_spectrum = power_spectrum / max_power

        return normalized_spectrum[:128]  # Return only positive frequencies

    def check_energy_concentration(self, spectrum: np.ndarray) -> Tuple[float, bool]:
        """
        Check if spectral energy is too concentrated (self-similarity syndrome).

        Concentrated energy = agent repeating itself/copying other agents.

        Args:
            spectrum: Power spectrum from FFT

        Returns:
            (concentration_ratio, is_concerning)
        """
        # Get top 10 frequencies
        top_k = 10
        top_powers = np.sort(spectrum)[-top_k:]
        top_sum = np.sum(top_powers)
        total_sum = np.sum(spectrum) or 1.0

        concentration = top_sum / total_sum
        is_concerning = concentration > self.ENERGY_CONCENTRATION_THRESHOLD

        return concentration, is_concerning

    def check_self_similarity(self, agent_name: str,
                             spectrum: np.ndarray) -> Tuple[float, bool]:
        """
        Check if agent is repeating itself (same response shape).

        Args:
            agent_name: Name of agent for history lookup
            spectrum: New response spectrum

        Returns:
            (similarity_score, is_concerning)
        """
        if agent_name not in self.frequency_signatures:
            self.frequency_signatures[agent_name] = spectrum
            return 0.0, False

        prev_spectrum = self.frequency_signatures[agent_name]
        similarity = np.dot(prev_spectrum, spectrum) / (
            np.linalg.norm(prev_spectrum) * np.linalg.norm(spectrum) + 1e-8
        )

        self.frequency_signatures[agent_name] = spectrum  # Update

        is_concerning = similarity > self.SELF_SIMILARITY_THRESHOLD
        return float(similarity), is_concerning

    def check_vocabulary_diversity(self, text: str) -> Tuple[float, bool]:
        """
        Check if response vocabulary is repeating (indicators of "Another perspective on...").

        Args:
            text: Response text

        Returns:
            (uniqueness_ratio, is_concerning)
        """
        if len(text) < 20:
            return 1.0, False

        words = text.lower().split()
        if len(words) == 0:
            return 1.0, False

        unique_words = len(set(words))
        uniqueness = unique_words / len(words)

        is_concerning = uniqueness < (1.0 - self.RUNAWAY_VOCABULARY_RATIO)

        return uniqueness, is_concerning

    def validate_analysis(self, agent_name: str, text: str) -> Dict:
        """
        Full stability validation for a single agent response.

        Args:
            agent_name: Name of agent
            text: Response text

        Returns:
            {
                'agent': str,
                'is_stable': bool,
                'stability_score': float (0-1),
                'flags': List[str],
                'spectrum': np.ndarray,
                'concerns': Dict
            }
        """
        spectrum = self.text_to_spectrum(text)

        flags = []
        concerns = {
            'energy_concentration': None,
            'self_similarity': None,
            'vocabulary_diversity': None
        }

        # Check 1: Energy concentration
        conc, conc_concerning = self.check_energy_concentration(spectrum)
        concerns['energy_concentration'] = {
            'ratio': float(conc),
            'concerning': conc_concerning
        }
        if conc_concerning:
            flags.append('HIGH_ENERGY_CONCENTRATION')

        # Check 2: Self-similarity
        similarity, sim_concerning = self.check_self_similarity(agent_name, spectrum)
        concerns['self_similarity'] = {
            'ratio': float(similarity),
            'concerning': sim_concerning
        }
        if sim_concerning:
            flags.append('REPEATING_RESPONSE_PATTERN')

        # Check 3: Vocabulary diversity
        uniqueness, vocab_concerning = self.check_vocabulary_diversity(text)
        concerns['vocabulary_diversity'] = {
            'uniqueness': float(uniqueness),
            'concerning': vocab_concerning
        }
        if vocab_concerning:
            flags.append('LOW_VOCABULARY_DIVERSITY')

        # Check 4: Response length sanity
        if len(text) < 50:
            flags.append('SUSPICIOUSLY_SHORT')
        if len(text) > 10000:
            flags.append('SUSPICIOUSLY_LONG')

        # Overall stability score
        num_flags = len(flags)
        stability_score = max(0.0, 1.0 - (num_flags * 0.25))

        is_stable = stability_score > self.COHERENCE_FLOOR

        if self.verbose and flags:
            logger.info(f"  {agent_name}: stability={stability_score:.2f}, flags={flags}")

        return {
            'agent': agent_name,
            'is_stable': is_stable,
            'stability_score': stability_score,
            'flags': flags,
            'spectrum': spectrum,
            'concerns': concerns
        }

    def validate_round(self, analyses: Dict[str, str],
                       round_num: int) -> Tuple[bool, List[Dict], float]:
        """
        Validate all agents' responses in a debate round.

        Args:
            analyses: Dict mapping agent_name → response_text
            round_num: Round number (for logging)

        Returns:
            (all_stable, validation_reports, avg_stability)
        """
        reports = []
        stability_scores = []

        for agent_name, text in analyses.items():
            report = self.validate_analysis(agent_name, text)
            reports.append(report)
            stability_scores.append(report['stability_score'])

        avg_stability = np.mean(stability_scores) if stability_scores else 0.5

        all_stable = all(r['is_stable'] for r in reports)

        unstable_agents = [r['agent'] for r in reports if not r['is_stable']]
        if unstable_agents:
            logger.warning(
                f"Round {round_num}: Unstable agents detected: {unstable_agents} "
                f"(avg_stability={avg_stability:.2f})"
            )

        # Store in history
        self.stability_history.append({
            'round': round_num,
            'all_stable': all_stable,
            'avg_stability': avg_stability,
            'unstable_agents': unstable_agents,
            'reports': reports
        })

        return all_stable, reports, avg_stability

    def should_halt_debate(self, analyses: Dict[str, str],
                          round_num: int, gamma: Optional[float] = None) -> Tuple[bool, str]:
        """
        Determine if debate should halt before synthesis.

        Halt if:
        1. Multiple agents unstable
        2. Gamma coherence < 0.35 (system collapse zone)
        3. Too many "REPEATING_RESPONSE_PATTERN" flags

        Args:
            analyses: Current round analyses
            round_num: Current round number
            gamma: Current gamma coherence (optional)

        Returns:
            (should_halt, reason)
        """
        all_stable, reports, avg_stability = self.validate_round(analyses, round_num)

        if not all_stable:
            unstable_count = sum(1 for r in reports if not r['is_stable'])
            if unstable_count >= 2:
                reason = (
                    f"Multiple agents unstable ({unstable_count}/{len(reports)}) "
                    f"at round {round_num}. Avg stability: {avg_stability:.2f}"
                )
                logger.warning(f"STABILITY CHECK: Halting debate. {reason}")
                return True, reason

        if gamma is not None and gamma < 0.35:
            reason = f"System in collapse zone (gamma={gamma:.2f} < 0.35)"
            logger.warning(f"STABILITY CHECK: Halting debate. {reason}")
            return True, reason

        # Check for repeating response patterns (synthesis loop indicator)
        repeating_count = sum(
            1 for r in reports
            if 'REPEATING_RESPONSE_PATTERN' in r['flags']
        )
        if repeating_count >= 2:
            reason = (
                f"Multiple agents repeating response patterns ({repeating_count}) "
                f"at round {round_num}. Synthesis loop risk."
            )
            logger.warning(f"STABILITY CHECK: Halting debate. {reason}")
            return True, reason

        return False, ""

    def get_summary(self) -> Dict:
        """Get stability history summary."""
        if not self.stability_history:
            return {"message": "No stability checks performed"}

        return {
            "total_rounds_checked": len(self.stability_history),
            "average_stability": np.mean([h['avg_stability'] for h in self.stability_history]),
            "halts_triggered": sum(1 for h in self.stability_history if not h['all_stable']),
            "recent": self.stability_history[-3:] if len(self.stability_history) >= 3 else self.stability_history,
        }
