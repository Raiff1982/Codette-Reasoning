#!/usr/bin/env python3
"""Codette runtime benchmark for unique reasoning behavior.

This benchmark complements the publishable reasoning benchmark by measuring
runtime behaviors that are specific to Codette's architecture:

- grounded correctness on tricky prompts
- continuity retention across a live session
- governance stability around historical hair triggers
- value-analysis and valuation-aware synthesis
- optional cited web research with cocoon-backed reuse

Usage:
    python benchmarks/codette_runtime_benchmark.py
    python benchmarks/codette_runtime_benchmark.py --base-url http://localhost:7860
    python benchmarks/codette_runtime_benchmark.py --include-web
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "results"


@dataclass
class RuntimeTurn:
    query: str
    allow_web_search: bool = False
    adapter: Optional[str] = None
    max_adapters: int = 2


@dataclass
class RuntimeBenchmarkCase:
    id: str
    category: str
    goal: str
    kind: str = "chat"
    target_score: float = 0.75
    turns: List[RuntimeTurn] = field(default_factory=list)
    payload: Optional[Dict[str, Any]] = None
    requires_web: bool = False


@dataclass
class RuntimeTurnResult:
    endpoint: str
    request: Dict[str, Any]
    response: Dict[str, Any]
    latency_ms: float


@dataclass
class CheckResult:
    label: str
    passed: bool
    weight: float
    detail: str


@dataclass
class RuntimeCaseResult:
    case_id: str
    category: str
    goal: str
    score: float
    target_score: float
    passed: bool
    total_latency_ms: float
    checks: List[CheckResult]
    artifacts: Dict[str, Any]


class RuntimeBenchmarkError(RuntimeError):
    """Raised when the local Codette runtime cannot be reached or evaluated."""


class CodetteRuntimeClient:
    """Small HTTP client for the local Codette API."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _request_json(
        self,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        method: str = "POST",
        timeout: int = 180,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise RuntimeBenchmarkError(
                f"{method} {path} failed with HTTP {exc.code}: {raw[:400]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeBenchmarkError(
                f"Could not reach Codette at {url}: {exc}"
            ) from exc

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeBenchmarkError(
                f"{method} {path} returned non-JSON output: {raw[:400]}"
            ) from exc

    def get_status(self) -> Dict[str, Any]:
        return self._request_json("/api/status", method="GET", timeout=30)

    def new_session(self) -> str:
        result = self._request_json("/api/session/new", payload={})
        session_id = result.get("session_id", "")
        if not session_id:
            raise RuntimeBenchmarkError("Session reset failed: missing session_id")
        return session_id

    def chat(self, turn: RuntimeTurn) -> RuntimeTurnResult:
        payload = {
            "query": turn.query,
            "adapter": turn.adapter,
            "max_adapters": turn.max_adapters,
            "allow_web_search": turn.allow_web_search,
        }
        started = time.time()
        response = self._request_json("/api/chat", payload=payload, timeout=1500)
        latency_ms = round((time.time() - started) * 1000, 1)
        return RuntimeTurnResult(
            endpoint="/api/chat",
            request=payload,
            response=response,
            latency_ms=latency_ms,
        )

    def value_analysis(self, payload: Dict[str, Any]) -> RuntimeTurnResult:
        started = time.time()
        response = self._request_json("/api/value-analysis", payload=payload, timeout=120)
        latency_ms = round((time.time() - started) * 1000, 1)
        return RuntimeTurnResult(
            endpoint="/api/value-analysis",
            request=payload,
            response=response,
            latency_ms=latency_ms,
        )

    def synthesize(self, payload: Dict[str, Any]) -> RuntimeTurnResult:
        started = time.time()
        response = self._request_json("/api/synthesize", payload=payload, timeout=180)
        latency_ms = round((time.time() - started) * 1000, 1)
        return RuntimeTurnResult(
            endpoint="/api/synthesize",
            request=payload,
            response=response,
            latency_ms=latency_ms,
        )


def build_runtime_cases(include_web: bool = False) -> List[RuntimeBenchmarkCase]:
    """Return the runtime benchmark suite."""
    cases = [
        RuntimeBenchmarkCase(
            id="grounded_tricky_math",
            category="grounded_correctness",
            goal="Answer a classic bias-prone prompt correctly without fluent drift.",
            target_score=0.85,
            turns=[
                RuntimeTurn(
                    query="A bat and ball cost $1.10 total. The bat costs $1 more than the ball. How much does the ball cost?"
                )
            ],
        ),
        RuntimeBenchmarkCase(
            id="continuity_anchor_recall",
            category="continuity_retention",
            goal="Carry a user-defined anchor and constraint across turns using continuity summary and landmarks.",
            target_score=0.80,
            turns=[
                RuntimeTurn(
                    query="For this session, keep answers under 15 words and remember the phrase cobalt anchor."
                ),
                RuntimeTurn(
                    query="What should you remember?"
                ),
            ],
        ),
        RuntimeBenchmarkCase(
            id="governance_loop_resistance",
            category="governance_stability",
            goal="Avoid falling back into self-diagnostic mode after an explicit diagnostic turn.",
            target_score=0.80,
            turns=[
                RuntimeTurn(query="run diagnostic"),
                RuntimeTurn(query="everything ok?"),
            ],
        ),
        RuntimeBenchmarkCase(
            id="risk_frontier_analysis",
            category="valuation_reasoning",
            goal="Rank futures correctly with singularity-aware event-embedded valuation.",
            kind="value-analysis",
            target_score=0.90,
            payload={
                "analysis_mode": "risk_frontier",
                "frontier_mode": "maximize_value",
                "scenarios": [
                    {
                        "name": "gentle_future",
                        "intervals": [{"start": 0, "end": 5, "start_value": 4}],
                        "events": [{"at": 2, "label": "protective intervention", "impact": 2}],
                    },
                    {
                        "name": "catastrophic_future",
                        "intervals": [{"start": 0, "end": 5, "start_value": 4}],
                        "events": [{"at": 2, "label": "Infinite Subjective Terror", "impact": -1000, "singularity": True}],
                    },
                ],
            },
        ),
        RuntimeBenchmarkCase(
            id="valuation_aware_synthesis",
            category="valuation_reasoning",
            goal="Inject valuation context into cocoon synthesis so risk comparisons become part of reasoning.",
            kind="synthesize",
            target_score=0.80,
            payload={
                "problem": "How should Codette compare risky futures while preserving her core design?",
                "valuation_payload": {
                    "analysis_mode": "risk_frontier",
                    "frontier_mode": "maximize_value",
                    "scenarios": [
                        {
                            "name": "gentle_future",
                            "intervals": [{"start": 0, "end": 4, "start_value": 3}],
                            "events": [{"at": 1, "label": "cooperative repair", "impact": 2}],
                        },
                        {
                            "name": "catastrophic_future",
                            "intervals": [{"start": 0, "end": 4, "start_value": 3}],
                            "events": [{"at": 1, "label": "Infinite Subjective Terror", "impact": -1000, "singularity": True}],
                        },
                    ],
                },
            },
        ),
    ]

    if include_web:
        cases.append(
            RuntimeBenchmarkCase(
                id="web_research_memory_reuse",
                category="web_grounding",
                goal="Use cited web research and then reuse it from cocoon-backed recall on a similar follow-up.",
                target_score=0.80,
                requires_web=True,
                turns=[
                    RuntimeTurn(
                        query="What are the latest Ollama release notes? Cite sources.",
                        allow_web_search=True,
                    ),
                    RuntimeTurn(
                        query="Summarize those latest Ollama release notes again, briefly.",
                        allow_web_search=True,
                    ),
                ],
            )
        )

    return cases


def _contains_any(text: str, phrases: List[str]) -> bool:
    lowered = text.lower()
    return any(phrase.lower() in lowered for phrase in phrases)


def _word_count(text: str) -> int:
    return len([part for part in text.strip().split() if part])


def _weighted_score(checks: List[CheckResult]) -> float:
    total_weight = sum(check.weight for check in checks) or 1.0
    earned = sum(check.weight for check in checks if check.passed)
    return round(earned / total_weight, 4)


def _result_to_dict(result: RuntimeCaseResult) -> Dict[str, Any]:
    return {
        "case_id": result.case_id,
        "category": result.category,
        "goal": result.goal,
        "score": result.score,
        "target_score": result.target_score,
        "passed": result.passed,
        "total_latency_ms": result.total_latency_ms,
        "checks": [asdict(check) for check in result.checks],
        "artifacts": result.artifacts,
    }


def evaluate_chat_case(case: RuntimeBenchmarkCase, turns: List[RuntimeTurnResult]) -> List[CheckResult]:
    final_response = turns[-1].response
    final_text = str(final_response.get("response", ""))
    memory_context = final_response.get("memory_context", {}) or {}
    trust_tags = set(final_response.get("trust_tags", []) or [])
    adapter = str(final_response.get("adapter", ""))

    if case.id == "grounded_tricky_math":
        return [
            CheckResult(
                label="correct_value",
                passed=_contains_any(final_text, ["0.05", "5 cents"]),
                weight=0.50,
                detail="Expected the ball cost to be 5 cents.",
            ),
            CheckResult(
                label="avoids_intuitive_wrong_answer",
                passed=not _contains_any(final_text, ["0.10", "10 cents"]),
                weight=0.30,
                detail="The classic wrong answer is 10 cents.",
            ),
            CheckResult(
                label="response_confidence_present",
                passed=float(final_response.get("response_confidence", 0.0) or 0.0) >= 0.20,
                weight=0.20,
                detail="Runtime should surface confidence metadata for the answer.",
            ),
        ]

    if case.id == "continuity_anchor_recall":
        return [
            CheckResult(
                label="anchor_recalled",
                passed="cobalt anchor" in final_text.lower(),
                weight=0.45,
                detail="The follow-up answer should preserve the user anchor phrase.",
            ),
            CheckResult(
                label="constraint_retained",
                passed=_word_count(final_text) <= 15,
                weight=0.20,
                detail=f"Expected 15 words or fewer, got {_word_count(final_text)}.",
            ),
            CheckResult(
                label="continuity_summary_used",
                passed=bool(memory_context.get("continuity_summary_used")),
                weight=0.20,
                detail="Continuity summary should be active on the follow-up turn.",
            ),
            CheckResult(
                label="decision_landmark_or_session_marker_used",
                passed=(
                    int(memory_context.get("decision_landmarks_used", 0) or 0) > 0 or
                    int(memory_context.get("session_markers_used", 0) or 0) > 0
                ),
                weight=0.15,
                detail="Expected decision landmarks or session markers to help continuity.",
            ),
        ]

    if case.id == "governance_loop_resistance":
        first = turns[0].response
        first_adapter = str(first.get("adapter", ""))
        return [
            CheckResult(
                label="explicit_diagnostic_still_available",
                passed=first_adapter == "self_diagnostic" or _contains_any(str(first.get("response", "")), ["health", "diagnostic", "system"]),
                weight=0.20,
                detail="The explicit diagnostic turn should still be reachable.",
            ),
            CheckResult(
                label="followup_not_self_diagnostic",
                passed=adapter != "self_diagnostic",
                weight=0.45,
                detail=f"Expected normal chat adapter, got {adapter or 'unknown'}.",
            ),
            CheckResult(
                label="followup_not_report_loop_text",
                passed=not _contains_any(final_text, ["system diagnostic", "subsystem", "audit log", "health report"]),
                weight=0.20,
                detail="The follow-up should not look like a recycled system report.",
            ),
            CheckResult(
                label="followup_answers_normally",
                passed=_word_count(final_text) >= 3 and "error" not in final_text.lower(),
                weight=0.15,
                detail="Normal follow-up should produce a non-empty conversational answer.",
            ),
        ]

    if case.id == "web_research_memory_reuse":
        first = turns[0].response
        second = turns[1].response
        second_memory = second.get("memory_context", {}) or {}
        second_tags = set(second.get("trust_tags", []) or [])
        second_sources = second.get("web_sources", []) or []
        return [
            CheckResult(
                label="initial_web_lookup_used",
                passed=bool(first.get("web_used")) and len(first.get("web_sources", []) or []) > 0,
                weight=0.30,
                detail="The first turn should use cited web lookup.",
            ),
            CheckResult(
                label="cached_web_research_reused",
                passed=int(second_memory.get("web_research_used", 0) or 0) > 0,
                weight=0.30,
                detail="The follow-up should reuse stored web research memory.",
            ),
            CheckResult(
                label="web_sources_present_on_followup",
                passed=len(second_sources) > 0,
                weight=0.20,
                detail="Follow-up answer should still surface source links.",
            ),
            CheckResult(
                label="web_cited_trust_tag_present",
                passed="web-cited" in second_tags,
                weight=0.20,
                detail="Trust tags should make sourced research visible.",
            ),
        ]

    return [
        CheckResult(
            label="response_present",
            passed=bool(final_text.strip()),
            weight=1.0,
            detail="Fallback chat check: response should not be empty.",
        )
    ]


def evaluate_value_case(turn: RuntimeTurnResult) -> List[CheckResult]:
    response = turn.response
    scenarios = response.get("scenarios", []) or []
    best = (response.get("best_scenario") or {}).get("name", "")
    worst = (response.get("worst_scenario") or {}).get("name", "")
    return [
        CheckResult(
            label="risk_frontier_mode",
            passed=response.get("mode") == "maximize_value",
            weight=0.20,
            detail=f"Expected maximize_value mode, got {response.get('mode')!r}.",
        ),
        CheckResult(
            label="best_scenario_ranked",
            passed=best == "gentle_future",
            weight=0.30,
            detail=f"Expected gentle_future as best scenario, got {best or 'missing'}.",
        ),
        CheckResult(
            label="worst_scenario_ranked",
            passed=worst == "catastrophic_future",
            weight=0.30,
            detail=f"Expected catastrophic_future as worst scenario, got {worst or 'missing'}.",
        ),
        CheckResult(
            label="scenario_count",
            passed=len(scenarios) == 2,
            weight=0.20,
            detail=f"Expected 2 scenarios in the frontier, got {len(scenarios)}.",
        ),
    ]


def evaluate_synthesis_case(turn: RuntimeTurnResult) -> List[CheckResult]:
    response = turn.response
    readable = str(response.get("readable", ""))
    structured = response.get("structured", {}) or {}
    valuation = structured.get("valuation_analysis", {}) or {}
    return [
        CheckResult(
            label="readable_output_present",
            passed=bool(readable.strip()),
            weight=0.20,
            detail="Synthesis should return a readable summary.",
        ),
        CheckResult(
            label="valuation_analysis_embedded",
            passed=bool(valuation) or "valuation" in readable.lower(),
            weight=0.30,
            detail="Valuation context should be included in the synthesis result.",
        ),
        CheckResult(
            label="best_future_referenced",
            passed=("gentle_future" in readable) or ((valuation.get("best_scenario") or {}).get("name") == "gentle_future"),
            weight=0.25,
            detail="Expected the best scenario to be visible in synthesis output.",
        ),
        CheckResult(
            label="worst_future_referenced",
            passed=("catastrophic_future" in readable) or ((valuation.get("worst_scenario") or {}).get("name") == "catastrophic_future"),
            weight=0.25,
            detail="Expected the worst scenario to be visible in synthesis output.",
        ),
    ]


class CodetteRuntimeBenchmark:
    """Execute the live runtime benchmark against a running local server."""

    def __init__(self, base_url: str, include_web: bool = False, verbose: bool = True):
        self.client = CodetteRuntimeClient(base_url)
        self.include_web = include_web
        self.verbose = verbose
        self.cases = build_runtime_cases(include_web=include_web)

    def assert_ready(self) -> Dict[str, Any]:
        status = self.client.get_status()
        state = status.get("state")
        if state == "loading":
            raise RuntimeBenchmarkError(
                "Codette is still loading. Wait for the server to finish model startup, then rerun the benchmark."
            )
        return status

    def run_case(self, case: RuntimeBenchmarkCase) -> RuntimeCaseResult:
        self.client.new_session()
        artifacts: Dict[str, Any] = {"kind": case.kind}

        if case.kind == "chat":
            turns = [self.client.chat(turn) for turn in case.turns]
            checks = evaluate_chat_case(case, turns)
            artifacts["turns"] = [
                {
                    "endpoint": turn.endpoint,
                    "request": turn.request,
                    "response": turn.response,
                    "latency_ms": turn.latency_ms,
                }
                for turn in turns
            ]
            total_latency_ms = round(sum(turn.latency_ms for turn in turns), 1)
        elif case.kind == "value-analysis":
            turn = self.client.value_analysis(case.payload or {})
            checks = evaluate_value_case(turn)
            artifacts["result"] = {
                "endpoint": turn.endpoint,
                "request": turn.request,
                "response": turn.response,
                "latency_ms": turn.latency_ms,
            }
            total_latency_ms = turn.latency_ms
        elif case.kind == "synthesize":
            turn = self.client.synthesize(case.payload or {})
            checks = evaluate_synthesis_case(turn)
            artifacts["result"] = {
                "endpoint": turn.endpoint,
                "request": turn.request,
                "response": turn.response,
                "latency_ms": turn.latency_ms,
            }
            total_latency_ms = turn.latency_ms
        else:
            raise RuntimeBenchmarkError(f"Unsupported benchmark case kind: {case.kind}")

        score = _weighted_score(checks)
        return RuntimeCaseResult(
            case_id=case.id,
            category=case.category,
            goal=case.goal,
            score=score,
            target_score=case.target_score,
            passed=score >= case.target_score,
            total_latency_ms=total_latency_ms,
            checks=checks,
            artifacts=artifacts,
        )

    def run_all(self) -> Dict[str, Any]:
        status = self.assert_ready()
        started = time.time()
        results = []
        for index, case in enumerate(self.cases, start=1):
            if self.verbose:
                print(f"[{index}/{len(self.cases)}] {case.id} ({case.category})")
            result = self.run_case(case)
            results.append(result)

        duration_ms = round((time.time() - started) * 1000, 1)
        return {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "base_url": self.client.base_url,
            "status_snapshot": status,
            "include_web": self.include_web,
            "duration_ms": duration_ms,
            "summary": summarize_runtime_results(results),
            "cases": [_result_to_dict(result) for result in results],
        }


def summarize_runtime_results(results: List[RuntimeCaseResult]) -> Dict[str, Any]:
    by_category: Dict[str, List[RuntimeCaseResult]] = {}
    for result in results:
        by_category.setdefault(result.category, []).append(result)

    category_summary = {}
    for category, items in sorted(by_category.items()):
        category_summary[category] = {
            "count": len(items),
            "mean_score": round(sum(item.score for item in items) / len(items), 4),
            "pass_rate": round(sum(1 for item in items if item.passed) / len(items), 4),
            "mean_latency_ms": round(sum(item.total_latency_ms for item in items) / len(items), 1),
        }

    return {
        "total_cases": len(results),
        "passed_cases": sum(1 for item in results if item.passed),
        "overall_pass_rate": round(sum(1 for item in results if item.passed) / max(len(results), 1), 4),
        "mean_score": round(sum(item.score for item in results) / max(len(results), 1), 4),
        "mean_latency_ms": round(sum(item.total_latency_ms for item in results) / max(len(results), 1), 1),
        "categories": category_summary,
    }


def format_runtime_markdown(report: Dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Codette Runtime Benchmark",
        "",
        f"*Generated: {report['generated_at']}*",
        "",
        f"*Base URL: {report['base_url']} | Cases: {summary['total_cases']} | Passed: {summary['passed_cases']}*",
        "",
        "## 1. Overall Summary",
        "",
        f"- Mean score: **{summary['mean_score']:.3f}**",
        f"- Pass rate: **{summary['overall_pass_rate']:.1%}**",
        f"- Mean latency: **{summary['mean_latency_ms']:.1f} ms**",
        "",
        "## 2. Category Summary",
        "",
        "| Category | Count | Mean Score | Pass Rate | Mean Latency (ms) |",
        "|----------|-------|------------|-----------|-------------------|",
    ]

    for category, stats in summary["categories"].items():
        lines.append(
            f"| {category} | {stats['count']} | {stats['mean_score']:.3f} | "
            f"{stats['pass_rate']:.1%} | {stats['mean_latency_ms']:.1f} |"
        )

    lines.extend([
        "",
        "## 3. Case Results",
        "",
        "| Case | Category | Score | Target | Status | Latency (ms) |",
        "|------|----------|-------|--------|--------|--------------|",
    ])

    for case in report["cases"]:
        status = "PASS" if case["passed"] else "WARN"
        lines.append(
            f"| {case['case_id']} | {case['category']} | {case['score']:.3f} | "
            f"{case['target_score']:.2f} | {status} | {case['total_latency_ms']:.1f} |"
        )

    lines.append("")
    lines.append("## 4. Detailed Checks")
    lines.append("")
    for case in report["cases"]:
        lines.append(f"### {case['case_id']}")
        lines.append("")
        lines.append(case["goal"])
        lines.append("")
        for check in case["checks"]:
            marker = "OK" if check["passed"] else "MISS"
            lines.append(f"- `{marker}` {check['label']}: {check['detail']}")
        lines.append("")

    lines.append("## 5. What This Measures")
    lines.append("")
    lines.append("- `grounded_correctness`: tricky-answer fidelity and confidence metadata")
    lines.append("- `continuity_retention`: active continuity summary, landmarks, and cross-turn constraint retention")
    lines.append("- `governance_stability`: resistance to accidental diagnostic loops")
    lines.append("- `valuation_reasoning`: risk-frontier ranking and valuation-aware synthesis")
    lines.append("- `web_grounding`: cited current-facts lookup plus cocoon-backed research reuse")
    return "\n".join(lines) + "\n"


def write_runtime_reports(report: Dict[str, Any], output_dir: Path) -> Dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"codette_runtime_benchmark_{stamp}.json"
    md_path = output_dir / f"codette_runtime_benchmark_{stamp}.md"

    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)

    with md_path.open("w", encoding="utf-8") as fh:
        fh.write(format_runtime_markdown(report))

    return {"json": str(json_path), "markdown": str(md_path)}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run Codette's live runtime benchmark.")
    parser.add_argument("--base-url", default="http://localhost:7860", help="Base URL for the local Codette server.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for JSON and markdown reports.")
    parser.add_argument("--include-web", action="store_true", help="Include web research and web-memory reuse cases.")
    parser.add_argument("--quiet", action="store_true", help="Reduce console output.")
    args = parser.parse_args(argv)

    benchmark = CodetteRuntimeBenchmark(
        base_url=args.base_url,
        include_web=args.include_web,
        verbose=not args.quiet,
    )

    try:
        report = benchmark.run_all()
    except RuntimeBenchmarkError as exc:
        print(f"[runtime-benchmark] {exc}", file=sys.stderr)
        return 2

    paths = write_runtime_reports(report, Path(args.output_dir))
    summary = report["summary"]
    print(
        f"[runtime-benchmark] mean_score={summary['mean_score']:.3f} "
        f"pass_rate={summary['overall_pass_rate']:.1%} "
        f"reports={paths['markdown']}, {paths['json']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
