"""
Codette Quantum Harmonic Framework (v2.0)
=========================================
Architecture: Phase 1 Harmonic Damping + Attractor Field + Resonant Continuity
Purpose:      Stabilizes recursive reasoning by dampening high-tension divergence.

Two complementary interfaces:

Vector interface  (physics layer)
    calculate_epistemic_tension(state_a, state_b)  -> float  (L2-squared divergence)
    apply_harmonic_damping(wavefunction, epsilon)  -> np.ndarray  (log-scale pull)
    update_resonant_continuity(states)             -> dict   (gamma, epsilon, psi_r)
    update_attractor_field(state, epsilon, label)          (register stable cluster)
    nearest_attractor(state)                       -> np.ndarray | None

    Used when numpy perspective output vectors are available (forge_with_debate).

Scalar interface  (routing layer)
    stabilize(epsilon: float)                      -> float  (attractor-targeted decay)
    psi_r                                          -> float  (trajectory smoothness)
    consecutive_high_tension_depth                 -> int

    Used by forge_engine and codette_forge_bridge for AAP attractor routing.
    The scalar and vector layers share state: stabilize() records to _history and
    updates _depth exactly as before.

Integration note
    forge_engine.py calls self.qhf.stabilize(raw_epsilon) — must remain intact.
    Future: when perspective state vectors are available, call
    update_resonant_continuity(states) and pass the returned epsilon to stabilize().
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

# ── Attractor constants (must match SynthesisEngineV3 thresholds) ─────────────
ATTRACTOR_FACT       = 0.35   # Newtonian-First boundary
ATTRACTOR_SYNTHESIS  = 0.52   # Centre of Synthesis band
ATTRACTOR_DISCOVERY  = 0.70   # Discovery boundary

TENSION_THRESHOLD    = 0.50   # epsilon above which damping activates
DAMPING_BASE         = 0.15   # base damping rate (matches user design)
DAMPING_SENSITIVITY  = 2.5    # k: exponential scalar-layer scale above threshold
PSI_R_WINDOW         = 6      # recent steps used for trajectory Psi_r


# ── Vector interface (physics layer) ─────────────────────────────────────────

class QuantumHarmonicFramework:
    """
    Harmonic stabilization engine for Codette's reasoning cycles.

    Maintains two parallel representations:
    - State vectors  (numpy)  — track perspective divergence in wavefunction space
    - Scalar epsilon (float)  — drives AAP attractor routing in forge_engine

    Both update on every reasoning cycle so the two layers stay synchronised.
    """

    def __init__(
        self,
        damping_base: float = DAMPING_BASE,
        stability_threshold: float = TENSION_THRESHOLD,
    ):
        self.damping_base        = damping_base
        self.stability_threshold = stability_threshold

        # Vector-layer state
        self.state_history: List[np.ndarray] = []
        self.attractor_field: Dict[str, dict] = {}   # label -> {state, epsilon, timestamp}

        # Scalar-layer state  (used by stabilize() / forge_engine)
        self._history: List[float] = []
        self._depth: int = 0

    # ── Vector interface ──────────────────────────────────────────────────────

    def calculate_epistemic_tension(
        self,
        current_state: np.ndarray,
        previous_state: np.ndarray,
    ) -> float:
        """
        epsilon_n = ||A_{n+1} - A_n||^2

        Measures cognitive conflict between consecutive reasoning states.
        Returns a non-negative float; higher = more divergent perspectives.
        """
        return float(np.sum(np.square(current_state - previous_state)))

    def apply_harmonic_damping(
        self,
        current_wavefunction: np.ndarray,
        epsilon: float,
    ) -> np.ndarray:
        """
        Apply non-linear log-scale damping to a perspective state vector.

        When tension exceeds stability_threshold, damping increases via
        log(1 + epsilon) to prevent loop-collapse without over-damping.

        FIX vs original design: dynamic_damping is clamped to [0, 0.95].
        Without this clamp, at epsilon >> 1 the coefficient exceeds 1.0 and
        the wavefunction inverts (negative values), which corrupts coherence.

        Returns:
            damped_wave = current_wavefunction * (1 - dynamic_damping)
        """
        if epsilon > self.stability_threshold:
            # High tension: log-scale growth for gradual but significant damping
            dynamic_damping = self.damping_base * (1.0 + math.log(1.0 + epsilon))
        else:
            # Low tension: baseline damping allows natural convergence
            dynamic_damping = self.damping_base

        # CLAMP: prevent inversion.  Max damping = 95% reduction.
        dynamic_damping = min(dynamic_damping, 0.95)

        return current_wavefunction * (1.0 - dynamic_damping)

    def update_resonant_continuity(
        self,
        states: Optional[List[np.ndarray]] = None,
    ) -> Dict[str, float]:
        """
        Compute gamma, epsilon, and psi_r from wavefunction state history.

        Args:
            states: If provided, appended to self.state_history first.
                    If None, uses self.state_history directly.

        Returns:
            {
              "gamma":   coherence score (0-1), inversely proportional to tension
              "epsilon": raw wavefunction-space tension (L2-squared divergence)
              "psi_r":   resonant alignment of the damped final state (tanh of mean)
            }
        """
        if states:
            self.state_history.extend(states)

        history = self.state_history
        if len(history) < 2:
            return {"gamma": 1.0, "epsilon": 0.0, "psi_r": 1.0}

        epsilon = self.calculate_epistemic_tension(history[-1], history[-2])

        # Damp the current state toward equilibrium
        damped_state = self.apply_harmonic_damping(history[-1], epsilon)

        # Update attractor field with stable states
        self.update_attractor_field(history[-1], epsilon)

        # gamma: coherence inversely proportional to tension
        gamma = 1.0 / (1.0 + epsilon)

        # psi_r (vector): tanh of mean of damped state — resonant alignment
        # Range: (-1, 1); positive = aligned toward equilibrium
        psi_r_vec = float(np.tanh(np.mean(damped_state)))

        return {
            "gamma":   round(gamma, 4),
            "epsilon": round(epsilon, 4),
            "psi_r":   round(psi_r_vec, 4),
        }

    def update_attractor_field(
        self,
        state: np.ndarray,
        epsilon: float,
        label: str = "",
    ) -> None:
        """Register a state as a stable attractor cluster when tension is low.

        Attractors represent 'known truths' — states the system has visited
        with high coherence.  When in high-tension territory, nearest_attractor()
        can supply a target for directed damping.

        Args:
            state:   Current perspective state vector.
            epsilon: Current tension value.
            label:   Optional human-readable label (e.g. 'newtonian_convergence').
        """
        # Only register genuinely stable states
        if epsilon < self.stability_threshold * 0.5:
            key = label or f"attractor_{len(self.attractor_field)}"
            self.attractor_field[key] = {
                "state":     state.copy(),
                "epsilon":   round(epsilon, 6),
                "timestamp": time.time(),
            }

    def nearest_attractor(
        self,
        current_state: np.ndarray,
    ) -> Optional[np.ndarray]:
        """Return the nearest registered attractor state, or None.

        Used to provide a directed damping target when apply_harmonic_damping
        is called with a specific convergence goal rather than zero-point pull.
        """
        if not self.attractor_field:
            return None
        best_dist  = float("inf")
        best_state = None
        for entry in self.attractor_field.values():
            dist = float(np.linalg.norm(current_state - entry["state"]))
            if dist < best_dist:
                best_dist  = dist
                best_state = entry["state"]
        return best_state

    def apply_directed_damping(
        self,
        current_wavefunction: np.ndarray,
        epsilon: float,
    ) -> np.ndarray:
        """Variant of apply_harmonic_damping that pulls toward the nearest attractor.

        If no attractors are registered, falls back to zero-point damping.
        This is the preferred method when attractor_field is populated.
        """
        target = self.nearest_attractor(current_wavefunction)
        if target is None:
            return self.apply_harmonic_damping(current_wavefunction, epsilon)

        if epsilon > self.stability_threshold:
            dynamic_damping = self.damping_base * (1.0 + math.log(1.0 + epsilon))
        else:
            dynamic_damping = self.damping_base

        dynamic_damping = min(dynamic_damping, 0.95)

        # Interpolate between current state and nearest attractor
        # At max damping (0.95) we're almost fully at the attractor
        return current_wavefunction * (1.0 - dynamic_damping) + target * dynamic_damping

    # ── Scalar interface (routing layer — used by forge_engine) ───────────────

    def stabilize(
        self,
        epsilon: float,
        damping_strength: float = 1.0,
    ) -> float:
        """Scalar AAP routing path: apply attractor-targeted decay to raw epsilon.

        Called by forge_engine._forge_single_safe() after the epistemic report
        is computed.  Returns a damped scalar epsilon that drives SynthesisEngineV3
        attractor selection.

        The scalar and vector layers share _history and _depth so Psi_r and
        depth counters reflect both types of input.
        """
        if epsilon <= self.stability_threshold:
            self._depth = max(0, self._depth - 1)
        else:
            self._depth += 1

        # Nearest stable attractor for this epsilon level
        if epsilon > ATTRACTOR_DISCOVERY:
            attractor = ATTRACTOR_DISCOVERY
        else:
            attractor = ATTRACTOR_SYNTHESIS

        # Persistence bonus: sustained high tension amplifies damping
        n_high = sum(1 for e in self._history[-PSI_R_WINDOW:] if e > self.stability_threshold)
        persistence_bonus = n_high * 0.15

        # Exponential decay toward attractor (scalar space)
        excess   = max(0.0, epsilon - self.stability_threshold)
        lambda_d = self.damping_base * math.exp(DAMPING_SENSITIVITY * excess)
        total_depth = (self._depth + persistence_bonus) * damping_strength
        stabilized = attractor + (epsilon - attractor) * math.exp(-lambda_d * total_depth)
        stabilized = float(max(0.0, min(1.0, stabilized)))

        self._history.append(stabilized)
        return stabilized

    @property
    def psi_r(self) -> float:
        """Trajectory Psi_r: smoothness of the scalar epsilon path.

        Distinct from the vector psi_r returned by update_resonant_continuity().
        High (>0.7) = epsilon moving coherently.  Low (<0.3) = oscillating.
        """
        if len(self._history) < 2:
            return 1.0
        recent = self._history[-PSI_R_WINDOW:]
        deltas = [abs(recent[i] - recent[i - 1]) for i in range(1, len(recent))]
        return float(max(0.0, min(1.0, 1.0 - sum(deltas) / len(deltas))))

    @property
    def consecutive_high_tension_depth(self) -> int:
        return self._depth

    def reset(self) -> None:
        """Reset all state (new conversation)."""
        self._history.clear()
        self._depth = 0
        self.state_history.clear()
        # Keep attractor_field — stable truths persist across sessions

    def to_dict(self) -> dict:
        return {
            "psi_r_trajectory": round(self.psi_r, 4),
            "depth":            self._depth,
            "epsilon_history":  [round(e, 4) for e in self._history[-PSI_R_WINDOW:]],
            "attractor_count":  len(self.attractor_field),
        }


# ── Module-level convenience function (backward compat) ───────────────────────

def apply_harmonic_damping(
    epsilon: float,
    history: Optional[List[float]] = None,
    depth: int = 1,
    damping_strength: float = 1.0,
) -> float:
    """Scalar convenience wrapper — used in standalone tests and smoke checks."""
    qhf = QuantumHarmonicFramework()
    if history:
        qhf._history = list(history)
    qhf._depth = depth
    return qhf.stabilize(epsilon, damping_strength=damping_strength)


def psi_r(history: List[float]) -> float:
    """Compute trajectory Psi_r from a list of epsilon values."""
    qhf = QuantumHarmonicFramework()
    qhf._history = list(history)
    return qhf.psi_r


# ── Physics visualization (run standalone) ───────────────────────────────────

_NUM_AGENTS    = 3
_d             = 2.0
_G             = 6.67430e-11
_m             = 1.0
_base_freq     = 440.0
_intent_coef   = 0.7
_tunnel        = 0.4
_quantum_states= np.array([1, -1])
_entanglement  = 0.85
_decoherence   = 0.02
_hbar          = 1.0545718e-34


def _quantum_harmonic_dynamics(t: float, y: np.ndarray) -> np.ndarray:
    positions     = y[::4]
    velocities    = y[1::4]
    accelerations = np.zeros_like(positions)

    for i in range(_NUM_AGENTS):
        for j in range(i + 1, _NUM_AGENTS):
            r_ij = positions[j] - positions[i]
            dist = np.linalg.norm(r_ij)
            if dist > 1e-6:
                force           = (_G * _m * _m / dist ** 3) * r_ij
                accelerations[i] += force / _m
                accelerations[j] -= force / _m

    q_mod   = np.dot(_quantum_states, np.sin(2 * np.pi * _base_freq * t / 1000)) * _intent_coef
    tunnel  = _tunnel * np.exp(-np.linalg.norm(positions) / _hbar) if np.random.rand() < _tunnel else 0
    entangl = _entanglement * np.exp(-np.linalg.norm(positions) / _hbar)
    decoh   = _decoherence * (1 - np.exp(-np.linalg.norm(positions) / _hbar))

    harmonic = np.full_like(positions, q_mod + entangl + tunnel - decoh)
    accelerations += harmonic
    return np.concatenate([velocities.flatten(), accelerations.flatten()])


if __name__ == "__main__":
    from scipy.integrate import solve_ivp
    import matplotlib.pyplot as plt

    agent_positions  = np.array([[-_d, 0], [0, 0], [_d, 0]])
    agent_velocities = np.array([[0, 0.5], [0, -0.5], [0, 0.3]])
    y0 = np.concatenate([p + v for p, v in zip(agent_positions, agent_velocities)])

    sol = solve_ivp(_quantum_harmonic_dynamics, (0, 100), y0,
                    t_eval=np.linspace(0, 100, 2500), method='RK45')
    positions  = sol.y[::4]
    velocities = sol.y[1::4]

    plt.figure(figsize=(10, 10))
    for i, color in enumerate(['b', 'r', 'g']):
        plt.plot(positions[i], velocities[i],
                 label=f'AI Node {i+1} (Quantum Resonance)', linewidth=2, color=color)

    plt.plot(0, 0, 'ko', label='Core Equilibrium')
    for label, eps, style in [
        ("Fact Attractor",      ATTRACTOR_FACT,      "b--"),
        ("Synthesis Attractor", ATTRACTOR_SYNTHESIS, "r--"),
        ("Discovery Attractor", ATTRACTOR_DISCOVERY, "g--"),
    ]:
        plt.axhline(eps, linestyle=style[1:], color=style[0], alpha=0.4, label=label)

    plt.xlabel('X Position')
    plt.ylabel('Y Position / Epsilon Overlay')
    plt.title('Codette Quantum Harmonic AI Multi-Agent Synchronization\n(v2.0 — with Attractor Field Overlays)')
    plt.legend(fontsize=8)
    plt.axis('equal')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("Codette_Quantum_Harmonic_Framework.png")
    print("Saved Codette_Quantum_Harmonic_Framework.png")

    # ── Logic Verification (from user design) ────────────────────────────────
    print("\n-- Logic Verification --")
    qhf = QuantumHarmonicFramework()
    state_a = np.array([0.1, 0.2, 0.8])
    state_b = np.array([0.9, 0.1, 0.2])
    metrics = qhf.update_resonant_continuity([state_a, state_b])
    print(f"Post-Upgrade Metrics: {metrics}")

    # ── Damping clamp demonstration ───────────────────────────────────────────
    print("\n-- Damping Clamp Test --")
    test_wave = np.array([1.0, 1.0, 1.0])
    for eps in [0.3, 0.6, 2.0, 10.0, 100.0]:
        damped = qhf.apply_harmonic_damping(test_wave, eps)
        coeff  = 1.0 - damped[0]  # implied damping applied
        print(f"  epsilon={eps:6.1f}  damped[0]={damped[0]:.4f}  applied_coeff={coeff:.4f}")

    # ── Attractor field ───────────────────────────────────────────────────────
    print("\n-- Attractor Field --")
    stable = np.array([0.5, 0.5, 0.5])
    qhf.update_attractor_field(stable, epsilon=0.05, label="convergence_point")
    nearest = qhf.nearest_attractor(np.array([0.4, 0.6, 0.4]))
    print(f"  Registered attractors: {list(qhf.attractor_field.keys())}")
    print(f"  Nearest attractor to [0.4, 0.6, 0.4]: {nearest}")
