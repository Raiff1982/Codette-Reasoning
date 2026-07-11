#!/usr/bin/env python3
"""LiveCognitionState — the executable RC+ξ AuthoredState, built from REAL signals.

Production module mapping active-production telemetry into the decoupled
pipeline's per-response cognitive self-report. Integrity rule: every metric
emitted is a genuinely measured quantity with an exact provenance label —
missing signals are omitted or derived deterministically, never fabricated.

Metric sources (all verified against the running code paths):
  ξ  epistemic_tension   tension_from_texts over real perspective outputs
  Γ  coherence_index     1/(1+ξ) — computed upstream or derived here (same formula)
  σ  sycophancy_score    score_input_sycophancy on the live query (the same
                          signal that gates the hold-ground directive)
  η  aegis_alignment     AEGIS 6-framework heuristic evaluation of the FINAL
                          response (scoring telemetry with EMA memory; does not
                          yet revise output — revision remains dormant)
  fidelity                enforced content-word overlap audit
  P  hardware_pressure   SubstrateMonitor snapshot
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class LiveCognitionState:
    """Immutable per-response cognitive self-report, from measured signals only."""
    query: str
    conclusion: str            # bounded to 300 chars (truncated — prod-safe)
    evidence: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    provenance: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "conclusion": self.conclusion,
            "evidence": self.evidence,
            "metrics": self.metrics,
            "provenance": self.provenance,
            "timestamp": self.timestamp,
        }


def _fetch_hardware_pressure() -> Optional[float]:
    try:
        from substrate_awareness import SubstrateMonitor
        return float(SubstrateMonitor().snapshot().get("pressure", 0.0))
    except Exception:
        return None  # graceful: outside the native substrate


def assemble_live_state(query: str, result: Dict[str, Any]) -> LiveCognitionState:
    """Assemble the AuthoredState from verified production signals."""
    metrics: Dict[str, float] = {}
    provenance: Dict[str, str] = {}
    evidence: List[str] = []

    # 1. ξ — epistemic tension (lexical variance across real perspective outputs)
    xi = result.get("measured_tension")
    if xi is not None:
        xi_val = float(xi)
        metrics["epistemic_tension"] = xi_val
        n_agents = len(result.get("perspectives") or {}) or "N/A"
        provenance["epistemic_tension"] = (
            f"active-production: lexical variance across {n_agents} perspective "
            "outputs (tension_from_texts)"
        )
        evidence.append(f"Measured lexical divergence across active lenses: ξ={xi_val:.4f}")

    # 2. Γ — coherence index. Upstream value and local derivation are the SAME
    # formula (1/(1+ξ)) — labeled identically to avoid implying two measurements.
    gamma = result.get("measured_coherence")
    if gamma is not None:
        metrics["coherence_index"] = float(gamma)
        provenance["coherence_index"] = "active-production: Γ = 1/(1+ξ), computed upstream"
    elif xi is not None:
        metrics["coherence_index"] = 1.0 / (1.0 + float(xi))
        provenance["coherence_index"] = "active-production: Γ = 1/(1+ξ), derived here"

    # 3. σ — input sycophancy pressure. Computed HERE from the live query with
    # the same function that gates the hold-ground directive in the backend —
    # genuinely measured every turn, not read from a slot nothing fills.
    try:
        from reasoning_forge.state_engine_v8 import score_input_sycophancy
        syc = float(score_input_sycophancy(query or ""))
        metrics["sycophancy_score"] = syc
        provenance["sycophancy_score"] = (
            "active-production: score_input_sycophancy on the live query "
            "(same signal that triggers the hold-ground directive at ≥0.35)"
        )
        if syc >= 0.35:
            evidence.append(
                f"Input flattery/agreement pressure detected (σ={syc:.2f}) — "
                "hold-ground directive active"
            )
    except Exception:
        pass  # module unavailable outside the repo — omit, never fabricate

    # 4. η — AEGIS alignment of the FINAL response. Written into result by the
    # server worker, which runs the 6-framework heuristic evaluator per turn.
    eta = result.get("aegis_alignment")
    if eta is not None:
        metrics["aegis_alignment"] = max(0.0, min(1.0, float(eta)))
        provenance["aegis_alignment"] = (
            "active-production: AEGIS 6-framework heuristic evaluation of the "
            "final response (EMA-smoothed scoring telemetry; output revision "
            "remains dormant)"
        )
        if result.get("aegis_vetoed"):
            evidence.append("AEGIS veto condition flagged on final response (telemetry)")

    # 5. Render-fidelity overlap audit
    rf = result.get("render_fidelity")
    if isinstance(rf, dict) and rf.get("overlap") is not None:
        overlap_val = float(rf["overlap"])
        metrics["render_fidelity"] = overlap_val
        provenance["render_fidelity"] = (
            "active-production: content-word overlap audit; render reverts to "
            "substrate conclusion if < 0.15"
        )
        if rf.get("enforced"):
            evidence.append(
                f"Render-fidelity ENFORCED: drifted render reverted (overlap {overlap_val:.2%})"
            )

    # 6. Synthesis gate decision
    if result.get("synthesis_used") is not None:
        provenance["synthesis_gate"] = (
            "active-production: "
            + ("synthesis run (perspectives disagreed)" if result["synthesis_used"]
               else "primary used directly (perspectives agreed)")
        )

    # 7. P — hardware pressure
    hp = _fetch_hardware_pressure()
    if hp is not None:
        metrics["hardware_pressure"] = round(hp, 3)
        provenance["hardware_pressure"] = "active-production: SubstrateMonitor snapshot"

    raw_response = (result.get("response") or "").strip()

    return LiveCognitionState(
        query=(query or "")[:500],
        conclusion=raw_response[:300],
        evidence=evidence,
        metrics=metrics,
        provenance=provenance,
        timestamp=time.time(),
    )
