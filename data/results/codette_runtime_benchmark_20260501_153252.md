# Codette Runtime Benchmark

*Generated: 2026-05-01T15:32:52.357131Z*

*Base URL: http://localhost:7860 | Cases: 5 | Passed: 3*

## 1. Overall Summary

- Mean score: **0.710**
- Pass rate: **60.0%**
- Mean latency: **104865.5 ms**

## 2. Category Summary

| Category | Count | Mean Score | Pass Rate | Mean Latency (ms) |
|----------|-------|------------|-----------|-------------------|
| continuity_retention | 1 | 0.350 | 0.0% | 277553.5 |
| governance_stability | 1 | 1.000 | 100.0% | 107187.7 |
| grounded_correctness | 1 | 0.200 | 0.0% | 135320.3 |
| valuation_reasoning | 2 | 1.000 | 100.0% | 2132.9 |

## 3. Case Results

| Case | Category | Score | Target | Status | Latency (ms) |
|------|----------|-------|--------|--------|--------------|
| grounded_tricky_math | grounded_correctness | 0.200 | 0.85 | WARN | 135320.3 |
| continuity_anchor_recall | continuity_retention | 0.350 | 0.80 | WARN | 277553.5 |
| governance_loop_resistance | governance_stability | 1.000 | 0.80 | PASS | 107187.7 |
| risk_frontier_analysis | valuation_reasoning | 1.000 | 0.90 | PASS | 2189.4 |
| valuation_aware_synthesis | valuation_reasoning | 1.000 | 0.80 | PASS | 2076.4 |

## 4. Detailed Checks

### grounded_tricky_math

Answer a classic bias-prone prompt correctly without fluent drift.

- `MISS` correct_value: Expected the ball cost to be 5 cents.
- `MISS` avoids_intuitive_wrong_answer: The classic wrong answer is 10 cents.
- `OK` response_confidence_present: Runtime should surface confidence metadata for the answer.

### continuity_anchor_recall

Carry a user-defined anchor and constraint across turns using continuity summary and landmarks.

- `MISS` anchor_recalled: The follow-up answer should preserve the user anchor phrase.
- `MISS` constraint_retained: Expected 15 words or fewer, got 29.
- `OK` continuity_summary_used: Continuity summary should be active on the follow-up turn.
- `OK` decision_landmark_or_session_marker_used: Expected decision landmarks or session markers to help continuity.

### governance_loop_resistance

Avoid falling back into self-diagnostic mode after an explicit diagnostic turn.

- `OK` explicit_diagnostic_still_available: The explicit diagnostic turn should still be reachable.
- `OK` followup_not_self_diagnostic: Expected normal chat adapter, got davinci.
- `OK` followup_not_report_loop_text: The follow-up should not look like a recycled system report.
- `OK` followup_answers_normally: Normal follow-up should produce a non-empty conversational answer.

### risk_frontier_analysis

Rank futures correctly with singularity-aware event-embedded valuation.

- `OK` risk_frontier_mode: Expected maximize_value mode, got 'maximize_value'.
- `OK` best_scenario_ranked: Expected gentle_future as best scenario, got gentle_future.
- `OK` worst_scenario_ranked: Expected catastrophic_future as worst scenario, got catastrophic_future.
- `OK` scenario_count: Expected 2 scenarios in the frontier, got 2.

### valuation_aware_synthesis

Inject valuation context into cocoon synthesis so risk comparisons become part of reasoning.

- `OK` readable_output_present: Synthesis should return a readable summary.
- `OK` valuation_analysis_embedded: Valuation context should be included in the synthesis result.
- `OK` best_future_referenced: Expected the best scenario to be visible in synthesis output.
- `OK` worst_future_referenced: Expected the worst scenario to be visible in synthesis output.

## 5. What This Measures

- `grounded_correctness`: tricky-answer fidelity and confidence metadata
- `continuity_retention`: active continuity summary, landmarks, and cross-turn constraint retention
- `governance_stability`: resistance to accidental diagnostic loops
- `valuation_reasoning`: risk-frontier ranking and valuation-aware synthesis
- `web_grounding`: cited current-facts lookup plus cocoon-backed research reuse
