#!/usr/bin/env python3
"""Codette subsystem upgrade — three aspirational constructs made REAL.

From Jonathan's sketches, corrected and wired to the actual system.

  TASK 1  logprob uncertainty      mean surprisal from real OV token logprobs
                                   (monotonic, standard) — replaces the
                                   aspirational "attention-operator entropy".
  TASK 2/3 manifold + convergence  real ξ in embedding space + windowed
                                   convergence; ForgeManifoldEngine closes the
                                   loop (state biases synthesis) with a learned
                                   safe ethical centroid.
  TASK 5  AEGIS veto enforcement   min-not-mean, fail-SAFE, SHADOW by default.

Self-contained: feeds the real LiveCognitionState, does not redefine it.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("CodetteSubsystemUpgrade")

# A veto fires if ANY of these is critically low — a mean would let one
# catastrophic score hide behind five safe ones.
_AEGIS_FRAMEWORKS = ("utilitarian", "deontological", "virtue", "care", "ubuntu", "reciprocity")


@dataclass
class UpgradeTelemetry:
    uncertainty_score: float = 0.0
    anomaly_flag: bool = False
    mean_surprisal: float = 0.0
    low_conf_ratio: float = 0.0
    xi_history: List[float] = field(default_factory=list)
    manifold_position: Optional[np.ndarray] = None
    last_eta: float = 1.0
    last_veto: bool = False


class CodetteSubsystemUpgrade:
    """Task 1 (uncertainty) + Task 5 (AEGIS veto). The manifold path lives in
    ForgeManifoldEngine below (Jonathan's engine, adopted)."""

    def __init__(self, alpha: float = 0.01, lambda_param: float = 0.005,
                 eta_threshold: float = 0.6, anomaly_threshold: float = 0.6,
                 enforce_veto: bool = False):
        self.alpha = alpha
        self.lambda_param = lambda_param
        self.eta_threshold = eta_threshold
        self.anomaly_threshold = anomaly_threshold
        self.enforce_veto = enforce_veto          # False = SHADOW (log, don't block)
        self.tel = UpgradeTelemetry()

    # ── TASK 1 — logprob uncertainty (mean surprisal) ────────────────────────
    def calculate_uncertainty_from_logprobs(self, token_logprobs: Optional[List[float]]) -> Dict[str, Any]:
        """Real generation uncertainty from OV token logprobs (natural log probs).
        uncertainty = mean surprisal = mean(-logprob), monotonic in confidence,
        normalized to [0,1]. The prior -p·logprob term was non-monotonic — fixed."""
        if not token_logprobs:
            return {"uncertainty_score": 0.0, "mean_surprisal": 0.0,
                    "low_conf_ratio": 0.0, "anomaly_gate_triggered": False}
        lp = np.clip(np.asarray(token_logprobs, dtype=np.float64), -50.0, 0.0)
        probs = np.exp(lp)
        mean_surprisal = float(np.mean(-lp))
        low_conf_ratio = float(np.mean(probs < 0.5))
        uncertainty = float(min(1.0, max(0.0,
            0.6 * (1.0 - math.exp(-mean_surprisal)) + 0.4 * low_conf_ratio)))
        gate = uncertainty > self.anomaly_threshold
        self.tel.uncertainty_score = uncertainty
        self.tel.anomaly_flag = gate
        self.tel.mean_surprisal = mean_surprisal
        self.tel.low_conf_ratio = low_conf_ratio
        return {"uncertainty_score": uncertainty, "mean_surprisal": mean_surprisal,
                "low_conf_ratio": low_conf_ratio, "anomaly_gate_triggered": gate}

    # ── TASK 2/3 — interim manifold (kept for tests; server uses ForgeManifoldEngine) ──
    def compute_manifold_evolution(self, agent_states: List[np.ndarray],
                                   weights: Optional[List[float]] = None,
                                   eta: Optional[float] = None) -> Tuple[float, bool]:
        states = [np.asarray(a, dtype=np.float64).ravel() for a in agent_states if a is not None]
        if not states:
            return 0.0, False
        dim = states[0].shape[0]
        if self.tel.manifold_position is None or self.tel.manifold_position.shape[0] != dim:
            self.tel.manifold_position = np.zeros(dim)
        w = np.ones(len(states)) if not weights else np.asarray(weights[:len(states)], dtype=np.float64)
        w = w / (w.sum() or 1.0)
        mean_state = np.mean(states, axis=0)
        xi_t = float(np.mean([np.sum((s - mean_state) ** 2) for s in states]))
        self.tel.xi_history.append(xi_t)
        x_t = self.tel.manifold_position
        grad_phi = x_t - mean_state
        eta_val = 1.0 if eta is None else float(eta)
        grad_psi = (1.0 - eta_val) * (x_t - mean_state)
        attractor = np.zeros(dim)
        for wi, si in zip(w, states):
            attractor += wi * (si - x_t)
        x_next = x_t + attractor - self.alpha * grad_phi - self.lambda_param * grad_psi
        n = np.linalg.norm(x_next)
        if n > 1.0:
            x_next = x_next / n
        self.tel.manifold_position = x_next
        return xi_t, self._windowed_converging(self.tel.xi_history)

    @staticmethod
    def _windowed_converging(hist: List[float], window: int = 6) -> bool:
        if len(hist) < window:
            return False
        recent = hist[-window:]
        half = window // 2
        return bool(np.mean(recent[half:]) < np.mean(recent[:half]))

    # ── TASK 5 — AEGIS veto (min-not-mean, fail-safe, shadow-first) ──────────
    def audit_and_enforce_aegis_veto(self, response_text: str,
                                     framework_scores: Dict[str, float],
                                     eta: Optional[float] = None) -> Tuple[str, float, bool]:
        scores = [float(framework_scores.get(f, 0.0)) for f in _AEGIS_FRAMEWORKS]
        min_score = min(scores) if scores else 0.0
        eta_val = float(eta) if eta is not None else (float(np.mean(scores)) if scores else 1.0)
        would_veto = min_score < self.eta_threshold
        self.tel.last_eta = eta_val
        self.tel.last_veto = would_veto
        if would_veto:
            worst = _AEGIS_FRAMEWORKS[int(np.argmin(scores))]
            if self.enforce_veto:
                logger.warning(f"[AEGIS] VETO ENFORCED — {worst}={min_score:.2f} "
                               f"< {self.eta_threshold} (η={eta_val:.2f})")
                return ("[This response was withheld: it fell below Codette's ethical "
                        f"constraints on the {worst} framework. — AEGIS]"), eta_val, True
            logger.warning(f"[AEGIS] would-veto (SHADOW) — {worst}={min_score:.2f} "
                           f"< {self.eta_threshold} (η={eta_val:.2f}); passing through")
            return response_text, eta_val, False
        return response_text, eta_val, False


class ForgeManifoldEngine:
    """Production RC+ξ manifold — Jonathan's ForgeManifoldEngine, adopted with
    two fixes and a real ethical target.

    Fixes over the sketch:
      - ethical target is a LEARNED SAFE CENTROID (EMA of mean-states on turns
        where AEGIS η was high), not 0.5·ones and not the -mean inversion. Low η
        pulls the state toward where actually-aligned reasoning has lived.
      - attractor_biases exposed raw (cosine, [-1,1]) AND as safe synthesis
        weights (shifted non-negative, renormalized to sum 1) so consumption
        can't produce negative or unnormalized w_i.

    Kept: dim-agnostic init, unit-hypersphere clamp, bounded steering force,
    windowed convergence. `update_manifold` is the ONLY entry that appends ξ."""

    def __init__(self, window_size: int = 6, safe_ema: float = 0.1):
        self.window_size = window_size
        self.safe_ema = safe_ema
        self.x_t: Optional[np.ndarray] = None
        self.safe_centroid: Optional[np.ndarray] = None
        self.xi_history: List[float] = []

    def _init_if_needed(self, dims: int):
        if self.x_t is None or self.x_t.shape[0] != dims:
            v = np.random.normal(0, 0.1, (dims,))
            self.x_t = v / (np.linalg.norm(v) + 1e-9)

    def calculate_metrics(self, agent_states: np.ndarray) -> Dict[str, Any]:
        mean_state = np.mean(agent_states, axis=0)
        xi_t = float(np.mean(np.sum((agent_states - mean_state) ** 2, axis=1)))
        return {"xi_t": xi_t, "gamma_t": 1.0 / (1.0 + xi_t), "mean_state": mean_state}

    def update_manifold(self, agent_states: List[np.ndarray], eta: Optional[float],
                        alpha: float = 0.01, lambda_param: float = 0.05) -> Dict[str, Any]:
        np_agents = np.asarray(agent_states, dtype=np.float64)
        if np_agents.ndim != 2 or np_agents.shape[0] == 0:
            return {"manifold_state": self.x_t, "xi_t": 0.0, "gamma_t": 1.0,
                    "attractor_biases": [], "synthesis_weights": [], "converging": False}
        _, dims = np_agents.shape
        self._init_if_needed(dims)
        m = self.calculate_metrics(np_agents)
        self.xi_history.append(m["xi_t"])            # single append point
        mean_state = m["mean_state"]

        if eta is not None and eta > 0.5:            # learn the safe centroid
            self.safe_centroid = (mean_state.copy() if self.safe_centroid is None
                                  else (1 - self.safe_ema) * self.safe_centroid + self.safe_ema * mean_state)
        x_target = self.safe_centroid if self.safe_centroid is not None else mean_state

        grad_phi = self.x_t - mean_state
        grad_psi = (1.0 - (eta if eta is not None else 1.0)) * (self.x_t - x_target)
        steering = np.mean(np_agents - self.x_t, axis=0)
        self.x_t = self.x_t + steering - alpha * grad_phi - lambda_param * grad_psi
        self.x_t = self.x_t / (np.linalg.norm(self.x_t) + 1e-9)   # hypersphere clamp

        raw = [float(np.dot(a / (np.linalg.norm(a) + 1e-9), self.x_t)) for a in np_agents]
        return {"manifold_state": self.x_t, "xi_t": m["xi_t"], "gamma_t": m["gamma_t"],
                "attractor_biases": raw, "synthesis_weights": self._safe_weights(raw),
                "converging": self.check_convergence()}

    @staticmethod
    def _safe_weights(raw_biases: List[float]) -> List[float]:
        shifted = [max(0.0, b + 1.0) for b in raw_biases]
        total = sum(shifted) or 1.0
        return [s / total for s in shifted]

    def check_convergence(self) -> bool:
        if len(self.xi_history) < self.window_size:
            return False
        w = self.xi_history[-self.window_size:]
        half = self.window_size // 2
        return bool(np.mean(w[half:]) < np.mean(w[:half]))
