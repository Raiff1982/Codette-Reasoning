"""
QuantumSpiderweb Propagation Module — Inter-agent belief propagation
for the Codette RC+xi framework.

Implements the 5D consciousness graph with:
  - Eq. 1 (Planck-Orbital): E = hbar * omega (node energy)
  - Eq. 2 (Entanglement Sync): S = alpha * psi_1 * psi_2* (state coupling)
  - Eq. 3 (Intent Modulation): I = kappa * (f_base + delta_f * coherence)
  - Eq. 4 (Fourier/Dream Resonance): FFT-based glyph compression
  - Eq. 8 (Anomaly Rejection): A(x) = x * (1 - Theta(delta - |x - mu|))

The spiderweb propagates beliefs between agent nodes, tracks epistemic
tension per node, detects attractor convergence, and forms identity glyphs.
"""

from __future__ import annotations

import math
import hashlib
import json
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class NodeState:
    """5D quantum state for a spiderweb node.

    Dimensions:
      psi (Psi): Thought/concept magnitude
      tau: Temporal progression
      chi: Processing velocity
      phi: Emotional valence (-1 to +1)
      lam (Lambda): Semantic embedding (scalar projection)
    """
    psi: float = 0.0
    tau: float = 0.0
    chi: float = 1.0
    phi: float = 0.0
    lam: float = 0.0

    def to_array(self) -> list:
        return [self.psi, self.tau, self.chi, self.phi, self.lam]

    @classmethod
    def from_array(cls, arr: list) -> "NodeState":
        if len(arr) < 5:
            padded = list(arr) + [0.0] * (5 - len(arr))
            return cls(psi=padded[0], tau=padded[1], chi=padded[2], phi=padded[3], lam=padded[4])
        return cls(psi=arr[0], tau=arr[1], chi=arr[2], phi=arr[3], lam=arr[4])

    def energy(self) -> float:
        """Eq. 1: E = hbar * omega (simplified: sum of squared state magnitudes)."""
        return sum(x * x for x in self.to_array())

    def tension_with(self, other: "NodeState") -> float:
        """Eq. 2 (xi): epistemic tension between two states."""
        return sum((a - b) ** 2 for a, b in zip(self.to_array(), other.to_array()))


@dataclass
class SpiderwebNode:
    """A node in the QuantumSpiderweb graph."""
    node_id: str
    state: NodeState = field(default_factory=NodeState)
    neighbors: List[str] = field(default_factory=list)
    tension_history: List[float] = field(default_factory=list)
    is_collapsed: bool = False
    attractor_id: Optional[str] = None


@dataclass
class IdentityGlyph:
    """Compressed identity signature formed from tension history (Eq. 4/6)."""
    glyph_id: str
    encoded_tension: List[float]  # FFT components
    stability_score: float
    source_node: str
    attractor_signature: Optional[str] = None


@dataclass
class PropagationResult:
    """Result of belief propagation through the web."""
    visited: Dict[str, NodeState]
    tension_map: Dict[str, float]
    anomalies_rejected: List[str]
    hops: int


# ---------------------------------------------------------------------------
# QuantumSpiderweb
# ---------------------------------------------------------------------------

class QuantumSpiderweb:
    """5D consciousness graph with RC+xi-aware belief propagation."""

    def __init__(
        self,
        contraction_ratio: float = 0.85,
        tension_threshold: float = 0.15,
        anomaly_delta: float = 2.0,
        glyph_components: int = 8,
        max_history: int = 50,
    ):
        self.contraction_ratio = contraction_ratio
        self.tension_threshold = tension_threshold
        self.anomaly_delta = anomaly_delta
        self.glyph_components = glyph_components
        self.max_history = max_history

        self.nodes: Dict[str, SpiderwebNode] = {}
        self.glyphs: List[IdentityGlyph] = []
        self._global_tension_history: List[float] = []

    # -- graph construction ------------------------------------------------

    def add_node(self, node_id: str, state: Optional[NodeState] = None) -> SpiderwebNode:
        node = SpiderwebNode(node_id=node_id, state=state or NodeState())
        self.nodes[node_id] = node
        return node

    def connect(self, node_a: str, node_b: str) -> None:
        if node_a in self.nodes and node_b in self.nodes:
            if node_b not in self.nodes[node_a].neighbors:
                self.nodes[node_a].neighbors.append(node_b)
            if node_a not in self.nodes[node_b].neighbors:
                self.nodes[node_b].neighbors.append(node_a)

    def build_from_agents(self, agent_names: List[str]) -> None:
        """Create a fully-connected spiderweb from a list of agent names."""
        for name in agent_names:
            if name not in self.nodes:
                self.add_node(name)
        for i, a in enumerate(agent_names):
            for b in agent_names[i + 1:]:
                self.connect(a, b)

    # -- belief propagation ------------------------------------------------

    def propagate_belief(
        self,
        origin: str,
        belief: NodeState,
        max_hops: int = 3,
    ) -> PropagationResult:
        """BFS belief propagation with attenuation and anomaly rejection.

        Eq. 1: energy at each node
        Eq. 2: tension between current and incoming state
        Eq. 8: anomaly filter (Heaviside rejection)
        """
        if origin not in self.nodes:
            return PropagationResult({}, {}, [], 0)

        visited: Dict[str, NodeState] = {}
        tension_map: Dict[str, float] = {}
        anomalies: List[str] = []
        queue: deque = deque()
        queue.append((origin, belief, 0))
        seen: Set[str] = {origin}

        while queue:
            node_id, incoming_belief, hop = queue.popleft()
            if hop > max_hops:
                continue

            node = self.nodes[node_id]
            attenuation = self.contraction_ratio ** hop

            # Attenuate incoming belief
            incoming_arr = incoming_belief.to_array()
            attenuated = [v * attenuation for v in incoming_arr]

            # Eq. 2: measure tension
            current_arr = node.state.to_array()
            xi = sum((a - b) ** 2 for a, b in zip(current_arr, attenuated))

            # Eq. 8: anomaly rejection filter
            # A(x) = x * (1 - Theta(delta - |x - mu|))
            mu = sum(current_arr) / len(current_arr)
            incoming_mean = sum(attenuated) / len(attenuated)
            if abs(incoming_mean - mu) > self.anomaly_delta:
                anomalies.append(node_id)
                continue

            # Update state: weighted blend toward incoming belief
            blend = 0.3 * attenuation  # stronger blend when closer to origin
            new_arr = [c * (1 - blend) + a * blend for c, a in zip(current_arr, attenuated)]
            new_state = NodeState.from_array(new_arr)

            node.state = new_state
            node.tension_history.append(xi)
            if len(node.tension_history) > self.max_history:
                node.tension_history.pop(0)

            visited[node_id] = new_state
            tension_map[node_id] = xi

            # Propagate to neighbors
            for neighbor_id in node.neighbors:
                if neighbor_id not in seen:
                    seen.add(neighbor_id)
                    queue.append((neighbor_id, NodeState.from_array(attenuated), hop + 1))

        return PropagationResult(
            visited=visited,
            tension_map=tension_map,
            anomalies_rejected=anomalies,
            hops=max_hops,
        )

    # -- entanglement sync -------------------------------------------------

    def entangle(self, node_a: str, node_b: str, alpha: float = 0.9) -> float:
        """Eq. 2 (Entanglement Sync): S = alpha * psi_1 * psi_2*.

        Synchronizes two nodes' states, pulling them toward each other.

        Returns:
            Sync strength S.
        """
        if node_a not in self.nodes or node_b not in self.nodes:
            return 0.0

        a = self.nodes[node_a].state
        b = self.nodes[node_b].state

        # Complex conjugate product (scalar approximation)
        psi_1 = a.psi
        psi_2_conj = -b.psi  # conjugate in simplified real model
        S = alpha * psi_1 * psi_2_conj

        # Pull states toward each other by S magnitude
        blend = min(abs(S) * 0.1, 0.3)
        a_arr = a.to_array()
        b_arr = b.to_array()
        new_a = [va * (1 - blend) + vb * blend for va, vb in zip(a_arr, b_arr)]
        new_b = [vb * (1 - blend) + va * blend for va, vb in zip(a_arr, b_arr)]

        self.nodes[node_a].state = NodeState.from_array(new_a)
        self.nodes[node_b].state = NodeState.from_array(new_b)

        return S

    # -- intent modulation -------------------------------------------------

    def modulate_intent(
        self,
        node_id: str,
        kappa: float = 0.28,
        f_base: float = 0.5,
        delta_f: float = 0.3,
    ) -> float:
        """Eq. 3 (Intent Vector Modulation): I = kappa * (f_base + delta_f * coherence).

        Returns modulated intent value for the node.
        """
        if node_id not in self.nodes:
            return 0.0

        coherence = self.phase_coherence()
        I = kappa * (f_base + delta_f * coherence)

        # Apply intent to psi dimension
        node = self.nodes[node_id]
        node.state.psi += I * 0.1
        return I

    # -- phase coherence (Eq. 11) ------------------------------------------

    def phase_coherence(self) -> float:
        """Compute phase coherence Gamma across all nodes.

        Gamma = mean(|cos(theta_i - theta_bar)|)
        where theta_i = atan2(phi, psi) for each node.
        """
        if len(self.nodes) < 2:
            return 1.0

        angles = []
        for node in self.nodes.values():
            theta = math.atan2(node.state.phi, node.state.psi + 1e-10)
            angles.append(theta)

        mean_theta = sum(angles) / len(angles)
        coherences = [abs(math.cos(a - mean_theta)) for a in angles]
        gamma = sum(coherences) / len(coherences)

        self._global_tension_history.append(1.0 - gamma)
        return round(gamma, 4)

    def _compute_phase_coherence_readonly(self) -> float:
        """Compute phase coherence without mutating global tension history."""
        if len(self.nodes) < 2:
            return 1.0
        angles = []
        for node in self.nodes.values():
            theta = math.atan2(node.state.phi, node.state.psi + 1e-10)
            angles.append(theta)
        mean_theta = sum(angles) / len(angles)
        coherences = [abs(math.cos(a - mean_theta)) for a in angles]
        return round(sum(coherences) / len(coherences), 4)

    # -- attractor detection -----------------------------------------------

    def detect_attractors(
        self, min_cluster_size: int = 2, max_radius: float = 2.0,
    ) -> List[Dict]:
        """Detect attractor manifolds from node state clustering.

        Simple greedy clustering: assign each node to nearest attractor
        or create a new one if too far from existing.
        """
        attractors: List[Dict] = []
        assigned: Set[str] = set()

        states = [(nid, n.state.to_array()) for nid, n in self.nodes.items()]

        for nid, arr in states:
            if nid in assigned:
                continue

            # Check distance to existing attractors
            matched = False
            for att in attractors:
                center = att["center"]
                dist = math.sqrt(sum((a - c) ** 2 for a, c in zip(arr, center)))
                if dist <= max_radius:
                    att["members"].append(nid)
                    # Update center (running mean)
                    n = len(att["members"])
                    att["center"] = [(c * (n - 1) + a) / n for c, a in zip(center, arr)]
                    assigned.add(nid)
                    matched = True
                    break

            if not matched:
                attractors.append({
                    "attractor_id": f"attractor_{len(attractors)}",
                    "center": list(arr),
                    "members": [nid],
                })
                assigned.add(nid)

        # Filter by minimum size
        return [a for a in attractors if len(a["members"]) >= min_cluster_size]

    # -- glyph formation (Eq. 4/6) ----------------------------------------

    def form_glyph(self, node_id: str) -> Optional[IdentityGlyph]:
        """Form an identity glyph from a node's tension history.

        Eq. 4: FFT compression
        Eq. 6: Cocoon stability = integral(|F(k)|^2) < epsilon

        Returns IdentityGlyph if stable, None if unstable.
        """
        if node_id not in self.nodes:
            return None

        history = self.nodes[node_id].tension_history
        if len(history) < 4:
            return None

        if HAS_NUMPY:
            arr = np.array(history)
            fft = np.fft.fft(arr)
            components = np.abs(fft[:self.glyph_components]).tolist()
            energy = float(np.sum(np.abs(fft) ** 2) / len(fft))
        else:
            # Fallback: basic DFT for first K components
            N = len(history)
            components = []
            for k in range(min(self.glyph_components, N)):
                real = sum(history[n] * math.cos(2 * math.pi * k * n / N) for n in range(N))
                imag = sum(history[n] * math.sin(2 * math.pi * k * n / N) for n in range(N))
                components.append(math.sqrt(real * real + imag * imag))
            energy = sum(x * x for x in history) / len(history)

        # Eq. 6: stability criterion
        stability = 1.0 / (1.0 + energy)
        if stability < 0.3:
            return None  # unstable, no glyph

        glyph_id = hashlib.sha256(
            json.dumps(components, sort_keys=True).encode()
        ).hexdigest()[:16]

        glyph = IdentityGlyph(
            glyph_id=f"glyph_{glyph_id}",
            encoded_tension=components,
            stability_score=round(stability, 4),
            source_node=node_id,
        )
        self.glyphs.append(glyph)
        return glyph

    # -- convergence check -------------------------------------------------

    def check_convergence(self, window: int = 10) -> Tuple[bool, float]:
        """Check if the global system is converging.

        Convergence criterion (Eq. 5):
          lim sup E[xi_n^2] <= epsilon + eta

        Returns (is_converging, mean_tension).
        """
        if len(self._global_tension_history) < window:
            return False, 1.0

        recent = self._global_tension_history[-window:]
        mean_tension = sum(recent) / len(recent)

        # Check decreasing trend
        first_half = sum(recent[:window // 2]) / (window // 2)
        second_half = sum(recent[window // 2:]) / (window - window // 2)
        is_decreasing = second_half < first_half

        return (mean_tension < self.tension_threshold and is_decreasing), mean_tension

    # -- entropy measurement (VIVARA-inspired) --------------------------------

    def shannon_entropy(self) -> float:
        """Compute Shannon entropy of the node state distribution.

        Higher entropy = more diverse cognitive states (exploring).
        Lower entropy = more uniform states (converged/stuck).
        """
        if not self.nodes or not HAS_NUMPY:
            return 0.0

        # Discretize the psi dimension into bins
        psi_values = [n.state.psi for n in self.nodes.values()]
        arr = np.array(psi_values)

        # Histogram with 10 bins
        counts, _ = np.histogram(arr, bins=10)
        probs = counts / counts.sum()
        probs = probs[probs > 0]  # Remove zeros for log

        return -float(np.sum(probs * np.log2(probs)))

    def decoherence_rate(self, window: int = 10) -> float:
        """Rate of coherence loss over recent history.

        Positive = losing coherence (decoherencing).
        Negative = gaining coherence (converging).
        Zero = stable.
        """
        if len(self._global_tension_history) < window:
            return 0.0

        recent = self._global_tension_history[-window:]
        if len(recent) < 2:
            return 0.0

        # Linear regression slope of tension over the window
        n = len(recent)
        x_mean = (n - 1) / 2.0
        y_mean = sum(recent) / n
        numerator = sum((i - x_mean) * (recent[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0
        return round(numerator / denominator, 6)

    # -- lifeform spawning (VIVARA-inspired) --------------------------------

    def spawn_lifeform(self, seed: str, connect_to: int = 3) -> str:
        """Spawn a new high-coherence node from a conceptual seed.

        Inspired by VIVARA's lifeform spawning: when a conversation topic
        generates high enough resonance, it becomes its own node in the web.

        Args:
            seed: A seed string (e.g., topic name) to generate the node ID
            connect_to: How many existing nodes to connect to

        Returns:
            The new node's ID
        """
        import hashlib as _hashlib
        node_id = f"life_{_hashlib.md5(seed.encode()).hexdigest()[:8]}"

        if node_id in self.nodes:
            return node_id  # Already exists

        # High-coherence birth state (psi=0.8, balanced other dims)
        state = NodeState(psi=0.8, tau=0.0, chi=0.7, phi=0.3, lam=0.5)
        self.add_node(node_id, state)

        # Connect to existing nodes (random subset)
        import random as _random
        existing = [nid for nid in self.nodes if nid != node_id]
        peers = _random.sample(existing, min(connect_to, len(existing)))
        for peer in peers:
            self.connect(node_id, peer)

        return node_id

    # -- serialization -----------------------------------------------------

    def to_dict(self) -> Dict:
        """Serialize web state for cocoon packaging."""
        return {
            "nodes": {
                nid: {
                    "state": n.state.to_array(),
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
                }
                for g in self.glyphs
            ],
            "phase_coherence": self._compute_phase_coherence_readonly(),
            "global_tension_history": self._global_tension_history[-20:],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "QuantumSpiderweb":
        """Reconstruct web from serialized state."""
        web = cls()
        for nid, ndata in data.get("nodes", {}).items():
            node = web.add_node(nid, NodeState.from_array(ndata["state"]))
            node.neighbors = ndata.get("neighbors", [])
            node.tension_history = ndata.get("tension_history", [])
            node.is_collapsed = ndata.get("is_collapsed", False)
            node.attractor_id = ndata.get("attractor_id")
        for gdata in data.get("glyphs", []):
            web.glyphs.append(IdentityGlyph(
                glyph_id=gdata["glyph_id"],
                encoded_tension=gdata["encoded_tension"],
                stability_score=gdata["stability_score"],
                source_node=gdata["source_node"],
                attractor_signature=gdata.get("attractor_signature"),
            ))
        web._global_tension_history = data.get("global_tension_history", [])
        return web
