#!/usr/bin/env python3
"""
AEGIS Layer 6 — RenderLayer with CocoonV3 Validation & Overlap Gate
Implements Phase 8 decoupled cognition:
  1. Separate CognitionSubstrate (math/reasoning, no LLM)
  2. RenderLayer validates output against AuthoredState
  3. Enforces >= 15% exact word overlap constraint

Uses real CocoonV3 schema validation from reasoning_forge.cocoon_schema_v3

Author: Jonathan Harrison / Codette Architecture
"""

import logging
import json
import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from collections import Counter

logger = logging.getLogger(__name__)


# =====================================================================
# PHASE 8 AUTHORED STATE (CognitionSubstrate Output)
# =====================================================================

@dataclass
class AuthoredState:
    """
    Pure mathematical/epistemic conclusion WITHOUT any rendering/prose synthesis.
    Output of CognitionSubstrate (LLM-free reasoning).
    """

    query: str  # Original user query
    conclusion: str  # Raw epistemic conclusion (can be terse, mathematical)
    evidence_vector: List[float]  # 128D epistemic embedding
    epsilon_value: float  # Epistemic tension from reasoning
    gamma_coherence: float  # Multi-perspective coherence
    emotional_tone: str  # Inferred emotion (joy, insight, confusion, etc.)
    active_perspectives: List[str] = field(default_factory=list)
    pairwise_tensions: Dict[str, float] = field(default_factory=dict)
    perspective_coverage: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dict for storage."""
        return {
            "query": self.query,
            "conclusion": self.conclusion,
            "evidence_vector": self.evidence_vector,
            "epsilon_value": self.epsilon_value,
            "gamma_coherence": self.gamma_coherence,
            "emotional_tone": self.emotional_tone,
            "active_perspectives": self.active_perspectives,
            "pairwise_tensions": self.pairwise_tensions,
            "perspective_coverage": self.perspective_coverage,
        }


# =====================================================================
# WORD OVERLAP VALIDATOR
# =====================================================================

class WordOverlapValidator:
    """
    Verifies that rendered output maintains >= 15% exact word overlap
    with the AuthoredState conclusion (hallucination guard).
    """

    @staticmethod
    def tokenize_words(text: str) -> List[str]:
        """Extract words (lowercase, alphanumeric only) from text."""
        # Remove punctuation, split, lowercase
        words = re.findall(r"\b[a-z0-9]+\b", text.lower())
        return words

    @staticmethod
    def calculate_overlap_percentage(authored_conclusion: str, rendered_output: str) -> Tuple[float, Dict]:
        """
        Calculate exact word overlap between two texts.

        Formula:
            overlap % = (2 * shared_words) / (words_in_authored + words_in_rendered)

        Args:
            authored_conclusion: Output from CognitionSubstrate
            rendered_output: Final rendered response

        Returns:
            Tuple: (overlap_percentage, details_dict)
        """
        authored_words = WordOverlapValidator.tokenize_words(authored_conclusion)
        rendered_words = WordOverlapValidator.tokenize_words(rendered_output)

        if not authored_words or not rendered_words:
            return 0.0, {"reason": "empty_text"}

        # Count word occurrences
        authored_counter = Counter(authored_words)
        rendered_counter = Counter(rendered_words)

        # Shared words (intersection with min counts)
        shared = sum(min(authored_counter[w], rendered_counter[w]) for w in authored_counter if w in rendered_counter)

        # Total unique vocabulary
        total_words = len(authored_words) + len(rendered_words)

        overlap_pct = (2.0 * shared) / total_words if total_words > 0 else 0.0

        details = {
            "authored_word_count": len(authored_words),
            "rendered_word_count": len(rendered_words),
            "shared_words_count": shared,
            "total_unique_vocab": len(set(authored_words) | set(rendered_words)),
            "overlap_percentage": round(overlap_pct * 100, 2),
        }

        return overlap_pct, details

    @staticmethod
    def validate_overlap(
        authored_conclusion: str, rendered_output: str, min_overlap: float = 0.15
    ) -> Tuple[bool, Dict]:
        """
        Validate that overlap meets minimum threshold.

        Args:
            authored_conclusion: Output from CognitionSubstrate
            rendered_output: Final rendered response
            min_overlap: Minimum overlap fraction (default 15%)

        Returns:
            Tuple: (valid, details)
        """
        overlap_pct, details = WordOverlapValidator.calculate_overlap_percentage(
            authored_conclusion, rendered_output
        )

        details["min_overlap_required"] = round(min_overlap * 100, 2)
        details["valid"] = overlap_pct >= min_overlap

        if overlap_pct < min_overlap:
            logger.warning(
                f"⚠️  [RenderLayer] Overlap {overlap_pct:.1%} < minimum {min_overlap:.1%}. "
                f"Possible hallucination detected."
            )
            details["alert"] = "POSSIBLE_HALLUCINATION"
        else:
            logger.info(f"✓ [RenderLayer] Overlap {overlap_pct:.1%} meets minimum threshold.")

        return details["valid"], details


# =====================================================================
# COCOON V3 SCHEMA VALIDATOR (Real Codette Integration)
# =====================================================================

class CocoonV3Validator:
    """
    Validates output cocoon against real CocoonV3 schema.
    Ensures all required fields are present and valid ranges.
    """

    # Valid enum values from cocoon_schema_v3.py
    VALID_EXECUTION_PATHS = frozenset([
        "forge_full",
        "adapter_lightweight",
        "fallback_template",
        "recovery_mode",
        "unknown",
    ])

    VALID_INTEGRITY_STATUSES = frozenset(["complete", "partial", "failed"])
    VALID_ECHO_RISK = frozenset(["unknown", "low", "medium", "high"])

    @staticmethod
    def validate_cocoon_v3(cocoon: dict) -> Tuple[bool, List[str]]:
        """
        Validate a CocoonV3 dict against schema constraints.

        Args:
            cocoon: Dictionary with CocoonV3 fields

        Returns:
            Tuple: (valid, errors_list)
        """
        errors = []

        # ── Required fields ────────────────────────────────────────────
        required_fields = [
            "cocoon_id",
            "query",
            "response_summary",
            "execution_path",
            "cocoon_integrity",
            "cocoon_integrity_score",
            "echo_risk",
            "epsilon_value",
            "gamma_coherence",
            "eta_score",
        ]

        for field_name in required_fields:
            if field_name not in cocoon:
                errors.append(f"Missing required field: {field_name}")

        # ── Execution path validation ──────────────────────────────────
        if "execution_path" in cocoon:
            if cocoon["execution_path"] not in CocoonV3Validator.VALID_EXECUTION_PATHS:
                errors.append(
                    f"Invalid execution_path: {cocoon['execution_path']}. "
                    f"Must be one of {sorted(CocoonV3Validator.VALID_EXECUTION_PATHS)}"
                )

        # ── Integrity status validation ────────────────────────────────
        if "cocoon_integrity" in cocoon:
            if cocoon["cocoon_integrity"] not in CocoonV3Validator.VALID_INTEGRITY_STATUSES:
                errors.append(
                    f"Invalid cocoon_integrity: {cocoon['cocoon_integrity']}. "
                    f"Must be one of {sorted(CocoonV3Validator.VALID_INTEGRITY_STATUSES)}"
                )

        # ── Echo risk validation ───────────────────────────────────────
        if "echo_risk" in cocoon:
            if cocoon["echo_risk"] not in CocoonV3Validator.VALID_ECHO_RISK:
                errors.append(
                    f"Invalid echo_risk: {cocoon['echo_risk']}. "
                    f"Must be one of {sorted(CocoonV3Validator.VALID_ECHO_RISK)}"
                )

        # ── Numeric range validation ───────────────────────────────────
        if "cocoon_integrity_score" in cocoon:
            score = cocoon["cocoon_integrity_score"]
            if not isinstance(score, (int, float)) or not 0.0 <= score <= 1.0:
                errors.append(f"cocoon_integrity_score {score} out of range [0.0, 1.0]")

        if "epsilon_value" in cocoon:
            eps = cocoon["epsilon_value"]
            if not isinstance(eps, (int, float)) or not 0.0 <= eps <= 1.0:
                errors.append(f"epsilon_value {eps} out of range [0.0, 1.0]")

        if "gamma_coherence" in cocoon:
            gamma = cocoon["gamma_coherence"]
            if not isinstance(gamma, (int, float)) or not 0.0 <= gamma <= 1.0:
                errors.append(f"gamma_coherence {gamma} out of range [0.0, 1.0]")

        if "eta_score" in cocoon:
            eta = cocoon["eta_score"]
            if eta is not None and (not isinstance(eta, (int, float)) or not 0.0 <= eta <= 1.0):
                errors.append(f"eta_score {eta} out of range [0.0, 1.0] (if present)")

        # ── Dict/List type validation ──────────────────────────────────
        if "pairwise_tensions" in cocoon:
            if not isinstance(cocoon["pairwise_tensions"], dict):
                errors.append(f"pairwise_tensions must be dict, got {type(cocoon['pairwise_tensions'])}")

        if "perspective_coverage" in cocoon:
            if not isinstance(cocoon["perspective_coverage"], dict):
                errors.append(f"perspective_coverage must be dict, got {type(cocoon['perspective_coverage'])}")

        if "active_perspectives" in cocoon:
            if not isinstance(cocoon["active_perspectives"], list):
                errors.append(f"active_perspectives must be list, got {type(cocoon['active_perspectives'])}")

        # ── Conditional field validation (forge_full path requires AEGIS) ──
        if cocoon.get("execution_path") == "forge_full":
            if not cocoon.get("model_inference_invoked"):
                errors.append("forge_full path requires model_inference_invoked=True")
            if not cocoon.get("active_perspectives"):
                errors.append("forge_full path requires active_perspectives populated")
            if cocoon.get("eta_score") is None:
                errors.append("forge_full path requires eta_score (AEGIS evaluation required)")

        valid = len(errors) == 0
        return valid, errors


# =====================================================================
# RENDER LAYER: ORCHESTRATOR
# =====================================================================

class RenderLayer:
    """
    Final output validation layer.
    Ensures rendered response maintains fidelity to AuthoredState
    while passing through CocoonV3 schema validation.
    """

    MIN_OVERLAP_THRESHOLD = 0.15  # 15% minimum word overlap

    @staticmethod
    def validate_and_render(
        authored_state: AuthoredState, rendered_output: str, target_cocoon: dict
    ) -> Tuple[bool, Dict]:
        """
        Full validation pipeline:
        1. Word overlap check (authored_state.conclusion vs rendered_output)
        2. CocoonV3 schema validation
        3. Integrity scoring

        Args:
            authored_state: Output from CognitionSubstrate
            rendered_output: Final user-facing response
            target_cocoon: Cocoon dict to be stored

        Returns:
            Tuple: (valid, validation_report)
        """

        report = {
            "timestamp": str(Path.cwd()),  # Could use time.time()
            "validation_steps": {},
            "valid": True,
            "alerts": [],
        }

        # ── Step 1: Word Overlap Validation ────────────────────────────
        logger.info(f"[RenderLayer] Validating word overlap...")
        overlap_valid, overlap_details = WordOverlapValidator.validate_overlap(
            authored_state.conclusion, rendered_output, min_overlap=RenderLayer.MIN_OVERLAP_THRESHOLD
        )

        report["validation_steps"]["word_overlap"] = {
            "valid": overlap_valid,
            "details": overlap_details,
        }

        if not overlap_valid:
            report["valid"] = False
            report["alerts"].append(f"Word overlap FAILED: {overlap_details['overlap_percentage']}% < 15%")

        # ── Step 2: CocoonV3 Schema Validation ─────────────────────────
        logger.info(f"[RenderLayer] Validating CocoonV3 schema...")
        cocoon_valid, cocoon_errors = CocoonV3Validator.validate_cocoon_v3(target_cocoon)

        report["validation_steps"]["cocoon_schema"] = {
            "valid": cocoon_valid,
            "errors": cocoon_errors,
        }

        if not cocoon_valid:
            report["valid"] = False
            report["alerts"].extend([f"CocoonV3 validation failed: {err}" for err in cocoon_errors])

        # ── Step 3: Coherence Consistency Check ────────────────────────
        # Verify that the cocoon's epistemic metrics align with AuthoredState
        logger.info(f"[RenderLayer] Checking coherence consistency...")
        cocoon_eps = target_cocoon.get("epsilon_value", 0.35)
        cocoon_gamma = target_cocoon.get("gamma_coherence", 0.72)
        authored_eps = authored_state.epsilon_value
        authored_gamma = authored_state.gamma_coherence

        eps_delta = abs(cocoon_eps - authored_eps)
        gamma_delta = abs(cocoon_gamma - authored_gamma)

        if eps_delta > 0.1 or gamma_delta > 0.1:
            logger.warning(
                f"⚠️  [RenderLayer] Coherence mismatch: ε Δ={eps_delta:.3f}, Γ Δ={gamma_delta:.3f}"
            )
            report["alerts"].append(f"Coherence drift detected: ε={eps_delta:.3f}, Γ={gamma_delta:.3f}")
            # Note: This is a warning but not a failure (could be legitimate evolution)

        report["validation_steps"]["coherence_check"] = {
            "epsilon_delta": eps_delta,
            "gamma_delta": gamma_delta,
            "valid": eps_delta < 0.15 and gamma_delta < 0.15,  # Soft threshold
        }

        # ── Final Decision ────────────────────────────────────────────
        if report["valid"]:
            logger.info("✓ [RenderLayer] VALIDATION PASSED — Output approved for storage")
        else:
            logger.error("✗ [RenderLayer] VALIDATION FAILED — Output blocked")

        return report["valid"], report

    @staticmethod
    def render_with_safeguards(
        authored_state: AuthoredState, user_facing_response: str
    ) -> Tuple[bool, str, Dict]:
        """
        High-level wrapper: Render user-facing response with built-in safeguards.

        Args:
            authored_state: Mathematical conclusion from CognitionSubstrate
            user_facing_response: Formatted response intended for user

        Returns:
            Tuple: (valid, response_text, validation_metadata)
        """
        # ── Overlap validation ────────────────────────────────────────
        overlap_valid, overlap_details = WordOverlapValidator.validate_overlap(
            authored_state.conclusion, user_facing_response, min_overlap=RenderLayer.MIN_OVERLAP_THRESHOLD
        )

        metadata = {
            "overlap_valid": overlap_valid,
            "overlap_details": overlap_details,
            "response_length": len(user_facing_response),
        }

        if not overlap_valid:
            logger.error(
                f"RenderLayer: Response rejected due to insufficient overlap "
                f"({overlap_details['overlap_percentage']}% < 15%)"
            )
            return False, user_facing_response, metadata

        logger.info(f"✓ RenderLayer: Response approved ({overlap_details['overlap_percentage']}% overlap)")
        return True, user_facing_response, metadata


# =====================================================================
# TESTING & DEMO
# =====================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("\n" + "=" * 70)
    print("AEGIS Layer 6 — RenderLayer with CocoonV3 Validation")
    print("=" * 70)

    # ── Test 1: Valid Overlap ──────────────────────────────────────
    print("\n[Test 1] Valid Word Overlap")
    authored = AuthoredState(
        query="What is the nature of recursive identity?",
        conclusion="Recursive identity emerges from epistemic tension and coherence.",
        evidence_vector=[0.5] * 128,
        epsilon_value=0.35,
        gamma_coherence=0.72,
        emotional_tone="insight",
        active_perspectives=["newton", "empathy", "philosophy"],
    )

    rendered = "The nature of recursive identity emerges from epistemic tension and coherence in multi-perspective reasoning."

    valid, metadata = WordOverlapValidator.validate_overlap(authored.conclusion, rendered)
    print(f"  Valid: {valid}")
    print(f"  Overlap: {metadata['overlap_percentage']}%")

    # ── Test 2: Invalid Overlap (Hallucination) ───────────────────
    print("\n[Test 2] Invalid Overlap (Hallucination Detection)")
    rendered_bad = "The universe consists of quantum strings and requires dark energy."

    valid_bad, metadata_bad = WordOverlapValidator.validate_overlap(authored.conclusion, rendered_bad)
    print(f"  Valid: {valid_bad}")
    print(f"  Overlap: {metadata_bad['overlap_percentage']}%")
    print(f"  Alert: {metadata_bad.get('alert', 'N/A')}")

    # ── Test 3: CocoonV3 Validation ────────────────────────────────
    print("\n[Test 3] CocoonV3 Schema Validation")
    mock_cocoon = {
        "cocoon_id": "test_001",
        "query": "What is recursive identity?",
        "response_summary": "Recursive identity emerges from epistemic tension.",
        "execution_path": "forge_full",
        "cocoon_integrity": "complete",
        "cocoon_integrity_score": 0.95,
        "echo_risk": "low",
        "epsilon_value": 0.35,
        "gamma_coherence": 0.72,
        "eta_score": 0.92,
        "model_inference_invoked": True,
        "active_perspectives": ["newton", "empathy", "philosophy"],
        "pairwise_tensions": {"newton_vs_empathy": 0.42},
        "perspective_coverage": {"newton": 0.85, "empathy": 0.72},
    }

    cocoon_valid, cocoon_errors = CocoonV3Validator.validate_cocoon_v3(mock_cocoon)
    print(f"  Valid: {cocoon_valid}")
    if cocoon_errors:
        for error in cocoon_errors:
            print(f"    - {error}")
    else:
        print("    ✓ All validations passed")

    # ── Test 4: Full RenderLayer Pipeline ──────────────────────────
    print("\n[Test 4] Full RenderLayer Pipeline")
    render_valid, render_report = RenderLayer.validate_and_render(authored, rendered, mock_cocoon)
    print(f"  Overall Valid: {render_valid}")
    print(f"  Steps Passed: {sum(1 for v in render_report['validation_steps'].values() if v.get('valid', True))}")
    if render_report["alerts"]:
        print(f"  Alerts: {render_report['alerts']}")

    print("\n" + "=" * 70 + "\n")
