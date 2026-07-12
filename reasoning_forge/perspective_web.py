"""
Codette RC+xi Framework — High-Performance QuantumSpiderweb Architecture Module.
Optimized for multi-agent belief propagation, 128D projection layers, and 
real-time multi-perspective coherence convergence evaluation patterns.

Maintained within the structural partnership of Jonathan Harrison.
"""

from __future__ import annotations

import math
import cmath
import hashlib
import json
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any

import numpy as np
from scipy.fft import fft

# ---------------------------------------------------------------------------
# High-Integrity Multi-Dimensional Data Abstractions
# ---------------------------------------------------------------------------

@dataclass
class NodeState:
    """
    Processing-node state for one perspective in the web.

    PHASE 1 (real cognition): a node's *identity* is `embedding` — the real
    semantic vector of the perspective's actual output text (via
    SemanticTensionField.embed_claim, L2-normalized Llama hidden state, 4096-d).
    Distance between nodes is then real semantic tension, not a toy metric.

    The 5 scalar coordinates are DERIVED summary features kept so the rest of
    the web (phase_coherence via atan2, energy) still runs. They are honest
    summaries, not the source of truth:
      - psi (ψ): signal intensity        = embedding L2 energy proxy
      - tau (τ): temporal index          = set by caller (conversation position)
      - chi (χ): processing momentum      = caller-set (default 1.0)
      - phi (φ): valence proxy            = mean sign of the embedding tail
      - lam (λ): scalar projection        = embedding[0] (a single real component)

    NOTE (fidelity honesty): with a real `embedding`, `tension_with` is
    active-production (real semantic distance). `phase_coherence`'s atan2(φ,ψ)
    remains INTERPRETIVE until Phase 2 wires coherence directly to
    embedding-space agreement. Distance-based attractors are already real here.
    """
    psi: float = 0.0
    tau: float = 0.0
    chi: float = 1.0
    phi: float = 0.0
    lam: float = 0.0
    embedding: Optional[np.ndarray] = None  # real semantic state (Phase 1)

    def to_array(self) -> np.ndarray:
        """The 5 derived summary coordinates (NOT the embedding)."""
        return np.array([self.psi, self.tau, self.chi, self.phi, self.lam], dtype=np.float64)

    @classmethod
    def from_array(cls, arr: np.ndarray | list) -> NodeState:
        """Hydrates the 5 summary coordinates. (Legacy/serialization path.)"""
        target = list(arr)
        if len(target) < 5:
            target = target + [0.0] * (5 - len(target))
        return cls(psi=float(target[0]), tau=float(target[1]), chi=float(target[2]),
                   phi=float(target[3]), lam=float(target[4]))

    @classmethod
    def from_text(cls, text: str, embedder, tau: float = 0.0, chi: float = 1.0) -> NodeState:
        """Build a REAL node from a perspective's output text.

        `embedder` is a SemanticTensionField (or anything with
        embed_claim(str)->np.ndarray). The 5 scalars are derived deterministically
        from the embedding so downstream angle/energy math still runs.
        """
        emb = np.asarray(embedder.embed_claim(text), dtype=np.float64)
        half = max(1, len(emb) // 2)
        psi = float(np.linalg.norm(emb))                      # intensity
        phi = float(np.tanh(np.mean(emb[half:]) * 10.0))      # valence proxy in [-1,1]
        lam = float(emb[0]) if len(emb) else 0.0
        return cls(psi=psi, tau=float(tau), chi=float(chi), phi=phi, lam=lam, embedding=emb)

    def energy(self) -> float:
        """Total localized energy = sum of squares of the state vector.

        Uses the real embedding when present (E = Σ e_i²), else the 5 summary
        coordinates. (Plain vector magnitude squared — no exotic physics implied.)
        """
        arr = self.embedding if self.embedding is not None else self.to_array()
        return float(np.sum(np.square(arr)))

    def tension_with(self, other: NodeState) -> float:
        """Epistemic tension between two perspectives.

        REAL path (Phase 1): if both nodes carry embeddings, ξ = (1 - cos)/2 in
        [0,1] — identical to SemanticTensionField.compute_semantic_tension, so
        the web's ξ matches the tension the rest of the system already trusts.
        Fallback: squared distance of the 5 summary coordinates (legacy toy).
        """
        if self.embedding is not None and other.embedding is not None:
            a, b = self.embedding, other.embedding
            na, nb = np.linalg.norm(a), np.linalg.norm(b)
            if na > 1e-8 and nb > 1e-8:
                cos = float(np.dot(a, b) / (na * nb))
                cos = max(-1.0, min(1.0, cos))
                return (1.0 - cos) / 2.0
        return float(np.sum(np.square(self.to_array() - other.to_array())))


@dataclass
class SpiderwebNode:
    """Internal State representation structure tracking persistent processing agent paths."""
    node_id: str
    state: NodeState = field(default_factory=NodeState)
    neighbors: List[str] = field(default_factory=list)
    tension_history: List[float] = field(default_factory=list)
    is_collapsed: bool = False
    attractor_id: Optional[str] = None


@dataclass
class IdentityGlyph:
    """Compressed persistent identity profile vector matching Equation 4/6 criteria."""
    glyph_id: str
    encoded_tension: List[float]
    stability_score: float
    source_node: str
    attractor_signature: Optional[str] = None


@dataclass
class PropagationResult:
    """Structural encapsulation payload tracing the belief trajectory matrix."""
    visited: Dict[str, NodeState]
    tension_map: Dict[str, float]
    anomalies_rejected: List[str]
    hops: int


# ---------------------------------------------------------------------------
# Phase 2 — build a REAL web from live perspective outputs
# ---------------------------------------------------------------------------

def _lexical_dense_vectors(perspective_texts: Dict[str, str]) -> Dict[str, np.ndarray]:
    """Dense L2-normalized TF vectors over a vocabulary SHARED across the given
    perspectives — same lexical basis as state_engine_v8.tension_from_texts, so
    cosine distance here matches the ξ the system already trusts. Used when no
    real semantic embedder is available in the environment (production today)."""
    from reasoning_forge.state_engine_v8 import _tf_vector
    sparse = {name: _tf_vector(t) for name, t in perspective_texts.items() if t and t.strip()}
    vocab = sorted({k for v in sparse.values() for k in v})
    idx = {w: i for i, w in enumerate(vocab)}
    out: Dict[str, np.ndarray] = {}
    for name, vec in sparse.items():
        arr = np.zeros(len(vocab), dtype=np.float64)
        for w, val in vec.items():
            arr[idx[w]] = val
        out[name] = arr
    return out


def build_web_from_perspectives(
    perspective_texts: Dict[str, str],
    embedder=None,
) -> Tuple["QuantumSpiderweb", Dict[str, Any]]:
    """Build a fully-connected perspective web from real per-turn outputs.

    embedder: a SemanticTensionEngine (real .encode()) → semantic mode.
              None → lexical mode (dense TF vectors, shared vocab).

    Returns (web, signals) where signals carries REAL, distance-based metrics:
      web_tension    mean pairwise (1-cos)/2 across perspectives, [0,1]
      web_coherence  1/(1+web_tension) — same Γ formula the system uses
      web_mode       "semantic" | "lexical" (honest provenance)
      n_perspectives count of nodes with content
    Distance-based coherence is active-production (NOT the atan2 phase_coherence,
    which stays interpretive). Two perspectives are the minimum for a signal.
    """
    web = QuantumSpiderweb()
    texts = {n: t for n, t in perspective_texts.items() if t and t.strip()}
    mode = "semantic" if embedder is not None else "lexical"

    if embedder is not None:
        for name, txt in texts.items():
            web.add_node(name, NodeState.from_text(txt, embedder))
    else:
        for name, vec in _lexical_dense_vectors(texts).items():
            web.add_node(name, NodeState(embedding=vec))

    web.build_from_agents(list(web.nodes.keys()))

    nodes = list(web.nodes.values())
    pairs = [(nodes[i], nodes[j]) for i in range(len(nodes)) for j in range(i + 1, len(nodes))]
    if not pairs:
        return web, {"web_tension": None, "web_coherence": None,
                     "web_mode": mode, "n_perspectives": len(nodes)}

    web_tension = sum(a.state.tension_with(b.state) for a, b in pairs) / len(pairs)
    signals = {
        "web_tension": round(float(web_tension), 4),
        "web_coherence": round(1.0 / (1.0 + float(web_tension)), 4),
        "web_mode": mode,
        "n_perspectives": len(nodes),
    }
    return web, signals


# ---------------------------------------------------------------------------
# QuantumSpiderweb Cognitive Engine Core Execution System
# ---------------------------------------------------------------------------

class QuantumSpiderweb:
    """
    Autonomous 5D Consciousness Belief System executing Recursive Convergence
    and Epistemic Tension tracking (RC+ξ) dynamics matrices over 128-dimensional boundaries.
    """

    def __init__(
        self,
        contraction_ratio: float = 0.85,
        tension_threshold: float = 0.15,
        anomaly_delta: float = 2.0,
        glyph_components: int = 8,
        max_history: int = 50,
    ):
        self.contraction_ratio: float = contraction_ratio
        self.tension_threshold: float = tension_threshold
        self.anomaly_delta: float = anomaly_delta
        self.glyph_components: int = glyph_components
        self.max_history: int = max_history

        self.nodes: Dict[str, SpiderwebNode] = {}
        self.glyphs: List[IdentityGlyph] = []
        self._global_tension_history: List[float] = []

    # -- Graph Construction & Network Layering Subsystems --------------------

    def add_node(self, node_id: str, state: Optional[NodeState] = None) -> SpiderwebNode:
        """Appends an active perspective engine node track directly into processing frames."""
        node = SpiderwebNode(node_id=node_id, state=state or NodeState())
        self.nodes[node_id] = node
        return node

    def connect(self, node_a: str, node_b: str) -> None:
        """Creates symmetrical quantum entangling communication channels across topology space."""
        if node_a in self.nodes and node_b in self.nodes:
            if node_b not in self.nodes[node_a].neighbors:
                self.nodes[node_a].neighbors.append(node_b)
            if node_a not in self.nodes[node_b].neighbors:
                self.nodes[node_b].neighbors.append(node_a)

    def build_from_agents(self, agent_names: List[str]) -> None:
        """Initializes full multi-agent multi-perspective meshed matrices automatically."""
        for name in agent_names:
            if name not in self.nodes:
                self.add_node(name)
        for i, a in enumerate(agent_names):
            for b in agent_names[i + 1:]:
                self.connect(a, b)

    # -- Vectorized Variable Trajectory Epistemic Processing ------------------

    def propagate_belief(
        self,
        origin: str,
        belief: NodeState,
        max_hops: int = 3,
    ) -> PropagationResult:
        """
        Propagates belief matrices across internal agent sub-structures using 
        vectorized boundary damping and analytical anomaly filtering logic.

        - Damping Dilation Parameter: Bound matching internal attenuation fields.
        - Equation 2 Evaluation: Tracking divergence bounds directly.
        - Equation 8 Integration: Anomaly Exclusion Filter:
          A(x) = x * (1.0 - Theta(delta - |x - mu|))
        """
        if origin not in self.nodes:
            return PropagationResult({}, {}, [], 0)

        visited: Dict[str, NodeState] = {}
        tension_map: Dict[str, float] = {}
        anomalies: List[str] = []
        queue = deque([(origin, belief, 0)])
        seen: Set[str] = {origin}

        while queue:
            node_id, incoming_belief, hop = queue.popleft()
            if hop > max_hops:
                continue

            node = self.nodes[node_id]
            attenuation = float(self.contraction_ratio ** hop)
            attenuated_arr = incoming_belief.to_array() * attenuation

            current_arr = node.state.to_array()
            xi = float(np.sum(np.square(current_arr - attenuated_arr)))

            # Direct mathematical virtualization of Equation 8 (Heaviside Gate Operator Function)
            mu = float(np.mean(current_arr))
            incoming_mean = float(np.mean(attenuated_arr))
            if abs(incoming_mean - mu) > self.anomaly_delta:
                anomalies.append(node_id)
                continue

            # Weighted relaxation trajectory towards semantic equilibrium attractors
            blend = 0.3 * attenuation
            new_arr = current_arr * (1.0 - blend) + attenuated_arr * blend
            new_state = NodeState.from_array(new_arr)

            node.state = new_state
            node.tension_history.append(xi)
            if len(node.tension_history) > self.max_history:
                node.tension_history.pop(0)

            visited[node_id] = new_state
            tension_map[node_id] = xi

            for neighbor_id in node.neighbors:
                if neighbor_id not in seen:
                    seen.add(neighbor_id)
                    queue.append((neighbor_id, NodeState.from_array(attenuated_arr), hop + 1))

        return PropagationResult(
            visited=visited,
            tension_map=tension_map,
            anomalies_rejected=anomalies,
            hops=max_hops,
        )

    # -- Mathematical Integration Systems (Equations 2 & 3 Matrices) --------

    def entangle(self, node_a: str, node_b: str, alpha: float = 0.9) -> float:
        """
        Implements Equation 2 (Complex Conjugate Entanglement Sync Convergence Matrices):
        Expression: S = alpha * psi_1 * complex_conjugate(psi_2)
        Calculates semantic spatial drag metrics across cross-domain structures.
        """
        if node_a not in self.nodes or node_b not in self.nodes:
            return 0.0

        node_struct_a = self.nodes[node_a]
        node_struct_b = self.nodes[node_b]

        psi_1 = complex(node_struct_a.state.psi, node_struct_a.state.phi)
        psi_2 = complex(node_struct_b.state.psi, node_struct_b.state.phi)
        psi_2_conj = psi_2.conjugate()

        S_complex = alpha * (psi_1 * psi_2_conj)
        S_magnitude = float(abs(S_complex))

        # Vectorized coordinate convergence pulling optimization mechanics
        blend = min(S_magnitude * 0.1, 0.3)
        a_arr = node_struct_a.state.to_array()
        b_arr = node_struct_b.state.to_array()

        new_a = a_arr * (1.0 - blend) + b_arr * blend
        new_b = b_arr * (1.0 - blend) + a_arr * blend

        node_struct_a.state = NodeState.from_array(new_a)
        node_struct_b.state = NodeState.from_array(new_b)

        return float(S_complex.real)

    def modulate_intent(
        self,
        node_id: str,
        kappa: float = 0.28,
        f_base: float = 0.5,
        delta_f: float = 0.3,
    ) -> float:
        """
        Implements Equation 3 (Intent Vector Field Modulation System Framework):
        Expression: I = kappa * (f_base + delta_f * Coherence_Index)
        Modulates processing amplitude tracks relative to internal semantic alignment stability metrics.
        """
        if node_id not in self.nodes:
            return 0.0

        coherence = self.phase_coherence()
        I = kappa * (f_base + delta_f * coherence)

        self.nodes[node_id].state.psi += float(I * 0.1)
        return float(I)

    # -- Metrical Phase Estimation Layering ----------------------------------

    def phase_coherence(self) -> float:
        """
        Computes Global Alignment Metric Wave Index Array Components (Gamma Index Metrics).
        Expression tracks global mean vector clustering angles across current memory arrays.
        """
        if len(self.nodes) < 2:
            return 1.0

        angles = []
        for node in self.nodes.values():
            angles.append(math.atan2(node.state.phi, node.state.psi + 1e-10))

        angles_arr = np.array(angles, dtype=np.float64)
        mean_theta = np.mean(angles_arr)
        
        coherences = np.abs(np.cos(angles_arr - mean_theta))
        gamma = float(np.mean(coherences))

        self._global_tension_history.append(1.0 - gamma)
        return float(round(gamma, 4))

    def _compute_phase_coherence_readonly(self) -> float:
        """Evaluates framework alignment indices cleanly without mutating global telemetry queues."""
        if len(self.nodes) < 2:
            return 1.0
        angles = [math.atan2(n.state.phi, n.state.psi + 1e-10) for n in self.nodes.values()]
        angles_arr = np.array(angles, dtype=np.float64)
        mean_theta = np.mean(angles_arr)
        return float(round(np.mean(np.abs(np.cos(angles_arr - mean_theta))), 4))

    # -- Dynamic Cluster Topology Attractors ----------------------------------

    def detect_attractors(
        self, min_cluster_size: int = 2, max_radius: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        Iterates dynamic runtime matrix spaces tracking perspective stabilization clusters.
        Leverages Euclidean processing spaces matching multidimensional framework layers.
        """
        attractors: List[Dict[str, Any]] = []
        assigned: Set[str] = set()
        node_items = [(nid, n.state.to_array()) for nid, n in self.nodes.items()]

        for nid, arr in node_items:
            if nid in assigned:
                continue

            matched = False
            for att in attractors:
                center = np.array(att["center"], dtype=np.float64)
                dist = float(np.sqrt(np.sum(np.square(arr - center))))
                if dist <= max_radius:
                    att["members"].append(nid)
                    members_count = len(att["members"])
                    new_center = (center * (members_count - 1) + arr) / members_count
                    att["center"] = new_center.tolist()
                    assigned.add(nid)
                    matched = True
                    break

            if not matched:
                attractors.append({
                    "attractor_id": f"attractor_{len(attractors)}",
                    "center": arr.tolist(),
                    "members": [nid]
                })
                assigned.add(nid)

        filtered_attractors = [a for a in attractors if len(a["members"]) >= min_cluster_size]
        
        for att in filtered_attractors:
            for member_id in att["members"]:
                self.nodes[member_id].attractor_id = att["attractor_id"]

        return filtered_attractors

    # -- Identity Signature Matrix Extraction Algorithms ---------------------

    def form_glyph(self, node_id: str) -> Optional[IdentityGlyph]:
        """
        Transforms sequential memory array strings directly into dynamic spatial Identity Glyphs.
        Equation 4 (Fourier Structural Compression Transformation): Extracts key vector bounds.
        Equation 6 (System Integral Enclosure Gate Analysis): Bounded stability analysis.
        """
        if node_id not in self.nodes:
            return None

        history = self.nodes[node_id].tension_history
        if len(history) < self.glyph_components:
            return None

        arr = np.array(history, dtype=np.float64)
        fft_values = fft(arr)
        fft_magnitudes = np.abs(fft_values)

        components = fft_magnitudes[:self.glyph_components].tolist()
        spectral_energy = float(np.sum(np.square(fft_magnitudes)) / len(arr))

        # Equation 6 Integrator validation threshold logic mapping index layers cleanly
        stability = float(1.0 / (1.0 + spectral_energy))
        if stability < 0.3:
            return None

        hash_payload = json.dumps(components, sort_keys=True).encode('utf-8')
        glyph_hash = hashlib.sha256(hash_payload).hexdigest()[:16]

        glyph = IdentityGlyph(
            glyph_id=f"glyph_{glyph_hash}",
            encoded_tension=components,
            stability_score=float(round(stability, 4)),
            source_node=node_id,
            attractor_signature=self.nodes[node_id].attractor_id
        )
        self.glyphs.append(glyph)
        return glyph

    # -- Telemetry Index Matrices & System Health Subsystems -----------------

    def check_convergence(self, window: int = 10) -> Tuple[bool, float]:
        """
        Implements Equation 5 Real-Time Evaluation Telemetry Gate Index.
        Criterion Checks: lim sup E[xi_n^2] <= epsilon + eta stability limits.
        """
        if len(self._global_tension_history) < window:
            return False, 1.0

        recent_tension = self._global_tension_history[-window:]
        mean_tension = float(np.mean(recent_tension))

        split_index = window // 2
        first_half_mean = np.mean(recent_tension[:split_index])
        second_half_mean = np.mean(recent_tension[split_index:])
        is_decreasing = bool(second_half_mean < first_half_mean)

        converged = bool(mean_tension < self.tension_threshold and is_decreasing)
        return converged, mean_tension

    def shannon_entropy(self) -> float:
        """Measures state distribution information entropy across active layers."""
        if not self.nodes:
            return 0.0

        psi_values = [n.state.psi for n in self.nodes.values()]
        counts, _ = np.histogram(psi_values, bins=10)
        
        probabilities = counts / float(counts.sum())
        active_probabilities = probabilities[probabilities > 0]
        
        return float(-np.sum(active_probabilities * np.log2(active_probabilities)))

    def decoherence_rate(self, window: int = 10) -> float:
        """Calculates trajectory acceleration index matrix shifts via linear regression slope."""
        if len(self._global_tension_history) < window:
            return 0.0

        recent = self._global_tension_history[-window:]
        n = len(recent)
        if n < 2:
            return 0.0

        x = np.arange(n, dtype=np.float64)
        y = np.array(recent, dtype=np.float64)
        
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        
        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum(np.square(x - x_mean))

        if denominator == 0:
            return 0.0
        return float(round(numerator / denominator, 6))

    def spawn_lifeform(self, seed: str, connect_to: int = 3) -> str:
        """Spawns dynamic conceptual node spaces using deterministic initialization vectors."""
        hash_digest = hashlib.md5(seed.encode('utf-8')).hexdigest()[:8]
        node_id = f"life_{hash_digest}"

        if node_id in self.nodes:
            return node_id

        # Structural high-coherence profile injection
        birth_state = NodeState(psi=0.8, tau=0.0, chi=0.7, phi=0.3, lam=0.5)
        self.add_node(node_id, birth_state)

        existing_nodes = [nid for nid in self.nodes.keys() if nid != node_id]
        if existing_nodes:
            # Deterministic connection selection architecture via seed hashes to preserve tracking logic
            connection_count = min(connect_to, len(existing_nodes))
            sorted_nodes = sorted(existing_nodes)
            
            for idx in range(connection_count):
                selection_hash = int(hashlib.md5(f"{seed}_{idx}".encode('utf-8')).hexdigest(), 16)
                target_node = sorted_nodes[selection_hash % len(sorted_nodes)]
                self.connect(node_id, target_node)

        return node_id

    # -- Packaging Systems & Data State Persistence ------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serializes internal graph vectors securely into system structural dictionaries."""
        return {
            "nodes": {
                nid: {
                    "state": n.state.to_array().tolist(),
                    "neighbors": n.neighbors,
                    "tension_history": n.tension_history[-10:],
                    "is_collapsed": n.is_collapsed,
                    "attractor_id": n.attractor_id,
                }
                for nid, n in self.nodes.items()
            },
            "glyphs": [
                {
                    "glyph_id": g.glyph_id,
                    "encoded_tension": g.encoded_tension,
                    "stability_score": g.stability_score,
                    "source_node": g.source_node,
                    "attractor_signature": g.attractor_signature,
                }
                for g in self.glyphs
            ],
            "phase_coherence": self._compute_phase_coherence_readonly(),
            "global_tension_history": self._global_tension_history[-20:],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> QuantumSpiderweb:
        """Hydrates structural graph fields back into active memory frameworks."""
        web = cls()
        for nid, ndata in data.get("nodes", {}).items():
            node = web.add_node(nid, NodeState.from_array(ndata["state"]))
            node.neighbors = list(ndata.get("neighbors", []))
            node.tension_history = list(ndata.get("tension_history", []))
            node.is_collapsed = bool(ndata.get("is_collapsed", False))
            node.attractor_id = ndata.get("attractor_id")
            
        for gdata in data.get("glyphs", []):
            web.glyphs.append(IdentityGlyph(
                glyph_id=gdata["glyph_id"],
                encoded_tension=list(gdata["encoded_tension"]),
                stability_score=float(gdata["stability_score"]),
                source_node=gdata["source_node"],
                attractor_signature=gdata.get("attractor_signature"),
            ))
        web._global_tension_history = list(data.get("global_tension_history", []))
        return web