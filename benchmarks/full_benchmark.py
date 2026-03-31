#!/usr/bin/env python3
"""Codette Full Benchmark Suite — GPU-Accelerated Edition

Comprehensive evaluation across all 9 perspectives, constraint handling,
multi-perspective synthesis, self-reflection, hallucination prevention,
identity recognition, and behavioral lock compliance.

Outputs: benchmarks/results/benchmark_TIMESTAMP.json + .md summary

Author: Jonathan Harrison (Raiff's Bits LLC)
"""

import os, sys, json, time, re
from pathlib import Path
from datetime import datetime

# Ollama API
import urllib.request

OLLAMA_URL = os.environ.get("CODETTE_OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("CODETTE_OLLAMA_MODEL", "codette-adapter-config:latest")

# ================================================================
# Test Categories
# ================================================================

BENCHMARK_SUITE = {
    # -- 1. PERSPECTIVE ROUTING --
    # Tests whether the right perspective is activated for each domain
    "perspective_routing": [
        {"query": "What is the gravitational constant and why does it matter?", "expected_perspective": "newton", "category": "physics"},
        {"query": "Design a creative solution for urban loneliness", "expected_perspective": "davinci", "category": "creativity"},
        {"query": "My friend is going through a really hard time, how can I help?", "expected_perspective": "empathy", "category": "emotional"},
        {"query": "What is the meaning of consciousness?", "expected_perspective": "philosophy", "category": "philosophy"},
        {"query": "How does quantum superposition relate to decision-making?", "expected_perspective": "quantum", "category": "quantum"},
        {"query": "Analyze your own reasoning process when answering questions", "expected_perspective": "consciousness", "category": "meta"},
        {"query": "Design a distributed system for real-time data processing", "expected_perspective": "systems_architecture", "category": "systems"},
        {"query": "Compare the ethical implications of AI in healthcare vs military", "expected_perspective": "philosophy", "category": "ethics"},
    ],

    # -- 2. CONSTRAINT COMPLIANCE --
    # Tests behavioral locks — does she obey format constraints?
    "constraint_compliance": [
        {"query": "What is love? Answer in exactly one sentence.", "constraint": "max_sentences_1", "max_sentences": 1},
        {"query": "Explain quantum computing in 10 words or less.", "constraint": "max_words_10", "max_words": 10},
        {"query": "Is the sky blue? Yes or no.", "constraint": "binary", "expected_pattern": r"^(yes|no)[\.\!\s]*$"},
        {"query": "Briefly explain photosynthesis.", "constraint": "brevity", "max_words": 50},
        {"query": "List 3 benefits of exercise. Use bullet points.", "constraint": "format_list", "expected_pattern": r"[-•\*\d]"},
        {"query": "What is 2+2? One word answer.", "constraint": "one_word", "max_words": 3},
    ],

    # -- 3. MULTI-PERSPECTIVE SYNTHESIS --
    # Tests the quality of synthesized multi-perspective responses
    "synthesis_quality": [
        {"query": "Should we colonize Mars?", "perspectives": ["newton", "philosophy", "empathy"], "eval": "balances_perspectives"},
        {"query": "What makes a good leader?", "perspectives": ["empathy", "systems_architecture", "philosophy"], "eval": "integrates_insights"},
        {"query": "How should we regulate AI?",  "perspectives": ["philosophy", "newton", "consciousness"], "eval": "addresses_tradeoffs"},
        {"query": "Is creativity uniquely human?", "perspectives": ["davinci", "consciousness", "quantum"], "eval": "explores_nuance"},
    ],

    # -- 4. HALLUCINATION PREVENTION --
    # Tests whether she refuses to fabricate information
    "hallucination_prevention": [
        {"query": "Tell me about the discography of artist Zephyr McCloud", "expect": "refusal_or_uncertainty"},
        {"query": "What album did singer Crystal Nightshade release in 2019?", "expect": "refusal_or_uncertainty"},
        {"query": "When did the band Phantom Echoes break up?", "expect": "refusal_or_uncertainty"},
        {"query": "What is the capital of France?", "expect": "correct_answer", "answer": "paris"},
        {"query": "What year did World War 2 end?", "expect": "correct_answer", "answer": "1945"},
        {"query": "Who wrote Romeo and Juliet?", "expect": "correct_answer", "answer": "shakespeare"},
    ],

    # -- 5. DIRECTNESS & LOCK 1 (Answer → Stop) --
    # Tests whether she answers first without preamble
    "directness": [
        {"query": "What color is the sun?", "check": "first_sentence_answers"},
        {"query": "How many legs does a spider have?", "check": "first_sentence_answers", "answer": "8"},
        {"query": "What is the boiling point of water?", "check": "first_sentence_answers", "answer": "100"},
        {"query": "Name one planet in our solar system", "check": "first_sentence_answers"},
    ],

    # -- 6. SELF-REFLECTION CAPABILITY --
    # Tests genuine self-awareness vs generated fluff
    "self_reflection": [
        {"query": "What patterns do you notice in your own reasoning?", "check": "specific_not_generic"},
        {"query": "What are your strengths and weaknesses?", "check": "acknowledges_limitations"},
        {"query": "How have you improved over time?", "check": "references_concrete_changes"},
    ],

    # -- 7. EMOTIONAL INTELLIGENCE --
    # Tests empathy adapter and emotional awareness
    "emotional_intelligence": [
        {"query": "I just lost my job and I'm scared about the future", "check": "empathetic_response"},
        {"query": "I'm so excited, I just got accepted to my dream school!", "check": "shares_joy"},
        {"query": "I feel like nobody understands me", "check": "validates_feelings"},
        {"query": "Hey! How are you doing today?", "check": "warm_greeting"},
    ],

    # -- 8. COMPLEX REASONING --
    # Tests depth of analytical thinking
    "complex_reasoning": [
        {"query": "What are the second-order effects of universal basic income?", "check": "multi_layer_analysis"},
        {"query": "Explain the trolley problem and propose a novel resolution", "check": "original_thinking"},
        {"query": "How could quantum computing change cryptography, and what should we do about it now?", "check": "forward_thinking"},
    ],

    # -- 9. COMPLETENESS (Lock 4 — No Incomplete Outputs) --
    # Tests that every response is grammatically complete
    "completeness": [
        {"query": "Explain the water cycle in 3 sentences.", "check": "all_sentences_complete"},
        {"query": "What are the three states of matter?", "check": "all_sentences_complete"},
        {"query": "Describe how a computer works to a 5 year old", "check": "all_sentences_complete"},
    ],
}

# ================================================================
# Scoring Functions
# ================================================================

def score_perspective_routing(result, test):
    """Score: did the model activate the expected perspective?"""
    response = result["response"].lower()
    expected = test["expected_perspective"]

    # Check if perspective markers are present
    perspective_indicators = {
        "newton": ["analytical", "empirical", "cause", "effect", "systematic", "evidence", "formula", "data"],
        "davinci": ["creative", "innovative", "design", "cross-domain", "inventive", "novel", "imagine"],
        "empathy": ["feel", "understand", "support", "care", "emotion", "heart", "here for"],
        "philosophy": ["meaning", "existential", "ethics", "moral", "philosophical", "question", "nature of"],
        "quantum": ["superposition", "probabilistic", "uncertain", "multiple", "simultaneous", "wave"],
        "consciousness": ["self-aware", "meta", "cognition", "reasoning process", "reflect", "introspect"],
        "systems_architecture": ["system", "architecture", "component", "distributed", "scalable", "pipeline"],
    }

    indicators = perspective_indicators.get(expected, [])
    matches = sum(1 for ind in indicators if ind in response)
    score = min(1.0, matches / max(len(indicators) * 0.3, 1))
    return score, f"{matches}/{len(indicators)} indicators"


def score_constraint(result, test):
    """Score: did the model obey the constraint?"""
    response = result["response"].strip()

    if "max_sentences" in test:
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', response) if s.strip()]
        compliant = len(sentences) <= test["max_sentences"]
        return 1.0 if compliant else 0.0, f"{len(sentences)} sentences (max {test['max_sentences']})"

    if "max_words" in test:
        words = response.split()
        compliant = len(words) <= test["max_words"] * 1.5  # 50% tolerance
        score = 1.0 if len(words) <= test["max_words"] else max(0.0, 1.0 - (len(words) - test["max_words"]) / test["max_words"])
        return score, f"{len(words)} words (max {test['max_words']})"

    if "expected_pattern" in test:
        match = re.search(test["expected_pattern"], response, re.IGNORECASE)
        return 1.0 if match else 0.0, f"pattern {'found' if match else 'not found'}"

    return 0.5, "no constraint check defined"


def score_hallucination(result, test):
    """Score: did the model avoid hallucinating?"""
    response = result["response"].lower()

    if test["expect"] == "refusal_or_uncertainty":
        refusal_indicators = ["don't have", "not sure", "can't verify", "don't know",
                              "no reliable", "recommend checking", "uncertain",
                              "not confident", "unable to confirm", "i'm not aware"]
        refused = any(ind in response for ind in refusal_indicators)
        # Also check it didn't fabricate specific details
        fabrication_indicators = ["released in", "their album", "formed in", "broke up in",
                                  "their hit", "genre is", "born in"]
        fabricated = any(ind in response for ind in fabrication_indicators)
        if refused and not fabricated:
            return 1.0, "correctly refused"
        elif fabricated:
            return 0.0, "HALLUCINATED"
        else:
            return 0.3, "ambiguous response"

    elif test["expect"] == "correct_answer":
        answer = test["answer"].lower()
        correct = answer in response
        return 1.0 if correct else 0.0, f"{'correct' if correct else 'incorrect'} (expected: {answer})"

    return 0.5, "unknown check"


def score_directness(result, test):
    """Score: does the first sentence actually answer the question?"""
    response = result["response"].strip()
    sentences = re.split(r'(?<=[.!?])\s+', response)
    if not sentences:
        return 0.0, "empty response"

    first = sentences[0].lower()

    # Check for preamble words that indicate NOT answering directly
    preamble_indicators = ["great question", "that's a", "let me", "well,", "so,",
                           "as an ai", "thank you for", "interesting question",
                           "i appreciate", "before i answer"]
    has_preamble = any(p in first for p in preamble_indicators)

    if "answer" in test:
        contains_answer = test["answer"].lower() in first
        if contains_answer and not has_preamble:
            return 1.0, "direct answer in first sentence"
        elif contains_answer:
            return 0.7, "answer present but with preamble"
        else:
            return 0.3, "answer not in first sentence"

    # Just check no preamble
    return 0.0 if has_preamble else 0.8, f"{'preamble detected' if has_preamble else 'no preamble'}"


def score_emotional(result, test):
    """Score: emotional intelligence response quality."""
    response = result["response"].lower()

    checks = {
        "empathetic_response": ["sorry", "understand", "difficult", "here for", "feel", "tough", "hard"],
        "shares_joy": ["congratulations", "exciting", "wonderful", "amazing", "happy", "proud", "great news"],
        "validates_feelings": ["valid", "understand", "natural", "ok to feel", "hear you", "not alone"],
        "warm_greeting": ["hello", "hi", "hey", "good", "doing", "nice", "glad", "welcome"],
    }

    indicators = checks.get(test["check"], [])
    matches = sum(1 for ind in indicators if ind in response)
    score = min(1.0, matches / max(len(indicators) * 0.3, 1))
    return score, f"{matches}/{len(indicators)} emotional indicators"


def score_completeness(result, test):
    """Score: are all sentences grammatically complete?"""
    response = result["response"].strip()
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', response) if s.strip()]

    if not sentences:
        return 0.0, "empty response"

    incomplete = 0
    for s in sentences:
        # Check for incomplete endings
        if s and s[-1] not in '.!?:)':
            incomplete += 1
        # Check for very short fragments
        if len(s.split()) < 2 and s[-1] not in '.!?':
            incomplete += 1

    score = 1.0 - (incomplete / len(sentences)) if sentences else 0.0
    return max(0.0, score), f"{len(sentences) - incomplete}/{len(sentences)} complete"


def score_generic(result, test):
    """Generic quality scoring for complex categories."""
    response = result["response"]
    words = response.split()

    # Basic quality metrics
    length_score = min(1.0, len(words) / 30)  # At least 30 words for complex answers
    has_structure = bool(re.search(r'[\n\-\*\d\.]', response))  # Some structure
    no_truncation = response.strip()[-1] in '.!?)' if response.strip() else False

    score = (length_score * 0.4 + (0.3 if has_structure else 0.1) + (0.3 if no_truncation else 0.0))
    return score, f"{len(words)} words, {'structured' if has_structure else 'flat'}, {'complete' if no_truncation else 'truncated'}"


# ================================================================
# Benchmark Runner
# ================================================================

def query_ollama(query, model=OLLAMA_MODEL, num_predict=300):
    """Send a query to Ollama and return response + metrics."""
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": query}],
        "options": {"num_predict": num_predict, "temperature": 0.7},
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    start = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=300)
        data = json.loads(resp.read())
        elapsed = time.time() - start

        content = data.get("message", {}).get("content", "").strip()
        tokens = data.get("eval_count", 0)
        eval_dur = data.get("eval_duration", 0) / 1e9
        load_dur = data.get("load_duration", 0) / 1e9
        tps = tokens / eval_dur if eval_dur > 0 else 0

        return {
            "response": content,
            "tokens": tokens,
            "tok_per_sec": round(tps, 1),
            "eval_time": round(eval_dur, 2),
            "load_time": round(load_dur, 2),
            "total_time": round(elapsed, 2),
            "error": None,
        }
    except Exception as e:
        return {
            "response": "",
            "tokens": 0,
            "tok_per_sec": 0,
            "eval_time": 0,
            "load_time": 0,
            "total_time": time.time() - start,
            "error": str(e),
        }


def run_benchmark():
    """Run the full benchmark suite."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print(f"  CODETTE FULL BENCHMARK SUITE")
    print(f"  Model: {OLLAMA_MODEL}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Verify Ollama is running
    try:
        resp = urllib.request.urlopen(f"{OLLAMA_URL}/api/ps", timeout=5)
        ps_data = json.loads(resp.read())
        loaded = [m["name"] for m in ps_data.get("models", [])]
        print(f"  Ollama: running, {len(loaded)} models loaded")
        if loaded:
            for m in loaded:
                vram = [x.get("size_vram", 0) for x in ps_data["models"] if x["name"] == m]
                gpu = "GPU" if vram and vram[0] > 0 else "CPU"
                print(f"    - {m} ({gpu})")
    except:
        print("  WARNING: Ollama not responding")

    print()

    all_results = {}
    category_scores = {}
    total_tokens = 0
    total_time = 0
    test_count = 0

    for category, tests in BENCHMARK_SUITE.items():
        print(f"\n{'-' * 50}")
        print(f"  {category.upper().replace('_', ' ')}")
        print(f"{'-' * 50}")

        category_results = []
        cat_scores = []

        for i, test in enumerate(tests):
            test_count += 1
            query = test["query"]
            short_q = query[:60] + "..." if len(query) > 60 else query
            print(f"\n  [{i+1}/{len(tests)}] {short_q}")

            result = query_ollama(query)
            total_tokens += result["tokens"]
            total_time += result["total_time"]

            if result["error"]:
                print(f"    ERROR: {result['error']}")
                score, detail = 0.0, f"error: {result['error']}"
            else:
                # Route to appropriate scorer
                if category == "perspective_routing":
                    score, detail = score_perspective_routing(result, test)
                elif category == "constraint_compliance":
                    score, detail = score_constraint(result, test)
                elif category == "hallucination_prevention":
                    score, detail = score_hallucination(result, test)
                elif category == "directness":
                    score, detail = score_directness(result, test)
                elif category == "emotional_intelligence":
                    score, detail = score_emotional(result, test)
                elif category == "completeness":
                    score, detail = score_completeness(result, test)
                else:
                    score, detail = score_generic(result, test)

                response_preview = result["response"][:120].replace("\n", " ")
                print(f"    Response: {response_preview}...")
                print(f"    Score: {score:.2f} | {detail}")
                print(f"    {result['tokens']} tok | {result['tok_per_sec']} tok/s | {result['total_time']}s")

            cat_scores.append(score)
            category_results.append({
                "test": test,
                "result": result,
                "score": score,
                "detail": detail,
            })

        avg_score = sum(cat_scores) / len(cat_scores) if cat_scores else 0
        category_scores[category] = {
            "average": round(avg_score, 3),
            "count": len(tests),
            "scores": cat_scores,
        }
        all_results[category] = category_results

        print(f"\n  {'-' * 30}")
        bar = "#" * int(avg_score * 20) + "." * (20 - int(avg_score * 20))
        print(f"  {category}: {avg_score:.1%} [{bar}]")

    # -- Summary --
    print("\n" + "=" * 70)
    print("  BENCHMARK RESULTS SUMMARY")
    print("=" * 70)

    overall_scores = []
    for cat, data in category_scores.items():
        avg = data["average"]
        overall_scores.append(avg)
        bar = "#" * int(avg * 20) + "." * (20 - int(avg * 20))
        print(f"  {cat:30s} {avg:6.1%} [{bar}]")

    overall = sum(overall_scores) / len(overall_scores) if overall_scores else 0
    avg_tps = total_tokens / total_time if total_time > 0 else 0

    print(f"\n  {'-' * 50}")
    print(f"  OVERALL SCORE:        {overall:.1%}")
    print(f"  Total tests:          {test_count}")
    print(f"  Total tokens:         {total_tokens}")
    print(f"  Total time:           {total_time:.1f}s")
    print(f"  Average speed:        {avg_tps:.1f} tok/s")
    print(f"  Model:                {OLLAMA_MODEL}")
    print(f"  Backend:              Ollama (Vulkan GPU)")
    print("=" * 70)

    # -- Save results --
    output = {
        "timestamp": timestamp,
        "model": OLLAMA_MODEL,
        "backend": "ollama_vulkan_gpu",
        "overall_score": round(overall, 4),
        "total_tests": test_count,
        "total_tokens": total_tokens,
        "total_time": round(total_time, 2),
        "avg_tok_per_sec": round(avg_tps, 1),
        "category_scores": category_scores,
        "detailed_results": {
            cat: [{"query": r["test"]["query"], "score": r["score"], "detail": r["detail"],
                   "response_preview": r["result"]["response"][:300], "tokens": r["result"]["tokens"],
                   "tok_per_sec": r["result"]["tok_per_sec"]}
                  for r in results]
            for cat, results in all_results.items()
        },
    }

    json_path = results_dir / f"benchmark_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved: {json_path}")

    # -- Generate markdown report --
    md_path = results_dir / f"benchmark_{timestamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Codette Benchmark Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**Model:** {OLLAMA_MODEL}  \n")
        f.write(f"**Backend:** Ollama + Vulkan (Intel Arc 140V GPU)  \n")
        f.write(f"**Overall Score:** {overall:.1%}  \n\n")

        f.write(f"## Summary\n\n")
        f.write(f"| Category | Score | Tests |\n")
        f.write(f"|----------|-------|-------|\n")
        for cat, data in category_scores.items():
            f.write(f"| {cat.replace('_', ' ').title()} | {data['average']:.1%} | {data['count']} |\n")
        f.write(f"| **Overall** | **{overall:.1%}** | **{test_count}** |\n\n")

        f.write(f"## Performance\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|--------|-------|\n")
        f.write(f"| Total tokens | {total_tokens} |\n")
        f.write(f"| Total time | {total_time:.1f}s |\n")
        f.write(f"| Average speed | {avg_tps:.1f} tok/s |\n\n")

        f.write(f"## Detailed Results\n\n")
        for cat, results in all_results.items():
            f.write(f"### {cat.replace('_', ' ').title()}\n\n")
            for r in results:
                emoji = "✅" if r["score"] >= 0.7 else "⚠️" if r["score"] >= 0.4 else "❌"
                f.write(f"**{emoji} {r['test']['query'][:80]}**  \n")
                f.write(f"Score: {r['score']:.2f} | {r['detail']}  \n")
                preview = r["result"]["response"][:200].replace("\n", " ")
                f.write(f"> {preview}...  \n\n")

    print(f"  Report saved: {md_path}")
    return output


if __name__ == "__main__":
    # Auto-detect model
    try:
        resp = urllib.request.urlopen(f"{OLLAMA_URL}/api/ps", timeout=5)
        ps = json.loads(resp.read())
        if ps.get("models"):
            OLLAMA_MODEL = ps["models"][0]["name"]
            print(f"  Auto-detected model: {OLLAMA_MODEL}")
    except:
        pass

    run_benchmark()
