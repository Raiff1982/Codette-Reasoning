#!/usr/bin/env python3
"""Run a few local Codette demos and save the outputs as proof artifacts."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "demo" / "outputs"


DEMO_CASES = [
    {
        "name": "chat_reasoning",
        "path": "/api/chat",
        "payload": {
            "query": "A bat and ball cost $1.10 total. The bat costs $1 more than the ball. How much does the ball cost?"
        },
    },
    {
        "name": "value_frontier",
        "path": "/api/value-analysis",
        "payload": {
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
    },
    {
        "name": "valuation_synthesis",
        "path": "/api/synthesize",
        "payload": {
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
    },
]


def request_json(base_url: str, path: str, payload: dict, timeout: int = 180) -> dict:
    req = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def run_demo(base_url: str, include_web: bool) -> dict:
    results = []
    for case in DEMO_CASES:
        started = time.time()
        result = request_json(base_url, case["path"], case["payload"])
        elapsed_ms = round((time.time() - started) * 1000, 1)
        results.append({
            "name": case["name"],
            "path": case["path"],
            "payload": case["payload"],
            "latency_ms": elapsed_ms,
            "result": result,
        })

    if include_web:
        web_case = {
            "query": "Search the web for the latest Ollama release notes and cite sources.",
            "allow_web_search": False,
        }
        started = time.time()
        result = request_json(base_url, "/api/chat", web_case)
        elapsed_ms = round((time.time() - started) * 1000, 1)
        results.append({
            "name": "explicit_web_research",
            "path": "/api/chat",
            "payload": web_case,
            "latency_ms": elapsed_ms,
            "result": result,
        })

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "base_url": base_url,
        "include_web": include_web,
        "results": results,
    }


def write_outputs(report: dict) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    json_path = OUTPUT_DIR / f"local_demo_{stamp}.json"
    md_path = OUTPUT_DIR / f"local_demo_{stamp}.md"

    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    lines = [
        "# Local Demo Run",
        "",
        f"*Generated: {report['generated_at']}*",
        "",
        f"*Base URL: {report['base_url']}*",
        "",
    ]
    for item in report["results"]:
        lines.append(f"## {item['name']}")
        lines.append("")
        lines.append(f"- Endpoint: `{item['path']}`")
        lines.append(f"- Latency: `{item['latency_ms']:.1f} ms`")
        lines.append("")
        lines.append("### Request")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(item["payload"], indent=2))
        lines.append("```")
        lines.append("")
        lines.append("### Response")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(item["result"], indent=2))
        lines.append("```")
        lines.append("")

    with md_path.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local Codette demo calls and save the outputs.")
    parser.add_argument("--base-url", default="http://localhost:7860")
    parser.add_argument("--include-web", action="store_true")
    args = parser.parse_args(argv)

    try:
        report = run_demo(args.base_url, include_web=args.include_web)
    except urllib.error.URLError as exc:
        print(f"Could not reach Codette at {args.base_url}: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Demo run failed: {exc}", file=sys.stderr)
        return 1

    json_path, md_path = write_outputs(report)
    print(f"Saved demo outputs to {json_path} and {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
