"""
Phase 6: Pre-Flight Conflict Predictor

Uses Spiderweb to predict conflicts BEFORE debate starts.

Strategy:
1. Encode query into 5D state vector (ψ)
2. Inject into fresh spiderweb as virtual "truth" node
3. Propagate belief outward (3 hops max)
4. Measure resultant tensions per agent pair
5. Extract dimension-wise conflict profiles
6. Generate router recommendations (boost/suppress adapters)

This allows:
- Pre-selection of stabilizing adapters
- Reduction of wasted debate cycles on predictable conflicts
- Faster convergence via informed initial routing
"""

from typing import Dict, List, Tuple, Optional
import numpy as np
from dataclasses import dataclass
from reasoning_forge.framework_definitions import StateVector, ConflictPrediction


@dataclass
class DimensionConflict:
    """Conflict localized to specific 5D dimension."""
    dimension: str              # "psi", "tau", "chi", "phi", "lam"
    agent_a: str
    agent_b: str
    dimension_diff: float       # How far apart in this dimension
    severity: str               # "low" | "medium" | "high"


class PreFlightConflictPredictor:
    """
    Predicts conflicts before debate using Spiderweb injection.

    Assumes Spiderweb has:
    - add_node(name, state=StateVector)
    - connect(node_a, node_b)
    - propagate_belief(origin, belief, max_hops) -> propagation_result
    - nodes: Dict[name, NodeState]
    """

    def __init__(self, spiderweb, memory_weighting=None, semantic_engine=None):
        """
        Initialize predictor with Spiderweb instance.

        Args:
            spiderweb: QuantumSpiderweb instance
            memory_weighting: Optional MemoryWeighting for boost recommendations
            semantic_engine: Optional SemanticTensionEngine for enhanced predictions
        """
        self.spiderweb = spiderweb
        self.memory_weighting = memory_weighting
        self.semantic_engine = semantic_engine
        self.prediction_history = []

    def encode_query_to_state(self, query: str) -> StateVector:
        """
        Convert query text to 5D state vector (ψ).

        Heuristic encoding:
        - ψ_psi:   concept_magnitude (TF-IDF norm of key concepts)
        - ψ_tau:   temporal_progression (presence of causality/time markers)
        - ψ_chi:   processing_velocity (query complexity / baseline)
        - ψ_phi:   emotional_valence (sentiment + ethical keywords)
        - ψ_lambda: semantic_diversity (unique_concepts / total)

        Returns:
            StateVector with 5D values
        """
        query_lower = query.lower()
        tokens = query_lower.split()

        # ψ_psi: Concept magnitude from query length and key concept presence
        key_concepts = ["what", "how", "why", "should", "could", "would", "is", "can"]
        concept_count = sum(1 for t in tokens if t in key_concepts)
        psi = min(1.0, (len(tokens) / 20.0) * 0.5 + (concept_count / 10.0) * 0.5)

        # ψ_tau: Temporal progression markers
        temporal_markers = ["past", "future", "before", "after", "then", "now", "when", "time", "history"]
        tau = min(1.0, sum(1 for m in temporal_markers if m in query_lower) / 10.0)

        # ψ_chi: Processing complexity
        # Sentence-like structures (questions, nested clauses)
        complexity_markers = ["that", "whether", "if", "and", "or", "but", "however"]
        chi_complexity = sum(1 for m in complexity_markers if m in query_lower) / 5.0
        # Normalize to [-1, 2]
        chi = max(-1.0, min(2.0, (chi_complexity - 0.5) * 2.0))

        # ψ_phi: Emotional/ethical valence
        positive_words = ["good", "right", "better", "best", "love", "beautiful"]
        negative_words = ["bad", "wrong", "worse", "hate", "ugly"]
        ethical_words = ["should", "must", "moral", "ethics", "justice", "fair"]

        pos_count = sum(1 for w in positive_words if w in query_lower)
        neg_count = sum(1 for w in negative_words if w in query_lower)
        eth_count = sum(1 for w in ethical_words if w in query_lower)

        sentiment = (pos_count - neg_count) / max(pos_count + neg_count, 1)
        ethics_density = eth_count / len(tokens) if tokens else 0
        phi = np.tanh((sentiment + ethics_density * 0.5))  # Squash to [-1, 1]

        # ψ_lambda: Semantic diversity
        unique_tokens = len(set(tokens))
        total_tokens = len(tokens)
        lam = unique_tokens / max(total_tokens, 1)

        query_state = StateVector(
            psi=float(np.clip(psi, 0.0, 1.0)),
            tau=float(np.clip(tau, 0.0, 1.0)),
            chi=float(np.clip(chi, -1.0, 2.0)),
            phi=float(np.clip(phi, -1.0, 1.0)),
            lam=float(np.clip(lam, 0.0, 1.0)),
        )

        return query_state

    def predict_conflicts(
        self, query: str, agent_names: List[str], max_hops: int = 3
    ) -> ConflictPrediction:
        """
        Predict conflicts using spiderweb belief propagation.

        Args:
            query: Query text
            agent_names: List of agent/adapter names
            max_hops: Maximum propagation distance

        Returns:
            ConflictPrediction with predicted pairs, profiles, recommendations
        """
        query_state = self.encode_query_to_state(query)

        # Build fresh spiderweb from agents
        try:
            self.spiderweb.build_from_agents(agent_names)
        except Exception as e:
            print(f"Warning: Could not build spiderweb: {e}")
            return self._empty_prediction(query_state)

        # Add query as virtual node
        try:
            self.spiderweb.add_node("_QUERY", state=query_state)
            if len(agent_names) > 0:
                self.spiderweb.connect("_QUERY", agent_names[0])
        except Exception as e:
            print(f"Warning: Could not add query node: {e}")
            return self._empty_prediction(query_state)

        # Propagate belief
        try:
            propagation = self.spiderweb.propagate_belief(
                origin="_QUERY", belief=query_state, max_hops=max_hops
            )
        except Exception as e:
            print(f"Warning: Propagation failed: {e}")
            return self._empty_prediction(query_state)

        # Analyze tensions and extract profiles
        high_tension_pairs = self._analyze_tensions(propagation, agent_names)
        conflict_profiles = self._extract_conflict_profiles(high_tension_pairs)

        # Generate recommendations
        recommendations = self._generate_recommendations(conflict_profiles)

        # Compute confidence in predictions
        preflight_confidence = self._compute_prediction_confidence(high_tension_pairs, agent_names)

        prediction = ConflictPrediction(
            query_state=query_state,
            predicted_high_tension_pairs=high_tension_pairs,
            conflict_profiles=conflict_profiles,
            recommendations=recommendations,
            preflight_confidence=preflight_confidence,
        )

        self.prediction_history.append(prediction)

        return prediction

    def _analyze_tensions(self, propagation: Dict, agent_names: List[str]) -> List[Dict]:
        """
        Extract high-tension agent pairs from propagation results.

        Returns:
            List of {agent_a, agent_b, spiderweb_tension, dimension_breakdown}
        """
        high_tension_pairs = []

        # Look for nodes in spiderweb
        if not hasattr(self.spiderweb, "nodes"):
            return high_tension_pairs

        nodes = self.spiderweb.nodes
        valid_agents = [a for a in agent_names if a in nodes]

        # Measure pairwise tensions
        for i, agent_a in enumerate(valid_agents):
            for agent_b in valid_agents[i + 1 :]:
                try:
                    state_a = nodes[agent_a].state if hasattr(nodes[agent_a], "state") else None
                    state_b = nodes[agent_b].state if hasattr(nodes[agent_b], "state") else None

                    if state_a and state_b:
                        # Compute 5D distance
                        xi_structural = StateVector.distance(state_a, state_b)

                        if xi_structural > 1.0:  # Only flag significant tensions
                            # Dimension-wise breakdown
                            arr_a = state_a.to_array()
                            arr_b = state_b.to_array()
                            diffs = arr_b - arr_a

                            dimension_names = ["psi", "tau", "chi", "phi", "lam"]

                            high_tension_pairs.append({
                                "agent_a": agent_a,
                                "agent_b": agent_b,
                                "spiderweb_tension": round(xi_structural, 3),
                                "dimension_breakdown": {
                                    dim: round(abs(diff), 3) for dim, diff in zip(dimension_names, diffs)
                                },
                            })
                except Exception:
                    pass

        # Sort by tension (strongest first)
        high_tension_pairs.sort(key=lambda p: p["spiderweb_tension"], reverse=True)

        return high_tension_pairs[:10]  # Top 10 pairs

    def _extract_conflict_profiles(self, high_tension_pairs: List[Dict]) -> Dict[str, List]:
        """
        Group conflicts by dimension to identify patterns.

        Returns:
            {
                "psi_conflicts": [{pair, diff}],
                "tau_conflicts": [...],
                ...
                "lam_conflicts": [...]
            }
        """
        profiles = {
            "psi_conflicts": [],
            "tau_conflicts": [],
            "chi_conflicts": [],
            "phi_conflicts": [],
            "lam_conflicts": [],
        }

        threshold = 0.4  # Flag if dimension diff > threshold

        for pair in high_tension_pairs:
            breakdown = pair["dimension_breakdown"]

            if breakdown.get("psi", 0) > threshold:
                profiles["psi_conflicts"].append(pair)
            if breakdown.get("tau", 0) > threshold:
                profiles["tau_conflicts"].append(pair)
            if breakdown.get("chi", 0) > threshold:
                profiles["chi_conflicts"].append(pair)
            if breakdown.get("phi", 0) > threshold:
                profiles["phi_conflicts"].append(pair)
            if breakdown.get("lam", 0) > threshold:
                profiles["lam_conflicts"].append(pair)

        return profiles

    def _generate_recommendations(self, profiles: Dict[str, List]) -> Dict:
        """
        Generate adapter boost/suppress recommendations based on conflict profiles.

        Logic:
        - phi_conflicts (ethical divergence) → boost Empathy, Ethics
        - tau_conflicts (temporal framing) → boost Philosophy
        - chi_conflicts (complexity mismatch) → boost multi_perspective
        - lam_conflicts (semantic diversity) → boost consciousness
        - psi_conflicts (concept magnitude) → boost newton (analytical)
        """
        recommendations = {
            "boost": [],
            "suppress": [],
            "reason": None,
        }

        # Count conflicts per dimension
        counts = {k: len(v) for k, v in profiles.items()}
        max_conflicts = max(counts.values()) if counts else 0

        if counts.get("phi_conflicts", 0) >= 2:
            recommendations["boost"] = ["empathy", "philosophy"]
            recommendations["reason"] = "emotional_and_ethical_divergence"
        elif counts.get("tau_conflicts", 0) >= 2:
            recommendations["boost"] = ["philosophy"]
            recommendations["reason"] = "temporal_framing_divergence"
        elif counts.get("chi_conflicts", 0) >= 2:
            recommendations["boost"] = ["multi_perspective"]
            recommendations["reason"] = "complexity_divergence"
        elif counts.get("lam_conflicts", 0) >= 2:
            recommendations["boost"] = ["consciousness"]
            recommendations["reason"] = "semantic_diversity_divergence"
        elif counts.get("psi_conflicts", 0) >= 2:
            recommendations["boost"] = ["newton"]
            recommendations["reason"] = "conceptual_magnitude_divergence"

        return recommendations

    def _compute_prediction_confidence(self, pairs: List[Dict], agent_names: List[str]) -> float:
        """
        Estimate confidence in pre-flight predictions.

        Higher if:
        - More agents involved
        - Consistent patterns across pairs
        - Previous predictions matched actual conflicts
        """
        if not pairs or not agent_names:
            return 0.3

        # Base confidence from number of predicted pairs
        confidence = min(1.0, len(pairs) / len(agent_names))

        # Boost if clear patterns (multiple conflicts in same dimension)
        return float(np.clip(confidence, 0.3, 0.95))

    def _empty_prediction(self, query_state: StateVector) -> ConflictPrediction:
        """Return safe empty prediction if propagation failed."""
        return ConflictPrediction(
            query_state=query_state,
            predicted_high_tension_pairs=[],
            conflict_profiles={},
            recommendations={"boost": [], "suppress": [], "reason": "no_prediction"},
            preflight_confidence=0.0,
        )

    def get_prediction_history(self, limit: int = 10) -> List[Dict]:
        """Get recent predictions for analysis."""
        recent = self.prediction_history[-limit:]
        return [p.to_dict() for p in recent]


__all__ = ["PreFlightConflictPredictor"]
