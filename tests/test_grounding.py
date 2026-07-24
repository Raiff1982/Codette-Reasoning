"""Tests for reasoning_forge/grounding.py — the verifying half of the mind.

The most important tests here are the HONESTY ones: a claim the verifier cannot
formalize must come back UNVERIFIABLE, never VERIFIED. A grounding layer that
guesses is worse than none.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_forge.grounding import (
    verify, extract_claims, log_shadow, Verdict, GroundingResult, _HAS_SYMPY,
)


# ── Core correctness ────────────────────────────────────────────────────────

def test_true_arithmetic_is_verified():
    assert verify("2 + 2 == 4").verdict is Verdict.VERIFIED
    assert verify("10 * 10 = 100").verdict is Verdict.VERIFIED

def test_false_arithmetic_is_refuted():
    assert verify("2 + 2 == 5").verdict is Verdict.REFUTED
    assert verify("1 = 2").verdict is Verdict.REFUTED

def test_algebraic_identity_verified():
    # (x+1)^2 == x^2 + 2x + 1 is true for all x
    assert verify("(x + 1)**2 == x**2 + 2*x + 1").verdict is Verdict.VERIFIED

def test_algebraic_falsehood_refuted():
    assert verify("(x + 1)**2 == x**2 + 1").verdict is Verdict.REFUTED

def test_inequalities():
    assert verify("5 > 3").verdict is Verdict.VERIFIED
    assert verify("3 > 5").verdict is Verdict.REFUTED
    assert verify("4 >= 4").verdict is Verdict.VERIFIED
    assert verify("4 < 4").verdict is Verdict.REFUTED
    assert verify("2 != 3").verdict is Verdict.VERIFIED


# ── THE HONESTY INVARIANTS (the whole point) ────────────────────────────────

def test_non_claim_is_unverifiable_not_verified():
    # Natural language with no formal comparator must NOT be VERIFIED.
    for text in [
        "the sky is a metaphor for hope",
        "Newton and DaVinci agree here",
        "this is a beautiful idea",
        "",
    ]:
        assert verify(text).verdict is Verdict.UNVERIFIABLE, text

def test_unparseable_math_is_unverifiable_not_verified():
    # Looks like a claim, can't be parsed — must be UNVERIFIABLE, never guessed.
    r = verify("2 +* 2 == 4")
    assert r.verdict is Verdict.UNVERIFIABLE

def test_non_constant_ordering_is_unverifiable():
    # x > 0 is not universally true or false -> we must NOT decide it.
    assert verify("x > 0").verdict is Verdict.UNVERIFIABLE

def test_every_result_carries_a_reason():
    # Omit-never-fabricate: a verdict always explains itself.
    for text in ["2+2==4", "x>0", "hello", "2+2==5"]:
        assert verify(text).detail

def test_symbolic_equation_that_is_conditional_not_verified():
    # x == 5 is only true for one value; as a universal claim it's not verified.
    # (simplify(x-5) != 0 in general) -> REFUTED as a universal identity.
    assert verify("x == 5").verdict is Verdict.REFUTED


# ── Claim extraction (conservative) ─────────────────────────────────────────

def test_extract_pulls_arithmetic_claims():
    claims = extract_claims("The result is 2 + 2 = 4 and also 3 * 3 = 9 here.")
    assert any("2 + 2" in c for c in claims)
    assert any("3 * 3" in c for c in claims)

def test_extract_ignores_pure_prose():
    assert extract_claims("This thought bridges empathy and physics beautifully.") == []

def test_extract_requires_a_digit():
    # "x = y" has no digit -> not extracted as an arithmetic claim to check.
    assert extract_claims("we set x = y for clarity") == []


# ── Purity + shadow logging ─────────────────────────────────────────────────

def test_verify_is_pure(tmp_path):
    # verify() must not create the shadow log; only log_shadow() writes.
    default_log = Path(__file__).resolve().parent.parent / "data" / "grounding_shadow.jsonl"
    before = default_log.exists()
    verify("2 + 2 == 4")
    after = default_log.exists()
    assert before == after  # verify() created nothing

def test_log_shadow_writes_applied_false(tmp_path):
    import json
    p = tmp_path / "g.jsonl"
    log_shadow(verify("2 + 2 == 4"), path=p)
    line = p.read_text(encoding="utf-8").strip()
    rec = json.loads(line)
    assert rec["applied"] is False
    assert rec["mode"] == "shadow"
    assert rec["verdict"] == "verified"


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call(["pytest", "-q", __file__]))
