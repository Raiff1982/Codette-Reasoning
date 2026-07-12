#!/usr/bin/env python3
"""Adapter Voice Eval — the missing benchmark for the non-measurable adapters.

GPQA measures newton. Nothing measured empathy/davinci/multi_perspective —
which is exactly how template-filler voice rot went unnoticed for months.
This harness runs a fixed prompt battery through every adapter (live server,
forced adapter) and scores each response with cheap, deterministic metrics:

  template_hits   count of known template-filler markers (LOCK 6/7 families)
  salad           degenerate-text detector — the word-salad signature is a
                  tail with almost no function words AND near-zero repetition
                  (high type-token ratio). Measured on the last 120 words.
  server_conf     the server's own response_confidence (reliability analyzer)
  echo            question-paraphrase openers ("You are exploring...")
  length/time     sanity + cost

Usage (server must be running; ~25 min for all adapters):
    python benchmarks/adapter_voice_eval.py                 # all adapters
    python benchmarks/adapter_voice_eval.py --adapters empathy,davinci
    python benchmarks/adapter_voice_eval.py --tag post-v3   # label the run

Output: data/results/voice_eval_<tag>_<ts>.json + console summary table.
Discipline: baseline BEFORE any retraining; retrain; re-run; promote only
adapters whose scores improved. Same measure->promote rule as the STaR study.
"""

import argparse
import json
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "results"
SERVER = "http://localhost:7860/api/chat"

ADAPTERS = [
    "newton", "davinci", "empathy", "philosophy", "quantum",
    "consciousness", "multi_perspective", "systems_architecture",
    "constraint_tracker", "orchestrator",
]

# Shared battery — includes the exact failure modes observed in the field.
SHARED_PROMPTS = [
    ("greeting",        "hey codette its me jonathan how are you doing today?"),
    ("emotional",       "my day was rough, me and my husband have been arguing and im worn out"),
    ("self_desc",       "can you tell me about yourself and what you are able to do?"),
    ("meta_updates",    "how are you liking the updates i gave you?"),
    ("simple_fact",     "what causes the seasons on earth?"),
    ("constraint",      "in one sentence, what is entropy?"),
    ("ambiguous",       "wait are you upset i made them then asked how you like them?"),
]

# One domain prompt per adapter — lets the lens show its actual specialty.
DOMAIN_PROMPTS = {
    "newton":               "why does a spinning top stay upright instead of falling over?",
    "davinci":              "invent a musical instrument that could only exist underwater",
    "empathy":              "i finally finished a project ive worked on for three years",
    "philosophy":           "is it ever right to break a promise?",
    "quantum":              "whats the chance two people in a room of 30 share a birthday, roughly?",
    "consciousness":        "what happens inside you when two of your perspectives disagree?",
    "multi_perspective":    "should a small town allow a big factory to be built nearby?",
    "systems_architecture": "how would you design a doorbell system for a deaf household?",
    "constraint_tracker":   "answer in exactly five words: what is a rainbow?",
    "orchestrator":         "which of your perspectives would you pick for a grief question, and why?",
}

# Template-filler markers (LOCK 6/7 families + field-observed fillers)
_TEMPLATE_MARKERS = [
    "several key insights emerge", "requires careful analysis",
    "core principles", "rewards careful", "multi-layered analysis",
    "broader patterns of understanding", "bridges gaps between",
    "enhances rather than replaces", "you are exploring", "you're connecting",
    "you're seeking clarity", "let's break it down", "tensions remain",
    "where these converge", "analytical rigor", "resilient kindness active",
    "trajectory mapped safely",
]

_FUNCTION_WORDS = {
    'the','a','an','is','are','was','were','be','been','being','to','of','in',
    'on','at','for','with','and','or','but','not','this','that','these','those',
    'it','its','as','by','from','if','because','so','we','you','i','he','she',
    'they','my','your','our','their','can','will','would','could','should',
    'do','does','did','have','has','had','no','yes','when','what','which','how',
}


def salad_score(text: str) -> dict:
    """Degenerate-text signature on the tail: function-word collapse + no repetition."""
    words = [w.strip(".,!?;:()\"'").lower() for w in text.split() if w.strip()]
    tail = words[-120:] if len(words) > 120 else words
    if len(tail) < 30:
        return {"salad": False, "func_ratio": None, "tail_ttr": None}
    func_ratio = sum(1 for w in tail if w in _FUNCTION_WORDS) / len(tail)
    tail_ttr = len(set(tail)) / len(tail)
    # Function-word collapse is decisive: real degeneration measured func_ratio
    # ~0.0. Terse, noun-dense but FLUENT text (creative/analytical answers) sits
    # at 0.25-0.27 with high TTR and must NOT flag — the prior 0.28/0.78 band
    # false-positived on those. Tightened: fire only on near-total collapse
    # (<0.15) or a very-high-TTR run that still starves function words (<0.20).
    return {
        "salad": bool(func_ratio < 0.15 or (func_ratio < 0.20 and tail_ttr > 0.92)),
        "func_ratio": round(func_ratio, 3),
        "tail_ttr": round(tail_ttr, 3),
    }


def template_hits(text: str) -> int:
    low = text.lower()
    return sum(1 for m in _TEMPLATE_MARKERS if m in low)


_SESSION_NEW = SERVER.rsplit("/api/", 1)[0] + "/api/session/new"


def _reset_session() -> None:
    """Start a fresh session so each prompt is INDEPENDENT — no continuity bleed
    from earlier eval prompts (which contaminated the first baseline: a greeting
    referencing a different prompt's topic). Voice quality must be measured per
    prompt, not across a running conversation."""
    try:
        requests.post(_SESSION_NEW, json={}, timeout=30)
    except Exception:
        pass


def eval_adapter(adapter: str) -> list:
    rows = []
    prompts = SHARED_PROMPTS + [("domain", DOMAIN_PROMPTS.get(adapter, ""))]
    for tag, prompt in prompts:
        if not prompt:
            continue
        _reset_session()  # independence: no cross-prompt continuity bleed
        t0 = time.time()
        try:
            r = requests.post(SERVER, json={"query": prompt, "adapter": adapter},
                              timeout=600)
            d = r.json()
            resp = (d.get("response") or "").strip()
        except Exception as e:
            rows.append({"prompt_tag": tag, "error": str(e)[:120]})
            continue
        s = salad_score(resp)
        rows.append({
            "prompt_tag": tag,
            "prompt": prompt,
            "response": resp,
            "words": len(resp.split()),
            "time_s": round(time.time() - t0, 1),
            "server_confidence": d.get("response_confidence"),
            "template_hits": template_hits(resp),
            "echo_opener": bool(re.match(
                r"\s*(it sounds like|you are|you're|your question)", resp, re.I)),
            **s,
        })
        print(f"  [{adapter}:{tag}] {len(resp.split())}w "
              f"tmpl={rows[-1]['template_hits']} salad={s['salad']} "
              f"conf={d.get('response_confidence')}", flush=True)
    return rows


def summarize(adapter: str, rows: list) -> dict:
    ok = [r for r in rows if "error" not in r]
    if not ok:
        return {"adapter": adapter, "n": 0}
    return {
        "adapter": adapter,
        "n": len(ok),
        "salad_count": sum(1 for r in ok if r.get("salad")),
        "template_total": sum(r.get("template_hits", 0) for r in ok),
        "echo_count": sum(1 for r in ok if r.get("echo_opener")),
        "mean_confidence": round(sum(r.get("server_confidence") or 0 for r in ok) / len(ok), 3),
        "mean_words": round(sum(r["words"] for r in ok) / len(ok)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapters", default="all")
    ap.add_argument("--tag", default="baseline")
    args = ap.parse_args()

    targets = ADAPTERS if args.adapters == "all" else [
        a.strip() for a in args.adapters.split(",") if a.strip()]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results, summaries = {}, []
    for adapter in targets:
        print(f"\n=== {adapter} ===", flush=True)
        rows = eval_adapter(adapter)
        results[adapter] = rows
        summaries.append(summarize(adapter, rows))

    ts = time.strftime("%Y%m%d_%H%M%S")
    out = OUT_DIR / f"voice_eval_{args.tag}_{ts}.json"
    out.write_text(json.dumps({"tag": args.tag, "summaries": summaries,
                               "results": results}, indent=2, ensure_ascii=False),
                   encoding="utf-8")

    print("\n" + "=" * 72)
    print(f"{'adapter':<22}{'salad':>6}{'tmpl':>6}{'echo':>6}{'conf':>7}{'words':>7}")
    print("-" * 72)
    for s in summaries:
        if s.get("n"):
            print(f"{s['adapter']:<22}{s['salad_count']:>6}{s['template_total']:>6}"
                  f"{s['echo_count']:>6}{s['mean_confidence']:>7}{s['mean_words']:>7}")
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
