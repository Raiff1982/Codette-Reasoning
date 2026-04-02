import unittest

from benchmarks.codette_runtime_benchmark import (
    CheckResult,
    RuntimeBenchmarkCase,
    RuntimeTurn,
    RuntimeTurnResult,
    _weighted_score,
    build_runtime_cases,
    evaluate_chat_case,
    evaluate_synthesis_case,
    evaluate_value_case,
    format_runtime_markdown,
    summarize_runtime_results,
)


class TestCodetteRuntimeBenchmarkHelpers(unittest.TestCase):
    def test_build_runtime_cases_includes_web_only_when_requested(self):
        default_cases = build_runtime_cases(include_web=False)
        web_cases = build_runtime_cases(include_web=True)

        self.assertFalse(any(case.requires_web for case in default_cases))
        self.assertTrue(any(case.requires_web for case in web_cases))
        self.assertGreater(len(web_cases), len(default_cases))

    def test_weighted_score_uses_check_weights(self):
        score = _weighted_score([
            CheckResult(label="a", passed=True, weight=0.7, detail=""),
            CheckResult(label="b", passed=False, weight=0.3, detail=""),
        ])
        self.assertAlmostEqual(score, 0.7)

    def test_continuity_case_rewards_anchor_and_memory_context(self):
        case = next(case for case in build_runtime_cases() if case.id == "continuity_anchor_recall")
        turns = [
            RuntimeTurnResult(
                endpoint="/api/chat",
                request={"query": case.turns[0].query},
                response={"response": "I will remember cobalt anchor."},
                latency_ms=10.0,
            ),
            RuntimeTurnResult(
                endpoint="/api/chat",
                request={"query": case.turns[1].query},
                response={
                    "response": "Cobalt anchor, under fifteen words.",
                    "memory_context": {
                        "continuity_summary_used": True,
                        "decision_landmarks_used": 1,
                        "session_markers_used": 0,
                    },
                    "trust_tags": ["memory-backed"],
                },
                latency_ms=15.0,
            ),
        ]

        checks = evaluate_chat_case(case, turns)
        self.assertTrue(all(check.passed for check in checks))

    def test_governance_case_rejects_self_diagnostic_followup(self):
        case = next(case for case in build_runtime_cases() if case.id == "governance_loop_resistance")
        turns = [
            RuntimeTurnResult(
                endpoint="/api/chat",
                request={"query": case.turns[0].query},
                response={"response": "Diagnostic complete.", "adapter": "self_diagnostic"},
                latency_ms=20.0,
            ),
            RuntimeTurnResult(
                endpoint="/api/chat",
                request={"query": case.turns[1].query},
                response={"response": "Yes, I am okay and ready to keep going.", "adapter": "empathy"},
                latency_ms=12.0,
            ),
        ]

        checks = evaluate_chat_case(case, turns)
        passed = {check.label: check.passed for check in checks}
        self.assertTrue(passed["explicit_diagnostic_still_available"])
        self.assertTrue(passed["followup_not_self_diagnostic"])
        self.assertTrue(passed["followup_not_report_loop_text"])

    def test_value_case_scores_best_and_worst_scenarios(self):
        turn = RuntimeTurnResult(
            endpoint="/api/value-analysis",
            request={},
            response={
                "mode": "maximize_value",
                "best_scenario": {"name": "gentle_future"},
                "worst_scenario": {"name": "catastrophic_future"},
                "scenarios": [{"name": "gentle_future"}, {"name": "catastrophic_future"}],
            },
            latency_ms=5.0,
        )
        checks = evaluate_value_case(turn)
        self.assertTrue(all(check.passed for check in checks))

    def test_synthesis_case_detects_valuation_context(self):
        turn = RuntimeTurnResult(
            endpoint="/api/synthesize",
            request={},
            response={
                "readable": "The valuation layer favors gentle_future and rejects catastrophic_future.",
                "structured": {
                    "valuation_analysis": {
                        "best_scenario": {"name": "gentle_future"},
                        "worst_scenario": {"name": "catastrophic_future"},
                    }
                },
            },
            latency_ms=7.0,
        )
        checks = evaluate_synthesis_case(turn)
        self.assertTrue(all(check.passed for check in checks))

    def test_markdown_report_renders_runtime_summary(self):
        case = RuntimeBenchmarkCase(
            id="demo",
            category="continuity_retention",
            goal="Demo goal",
            turns=[RuntimeTurn(query="hello")],
        )
        result = {
            "generated_at": "2026-04-02T12:00:00Z",
            "base_url": "http://localhost:7860",
            "summary": summarize_runtime_results([
                type(
                    "CaseResult",
                    (),
                    {
                        "case_id": case.id,
                        "category": case.category,
                        "goal": case.goal,
                        "score": 0.9,
                        "target_score": 0.75,
                        "passed": True,
                        "total_latency_ms": 10.0,
                    },
                )()
            ]),
            "cases": [
                {
                    "case_id": case.id,
                    "category": case.category,
                    "goal": case.goal,
                    "score": 0.9,
                    "target_score": 0.75,
                    "passed": True,
                    "total_latency_ms": 10.0,
                    "checks": [{"label": "anchor_recalled", "passed": True, "detail": "demo"}],
                }
            ],
        }
        markdown = format_runtime_markdown(result)
        self.assertIn("Codette Runtime Benchmark", markdown)
        self.assertIn("continuity_retention", markdown)
        self.assertIn("anchor_recalled", markdown)
