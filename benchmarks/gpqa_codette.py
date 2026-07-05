#!/usr/bin/env python3
"""
Codette GPQA Benchmark
======================
Runs Codette against the GPQA (Graduate-Level Google-Proof Q&A) benchmark.

Adapted from the official Kaggle GPQA implementation:
  https://kaggle.com/benchmarks/kaggle/gpqa

Requires:
  - Codette server running:  python inference/codette_server.py
  - kagglehub + pandas:      pip install kagglehub pandas

Usage:
    python benchmarks/gpqa_codette.py                      # 0-shot, gpqa_mini
    python benchmarks/gpqa_codette.py --mode cot           # 5-shot chain-of-thought
    python benchmarks/gpqa_codette.py --dataset gpqa_diamond.csv
    python benchmarks/gpqa_codette.py --port 8080
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from collections import Counter, namedtuple
from pathlib import Path
from typing import Callable

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CODETTE_PORT = 7860
CODETTE_URL_TEMPLATE = "http://localhost:{port}/api/chat"
KAGGLEHUB_HANDLE = "open-benchmarks/gpqa-a-graduate-level-google-proof-q-and-a"
RESULTS_DIR = Path(__file__).parent.parent / "data" / "results"

# ---------------------------------------------------------------------------
# Codette PROMPT — drop-in replacement for the Kaggle notebook's PROMPT()
# ---------------------------------------------------------------------------

def make_prompt_fn(port: int, full_synthesis: bool = False, max_adapters: int = 2,
                   tok_stats: list | None = None):
    """
    tok_stats: optional list to accumulate (tokens, elapsed_s) tuples per call.
    After the run, compute mean tok/s with:
        mean_tps = sum(t for _, t_s, t in ...) / total_s
    """
    url = CODETTE_URL_TEMPLATE.format(port=port)

    def PROMPT(full_model_name: str, messages: list[dict], **_ignored_params):
        """Call Codette's /api/chat instead of an external OpenAI-compatible API."""
        print(f"Prompting Codette ({full_model_name})", end="... ", flush=True)

        user_content = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            "",
        )

        t0 = time.time()
        try:
            resp = requests.post(
                url,
                json={
                    "query": user_content,
                    "full_synthesis": full_synthesis,
                    "max_adapters": max_adapters,
                },
                timeout=1500,  # 25 min — matches server's 20-min inference cap
            )
            resp.raise_for_status()
        except requests.exceptions.ConnectionError:
            print(f"\n[ERROR] Cannot connect to Codette server at {url}")
            print("Start it with:  python inference/codette_server.py")
            sys.exit(1)
        wall_s = time.time() - t0

        data = resp.json()

        if "error" in data:
            raise RuntimeError(f"Codette server error: {data['error']}")

        text = data.get("response") or data.get("text") or str(data)
        tokens = data.get("tokens", 0) or 0
        server_s = data.get("time", 0) or wall_s

        tps = tokens / server_s if server_s > 0 else 0
        print(f"Success! ({tokens} tok, {tps:.1f} tok/s, {server_s:.1f}s)")

        if tok_stats is not None:
            tok_stats.append((tokens, server_s, tps))

        return text

    return PROMPT


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

def load_dataset(file: str) -> pd.DataFrame:
    try:
        import kagglehub
    except ImportError:
        print("[ERROR] kagglehub not installed. Run: pip install kagglehub")
        sys.exit(1)

    print(f"Downloading GPQA dataset ({file}) from Kaggle Hub...")
    dataset_path = Path(kagglehub.dataset_download(KAGGLEHUB_HANDLE))
    csv_path = dataset_path / file
    if not csv_path.exists():
        available = [p.name for p in dataset_path.glob("*.csv")]
        print(f"[ERROR] {file} not found. Available CSVs: {available}")
        sys.exit(1)
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} questions from {file}")
    return df


# ---------------------------------------------------------------------------
# Benchmark logic (ported directly from the Kaggle notebook)
# ---------------------------------------------------------------------------

Example = namedtuple("Example", ["question", "choice1", "choice2", "choice3", "choice4", "correct_index"])

LETTER_TO_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3}


def base_prompt(example: Example) -> str:
    return (
        f"\nWhat is the correct answer to this question: {example.question}\n\n"
        f"Choices:\n"
        f"(A) {example.choice1}\n"
        f"(B) {example.choice2}\n"
        f"(C) {example.choice3}\n"
        f"(D) {example.choice4}\n"
    )


def prompt_0s(example: Example) -> str:
    return (
        base_prompt(example)
        + '\n\nOutput ONLY this exact line: "The correct answer is (X)" where X is A, B, C, or D.'
        ' No other text before or after.'
    )


def get_CoT_examples(cot_df: pd.DataFrame, with_explanations: bool = True) -> str:
    output = ""
    for row in cot_df.itertuples():
        output += f"Question: {row.question}\nChoices:\n"
        output += f"(A) {row.A}\n(B) {row.B}\n(C) {row.C}\n(D) {row.D}\n"
        if with_explanations:
            output += f"Let's think step by step: \n{row.explanation}\n"
        output += f"The correct answer is ({row.correct_answer})\n"
    return output


def prompt_5s_CoT(example: Example, cot_df: pd.DataFrame) -> str:
    header = (
        "Here are some example questions from experts. An explanation is given before "
        "the final answer. Answer the final question yourself, giving your reasoning beforehand.\n"
    )
    header += get_CoT_examples(cot_df, with_explanations=True)
    header += (
        f"Question: {example.question}\n"
        f"Choices:\n"
        f"(A) {example.choice1}\n"
        f"(B) {example.choice2}\n"
        f"(C) {example.choice3}\n"
        f"(D) {example.choice4}\n"
        'Begin your response with ONLY the answer letter in this exact format: '
        '"The correct answer is (X)" where X is A, B, C, or D. '
        'Then give your step by step reasoning.\n'
    )
    return header


def prepare_example(row: dict) -> Example:
    choices = [
        row["Incorrect Answer 1"],
        row["Incorrect Answer 2"],
        row["Incorrect Answer 3"],
        row["Correct Answer"],
    ]
    random.shuffle(choices)
    return Example(
        question=row["Question"],
        choice1=choices[0],
        choice2=choices[1],
        choice3=choices[2],
        choice4=choices[3],
        correct_index=choices.index(row["Correct Answer"]),
    )


def parse_sampled_response(response: str) -> str | None:
    patterns = [
        r"answer is \(([ABCD])\)",
        r"Answer: \(([ABCD])\)",
        r"answer: \(([ABCD])\)",
        r"answer \(([ABCD])\)",
        r"correct.*?[\(\[]([ABCD])[\)\]]",
        r"[\(\[]([ABCD])[\)\]]",
        r"\b([ABCD])\b",           # bare letter fallback — last resort
    ]
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match and match.group(1).upper() in LETTER_TO_INDEX:
            return match.group(1).upper()
    return None


def run_gpqa_task(
    prompt_fn: Callable,
    model_name: str,
    data_row: dict,
    get_prompt_fn: Callable[[Example], str],
    PROMPT,
) -> dict:
    example = prepare_example(data_row)
    prompt = get_prompt_fn(example)

    response = PROMPT(model_name, [{"role": "user", "content": prompt}])
    answer_abcd = parse_sampled_response(response)
    answer_int = LETTER_TO_INDEX.get(answer_abcd) if answer_abcd else None

    return {
        "response": response,
        "full_question": prompt,
        "answer_letter": answer_abcd,
        "answer_index": answer_int,
        "correct_index": example.correct_index,
        "correct": answer_int == example.correct_index,
    }


def run_gpqa_task_sc(
    model_name: str,
    data_row: dict,
    get_prompt_fn: Callable[[Example], str],
    PROMPT,
    n_votes: int = 3,
) -> dict:
    """Self-consistency: run N times with independently shuffled answer orderings.

    Each call uses a different random seed so the four choices appear in a
    different order.  We compare votes by *answer text* (not letter) so
    position bias is cancelled out.  Majority text wins; ties fall back to
    the first vote.
    """
    correct_answer_text = data_row["Correct Answer"]
    votes = []

    for i in range(n_votes):
        random.seed(i)            # deterministic per-vote seed → reproducible
        example = prepare_example(data_row)
        prompt = get_prompt_fn(example)
        response = PROMPT(model_name, [{"role": "user", "content": prompt}])
        letter = parse_sampled_response(response)
        idx = LETTER_TO_INDEX.get(letter) if letter else None
        choices = [example.choice1, example.choice2, example.choice3, example.choice4]
        text = choices[idx] if idx is not None else None
        votes.append({"letter": letter, "index": idx, "text": text, "response": response})

    valid = [v for v in votes if v["text"] is not None]

    if not valid:
        return {
            "response": votes[0]["response"],
            "full_question": "",
            "answer_letter": None,
            "answer_index": None,
            "correct_index": None,
            "correct": False,
            "votes": [{"letter": v["letter"], "text": v["text"]} for v in votes],
            "consensus": "0/0",
        }

    text_counts = Counter(v["text"] for v in valid)
    majority_text, majority_count = text_counts.most_common(1)[0]
    winner = next(v for v in valid if v["text"] == majority_text)
    is_correct = (majority_text == correct_answer_text)

    return {
        "response": winner["response"],
        "full_question": "",
        "answer_letter": winner["letter"],
        "answer_index": winner["index"],
        "correct_index": winner["index"],   # already shuffled — use text for truth
        "correct": is_correct,
        "votes": [{"letter": v["letter"], "text": v["text"]} for v in votes],
        "consensus": f"{majority_count}/{len(valid)}",
    }


# ---------------------------------------------------------------------------
# Results saving
# ---------------------------------------------------------------------------

def save_results(outputs: list[dict], mode: str, dataset_file: str) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_DIR / f"gpqa_codette_{mode}_{timestamp}.json"

    correct = sum(o["correct"] for o in outputs)
    total = len(outputs)
    accuracy = correct / total if total else 0.0

    payload = {
        "model": "codette/full-synthesis",
        "dataset": dataset_file,
        "mode": mode,
        "accuracy": round(accuracy, 4),
        "correct": correct,
        "total": total,
        "parse_failures": sum(1 for o in outputs if o["answer_index"] is None),
        "baselines": {
            "random": 0.25,
            "gpt4_zero_shot": 0.39,
            "claude_opus_3": 0.50,
            "human_expert": 0.65,
        },
        "results": outputs,
    }

    # sc3-specific consensus stats
    if mode == "sc3":
        consensus_counts = Counter(o.get("consensus", "?") for o in outputs)
        unanimous = sum(v for k, v in consensus_counts.items() if k == "3/3")
        split = sum(v for k, v in consensus_counts.items() if k == "2/3")
        payload["sc3_stats"] = {
            "unanimous_3_3": unanimous,
            "majority_2_3": split,
            "unanimous_pct": round(unanimous / total, 3) if total else 0,
        }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return out_path


def print_summary(outputs: list[dict], mode: str):
    correct = sum(o["correct"] for o in outputs)
    total = len(outputs)
    failures = sum(1 for o in outputs if o["answer_index"] is None)
    accuracy = correct / total if total else 0.0

    print("\n" + "=" * 60)
    print(f"  Codette GPQA Results  ({mode.upper()} mode)")
    print("=" * 60)
    print(f"  Questions:      {total}")
    print(f"  Correct:        {correct}")
    print(f"  Parse failures: {failures}")
    print(f"  Accuracy:       {accuracy:.1%}")
    print()
    print("  Baselines:")
    print(f"    Random         25.0%")
    print(f"    GPT-4 0-shot   39.0%")
    print(f"    Claude Opus 3  50.0%")
    print(f"    Human expert   65.0%")
    print()
    margin = accuracy - 0.39
    sign = "+" if margin >= 0 else ""
    print(f"  vs GPT-4:  {sign}{margin:.1%}")

    if mode == "sc3":
        unanimous = sum(1 for o in outputs if o.get("consensus") == "3/3")
        split = sum(1 for o in outputs if o.get("consensus") == "2/3")
        print(f"\n  Self-consistency breakdown ({total} questions, 3 votes each):")
        print(f"    Unanimous (3/3): {unanimous}  ({unanimous/total:.0%})")
        print(f"    Majority  (2/3): {split}  ({split/total:.0%})")

    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run Codette against GPQA benchmark")
    parser.add_argument("--mode", choices=["0shot", "cot", "sc3"], default="0shot",
                        help="Prompting mode: 0shot, cot (5-shot CoT), sc3 (self-consistency 3-vote)")
    parser.add_argument("--dataset", default="gpqa_mini.csv",
                        help="CSV file to use: gpqa_mini.csv (default) or gpqa_diamond.csv")
    parser.add_argument("--port", type=int, default=CODETTE_PORT,
                        help=f"Codette server port (default: {CODETTE_PORT})")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max questions to run (omit for all)")
    parser.add_argument("--offset", type=int, default=0,
                        help="Skip the first N questions (for batched runs)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for answer shuffling")
    parser.add_argument("--full-synthesis", action="store_true",
                        help="Enable full_synthesis with all 8 adapters (~20 min/question on CPU)")
    parser.add_argument("--max-adapters", type=int, default=2,
                        help="Max adapter perspectives to use (default: 2, ~5 min/question)")
    args = parser.parse_args()

    random.seed(args.seed)

    # Verify server is up before loading the dataset
    url = CODETTE_URL_TEMPLATE.format(port=args.port)
    print(f"Checking Codette server at {url} ...", end=" ", flush=True)
    try:
        requests.get(f"http://localhost:{args.port}/", timeout=5)
        print("reachable.")
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Server not reachable. Start it with:\n  python inference/codette_server.py")
        sys.exit(1)
    except Exception:
        print("(ping failed — will try anyway)")

    # Load dataset
    dataset = load_dataset(args.dataset)
    if args.offset:
        dataset = dataset.iloc[args.offset:].reset_index(drop=True)
        print(f"Skipped first {args.offset} questions (offset mode).")
    if args.limit:
        dataset = dataset.head(args.limit)
        print(f"Limited to {args.limit} questions.")

    # Load CoT examples (needed for cot mode)
    cot_df = None
    if args.mode == "cot":
        cot_df = load_dataset("chain_of_thought_examples.csv")

    # Build PROMPT and prompt-fn
    tok_stats: list = []
    PROMPT = make_prompt_fn(port=args.port, full_synthesis=args.full_synthesis,
                            max_adapters=args.max_adapters, tok_stats=tok_stats)
    model_name = f"codette/{'full-synthesis' if args.full_synthesis else f'multi-{args.max_adapters}adapt'}"

    if args.mode in ("0shot", "sc3"):
        get_prompt_fn = prompt_0s
    else:
        get_prompt_fn = lambda ex: prompt_5s_CoT(ex, cot_df)

    # Run benchmark
    print(f"\nRunning GPQA [{args.mode}] on {len(dataset)} questions...\n")
    if args.mode == "sc3":
        print("  Self-consistency mode: 3 votes per question (seeds 0,1,2)\n")

    all_outputs = []

    for idx, row in dataset.iterrows():
        try:
            if args.mode == "sc3":
                result = run_gpqa_task_sc(
                    model_name=model_name,
                    data_row=row.to_dict(),
                    get_prompt_fn=get_prompt_fn,
                    PROMPT=PROMPT,
                    n_votes=3,
                )
                consensus_tag = f"  consensus={result.get('consensus', '?')}"
            else:
                result = run_gpqa_task(
                    prompt_fn=get_prompt_fn,
                    model_name=model_name,
                    data_row=row.to_dict(),
                    get_prompt_fn=get_prompt_fn,
                    PROMPT=PROMPT,
                )
                consensus_tag = ""

            if result["answer_letter"] is None:
                print(f"  [PARSE FAIL] Raw response: {result['response'][:300]!r}")
        except Exception as e:
            print(f"  [WARN] Row {idx} failed: {e}")
            result = {
                "response": f"ERROR: {e}",
                "full_question": "",
                "answer_letter": None,
                "answer_index": None,
                "correct_index": None,
                "correct": False,
            }
            consensus_tag = ""

        running_correct = sum(o["correct"] for o in all_outputs) + int(result["correct"])
        running_total = len(all_outputs) + 1
        print(f"  Row {idx:>3}  correct={result['correct']}  "
              f"predicted={result['answer_letter']}"
              f"{consensus_tag}  "
              f"running={running_correct}/{running_total} "
              f"({running_correct/running_total:.0%})")
        all_outputs.append(result)

    # Save and print
    out_path = save_results(all_outputs, args.mode, args.dataset)
    print_summary(all_outputs, args.mode)

    # tok/s summary
    if tok_stats:
        total_tok = sum(t for t, _, _ in tok_stats)
        total_s   = sum(s for _, s, _ in tok_stats)
        mean_tps  = total_tok / total_s if total_s > 0 else 0
        per_call  = [tps for _, _, tps in tok_stats if tps > 0]
        med_tps   = sorted(per_call)[len(per_call) // 2] if per_call else 0
        print(f"\n── Throughput ──────────────────────────────────")
        print(f"  Total tokens : {total_tok:,}")
        print(f"  Total time   : {total_s:.1f}s")
        print(f"  Mean tok/s   : {mean_tps:.2f}")
        print(f"  Median tok/s : {med_tps:.2f}")
        print(f"  Calls logged : {len(tok_stats)}")

    print(f"\nFull results saved to: {out_path}")


if __name__ == "__main__":
    main()
