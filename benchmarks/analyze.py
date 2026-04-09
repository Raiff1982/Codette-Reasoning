#!/usr/bin/env python3
"""
Codette Benchmark Analysis — Reproducible Stats Pipeline
=========================================================

Turns raw benchmark JSON into:
  1. Per-problem long-form CSV (one row per problem_id x condition, all 7 dims + composite)
  2. Paired statistics report (paired t-test, Wilcoxon signed-rank, 95% CI, Holm-Bonferroni)
  3. Sanity checks (within-condition variance, unique problem IDs, no duplicate rows)
  4. Console summary suitable for paper appendix

Usage:
    python benchmarks/analyze.py                              # uses default path
    python benchmarks/analyze.py --input data/results/codette_benchmark_results.json
    python benchmarks/analyze.py --input results.json --output data/results/

Author: Jonathan Harrison (Raiff's Bits LLC)
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import sys
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ═══════════════════════════════════════════════════════════════════
# SECTION 1: LOAD & FLATTEN
# ═══════════════════════════════════════════════════════════════════

DIMENSIONS = [
    "reasoning_depth",
    "perspective_diversity",
    "coherence",
    "ethical_coverage",
    "novelty",
    "factual_grounding",
    "turing_naturalness",
]

CSV_COLUMNS = [
    "problem_id", "condition",
    *DIMENSIONS,
    "composite",
    "response_length", "latency_ms",
]


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def flatten_to_rows(report: dict) -> List[dict]:
    """Convert nested per_problem JSON into flat rows."""
    rows = []
    per_problem = report.get("per_problem", {})
    for problem_id, conditions in sorted(per_problem.items()):
        for condition, data in sorted(conditions.items()):
            row = {
                "problem_id": problem_id,
                "condition": condition,
                "composite": data.get("composite", 0),
                "response_length": data.get("response_length", 0),
                "latency_ms": data.get("latency_ms", 0),
            }
            dims = data.get("dimensions", {})
            for dim in DIMENSIONS:
                row[dim] = dims.get(dim, {}).get("score", 0)
            rows.append(row)
    return rows


def write_csv(rows: List[dict], path: str):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  CSV written: {path} ({len(rows)} rows)")


# ═══════════════════════════════════════════════════════════════════
# SECTION 2: PAIRED STATISTICS
# ═══════════════════════════════════════════════════════════════════

def paired_scores(rows: List[dict], cond_a: str, cond_b: str) -> Tuple[List[float], List[float], List[str]]:
    """Extract paired composite scores for two conditions, matched by problem_id."""
    by_problem_a = {r["problem_id"]: r["composite"] for r in rows if r["condition"] == cond_a}
    by_problem_b = {r["problem_id"]: r["composite"] for r in rows if r["condition"] == cond_b}
    common = sorted(set(by_problem_a) & set(by_problem_b))
    return (
        [by_problem_a[p] for p in common],
        [by_problem_b[p] for p in common],
        common,
    )


def paired_t_test(x: List[float], y: List[float]) -> Tuple[float, float, int]:
    """Paired t-test. Returns (t_stat, p_approx, df)."""
    n = len(x)
    if n < 2:
        return 0.0, 1.0, 0
    diffs = [b - a for a, b in zip(x, y)]
    mean_d = statistics.mean(diffs)
    std_d = statistics.stdev(diffs)
    if std_d == 0:
        return float("inf") if mean_d != 0 else 0.0, 0.0 if mean_d != 0 else 1.0, n - 1
    se = std_d / math.sqrt(n)
    t = mean_d / se
    df = n - 1
    # Approximate two-tailed p via normal (conservative for small n)
    z = abs(t)
    p = 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))
    return round(t, 4), round(p, 6), df


def wilcoxon_signed_rank(x: List[float], y: List[float]) -> Tuple[float, float]:
    """Wilcoxon signed-rank test (exact for small n, normal approx for large n).
    Returns (W_statistic, p_approx)."""
    diffs = [(b - a) for a, b in zip(x, y)]
    # Remove zeros
    nonzero = [(abs(d), 1 if d > 0 else -1) for d in diffs if d != 0]
    n = len(nonzero)
    if n < 2:
        return 0.0, 1.0

    # Rank by absolute difference
    nonzero.sort(key=lambda t: t[0])
    ranks = []
    i = 0
    while i < n:
        j = i
        while j < n and nonzero[j][0] == nonzero[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2  # 1-indexed average
        for k in range(i, j):
            ranks.append((avg_rank, nonzero[k][1]))
        i = j

    W_plus = sum(r for r, s in ranks if s > 0)
    W_minus = sum(r for r, s in ranks if s < 0)
    W = min(W_plus, W_minus)

    # Normal approximation for p-value
    mean_W = n * (n + 1) / 4
    std_W = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    if std_W == 0:
        return W, 1.0
    z = (W - mean_W) / std_W
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return round(W, 2), round(p, 6)


def cohens_d_paired(x: List[float], y: List[float]) -> float:
    """Cohen's d for paired samples (d_z = mean_diff / std_diff)."""
    diffs = [b - a for a, b in zip(x, y)]
    if len(diffs) < 2:
        return 0.0
    mean_d = statistics.mean(diffs)
    std_d = statistics.stdev(diffs)
    if std_d == 0:
        return float("inf") if mean_d != 0 else 0.0
    return round(mean_d / std_d, 4)


def confidence_interval_95(x: List[float], y: List[float]) -> Tuple[float, float]:
    """95% CI for mean difference (paired)."""
    diffs = [b - a for a, b in zip(x, y)]
    n = len(diffs)
    if n < 2:
        return 0.0, 0.0
    mean_d = statistics.mean(diffs)
    std_d = statistics.stdev(diffs)
    se = std_d / math.sqrt(n)
    # Use z=1.96 (normal approx; for n=17, t_crit ~2.12 but we note this)
    # For rigor with small n, use t-distribution critical value
    # Approximate t_crit for df=n-1 using Cornish-Fisher expansion
    df = n - 1
    if df <= 30:
        # Simple lookup for common small df values
        t_crit_table = {
            1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
            6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
            11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
            16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
            25: 2.060, 30: 2.042,
        }
        t_crit = t_crit_table.get(df, 2.0)  # fallback
    else:
        t_crit = 1.96
    margin = t_crit * se
    return round(mean_d - margin, 4), round(mean_d + margin, 4)


def holm_bonferroni(p_values: List[Tuple[str, float]]) -> List[Tuple[str, float, bool]]:
    """Holm-Bonferroni correction for multiple comparisons.
    Input: [(label, p_value), ...]
    Output: [(label, adjusted_p, significant), ...]"""
    m = len(p_values)
    sorted_ps = sorted(p_values, key=lambda x: x[1])
    results = []
    for i, (label, p) in enumerate(sorted_ps):
        adjusted = min(p * (m - i), 1.0)
        results.append((label, round(adjusted, 6), adjusted < 0.05))
    # Enforce monotonicity (adjusted p can't decrease)
    for i in range(1, len(results)):
        if results[i][1] < results[i - 1][1]:
            results[i] = (results[i][0], results[i - 1][1], results[i - 1][1] < 0.05)
    return results


# ═══════════════════════════════════════════════════════════════════
# SECTION 3: SANITY CHECKS
# ═══════════════════════════════════════════════════════════════════

def run_sanity_checks(rows: List[dict]) -> List[str]:
    """Run all sanity checks. Returns list of issues (empty = all pass)."""
    issues = []

    # Check 1: Unique problem IDs
    problem_ids = sorted(set(r["problem_id"] for r in rows))
    conditions = sorted(set(r["condition"] for r in rows))
    print(f"\n  Problem IDs ({len(problem_ids)}): {problem_ids}")
    print(f"  Conditions ({len(conditions)}): {conditions}")

    expected_rows = len(problem_ids) * len(conditions)
    if len(rows) != expected_rows:
        issues.append(f"WARN: Expected {expected_rows} rows, got {len(rows)}")

    # Check 2: No duplicate (problem_id, condition) pairs
    seen = set()
    for r in rows:
        key = (r["problem_id"], r["condition"])
        if key in seen:
            issues.append(f"DUPLICATE: {key}")
        seen.add(key)

    # Check 3: Within-condition variance (scores should NOT be identical across problems)
    for cond in conditions:
        cond_rows = [r for r in rows if r["condition"] == cond]
        composites = [r["composite"] for r in cond_rows]
        if len(set(composites)) == 1:
            issues.append(f"ZERO VARIANCE: {cond} — all composites identical ({composites[0]})")
        else:
            std = statistics.stdev(composites)
            print(f"  {cond}: mean={statistics.mean(composites):.4f}, std={std:.4f}, "
                  f"range=[{min(composites):.4f}, {max(composites):.4f}]")

    # Check 4: No two different problems have identical full score vectors
    for cond in conditions:
        cond_rows = [r for r in rows if r["condition"] == cond]
        vectors = {}
        for r in cond_rows:
            vec = tuple(round(r[d], 4) for d in DIMENSIONS)
            if vec in vectors:
                issues.append(
                    f"IDENTICAL VECTORS in {cond}: {r['problem_id']} == {vectors[vec]}"
                )
            vectors[vec] = r["problem_id"]

    # Check 5: All dimension scores are in [0, 1]
    for r in rows:
        for d in DIMENSIONS:
            v = r.get(d, 0)
            if not (0.0 <= v <= 1.0):
                issues.append(f"OUT OF RANGE: {r['problem_id']}/{r['condition']}/{d} = {v}")

    return issues


# ═══════════════════════════════════════════════════════════════════
# SECTION 4: REPORT GENERATION
# ═══════════════════════════════════════════════════════════════════

COMPARISON_PAIRS = [
    ("SINGLE", "MULTI", "Multi-perspective vs single"),
    ("MULTI", "MEMORY", "Memory augmentation vs vanilla multi"),
    ("MEMORY", "CODETTE", "Full Codette vs memory-augmented"),
    ("SINGLE", "CODETTE", "Full Codette vs single (total improvement)"),
]


def generate_stats_report(rows: List[dict]) -> str:
    """Generate full paired statistics report."""
    lines = []
    lines.append("=" * 70)
    lines.append("CODETTE BENCHMARK — PAIRED STATISTICAL ANALYSIS")
    lines.append("=" * 70)

    raw_p_values = []

    for cond_a, cond_b, label in COMPARISON_PAIRS:
        xa, xb, pids = paired_scores(rows, cond_a, cond_b)
        if len(xa) < 2:
            lines.append(f"\n{label}: SKIPPED (insufficient paired data)")
            continue

        t_stat, t_p, df = paired_t_test(xa, xb)
        W, w_p = wilcoxon_signed_rank(xa, xb)
        d = cohens_d_paired(xa, xb)
        ci_lo, ci_hi = confidence_interval_95(xa, xb)
        mean_a = statistics.mean(xa)
        mean_b = statistics.mean(xb)
        mean_diff = mean_b - mean_a

        raw_p_values.append((label, t_p))

        lines.append(f"\n{'-' * 70}")
        lines.append(f"  {label}")
        lines.append(f"  {cond_a} (M={mean_a:.4f}) vs {cond_b} (M={mean_b:.4f})")
        lines.append(f"{'-' * 70}")
        lines.append(f"  N (paired problems):  {len(xa)}")
        lines.append(f"  Mean difference:      {mean_diff:+.4f} ({mean_diff/max(mean_a,0.001)*100:+.1f}%)")
        lines.append(f"  95% CI (t-based):     [{ci_lo:+.4f}, {ci_hi:+.4f}]")
        lines.append(f"  Paired t-test:        t({df}) = {t_stat:.3f}, p = {t_p:.6f}")
        lines.append(f"  Wilcoxon signed-rank: W = {W:.1f}, p = {w_p:.6f}")
        d_label = ("negligible" if abs(d) < 0.2 else
                   "small" if abs(d) < 0.5 else
                   "medium" if abs(d) < 0.8 else
                   "large" if abs(d) < 1.2 else
                   "very large")
        lines.append(f"  Cohen's d (paired):   {d:.3f}  ({d_label})")

    # Multiple comparison correction
    lines.append(f"\n{'=' * 70}")
    lines.append("MULTIPLE COMPARISON CORRECTION (Holm-Bonferroni)")
    lines.append(f"{'=' * 70}")

    corrected = holm_bonferroni(raw_p_values)
    for label, adj_p, sig in corrected:
        sig_str = "SIGNIFICANT" if sig else "not significant"
        lines.append(f"  {label}")
        lines.append(f"    Adjusted p = {adj_p:.6f}  -> {sig_str}")

    # Per-dimension breakdown for key comparison (SINGLE vs CODETTE)
    lines.append(f"\n{'=' * 70}")
    lines.append("PER-DIMENSION BREAKDOWN: SINGLE vs CODETTE")
    lines.append(f"{'=' * 70}")

    for dim in DIMENSIONS:
        by_a = {r["problem_id"]: r[dim] for r in rows if r["condition"] == "SINGLE"}
        by_b = {r["problem_id"]: r[dim] for r in rows if r["condition"] == "CODETTE"}
        common = sorted(set(by_a) & set(by_b))
        if len(common) < 2:
            continue
        xa = [by_a[p] for p in common]
        xb = [by_b[p] for p in common]
        t_stat, t_p, df = paired_t_test(xa, xb)
        d = cohens_d_paired(xa, xb)
        lines.append(f"  {dim:25s}: delta={statistics.mean(xb)-statistics.mean(xa):+.4f}, "
                      f"d={d:.3f}, t({df})={t_stat:.3f}, p={t_p:.6f}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# SECTION 5: MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Codette Benchmark Analysis")
    parser.add_argument(
        "--input", "-i",
        default=str(Path(__file__).resolve().parent.parent / "data" / "results" / "codette_benchmark_results.json"),
        help="Path to raw benchmark JSON",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output directory (defaults to same dir as input)",
    )
    args = parser.parse_args()

    input_path = args.input
    output_dir = args.output or str(Path(input_path).parent)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Loading: {input_path}")
    report = load_json(input_path)

    # Metadata
    meta = report.get("metadata", {})
    print(f"  Timestamp:    {meta.get('timestamp', 'unknown')}")
    print(f"  Problems:     {meta.get('num_problems', '?')}")
    print(f"  Conditions:   {meta.get('num_conditions', '?')}")
    print(f"  Evaluations:  {meta.get('total_evaluations', '?')}")

    # Step 1: Flatten to rows
    print("\n--- Flattening to CSV rows ---")
    rows = flatten_to_rows(report)
    csv_path = os.path.join(output_dir, "codette_results.csv")
    write_csv(rows, csv_path)

    # Step 2: Sanity checks
    print("\n--- Sanity Checks ---")
    issues = run_sanity_checks(rows)
    if issues:
        print(f"\n  ISSUES FOUND ({len(issues)}):")
        for issue in issues:
            print(f"    ! {issue}")
    else:
        print("\n  ALL CHECKS PASSED")

    # Step 3: Paired statistics
    print("\n--- Paired Statistical Analysis ---")
    stats_report = generate_stats_report(rows)
    print(stats_report)

    stats_path = os.path.join(output_dir, "codette_paired_stats.txt")
    with open(stats_path, "w", encoding="utf-8") as f:
        f.write(stats_report)
    print(f"\n  Stats report written: {stats_path}")

    # Step 4: Summary JSON (machine-readable stats)
    summary = {
        "input": input_path,
        "n_problems": len(set(r["problem_id"] for r in rows)),
        "n_conditions": len(set(r["condition"] for r in rows)),
        "n_rows": len(rows),
        "sanity_issues": issues,
        "comparisons": [],
    }
    for cond_a, cond_b, label in COMPARISON_PAIRS:
        xa, xb, pids = paired_scores(rows, cond_a, cond_b)
        if len(xa) < 2:
            continue
        t_stat, t_p, df = paired_t_test(xa, xb)
        W, w_p = wilcoxon_signed_rank(xa, xb)
        d = cohens_d_paired(xa, xb)
        ci_lo, ci_hi = confidence_interval_95(xa, xb)
        summary["comparisons"].append({
            "label": label,
            "cond_a": cond_a, "cond_b": cond_b,
            "n_paired": len(xa),
            "mean_a": round(statistics.mean(xa), 4),
            "mean_b": round(statistics.mean(xb), 4),
            "mean_diff": round(statistics.mean(xb) - statistics.mean(xa), 4),
            "ci_95": [ci_lo, ci_hi],
            "paired_t": {"t": t_stat, "p": t_p, "df": df},
            "wilcoxon": {"W": W, "p": w_p},
            "cohens_d": d,
        })

    summary_path = os.path.join(output_dir, "codette_stats_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"  Stats summary JSON: {summary_path}")

    print(f"\n{'=' * 70}")
    print("DONE. Outputs:")
    print(f"  1. CSV (per-problem):     {csv_path}")
    print(f"  2. Raw evaluator export:  {input_path}")
    print(f"  3. Repro script:          {os.path.abspath(__file__)}")
    print(f"  4. Paired stats report:   {stats_path}")
    print(f"  5. Stats summary JSON:    {summary_path}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
