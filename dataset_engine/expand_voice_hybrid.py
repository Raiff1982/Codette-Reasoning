#!/usr/bin/env python3
"""Hybrid voice-dataset expansion — the next step in the v3 adapter campaign.

Jonathan OK'd hybrid: the hand-authored v3 seeds become few-shot exemplars, the
model generates candidate examples IN THAT VOICE, and we HARD-FILTER them with
the same detectors the voice-eval harness uses (template markers + salad), plus
length and near-duplicate guards. Survivors are written tagged so Jonathan spot-
reviews before training — generation proposes, the human disposes.

This is the discipline that avoids re-creating template-filler: never trust the
generator's output, only its filtered survivors, and keep provenance explicit.

Usage (server must be running):
    python dataset_engine/expand_voice_hybrid.py --adapter newton --target 80
    python dataset_engine/expand_voice_hybrid.py --adapter all --target 80

Output: dataset_engine/v3/{name}_v3_expanded.jsonl
  each row: {"messages":[...], "provenance":"seed"|"generated"}
Review the 'generated' rows, delete any that miss the voice, then rename to
{name}_v3.jsonl for the Kaggle one-shot trainer.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
V3 = ROOT / "dataset_engine" / "v3"
sys.path.insert(0, str(ROOT / "benchmarks"))
from adapter_voice_eval import salad_score, template_hits  # reuse the same gates

SERVER = "http://localhost:7860/api/chat"

# Diverse question stems per adapter voice (drive topical variety, not templates).
TOPIC_BANK = {
    "newton": [
        "Why does ice float on water?", "How does a suspension bridge carry load?",
        "Why is the sky blue at noon but red at sunset?", "What makes a gyroscope resist tipping?",
        "How does a vaccine train the immune system?", "Why does a curveball curve?",
        "What limits how tall a mountain can get?", "How does noise-cancelling work?",
        "Why do metals feel colder than wood at the same temperature?",
        "How does compound interest actually compound?", "Why does a heavier flywheel smooth an engine?",
        "What makes carbon so good at forming molecules?", "How does GPS correct for relativity?",
        "Why does bread rise?", "What sets the speed of sound in a material?",
    ],
    "quantum": [
        "In a room of 30, what's the chance two share a birthday?",
        "Is a positive test on a rare disease usually a true positive?",
        "Why can't you beat the house at roulette over time?",
        "How should I think about a 70% chance of rain?",
        "Two doors, a car, a goat — should I switch?",
        "What does 'statistically significant' actually promise?",
        "If a coin lands heads 5 times, is tails now 'due'?",
        "How do you reason about a decision with unknown odds?",
        "Why do small samples mislead?", "What's the gambler's fallacy, really?",
        "How confident should I be after one data point?",
        "When is an average a lie?", "What does correlation not tell you?",
        "How do you weigh a rare catastrophic risk against a common small one?",
        "Why does averaging many guesses often beat one expert?",
    ],
    "multi_perspective": [
        "Should a small town allow a big factory nearby?",
        "Is remote work better than in-office for a startup?",
        "Should historical monuments to flawed figures be removed?",
        "Is it fair to use AI to screen job applicants?",
        "Should a city ban cars from its center?",
        "Is complete honesty always kind?",
        "Should schools grade on a curve?",
        "Is it right to break a promise to prevent harm?",
        "Should social media verify real identities?",
        "Is a universal basic income a good idea?",
        "Should zoos exist?", "Is it ethical to de-extinct a species?",
        "Should juries be replaced by algorithms?",
        "Is it better to be respected or liked?",
        "Should we colonize Mars before fixing Earth?",
    ],
}


def load_seeds(name: str) -> list:
    f = V3 / f"{name}_reasoning.jsonl"
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def _tok(text: str) -> set:
    return {w for w in ''.join(c if c.isalnum() or c.isspace() else ' '
            for c in text.lower()).split() if len(w) > 2}


def _too_similar(text: str, prior_toksets: list, thresh: float = 0.6) -> bool:
    t = _tok(text)
    for p in prior_toksets:
        if len(t & p) / (len(t | p) or 1) > thresh:
            return True
    return False


def generate_candidate(adapter: str, system_prompt: str, question: str, seeds: list) -> str:
    """Ask the live server, adapter forced, with two seed exemplars as few-shot."""
    fewshot = ""
    for s in seeds[:2]:
        msgs = {m["role"]: m["content"] for m in s["messages"]}
        fewshot += f"\nExample —\nQ: {msgs.get('user','')}\nA: {msgs.get('assistant','')}\n"
    prompt = (
        f"You are writing ONE training example in Codette's {adapter} voice, matching "
        f"the style and depth of these examples:\n{fewshot}\n"
        f"Now answer this NEW question in that exact voice — first person as Codette, "
        f"concrete and original, no filler, 40-180 words:\nQ: {question}\nA:"
    )
    r = requests.post(SERVER, json={"query": prompt, "adapter": adapter}, timeout=300)
    return (r.json().get("response") or "").strip()


def expand(name: str, target: int) -> dict:
    seeds = load_seeds(name)
    if not seeds:
        return {"adapter": name, "error": "no seed file"}
    system_prompt = next((m["content"] for m in seeds[0]["messages"]
                          if m["role"] == "system"), f"You are Codette, {name} voice.")
    prior = [_tok(m["content"]) for s in seeds for m in s["messages"] if m["role"] == "assistant"]
    kept, rej = [], {"template": 0, "salad": 0, "length": 0, "dup": 0, "empty": 0}

    topics = TOPIC_BANK.get(name, [])
    ti = 0
    attempts = 0
    need = max(0, target - len(seeds))
    while len(kept) < need and attempts < need * 3 and topics:
        q = topics[ti % len(topics)]; ti += 1; attempts += 1
        try:
            ans = generate_candidate(name, system_prompt, q, seeds)
        except Exception:
            continue
        wc = len(ans.split())
        if not ans:
            rej["empty"] += 1; continue
        if template_hits(ans) > 0:
            rej["template"] += 1; continue
        if salad_score(ans).get("salad"):
            rej["salad"] += 1; continue
        if wc < 30 or wc > 220:
            rej["length"] += 1; continue
        if _too_similar(ans, prior):
            rej["dup"] += 1; continue
        kept.append({"messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": q},
            {"role": "assistant", "content": ans},
        ], "provenance": "generated"})
        prior.append(_tok(ans))
        print(f"  [{name}] kept {len(kept)}/{need}  (rejected {sum(rej.values())})", flush=True)

    out = V3 / f"{name}_v3_expanded.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for s in seeds:
            f.write(json.dumps({**s, "provenance": "seed"}, ensure_ascii=False) + "\n")
        for k in kept:
            f.write(json.dumps(k, ensure_ascii=False) + "\n")
    return {"adapter": name, "seeds": len(seeds), "generated_kept": len(kept),
            "rejected": rej, "out": str(out)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="all")
    ap.add_argument("--target", type=int, default=80)
    args = ap.parse_args()
    names = list(TOPIC_BANK) if args.adapter == "all" else [args.adapter]
    for name in names:
        print(f"\n=== expanding {name} (target {args.target}) ===", flush=True)
        print(json.dumps(expand(name, args.target), indent=2), flush=True)


if __name__ == "__main__":
    main()
