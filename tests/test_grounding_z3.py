"""Tests for the z3 layer — Phase C3: universal validity + contradiction detection.

These reach claims sympy alone could not: universal validity over variables, and
whole-set contradictions (a circular ordering) that no single-claim check sees.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.grounding import verify, verify_consistency, Verdict, _HAS_Z3
from reasoning_forge.grounding_bridge import ground_text, FLAGGED, SUPPORTED, UNGROUNDED

import pytest

requires_z3 = pytest.mark.skipif(not _HAS_Z3, reason="z3 not installed")


# ── Universal validity over variables (sympy left these UNVERIFIABLE) ────────

@requires_z3
def test_universally_valid_inequality_verified():
    # x**2 >= 0 is true for every real x.
    assert verify("x**2 >= 0").verdict is Verdict.VERIFIED

@requires_z3
def test_universally_false_inequality_refuted():
    # x**2 < 0 is false for every real x.
    assert verify("x**2 < 0").verdict is Verdict.REFUTED

@requires_z3
def test_contingent_inequality_stays_unverifiable():
    # x > 0 is sometimes true, sometimes false — must NOT be decided.
    assert verify("x > 0").verdict is Verdict.UNVERIFIABLE

@requires_z3
def test_valid_entailment_shape():
    # 2*x >= x + x is a universal identity-inequality -> valid.
    assert verify("2*x >= x + x").verdict is Verdict.VERIFIED


# ── Cross-claim contradiction (the headline z3 capability) ───────────────────

@requires_z3
def test_circular_ordering_is_contradictory():
    r = verify_consistency(["a > b", "b > c", "c > a"])
    assert r.verdict is Verdict.REFUTED  # jointly impossible

@requires_z3
def test_consistent_ordering_is_verified():
    r = verify_consistency(["a > b", "b > c"])
    assert r.verdict is Verdict.VERIFIED  # a>b>c is satisfiable

@requires_z3
def test_consistency_needs_two_claims():
    assert verify_consistency(["a > b"]).verdict is Verdict.UNVERIFIABLE


# ── Bridge integration: contradictory thought gets FLAGGED ───────────────────

@requires_z3
def test_bridge_flags_jointly_contradictory_thought():
    # Each claim is individually satisfiable; together they are impossible.
    thought = "The ranking shows a > b, and clearly b > c, yet somehow c > a."
    r = ground_text(thought)
    assert r.status == FLAGGED
    assert "contradictory" in r.note.lower()

@requires_z3
def test_bridge_qualitative_thought_still_ungrounded():
    # No numeric/relational claims -> still honestly UNGROUNDED, not flagged.
    r = ground_text("Rational discomfort signals when principled change is needed.")
    assert r.status == UNGROUNDED


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call(["pytest", "-q", __file__]))
