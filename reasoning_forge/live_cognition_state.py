#!/usr/bin/env python3
"""LiveCognitionState — the executable RC+ξ AuthoredState, built from REAL signals.

This is the live counterpart to Jonathan's CodetteEngine simulation. Same
AuthoredState structure he designed — but every metric is a genuine measured
quantity from the production pipeline, never np.random, never a fabricated value.

The integrity rule: the state reports ONLY active-production quantities. The
simulated/aspirational metrics from the fidelity table (spectral entropy of the
attention operator, the anomaly-suppression gate) are deliberately ABSENT — the
object refuses to emit a number it doesn't actually measure. Each field it does
emit carries a `provenance` tag naming its fidelity status, so the object itself
is the "Formal-to-Operational Fidelity" taxonomy, executable and per-response.

This is the moment the theory stops being a diagram and starts running: ξ comes
from tension_from_texts over the real perspective outputs; Γ from 1/(1+ξ); render
fidelity from the enforced overlap audit; hardware pressure from the live monitor.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class LiveCognitionState:
    """Immutable per-response cognitive self-report, from measured signals only."""
    query: str
    conclusion: str            # bounded to 300 chars (truncated, not raised — prod-safe)
    evidence: List[str]
    metrics: Dict[str, float]
    provenance: Dict[str, str]  # metric -> fidelity status + mechanism
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "conclusion": self.conclusion,
            "evidence": self.evidence,
            "metrics": self.metrics,
            "provenance": self.provenance,
            "timestamp": self.timestamp,
        }


def _hardware_pressure() -> Optional[float]:
    try:
        from substrate_awareness import SubstrateMonitor
        return float(SubstrateMonitor().snapshot().get("pressure"))
    except Exception:
        return None


def assemble_live_state(query: str, result: Dict[str, Any]) -> LiveCognitionState:
    """Assemble the AuthoredState from REAL production signals in `result`.

    Only measured quantities are populated; each is tagged with its fidelity
    status. Missing signals are omitted — never invented.
    """
    metrics: Dict[str, float] = {}
    provenance: Dict[str, str] = {}
    evidence: List[str] = []

    # ξ_t — epistemic tension (ACTIVE: lexical variance across perspective texts)
    xi = result.get("measured_tension")
    if xi is not None:
        metrics["epistemic_tension"] = float(xi)
        n = len(result.get("perspectives") or {}) or "n"
        provenance["epistemic_tension"] = (
            "active-production: lexical variance across perspective outputs "
            "(tension_from_texts)"
        )
        evidence.append(f"Measured lexical divergence across {n} perspectives: ξ={float(xi):.4f}")

    # Γ_t — coherence index (ACTIVE: derived 1/(1+ξ))
    gamma = result.get("measured_coherence")
    if gamma is not None:
        metrics["coherence_index"] = float(gamma)
        provenance["coherence_index"] = "active-production: Γ = 1/(1+ξ)"

    # render fidelity (ACTIVE: enforced content-word overlap audit)
    rf = result.get("render_fidelity")
    if isinstance(rf, dict) and rf.get("overlap") is not None:
        metrics["render_fidelity"] = float(rf["overlap"])
        provenance["render_fidelity"] = (
            "active-production: content-word overlap; render reverts to substrate "
            "conclusion if < 0.15"
        )
        if rf.get("enforced"):
            evidence.append("Render-fidelity ENFORCED: drifted render reverted to substrate conclusion")

    # synthesis gate decision (ACTIVE: tension-gated dispatch)
    if result.get("synthesis_used") is not None:
        provenance["synthesis_gate"] = (
            "active-production: "
            + ("synthesis run (perspectives disagreed)" if result["synthesis_used"]
               else "primary used directly (perspectives agreed)")
        )

    # hardware pressure P (ACTIVE: substrate monitor)
    hp = _hardware_pressure()
    if hp is not None:
        metrics["hardware_pressure"] = round(hp, 3)
        provenance["hardware_pressure"] = "active-production: SubstrateMonitor snapshot"

    resp = (result.get("response") or "").strip()
    conclusion = resp[:300]

    return LiveCognitionState(
        query=(query or "")[:500],
        conclusion=conclusion,
        evidence=evidence,
        metrics=metrics,
        provenance=provenance,
        timestamp=time.time(),
    )
