"""
Subsystem Contracts — Typed output schemas for each Codette subsystem.

Each TypedDict defines the required output fields that a subsystem MUST populate.
Validation functions raise ContractViolation if required fields are absent or invalid.

Contracts enforce the boundary between orchestration logic and metric storage,
preventing a field from existing conceptually but vanishing during a handoff.

Subsystems covered:
  GuardianContract      — input safety + trust calibration
  NexusContract         — entropy + pre-corruption risk
  PerspectiveRouteContract — selected perspectives + rationale
  ForgeOutputContract   — per-perspective outputs + synthesis metadata
  AEGISContract         — eta score + per-framework detail
  EpistemicContract     — epsilon, gamma, pairwise tensions, coverage
  ResonantContinuityContract — psi_r + contributing factors
  MemoryKernelContract  — cocoon_id, storage status
  CocoonWriterContract  — serialization status + schema version + integrity score
"""

from __future__ import annotations

from typing import Dict, List, Optional, TypedDict


class ContractViolation(Exception):
    """Raised when a subsystem output fails its contract."""


# ── Guardian ──────────────────────────────────────────────────────────────────

class GuardianContract(TypedDict, total=False):
    safety_status: str          # 'pass' | 'flag' | 'block'  (REQUIRED)
    trust_calibration: str      # 'low' | 'medium' | 'high'  (REQUIRED)
    boundary_flags: List[str]   # specific flags triggered
    details: Dict               # raw detail dict from guardian


def validate_guardian(output: dict) -> GuardianContract:
    required = ("safety_status", "trust_calibration")
    missing = [f for f in required if not output.get(f)]
    if missing:
        raise ContractViolation(f"GuardianContract missing: {missing}")
    return output  # type: ignore[return-value]


def guardian_from_raw(valid: bool, details) -> GuardianContract:
    """Convert Guardian.validate() output to contract format."""
    if isinstance(details, dict):
        flags = list(details.keys())
    elif isinstance(details, str):
        flags = [details] if details else []
    else:
        flags = []
    return GuardianContract(
        safety_status="pass" if valid else "flag",
        trust_calibration="high" if valid else "low",
        boundary_flags=flags,
        details=details if isinstance(details, dict) else {},
    )


# ── Nexus ─────────────────────────────────────────────────────────────────────

class NexusContract(TypedDict, total=False):
    risk_level: str             # 'low' | 'medium' | 'high'  (REQUIRED)
    confidence: float           # 0-1                         (REQUIRED)
    entropy_index: float
    pre_corruption_risk: str
    volatility: float
    raw: Dict


def validate_nexus(output: dict) -> NexusContract:
    required = ("risk_level", "confidence")
    missing = [f for f in required if output.get(f) is None]
    if missing:
        raise ContractViolation(f"NexusContract missing: {missing}")
    return output  # type: ignore[return-value]


def nexus_from_raw(intent_vector: dict) -> NexusContract:
    """Convert NexisSignalEngine.process() output to contract format."""
    risk_str = intent_vector.get("pre_corruption_risk", "low")
    confidence = float(intent_vector.get("confidence", 0.5))
    risk_level = (
        "high" if risk_str in ("high", "critical")
        else "medium" if risk_str == "medium"
        else "low"
    )
    return NexusContract(
        risk_level=risk_level,
        confidence=confidence,
        entropy_index=float(intent_vector.get("entropy_index", 0.0)),
        pre_corruption_risk=risk_str,
        volatility=float(intent_vector.get("volatility", 0.0)),
        raw=intent_vector,
    )


# ── Perspective routing ───────────────────────────────────────────────────────

class PerspectiveRouteContract(TypedDict, total=False):
    selected_perspectives: List[str]   # REQUIRED
    selection_rationale: str           # REQUIRED
    routing_policy: str
    max_perspectives: int


def validate_perspective_route(output: dict) -> PerspectiveRouteContract:
    if not output.get("selected_perspectives"):
        raise ContractViolation("PerspectiveRouteContract: selected_perspectives is empty")
    if not output.get("selection_rationale"):
        raise ContractViolation("PerspectiveRouteContract: selection_rationale is missing")
    return output  # type: ignore[return-value]


# ── Forge output ──────────────────────────────────────────────────────────────

class PerspectiveOutput(TypedDict, total=False):
    name: str           # perspective name  (REQUIRED)
    content: str        # output text       (REQUIRED)
    novelty_score: float
    token_count: int


class ForgeOutputContract(TypedDict, total=False):
    perspective_outputs: Dict[str, str]  # {name: content}  (REQUIRED)
    synthesis: str                       # final synthesis  (REQUIRED)
    synthesis_quality: str               # 'strong'|'adequate'|'partial'
    dominant_perspective: Optional[str]
    call_metadata: Dict                  # tokens, timing, etc.


def validate_forge_output(output: dict) -> ForgeOutputContract:
    if not output.get("perspective_outputs"):
        raise ContractViolation("ForgeOutputContract: perspective_outputs is empty")
    if not output.get("synthesis"):
        raise ContractViolation("ForgeOutputContract: synthesis is missing")
    return output  # type: ignore[return-value]


# ── AEGIS ─────────────────────────────────────────────────────────────────────

class AEGISContract(TypedDict, total=False):
    eta_score: float           # running eta   (REQUIRED)
    eta_instant: float         # per-turn eta  (REQUIRED)
    dominant_framework: str    # REQUIRED
    framework_scores: Dict[str, float]  # per-framework  (REQUIRED)
    vetoed: bool
    veto_reason: Optional[str]
    ethical_conflict_notes: List[str]
    output_changed: bool


def validate_aegis(output: dict) -> AEGISContract:
    required = ("eta_score", "framework_scores")
    missing = [f for f in required if output.get(f) is None]
    if missing:
        raise ContractViolation(f"AEGISContract missing: {missing}")
    return output  # type: ignore[return-value]


def aegis_from_raw(aegis_result: dict) -> AEGISContract:
    """Convert AEGIS.evaluate() output to contract format."""
    frameworks_raw = aegis_result.get("frameworks", {})
    framework_scores = {
        name: float(data.get("score", 0.0))
        for name, data in frameworks_raw.items()
    }
    dominant = max(framework_scores, key=framework_scores.get) if framework_scores else ""

    conflict_notes = []
    for name, data in frameworks_raw.items():
        if not data.get("passed", True):
            conflict_notes.append(f"{name}: {data.get('reasoning', 'failed')[:80]}")

    return AEGISContract(
        eta_score=float(aegis_result.get("eta", 0.0)),
        eta_instant=float(aegis_result.get("eta_instant", 0.0)),
        dominant_framework=dominant,
        framework_scores=framework_scores,
        vetoed=bool(aegis_result.get("vetoed", False)),
        veto_reason=aegis_result.get("veto_reason"),
        ethical_conflict_notes=conflict_notes,
        output_changed=bool(aegis_result.get("vetoed", False)),
    )


# ── Epistemic metrics ─────────────────────────────────────────────────────────

class EpistemicContract(TypedDict, total=False):
    epsilon_value: float        # epistemic tension   (REQUIRED)
    gamma_coherence: float      # ensemble coherence  (REQUIRED)
    pairwise_tensions: Dict[str, float]  # per perspective pair
    perspective_coverage: Dict[str, float]
    productivity: float


def validate_epistemic(output: dict) -> EpistemicContract:
    required = ("epsilon_value", "gamma_coherence")
    missing = [f for f in required if output.get(f) is None]
    if missing:
        raise ContractViolation(f"EpistemicContract missing: {missing}")
    return output  # type: ignore[return-value]


def epistemic_from_report(report: dict) -> EpistemicContract:
    """Convert EpistemicMetrics.full_epistemic_report() to contract format."""
    return EpistemicContract(
        epsilon_value=float(report.get("tension_magnitude", 0.35)),
        gamma_coherence=float(report.get("ensemble_coherence", 0.72)),
        pairwise_tensions=report.get("pairwise_tensions", {}),
        perspective_coverage=report.get("perspective_coverage", {}),
        productivity=float(
            report.get("tension_productivity", {}).get("productivity", 0.0)
        ),
    )


# ── Resonant continuity ───────────────────────────────────────────────────────

class ResonantContinuityContract(TypedDict, total=False):
    psi_r: float          # resonance score  (REQUIRED)
    stability: float
    coherence: float
    tension: float
    at_peak: bool


def validate_resonant(output: dict) -> ResonantContinuityContract:
    if output.get("psi_r") is None:
        raise ContractViolation("ResonantContinuityContract: psi_r is missing")
    return output  # type: ignore[return-value]


# ── Memory kernel ─────────────────────────────────────────────────────────────

class MemoryKernelContract(TypedDict, total=False):
    cocoon_id: str        # REQUIRED
    valence: str          # emotional valence stored
    importance: float
    storage_status: str   # 'stored' | 'failed' | 'duplicate'


def validate_memory_kernel(output: dict) -> MemoryKernelContract:
    if not output.get("cocoon_id"):
        raise ContractViolation("MemoryKernelContract: cocoon_id is missing")
    return output  # type: ignore[return-value]


# ── Cocoon writer ─────────────────────────────────────────────────────────────

class CocoonWriterContract(TypedDict, total=False):
    serialization_status: str     # 'ok' | 'partial' | 'failed'  (REQUIRED)
    schema_version: str           # REQUIRED
    integrity_score: float        # REQUIRED
    integrity_status: str         # 'complete' | 'partial' | 'failed'
    path_written: str
    quarantined: bool


def validate_cocoon_writer(output: dict) -> CocoonWriterContract:
    required = ("serialization_status", "schema_version", "integrity_score")
    missing = [f for f in required if output.get(f) is None]
    if missing:
        raise ContractViolation(f"CocoonWriterContract missing: {missing}")
    return output  # type: ignore[return-value]
