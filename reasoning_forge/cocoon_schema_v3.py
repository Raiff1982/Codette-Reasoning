"""
Cocoon Schema v3 — Runtime Provenance + Integrity + Telemetry

Extends v2.Cocoon with:
  - Execution path provenance (forge_full / adapter_lightweight / fallback_template / recovery_mode)
  - Model inference attestation
  - Integrity scoring (0-1 composite)
  - Echo / perspective-collapse detection flags
  - Full AEGIS per-framework detail
  - Guardian + Nexus block fields
  - Synthesis structure (convergences, divergences, tradeoffs)
  - Pairwise epistemic tensions + perspective coverage
  - Graded fallback ladder support

Every cocoon written to disk MUST include execution_path and cocoon_integrity_score.
Silent omission of these fields is treated as an incomplete write.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from reasoning_forge.cocoon_schema_v2 import Cocoon, build_cocoon, VALID_VALENCES, VALID_PROBLEM_TYPES

SCHEMA_VERSION = "3.0"

VALID_EXECUTION_PATHS = frozenset([
    "forge_full",          # Full ForgeEngine: all perspectives + all metrics
    "adapter_lightweight", # Single-adapter reduced path
    "fallback_template",   # Template/simulation only (no model inference)
    "recovery_mode",       # Partial run due to subsystem failure
    "unknown",             # Path not recorded (legacy / pre-v3)
])

VALID_INTEGRITY_STATUSES = frozenset(["complete", "partial", "failed"])
VALID_ECHO_RISK = frozenset(["unknown", "low", "medium", "high"])
VALID_METRICS_STATUS = frozenset(["complete", "partial", "failed"])


@dataclass
class CocoonV3(Cocoon):
    """Extended cocoon with runtime provenance, integrity, and full telemetry.

    Inherits all v2.Cocoon fields.  New field groups:
      - Runtime provenance
      - Integrity
      - Echo / collapse detection
      - Full epistemic telemetry
      - AEGIS detail
      - Guardian + Nexus
      - Synthesis structure
    """

    # ─── Runtime provenance ──────────────────────────────────────────────────
    serialization_version: str = SCHEMA_VERSION
    execution_path: str = "unknown"
    model_inference_invoked: bool = False
    orchestrator_trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    runtime_version: str = ""
    metrics_population_status: str = "partial"   # 'complete'|'partial'|'failed'
    reason_for_fallback: Optional[str] = None

    # ─── Integrity ───────────────────────────────────────────────────────────
    cocoon_integrity: str = "partial"            # 'complete'|'partial'|'failed'
    cocoon_integrity_score: float = 0.0          # 0.0 – 1.0

    # ─── Echo / perspective-collapse detection ───────────────────────────────
    echo_risk: str = "unknown"                   # 'unknown'|'low'|'medium'|'high'
    perspective_collapse_detected: bool = False  # True if all outputs near-identical

    # ─── Epistemic telemetry (live computed from real outputs) ───────────────
    pairwise_tensions: dict = field(default_factory=dict)
    # e.g. {"newton_vs_empathy": 0.41, "philosophy_vs_systems": 0.28}
    perspective_coverage: dict = field(default_factory=dict)
    # e.g. {"newton": 0.85, "empathy": 0.72, "philosophy": 0.60}
    psi_r: float = 0.0

    # ─── AEGIS detail ────────────────────────────────────────────────────────
    aegis_framework_scores: dict = field(default_factory=dict)
    # e.g. {"utilitarian": 0.82, "deontological": 0.91, "virtue": 0.84, ...}
    aegis_dominant_framework: str = ""
    aegis_ethical_conflict_notes: list = field(default_factory=list)
    aegis_output_changed: bool = False

    # ─── Guardian ────────────────────────────────────────────────────────────
    guardian_safety_status: str = ""     # 'pass'|'flag'|'block'|''
    guardian_trust_calibration: str = "" # 'low'|'medium'|'high'|''

    # ─── Nexus ───────────────────────────────────────────────────────────────
    nexus_risk_level: str = ""           # 'low'|'medium'|'high'|''
    nexus_confidence: float = 0.0

    # ─── Synthesis structure ─────────────────────────────────────────────────
    synthesis_convergences: list = field(default_factory=list)
    synthesis_divergences: list = field(default_factory=list)
    synthesis_tradeoffs: list = field(default_factory=list)
    synthesis_recommended_position: str = ""
    synthesis_uncertainty_notes: list = field(default_factory=list)

    # ─── User-facing ─────────────────────────────────────────────────────────
    user_response_text: str = ""

    def validate(self) -> list[str]:
        """Extend v2 validation with v3-specific field checks."""
        errors = super().validate()

        if self.execution_path not in VALID_EXECUTION_PATHS:
            errors.append(
                f"Invalid execution_path: {self.execution_path!r}. "
                f"Must be one of {sorted(VALID_EXECUTION_PATHS)}"
            )
        if self.cocoon_integrity not in VALID_INTEGRITY_STATUSES:
            errors.append(f"Invalid cocoon_integrity: {self.cocoon_integrity!r}")
        if self.echo_risk not in VALID_ECHO_RISK:
            errors.append(f"Invalid echo_risk: {self.echo_risk!r}")
        if self.metrics_population_status not in VALID_METRICS_STATUS:
            errors.append(f"Invalid metrics_population_status: {self.metrics_population_status!r}")
        if not 0.0 <= self.cocoon_integrity_score <= 1.0:
            errors.append(f"cocoon_integrity_score {self.cocoon_integrity_score} out of range [0, 1]")
        if not 0.0 <= self.psi_r <= 1.0:
            errors.append(f"psi_r {self.psi_r} out of range [0, 1]")

        # Enforce required fields based on execution path
        if self.execution_path == "forge_full":
            if not self.model_inference_invoked:
                errors.append("forge_full path must have model_inference_invoked=True")
            if not self.active_perspectives:
                errors.append("forge_full path must have active_perspectives populated")
            if self.eta_score is None:
                errors.append("forge_full path must have eta_score populated (AEGIS required)")

        return errors

    def to_dict(self) -> dict:
        """Full serialization including all v3 fields."""
        base = {
            # ── Identity ──
            "cocoon_id":                    self.cocoon_id,
            "timestamp":                    self.timestamp,
            "session_id":                   self.session_id,
            "serialization_version":        self.serialization_version,
            # ── Content ──
            "query":                        self.query[:500],
            "response_summary":             self.response_summary[:500],
            "full_response_hash":           self.full_response_hash,
            "user_response_text":           self.user_response_text[:2000],
            # ── Emotional / importance ──
            "emotional_valence":            self.emotional_valence,
            "importance_score":             self.importance_score,
            "confidence":                   self.confidence,
            # ── Cognitive state ──
            "epsilon_value":                self.epsilon_value,
            "gamma_coherence":              self.gamma_coherence,
            "eta_score":                    self.eta_score,
            "psi_r":                        self.psi_r,
            "active_perspectives":          self.active_perspectives,
            "dominant_perspective":         self.dominant_perspective,
            "unresolved_tensions":          self.unresolved_tensions,
            "synthesis_quality":            self.synthesis_quality,
            # ── Retrieval ──
            "problem_type":                 self.problem_type,
            "topic_tags":                   self.topic_tags,
            "project_context":              self.project_context,
            "user_preferences_inferred":    self.user_preferences_inferred,
            # ── Continuity ──
            "open_threads":                 self.open_threads,
            "contradicts_cocoon_ids":       self.contradicts_cocoon_ids,
            "references_cocoon_ids":        self.references_cocoon_ids,
            # ── Quality flags ──
            "is_hallucination_flagged":     self.is_hallucination_flagged,
            "is_sycophancy_flagged":        self.is_sycophancy_flagged,
            "is_verified":                  self.is_verified,
            # ── Runtime provenance (v3) ──
            "execution_path":               self.execution_path,
            "model_inference_invoked":      self.model_inference_invoked,
            "orchestrator_trace_id":        self.orchestrator_trace_id,
            "runtime_version":              self.runtime_version,
            "metrics_population_status":    self.metrics_population_status,
            "reason_for_fallback":          self.reason_for_fallback,
            # ── Integrity (v3) ──
            "cocoon_integrity":             self.cocoon_integrity,
            "cocoon_integrity_score":       round(self.cocoon_integrity_score, 4),
            # ── Echo / collapse (v3) ──
            "echo_risk":                    self.echo_risk,
            "perspective_collapse_detected": self.perspective_collapse_detected,
            # ── Epistemic telemetry (v3) ──
            "pairwise_tensions":            self.pairwise_tensions,
            "perspective_coverage":         self.perspective_coverage,
            # ── AEGIS detail (v3) ──
            "aegis_framework_scores":       self.aegis_framework_scores,
            "aegis_dominant_framework":     self.aegis_dominant_framework,
            "aegis_ethical_conflict_notes": self.aegis_ethical_conflict_notes,
            "aegis_output_changed":         self.aegis_output_changed,
            # ── Guardian (v3) ──
            "guardian_safety_status":       self.guardian_safety_status,
            "guardian_trust_calibration":   self.guardian_trust_calibration,
            # ── Nexus (v3) ──
            "nexus_risk_level":             self.nexus_risk_level,
            "nexus_confidence":             self.nexus_confidence,
            # ── Synthesis structure (v3) ──
            "synthesis_convergences":       self.synthesis_convergences,
            "synthesis_divergences":        self.synthesis_divergences,
            "synthesis_tradeoffs":          self.synthesis_tradeoffs,
            "synthesis_recommended_position": self.synthesis_recommended_position,
            "synthesis_uncertainty_notes":  self.synthesis_uncertainty_notes,
        }
        return base


def build_cocoon_v3(
    query: str,
    response_text: str,
    response_summary: str,
    # ── v2 fields (all optional) ──
    emotional_valence: str = "curiosity",
    importance_score: float = 5.0,
    epsilon_value: float = 0.35,
    gamma_coherence: float = 0.72,
    eta_score: Optional[float] = None,
    active_perspectives: Optional[list] = None,
    dominant_perspective: Optional[str] = None,
    unresolved_tensions: Optional[list] = None,
    synthesis_quality: str = "adequate",
    problem_type: str = "unknown",
    topic_tags: Optional[list] = None,
    project_context: Optional[str] = None,
    user_preferences_inferred: Optional[dict] = None,
    open_threads: Optional[list] = None,
    contradicts_cocoon_ids: Optional[list] = None,
    references_cocoon_ids: Optional[list] = None,
    confidence: float = 0.75,
    session_id: Optional[str] = None,
    # ── v3-only fields ──
    execution_path: str = "unknown",
    model_inference_invoked: bool = False,
    orchestrator_trace_id: Optional[str] = None,
    runtime_version: str = "",
    metrics_population_status: str = "partial",
    reason_for_fallback: Optional[str] = None,
    psi_r: float = 0.0,
    pairwise_tensions: Optional[dict] = None,
    perspective_coverage: Optional[dict] = None,
    aegis_framework_scores: Optional[dict] = None,
    aegis_dominant_framework: str = "",
    aegis_ethical_conflict_notes: Optional[list] = None,
    aegis_output_changed: bool = False,
    guardian_safety_status: str = "",
    guardian_trust_calibration: str = "",
    nexus_risk_level: str = "",
    nexus_confidence: float = 0.0,
    synthesis_convergences: Optional[list] = None,
    synthesis_divergences: Optional[list] = None,
    synthesis_tradeoffs: Optional[list] = None,
    synthesis_recommended_position: str = "",
    synthesis_uncertainty_notes: Optional[list] = None,
    user_response_text: str = "",
    is_hallucination_flagged: bool = False,
    is_sycophancy_flagged: bool = False,
    echo_risk: str = "unknown",
    perspective_collapse_detected: bool = False,
) -> CocoonV3:
    """Build and validate a CocoonV3.  Raises ValueError on validation failure."""
    import hashlib
    ts = time.time()
    cocoon_id = hashlib.sha256(f"{query}{ts}".encode()).hexdigest()
    full_hash = hashlib.sha256(response_text.encode()).hexdigest()

    if topic_tags is None:
        import re
        words = re.findall(r'\b[a-zA-Z][a-zA-Z]{3,}\b', query.lower())
        stop = {"this", "that", "with", "from", "have", "what", "when", "where",
                "which", "will", "been", "should", "could", "would"}
        topic_tags = [w for w in dict.fromkeys(words) if w not in stop][:8]

    # Clamp valence to valid set
    if emotional_valence not in VALID_VALENCES:
        emotional_valence = "insight"

    cocoon = CocoonV3(
        # v2 fields
        cocoon_id=cocoon_id,
        timestamp=ts,
        session_id=session_id,
        query=query,
        response_summary=response_summary,
        full_response_hash=full_hash,
        emotional_valence=emotional_valence,
        importance_score=float(importance_score),
        confidence=confidence,
        epsilon_value=float(epsilon_value),
        gamma_coherence=float(gamma_coherence),
        eta_score=eta_score,
        active_perspectives=active_perspectives or [],
        dominant_perspective=dominant_perspective,
        unresolved_tensions=unresolved_tensions or [],
        synthesis_quality=synthesis_quality,
        problem_type=problem_type,
        topic_tags=topic_tags,
        project_context=project_context,
        user_preferences_inferred=user_preferences_inferred or {},
        open_threads=open_threads or [],
        contradicts_cocoon_ids=contradicts_cocoon_ids or [],
        references_cocoon_ids=references_cocoon_ids or [],
        is_hallucination_flagged=is_hallucination_flagged,
        is_sycophancy_flagged=is_sycophancy_flagged,
        # v3 fields
        execution_path=execution_path,
        model_inference_invoked=model_inference_invoked,
        orchestrator_trace_id=orchestrator_trace_id or str(uuid.uuid4()),
        runtime_version=runtime_version,
        metrics_population_status=metrics_population_status,
        reason_for_fallback=reason_for_fallback,
        psi_r=max(0.0, min(1.0, float(psi_r))),
        pairwise_tensions=pairwise_tensions or {},
        perspective_coverage=perspective_coverage or {},
        aegis_framework_scores=aegis_framework_scores or {},
        aegis_dominant_framework=aegis_dominant_framework,
        aegis_ethical_conflict_notes=aegis_ethical_conflict_notes or [],
        aegis_output_changed=aegis_output_changed,
        guardian_safety_status=guardian_safety_status,
        guardian_trust_calibration=guardian_trust_calibration,
        nexus_risk_level=nexus_risk_level,
        nexus_confidence=float(nexus_confidence),
        synthesis_convergences=synthesis_convergences or [],
        synthesis_divergences=synthesis_divergences or [],
        synthesis_tradeoffs=synthesis_tradeoffs or [],
        synthesis_recommended_position=synthesis_recommended_position,
        synthesis_uncertainty_notes=synthesis_uncertainty_notes or [],
        user_response_text=user_response_text,
        echo_risk=echo_risk,
        perspective_collapse_detected=perspective_collapse_detected,
    )

    errors = cocoon.validate()
    if errors:
        raise ValueError(f"CocoonV3 validation failed: {errors}")

    return cocoon
