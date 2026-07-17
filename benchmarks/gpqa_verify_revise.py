#!/usr/bin/env python3
"""GPQA harness for Verify-and-Revise — paired against single-pass by design.

Every question yields TWO answers from the SAME derive call:
    single-pass  = the derive answer (what newton alone said)
    verify-revise = the final answer after attack + hold/revise

So the comparison is perfectly paired — same question, same shuffle, same
derive sample — and the delta isolates exactly what the critic loop adds.
McNemar-ready output (see benchmarks/paired_analysis.py).

Runs through the LIVE server API (/api/chat with forced adapters), so it
measures the real system: v4 adapters, locks, the lot. Nothing is wired
into production — this is the shadow evaluation that decides whether
verify-and-revise earns wiring.

Usage:
    python benchmarks/gpqa_verify_revise.py --limit 50
    python benchmarks/gpqa_verify_revise.py --limit 50 --offset 50   # resume
    python benchmarks/gpqa_verify_revise.py --dataset gpqa_diamond.csv --limit 198
"""

import argparse
import json
import random
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from reasoning_forge.verify_revise import VerifyReviseEngine, parse_letter

RESULTS_DIR = REPO / "data" / "results" / "verify_revise"
KAGGLEHUB_HANDLE = "open-benchmarks/gpqa-a-graduate-level-google-proof-q-and-a"
LETTER_TO_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3}
SEED = 42


def load_dataset(file: str):
    import kagglehub
    import csv
    dataset_path = Path(kagglehub.dataset_download(KAGGLEHUB_HANDLE))
    csv_path = dataset_path / file
    with open(csv_path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def make_llm_call(port: int, timeout: int):
    def llm_call(user_prompt: str, system_prompt: str, adapter: str) -> str:
        # The server's forced-adapter path uses the adapter's own system
        # prompt; we carry the step's METHOD instructions in the user prompt
        # so the same route works for derive/attack/revise.
        payload = json.dumps({
            "query": f"{system_prompt}\n\n---\n\n{user_prompt}",
            "adapter": adapter,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/chat", data=payload,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        if "error" in data and not data.get("response"):
            raise RuntimeError(data["error"])
        return str(data.get("response", ""))
    return llm_call


def build_question_block(row: dict, row_i: int):
    random.seed(SEED + row_i)   # identical shuffles to phase0 runs
    choices = [row["Incorrect Answer 1"], row["Incorrect Answer 2"],
               row["Incorrect Answer 3"], row["Correct Answer"]]
    random.shuffle(choices)
    correct_index = choices.index(row["Correct Answer"])
    block = (
        f"What is the correct answer to this question: {row['Question']}\n\n"
        f"Choices:\n(A) {choices[0]}\n(B) {choices[1]}\n"
        f"(C) {choices[2]}\n(D) {choices[3]}"
    )
    return block, correct_index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="gpqa_mini.csv")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--port", type=int, default=7860)
    ap.add_argument("--timeout", type=int, default=600, help="per-call timeout (s)")
    ap.add_argument("--derive-adapter", default="newton")
    ap.add_argument("--critic-adapter", default="quantum")
    args = ap.parse_args()

    rows = load_dataset(args.dataset)[args.offset:args.offset + args.limit]
    print(f"Verify-and-Revise: {len(rows)} questions from {args.dataset} "
          f"(offset {args.offset}), derive={args.derive_adapter}, "
          f"critic={args.critic_adapter}")

    engine = VerifyReviseEngine(
        make_llm_call(args.port, args.timeout),
        derive_adapter=args.derive_adapter,
        critic_adapter=args.critic_adapter)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / (
        f"vr_{args.dataset.replace('.csv','')}_o{args.offset}_n{len(rows)}_"
        f"{time.strftime('%Y%m%d_%H%M')}.json")

    results = []
    sp_correct = vr_correct = changed_total = changed_to_right = changed_to_wrong = 0

    for i, row in enumerate(rows):
        block, correct_index = build_question_block(row, args.offset + i)
        t0 = time.time()
        trace = engine.run(block)
        elapsed = time.time() - t0

        sp_idx = LETTER_TO_INDEX.get(trace.derive_answer) if trace.derive_answer else None
        vr_idx = LETTER_TO_INDEX.get(trace.final_answer) if trace.final_answer else None
        sp_ok = sp_idx == correct_index
        vr_ok = vr_idx == correct_index
        sp_correct += sp_ok
        vr_correct += vr_ok
        if trace.decision == "revise":
            changed_total += 1
            if vr_ok and not sp_ok:
                changed_to_right += 1
            elif sp_ok and not vr_ok:
                changed_to_wrong += 1

        n = i + 1
        print(f"  {args.offset+i:3d} sp={trace.derive_answer}({'Y' if sp_ok else 'n'}) "
              f"verdict={trace.attack_verdict:<8} decision={trace.decision:<11} "
              f"vr={trace.final_answer}({'Y' if vr_ok else 'n'}) | "
              f"SP {sp_correct}/{n} ({sp_correct/n:.0%})  "
              f"VR {vr_correct}/{n} ({vr_correct/n:.0%})  [{elapsed:.0f}s]",
              flush=True)

        results.append({
            "row": args.offset + i,
            "correct_index": correct_index,
            "sp_correct": bool(sp_ok), "vr_correct": bool(vr_ok),
            "elapsed_s": round(elapsed, 1),
            **trace.to_dict(),
        })
        # checkpoint after every question — a crash loses nothing
        out_path.write_text(json.dumps({
            "config": vars(args), "n": n,
            "single_pass": {"correct": sp_correct, "accuracy": round(sp_correct/n*100, 2)},
            "verify_revise": {"correct": vr_correct, "accuracy": round(vr_correct/n*100, 2)},
            "revisions": {"total": changed_total, "to_right": changed_to_right,
                          "to_wrong": changed_to_wrong},
            "results": results,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    n = len(results) or 1
    print(f"\n{'='*60}")
    print(f"single-pass ({args.derive_adapter}):  {sp_correct}/{n}  ({sp_correct/n:.1%})")
    print(f"verify-revise:                        {vr_correct}/{n}  ({vr_correct/n:.1%})")
    print(f"delta: {(vr_correct-sp_correct)/n*100:+.1f}pp")
    print(f"revisions: {changed_total} total — {changed_to_right} fixed a wrong answer, "
          f"{changed_to_wrong} broke a right one")
    print(f"\nResults: {out_path}")


if __name__ == "__main__":
    main()
