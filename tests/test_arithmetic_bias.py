#!/usr/bin/env python3
"""Tests for arithmetic bias detection in self_correction.py."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from inference.self_correction import (
    _extract_sum_diff_problem,
    _check_sum_diff_bias,
    universal_self_check,
)


def test_problem_detection():
    result = _extract_sum_diff_problem(
        "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?"
    )
    assert result is not None
    total, diff, correct = result
    assert abs(total - 1.10) < 0.001, f"Total={total}"
    assert abs(diff - 1.00) < 0.001, f"Diff={diff}"
    assert abs(correct - 0.05) < 0.001, f"Correct={correct}"
    print(f"[PASS] Problem detection: total={total}, diff={diff}, correct={correct}")


def test_non_math_query():
    result = _extract_sum_diff_problem("What is the capital of France?")
    assert result is None
    print("[PASS] Non-math query correctly returns None")


def test_bias_correction_cents():
    biased = "The ball costs 10 cents."
    corrected, issues = _check_sum_diff_bias(
        "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?",
        biased,
    )
    assert "5 cents" in corrected, f"Expected '5 cents', got: {corrected}"
    assert "10 cents" not in corrected, f"'10 cents' should be replaced: {corrected}"
    assert any("ARITHMETIC_FIX" in i for i in issues)
    print(f"[PASS] Cents correction: '{biased}' -> '{corrected}'")


def test_already_correct():
    correct_resp = "The ball costs 5 cents."
    unchanged, issues = _check_sum_diff_bias(
        "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?",
        correct_resp,
    )
    assert unchanged == correct_resp, f"Correct response modified: {unchanged}"
    assert not issues
    print(f"[PASS] Correct response untouched: '{correct_resp}'")


def test_bias_correction_dollar():
    biased = "The ball costs $0.10."
    corrected, issues = _check_sum_diff_bias(
        "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?",
        biased,
    )
    assert "$0.05" in corrected or "5 cents" in corrected, f"Expected $0.05 or '5 cents', got: {corrected}"
    print(f"[PASS] Dollar format: '{biased}' -> '{corrected}'")


def test_universal_self_check_integration():
    response = "The answer is 10 cents."
    final, issues = universal_self_check(
        response,
        query="A bat and a ball cost $1.10 total. The bat costs $1.00 more than the ball. What does the ball cost?",
    )
    assert "5 cents" in final, f"Expected '5 cents' in: {final}"
    assert any("ARITHMETIC_FIX" in i for i in issues)
    print(f"[PASS] universal_self_check: '{response}' -> '{final}'")


def test_universal_self_check_no_query():
    """Without a query, no arithmetic check runs — backward compat."""
    response = "The answer is 10 cents."
    final, issues = universal_self_check(response)
    assert "10 cents" in final, f"Without query, should not modify: {final}"
    assert not any("ARITHMETIC_FIX" in i for i in issues)
    print(f"[PASS] No query: response unchanged ({final})")


def test_non_math_query_no_interference():
    response = "Paris is the capital of France."
    final, issues = universal_self_check(response, query="What is the capital of France?")
    assert final.startswith("Paris"), f"Non-math should not change response: {final}"
    print("[PASS] Non-math query: response unchanged")


def test_generalization():
    # Widget A and B cost $1.20 total, A costs $0.80 more than B
    # correct = (1.20 - 0.80) / 2 = 0.20
    # biased  = 1.20 - 0.80 = 0.40
    # (amounts must be in consistent units for the detector to work)
    result = _extract_sum_diff_problem(
        "Widget A and Widget B cost $1.20 in total. Widget A costs $0.80 more than Widget B. What does Widget B cost?"
    )
    assert result is not None
    total, diff, correct = result
    assert abs(correct - 0.20) < 0.001, f"Expected correct=0.20, got {correct}"
    biased = round(total - diff, 4)
    assert abs(biased - 0.40) < 0.001, f"Expected biased=0.40, got {biased}"
    print(f"[PASS] Generalization: total={total}, diff={diff}, correct={correct}, biased={biased}")


def test_multiple_wrong_mentions():
    """All occurrences of the biased answer are replaced, not just the first."""
    response = "The ball costs 10 cents. So if the ball is 10 cents, the bat is $1.10."
    corrected, issues = _check_sum_diff_bias(
        "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?",
        response,
    )
    assert corrected.count("10 cents") == 0, f"All '10 cents' should be replaced: {corrected}"
    assert corrected.count("5 cents") >= 2, f"Both mentions should become '5 cents': {corrected}"
    print(f"[PASS] Multiple mentions: all corrected\n  {corrected}")


def test_simple_addition_not_triggered():
    """'I have 3 apples and 5 oranges, how many total?' must NOT trigger the bias check."""
    result = _extract_sum_diff_problem(
        "I have 3 apples and 5 oranges. How many pieces of fruit do I have in total?"
    )
    assert result is None, f"Simple addition should not be detected: {result}"
    print("[PASS] Simple addition: not triggered (no 'more than' signal)")


def test_requires_both_sum_and_diff():
    """Both a sum signal AND a difference signal must be present."""
    # Has diff but no sum signal
    result1 = _extract_sum_diff_problem(
        "Item A costs $1.00 more than item B. What does B cost?"
    )
    assert result1 is None, f"No sum signal: should return None, got {result1}"

    # Has sum but no diff signal
    result2 = _extract_sum_diff_problem(
        "A and B together cost $1.10. What does each cost?"
    )
    assert result2 is None, f"No diff signal: should return None, got {result2}"

    print("[PASS] Both signals required: sum-only and diff-only both rejected")


def test_large_numbers():
    """Works with non-trivial numbers beyond the canonical example."""
    # Pen + paper = $5.50, pen costs $5.00 more → paper = $0.25
    result = _extract_sum_diff_problem(
        "A pen and a notepad together cost $5.50. The pen costs $5.00 more than the notepad. What does the notepad cost?"
    )
    assert result is not None
    total, diff, correct = result
    assert abs(correct - 0.25) < 0.001, f"Expected 0.25, got {correct}"
    biased = round(total - diff, 4)
    corrected, issues = _check_sum_diff_bias(
        "A pen and a notepad together cost $5.50. The pen costs $5.00 more than the notepad. What does the notepad cost?",
        f"The notepad costs ${biased:.2f}.",
    )
    assert f"${correct:.2f}" in corrected or f"{int(round(correct*100))} cents" in corrected
    print(f"[PASS] Large numbers: total={total}, correct={correct}")


def test_zero_difference_edge():
    """A + B = S, A costs $0 more than B → A = B = S/2 (equal cost)."""
    # This should not trigger — "more than 0" is unusual phrasing and diff=0 gives biased=total
    # The existing guard (correct > 0) should return None for this
    result = _extract_sum_diff_problem(
        "Two items together cost $1.00. One costs $0.00 more than the other. How much is each?"
    )
    # Either returns None (correct guard fires) or correct = 0.50 (valid edge)
    if result is not None:
        _, _, correct = result
        assert abs(correct - 0.50) < 0.001, f"Equal-cost case: expected 0.50, got {correct}"
        print(f"[PASS] Zero-difference edge: detected as equal cost = {correct}")
    else:
        print("[PASS] Zero-difference edge: correctly returned None (no real 'more' signal)")


def main():
    print("=" * 60)
    print("ARITHMETIC BIAS TESTS")
    print("=" * 60)
    tests = [
        ("Problem detection", test_problem_detection),
        ("Non-math query", test_non_math_query),
        ("Cents correction", test_bias_correction_cents),
        ("Already correct", test_already_correct),
        ("Dollar format", test_bias_correction_dollar),
        ("universal_self_check integration", test_universal_self_check_integration),
        ("No query (backward compat)", test_universal_self_check_no_query),
        ("Non-math no interference", test_non_math_query_no_interference),
        ("Generalization", test_generalization),
        ("Multiple wrong mentions", test_multiple_wrong_mentions),
        ("Simple addition not triggered", test_simple_addition_not_triggered),
        ("Requires both sum and diff", test_requires_both_sum_and_diff),
        ("Large numbers", test_large_numbers),
        ("Zero-difference edge", test_zero_difference_edge),
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
            print(f"[ERROR] {e}")
            failed += 1
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
