"""
Epistemic Metrics — RC+xi tension and coherence measurement for the Reasoning Forge.

Implements the core RC+xi equations within the forge context:
  - Epistemic tension (Eq. 2): xi_n = ||A_{n+1} - A_n||^2
  - Phase coherence (Eq. 11): Gamma = mean(|cos(theta_i - theta_bar)|)
  - Perspective coverage scoring
  - Tension decay tracking across debate rounds

These metrics let the forge quantify whether multi-agent reasoning actually
converges (productive tension resolution) or stalls (tension suppression).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Text -> vector helpers (lightweight, no external deps)
# ---------------------------------------------------------------------------

_STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "and", "but", "or", "nor", "not", "so",
    "yet", "both", "this", "that", "these", "those", "it", "its", "they",
    "them", "their", "we", "our", "you", "your", "he", "she", "his", "her",
}


def _tokenize(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in _STOP_WORDS]


def _term_vector(text: str) -> Counter:
    return Counter(_tokenize(text))


def _cosine_similarity(vec_a: Counter, vec_b: Counter) -> float:
    keys = set(vec_a) | set(vec_b)
    if not keys:
        return 0.0
    dot = sum(vec_a.get(k, 0) * vec_b.get(k, 0) for k in keys)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ---------------------------------------------------------------------------
# Perspective vocabulary banks (for coverage scoring)
# ---------------------------------------------------------------------------

_PERSPECTIVE_VOCAB = {
    "Newton": {
        "force", "energy", "momentum", "conservation", "equilibrium", "dynamics",
        "causality", "mass", "acceleration", "entropy", "thermodynamic",
        "symmetry", "invariance", "field", "potential", "kinetic",
    },
    "Quantum": {
        "probability", "superposition", "uncertainty", "complementarity",
        "entanglement", "wave", "particle", "observer", "collapse",
        "interference", "tunneling", "decoherence", "amplitude",
    },
    "Ethics": {
        "ethical", "moral", "fairness", "justice", "rights", "duty",
        "consequence", "harm", "benefit", "stakeholder", "autonomy",
        "consent", "accountability", "responsibility", "welfare",
    },
    "Philosophy": {
        "epistemology", "ontology", "metaphysics", "assumption", "paradox",
        "dialectic", "phenomenology", "consciousness", "existence", "meaning",
        "truth", "knowledge", "belief", "certainty", "skepticism",
    },
    "DaVinci": {
        "creative", "invention", "analogy", "design", "innovation",
        "prototype", "biomimicry", "synthesis", "novel", "interdisciplinary",
        "combination", "reimagine", "solution", "insight",
    },
    "Empathy": {
        "emotional", "experience", "feeling", "compassion", "support",
        "community", "relationship", "wellbeing", "vulnerability",
        "understanding", "perspective", "human", "care", "dignity",
    },
    "Consciousness": {
        "awareness", "recursive", "self-referential", "metacognition",
        "emergence", "cognition", "reflection", "introspection",
        "sentience", "subjective", "qualia", "binding", "attention",
        "intentionality", "phenomenal",
    },
    "SystemsArchitecture": {
        "modular", "scalable", "interface", "pattern", "component",
        "microservice", "pipeline", "throughput", "latency", "resilience",
        "abstraction", "coupling", "cohesion", "architecture",
    },
}


# ---------------------------------------------------------------------------
# EpistemicMetrics
# ---------------------------------------------------------------------------

class EpistemicMetrics:
    """Measure RC+xi epistemic tension and coherence across agent analyses."""

    def score_pairwise_tension(
        self, analyses: Dict[str, str],
    ) -> Dict[str, float]:
        """Compute epistemic tension between each pair of agent analyses.

        Tension is 1 - cosine_similarity: high when perspectives diverge,
        low when they repeat each other.

        Returns:
            Dict with keys like "Newton_vs_Ethics" -> tension float 0-1.
        """
        agents = list(analyses.keys())
        vectors = {name: _term_vector(text) for name, text in analyses.items()}
        tensions = {}
        for i in range(len(agents)):
            for j in range(i + 1, len(agents)):
                sim = _cosine_similarity(vectors[agents[i]], vectors[agents[j]])
                tensions[f"{agents[i]}_vs_{agents[j]}"] = round(1.0 - sim, 4)
        return tensions

    def score_ensemble_coherence(
        self, analyses: Dict[str, str],
    ) -> float:
        """Phase coherence Gamma across the agent ensemble.

        Analogous to Eq. 11 in the embodied sim:
          Gamma = mean(cos(theta_i - theta_bar))

        Here 'theta' is the term-vector direction, and coherence measures
        how much all agents point in a similar semantic direction.

        Returns:
            Gamma in [0, 1] where 1 = all agents semantically aligned.
        """
        vectors = [_term_vector(text) for text in analyses.values()]
        if len(vectors) < 2:
            return 1.0

        # Build centroid
        centroid: Counter = Counter()
        for v in vectors:
            centroid.update(v)

        similarities = [_cosine_similarity(v, centroid) for v in vectors]
        return round(sum(similarities) / len(similarities), 4)

    def score_tension_magnitude(
        self, analyses: Dict[str, str],
    ) -> float:
        """Overall epistemic tension magnitude (mean pairwise tension).

        Analogous to Eq. 2 xi_n but measured across agents rather than
        across time steps.

        Returns:
            Mean tension 0-1 where 0 = all identical, 1 = fully orthogonal.
        """
        tensions = self.score_pairwise_tension(analyses)
        if not tensions:
            return 0.0
        return round(sum(tensions.values()) / len(tensions), 4)

    def score_tension_productivity(
        self,
        analyses: Dict[str, str],
        synthesis: str,
    ) -> Dict[str, float]:
        """Evaluate whether tension is productive (resolved in synthesis)
        or destructive (suppressed or ignored).

        Productive tension: agents diverge but synthesis addresses the
        divergence explicitly. Destructive: synthesis ignores disagreements.

        Returns:
            Dict with tension_magnitude, coherence_gain, productivity score.
        """
        tension = self.score_tension_magnitude(analyses)
        ensemble_coherence = self.score_ensemble_coherence(analyses)

        # How much of each agent's unique vocabulary appears in synthesis
        synthesis_vec = _term_vector(synthesis)
        agent_coverage_in_synthesis = []
        for name, text in analyses.items():
            agent_vec = _term_vector(text)
            unique_to_agent = set(agent_vec) - set().union(
                *(_term_vector(t) for n, t in analyses.items() if n != name)
            )
            if unique_to_agent:
                covered = sum(1 for w in unique_to_agent if w in synthesis_vec)
                agent_coverage_in_synthesis.append(covered / len(unique_to_agent))
            else:
                agent_coverage_in_synthesis.append(1.0)

        synthesis_coverage = sum(agent_coverage_in_synthesis) / max(len(agent_coverage_in_synthesis), 1)

        # Productivity = high tension + high synthesis coverage
        # (divergent views that get integrated = productive)
        productivity = tension * synthesis_coverage
        # Coherence gain: synthesis should be more coherent than raw ensemble
        synthesis_vs_agents = _cosine_similarity(synthesis_vec, _term_vector(" ".join(analyses.values())))
        coherence_gain = max(0.0, synthesis_vs_agents - ensemble_coherence)

        return {
            "tension_magnitude": round(tension, 4),
            "ensemble_coherence": round(ensemble_coherence, 4),
            "synthesis_coverage": round(synthesis_coverage, 4),
            "coherence_gain": round(coherence_gain, 4),
            "productivity": round(productivity, 4),
        }

    def score_perspective_coverage(
        self, analyses: Dict[str, str],
    ) -> Dict[str, float]:
        """Score how deeply each RC+xi perspective is actually engaged.

        Returns:
            Dict mapping perspective name -> coverage score 0-1.
        """
        all_text_lower = {name: text.lower() for name, text in analyses.items()}
        coverage = {}
        for perspective, vocab in _PERSPECTIVE_VOCAB.items():
            # Check across all agents, not just the named agent
            all_words = " ".join(all_text_lower.values())
            hits = sum(1 for term in vocab if term in all_words)
            coverage[perspective] = round(hits / len(vocab), 4)
        return coverage

    def score_debate_convergence(
        self,
        round_analyses: List[Dict[str, str]],
    ) -> Dict[str, object]:
        """Track tension decay across multiple debate rounds.

        Takes a list of analyses dicts (one per round). Measures whether
        tension decreases (convergence) or increases (divergence).

        Returns:
            Dict with per-round tension, decay_rate, is_converging.
        """
        if not round_analyses:
            return {"per_round_tension": [], "decay_rate": 0.0, "is_converging": False}

        per_round = [self.score_tension_magnitude(a) for a in round_analyses]

        if len(per_round) >= 2:
            initial = per_round[0]
            final = per_round[-1]
            decay_rate = (initial - final) / max(initial, 1e-6)
        else:
            decay_rate = 0.0

        return {
            "per_round_tension": per_round,
            "decay_rate": round(decay_rate, 4),
            "is_converging": decay_rate > 0.05,
        }

    def full_epistemic_report(
        self,
        analyses: Dict[str, str],
        synthesis: str,
    ) -> Dict[str, object]:
        """Complete RC+xi metrics report for a single forge cycle."""
        return {
            "pairwise_tension": self.score_pairwise_tension(analyses),
            "tension_magnitude": self.score_tension_magnitude(analyses),
            "ensemble_coherence": self.score_ensemble_coherence(analyses),
            "perspective_coverage": self.score_perspective_coverage(analyses),
            "tension_productivity": self.score_tension_productivity(analyses, synthesis),
        }
