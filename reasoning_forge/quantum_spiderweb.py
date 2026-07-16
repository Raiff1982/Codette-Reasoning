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
import cmath
import hashlib
import json
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from scipy.fft import fft, fftfreq
    from scipy.cluster.hierarchy import linkage, fcluster
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


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

    def to_array(self):
        """Converts state to numpy array for vectorized operations (ndarray if numpy available, else list)."""
        if HAS_NUMPY:
            return np.array([self.psi, self.tau, self.chi, self.phi, self.lam], dtype=np.float64)
        return [self.psi, self.tau, self.chi, self.phi, self.lam]

    @classmethod
    def from_array(cls, arr: Union[list, Any]) -> "NodeState":
        if HAS_NUMPY:
            target = np.array(arr, dtype=np.float64).flatten()
            if len(target) < 5:
                target = np.pad(target, (0, 5 - len(target)), 'constant')
            return cls(psi=float(target[0]), tau=float(target[1]), chi=float(target[2]),
                       phi=float(target[3]), lam=float(target[4]))
        if len(arr) < 5:
            padded = list(arr) + [0.0] * (5 - len(arr))
            return cls(psi=padded[0], tau=padded[1], chi=padded[2], phi=padded[3], lam=padded[4])
        return cls(psi=arr[0], tau=arr[1], chi=arr[2], phi=arr[3], lam=arr[4])

    def energy(self) -> float:
        """Eq. 1: E = hbar * omega (simplified: sum of squared state magnitudes)."""
        if HAS_NUMPY:
            return float(np.sum(self.to_array() ** 2))
        return sum(x * x for x in self.to_array())

    def tension_with(self, other: "NodeState") -> float:
        """Eq. 2 (xi): epistemic tension between two states."""
        if HAS_NUMPY:
            return float(np.sum((self.to_array() - other.to_array()) ** 2))
        return sum((a - b) ** 2 for a, b in zip(self.to_array(), other.to_array()))

    def distance_to(self, other: "NodeState") -> float:
        """Euclidean distance between states."""
        if HAS_NUMPY:
            return float(np.linalg.norm(self.to_array() - other.to_array()))
        return math.sqrt(self.tension_with(other))

    def normalize(self) -> "NodeState":
        """Returns normalized (unit-length) state vector."""
        if HAS_NUMPY:
            arr = self.to_array()
            norm = np.linalg.norm(arr)
            if norm > 0:
                arr = arr / norm
            return NodeState.from_array(arr)
        arr = self.to_array()
        norm = math.sqrt(sum(x * x for x in arr))
        if norm > 0:
            arr = [x / norm for x in arr]
        return NodeState.from_array(arr)


@dataclass
class SpiderwebNode:
    """A node in the QuantumSpiderweb graph."""
    node_id: str
    state: NodeState = field(default_factory=NodeState)
    neighbors: Set[str] = field(default_factory=set)
    tension_history: deque = field(default_factory=lambda: deque(maxlen=50))
    is_collapsed: bool = False
    attractor_id: Optional[str] = None
    last_updated: float = 0.0
    activation_level: float = 1.0


@dataclass
class IdentityGlyph:
    """Compressed identity signature formed from tension history (Eq. 4/6)."""
    glyph_id: str
    encoded_tension: List[float]  # FFT components
    stability_score: float
    source_node: str
    attractor_signature: Optional[str] = None
    creation_time: float = field(default_factory=time.time)
    phases: List[float] = field(default_factory=list)
    spectral_energy: float = 0.0
    spectral_entropy: float = 0.0
    dominant_freq: float = 0.0


@dataclass
class PropagationResult:
    """Result of belief propagation through the web."""
    visited: Dict[str, NodeState]
    tension_map: Dict[str, float]
    anomalies_rejected: List[str]
    hops: int
    propagation_time: float = 0.0
    total_energy: float = 0.0


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

        # Performance tracking
        self._propagation_stats: Dict[str, Any] = {
            "total_propagations": 0,
            "avg_propagation_time": 0.0,
            "anomaly_rate": 0.0,
            "convergence_events": 0,
        }

    # -- graph construction ------------------------------------------------

    def add_node(self, node_id: str, state: Optional[NodeState] = None) -> SpiderwebNode:
        """Adds a node. Returns existing node if already present (duplicate guard)."""
        if node_id in self.nodes:
            return self.nodes[node_id]
        node = SpiderwebNode(node_id=node_id, state=state or NodeState())
        self.nodes[node_id] = node
        return node

    def connect(self, node_a: str, node_b: str, bidirectional: bool = True) -> bool:
        """Creates connection with validation. Returns False on missing nodes or self-loops."""
        if node_a not in self.nodes or node_b not in self.nodes:
            return False
        if node_a == node_b:
            return False

        self.nodes[node_a].neighbors.add(node_b)
        if bidirectional:
            self.nodes[node_b].neighbors.add(node_a)
        return True

    def disconnect(self, node_a: str, node_b: str, bidirectional: bool = True) -> bool:
        """Removes connection between two nodes."""
        if node_a not in self.nodes or node_b not in self.nodes:
            return False

        self.nodes[node_a].neighbors.discard(node_b)
        if bidirectional:
            self.nodes[node_b].neighbors.discard(node_a)
        return True

    def build_from_agents(self, agent_names: List[str], fully_connected: bool = True) -> None:
        """Create a spiderweb from a list of agent names.

        Args:
            agent_names: List of agent identifiers.
            fully_connected: If True (default), connect every pair.
        """
        for name in agent_names:
            if name not in self.nodes:
                self.add_node(name)
        if fully_connected:
            for i, a in enumerate(agent_names):
                for b in agent_names[i + 1:]:
                    self.connect(a, b)

    # -- belief propagation ------------------------------------------------

    def propagate_belief(
        self,
        origin: str,
        belief: NodeState,
        max_hops: int = 3,
        attenuation_model: str = "exponential",
    ) -> PropagationResult:
        """BFS belief propagation with attenuation and anomaly rejection.

        Eq. 1: energy at each node
        Eq. 2: tension between current and incoming state
        Eq. 8: anomaly filter (Heaviside rejection)

        Args:
            attenuation_model: "exponential" (default), "linear", or "inverse".
        """
        start_time = time.time()

        if origin not in self.nodes:
            return PropagationResult({}, {}, [], 0, 0.0, 0.0)

        visited: Dict[str, NodeState] = {}
        tension_map: Dict[str, float] = {}
        anomalies: List[str] = []
        queue: deque = deque()
        queue.append((origin, belief, 0))
        seen: Set[str] = {origin}
        total_energy = 0.0

        while queue:
            node_id, incoming_belief, hop = queue.popleft()
            if hop > max_hops:
                continue

            node = self.nodes[node_id]

            # Different attenuation models
            if attenuation_model == "linear":
                attenuation = max(0.0, 1.0 - (hop * (1.0 - self.contraction_ratio)))
            elif attenuation_model == "inverse":
                attenuation = 1.0 / (1.0 + hop)
            else:  # exponential (default)
                attenuation = self.contraction_ratio ** hop

            # Attenuate incoming belief
            incoming_arr = incoming_belief.to_array()
            current_arr = node.state.to_array()

            if HAS_NUMPY:
                attenuated = incoming_arr * attenuation
                xi = float(np.sum((current_arr - attenuated) ** 2))
                mu = float(np.mean(current_arr))
                incoming_mean = float(np.mean(attenuated))
            else:
                attenuated = [v * attenuation for v in incoming_arr]
                xi = sum((a - b) ** 2 for a, b in zip(current_arr, attenuated))
                mu = sum(current_arr) / len(current_arr)
                incoming_mean = sum(attenuated) / len(attenuated)

            # Eq. 8: anomaly rejection filter
            # A(x) = x * (1 - Theta(delta - |x - mu|))
            if abs(incoming_mean - mu) > self.anomaly_delta:
                anomalies.append(node_id)
                continue

            # Update state: weighted blend toward incoming belief
            blend = 0.3 * attenuation  # stronger blend when closer to origin
            if HAS_NUMPY:
                new_arr = current_arr * (1.0 - blend) + np.array(attenuated) * blend
            else:
                new_arr = [c * (1 - blend) + a * blend for c, a in zip(current_arr, attenuated)]
            new_state = NodeState.from_array(new_arr)

            node.state = new_state
            node.last_updated = time.time()
            node.tension_history.append(xi)
            total_energy += new_state.energy()

            visited[node_id] = new_state
            tension_map[node_id] = xi

            # Propagate to neighbors
            for neighbor_id in node.neighbors:
                if neighbor_id not in seen:
                    seen.add(neighbor_id)
                    queue.append((neighbor_id, NodeState.from_array(attenuated), hop + 1))

        propagation_time = time.time() - start_time
        self._propagation_stats["total_propagations"] += 1
        total_props = self._propagation_stats["total_propagations"]
        self._propagation_stats["avg_propagation_time"] = (
            (self._propagation_stats["avg_propagation_time"] * (total_props - 1) + propagation_time) / total_props
        )

        return PropagationResult(
            visited=visited,
            tension_map=tension_map,
            anomalies_rejected=anomalies,
            hops=max_hops,
            propagation_time=propagation_time,
            total_energy=total_energy,
        )

    # -- entanglement sync -------------------------------------------------

    def entangle(self, node_a: str, node_b: str, alpha: float = 0.9) -> float:
        """Eq. 2 (Entanglement Sync): S = alpha * psi_1 * psi_2*.

        Synchronizes two nodes' states using complex phase with rotation matrix.

        Returns:
            Sync strength S (magnitude).
        """
        if node_a not in self.nodes or node_b not in self.nodes:
            return 0.0

        a = self.nodes[node_a].state
        b = self.nodes[node_b].state

        # Complex representation with phase
        psi_1 = complex(a.psi, a.phi)
        psi_2 = complex(b.psi, b.phi)
        psi_2_conj = psi_2.conjugate()

        # Entanglement strength (Eq. 2)
        S_complex = alpha * (psi_1 * psi_2_conj)
        S_magnitude = abs(S_complex)
        S_phase = cmath.phase(S_complex)

        # Pull states toward each other by S magnitude
        blend = min(S_magnitude * 0.1, 0.3)

        if HAS_NUMPY:
            # Phase-aware rotation in psi-phi subspace
            rotation = np.array([
                [np.cos(S_phase), -np.sin(S_phase)],
                [np.sin(S_phase), np.cos(S_phase)]
            ])

            a_arr = a.to_array()
            b_arr = b.to_array()

            a_sub = np.array([a.psi, a.phi])
            b_sub = np.array([b.psi, b.phi])

            a_rotated = rotation @ a_sub
            b_rotated = rotation @ b_sub

            new_a = a_arr.copy()
            new_b = b_arr.copy()
            new_a[:2] = a_arr[:2] * (1 - blend) + b_rotated * blend
            new_b[:2] = b_arr[:2] * (1 - blend) + a_rotated * blend
        else:
            a_arr = a.to_array()
            b_arr = b.to_array()
            new_a = [va * (1 - blend) + vb * blend for va, vb in zip(a_arr, b_arr)]
            new_b = [vb * (1 - blend) + va * blend for va, vb in zip(a_arr, b_arr)]

        self.nodes[node_a].state = NodeState.from_array(new_a)
        self.nodes[node_b].state = NodeState.from_array(new_b)

        return float(S_magnitude)

    # -- intent modulation -------------------------------------------------

    def modulate_intent(
        self,
        node_id: str,
        kappa: float = 0.28,
        f_base: float = 0.5,
        delta_f: float = 0.3,
    ) -> float:
        """Eq. 3 (Intent Vector Modulation): I = kappa * (f_base + delta_f * coherence).

        Uses adaptive kappa based on coherence. Modulates psi, chi, and phi.

        Returns modulated intent value for the node.
        """
        if node_id not in self.nodes:
            return 0.0

        coherence = self.phase_coherence()

        # Adaptive kappa based on coherence
        adaptive_kappa = kappa * (1.0 + coherence)

        I = adaptive_kappa * (f_base + delta_f * coherence)

        # Apply intent modulation to multiple dimensions
        node = self.nodes[node_id]
        node.state.psi += I * 0.1
        node.state.chi += I * 0.05  # Modulate processing velocity
        node.state.phi += math.tanh(I) * 0.02  # Small valence adjustment
        return float(I)

    # -- phase coherence (Eq. 11) ------------------------------------------

    def phase_coherence(self) -> float:
        """Compute phase coherence Gamma across all nodes.

        Gamma = mean(|cos(theta_i - theta_bar)|)
        where theta_i = atan2(phi, psi) for each node.

        Uses circular statistics with numpy when available.
        """
        if len(self.nodes) < 2:
            return 1.0

        if HAS_NUMPY:
            angles = np.array([
                math.atan2(node.state.phi, node.state.psi + 1e-10)
                for node in self.nodes.values()
            ])
            sin_sum = np.sum(np.sin(angles))
            cos_sum = np.sum(np.cos(angles))
            gamma = float(np.sqrt(sin_sum**2 + cos_sum**2) / len(angles))
        else:
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
        if HAS_NUMPY:
            angles = np.array([
                math.atan2(node.state.phi, node.state.psi + 1e-10)
                for node in self.nodes.values()
            ])
            sin_sum = np.sum(np.sin(angles))
            cos_sum = np.sum(np.cos(angles))
            return float(round(np.sqrt(sin_sum**2 + cos_sum**2) / len(angles), 4))
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
                if HAS_NUMPY:
                    dist = float(np.linalg.norm(np.array(arr) - np.array(center)))
                else:
                    dist = math.sqrt(sum((a - c) ** 2 for a, c in zip(arr, center)))
                if dist <= max_radius:
                    att["members"].append(nid)
                    # Update center (running mean)
                    n = len(att["members"])
                    if HAS_NUMPY:
                        att["center"] = ((np.array(center) * (n - 1) + np.array(arr)) / n).tolist()
                    else:
                        att["center"] = [(c * (n - 1) + a) / n for c, a in zip(center, arr)]
                    assigned.add(nid)
                    matched = True
                    break

            if not matched:
                attractors.append({
                    "attractor_id": f"attractor_{len(attractors)}",
                    "center": list(arr) if not HAS_NUMPY else (arr.tolist() if hasattr(arr, 'tolist') else list(arr)),
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

        history = list(self.nodes[node_id].tension_history)
        if len(history) < 4:
            return None

        phases: List[float] = []
        spectral_entropy = 0.0
        dominant_freq = 0.0

        if HAS_NUMPY:
            arr = np.array(history)
            if HAS_SCIPY:
                fft_values = fft(arr)
            else:
                fft_values = np.fft.fft(arr)
            fft_magnitudes = np.abs(fft_values)
            fft_phases = np.angle(fft_values)

            components = fft_magnitudes[:self.glyph_components].tolist()
            phases = fft_phases[:self.glyph_components].tolist()

            energy = float(np.sum(fft_magnitudes ** 2) / len(fft_magnitudes))

            # Spectral entropy
            power_spectrum = fft_magnitudes ** 2
            ps_sum = np.sum(power_spectrum)
            if ps_sum > 0:
                power_spectrum = power_spectrum / ps_sum
                spectral_entropy = float(-np.sum(power_spectrum * np.log2(power_spectrum + 1e-10)))

            # Dominant frequency
            if HAS_SCIPY:
                freqs = fftfreq(len(arr))
            else:
                freqs = np.fft.fftfreq(len(arr))
            half = len(fft_magnitudes) // 2
            if half > 1:
                dominant_freq = float(freqs[np.argmax(fft_magnitudes[1:half]) + 1])
        else:
            # Fallback: basic DFT for first K components
            N = len(history)
            components = []
            for k in range(min(self.glyph_components, N)):
                real = sum(history[n] * math.cos(2 * math.pi * k * n / N) for n in range(N))
                imag = sum(history[n] * math.sin(2 * math.pi * k * n / N) for n in range(N))
                components.append(math.sqrt(real * real + imag * imag))
                phases.append(math.atan2(imag, real))
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
            phases=phases,
            spectral_energy=energy,
            spectral_entropy=spectral_entropy,
            dominant_freq=dominant_freq,
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

        converged = mean_tension < self.tension_threshold and is_decreasing
        if converged:
            self._propagation_stats["convergence_events"] += 1

        return converged, mean_tension

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

    # -- graph analysis helpers --------------------------------------------

    def _compute_centrality(self) -> Dict[str, Dict[str, float]]:
        """Computes degree, betweenness, and closeness centrality for all nodes."""
        centrality: Dict[str, Dict[str, float]] = {}
        node_ids = list(self.nodes.keys())
        max_degree = len(self.nodes) - 1

        # Degree centrality
        for nid, node in self.nodes.items():
            centrality[nid] = {
                "degree": len(node.neighbors) / max_degree if max_degree > 0 else 0,
            }

        # Betweenness centrality (simplified)
        for nid in node_ids:
            paths = 0
            total_paths = 0
            for source in node_ids:
                if source == nid:
                    continue
                for target in node_ids:
                    if target == nid or target == source:
                        continue
                    if self._shortest_path(source, target, nid):
                        paths += 1
                    total_paths += 1
            centrality[nid]["betweenness"] = paths / total_paths if total_paths > 0 else 0

        # Closeness centrality
        for nid in node_ids:
            distances = []
            for other in node_ids:
                if other != nid:
                    dist = self._shortest_distance(nid, other)
                    if dist is not None:
                        distances.append(dist)
            if distances and sum(distances) > 0:
                centrality[nid]["closeness"] = len(distances) / sum(distances)
            else:
                centrality[nid]["closeness"] = 0

        return centrality

    def _shortest_path(self, source: str, target: str, through: Optional[str] = None) -> bool:
        """Checks if shortest path from source to target goes through 'through'."""
        if source not in self.nodes or target not in self.nodes:
            return False

        queue_bfs: deque = deque([(source, [source])])
        visited: Set[str] = {source}

        while queue_bfs:
            current, path = queue_bfs.popleft()
            if current == target:
                return through in path if through else True
            for neighbor in self.nodes[current].neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue_bfs.append((neighbor, path + [neighbor]))

        return False

    def _shortest_distance(self, source: str, target: str) -> Optional[int]:
        """BFS shortest path distance between source and target."""
        if source not in self.nodes or target not in self.nodes:
            return None
        if source == target:
            return 0

        queue_bfs: deque = deque([(source, 0)])
        visited: Set[str] = {source}

        while queue_bfs:
            current, dist = queue_bfs.popleft()
            if current == target:
                return dist
            for neighbor in self.nodes[current].neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue_bfs.append((neighbor, dist + 1))
        return None

    def _avg_path_length(self) -> float:
        """Average shortest path length of the network."""
        node_ids = list(self.nodes.keys())
        if len(node_ids) < 2:
            return 0.0

        total_dist = 0
        pairs = 0

        for source in node_ids:
            queue_bfs: deque = deque([(source, 0)])
            visited: Set[str] = {source}
            while queue_bfs:
                current, dist = queue_bfs.popleft()
                if current != source:
                    total_dist += dist
                    pairs += 1
                for neighbor in self.nodes[current].neighbors:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue_bfs.append((neighbor, dist + 1))

        return round(total_dist / pairs, 4) if pairs > 0 else 0.0

    # -- web analysis (comprehensive topology report) ----------------------

    def web_analysis(self) -> Dict[str, Any]:
        """Comprehensive topology/energy/tension/centrality report."""
        if not self.nodes:
            return {"error": "Empty network"}

        node_count = len(self.nodes)
        edge_count = sum(len(node.neighbors) for node in self.nodes.values()) // 2
        max_edges = node_count * (node_count - 1) / 2
        density = edge_count / max_edges if max_edges > 0 else 0

        # Energy distribution
        energies = [node.state.energy() for node in self.nodes.values()]
        energy_stats = {
            "mean": sum(energies) / len(energies),
            "min": min(energies),
            "max": max(energies),
        }

        # Tension statistics
        all_tensions: List[float] = []
        for node in self.nodes.values():
            all_tensions.extend(list(node.tension_history))

        tension_stats: Dict[str, Any] = {}
        if all_tensions:
            tension_stats = {
                "mean": sum(all_tensions) / len(all_tensions),
                "trend": self.decoherence_rate(min(20, len(all_tensions))),
            }

        centrality = self._compute_centrality()

        return {
            "topology": {
                "nodes": node_count,
                "edges": edge_count,
                "density": round(density, 4),
                "avg_path_length": self._avg_path_length(),
            },
            "centrality": centrality,
            "energy": {k: round(v, 4) for k, v in energy_stats.items()},
            "tension": {k: round(v, 4) if isinstance(v, float) else v for k, v in tension_stats.items()},
            "coherence": self._compute_phase_coherence_readonly(),
            "entropy": round(self.shannon_entropy(), 4),
            "glyphs": len(self.glyphs),
            "attractors": len(self.detect_attractors()),
            "propagation_stats": dict(self._propagation_stats),
        }

    # -- serialization -----------------------------------------------------

    def to_dict(self) -> Dict:
        """Serialize web state for cocoon packaging."""
        return {
            "nodes": {
                nid: {
                    "state": n.state.to_array() if not HAS_NUMPY else n.state.to_array().tolist(),
                    "neighbors": list(n.neighbors),
                    "tension_history": list(n.tension_history)[-10:],
                    "is_collapsed": n.is_collapsed,
                    "attractor_id": n.attractor_id,
                    "last_updated": n.last_updated,
                    "activation_level": n.activation_level,
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
                    "creation_time": g.creation_time,
                    "phases": g.phases,
                    "spectral_energy": g.spectral_energy,
                    "spectral_entropy": g.spectral_entropy,
                    "dominant_freq": g.dominant_freq,
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
            node.neighbors = set(ndata.get("neighbors", []))
            for t in ndata.get("tension_history", []):
                node.tension_history.append(t)
            node.is_collapsed = ndata.get("is_collapsed", False)
            node.attractor_id = ndata.get("attractor_id")
            node.last_updated = ndata.get("last_updated", 0.0)
            node.activation_level = ndata.get("activation_level", 1.0)
        for gdata in data.get("glyphs", []):
            web.glyphs.append(IdentityGlyph(
                glyph_id=gdata["glyph_id"],
                encoded_tension=gdata["encoded_tension"],
                stability_score=gdata["stability_score"],
                source_node=gdata["source_node"],
                attractor_signature=gdata.get("attractor_signature"),
                creation_time=gdata.get("creation_time", 0.0),
                phases=gdata.get("phases", []),
                spectral_energy=gdata.get("spectral_energy", 0.0),
                spectral_entropy=gdata.get("spectral_entropy", 0.0),
                dominant_freq=gdata.get("dominant_freq", 0.0),
            ))
        web._global_tension_history = data.get("global_tension_history", [])
        return web
