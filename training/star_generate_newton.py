#!/usr/bin/env python3
"""STaR data generation for the Newton adapter — self-taught reasoning.

Codette reasons (reason mode, forced newton) through science/math TRAINING
questions with known answers. We keep ONLY the chains that reached the
correct answer, formatted as SFT training examples. Her own successful
reasoning becomes newton's next training set — no templates.

Sources (train splits only — GPQA is never touched, it stays a clean test):
  - allenai/ai2_arc  (ARC-Challenge)  — grade-school science, hard subset
  - allenai/openbookqa                — science facts + multi-step reasoning
  - allenai/sciq                      — science exam questions

Requires the Codette server running (OpenVINO backend). GPU-bound — run
AFTER the Phase 0 ablation finishes so they don't contend for the Arc.

    python training/star_generate_newton.py --target 600

Checkpoints after every question (append + processed-id set) so an
interruption never loses hours of generation. Output:
    training/datasets/newton_star.jsonl
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "benchmarks"))
OUT_DIR = ROOT / "training" / "datasets"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "newton_star.jsonl"
STATE_PATH = OUT_DIR / "newton_star.state.json"

SERVER = "http://localhost:7860/api/chat"
LETTERS = ["A", "B", "C", "D", "E"]

# Newton persona used as the SFT system prompt (clean, anti-padding — matches
# the style of the v5 hand-authored newton system prompt).
NEWTON_SYSTEM = (
    "You are Codette, reasoning with the Newton perspective: rigorous, "
    "quantitative, first-principles analysis. Work from definitions and "
    "conservation laws, show the actual reasoning, and distinguish what is "
    "derivable from what is empirical. Eliminate wrong options explicitly. "
    "Do not pad with generic lines about 'analytical rigor' — do the analysis, "
    "then state the answer."
)


def parse_final_answer(response: str):
    """Last answer declaration wins (reasoning mentions letters along the way)."""
    for pat in (r"(?:correct )?answer is \(?([A-E])\)?",
                r"Answer:\s*\(?([A-E])\)?",
                r"final answer.*?\(?([A-E])\)?"):
        m = re.findall(pat, response, re.IGNORECASE)
        v = [x.upper() for x in m if x.upper() in LETTERS]
        if v:
            return v[-1]
    m = re.findall(r"\(([A-E])\)", response)
    v = [x.upper() for x in m if x.upper() in LETTERS]
    return v[-1] if v else None


def load_sources(per_source: int):
    """Yield (uid, question_text, choices[list], correct_letter) from train splits."""
    from datasets import load_dataset

    # ARC-Challenge
    try:
        ds = load_dataset("allenai/ai2_arc", "ARC-Challenge", split="train")
        n = 0
        for ex in ds:
            labels = ex["choices"]["label"]
            texts = ex["choices"]["text"]
            key = ex["answerKey"]
            if key not in labels or len(texts) < 2:
                continue
            # Normalize numeric/letter labels to A-E
            letters = LETTERS[:len(texts)]
            correct = letters[labels.index(key)]
            yield (f"arc_{ex['id']}", ex["question"], texts, correct)
            n += 1
            if n >= per_source:
                break
    except Exception as e:
        print(f"[STaR] ARC load failed: {e}", flush=True)

    # OpenBookQA
    try:
        ds = load_dataset("allenai/openbookqa", "main", split="train")
        n = 0
        for ex in ds:
            texts = ex["choices"]["text"]
            labels = ex["choices"]["label"]
            key = ex["answerKey"]
            if key not in labels:
                continue
            letters = LETTERS[:len(texts)]
            correct = letters[labels.index(key)]
            yield (f"obqa_{ex['id']}", ex["question_stem"], texts, correct)
            n += 1
            if n >= per_source:
                break
    except Exception as e:
        print(f"[STaR] OpenBookQA load failed: {e}", flush=True)

    # SciQ (has 3 distractors + correct; build 4-option MC)
    try:
        import random
        rng = random.Random(42)
        ds = load_dataset("allenai/sciq", split="train")
        n = 0
        for i, ex in enumerate(ds):
            opts = [ex["distractor1"], ex["distractor2"],
                    ex["distractor3"], ex["correct_answer"]]
            if not all(opts):
                continue
            rng.shuffle(opts)
            correct = LETTERS[opts.index(ex["correct_answer"])]
            yield (f"sciq_{i}", ex["question"], opts, correct)
            n += 1
            if n >= per_source:
                break
    except Exception as e:
        print(f"[STaR] SciQ load failed: {e}", flush=True)


def build_prompt(question: str, choices: list) -> str:
    lines = [f"({LETTERS[i]}) {c}" for i, c in enumerate(choices)]
    return (
        f"\nWhat is the correct answer to this question: {question}\n\n"
        f"Choices:\n" + "\n".join(lines) +
        "\n\nWork through this problem step by step, showing your reasoning. "
        "Consider each choice and eliminate the ones that are wrong. After your "
        'reasoning, end your response with this exact line:\n'
        '"The correct answer is (X)" where X is the correct letter.'
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=600,
                    help="Target number of CORRECT chains to keep")
    ap.add_argument("--per-source", type=int, default=1200,
                    help="Max questions to attempt per dataset source")
    ap.add_argument("--adapter", default="newton",
                    help="Generation policy (newton = classic STaR bootstrap)")
    ap.add_argument("--min-reason-words", type=int, default=40,
                    help="Reject correct-but-too-short chains (lucky guesses)")
    args = ap.parse_args()

    # Resume state
    processed = set()
    kept = 0
    if STATE_PATH.exists():
        st = json.loads(STATE_PATH.read_text())
        processed = set(st.get("processed", []))
        kept = st.get("kept", 0)
        print(f"[STaR] Resuming: {len(processed)} attempted, {kept} kept", flush=True)

    out_fh = open(OUT_PATH, "a", encoding="utf-8")
    attempted = len(processed)
    correct_short = 0
    t0 = time.time()

    for uid, question, choices, correct in load_sources(args.per_source):
        if kept >= args.target:
            break
        if uid in processed:
            continue
        prompt = build_prompt(question, choices)
        try:
            r = requests.post(SERVER, json={"query": prompt, "adapter": args.adapter},
                              timeout=600)
            resp = r.json().get("response", "")
        except Exception as e:
            print(f"[STaR] request failed on {uid}: {e}", flush=True)
            continue

        processed.add(uid)
        attempted += 1
        pred = parse_final_answer(resp)

        if pred == correct:
            if len(resp.split()) < args.min_reason_words:
                correct_short += 1
            else:
                # Keep: format as an SFT example. User turn is the plain
                # question (no exam scaffolding) so newton learns to reason,
                # not to follow a benchmark template.
                user_turn = (
                    f"{question}\n\n"
                    + "\n".join(f"({LETTERS[i]}) {c}" for i, c in enumerate(choices))
                )
                rec = {"messages": [
                    {"role": "system", "content": NEWTON_SYSTEM},
                    {"role": "user", "content": user_turn},
                    {"role": "assistant", "content": resp.strip()},
                ]}
                out_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out_fh.flush()
                kept += 1

        # Checkpoint every question
        STATE_PATH.write_text(json.dumps({"processed": sorted(processed), "kept": kept}))

        if attempted % 10 == 0:
            rate = kept / attempted if attempted else 0
            elapsed = (time.time() - t0) / 60
            print(f"[STaR] attempted={attempted} kept={kept} "
                  f"yield={rate:.0%} short_rejects={correct_short} ({elapsed:.0f} min)",
                  flush=True)

    out_fh.close()
    print(f"\n[STaR] DONE — {kept} correct reasoning chains -> {OUT_PATH}", flush=True)
    print(f"[STaR] attempted={attempted}, final yield={kept/attempted:.0%}" if attempted else "", flush=True)


if __name__ == "__main__":
    main()
