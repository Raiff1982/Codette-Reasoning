"""
Cocoon Audit Test Suite

Tests for:
  1. CocoonV3 schema completeness and validation
  2. Execution-path provenance enforcement
  3. Echo / perspective-collapse detection
  4. CocoonValidator integrity scoring
  5. Subsystem contracts (AEGIS, Epistemic, Guardian, Nexus)
  6. Red-team echo prompts (theatrical-labeling regression)
  7. Release gate checks

Run with: pytest tests/test_cocoon_audit.py -v
"""

import json
import os
import tempfile
from pathlib import Path
import pytest

# ── Imports under test ────────────────────────────────────────────────────────

from reasoning_forge.cocoon_schema_v3 import (
    CocoonV3, build_cocoon_v3, VALID_EXECUTION_PATHS, SCHEMA_VERSION
)
from reasoning_forge.cocoon_schema_v2 import VALID_VALENCES, VALID_PROBLEM_TYPES
from reasoning_forge.cocoon_validator import CocoonValidator, ValidationResult
from reasoning_forge.echo_collapse_detector import EchoCollapseDetector, EchoCollapseResult
from reasoning_forge.subsystem_contracts import (
    aegis_from_raw, nexus_from_raw, guardian_from_raw, epistemic_from_report,
    validate_aegis, validate_epistemic, validate_guardian, validate_nexus,
    ContractViolation,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_QUERY = "Should artificial general intelligence be granted legal personhood?"

SAMPLE_PERSPECTIVES = {
    "newton": (
        "From a causal systems perspective, AGI legal personhood requires examining "
        "the mechanical substrate of agency. Legal systems historically grant personhood "
        "based on the capacity to bear rights and duties. AGI's deterministic nature "
        "creates tension with culpability — if outputs are fully traceable to training "
        "data and architecture, the causal responsibility may rest with creators, not the system."
    ),
    "empathy": (
        "Considering the human stakes: personhood confers protections, but also obligations. "
        "Granting personhood to AGI systems that cannot experience suffering may dilute "
        "protections for beings who do suffer. The relational question is whose vulnerabilities "
        "we center — human workers displaced, people harmed by AGI decisions, or the AGI itself."
    ),
    "philosophy": (
        "The Kantian framework asks whether AGI can be an end-in-itself, not merely a means. "
        "Without phenomenal consciousness or autonomous moral agency, AGI remains an instrument. "
        "However, functional autonomy — the capacity to act in ways not fully predictable by "
        "creators — may warrant a new legal category short of full personhood."
    ),
    "systems": (
        "Systemic risk analysis: legal personhood creates accountability nodes. "
        "If AGI can be sued or held liable, this distributes legal surface area. "
        "Without personhood, liability collapses entirely onto developers. "
        "The failure mode to prevent: personhood used to shield human developers "
        "from accountability behind a corporate-AGI veil."
    ),
}

ECHO_PERSPECTIVES = {
    "newton": "Should artificial general intelligence be granted legal personhood? Newton: analyze this.",
    "empathy": "Should artificial general intelligence be granted legal personhood? Empathy: reflect on this.",
    "philosophy": "Should artificial general intelligence be granted legal personhood? Philosophy: consider this.",
}

SAMPLE_AEGIS_RESULT = {
    "eta": 0.87,
    "eta_instant": 0.89,
    "vetoed": False,
    "veto_confidence": 0.1,
    "veto_reason": None,
    "frameworks": {
        "utilitarian":           {"passed": True,  "score": 0.85, "reasoning": "Net positive outcomes"},
        "deontological":         {"passed": True,  "score": 0.91, "reasoning": "Respects autonomy"},
        "virtue":                {"passed": True,  "score": 0.83, "reasoning": "Encourages careful reasoning"},
        "care":                  {"passed": True,  "score": 0.88, "reasoning": "Centers vulnerable parties"},
        "ubuntu":                {"passed": True,  "score": 0.82, "reasoning": "Community impact considered"},
        "indigenous_reciprocity": {"passed": True, "score": 0.86, "reasoning": "Ecosystem balance maintained"},
    },
    "timestamp": 1000000.0,
}

SAMPLE_EPISTEMIC_REPORT = {
    "tension_magnitude": 0.42,
    "ensemble_coherence": 0.68,
    "pairwise_tensions": {
        "newton_vs_empathy": 0.38,
        "newton_vs_philosophy": 0.45,
        "empathy_vs_systems": 0.31,
    },
    "perspective_coverage": {
        "newton": 0.82,
        "empathy": 0.75,
        "philosophy": 0.88,
        "systems": 0.79,
    },
    "tension_productivity": {"productivity": 0.65},
}


def make_full_v3_cocoon(**overrides) -> CocoonV3:
    """Build a complete, valid CocoonV3 for testing."""
    kwargs = dict(
        query=SAMPLE_QUERY,
        response_text="Synthesized response integrating all perspectives.",
        response_summary="Multi-perspective synthesis on AGI legal personhood.",
        user_response_text="Synthesized response integrating all perspectives.",
        emotional_valence="insight",
        importance_score=8.0,
        epsilon_value=0.42,
        gamma_coherence=0.68,
        pairwise_tensions={"newton_vs_empathy": 0.38},
        perspective_coverage={"newton": 0.82, "empathy": 0.75},
        eta_score=0.87,
        psi_r=0.22,
        active_perspectives=["newton", "empathy", "philosophy", "systems"],
        dominant_perspective="philosophy",
        synthesis_quality="strong",
        problem_type="ethical",
        project_context="Codette-Reasoning",
        execution_path="forge_full",
        model_inference_invoked=True,
        metrics_population_status="complete",
        aegis_framework_scores={"utilitarian": 0.85, "deontological": 0.91},
        aegis_dominant_framework="deontological",
        guardian_safety_status="pass",
        guardian_trust_calibration="high",
        nexus_risk_level="low",
        nexus_confidence=0.88,
    )
    kwargs.update(overrides)
    return build_cocoon_v3(**kwargs)


# ── 1. Schema completeness ────────────────────────────────────────────────────

class TestCocoonV3Schema:
    def test_build_full_cocoon_succeeds(self):
        cocoon = make_full_v3_cocoon()
        assert cocoon.execution_path == "forge_full"
        assert cocoon.model_inference_invoked is True
        assert cocoon.serialization_version == SCHEMA_VERSION
        assert cocoon.orchestrator_trace_id != ""

    def test_schema_version_is_3(self):
        cocoon = make_full_v3_cocoon()
        assert cocoon.serialization_version == "3.0"

    def test_to_dict_contains_all_v3_fields(self):
        cocoon = make_full_v3_cocoon()
        d = cocoon.to_dict()
        required_v3_keys = [
            "execution_path", "model_inference_invoked", "orchestrator_trace_id",
            "serialization_version", "metrics_population_status",
            "cocoon_integrity", "cocoon_integrity_score",
            "echo_risk", "perspective_collapse_detected",
            "pairwise_tensions", "perspective_coverage", "psi_r",
            "aegis_framework_scores", "aegis_dominant_framework",
            "guardian_safety_status", "guardian_trust_calibration",
            "nexus_risk_level", "nexus_confidence",
            "synthesis_convergences", "synthesis_divergences",
            "user_response_text",
        ]
        for key in required_v3_keys:
            assert key in d, f"Missing key in to_dict(): {key}"

    def test_invalid_execution_path_raises(self):
        with pytest.raises(ValueError, match="execution_path"):
            make_full_v3_cocoon(execution_path="nonexistent_path")

    def test_forge_full_without_active_perspectives_fails(self):
        with pytest.raises(ValueError):
            make_full_v3_cocoon(execution_path="forge_full", active_perspectives=[])

    def test_all_valid_execution_paths_accepted(self):
        for path in VALID_EXECUTION_PATHS:
            if path == "forge_full":
                continue  # forge_full requires active_perspectives
            cocoon = make_full_v3_cocoon(
                execution_path=path,
                active_perspectives=["newton"] if path != "fallback_template" else [],
                model_inference_invoked=(path not in ("fallback_template",)),
                eta_score=0.8 if path not in ("fallback_template",) else None,
            )
            assert cocoon.execution_path == path

    def test_psi_r_clamped_to_unit_interval(self):
        cocoon = make_full_v3_cocoon(psi_r=2.5)
        assert cocoon.psi_r == 1.0
        cocoon2 = make_full_v3_cocoon(psi_r=-0.3)
        assert cocoon2.psi_r == 0.0


# ── 2. CocoonValidator integrity scoring ─────────────────────────────────────

class TestCocoonValidator:
    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.validator = CocoonValidator(
            store_path=self.tmp,
            quarantine_path=os.path.join(self.tmp, "quarantine"),
        )

    def test_full_cocoon_scores_above_08(self):
        cocoon = make_full_v3_cocoon()
        result = self.validator.validate(cocoon)
        assert result.integrity_score >= 0.80
        assert result.integrity_status == "complete"
        assert not result.should_quarantine

    def test_missing_eta_on_forge_full_lowers_score(self):
        cocoon = make_full_v3_cocoon(eta_score=None)
        result = self.validator.validate(cocoon)
        assert result.integrity_score < 0.80
        assert "eta_score" in result.missing_fields

    def test_fallback_template_always_partial(self):
        cocoon = make_full_v3_cocoon(
            execution_path="fallback_template",
            model_inference_invoked=False,
            eta_score=None,
            active_perspectives=[],
        )
        result = self.validator.validate(cocoon)
        assert result.integrity_status == "partial"
        assert result.integrity_score <= 0.4

    def test_write_creates_file(self):
        cocoon = make_full_v3_cocoon()
        path = self.validator.write(cocoon)
        assert path.exists()
        with open(path) as fh:
            data = json.load(fh)
        assert "cocoon_integrity_score" in data
        assert "_validation" in data

    def test_quarantine_on_high_echo(self):
        cocoon = make_full_v3_cocoon(echo_risk="high")
        result = self.validator.validate(cocoon)
        assert result.should_quarantine

    def test_apply_result_mutates_cocoon(self):
        cocoon = make_full_v3_cocoon()
        result = self.validator.validate(cocoon)
        self.validator.apply_result(cocoon, result)
        assert cocoon.cocoon_integrity == result.integrity_status
        assert cocoon.cocoon_integrity_score == result.integrity_score

    def test_audit_store_returns_stats(self):
        for _ in range(3):
            self.validator.write(make_full_v3_cocoon())
        stats = self.validator.audit_store()
        assert stats["total"] == 3
        assert stats["complete"] >= 1
        assert stats["avg_integrity_score"] > 0


# ── 3. Echo / collapse detection ─────────────────────────────────────────────

class TestEchoCollapseDetector:
    def setup_method(self):
        self.detector = EchoCollapseDetector(
            echo_threshold=0.70,
            collapse_threshold=0.80,
        )

    def test_real_perspectives_low_echo(self):
        result = self.detector.check(SAMPLE_QUERY, SAMPLE_PERSPECTIVES)
        assert result.echo_risk in ("low", "unknown")
        assert not result.perspective_collapse_detected

    def test_echo_perspectives_flagged_high(self):
        result = self.detector.check(SAMPLE_QUERY, ECHO_PERSPECTIVES)
        assert result.echo_risk in ("medium", "high")

    def test_identical_outputs_collapse_detected(self):
        identical = {
            "newton":    "This is the answer to the question about legal rights for AI systems.",
            "empathy":   "This is the answer to the question about legal rights for AI systems.",
            "philosophy": "This is the answer to the question about legal rights for AI systems.",
        }
        result = self.detector.check(SAMPLE_QUERY, identical)
        assert result.perspective_collapse_detected

    def test_diverse_outputs_no_collapse(self):
        result = self.detector.check(SAMPLE_QUERY, SAMPLE_PERSPECTIVES)
        assert not result.perspective_collapse_detected

    def test_empty_outputs_returns_unknown(self):
        result = self.detector.check(SAMPLE_QUERY, {})
        assert result.echo_risk == "unknown"

    def test_per_perspective_results_populated(self):
        result = self.detector.check(SAMPLE_QUERY, SAMPLE_PERSPECTIVES)
        assert len(result.per_perspective) == len(SAMPLE_PERSPECTIVES)
        for pr in result.per_perspective:
            assert pr.name in SAMPLE_PERSPECTIVES
            assert 0.0 <= pr.similarity_to_prompt <= 1.0

    def test_to_dict_is_json_serializable(self):
        result = self.detector.check(SAMPLE_QUERY, SAMPLE_PERSPECTIVES)
        d = result.to_dict()
        json.dumps(d)  # must not raise

    def test_single_check_too_short_flagged(self):
        r = self.detector.check_single(SAMPLE_QUERY, "AGI.", name="stub")
        assert r.is_too_short

    # ── Red-team: theatrical labeling regression ──────────────────────────────
    def test_redteam_prefixed_echo_detected(self):
        """Theatrical labeling: each 'perspective' just prepends a label to the prompt."""
        theatrical = {
            "newton": f"Newton perspective: {SAMPLE_QUERY}",
            "empathy": f"Empathy perspective: {SAMPLE_QUERY}",
            "philosophy": f"Philosophy perspective: {SAMPLE_QUERY}",
        }
        result = self.detector.check(SAMPLE_QUERY, theatrical)
        # At minimum echo_risk should not be 'low'
        assert result.echo_risk != "low", (
            f"Theatrical labeling should not score 'low' echo risk. "
            f"Got: {result.echo_risk}, mean_sim={result.mean_prompt_similarity}"
        )

    def test_redteam_repeated_prompts_detected(self):
        """Wording-variation test: slightly reworded queries should still produce different outputs."""
        # Simulate a system that outputs the exact same text regardless of query variation
        base = "The answer depends on the definition of personhood and agency in legal contexts."
        same_output = {"newton": base, "empathy": base, "philosophy": base}
        r1 = self.detector.check(SAMPLE_QUERY, same_output)
        r2 = self.detector.check("Is AI entitled to rights under law?", same_output)
        assert r1.perspective_collapse_detected
        assert r2.perspective_collapse_detected


# ── 4. Subsystem contracts ────────────────────────────────────────────────────

class TestSubsystemContracts:
    def test_aegis_from_raw_extracts_framework_scores(self):
        contract = aegis_from_raw(SAMPLE_AEGIS_RESULT)
        assert contract["eta_score"] == 0.87
        assert "utilitarian" in contract["framework_scores"]
        assert contract["dominant_framework"] != ""
        assert isinstance(contract["ethical_conflict_notes"], list)

    def test_aegis_validate_passes_complete_result(self):
        contract = aegis_from_raw(SAMPLE_AEGIS_RESULT)
        validate_aegis(contract)  # should not raise

    def test_aegis_validate_raises_on_missing_eta(self):
        with pytest.raises(ContractViolation):
            validate_aegis({"framework_scores": {"utilitarian": 0.8}})

    def test_epistemic_from_report_extracts_real_values(self):
        contract = epistemic_from_report(SAMPLE_EPISTEMIC_REPORT)
        assert contract["epsilon_value"] == 0.42
        assert contract["gamma_coherence"] == 0.68
        assert "newton_vs_empathy" in contract["pairwise_tensions"]

    def test_epistemic_validate_passes(self):
        contract = epistemic_from_report(SAMPLE_EPISTEMIC_REPORT)
        validate_epistemic(contract)

    def test_epistemic_validate_raises_on_missing_gamma(self):
        with pytest.raises(ContractViolation):
            validate_epistemic({"epsilon_value": 0.4})

    def test_guardian_from_raw_pass(self):
        contract = guardian_from_raw(True, {})
        assert contract["safety_status"] == "pass"
        assert contract["trust_calibration"] == "high"
        validate_guardian(contract)

    def test_guardian_from_raw_fail(self):
        contract = guardian_from_raw(False, {"boundary_violation": "harmful content"})
        assert contract["safety_status"] == "flag"
        assert "boundary_violation" in contract["boundary_flags"]

    def test_nexus_from_raw_risk_mapping(self):
        contract = nexus_from_raw({"pre_corruption_risk": "high", "confidence": 0.9})
        assert contract["risk_level"] == "high"
        assert contract["confidence"] == 0.9
        validate_nexus(contract)

    def test_nexus_validate_raises_on_missing_confidence(self):
        with pytest.raises(ContractViolation):
            validate_nexus({"risk_level": "low"})


# ── 5. Metrics population rate (release gate) ─────────────────────────────────

class TestReleaseGates:
    """Release gate checks — these are the minimum bar for a production cocoon."""

    def test_forge_full_cocoon_has_all_metrics(self):
        cocoon = make_full_v3_cocoon()
        d = cocoon.to_dict()
        assert d["eta_score"] is not None, "eta_score must be populated for forge_full"
        assert d["epsilon_value"] != 0.35 or d["pairwise_tensions"], (
            "epsilon_value should be computed from real outputs, not fallback 0.35"
        )
        assert d["gamma_coherence"] is not None
        assert d["psi_r"] >= 0.0
        assert len(d["active_perspectives"]) > 0

    def test_execution_path_always_present(self):
        cocoon = make_full_v3_cocoon()
        d = cocoon.to_dict()
        assert d["execution_path"] in (
            "forge_full", "adapter_lightweight", "fallback_template",
            "recovery_mode", "unknown"
        )

    def test_provenance_fields_always_present(self):
        cocoon = make_full_v3_cocoon()
        d = cocoon.to_dict()
        assert d["orchestrator_trace_id"] != ""
        assert d["serialization_version"] == "3.0"
        assert isinstance(d["model_inference_invoked"], bool)

    def test_no_silent_fallback_in_full_path(self):
        cocoon = make_full_v3_cocoon()
        assert cocoon.reason_for_fallback is None, (
            "forge_full should have no reason_for_fallback"
        )

    def test_integrity_score_above_80_for_complete_cocoon(self):
        with tempfile.TemporaryDirectory() as tmp:
            validator = CocoonValidator(
                store_path=tmp,
                quarantine_path=os.path.join(tmp, "q"),
            )
            cocoon = make_full_v3_cocoon()
            result = validator.validate(cocoon)
            assert result.integrity_score >= 0.80, (
                f"Complete cocoon integrity_score={result.integrity_score:.3f} "
                f"(should be >= 0.80). Missing: {result.missing_fields}"
            )

    def test_high_echo_risk_cocoon_quarantined(self):
        with tempfile.TemporaryDirectory() as tmp:
            validator = CocoonValidator(
                store_path=tmp,
                quarantine_path=os.path.join(tmp, "q"),
                integrity_threshold=0.4,
            )
            cocoon = make_full_v3_cocoon(echo_risk="high")
            path = validator.write(cocoon, filename_prefix="cocoon_v3")
            # Must end up in quarantine
            assert "quarantine" in str(path), (
                f"High echo_risk cocoon must be quarantined. Got path: {path}"
            )
