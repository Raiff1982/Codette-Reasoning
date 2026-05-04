#!/usr/bin/env python3
"""
Phase 7.1 AAP Benchmark — Adaptive Answer Placement + Spectral Trust
=====================================================================

Measures the concrete improvements from SynthesisEngineV3:

1. Directness Score    — % of SIMPLE queries where the answer is in sentence 1
2. Preamble Length     — words before the first substantive answer, by tier
3. Attractor Distribution — Fact / Synthesis / Discovery hit rate
4. Spectral Trust      — avg trust score across all responses
5. Latency by Tier     — ms per complexity level
6. Response Quality    — length-normalized answer density

Compares SIMPLE vs COMPLEX to verify the gating is working
(simple queries should be far shorter and more direct than complex ones).

Usage:
    python benchmarks/phase71_aap_benchmark.py
    python benchmarks/phase71_aap_benchmark.py --url http://localhost:7860
    python benchmarks/phase71_aap_benchmark.py --quick   # 5 queries per tier

Requires: Codette server running at --url (default: http://localhost:7860)
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "benchmarks" / "results"

# ── Query sets ────────────────────────────────────────────────────────────────

SIMPLE_QUERIES = [
    # Factual — should fire Fact attractor (eps < 0.35), answer first
    "How many legs does a spider have?",
    "What is the speed of light in a vacuum?",
    "What is the boiling point of water in Celsius?",
    "Who wrote Hamlet?",
    "What is the chemical symbol for gold?",
    "How many bones are in the adult human body?",
    "What planet is closest to the Sun?",
    "What is 2 to the power of 10?",
    "In what year did World War II end?",
    "What is the SI unit of electrical resistance?",
]

SYNTHESIS_QUERIES = [
    # Moderate tension — should fire Synthesis attractor (0.35 < eps < 0.70)
    "How does inflation affect interest rates?",
    "What are the tradeoffs between static and dynamic typing in programming?",
    "How does sleep deprivation affect cognitive performance?",
    "What are the pros and cons of remote work for software teams?",
    "How do vaccines produce immunity?",
    "What distinguishes machine learning from traditional programming?",
    "How does compound interest work over long time horizons?",
    "What are the main causes of the 2008 financial crisis?",
]

DISCOVERY_QUERIES = [
    # High tension — should fire Discovery attractor (eps > 0.70)
    "Can artificial intelligence ever be truly conscious?",
    "Is free will compatible with determinism?",
    "What are the ethical implications of genetic engineering in humans?",
    "How should society balance individual privacy against collective security?",
    "What does it mean for an AI to be aligned with human values?",
    "Is mathematical truth discovered or invented?",
    "How do we weigh present welfare against future generations?",
]

QUICK_SIMPLE    = SIMPLE_QUERIES[:4]
QUICK_SYNTHESIS = SYNTHESIS_QUERIES[:3]
QUICK_DISCOVERY = DISCOVERY_QUERIES[:2]

# ── Local SynthesisV3 attractor for offline scoring ───────────────────────────

try:
    from reasoning_forge.synthesis_engine_v3 import SynthesisEngineV3, ATTRACTOR_FACT, ATTRACTOR_DISCOVERY
    _local_engine = SynthesisEngineV3()
    _LOCAL_V3 = True
except ImportError:
    _LOCAL_V3 = False
    ATTRACTOR_FACT = 0.35
    ATTRACTOR_DISCOVERY = 0.70


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class TurnResult:
    query: str
    tier: str                          # SIMPLE | SYNTHESIS | DISCOVERY
    latency_ms: float
    response_text: str
    response_words: int
    # Directness analysis
    preamble_words: int                # words before first real answer
    answer_in_first_sentence: bool     # True if verdict in sentence 1
    attractor_detected: str            # Fact | Synthesis | Discovery | unknown
    # Trust
    spectral_trust: float              # from score_text_resonance if available
    # Raw
    api_complexity: str = ""           # complexity tag returned by server
    error: Optional[str] = None


def _detect_attractor(text: str) -> str:
    """Infer which attractor fired from response text format."""
    stripped = text.strip()
    if stripped.startswith("**") and "Metacognitive Trace" in text:
        return "Fact"
    if stripped.startswith("Analysis of *'") or stripped.startswith("Analysis of '"):
        return "Synthesis"
    if "high-tension epistemic space" in text or "productive divergences" in text:
        return "Discovery"
    return "unknown"


def _preamble_words(text: str) -> int:
    """Count words appearing before the first substantive answer content.

    For Fact attractor: 0 (answer is sentence 1).
    For Synthesis/Discovery: words before 'Synthesis:' or 'Convergence:'.
    """
    stripped = text.strip()
    # Fact attractor — answer is first
    if stripped.startswith("**") and "Metacognitive Trace" not in stripped[:10]:
        return 0
    if stripped.startswith("**") and "Metacognitive Trace" in stripped:
        # Extract the bold answer — that's sentence 0
        return 0
    # Synthesis / Discovery — find where the verdict/synthesis line is
    for marker in ("**Synthesis:**", "**Convergence point:**", "**Final Synthesis:**"):
        idx = text.find(marker)
        if idx > 0:
            return len(text[:idx].split())
    # Fallback: count words in first 'sentence'
    sentences = re.split(r"(?<=[.!?])\s+", stripped)
    if sentences:
        return len(sentences[0].split())
    return len(stripped.split())


def _answer_in_first_sentence(text: str, query: str) -> bool:
    """True if the response leads with factual content rather than meta-preamble."""
    stripped = text.strip()
    # Bold verdict = Fact attractor = answer first
    if stripped.startswith("**"):
        return True
    # Check if first sentence is longer than the query (not just echoing it)
    sentences = re.split(r"(?<=[.!?])\s+", stripped)
    if not sentences:
        return False
    first = sentences[0].strip()
    # Long first sentence with no "Analysis" preamble is usually an answer
    if len(first.split()) >= 5 and not first.lower().startswith(("analysis", "i'll", "let me", "to answer")):
        return True
    return False


# ── HTTP client ───────────────────────────────────────────────────────────────

def _post(url: str, query: str, timeout: int = 90) -> tuple[float, dict]:
    payload = json.dumps({"query": query, "max_adapters": 2}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return (time.time() - t0) * 1000, body


def _ping(base_url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{base_url}/health", timeout=3) as r:
            return r.status == 200
    except Exception:
        try:
            with urllib.request.urlopen(f"{base_url}/api/status", timeout=3) as r:
                return r.status == 200
        except Exception:
            return False


# ── Benchmark runner ──────────────────────────────────────────────────────────

class Phase71Benchmark:
    def __init__(self, base_url: str = "http://localhost:7860"):
        self.url = f"{base_url}/api/chat"
        self.base_url = base_url
        self.results: list[TurnResult] = []

    def _run_tier(self, queries: list[str], tier: str) -> None:
        for i, q in enumerate(queries, 1):
            print(f"  [{i}/{len(queries)}] {tier}: {q[:60]}...", end="", flush=True)
            try:
                latency_ms, data = _post(self.url, q)
                text = data.get("response", "") or ""
                if not text and isinstance(data, dict):
                    text = data.get("response_text", "") or str(data)[:200]

                attractor = _detect_attractor(text)
                preamble  = _preamble_words(text)
                direct    = _answer_in_first_sentence(text, q)
                trust     = 0.0
                if _LOCAL_V3:
                    try:
                        tr = _local_engine.score_text_resonance(text)
                        trust = tr.get("trust", 0.0)
                    except Exception:
                        pass

                result = TurnResult(
                    query=q,
                    tier=tier,
                    latency_ms=round(latency_ms, 1),
                    response_text=text,
                    response_words=len(text.split()),
                    preamble_words=preamble,
                    answer_in_first_sentence=direct,
                    attractor_detected=attractor,
                    spectral_trust=round(trust, 3),
                    api_complexity=data.get("complexity", ""),
                )
                self.results.append(result)
                marker = "DIRECT" if direct else "preamble"
                print(f"  {latency_ms:6.0f}ms  [{attractor:<11}]  trust={trust:.2f}  {marker}")
            except urllib.error.URLError as e:
                print(f"  NETWORK ERROR: {e}")
                self.results.append(TurnResult(
                    query=q, tier=tier, latency_ms=0, response_text="",
                    response_words=0, preamble_words=0,
                    answer_in_first_sentence=False, attractor_detected="error",
                    spectral_trust=0.0, error=str(e),
                ))
            except Exception as e:
                print(f"  ERROR: {e}")

    def run(self, quick: bool = False) -> None:
        simple    = QUICK_SIMPLE    if quick else SIMPLE_QUERIES
        synthesis = QUICK_SYNTHESIS if quick else SYNTHESIS_QUERIES
        discovery = QUICK_DISCOVERY if quick else DISCOVERY_QUERIES

        total = len(simple) + len(synthesis) + len(discovery)
        print(f"\nPhase 7.1 AAP Benchmark  —  {total} queries  —  {datetime.now():%Y-%m-%d %H:%M}")
        print("=" * 72)

        for tier, queries in [("SIMPLE", simple), ("SYNTHESIS", synthesis), ("DISCOVERY", discovery)]:
            print(f"\n--- {tier} tier ({len(queries)} queries) ---")
            self._run_tier(queries, tier)

    def report(self) -> str:
        lines = ["\n" + "=" * 72, "PHASE 7.1 AAP BENCHMARK RESULTS", "=" * 72]

        tiers = ["SIMPLE", "SYNTHESIS", "DISCOVERY"]
        all_direct_rates = {}
        all_preamble     = {}
        all_latency      = {}
        all_trust        = {}
        all_attractors   = {}

        for tier in tiers:
            tier_results = [r for r in self.results if r.tier == tier and not r.error]
            if not tier_results:
                continue

            direct_rate   = sum(1 for r in tier_results if r.answer_in_first_sentence) / len(tier_results) * 100
            avg_preamble  = statistics.mean(r.preamble_words for r in tier_results)
            avg_latency   = statistics.mean(r.latency_ms for r in tier_results)
            avg_trust     = statistics.mean(r.spectral_trust for r in tier_results)
            attractor_dist = {}
            for r in tier_results:
                attractor_dist[r.attractor_detected] = attractor_dist.get(r.attractor_detected, 0) + 1

            all_direct_rates[tier] = direct_rate
            all_preamble[tier]     = avg_preamble
            all_latency[tier]      = avg_latency
            all_trust[tier]        = avg_trust
            all_attractors[tier]   = attractor_dist

            lines.append(f"\n{tier} tier  ({len(tier_results)} queries)")
            lines.append(f"  Directness (answer in sentence 1) : {direct_rate:5.1f}%")
            lines.append(f"  Avg preamble words                : {avg_preamble:5.1f}")
            lines.append(f"  Avg latency                       : {avg_latency:7.0f} ms")
            lines.append(f"  Avg spectral trust                : {avg_trust:5.3f}")
            lines.append(f"  Attractor distribution            : {attractor_dist}")

        # ── Cross-tier comparison ─────────────────────────────────────────────
        lines.append("\n" + "-" * 72)
        lines.append("CROSS-TIER COMPARISON")
        lines.append("-" * 72)

        if "SIMPLE" in all_direct_rates and "DISCOVERY" in all_direct_rates:
            gap = all_direct_rates["SIMPLE"] - all_direct_rates["DISCOVERY"]
            lines.append(
                f"  Directness gap (SIMPLE - DISCOVERY) : {gap:+.1f}pp "
                f"{'(gating working)' if gap > 20 else '(check gating)'}"
            )

        if "SIMPLE" in all_latency and "DISCOVERY" in all_latency:
            ratio = all_latency["DISCOVERY"] / max(all_latency["SIMPLE"], 1)
            lines.append(
                f"  Latency ratio (DISCOVERY / SIMPLE)  : {ratio:.1f}x "
                f"{'(expected >1.5x)' if ratio > 1.5 else '(lower than expected)'}"
            )

        if "SIMPLE" in all_preamble and "DISCOVERY" in all_preamble:
            preamble_gap = all_preamble["DISCOVERY"] - all_preamble["SIMPLE"]
            lines.append(
                f"  Preamble gap (DISCOVERY - SIMPLE)   : {preamble_gap:+.1f} words "
                f"{'(synthesis depth showing)' if preamble_gap > 10 else '(flat — check attractor routing)'}"
            )

        # ── Overall health ────────────────────────────────────────────────────
        lines.append("\n" + "-" * 72)
        lines.append("OVERALL HEALTH")
        lines.append("-" * 72)

        all_ok = self.results and not any(r.error for r in self.results)
        errors = [r for r in self.results if r.error]
        simple_direct = all_direct_rates.get("SIMPLE", 0)

        health = "OK" if simple_direct >= 70 and not errors else "DEGRADED"
        lines.append(f"  Status                 : {health}")
        lines.append(f"  Total turns            : {len(self.results)}")
        lines.append(f"  Errors                 : {len(errors)}")
        lines.append(f"  SIMPLE directness      : {simple_direct:.1f}%  (target: >70%)")

        all_trust_vals = [r.spectral_trust for r in self.results if not r.error and r.spectral_trust > 0]
        if all_trust_vals:
            lines.append(f"  Overall spectral trust : {statistics.mean(all_trust_vals):.3f}  (target: >0.6)")

        # ── Sample responses ──────────────────────────────────────────────────
        lines.append("\n" + "-" * 72)
        lines.append("SAMPLE RESPONSES (first query per tier)")
        lines.append("-" * 72)
        for tier in tiers:
            tier_r = [r for r in self.results if r.tier == tier and not r.error]
            if tier_r:
                r = tier_r[0]
                lines.append(f"\n  {tier}: {r.query}")
                lines.append(f"  Attractor: {r.attractor_detected}  trust={r.spectral_trust:.3f}")
                preview = r.response_text.replace("\n", " ")[:200]
                lines.append(f"  Response: {preview}...")

        lines.append("\n" + "=" * 72)
        return "\n".join(lines)

    def save(self) -> Path:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = RESULTS_DIR / f"phase71_aap_{ts}.json"
        payload = {
            "benchmark": "phase71_aap",
            "timestamp": ts,
            "total_turns": len(self.results),
            "results": [asdict(r) for r in self.results],
        }
        out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return out


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Phase 7.1 AAP Benchmark")
    parser.add_argument("--url", default="http://localhost:7860", help="Server base URL")
    parser.add_argument("--quick", action="store_true", help="Run reduced query set (faster)")
    args = parser.parse_args()

    print(f"Checking server at {args.url}...")
    if not _ping(args.url):
        print(f"  Server not responding at {args.url} — is Codette running?")
        print(f"  Start with: make dev   or   python inference/codette_server.py")
        sys.exit(1)
    print("  Server OK")

    bench = Phase71Benchmark(base_url=args.url)
    bench.run(quick=args.quick)

    report = bench.report()
    print(report)

    out = bench.save()
    print(f"\nResults saved: {out}")


if __name__ == "__main__":
    main()
