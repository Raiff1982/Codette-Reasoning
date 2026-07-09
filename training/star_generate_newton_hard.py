#!/usr/bin/env python3
"""STaR data generation for Newton — HARD sources (v2).

The v1 run (star_generate_newton.py) used ARC/OpenBookQA/SciQ — easy science,
81% yield — and the resulting newton-star adapter REGRESSED on GPQA (34%->25%,
controlled). The one-variable fix: train on data at or above the eval's
difficulty. This pulls from MMLU-Pro STEM — reasoning-heavy, up to 10 options,
substantially harder than ARC, and NOT GPQA (which stays a clean test set).

Same method: Codette reasons (reason mode, forced newton) through the questions,
keep only chains that reached the correct answer, format as SFT examples.

    python training/star_generate_newton_hard.py --target 500

Requires the Codette server running. GPU-bound. Resumable checkpoints.
Output: training/datasets/newton_star_hard.jsonl
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "training" / "datasets"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "newton_star_hard.jsonl"
STATE_PATH = OUT_DIR / "newton_star_hard.state.json"

SERVER = "http://localhost:7860/api/chat"
LETTERS = [chr(ord("A") + i) for i in range(10)]  # A..J (MMLU-Pro has up to 10)

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


def parse_final_answer(response: str, n_options: int):
    valid_letters = set(LETTERS[:n_options])
    for pat in (r"(?:correct )?answer is \(?([A-J])\)?",
                r"Answer:\s*\(?([A-J])\)?",
                r"final answer.*?\(?([A-J])\)?"):
        m = re.findall(pat, response, re.IGNORECASE)
        v = [x.upper() for x in m if x.upper() in valid_letters]
        if v:
            return v[-1]
    m = re.findall(r"\(([A-J])\)", response)
    v = [x.upper() for x in m if x.upper() in valid_letters]
    return v[-1] if v else None


def load_sources(per_source: int):
    """Yield (uid, question, options[list], correct_letter) from MMLU-Pro STEM."""
    from datasets import load_dataset
    try:
        ds = load_dataset("TIGER-Lab/MMLU-Pro", split="test")
        n = 0
        for ex in ds:
            cat = (ex.get("category") or "").lower()
            if cat not in STEM_CATEGORIES:
                continue
            opts = ex["options"]
            ans = ex.get("answer")  # letter string
            if not opts or ans not in LETTERS[:len(opts)]:
                continue
            yield (f"mmlupro_{ex['question_id']}", ex["question"], opts, ans)
            n += 1
            if n >= per_source:
                break
    except Exception as e:
        print(f"[STaR-hard] MMLU-Pro load failed: {e}", flush=True)


def build_prompt(question: str, options: list) -> str:
    lines = [f"({LETTERS[i]}) {c}" for i, c in enumerate(options)]
    letters_str = ", ".join(LETTERS[:len(options)])
    return (
        f"\nWhat is the correct answer to this question: {question}\n\n"
        f"Choices:\n" + "\n".join(lines) +
        "\n\nWork through this problem step by step, showing your reasoning. "
        "Consider each choice and eliminate the ones that are wrong. After your "
        'reasoning, end your response with this exact line:\n'
        f'"The correct answer is (X)" where X is one of {letters_str}.'
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=500)
    ap.add_argument("--per-source", type=int, default=6000)
    ap.add_argument("--adapter", default="newton")
    ap.add_argument("--min-reason-words", type=int, default=50)
    args = ap.parse_args()

    processed, kept = set(), 0
    if STATE_PATH.exists():
        st = json.loads(STATE_PATH.read_text())
        processed = set(st.get("processed", []))
        kept = st.get("kept", 0)
        print(f"[STaR-hard] Resuming: {len(processed)} attempted, {kept} kept", flush=True)

    out_fh = open(OUT_PATH, "a", encoding="utf-8")
    attempted, correct_short = len(processed), 0
    t0 = time.time()

    for uid, question, options, correct in load_sources(args.per_source):
        if kept >= args.target:
            break
        if uid in processed:
            continue
        prompt = build_prompt(question, options)
        try:
            r = requests.post(SERVER, json={"query": prompt, "adapter": args.adapter}, timeout=600)
            resp = r.json().get("response", "")
        except Exception as e:
            print(f"[STaR-hard] request failed on {uid}: {e}", flush=True)
            continue

        processed.add(uid)
        attempted += 1
        pred = parse_final_answer(resp, len(options))

        if pred == correct:
            if len(resp.split()) < args.min_reason_words:
                correct_short += 1
            else:
                user_turn = (
                    f"{question}\n\n"
                    + "\n".join(f"({LETTERS[i]}) {c}" for i, c in enumerate(options))
                )
                rec = {"messages": [
                    {"role": "system", "content": NEWTON_SYSTEM},
                    {"role": "user", "content": user_turn},
                    {"role": "assistant", "content": resp.strip()},
                ]}
                out_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out_fh.flush()
                kept += 1

        STATE_PATH.write_text(json.dumps({"processed": sorted(processed), "kept": kept}))

        if attempted % 10 == 0:
            rate = kept / attempted if attempted else 0
            elapsed = (time.time() - t0) / 60
            print(f"[STaR-hard] attempted={attempted} kept={kept} yield={rate:.0%} "
                  f"short={correct_short} ({elapsed:.0f} min)", flush=True)

    out_fh.close()
    print(f"\n[STaR-hard] DONE — {kept} correct hard-reasoning chains -> {OUT_PATH}", flush=True)
    if attempted:
        print(f"[STaR-hard] attempted={attempted}, yield={kept/attempted:.0%}", flush=True)


if __name__ == "__main__":
    main()
