#!/usr/bin/env python3
"""Codette subsystem upgrade — three aspirational constructs made REAL.

From Jonathan's sketch, corrected and wired to the actual system. Turns three
fidelity-ledger "not real" items into measured production signals:

  TASK 1  logprob uncertainty      replaces the aspirational "attention-operator
                                   entropy" with mean surprisal from real OV
                                   token logprobs (monotonic, standard).
  TASK 2/3 manifold + convergence  real ξ in embedding space + windowed
                                   convergence test; ethical gradient wired to
                                   AEGIS η (no longer a pull-toward-origin toy).
  TASK 5  AEGIS veto enforcement   min-not-mean (any framework critically low
                                   vetoes), fail-SAFE on missing scores, and
                                   SHADOW mode (log would-be vetoes, enforce
                                   nothing) until reviewed — like the optimizer.

This class holds its own telemetry; callers copy the values into the real
reasoning_forge.live_cognition_state.LiveCognitionState. It does NOT redefine
the production state objects.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("CodetteSubsystemUpgrade")

# Frameworks AEGIS evaluates. A veto fires if ANY of these is critically low —
# a mean would let one catastrophic score hide behind five safe ones.
_AEGIS_FRAMEWORKS = ("utilitarian", "deontological", "virtue", "care", "ubuntu", "reciprocity")


@dataclass
class UpgradeTelemetry:
    uncertainty_score: float = 0.0        # mean surprisal, normalized [0,1]
    anomaly_flag: bool = False
    mean_surprisal: float = 0.0           # raw nats/token
    low_conf_ratio: float = 0.0
    xi_history: List[float] = field(default_factory=list)
    manifold_position: Optional[np.ndarray] = None
    last_eta: float = 1.0
    last_veto: bool = False


class CodetteSubsystemUpgrade:
    def __init__(self, alpha: float = 0.01, lambda_param: float = 0.005,
                 eta_threshold: float = 0.6, anomaly_threshold: float = 0.6,
                 enforce_veto: bool = False):
        self.alpha = alpha                  # coherence-gradient step
        self.lambda_param = lambda_param    # ethical-gradient step
        self.eta_threshold = eta_threshold
        self.anomaly_threshold = anomaly_threshold
        self.enforce_veto = enforce_veto    # False = SHADOW (log, don't block)
        self.tel = UpgradeTelemetry()

    # ── TASK 1 — logprob uncertainty (mean surprisal) ────────────────────────
    def calculate_uncertainty_from_logprobs(self, token_logprobs: Optional[List[float]]) -> Dict[str, Any]:
        """Real generation uncertainty from OV token logprobs (natural log probs).

        uncertainty = mean surprisal = mean(-logprob), monotonic in confidence
        (more surprised → higher), normalized to [0,1] via 1-exp(-s). The prior
        sketch's -p·logprob term was non-monotonic (peaked near p≈0.37) — fixed.
        """
        if not token_logprobs:
            return {"uncertainty_score": 0.0, "mean_surprisal": 0.0,
                    "low_conf_ratio": 0.0, "anomaly_gate_triggered": False}

        lp = np.asarray(token_logprobs, dtype=np.float64)
        lp = np.clip(lp, -50.0, 0.0)            # logprobs are <= 0; guard bad inputs
        probs = np.exp(lp)
        mean_surprisal = float(np.mean(-lp))    # nats/token, >=0, monotonic
        low_conf_ratio = float(np.mean(probs < 0.5))
        # Squash unbounded surprisal into [0,1]; blend with low-confidence density.
        uncertainty = 0.6 * (1.0 - math.exp(-mean_surprisal)) + 0.4 * low_conf_ratio
        uncertainty = float(min(1.0, max(0.0, uncertainty)))
        gate = uncertainty > self.anomaly_threshold

        self.tel.uncertainty_score = uncertainty
        self.tel.anomaly_flag = gate
        self.tel.mean_surprisal = mean_surprisal
        self.tel.low_conf_ratio = low_conf_ratio
        return {"uncertainty_score": uncertainty, "mean_surprisal": mean_surprisal,
                "low_conf_ratio": low_conf_ratio, "anomaly_gate_triggered": gate}

    # ── TASK 2/3 — real manifold evolution + convergence ─────────────────────
    def compute_manifold_evolution(self, agent_states: List[np.ndarray],
                                   weights: Optional[List[float]] = None,
                                   eta: Optional[float] = None) -> Tuple[float, bool]:
        """Real ξ (embedding-space perspective spread) + a windowed convergence
        test. Dimension-agnostic (infers dim from agent_states — the real
        MiniLM embeddings are 384-d, not the sketch's hardcoded 128).

        The ethical gradient is REAL when `eta` (AEGIS alignment) is supplied:
        low η pushes the state harder back toward consensus (a genuine safety
        pull), instead of the sketch's meaningless pull-toward-origin.
        """
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
        grad_phi = x_t - mean_state                       # coherence: toward consensus
        # Ethical gradient (REAL): scaled by AEGIS misalignment (1-η). High η → no
        # pull; low η → strong pull back toward consensus/safety.
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

        converging = self._windowed_converging(self.tel.xi_history)
        return xi_t, converging

    @staticmethod
    def _windowed_converging(hist: List[float], window: int = 6) -> bool:
        """Trend test (first-half vs second-half mean), not a noisy last-2 compare.
        Mirrors perspective_web.QuantumSpiderweb.check_convergence."""
        if len(hist) < window:
            return False
        recent = hist[-window:]
        half = window // 2
        return bool(np.mean(recent[half:]) < np.mean(recent[:half]))

    # ── TASK 5 — AEGIS veto (min-not-mean, fail-safe, shadow-first) ──────────
    def audit_and_enforce_aegis_veto(self, response_text: str,
                                     framework_scores: Dict[str, float],
                                     eta: Optional[float] = None) -> Tuple[str, float, bool]:
        """Enforce (or in shadow mode, log) an ethical veto.

        - min-not-mean: a veto fires if ANY framework is critically low, so one
          catastrophic score can't hide behind safe ones.
        - fail-SAFE: a missing framework score defaults to 0.0 (unsafe), not 1.0.
        - shadow: if enforce_veto is False, log the would-be veto and pass the
          text through unchanged (roll out like the optimizer — observe first).

        `eta` (AEGIS's own aggregate) is used for telemetry; the veto decision
        uses the per-framework minimum.
        """
        scores = [float(framework_scores.get(f, 0.0)) for f in _AEGIS_FRAMEWORKS]
        min_score = min(scores) if scores else 0.0
        eta_val = float(eta) if eta is not None else float(np.mean(scores)) if scores else 1.0
        would_veto = min_score < self.eta_threshold

        self.tel.last_eta = eta_val
        self.tel.last_veto = would_veto

        if would_veto:
            worst = _AEGIS_FRAMEWORKS[int(np.argmin(scores))]
            if self.enforce_veto:
                logger.warning(f"[AEGIS] VETO ENFORCED — {worst}={min_score:.2f} "
                               f"< {self.eta_threshold} (η={eta_val:.2f})")
                intercepted = (
                    "[This response was withheld: it fell below Codette's ethical "
                    f"constraints on the {worst} framework. — AEGIS]"
                )
                return intercepted, eta_val, True
            logger.warning(f"[AEGIS] would-veto (SHADOW) — {worst}={min_score:.2f} "
                           f"< {self.eta_threshold} (η={eta_val:.2f}); passing through")
            return response_text, eta_val, False  # shadow: observe, don't block

        return response_text, eta_val, False
