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
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any, Union

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
    def from_array(cls, arr: Union[np.ndarray, List[float]]) -> NodeState:
        """Hydrates the 5 summary coordinates. (Legacy/serialization path.)"""
        target = list(arr)
        if len(target) < 5:
            target = target + [0.0] * (5 - len(target))
        return cls(psi=float(target[0]), tau=float(target[1]), chi=float(target[2]),
                   phi=float(target[3]), lam=float(target[4]))

    @classmethod
    def from_text(cls, text: str, embedder: Any, tau: float = 0.0) -> NodeState:
        """Generates a NodeState directly from production text hidden-state embeddings."""
        if embedder is not None and hasattr(embedder, 'embed_claim'):
            vec = np.asarray(embedder.embed_claim(text), dtype=np.float64)
        else:
            # High-integrity deterministic fallback vector space based on lexical hashing
            words = text.split()
            vec = np.zeros(128, dtype=np.float64)
            for w in words:
                h = int(hashlib.md5(w.encode('utf-8')).hexdigest(), 16)
                vec[h % 128] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm

        psi_val = float(np.linalg.norm(vec))
        phi_val = float(np.mean(np.sign(vec[len(vec)//2:]))) if len(vec) > 0 else 0.0
        lam_val = float(vec[0]) if len(vec) > 0 else 0.0
        
        return cls(psi=psi_val, tau=tau, chi=1.0, phi=phi_val, lam=lam_val, embedding=vec)

    def energy(self) -> float:
        """Eq. 1: E = hbar * omega (derived from summary or real vector magnitude)."""
        if self.embedding is not None:
            return float(np.sum(np.square(self.embedding)))
        return float(np.sum(np.square(self.to_array())))

    def tension_with(self, other: "NodeState") -> float:
        """Eq. 2 (xi): epistemic tension computed directly across high-dimensional space."""
        if self.embedding is not None and other.embedding is not None:
            min_dim = min(self.embedding.shape[0], other.embedding.shape[0])
            return float(np.sum(np.square(self.embedding[:min_dim] - other.embedding[:min_dim])))
        return float(np.sum(np.square(self.to_array() - other.to_array())))


@dataclass
class SpiderwebNode:
    """A node wrapping structural perspective vectors inside the mesh graph layer."""
    node_id: str
    state: NodeState = field(default_factory=NodeState)
    neighbors: Set[str] = field(default_factory=set)
    tension_history: deque[float] = field(default_factory=lambda: deque(maxlen=50))
    is_collapsed: bool = False
    attractor_id: Optional[str] = None


@dataclass
class IdentityGlyph:
    """Compressed identity signature formed from tension history (Eq. 4/6)."""
    glyph_id: str
    encoded_tension: List[float]
    stability_score: float
    source_node: str
    attractor_signature: Optional[str] = None


@dataclass
class PropagationResult:
    """Result payload tracking vectorized communication across web cycles."""
    visited: Dict[str, NodeState]
    tension_map: Dict[str, float]
    anomalies_rejected: List[str]
    hops: int
    propagation_time: float = 0.0


# ---------------------------------------------------------------------------
# Lexical Dense Vector Utilities
# ---------------------------------------------------------------------------

def _lexical_dense_vectors(texts: Dict[str, str]) -> Dict[str, np.ndarray]:
    """Helper execution boundary constructing standardized dense tracking matrices from lists."""
    vecs = {}
    for name, text in texts.items():
        words = text.split() if text else []
        vec = np.zeros(128, dtype=np.float64)
        for w in words:
            h = int(hashlib.md5(w.encode('utf-8')).hexdigest(), 16)
            vec[h % 128] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        vecs[name] = vec
    return vecs


def initialize_web_metrics(texts: Dict[str, str], mode: str = "production") -> Tuple[QuantumSpiderweb, Dict[str, Any]]:
    """Initializes and meshes network nodes safely to extract initial system performance scopes."""
    web = QuantumSpiderweb()
    
    for name, vec in _lexical_dense_vectors(texts).items():
        web.add_node(name, NodeState(embedding=vec))

    web.build_from_agents(list(web.nodes.keys()))
    nodes = list(web.nodes.values())
    pairs = [(nodes[i], nodes[j]) for i in range(len(nodes)) for j in range(i + 1, len(nodes))]
    
    if not pairs:
        return web, {"web_tension": None, "web_coherence": None, "web_mode": mode, "n_perspectives": len(nodes)}

    web_tension = sum(a.state.tension_with(b.state) for a, b in pairs) / len(pairs)
    signals = {
        "web_tension": round(float(web_tension), 4),
        "web_coherence": round(1.0 / (1.0 + float(web_tension)), 4),
        "web_mode": mode,
        "n_perspectives": len(nodes),
    }
    return web, signals


# ---------------------------------------------------------------------------
# Phase 3 — Spectral Identity Glyphs Tracker Framework
# ---------------------------------------------------------------------------

class SessionGlyphTracker:
    """Per-conversation accumulator tracking perspective consensus alignment via FFT metrics."""

    def __init__(self, embedder: Any = None, glyph_components: int = 8, max_history: int = 50):
        self.embedder = embedder
        self.web = QuantumSpiderweb(glyph_components=glyph_components, max_history=max_history)
        self.turns = 0
        self._perspective_vectors: Dict[str, np.ndarray] = {}

    def _turn_vectors(self, texts: Dict[str, str]) -> Dict[str, np.ndarray]:
        if self.embedder is not None:
            return {n: np.asarray(self.embedder.embed_claim(t), dtype=np.float64) for n, t in texts.items()}
        return _lexical_dense_vectors(texts)

    @staticmethod
    def _cos_tension(a: np.ndarray, b: np.ndarray) -> float:
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na < 1e-8 or nb < 1e-8:
            return 0.5
        cos = max(-1.0, min(1.0, float(np.dot(a, b) / (na * nb))))
        return (1.0 - cos) / 2.0

    def observe_turn(self, perspective_texts: Dict[str, str]) -> Dict[str, Any]:
        """Records one turn sequence loop metrics across active conversational agents."""
        texts = {n: t for n, t in perspective_texts.items() if t and t.strip()}
        if len(texts) < 2:
            return {"turn": self.turns + 1, "turn_tension": {}, "glyphs": {}}
        
        self.turns += 1
        vecs = self._turn_vectors(texts)
        self._perspective_vectors.update(vecs)

        per_persp: Dict[str, float] = {}
        names = list(vecs.keys())
        for n in names:
            others = [self._cos_tension(vecs[n], vecs[m]) for m in names if m != n]
            per_persp[n] = float(sum(others) / len(others)) if others else 0.0

        glyphs: Dict[str, Any] = {}
        for n, xi in per_persp.items():
            if n not in self.web.nodes:
                self.web.add_node(n)
            self.web.nodes[n].tension_history.append(xi)
            g = self.web.form_glyph(n)
            if g is not None:
                glyphs[n] = {"glyph_id": g.glyph_id, "stability": g.stability_score}

        return {
            "turn": self.turns,
            "turn_tension": {k: round(v, 4) for k, v in per_persp.items()},
            "glyphs": glyphs
        }


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
        self._global_tension_history: deque[float] = deque(maxlen=100)

    # -- Graph Construction & Network Layering Subsystems --------------------

    def add_node(self, node_id: str, state: Optional[NodeState] = None) -> SpiderwebNode:
        """Appends an active perspective engine node track directly into processing frames."""
        node = SpiderwebNode(node_id=node_id, state=state or NodeState())
        self.nodes[node_id] = node
        return node

    def connect(self, node_a: str, node_b: str) -> None:
        """Creates symmetrical quantum entangling communication channels across topology space."""
        if node_a in self.nodes and node_b in self.nodes:
            self.nodes[node_a].neighbors.add(node_b)
            self.nodes[node_b].neighbors.add(node_a)

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
        """
        start_time = time.time()
        
        if origin not in self.nodes:
            return PropagationResult({}, {}, [], 0, 0.0)

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
            
            # Attenuate the summary components
            attenuated_arr = incoming_belief.to_array() * attenuation
            current_arr = node.state.to_array()
            
            # Propagating real embedding alignment updates if tracking high-dimensional space
            new_embedding = None
            if incoming_belief.embedding is not None and node.state.embedding is not None:
                new_embedding = node.state.embedding * (1.0 - (0.3 * attenuation)) + (incoming_belief.embedding * attenuation * 0.3)
                # Recalculate tension across structural real semantics
                min_dim = min(node.state.embedding.shape[0], incoming_belief.embedding.shape[0])
                xi = float(np.sum(np.square(node.state.embedding[:min_dim] - (incoming_belief.embedding[:min_dim] * attenuation))))
            else:
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
            new_state.embedding = new_embedding

            node.state = new_state
            node.tension_history.append(xi)

            visited[node_id] = new_state
            tension_map[node_id] = xi

            for neighbor_id in node.neighbors:
                if neighbor_id not in seen:
                    seen.add(neighbor_id)
                    # Pass forward passing alignment profiles
                    next_belief = NodeState.from_array(attenuated_arr)
                    if incoming_belief.embedding is not None:
                        next_belief.embedding = incoming_belief.embedding * attenuation
                    queue.append((neighbor_id, next_belief, hop + 1))

        propagation_time = time.time() - start_time
        return PropagationResult(
            visited=visited,
            tension_map=tension_map,
            anomalies_rejected=anomalies,
            hops=max_hops,
            propagation_time=propagation_time
        )

    # -- Mathematical Integration Systems (Equations 2 & 3 Matrices) --------

    def entangle(self, node_a: str, node_b: str, alpha: float = 0.9) -> float:
        """Enhanced entanglement phase coupling execution across spatial fields (Eq. 2)."""
        if node_a not in self.nodes or node_b not in self.nodes:
            return 0.0

        node_struct_a = self.nodes[node_a]
        node_struct_b = self.nodes[node_b]

        psi_1 = complex(node_struct_a.state.psi, node_struct_a.state.phi)
        psi_2 = complex(node_struct_b.state.psi, node_struct_b.state.phi)
        
        S_complex = alpha * (psi_1 * psi_2.conjugate())
        S_phase = cmath.phase(S_complex)
        blend = min(abs(S_complex) * 0.1, 0.3)

        rotation = np.array([
            [np.cos(S_phase), -np.sin(S_phase)],
            [np.sin(S_phase), np.cos(S_phase)]
        ], dtype=np.float64)

        a_arr = node_struct_a.state.to_array()
        b_arr = node_struct_b.state.to_array()

        a_rotated = rotation @ np.array([node_struct_a.state.psi, node_struct_a.state.phi])
        b_rotated = rotation @ np.array([node_struct_b.state.psi, node_struct_b.state.phi])

        new_a = a_arr.copy()
        new_b = b_arr.copy()
        new_a[:2] = a_arr[:2] * (1.0 - blend) + b_rotated * blend
        new_b[:2] = b_arr[:2] * (1.0 - blend) + a_rotated * blend

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
        """
        if node_id not in self.nodes:
            return 0.0

        coherence = self.phase_coherence()
        I = kappa * (f_base + delta_f * coherence)

        self.nodes[node_id].state.psi += float(I * 0.1)
        return float(I)

    # -- Metrical Phase Estimation Layering ----------------------------------

    def phase_coherence(self) -> float:
        """Computes Global Alignment Metric Wave Index Array Components (Gamma Index Metrics)."""
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
        """Iterates dynamic runtime matrix spaces tracking perspective stabilization clusters."""
        attractors: List[Dict[str, Any]] = []
        assigned: Set[str] = set()
        
        node_items = [
            (nid, n.state.embedding if n.state.embedding is not None else n.state.to_array())
            for nid, n in self.nodes.items()
        ]

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
        """Transforms sequential tension history arrays into dynamic identity spectral signatures."""
        if node_id not in self.nodes:
            return None

        history = list(self.nodes[node_id].tension_history)
        if len(history) < self.glyph_components:
            return None

        arr = np.array(history, dtype=np.float64)
        fft_values = fft(arr)
        fft_magnitudes = np.abs(fft_values)

        components = fft_magnitudes[:self.glyph_components].tolist()
        spectral_energy = float(np.sum(np.square(fft_magnitudes)) / len(arr))

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
        """Implements Equation 5 Real-Time Evaluation Telemetry Gate Index."""
        if len(self._global_tension_history) < window:
            return False, 1.0

        recent_tension = list(self._global_tension_history)[-window:]
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
        
        probabilities = counts / float(counts.sum()) if counts.sum() > 0 else counts
        active_probabilities = probabilities[probabilities > 0]
        
        return float(-np.sum(active_probabilities * np.log2(active_probabilities))) if len(active_probabilities) > 0 else 0.0

    def decoherence_rate(self, window: int = 10) -> float:
        """Calculates trajectory acceleration index matrix shifts via linear regression slope."""
        if len(self._global_tension_history) < window:
            return 0.0

        recent = list(self._global_tension_history)[-window:]
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

        birth_state = NodeState(psi=0.8, tau=0.0, chi=0.7, phi=0.3, lam=0.5)
        self.add_node(node_id, birth_state)

        existing_nodes = [nid for nid in self.nodes.keys() if nid != node_id]
        if existing_nodes:
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
                    "neighbors": list(n.neighbors),
                    "tension_history": list(n.tension_history)[-10:],
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
            "global_tension_history": list(self._global_tension_history)[-20:],
            "parameters": {
                "contraction_ratio": self.contraction_ratio,
                "tension_threshold": self.tension_threshold,
                "anomaly_delta": self.anomaly_delta,
                "glyph_components": self.glyph_components,
                "max_history": self.max_history,
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> QuantumSpiderweb:
        """Hydrates structural graph fields back into active memory frameworks."""
        params = data.get("parameters", {})
        web = cls(
            contraction_ratio=params.get("contraction_ratio", 0.85),
            tension_threshold=params.get("tension_threshold", 0.15),
            anomaly_delta=params.get("anomaly_delta", 2.0),
            glyph_components=params.get("glyph_components", 8),
            max_history=params.get("max_history", 50),
        )
        
        for nid, ndata in data.get("nodes", {}).items():
            node = web.add_node(nid, NodeState.from_array(ndata["state"]))
            node.neighbors = set(ndata.get("neighbors", []))
            node.tension_history = deque(ndata.get("tension_history", []), maxlen=web.max_history)
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
        web._global_tension_history = deque(data.get("global_tension_history", []), maxlen=100)
        return web

    # -- Advanced Analytics & Diagnostics ----------------------------------

    def compute_network_metrics(self) -> Dict[str, Any]:
        """Computes comprehensive network health metrics."""
        if not self.nodes:
            return {"error": "Empty network"}
        
        node_count = len(self.nodes)
        edge_count = sum(len(n.neighbors) for n in self.nodes.values()) // 2
        density = edge_count / (node_count * (node_count - 1) / 2) if node_count > 1 else 0
        
        clustering_sum = 0.0
        for node in self.nodes.values():
            if len(node.neighbors) < 2:
                continue
            neighbor_edges = 0
            for n1 in node.neighbors:
                for n2 in node.neighbors:
                    if n1 in self.nodes and n2 in self.nodes[n1].neighbors:
                        neighbor_edges += 1
            clustering_sum += neighbor_edges / (len(node.neighbors) * (len(node.neighbors) - 1))
        
        avg_clustering = clustering_sum / node_count if node_count > 0 else 0
        
        energies = [n.state.energy() for n in self.nodes.values()]
        energy_stats = {
            "mean": float(np.mean(energies)),
            "std": float(np.std(energies)),
            "min": float(np.min(energies)),
            "max": float(np.max(energies)),
        }
        
        all_tensions = []
        for node in self.nodes.values():
            all_tensions.extend(list(node.tension_history))
        
        tension_stats = {}
        if all_tensions:
            tension_stats = {
                "mean": float(np.mean(all_tensions)),
                "std": float(np.std(all_tensions)),
                "trend": self.decoherence_rate(min(20, len(all_tensions))),
            }
        
        return {
            "topology": {
                "nodes": node_count,
                "edges": edge_count,
                "density": round(density, 4),
                "avg_clustering": round(avg_clustering, 4),
            },
            "energy": {k: round(v, 4) for k, v in energy_stats.items()},
            "tension": {k: round(v, 4) for k, v in tension_stats.items()},
            "coherence": self.phase_coherence(),
            "entropy": round(self.shannon_entropy(), 4),
            "glyphs": len(self.glyphs),
        }

    def optimize_topology(self, target_density: float = 0.3) -> None:
        """Optimizes network topology toward target density by adding/removing edges."""
        if len(self.nodes) < 2:
            return
        
        current_density = sum(len(n.neighbors) for n in self.nodes.values()) / (len(self.nodes) * (len(self.nodes) - 1))
        
        if current_density < target_density:
            node_pairs = [(a, b) for a in self.nodes for b in self.nodes if a != b and b not in self.nodes[a].neighbors]
            if node_pairs:
                tensions = [(a, b, self.nodes[a].state.tension_with(self.nodes[b].state)) for a, b in node_pairs]
                tensions.sort(key=lambda x: x[2])
                for a, b, _ in tensions[:5]:
                    self.connect(a, b)
        elif current_density > target_density:
            edges = [(a, b, self.nodes[a].state.tension_with(self.nodes[b].state)) 
                     for a in self.nodes for b in list(self.nodes[a].neighbors) if a < b]
            if edges:
                edges.sort(key=lambda x: x[2], reverse=True)
                for a, b, _ in edges[:5]:
                    self.nodes[a].neighbors.discard(b)
                    self.nodes[b].neighbors.discard(a)

    def reset_transient_state(self) -> None:
        """Resets transient state while preserving topology and glyphs."""
        for node in self.nodes.values():
            node.tension_history.clear()
            node.state = NodeState()
        self._global_tension_history.clear()