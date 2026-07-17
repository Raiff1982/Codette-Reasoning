#!/usr/bin/env python3
"""Paired comparison of two benchmark result files — McNemar test + bias checks.

Works on:
  - phase0_kaggle.py outputs      (phase0_base_results.json vs phase0_newton_results.json)
  - gpqa_verify_revise.py output  (single file — sp vs vr are already paired inside)
  - any two JSONs whose results[] share "row" keys and a per-row correctness bool

Why McNemar: both arms answered the SAME questions, so the honest test is on
the discordant pairs (one right where the other is wrong), not on the two
accuracy totals. n01/n10 tell you more than the headline percentages.

Usage:
    python benchmarks/paired_analysis.py phase0_base_results.json phase0_newton_results.json
    python benchmarks/paired_analysis.py data/results/verify_revise/vr_*.json
"""

import json
import math
import sys
from pathlib import Path


def mcnemar(n01: int, n10: int) -> float:
    """Exact binomial McNemar p-value (two-sided). n01/n10 = discordant counts."""
    n = n01 + n10
    if n == 0:
        return 1.0
    k = min(n01, n10)
    # two-sided exact binomial test, p=0.5
    def binom_cdf(k, n):
        return sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    p = 2 * binom_cdf(k, n)
    return min(1.0, p)


def letter_bias(results: list, pred_key: str) -> dict:
    counts = {}
    for r in results:
        letter = r.get(pred_key)
        if letter:
            counts[letter] = counts.get(letter, 0) + 1
    return dict(sorted(counts.items()))


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compare_two_files(a_path: str, b_path: str):
    a, b = load(a_path), load(b_path)
    a_name = a.get("arm", Path(a_path).stem)
    b_name = b.get("arm", Path(b_path).stem)
    a_by_row = {r["row"]: r for r in a["results"]}
    b_by_row = {r["row"]: r for r in b["results"]}
    common = sorted(set(a_by_row) & set(b_by_row))
    if not common:
        sys.exit("No common rows between the two files.")

    n11 = n00 = n10 = n01 = 0
    for row in common:
        ra, rb = a_by_row[row]["correct"], b_by_row[row]["correct"]
        if ra and rb: n11 += 1
        elif ra and not rb: n10 += 1
        elif rb and not ra: n01 += 1
        else: n00 += 1

    acc_a = (n11 + n10) / len(common)
    acc_b = (n11 + n01) / len(common)
    p = mcnemar(n01, n10)

    print(f"Paired comparison on {len(common)} shared questions")
    print(f"  {a_name:<24} {acc_a:.1%}")
    print(f"  {b_name:<24} {acc_b:.1%}")
    print(f"  delta                    {(acc_b-acc_a)*100:+.2f}pp")
    print(f"\n  both right {n11} | both wrong {n00} | "
          f"only-{a_name} {n10} | only-{b_name} {n01}")
    print(f"  McNemar exact p = {p:.4f}"
          + ("  (significant at .05)" if p < 0.05 else "  (not significant)"))
    print(f"\n  Answer-letter distribution:")
    print(f"    {a_name}: {letter_bias(a['results'], 'predicted')}")
    print(f"    {b_name}: {letter_bias(b['results'], 'predicted')}")


def analyze_vr_file(path: str):
    d = load(path)
    results = d["results"]
    n = len(results)
    n11 = sum(1 for r in results if r["sp_correct"] and r["vr_correct"])
    n10 = sum(1 for r in results if r["sp_correct"] and not r["vr_correct"])
    n01 = sum(1 for r in results if r["vr_correct"] and not r["sp_correct"])
    n00 = n - n11 - n10 - n01
    p = mcnemar(n01, n10)
    rev = d.get("revisions", {})

    print(f"Verify-and-Revise paired analysis ({n} questions)")
    print(f"  single-pass    {(n11+n10)/n:.1%}")
    print(f"  verify-revise  {(n11+n01)/n:.1%}   delta {(n01-n10)/n*100:+.2f}pp")
    print(f"\n  both right {n11} | both wrong {n00} | "
          f"only-SP {n10} | only-VR {n01}")
    print(f"  McNemar exact p = {p:.4f}"
          + ("  (significant at .05)" if p < 0.05 else "  (not significant)"))
    print(f"  revisions: {rev.get('total','?')} total, "
          f"{rev.get('to_right','?')} fixed, {rev.get('to_wrong','?')} broke")
    verdicts = {}
    for r in results:
        v = r.get("attack_verdict", "?")
        verdicts[v] = verdicts.get(v, 0) + 1
    print(f"  critic verdicts: {verdicts}")


if __name__ == "__main__":
    if len(sys.argv) == 2:
        analyze_vr_file(sys.argv[1])
    elif len(sys.argv) == 3:
        compare_two_files(sys.argv[1], sys.argv[2])
    else:
        sys.exit(__doc__)
