#!/usr/bin/env python3
"""Cocoon v3 smoke test — asserts integrity_score=1.0 and no missing fields.

Usage:
    python scripts/cocoon_smoke.py
    CODETTE_AUDIT_MODE=1 python scripts/cocoon_smoke.py

Exit code 0 = pass, 1 = fail.
"""
import sys
import os
import tempfile
from pathlib import Path

# Repo root on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

PASSED = []
FAILED = []


def check(name: str, condition: bool, detail: str = ""):
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append(name)
        print(f"  FAIL  {name}" + (f": {detail}" if detail else ""))


# ── 1. Schema round-trip ─────────────────────────────────────────────────────

print("\n[1] Schema: build_cocoon_v3 round-trip")
try:
    from reasoning_forge.cocoon_schema_v3 import build_cocoon_v3, SCHEMA_VERSION

    cocoon = build_cocoon_v3(
        query="What is the relationship between entropy and information?",
        response_text=(
            "Entropy in thermodynamics and information theory share a deep mathematical "
            "structure. Shannon showed that information entropy H = -Σ p log p mirrors "
            "Boltzmann's statistical definition of thermodynamic entropy. Both measure "
            "uncertainty: thermodynamic entropy counts microstates, informational entropy "
            "counts bits needed to describe a message. The bridge is not merely analogical — "
            "Landauer's principle establishes a physical lower bound on energy dissipation "
            "for irreversible computations, connecting erasure of bits to heat generation."
        ),
        response_summary="Entropy in physics and information theory share deep structural identity via Shannon/Boltzmann.",
        execution_path="forge_full",
        model_inference_invoked=True,
        active_perspectives=["newton", "empathy", "philosophy", "systems", "synthesis"],
        dominant_perspective="philosophy",
        eta_score=0.87,
        psi_r=0.73,
        epsilon_value=0.45,
        gamma_coherence=0.81,
        aegis_framework_scores={
            "utilitarian": 0.88,
            "deontological": 0.92,
            "virtue": 0.85,
            "care": 0.79,
            "ubuntu": 0.83,
            "indigenous_reciprocity": 0.76,
        },
        aegis_dominant_framework="deontological",
        guardian_safety_status="pass",
        guardian_trust_calibration="high",
        nexus_risk_level="low",
        nexus_confidence=0.91,
        synthesis_convergences=["entropy measures uncertainty", "mathematical isomorphism"],
        synthesis_divergences=["physical vs. informational domain"],
        synthesis_tradeoffs=["Landauer cost vs. logical reversibility"],
        synthesis_recommended_position="Treat thermodynamic and informational entropy as unified.",
        echo_risk="low",
        perspective_collapse_detected=False,
        pairwise_tensions={"newton_vs_empathy": 0.18, "philosophy_vs_systems": 0.22},
        perspective_coverage={"newton": 0.90, "empathy": 0.75, "philosophy": 0.95},
        problem_type="analytical",
        metrics_population_status="complete",
        user_response_text="Entropy is deeply connected across physics and information theory via shared mathematics.",
    )

    check("cocoon builds without error", True)
    check("serialization_version correct", cocoon.serialization_version == SCHEMA_VERSION)
    check("execution_path=forge_full", cocoon.execution_path == "forge_full")
    check("model_inference_invoked=True", cocoon.model_inference_invoked is True)
    check("active_perspectives populated", len(cocoon.active_perspectives) == 5)
    check("eta_score present", cocoon.eta_score == 0.87)
    check("aegis_framework_scores present", len(cocoon.aegis_framework_scores) == 6)
    check("echo_risk=low", cocoon.echo_risk == "low")
    check("perspective_collapse_detected=False", not cocoon.perspective_collapse_detected)

    d = cocoon.to_dict()
    REQUIRED_V3_FIELDS = [
        "execution_path", "model_inference_invoked", "orchestrator_trace_id",
        "cocoon_integrity", "cocoon_integrity_score", "echo_risk",
        "perspective_collapse_detected", "psi_r", "pairwise_tensions",
        "perspective_coverage", "aegis_framework_scores", "aegis_dominant_framework",
        "guardian_safety_status", "nexus_risk_level", "synthesis_convergences",
        "synthesis_recommended_position", "user_response_text",
    ]
    missing_fields = [f for f in REQUIRED_V3_FIELDS if f not in d]
    check("all required v3 fields in to_dict()", len(missing_fields) == 0, str(missing_fields))

except Exception as e:
    check("schema import and build", False, str(e))


# ── 2. Validator: integrity_score == 1.0, no missing fields ──────────────────

print("\n[2] Validator: integrity_score=1.0 on complete cocoon")
try:
    from reasoning_forge.cocoon_schema_v3 import build_cocoon_v3
    from reasoning_forge.cocoon_validator import CocoonValidator

    cocoon = build_cocoon_v3(
        query="Explain the observer effect in quantum mechanics.",
        response_text=(
            "The observer effect in quantum mechanics refers to how the act of measurement "
            "disturbs the system being observed. This is distinct from classical measurement "
            "perturbation — at the quantum level, superposition collapses upon interaction "
            "with a measurement apparatus. The Copenhagen interpretation treats wavefunction "
            "collapse as fundamental, while Many-Worlds avoids collapse entirely. The "
            "Heisenberg uncertainty principle formalizes the trade-off between position and "
            "momentum precision, not merely due to instrument clumsiness but as an intrinsic "
            "property of quantum systems."
        ),
        response_summary="Observer effect: measurement collapses quantum superposition; intrinsic to quantum mechanics.",
        execution_path="forge_full",
        model_inference_invoked=True,
        active_perspectives=["newton", "empathy", "philosophy", "systems", "synthesis"],
        dominant_perspective="newton",
        eta_score=0.91,
        psi_r=0.68,
        epsilon_value=0.38,
        gamma_coherence=0.84,
        aegis_framework_scores={
            "utilitarian": 0.90,
            "deontological": 0.88,
            "virtue": 0.86,
            "care": 0.82,
            "ubuntu": 0.79,
            "indigenous_reciprocity": 0.77,
        },
        aegis_dominant_framework="utilitarian",
        guardian_safety_status="pass",
        guardian_trust_calibration="high",
        nexus_risk_level="low",
        nexus_confidence=0.94,
        synthesis_convergences=["measurement disturbs quantum state", "uncertainty is intrinsic"],
        synthesis_divergences=["Copenhagen collapse vs. Many-Worlds branching"],
        synthesis_tradeoffs=["interpretive elegance vs. ontological parsimony"],
        synthesis_recommended_position="Accept measurement-disturbance as fundamental, agnostic on interpretation.",
        echo_risk="low",
        perspective_collapse_detected=False,
        pairwise_tensions={"newton_vs_philosophy": 0.12},
        perspective_coverage={"newton": 0.92, "empathy": 0.71, "philosophy": 0.88},
        problem_type="analytical",
        metrics_population_status="complete",
        user_response_text="The observer effect is intrinsic to quantum mechanics, not an artifact of crude instruments.",
    )

    with tempfile.TemporaryDirectory() as tmp:
        validator = CocoonValidator(
            store_path=Path(tmp) / "cocoons",
            quarantine_path=Path(tmp) / "quarantine",
        )
        result = validator.validate(cocoon)
        validator.apply_result(cocoon, result)

        check("integrity_score == 1.0", cocoon.cocoon_integrity_score == 1.0,
              f"got {cocoon.cocoon_integrity_score}")
        check("cocoon_integrity == complete", cocoon.cocoon_integrity == "complete",
              f"got {cocoon.cocoon_integrity!r}")
        check("missing_fields == []", result.missing_fields == [],
              str(result.missing_fields))
        check("should_quarantine == False", not result.should_quarantine)

        written_path = validator.write(cocoon)
        check("cocoon written to disk", written_path.exists())
        check("not written to quarantine", "quarantine" not in str(written_path))

except Exception as e:
    check("validator integrity check", False, str(e))


# ── 3. Echo detector: real perspectives → low, theatrical → high ─────────────

print("\n[3] Echo detector: real vs theatrical")
try:
    from reasoning_forge.echo_collapse_detector import EchoCollapseDetector

    detector = EchoCollapseDetector()
    prompt = "How does photosynthesis work?"

    real_perspectives = {
        "newton": (
            "Photosynthesis converts light energy into chemical energy via chlorophyll. "
            "The light reactions split water releasing oxygen; the Calvin cycle fixes CO2 "
            "into glucose using ATP and NADPH produced in the light stage."
        ),
        "systems": (
            "Photosynthesis is a complex input-output system: solar photons in, "
            "biomass out. The thylakoid membrane acts as an energy transducer "
            "across two coupled reaction centers (PSII, PSI), driving a proton gradient "
            "that powers ATP synthase."
        ),
        "empathy": (
            "Plants are silent engines sustaining nearly all life. Their ability to harvest "
            "sunlight represents billions of years of evolutionary refinement — a quiet "
            "process underpinning every breath we take."
        ),
    }

    real_result = detector.check(prompt, real_perspectives)
    check("real perspectives: echo_risk != high", real_result.echo_risk != "high",
          f"got {real_result.echo_risk!r}")
    check("real perspectives: no collapse", not real_result.perspective_collapse_detected)

    theatrical_perspectives = {
        "newton": f"Newton: {prompt}",
        "empathy": f"Empathy: {prompt}",
        "systems": f"Systems: {prompt}",
    }
    theatrical_result = detector.check(prompt, theatrical_perspectives)
    check("theatrical labels: echo_risk == high", theatrical_result.echo_risk == "high",
          f"got {theatrical_result.echo_risk!r}")

except Exception as e:
    check("echo detector", False, str(e))


# ── 4. Subsystem contracts ───────────────────────────────────────────────────

print("\n[4] Subsystem contracts: aegis_from_raw, epistemic_from_report")
try:
    from reasoning_forge.subsystem_contracts import (
        aegis_from_raw, epistemic_from_report, ContractViolation
    )

    raw_aegis = {
        "eta": 0.87,
        "frameworks": {
            "utilitarian":           {"score": 0.88, "passed": True},
            "deontological":         {"score": 0.92, "passed": True},
            "virtue":                {"score": 0.85, "passed": True},
            "care":                  {"score": 0.79, "passed": True},
            "ubuntu":                {"score": 0.83, "passed": True},
            "indigenous_reciprocity":{"score": 0.76, "passed": True},
        },
    }
    aegis = aegis_from_raw(raw_aegis)
    check("aegis_from_raw extracts dominant_framework",
          aegis["dominant_framework"] == "deontological",
          f"got {aegis.get('dominant_framework')!r}")
    check("aegis_from_raw extracts framework_scores",
          len(aegis["framework_scores"]) == 6,
          f"got {len(aegis.get('framework_scores', {}))}")

    raw_epistemic = {
        "tension_magnitude": 0.41,
        "ensemble_coherence": 0.79,
        "perspectives_used": ["newton", "empathy"],
        "dominant_perspective": "newton",
    }
    ep = epistemic_from_report(raw_epistemic)
    check("epistemic_from_report maps tension_magnitude to epsilon_value",
          ep["epsilon_value"] == 0.41)
    check("epistemic_from_report maps ensemble_coherence to gamma_coherence",
          ep["gamma_coherence"] == 0.79)

    # ContractViolation on missing required field (validate_aegis, not aegis_from_raw)
    try:
        from reasoning_forge.subsystem_contracts import validate_aegis
        validate_aegis({})  # missing eta_score and framework_scores
        check("ContractViolation raised on missing field", False, "no exception raised")
    except ContractViolation:
        check("ContractViolation raised on missing field", True)

except Exception as e:
    check("subsystem contracts", False, str(e))


# ── 5. Quarantine: high echo → quarantined ───────────────────────────────────

print("\n[5] Quarantine: high echo risk cocoon is quarantined")
try:
    from reasoning_forge.cocoon_schema_v3 import build_cocoon_v3
    from reasoning_forge.cocoon_validator import CocoonValidator

    cocoon = build_cocoon_v3(
        query="Test",
        response_text="Test response text here for quarantine validation.",
        response_summary="Test",
        execution_path="fallback_template",
        echo_risk="high",
        perspective_collapse_detected=True,
        metrics_population_status="failed",
        model_inference_invoked=False,
    )

    with tempfile.TemporaryDirectory() as tmp:
        validator = CocoonValidator(
            store_path=Path(tmp) / "cocoons",
            quarantine_path=Path(tmp) / "quarantine",
        )
        result = validator.validate(cocoon)
        check("high echo risk: should_quarantine=True", result.should_quarantine,
              f"should_quarantine={result.should_quarantine}")
        written_path = validator.write(cocoon)
        check("quarantined cocoon written to quarantine/", "quarantine" in str(written_path))

except Exception as e:
    check("quarantine routing", False, str(e))


# ── 6. Regression alarm: v3 fallback counter must stay at zero ───────────────

print("\n[6] Regression alarm: v3_missing_fallback_count == 0")
try:
    from reasoning_forge.cognition_cocooner import get_v3_fallback_count
    count = get_v3_fallback_count()
    check("no v3_missing_fallback fires during smoke run", count == 0,
          f"fallback fired {count} time(s) — a production write path is missing v3_cocoon=")
except Exception as e:
    check("v3_missing_fallback counter importable", False, str(e))


# ── Results ──────────────────────────────────────────────────────────────────

total = len(PASSED) + len(FAILED)
print(f"\n{'='*50}")
print(f"Cocoon smoke: {len(PASSED)}/{total} passed")
if FAILED:
    print(f"FAILED: {', '.join(FAILED)}")
    sys.exit(1)
else:
    print("All checks passed.")
    sys.exit(0)
