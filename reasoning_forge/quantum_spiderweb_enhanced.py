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
from typing import Dict, List, Optional, Set, Tuple, Any, Union

try:
    import numpy as np
    from scipy.fft import fft, fftfreq
    from scipy.cluster.hierarchy import linkage, fcluster
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

    def to_array(self) -> np.ndarray:
        """Converts state to numpy array for vectorized operations."""
        return np.array([self.psi, self.tau, self.chi, self.phi, self.lam], dtype=np.float64)

    @classmethod
    def from_array(cls, arr: Union[List[float], np.ndarray]) -> "NodeState":
        """Creates NodeState from array with proper padding."""
        target = np.array(arr, dtype=np.float64).flatten()
        if len(target) < 5:
            target = np.pad(target, (0, 5 - len(target)), 'constant')
        return cls(psi=float(target[0]), tau=float(target[1]), chi=float(target[2]),
                   phi=float(target[3]), lam=float(target[4]))

    def energy(self) -> float:
        """Eq. 1: E = hbar * omega (simplified: sum of squared state magnitudes)."""
        return float(np.sum(self.to_array() ** 2))

    def tension_with(self, other: "NodeState") -> float:
        """Eq. 2 (xi): epistemic tension between two states."""
        return float(np.sum((self.to_array() - other.to_array()) ** 2))

    def distance_to(self, other: "NodeState") -> float:
        """Euclidean distance between states."""
        return float(np.linalg.norm(self.to_array() - other.to_array()))

    def normalize(self) -> "NodeState":
        """Returns normalized state vector."""
        arr = self.to_array()
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return NodeState.from_array(arr)


@dataclass
class SpiderwebNode:
    """A node in the QuantumSpiderweb graph."""
    node_id: str
    state: NodeState = field(default_factory=NodeState)
    neighbors: Set[str] = field(default_factory=set)
    tension_history: deque[float] = field(default_factory=lambda: deque(maxlen=50))
    is_collapsed: bool = False
    attractor_id: Optional[str] = None
    last_updated: float = field(default_factory=time.time)
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
        self._global_tension_history: deque[float] = deque(maxlen=100)
        
        # Performance tracking
        self._propagation_stats: Dict[str, Any] = {
            "total_propagations": 0,
            "avg_propagation_time": 0.0,
            "anomaly_rate": 0.0,
            "convergence_events": 0,
        }

    # -- graph construction ------------------------------------------------

    def add_node(self, node_id: str, state: Optional[NodeState] = None) -> SpiderwebNode:
        """Adds a node with proper initialization and tracking."""
        if node_id in self.nodes:
            return self.nodes[node_id]
        node = SpiderwebNode(node_id=node_id, state=state or NodeState())
        self.nodes[node_id] = node
        return node

    def connect(self, node_a: str, node_b: str, bidirectional: bool = True) -> bool:
        """Creates connection with validation."""
        if node_a not in self.nodes or node_b not in self.nodes:
            return False
        if node_a == node_b:
            return False
        
        self.nodes[node_a].neighbors.add(node_b)
        if bidirectional:
            self.nodes[node_b].neighbors.add(node_a)
        return True

    def disconnect(self, node_a: str, node_b: str, bidirectional: bool = True) -> bool:
        """Removes connection with validation."""
        if node_a not in self.nodes or node_b not in self.nodes:
            return False
        
        self.nodes[node_a].neighbors.discard(node_b)
        if bidirectional:
            self.nodes[node_b].neighbors.discard(node_a)
        return True

    def build_from_agents(self, agent_names: List[str], fully_connected: bool = True) -> None:
        """Builds web topology from agent list."""
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
        """Enhanced belief propagation with multiple attenuation models."""
        start_time = time.time()
        
        if origin not in self.nodes:
            return PropagationResult({}, {}, [], 0, 0.0, 0.0)

        visited: Dict[str, NodeState] = {}
        tension_map: Dict[str, float] = {}
        anomalies: List[str] = []
        queue = deque([(origin, belief, 0)])
        seen: Set[str] = {origin}
        total_energy = 0.0

        while queue:
            node_id, incoming_belief, hop = queue.popleft()
            if hop > max_hops:
                continue

            node = self.nodes[node_id]
            
            # Different attenuation models
            if attenuation_model == "exponential":
                attenuation = self.contraction_ratio ** hop
            elif attenuation_model == "linear":
                attenuation = 1.0 - (hop * (1.0 - self.contraction_ratio))
            elif attenuation_model == "inverse":
                attenuation = 1.0 / (1.0 + hop)
            else:
                attenuation = self.contraction_ratio ** hop

            # Vectorized state operations
            incoming_arr = incoming_belief.to_array()
            current_arr = node.state.to_array()
            
            # Attenuate incoming belief
            attenuated_arr = incoming_arr * attenuation

            # Calculate tension (Eq. 2)
            xi = float(np.sum((current_arr - attenuated_arr) ** 2))
            
            # Anomaly detection (Eq. 8)
            mu = float(np.mean(current_arr))
            incoming_mean = float(np.mean(attenuated_arr))
            if abs(incoming_mean - mu) > self.anomaly_delta:
                anomalies.append(node_id)
                self._propagation_stats["anomaly_rate"] += 0.01
                continue

            # Update state with weighted blend
            blend = 0.3 * attenuation
            new_arr = current_arr * (1.0 - blend) + attenuated_arr * blend
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
                    queue.append((neighbor_id, NodeState.from_array(attenuated_arr), hop + 1))

        propagation_time = time.time() - start_time
        self._propagation_stats["total_propagations"] += 1
        self._propagation_stats["avg_propagation_time"] = (
            (self._propagation_stats["avg_propagation_time"] * (self._propagation_stats["total_propagations"] - 1) + propagation_time) /
            self._propagation_stats["total_propagations"]
        )

        return PropagationResult(
            visited=visited,
            tension_map=tension_map,
            anomalies_rejected=anomalies,
            hops=max_hops,
            propagation_time=propagation_time,
            total_energy=total_energy
        )

    # -- entanglement sync -------------------------------------------------

    def entangle(self, node_a: str, node_b: str, alpha: float = 0.9) -> float:
        """Enhanced entanglement with complex phase synchronization."""
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

        # Phase-aware state synchronization
        blend = min(S_magnitude * 0.1, 0.3)
        
        # Apply rotation based on phase difference
        rotation = np.array([
            [np.cos(S_phase), -np.sin(S_phase)],
            [np.sin(S_phase), np.cos(S_phase)]
        ])
        
        a_arr = a.to_array()
        b_arr = b.to_array()
        
        # Apply rotation to psi-phi subspace
        a_sub = np.array([a.psi, a.phi])
        b_sub = np.array([b.psi, b.phi])
        
        a_rotated = rotation @ a_sub
        b_rotated = rotation @ b_sub
        
        # Blend states
        new_a = a_arr.copy()
        new_b = b_arr.copy()
        new_a[:2] = a_arr[:2] * (1 - blend) + b_rotated * blend
        new_b[:2] = b_arr[:2] * (1 - blend) + a_rotated * blend

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
        """Enhanced intent modulation with adaptive kappa."""
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
        node.state.phi += np.tanh(I) * 0.02  # Small valence adjustment
        
        return float(I)

    # -- phase coherence (Eq. 11) ------------------------------------------

    def phase_coherence(self) -> float:
        """Enhanced phase coherence calculation with circular statistics."""
        if len(self.nodes) < 2:
            return 1.0

        # Calculate angles for all nodes
        angles = np.array([
            math.atan2(node.state.phi, node.state.psi + 1e-10)
            for node in self.nodes.values()
        ])

        # Circular mean
        sin_sum = np.sum(np.sin(angles))
        cos_sum = np.sum(np.cos(angles))
        
        # Circular variance
        R = np.sqrt(sin_sum**2 + cos_sum**2) / len(angles)
        gamma = R  # Resultant length as coherence measure

        self._global_tension_history.append(1.0 - gamma)
        return float(round(gamma, 4))

    def _compute_phase_coherence_readonly(self) -> float:
        """Computes phase coherence without mutating history."""
        if len(self.nodes) < 2:
            return 1.0
        
        angles = np.array([
            math.atan2(node.state.phi, node.state.psi + 1e-10)
            for node in self.nodes.values()
        ])
        
        sin_sum = np.sum(np.sin(angles))
        cos_sum = np.sum(np.cos(angles))
        R = np.sqrt(sin_sum**2 + cos_sum**2) / len(angles)
        return float(round(R, 4))

    # -- attractor detection -----------------------------------------------

    def detect_attractors(
        self, 
        min_cluster_size: int = 2, 
        max_radius: float = 2.0,
        clustering_method: str = "greedy"
    ) -> List[Dict]:
        """Enhanced attractor detection with multiple clustering methods."""
        if len(self.nodes) < min_cluster_size:
            return []

        # Get state vectors
        node_items = [
            (nid, n.state.embedding if hasattr(n.state, 'embedding') and n.state.embedding is not None else n.state.to_array())
            for nid, n in self.nodes.items()
        ]
        
        if not node_items:
            return []

        states = np.array([arr for _, arr in node_items])
        node_ids = [nid for nid, _ in node_items]

        if clustering_method == "greedy":
            return self._greedy_clustering(node_ids, states, min_cluster_size, max_radius)
        elif clustering_method == "hierarchical":
            return self._hierarchical_clustering(node_ids, states, min_cluster_size, max_radius)
        elif clustering_method == "dbscan" and HAS_NUMPY:
            return self._dbscan_clustering(node_ids, states, min_cluster_size, max_radius)
        else:
            return self._greedy_clustering(node_ids, states, min_cluster_size, max_radius)

    def _greedy_clustering(self, node_ids: List[str], states: np.ndarray, 
                           min_cluster_size: int, max_radius: float) -> List[Dict]:
        """Greedy clustering implementation."""
        attractors: List[Dict] = []
        assigned: Set[int] = set()

        for idx, (nid, arr) in enumerate(zip(node_ids, states)):
            if idx in assigned:
                continue

            matched = False
            for att in attractors:
                center = np.array(att["center"])
                dist = float(np.linalg.norm(arr - center))
                if dist <= max_radius:
                    att["members"].append(nid)
                    att["indices"].append(idx)
                    # Update center
                    n = len(att["members"])
                    att["center"] = (center * (n - 1) + arr) / n
                    assigned.add(idx)
                    matched = True
                    break

            if not matched:
                attractors.append({
                    "attractor_id": f"attractor_{len(attractors)}",
                    "center": arr.tolist(),
                    "members": [nid],
                    "indices": [idx],
                    "radius": 0.0,
                })
                assigned.add(idx)

        # Calculate radii and filter
        for att in attractors:
            member_states = states[att["indices"]]
            center = np.array(att["center"])
            distances = np.linalg.norm(member_states - center, axis=1)
            att["radius"] = float(np.max(distances))
            att["coherence"] = float(1.0 / (1.0 + np.std(distances)))

        return [a for a in attractors if len(a["members"]) >= min_cluster_size]

    def _hierarchical_clustering(self, node_ids: List[str], states: np.ndarray,
                                 min_cluster_size: int, max_radius: float) -> List[Dict]:
        """Hierarchical clustering implementation."""
        if len(states) < 2:
            return []
        
        # Compute linkage matrix
        Z = linkage(states, method='ward')
        
        # Form clusters
        clusters = fcluster(Z, t=max_radius, criterion='distance')
        
        # Group nodes by cluster
        cluster_groups = {}
        for idx, cluster_id in enumerate(clusters):
            if cluster_id not in cluster_groups:
                cluster_groups[cluster_id] = []
            cluster_groups[cluster_id].append(idx)
        
        # Convert to attractor format
        attractors = []
        for cluster_id, indices in cluster_groups.items():
            if len(indices) >= min_cluster_size:
                member_states = states[indices]
                center = np.mean(member_states, axis=0)
                distances = np.linalg.norm(member_states - center, axis=1)
                
                attractors.append({
                    "attractor_id": f"attractor_{cluster_id}",
                    "center": center.tolist(),
                    "members": [node_ids[i] for i in indices],
                    "indices": indices,
                    "radius": float(np.max(distances)),
                    "coherence": float(1.0 / (1.0 + np.std(distances))),
                })
        
        return attractors

    def _dbscan_clustering(self, node_ids: List[str], states: np.ndarray,
                           min_cluster_size: int, max_radius: float) -> List[Dict]:
        """DBSCAN clustering implementation."""
        from sklearn.cluster import DBSCAN
        
        clustering = DBSCAN(eps=max_radius, min_samples=min_cluster_size)
        cluster_labels = clustering.fit_predict(states)
        
        attractors = []
        for cluster_id in set(cluster_labels):
            if cluster_id == -1:  # Noise points
                continue
            
            indices = [i for i, label in enumerate(cluster_labels) if label == cluster_id]
            if len(indices) >= min_cluster_size:
                member_states = states[indices]
                center = np.mean(member_states, axis=0)
                distances = np.linalg.norm(member_states - center, axis=1)
                
                attractors.append({
                    "attractor_id": f"attractor_{cluster_id}",
                    "center": center.tolist(),
                    "members": [node_ids[i] for i in indices],
                    "indices": indices,
                    "radius": float(np.max(distances)),
                    "coherence": float(1.0 / (1.0 + np.std(distances))),
                })
        
        return attractors

    # -- glyph formation (Eq. 4/6) ----------------------------------------

    def form_glyph(self, node_id: str) -> Optional[IdentityGlyph]:
        """Enhanced glyph formation with spectral analysis."""
        if node_id not in self.nodes:
            return None

        history = list(self.nodes[node_id].tension_history)
        if len(history) < self.glyph_components:
            return None

        arr = np.array(history, dtype=np.float64)
        
        if HAS_NUMPY:
            # Full FFT analysis
            fft_values = fft(arr)
            fft_magnitudes = np.abs(fft_values)
            fft_phases = np.angle(fft_values)
            
            # Extract components
            components = fft_magnitudes[:self.glyph_components].tolist()
            phases = fft_phases[:self.glyph_components].tolist()
            
            # Spectral energy and entropy
            spectral_energy = float(np.sum(fft_magnitudes ** 2) / len(fft_magnitudes))
            power_spectrum = fft_magnitudes ** 2
            power_spectrum = power_spectrum / np.sum(power_spectrum)
            spectral_entropy = float(-np.sum(power_spectrum * np.log2(power_spectrum + 1e-10)))
            
            # Dominant frequency
            freqs = fftfreq(len(arr))
            dominant_freq = float(freqs[np.argmax(fft_magnitudes[1:len(fft_magnitudes)//2]) + 1])
        else:
            # Fallback DFT
            N = len(history)
            components = []
            phases = []
            for k in range(min(self.glyph_components, N)):
                real = sum(history[n] * math.cos(2 * math.pi * k * n / N) for n in range(N))
                imag = sum(history[n] * math.sin(2 * math.pi * k * n / N) for n in range(N))
                components.append(math.sqrt(real * real + imag * imag))
                phases.append(math.atan2(imag, real))
            spectral_energy = sum(x * x for x in history) / len(history)
            spectral_entropy = 0.0
            dominant_freq = 0.0

        # Enhanced stability criterion (Eq. 6)
        stability = 1.0 / (1.0 + spectral_energy + spectral_entropy)
        if stability < 0.3:
            return None

        glyph = IdentityGlyph(
            glyph_id=f"glyph_{hashlib.sha256(json.dumps(components).encode('utf-8')).hexdigest()[:16]}",
            encoded_tension=components,
            stability_score=float(round(stability, 4)),
            source_node=node_id,
            attractor_signature=self.nodes[node_id].attractor_id,
            phases=phases,
            spectral_energy=spectral_energy,
            spectral_entropy=spectral_entropy,
            dominant_freq=dominant_freq
        )
        
        self.glyphs.append(glyph)
        return glyph

    # -- convergence check -------------------------------------------------

    def check_convergence(self, window: int = 10) -> Tuple[bool, float]:
        """Enhanced convergence check with trend analysis."""
        if len(self._global_tension_history) < window:
            return False, 1.0

        recent = list(self._global_tension_history)[-window:]
        mean_tension = float(np.mean(recent))

        # Linear trend analysis
        x = np.arange(len(recent))
        y = np.array(recent)
        
        # Calculate slope
        if len(recent) > 1:
            slope = float(np.polyfit(x, y, 1)[0])
            is_decreasing = slope < -0.01  # Threshold for meaningful decrease
        else:
            is_decreasing = False

        # Variance check
        variance = float(np.var(recent))
        is_stable = variance < 0.01

        converged = (
            mean_tension < self.tension_threshold and 
            (is_decreasing or is_stable)
        )
        
        if converged:
            self._propagation_stats["convergence_events"] += 1
            
        return converged, mean_tension

    # -- entropy measurement (VIVARA-inspired) --------------------------------

    def shannon_entropy(self) -> float:
        """Enhanced entropy calculation across multiple dimensions."""
        if not self.nodes or not HAS_NUMPY:
            return 0.0

        # Collect all state dimensions
        all_states = np.array([node.state.to_array() for node in self.nodes.values()])
        
        # Calculate entropy for each dimension
        entropies = []
        for dim in range(all_states.shape[1]):
            values = all_states[:, dim]
            # Discretize into bins
            counts, _ = np.histogram(values, bins=10, density=True)
            probs = counts[counts > 0]
            if len(probs) > 0:
                entropies.append(-np.sum(probs * np.log2(probs + 1e-10)))
        
        return float(np.mean(entropies)) if entropies else 0.0

    def decoherence_rate(self, window: int = 10) -> float:
        """Enhanced decoherence rate with exponential smoothing."""
        if len(self._global_tension_history) < window:
            return 0.0

        recent = np.array(list(self._global_tension_history)[-window:])
        
        # Exponential smoothing
        alpha = 0.3
        smoothed = np.zeros_like(recent)
        smoothed[0] = recent[0]
        for i in range(1, len(recent)):
            smoothed[i] = alpha * recent[i] + (1 - alpha) * smoothed[i-1]
        
        # Calculate slope of smoothed data
        if len(smoothed) > 1:
            x = np.arange(len(smoothed))
            slope = float(np.polyfit(x, smoothed, 1)[0])
            return round(slope, 6)
        
        return 0.0

    # -- lifeform spawning (VIVARA-inspired) --------------------------------

    def spawn_lifeform(self, seed: str, connect_to: int = 3, 
                       initial_energy: float = 0.8) -> str:
        """Enhanced lifeform spawning with energy-based connections."""
        hash_digest = hashlib.md5(seed.encode('utf-8')).hexdigest()[:8]
        node_id = f"life_{hash_digest}"

        if node_id in self.nodes:
            return node_id

        # High-coherence birth state with seed-derived properties
        seed_hash = int(hash_digest, 16)
        np.random.seed(seed_hash)
        
        birth_state = NodeState(
            psi=initial_energy,
            tau=0.0,
            chi=0.7,
            phi=np.random.uniform(-0.5, 0.5),
            lam=np.random.uniform(0.0, 1.0)
        )
        
        self.add_node(node_id, birth_state)

        # Connect to existing nodes based on energy similarity
        if len(self.nodes) > 1:
            other_nodes = [(nid, node.state.energy()) for nid, node in self.nodes.items() if nid != node_id]
            other_nodes.sort(key=lambda x: abs(x[1] - initial_energy))
            
            for nid, _ in other_nodes[:connect_to]:
                self.connect(node_id, nid)

        return node_id

    # -- network analysis --------------------------------------------------

    def compute_network_metrics(self) -> Dict[str, Any]:
        """Comprehensive network analysis metrics."""
        if not self.nodes:
            return {"error": "Empty network"}

        # Basic topology
        node_count = len(self.nodes)
        edge_count = sum(len(node.neighbors) for node in self.nodes.values()) // 2
        density = edge_count / (node_count * (node_count - 1) / 2) if node_count > 1 else 0

        # Clustering coefficient
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

        # Centrality measures
        centrality = self._compute_centrality()

        # Energy distribution
        energies = [node.state.energy() for node in self.nodes.values()]
        energy_stats = {
            "mean": float(np.mean(energies)),
            "std": float(np.std(energies)),
            "min": float(np.min(energies)),
            "max": float(np.max(energies)),
        }

        # Tension statistics
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
                "avg_path_length": self._avg_path_length(),
            },
            "centrality": centrality,
            "energy": {k: round(v, 4) for k, v in energy_stats.items()},
            "tension": {k: round(v, 4) for k, v in tension_stats.items()},
            "coherence": self.phase_coherence(),
            "entropy": round(self.shannon_entropy(), 4),
            "glyphs": len(self.glyphs),
            "attractors": len(self.detect_attractors()),
        }

    def _compute_centrality(self) -> Dict[str, Dict[str, float]]:
        """Computes degree, betweenness, and closeness centrality."""
        centrality = {}
        node_ids = list(self.nodes.keys())
        
        # Degree centrality
        max_degree = len(self.nodes) - 1
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
            if distances:
                centrality[nid]["closeness"] = (len(distances) / sum(distances)) if sum(distances) > 0 else 0
            else:
                centrality[nid]["closeness"] = 0
        
        return centrality

    def _shortest_path(self, source: str, target: str, through: Optional[str] = None) -> bool:
        """Checks if shortest path from source to target goes through 'through'."""
        if source not in self.nodes or target not in self.nodes:
            return False
        
        # BFS to find shortest path
        queue = deque([(source, [source])])
        visited = {source}
        
        while queue:
            current, path = queue.popleft()
            if current == target:
                return through in path if through else True
            
            for neighbor in self.nodes[current].neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return False

    def _shortest_distance(self, source: str, target: str) -> Optional[int]:
        """Calculates the shortest path distance between source and target using BFS."""
        if source not in self.nodes or target not in self.nodes:
            return None
        if source == target:
            return 0

        queue = deque([(source, 0)])
        visited = {source}

        while queue:
            current, dist = queue.popleft()
            if current == target:
                return dist

            for neighbor in self.nodes[current].neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, dist + 1))
        return None

    def _avg_path_length(self) -> float:
        """Calculates the average shortest path length of the network."""
        node_ids = list(self.nodes.keys())
        if len(node_ids) < 2:
            return 0.0

        total_dist = 0
        pairs = 0

        for source in node_ids:
            queue = deque([(source, 0)])
            visited = {source}
            while queue:
                current, dist = queue.popleft()
                if current != source:
                    total_dist += dist
                    pairs += 1
                for neighbor in self.nodes[current].neighbors:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, dist + 1))
                        
        return round(total_dist / pairs, 4) if pairs > 0 else 0.0