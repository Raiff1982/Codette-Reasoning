#!/usr/bin/env python3
"""STaR RATIONALIZATION for Newton — the missing half of the method (v3).

Zelikman et al.'s STaR has two mechanisms. We built only the first:
  1. Keep-correct: train on chains that reached the right answer.
     -> Result: consolidates the comfort zone. Measured: easy data 25%,
        hard data 28%, vs 34% untrained baseline. Never extends ability.
  2. RATIONALIZATION (this file): for problems the model got WRONG, give it
     the correct answer and have it generate the reasoning that reaches it.
     The hint is then STRIPPED from the training example — the model trains
     as if it derived the answer itself. This is how STaR trains on problems
     beyond current ability instead of only within it.

Candidates: the exact MMLU-Pro STEM questions newton FAILED during the v2
hard run (571 attempted − 350 kept, 0 short-rejects = 221 wrong), identified
from newton_star_hard.state.json + the kept-question texts in the jsonl.

Anti-leak: generated chains that reference being given the answer ("we are
told", "the given answer", "as stated") are rejected — she must derive.

    python training/star_generate_newton_rational.py --target 180

Output: training/datasets/newton_star_rational.jsonl (same SFT format).
Train on hard + rational combined -> newton-star-r.
"""

import argparse
import json
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "training" / "datasets"
OUT_PATH = OUT_DIR / "newton_star_rational.jsonl"
STATE_PATH = OUT_DIR / "newton_star_rational.state.json"
HARD_JSONL = OUT_DIR / "newton_star_hard.jsonl"
HARD_STATE = OUT_DIR / "newton_star_hard.state.json"

SERVER = "http://localhost:7860/api/chat"
LETTERS = [chr(ord("A") + i) for i in range(10)]
STEM_CATEGORIES = {"math", "physics", "chemistry", "biology",
                   "computer science", "engineering"}

NEWTON_SYSTEM = (
    "You are Codette, reasoning with the Newton perspective: rigorous, "
    "quantitative, first-principles analysis. Work from definitions and "
    "conservation laws, show the actual reasoning, and distinguish what is "
    "derivable from what is empirical. Eliminate wrong options explicitly. "
    "Do not pad with generic lines about 'analytical rigor' — do the analysis, "
    "then state the answer."
)

# Chains that cite the hint instead of deriving are rejected.
_LEAK_PATTERNS = re.compile(
    r"we (?:are|were) told|the given answer|as stated|since the answer is|"
    r"the answer (?:provided|given)|it is given that the correct|"
    r"known to be correct|the provided answer|because the question says the answer",
    re.IGNORECASE,
)


def parse_final_answer(response: str, n_options: int):
    valid = set(LETTERS[:n_options])
    for pat in (r"(?:correct )?answer is \(?([A-J])\)?",
                r"Answer:\s*\(?([A-J])\)?",
                r"final answer.*?\(?([A-J])\)?"):
        m = re.findall(pat, response, re.IGNORECASE)
        v = [x.upper() for x in m if x.upper() in valid]
        if v:
            return v[-1]
    m = re.findall(r"\(([A-J])\)", response)
    v = [x.upper() for x in m if x.upper() in valid]
    return v[-1] if v else None


def load_failed_candidates(per_source: int):
    """Yield (uid, question, options, correct) for questions newton FAILED in v2."""
    from datasets import load_dataset

    attempted = set()
    if HARD_STATE.exists():
        attempted = set(json.loads(HARD_STATE.read_text()).get("processed", []))

    kept_questions = set()
    if HARD_JSONL.exists():
        for line in open(HARD_JSONL, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                user_turn = json.loads(line)["messages"][1]["content"]
                kept_questions.add(user_turn.split("\n\n(")[0].strip())
            except Exception:
                pass

    print(f"[STaR-R] hard-run attempted={len(attempted)}, kept={len(kept_questions)}",
          flush=True)

    ds = load_dataset("TIGER-Lab/MMLU-Pro", split="test")
    n = 0
    for ex in ds:
        cat = (ex.get("category") or "").lower()
        if cat not in STEM_CATEGORIES:
            continue
        uid = f"mmlupro_{ex['question_id']}"
        if uid not in attempted:
            continue                      # never tried — not a failure candidate
        if ex["question"].strip() in kept_questions:
            continue                      # she got this one right already
        opts = ex["options"]
        ans = ex.get("answer")
        if not opts or ans not in LETTERS[:len(opts)]:
            continue
        yield (uid, ex["question"], opts, ans)
        n += 1
        if n >= per_source:
            break


def build_rationalization_prompt(question: str, options: list, correct: str) -> str:
    """Generation prompt WITH the answer hint (stripped later for training)."""
    lines = [f"({LETTERS[i]}) {c}" for i, c in enumerate(options)]
    return (
        f"\nWhat is the correct answer to this question: {question}\n\n"
        f"Choices:\n" + "\n".join(lines) +
        f"\n\nThe correct answer is ({correct}). Work through this problem step "
        f"by step and show the rigorous reasoning that DERIVES why ({correct}) "
        "is correct and why the other options fail. Derive it from first "
        "principles — do NOT mention that the answer was provided to you. "
        f'End your response with this exact line:\n"The correct answer is ({correct})"'
    )


def build_training_user_turn(question: str, options: list) -> str:
    """Training example user turn: the BARE question. No hint. Ever."""
    return question + "\n\n" + "\n".join(
        f"({LETTERS[i]}) {c}" for i, c in enumerate(options))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=180)
    ap.add_argument("--per-source", type=int, default=6000)
    ap.add_argument("--adapter", default="newton")
    ap.add_argument("--min-reason-words", type=int, default=50)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    processed, kept = set(), 0
    if STATE_PATH.exists():
        st = json.loads(STATE_PATH.read_text())
        processed = set(st.get("processed", []))
        kept = st.get("kept", 0)
        print(f"[STaR-R] Resuming: {len(processed)} attempted, {kept} kept", flush=True)

    out_fh = open(OUT_PATH, "a", encoding="utf-8")
    attempted, leak_rejects, wrong_letter = len(processed), 0, 0
    t0 = time.time()

    for uid, question, options, correct in load_failed_candidates(args.per_source):
        if kept >= args.target:
            break
        if uid in processed:
            continue

        prompt = build_rationalization_prompt(question, options, correct)
        try:
            r = requests.post(SERVER, json={"query": prompt, "adapter": args.adapter},
                              timeout=600)
            resp = (r.json().get("response") or "").strip()
        except Exception as e:
            print(f"[STaR-R] request failed on {uid}: {e}", flush=True)
            continue

        processed.add(uid)
        attempted += 1

        ok = (
            parse_final_answer(resp, len(options)) == correct
            and len(resp.split()) >= args.min_reason_words
            and not _LEAK_PATTERNS.search(resp)
        )
        if _LEAK_PATTERNS.search(resp):
            leak_rejects += 1
        elif parse_final_answer(resp, len(options)) != correct:
            wrong_letter += 1

        if ok:
            rec = {"messages": [
                {"role": "system", "content": NEWTON_SYSTEM},
                {"role": "user", "content": build_training_user_turn(question, options)},
                {"role": "assistant", "content": resp},
            ]}
            out_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out_fh.flush()
            kept += 1

        STATE_PATH.write_text(json.dumps({"processed": sorted(processed), "kept": kept}))

        if attempted % 10 == 0:
            rate = kept / attempted if attempted else 0
            print(f"[STaR-R] attempted={attempted} kept={kept} yield={rate:.0%} "
                  f"leaks={leak_rejects} wrong={wrong_letter} "
                  f"({(time.time()-t0)/60:.0f} min)", flush=True)

    out_fh.close()
    print(f"\n[STaR-R] DONE — {kept} rationalized chains -> {OUT_PATH}", flush=True)
    print(f"[STaR-R] attempted={attempted} leaks_rejected={leak_rejects} "
          f"wrong_letter={wrong_letter}", flush=True)


if __name__ == "__main__":
    main()
