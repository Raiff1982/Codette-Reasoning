"""
Phase 6: RC+xi Framework Mathematical Definitions

Formalizes three core concepts as first-class mathematical objects:

ψ (Psi/State): Cognitive state vector in 5D manifold
  ψ = (ψ_psi, ψ_tau, ψ_chi, ψ_phi, ψ_lambda)
  - ψ_psi    ∈ [0, 1]   : Concept magnitude (epistemic weight)
  - ψ_tau    ∈ [0, 1]   : Temporal progression (causality)
  - ψ_chi    ∈ [-1, 2]  : Processing velocity (agility)
  - ψ_phi    ∈ [-1, 1]  : Emotional valence (ethical charge)
  - ψ_lambda ∈ [0, 1]   : Semantic diversity (concept breadth)

ξ (Xi/Tension): Epistemic tension between states
  ξ_structural(ψ_a, ψ_b) = sqrt(sum((ψ_a_i - ψ_b_i)^2 for all 5 dimensions))
  ξ_semantic(claim_a, claim_b) = 1.0 - cosine_similarity(embed(claim_a), embed(claim_b))
  ξ_combined = w_struct * ξ_struct + w_semantic * ξ_semantic (weighted blend)

Γ (Gamma/Coherence): System health and integrity
  Γ = (0.25 * perspective_diversity +
       0.25 * tension_health +
       0.25 * (1.0 - adapter_weight_variance) +
       0.25 * resolution_rate)
  Γ ∈ [0, 1]
  - Γ < 0.4   : Collapse (monoculture/weight drift detected)
  - 0.4 ≤ Γ ≤ 0.8: Healthy (productive tension)
  - Γ > 0.8   : Groupthink (false consensus, enforce conflict)
"""

from dataclasses import dataclass
from typing import List, Dict
import numpy as np


@dataclass
class StateVector:
    """
    ψ (Psi): Complete cognitive state in 5D manifold.

    Used for:
    - Representing query semantics in pre-flight prediction
    - Encoding agent analyses for Spiderweb injection
    - Measuring state-space distance between perspectives
    """
    psi: float      # [0, 1] concept magnitude / epistemic weight
    tau: float      # [0, 1] temporal progression / causality
    chi: float      # [-1, 2] processing velocity / agility
    phi: float      # [-1, 1] emotional valence / ethical charge
    lam: float      # [0, 1] semantic diversity / concept breadth

    def to_array(self) -> np.ndarray:
        """Convert to numpy array for distance calculations."""
        return np.array([self.psi, self.tau, self.chi, self.phi, self.lam], dtype=np.float32)

    def to_dict(self) -> Dict:
        """Export as dictionary for JSON serialization."""
        return {
            "psi": round(self.psi, 3),
            "tau": round(self.tau, 3),
            "chi": round(self.chi, 3),
            "phi": round(self.phi, 3),
            "lam": round(self.lam, 3),
        }

    @staticmethod
    def distance(state_a: "StateVector", state_b: "StateVector") -> float:
        """
        Compute ξ_structural: Euclidean distance in 5D state space.
        Range: [0, ~3.5] (theoretical max sqrt(4+4+9+4+1))
        """
        arr_a = state_a.to_array()
        arr_b = state_b.to_array()
        return float(np.linalg.norm(arr_a - arr_b))


@dataclass
class TensionDefinition:
    """
    ξ (Xi): Complete specification of epistemic tension.

    Blends structural (5D state distance) and semantic (embedding) components
    for nuanced conflict detection.
    """
    structural_xi: float      # [0, ~3.5] 5D state distance
    semantic_xi: float        # [0, 1] embedding-based semantic distance
    combined_xi: float        # [0, ~2] weighted combination
    opposition_type: str      # "contradiction" | "emphasis" | "framework" | "paraphrase"
    weight_structural: float  # 0.4 default, tuneable
    weight_semantic: float    # 0.6 default, tuneable

    def to_dict(self) -> Dict:
        """Export for analysis/benchmarking."""
        return {
            "structural_xi": round(self.structural_xi, 3),
            "semantic_xi": round(self.semantic_xi, 3),
            "combined_xi": round(self.combined_xi, 3),
            "opposition_type": self.opposition_type,
            "weight_structural": self.weight_structural,
            "weight_semantic": self.weight_semantic,
        }


@dataclass
class CoherenceMetrics:
    """
    Γ (Gamma): Detailed characterization of system coherence/health.

    Monitors four pillars; used by Phase 5 coherence_field to detect
    collapse/groupthink and trigger interventions.
    """
    perspective_diversity: float        # [0, 1] uniqueness of agent perspectives
    tension_health: float               # [0, 1] productivity of epistemic tensions
    adapter_weight_variance: float      # [0, 1] distribution across adapters
    resolution_rate: float              # [0, 1] conflicts resolved per round
    gamma_score: float                  # [0, 1] final coherence value
    health_status: str                  # "collapsing" | "healthy" | "groupthinking"

    @staticmethod
    def compute_gamma(
        perspective_diversity: float,
        tension_health: float,
        adapter_weight_variance: float,
        resolution_rate: float,
    ) -> tuple:
        """
        Compute Γ score from four pillars.

        Returns: (gamma_score, health_status)
        """
        gamma = (
            0.25 * perspective_diversity
            + 0.25 * tension_health
            + 0.25 * (1.0 - adapter_weight_variance)
            + 0.25 * resolution_rate
        )

        # Determine health status
        if gamma < 0.4:
            status = "collapsing"
        elif gamma > 0.8:
            status = "groupthinking"
        else:
            status = "healthy"

        return float(np.clip(gamma, 0.0, 1.0)), status

    def to_dict(self) -> Dict:
        """Export for monitoring/logging."""
        return {
            "perspective_diversity": round(self.perspective_diversity, 3),
            "tension_health": round(self.tension_health, 3),
            "adapter_weight_variance": round(self.adapter_weight_variance, 3),
            "resolution_rate": round(self.resolution_rate, 3),
            "gamma_score": round(self.gamma_score, 3),
            "health_status": self.health_status,
        }


@dataclass
class ConflictPrediction:
    """
    Output from pre-flight predictor.

    Captures predicted conflicts, dimension-wise profiles, and router
    recommendations before debate even begins.
    """
    query_state: StateVector                    # Encoded query ψ
    predicted_high_tension_pairs: List[Dict]    # Agent pairs likely to conflict
    conflict_profiles: Dict[str, List]          # Grouped by dimension (phi, tau, chi, etc)
    recommendations: Dict                        # {"boost": [...], "suppress": [...]}
    preflight_confidence: float                 # [0, 1] how confident in prediction

    def to_dict(self) -> Dict:
        """Export for metadata/analysis."""
        return {
            "query_state": self.query_state.to_dict(),
            "predicted_pairs_count": len(self.predicted_high_tension_pairs),
            "conflict_profiles": {k: len(v) for k, v in self.conflict_profiles.items()},
            "recommendations": self.recommendations,
            "preflight_confidence": round(self.preflight_confidence, 3),
        }


@dataclass
class SpecializationScore:
    """
    Measures adapter specialization within a domain.

    specialization = domain_accuracy / usage_frequency
    High score = expert in domain, not overused
    Low score = either poor performance or overtaxed
    """
    adapter: str                       # Adapter name
    domain: str                        # "physics", "ethics", "consciousness", etc.
    domain_accuracy: float             # [0, 1] mean coherence in domain
    usage_frequency: int               # Times used in domain
    specialization_score: float        # domain_accuracy / max(usage, 1)
    convergence_risk: bool             # Semantic overlap with similar adapters > 0.85
    recommendation: str                # "maintain" | "boost" | "suppress" | "diversify"

    def to_dict(self) -> Dict:
        """Export for adapter management."""
        return {
            "adapter": self.adapter,
            "domain": self.domain,
            "domain_accuracy": round(self.domain_accuracy, 3),
            "usage_frequency": self.usage_frequency,
            "specialization_score": round(self.specialization_score, 3),
            "convergence_risk": self.convergence_risk,
            "recommendation": self.recommendation,
        }
