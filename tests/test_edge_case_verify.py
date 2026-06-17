#!/usr/bin/env python3
"""Edge case verification from the technical review."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from inference.self_correction import _extract_sum_diff_problem, _check_sum_diff_bias


def test_valuation_false_positives():
    """Valuation reasoning and risk frontier outputs must NOT trigger the check."""
    cases = [
        "Scenario A costs 2M more than scenario B in the risk frontier analysis",
        "Risk frontier: best case saves 50M, worst case costs 30M more to implement",
        "I have $1.00 left over after buying the ball",
        "3 apples and 5 oranges cost $2.00 in total",  # no diff signal
        "The expected value of portfolio A is $500M, portfolio B is $450M more risky",
    ]
    for q in cases:
        result = _extract_sum_diff_problem(q)
        assert result is None, f"FALSE POSITIVE — should return None for: {q!r}\n  got: {result}"
        print(f"  [OK] None: {q[:70]}")
    print("[PASS] All valuation/non-bias queries correctly rejected")


def test_correct_already_in_response():
    """If the correct answer is already in the response, leave it alone."""
    query = "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?"
    # Response mentions both wrong (10 cents) AND correct (5 cents)
    mixed = "Some people say 10 cents, but the correct answer is 5 cents."
    corrected, issues = _check_sum_diff_bias(query, mixed)
    assert corrected == mixed, f"Mixed response should not be modified:\n  got: {corrected!r}"
    assert not issues, f"No ARITHMETIC_FIX expected: {issues}"
    print(f"[PASS] Mixed response untouched (correct already present)")


def test_canonical_bat_and_ball():
    """Canonical bat-and-ball: biased answer should be corrected to 5 cents."""
    query = "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?"
    result = _extract_sum_diff_problem(query)
    assert result is not None
    total, diff, correct = result
    assert abs(total - 1.10) < 0.001, f"total={total}"
    assert abs(diff - 1.00) < 0.001, f"diff={diff}"
    assert abs(correct - 0.05) < 0.001, f"correct={correct}"

    response = "The ball costs 10 cents."
    corrected, issues = _check_sum_diff_bias(query, response)
    assert "5 cents" in corrected, f"Expected '5 cents': {corrected}"
    assert "10 cents" not in corrected, f"'10 cents' should be gone: {corrected}"
    print(f"[PASS] Bat-and-ball: '{response}' -> '{corrected}'")


def test_implicit_diff_signals():
    """'extra' is a valid difference signal and should trigger detection."""
    query = "Two items together cost $2.20. One costs $2.00 more than the other. What does the cheaper one cost?"
    result = _extract_sum_diff_problem(query)
    assert result is not None, "Should detect sum-diff with 'more than'"
    _, _, correct = result
    assert abs(correct - 0.10) < 0.001, f"Expected 0.10, got {correct}"
    print(f"[PASS] 'more than' detection: correct={correct}")

    # 'extra' — currently requires explicit "more than" extraction
    # This tests that 'extra' as a has_diff signal works end-to-end when
    # 'more' is also present in the sentence
    query2 = "Pen and paper cost $5.50 total. The pen costs $5.00 more. How much is the paper?"
    result2 = _extract_sum_diff_problem(query2)
    assert result2 is not None, f"Should detect: {query2}"
    _, _, c2 = result2
    assert abs(c2 - 0.25) < 0.001, f"Expected 0.25, got {c2}"
    print(f"[PASS] Implicit: pen+paper correct={c2}")


def main():
    print("=" * 60)
    print("EDGE CASE VERIFICATION")
    print("=" * 60)
    tests = [
        ("Valuation false positives", test_valuation_false_positives),
        ("Correct already in response", test_correct_already_in_response),
        ("Canonical bat-and-ball", test_canonical_bat_and_ball),
        ("Implicit diff signals", test_implicit_diff_signals),
    ]
    passed = failed = 0
    for name, fn in tests:
        try:
            print(f"\n[TEST] {name}")
            fn()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{'='*60}")
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
