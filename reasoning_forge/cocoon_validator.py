"""
Cocoon Validator — Integrity scoring, required-field enforcement, quarantine.

Every cocoon write must pass through CocoonValidator before hitting disk.
If required fields are missing the cocoon is downgraded to 'partial' or
moved to quarantine rather than silently stored as complete.

Integrity score factors (each 0-1, weighted):
  1. Required field completion          (weight 0.35)
  2. Execution path quality             (weight 0.20)
  3. Perspective diversity              (weight 0.15)
  4. Metrics population                 (weight 0.20)
  5. No echo / collapse detected        (weight 0.10)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── Weight map for integrity scoring ────────────────────────────────────────

_WEIGHTS = {
    "required_fields":      0.35,
    "execution_path":       0.20,
    "perspectives":         0.15,
    "metrics":              0.20,
    "echo_collapse":        0.10,
}

# Execution-path quality scores
_PATH_QUALITY = {
    "forge_full":          1.0,
    "adapter_lightweight": 0.6,
    "recovery_mode":       0.3,
    "fallback_template":   0.0,
    "unknown":             0.0,
}

# Required fields for each execution path
_REQUIRED_FIELDS = {
    "forge_full": [
        "execution_path", "model_inference_invoked", "orchestrator_trace_id",
        "eta_score", "epsilon_value", "gamma_coherence",
        "active_perspectives", "emotional_valence", "importance_score",
        "aegis_framework_scores", "pairwise_tensions",
    ],
    "adapter_lightweight": [
        "execution_path", "orchestrator_trace_id",
        "eta_score", "emotional_valence", "importance_score",
        "reason_for_fallback",
    ],
    "recovery_mode": [
        "execution_path", "reason_for_fallback",
        "emotional_valence", "importance_score",
    ],
    "fallback_template": [
        "execution_path", "reason_for_fallback",
    ],
    "unknown": ["execution_path"],
}


@dataclass
class ValidationResult:
    """Result of a CocoonValidator.validate() call."""
    integrity_score: float          # 0.0 – 1.0
    integrity_status: str           # 'complete' | 'partial' | 'failed'
    missing_fields: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    field_scores: dict = field(default_factory=dict)
    should_quarantine: bool = False
    quarantine_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "integrity_score":   round(self.integrity_score, 4),
            "integrity_status":  self.integrity_status,
            "missing_fields":    self.missing_fields,
            "warnings":          self.warnings,
            "errors":            self.errors,
            "field_scores":      {k: round(v, 3) for k, v in self.field_scores.items()},
            "should_quarantine": self.should_quarantine,
            "quarantine_reason": self.quarantine_reason,
        }


class CocoonValidator:
    """Validates CocoonV3 instances before disk persistence.

    Usage:
        validator = CocoonValidator()
        result = validator.validate(cocoon)
        if result.should_quarantine:
            validator.quarantine(cocoon, result)
        else:
            validator.write(cocoon, store_path)
    """

    def __init__(
        self,
        store_path: str = "cocoons",
        quarantine_path: str = "cocoons/quarantine",
        integrity_threshold: float = 0.4,
    ):
        self.store_path = Path(store_path)
        self.quarantine_path = Path(quarantine_path)
        self.integrity_threshold = integrity_threshold
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.quarantine_path.mkdir(parents=True, exist_ok=True)

    def validate(self, cocoon) -> ValidationResult:
        """Score a CocoonV3 for integrity.  Returns ValidationResult."""
        missing = []
        warnings = []
        errors = []

        # ── 1. Required field completion ─────────────────────────────────────
        path = getattr(cocoon, "execution_path", "unknown")
        required = _REQUIRED_FIELDS.get(path, _REQUIRED_FIELDS["unknown"])

        cocoon_dict = cocoon.to_dict() if hasattr(cocoon, "to_dict") else vars(cocoon)

        for fname in required:
            val = cocoon_dict.get(fname)
            if val is None or val == "" or val == [] or val == {}:
                missing.append(fname)

        n_required = len(required)
        n_present = n_required - len(missing)
        field_completion = n_present / n_required if n_required > 0 else 1.0

        # ── 2. Execution path quality ─────────────────────────────────────────
        path_score = _PATH_QUALITY.get(path, 0.0)

        if path == "fallback_template":
            warnings.append(
                "Execution path is fallback_template — no real inference occurred. "
                "cocoon_integrity will be capped at 'partial'."
            )
        if path == "unknown":
            warnings.append("execution_path is 'unknown' — legacy cocoon or missing provenance.")

        # ── 3. Perspective diversity ──────────────────────────────────────────
        perspectives = cocoon_dict.get("active_perspectives") or []
        n_perspectives = len(perspectives)
        perspective_score = min(1.0, n_perspectives / 3.0)  # 3+ perspectives = full score

        if n_perspectives == 0 and path == "forge_full":
            errors.append("forge_full path must have at least 1 active_perspective")

        # ── 4. Metrics population ─────────────────────────────────────────────
        metric_fields = [
            ("eta_score",       cocoon_dict.get("eta_score")),
            ("epsilon_value",   cocoon_dict.get("epsilon_value")),
            ("gamma_coherence", cocoon_dict.get("gamma_coherence")),
            ("psi_r",           cocoon_dict.get("psi_r")),
            ("pairwise_tensions", cocoon_dict.get("pairwise_tensions")),
        ]
        metrics_present = sum(
            1 for _, v in metric_fields
            if v is not None and v != {} and v != 0.0
        )
        metrics_score = metrics_present / len(metric_fields)

        if metrics_present < 3 and path == "forge_full":
            warnings.append(
                f"forge_full path has only {metrics_present}/5 metric fields populated. "
                "Check epistemic metrics wiring."
            )

        # ── 5. Echo / collapse ────────────────────────────────────────────────
        echo_risk = cocoon_dict.get("echo_risk", "unknown")
        collapse = cocoon_dict.get("perspective_collapse_detected", False)
        echo_score = 1.0
        if echo_risk == "high":
            echo_score = 0.0
            errors.append("echo_risk=high: perspective outputs are near-identical to input prompt.")
        elif echo_risk == "medium":
            echo_score = 0.5
            warnings.append("echo_risk=medium: some perspective outputs may be echoing the prompt.")
        elif echo_risk == "unknown":
            echo_score = 0.7
        if collapse:
            echo_score *= 0.3
            errors.append("perspective_collapse_detected: all perspectives produced nearly identical outputs.")

        # ── Composite integrity score ─────────────────────────────────────────
        field_scores = {
            "required_fields":  field_completion,
            "execution_path":   path_score,
            "perspectives":     perspective_score,
            "metrics":          metrics_score,
            "echo_collapse":    echo_score,
        }
        integrity_score = sum(
            field_scores[k] * _WEIGHTS[k]
            for k in _WEIGHTS
        )

        # ── Status and quarantine decision ────────────────────────────────────
        if integrity_score >= 0.80 and not errors:
            status = "complete"
        elif integrity_score >= self.integrity_threshold and not any(
            "echo_risk=high" in e or "perspective_collapse" in e for e in errors
        ):
            status = "partial"
        else:
            status = "failed"

        # Force partial for fallback_template regardless of score
        if path == "fallback_template":
            status = "partial"
            integrity_score = min(integrity_score, 0.4)

        should_quarantine = (
            status == "failed"
            or echo_risk == "high"
            or collapse
            or len(errors) >= 3
        )
        quarantine_reason = (
            "; ".join(errors[:3]) if should_quarantine else ""
        )

        return ValidationResult(
            integrity_score=integrity_score,
            integrity_status=status,
            missing_fields=missing,
            warnings=warnings,
            errors=errors,
            field_scores=field_scores,
            should_quarantine=should_quarantine,
            quarantine_reason=quarantine_reason,
        )

    def apply_result(self, cocoon, result: ValidationResult):
        """Mutate cocoon's integrity fields with validator findings."""
        cocoon.cocoon_integrity = result.integrity_status
        cocoon.cocoon_integrity_score = result.integrity_score
        cocoon.metrics_population_status = (
            "complete" if result.field_scores.get("metrics", 0) >= 0.8 else
            "partial" if result.field_scores.get("metrics", 0) >= 0.4 else
            "failed"
        )
        return cocoon

    def write(self, cocoon, filename_prefix: str = "cocoon_v3") -> Path:
        """Write validated cocoon to store_path.  Returns written path."""
        result = self.validate(cocoon)
        self.apply_result(cocoon, result)

        ts = int(cocoon.timestamp)
        rand = int(cocoon.cocoon_id[-4:], 16) % 10000
        fname = f"{filename_prefix}_{ts}_{rand}.json"

        if result.should_quarantine:
            dest = self.quarantine_path / fname
            logger.warning(
                f"[CocoonValidator] Quarantining {fname}: {result.quarantine_reason}"
            )
        else:
            dest = self.store_path / fname

        payload = cocoon.to_dict()
        payload["_validation"] = result.to_dict()

        with open(dest, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)

        if not result.should_quarantine:
            logger.debug(
                f"[CocoonValidator] Wrote {fname} "
                f"integrity={result.integrity_score:.2f} ({result.integrity_status})"
            )
        return dest

    def audit_store(self, limit: int = 100) -> dict:
        """Scan cocoon store and return aggregate integrity stats."""
        files = sorted(
            self.store_path.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )[:limit]

        stats = {
            "total": 0,
            "complete": 0,
            "partial": 0,
            "failed": 0,
            "quarantined": len(list(self.quarantine_path.glob("*.json"))),
            "avg_integrity_score": 0.0,
            "avg_eta": 0.0,
            "avg_epsilon": 0.0,
            "avg_gamma": 0.0,
            "execution_paths": {},
            "echo_risk_distribution": {"low": 0, "medium": 0, "high": 0, "unknown": 0},
            "missing_field_frequency": {},
        }

        scores = []
        etas = []
        epsilons = []
        gammas = []

        for fpath in files:
            try:
                with open(fpath, encoding="utf-8") as fh:
                    data = json.load(fh)
            except Exception:
                continue

            stats["total"] += 1
            integrity = data.get("cocoon_integrity", "unknown")
            if integrity in ("complete", "partial", "failed"):
                stats[integrity] += 1

            score = data.get("cocoon_integrity_score")
            if isinstance(score, (int, float)):
                scores.append(score)

            eta = data.get("eta_score")
            if isinstance(eta, (int, float)):
                etas.append(eta)

            eps = data.get("epsilon_value")
            if isinstance(eps, (int, float)):
                epsilons.append(eps)

            gam = data.get("gamma_coherence")
            if isinstance(gam, (int, float)):
                gammas.append(gam)

            ep = data.get("execution_path", "unknown")
            stats["execution_paths"][ep] = stats["execution_paths"].get(ep, 0) + 1

            er = data.get("echo_risk", "unknown")
            if er in stats["echo_risk_distribution"]:
                stats["echo_risk_distribution"][er] += 1

            validation = data.get("_validation", {})
            for mf in validation.get("missing_fields", []):
                stats["missing_field_frequency"][mf] = (
                    stats["missing_field_frequency"].get(mf, 0) + 1
                )

        if scores:
            stats["avg_integrity_score"] = round(sum(scores) / len(scores), 4)
        if etas:
            stats["avg_eta"] = round(sum(etas) / len(etas), 4)
        if epsilons:
            stats["avg_epsilon"] = round(sum(epsilons) / len(epsilons), 4)
        if gammas:
            stats["avg_gamma"] = round(sum(gammas) / len(gammas), 4)

        # Sort missing fields by frequency
        stats["missing_field_frequency"] = dict(
            sorted(stats["missing_field_frequency"].items(), key=lambda x: -x[1])
        )

        return stats
