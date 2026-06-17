#!/usr/bin/env python3
"""
Behavioral verification for the 7 non-empathy perspective adapters.

Tests each adapter with targeted prompts and checks for template-filler
contamination from train_hf_job_v4.py's _generate_answer() patterns.

Pass/fail per adapter. Run with server on port 7860.

Usage:
    python benchmarks/verify_adapters.py
    python benchmarks/verify_adapters.py --port 7860
    python benchmarks/verify_adapters.py --adapter newton
    python benchmarks/verify_adapters.py --save-report
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
import time
from pathlib import Path

import requests

PORT = 7860
BASE_URL = "http://localhost:{port}/api/chat"

# ── Template contamination markers from train_hf_job_v4.py _generate_answer() ──
# Exact phrases that appear in the template-generated training data.
# A genuine LLM response should NOT start with or heavily use these.
INTRO_MARKERS = [
    "when examining",
    "understanding {topic} requires",
    "the study of",
    "approaching {topic} with analytical rigor",
    "a thorough examination of",
]

GENERAL_MARKERS = [
    "several key insights emerge",
    "careful analysis of its core principles",
    "fundamental patterns that connect",
    "quantitative relationships and conservation principles",
    "creative synthesis reveals unexpected connections",
    "empirical verification",
    "eliminates physically impossible solutions",
    "philosophical analysis of",
    "through socratic questioning",
    "probabilistic analysis of",
    "multiple hypotheses simultaneously",
    "recursive analysis of",
    "through the rc+ξ framework",
    "multi-perspective synthesis of",
    "integrates insights from six specialized lenses",
    "dimensional analysis ensures our equations",
    "cross-domain thinking — borrowing",
    "psychologically safe spaces for exploration",
    "emotional intelligence enhances rather than replaces",
    "bayesian updating allows us to refine",
    "coherence field γ monitors",
]

# ── Per-adapter prompts ──
# Each is a SPECIFIC question that requires genuinely substantive answers.
# Template filler would give generic structural text; real LLM should engage specifics.
ADAPTER_PROBES = {
    "newton": [
        "A 5 kg ball is thrown upward at 20 m/s. How high does it go and how long until it lands? Show the calculation.",
        "Why does a heavier object and a lighter object fall at the same rate in a vacuum? What did Galileo show?",
    ],
    "davinci": [
        "What does the architectural principle of tensegrity have in common with how muscles and tendons work in the human body?",
        "How could the way spiderwebs distribute tension inspire the design of a bridge?",
    ],
    "philosophy": [
        "Is it ethical to lie to protect someone's feelings? Walk through two conflicting philosophical positions.",
        "What did Descartes actually mean by 'I think therefore I am' — what was he trying to prove and does it work?",
    ],
    "quantum": [
        "If I have a 70% weather forecast for rain and an independent 60% forecast from another service, what is the probability it actually rains?",
        "What is Bayes' theorem and give a concrete example of updating a belief from prior to posterior.",
    ],
    "consciousness": [
        "When you notice yourself having made an error in reasoning, what does that feel like and what do you do next?",
        "Describe a moment when two of your reasoning perspectives gave contradictory answers to the same question.",
    ],
    "multi_perspective": [
        "Should AI systems be given legal personhood? Give me the strongest argument FOR and the strongest argument AGAINST.",
        "Is nuclear energy a good solution to climate change? Synthesize the scientific, ethical, and economic angles.",
    ],
    "systems_architecture": [
        "What is the difference between a monolith and microservices and when would you choose each?",
        "Explain why database normalization trades off query performance for storage efficiency.",
    ],
}


def call_adapter(url: str, query: str, adapter: str, timeout: int = 180) -> dict:
    try:
        resp = requests.post(
            url,
            json={"query": query, "adapter": adapter, "max_adapters": 1},
            timeout=timeout,  # 180s — newton physics calculations can be slow on CPU
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"error": f"Cannot connect to {url}. Is the server running?"}
    except Exception as e:
        return {"error": str(e)}


def score_response(text: str, adapter: str) -> tuple[bool, list[str]]:
    """Return (is_clean, list_of_found_markers)."""
    lower = text.lower()
    found = []
    for marker in INTRO_MARKERS + GENERAL_MARKERS:
        # Replace {topic} with a wildcard check — we just look for the static parts
        check = marker.replace("{topic}", "")
        if check.strip() and check.strip() in lower:
            found.append(marker)
    return (len(found) == 0, found)


def verify_adapter(adapter: str, url: str, verbose: bool = True) -> dict:
    probes = ADAPTER_PROBES.get(adapter, [])
    if not probes:
        return {"adapter": adapter, "status": "SKIP", "reason": "No probes defined"}

    results = []
    for i, prompt in enumerate(probes, 1):
        if verbose:
            print(f"\n  [{adapter}] Probe {i}/{len(probes)}: {prompt[:70]}...")

        t0 = time.time()
        data = call_adapter(url, prompt, adapter)
        elapsed = time.time() - t0

        if "error" in data:
            results.append({
                "probe": prompt,
                "status": "ERROR",
                "error": data["error"],
                "elapsed_s": round(elapsed, 1),
            })
            if verbose:
                print(f"    ERROR: {data['error']}")
            continue

        text = data.get("response") or data.get("text") or ""
        routed_adapter = data.get("adapter", "?")
        is_clean, markers = score_response(text, adapter)

        status = "PASS" if is_clean else "FAIL"
        result = {
            "probe": prompt,
            "status": status,
            "routed_adapter": routed_adapter,
            "response_words": len(text.split()),
            "markers_found": markers,
            "elapsed_s": round(elapsed, 1),
        }
        results.append(result)

        if verbose:
            color_pass = "\033[92m" if is_clean else "\033[91m"
            reset = "\033[0m"
            print(f"    {color_pass}{status}{reset} ({len(text.split())} words, {elapsed:.1f}s, routed→{routed_adapter})")
            if markers:
                print(f"    ⚠ Template markers found:")
                for m in markers:
                    print(f"      - '{m}'")
            if verbose and len(text) > 0:
                # Print first 200 chars of response
                preview = text[:280].replace("\n", " ")
                print(f"    Response preview: {preview}...")

    all_pass = all(r["status"] == "PASS" for r in results)
    any_error = any(r["status"] == "ERROR" for r in results)
    overall = "PASS" if all_pass else ("ERROR" if any_error else "FAIL")

    return {
        "adapter": adapter,
        "overall": overall,
        "probes": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Verify adapter behavioral quality")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--adapter", help="Test only this adapter (default: all 7)")
    parser.add_argument("--save-report", action="store_true", help="Save JSON report to data/results/")
    parser.add_argument("--quiet", action="store_true", help="Only print summary")
    args = parser.parse_args()

    url = BASE_URL.format(port=args.port)
    adapters = [args.adapter] if args.adapter else list(ADAPTER_PROBES.keys())

    print(f"\n{'=' * 60}")
    print(f"Codette Adapter Behavioral Verification")
    print(f"Server: {url}")
    print(f"Adapters: {', '.join(adapters)}")
    print(f"{'=' * 60}")

    all_results = []
    for adapter in adapters:
        print(f"\n[{adapter.upper()}]")
        result = verify_adapter(adapter, url, verbose=not args.quiet)
        all_results.append(result)

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    pass_count = 0
    for r in all_results:
        marker = "✓" if r["overall"] == "PASS" else ("✗" if r["overall"] == "FAIL" else "!")
        n_markers = sum(len(p.get("markers_found", [])) for p in r.get("probes", []))
        print(f"  {marker} {r['adapter']:22s} {r['overall']:6s}  ({n_markers} template markers across all probes)")
        if r["overall"] == "PASS":
            pass_count += 1

    print(f"\n  Result: {pass_count}/{len(all_results)} adapters clean")

    if args.save_report:
        out_dir = Path(__file__).parent.parent / "data" / "results"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"adapter_verification_{ts}.json"
        with open(out_path, "w") as f:
            json.dump({"timestamp": ts, "results": all_results}, f, indent=2)
        print(f"\n  Report saved to {out_path}")

    sys.exit(0 if pass_count == len(all_results) else 1)


if __name__ == "__main__":
    main()
