"""
Phase 0 (Kaggle) — adapter ablation arms on GPU
=================================================
Answers the roadmap's first question with numbers, fast:
    "Do the adapters help at all?"

Arms (each on identical questions, identical shuffles):
    base       — Raiff1982/codette-llama-3.1-8b-merged, no adapter
    newton     — base + v4 newton adapter forced on EVERY question
                 (no domain routing — that would blur the arm)

The layer ablation (LOCK/AAP/complexity/manifold) cannot run here — those
live in the local server stack. Use benchmarks/phase0_ablation.py for that.

HOW TO RUN (Kaggle):
  1. New Notebook -> GPU T4 x2 -> Internet ON
  2. Secrets -> HF_TOKEN
  3. Paste this file into one cell, run. (~1.5h both arms, n=198)

Env knobs (optional):
    PHASE0_ARMS=base,newton     which arms to run
    PHASE0_LIMIT=198            questions per arm
    PHASE0_ADAPTER_REPO=Raiff1982/codette-adapters-v4
"""

# ── Install deps (Kaggle cold start) ─────────────────────────────────────────
import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q",
    "torch", "transformers>=4.46,<5", "peft>=0.11.0", "accelerate>=0.30.0",
    "bitsandbytes>=0.43.0", "kagglehub[pandas-datasets]", "pandas",
    "huggingface_hub>=0.24.0",
])

import json, os, random, re, time
from collections import namedtuple
from pathlib import Path

import pandas as pd
import torch
from huggingface_hub import get_token
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# ── Config ───────────────────────────────────────────────────────────────────
BASE_MODEL   = "Raiff1982/codette-llama-3.1-8b-merged"
ADAPTER_REPO = os.environ.get("PHASE0_ADAPTER_REPO", "Raiff1982/codette-adapters-v4")
GPQA_HANDLE  = "open-benchmarks/gpqa-a-graduate-level-google-proof-q-and-a"
DATASET_FILE = "gpqa_diamond.csv"
ARMS         = [a.strip() for a in os.environ.get("PHASE0_ARMS", "base,newton").split(",")]
LIMIT        = int(os.environ.get("PHASE0_LIMIT", "198"))
SEED         = 42
MAX_NEW_TOKENS = 64

def _load_hf_token():
    try:
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret("HF_TOKEN")
    except Exception:
        pass
    return os.environ.get("HF_TOKEN") or get_token()

HF_TOKEN = _load_hf_token()
if HF_TOKEN:
    from huggingface_hub import login
    login(token=HF_TOKEN, add_to_git_credential=False)

SYSTEM_PROMPT = (
    "You are Codette, a multi-perspective reasoning AI. "
    "Answer graduate-level multiple-choice questions with rigorous accuracy. "
    "Output ONLY this exact line: \"The correct answer is (X)\" where X is A, B, C, or D. "
    "No other text."
)

LETTER_TO_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3}
Example = namedtuple("Example", ["question", "choice1", "choice2", "choice3", "choice4", "correct_index"])


def build_prompt(tok, example):
    user_content = (
        f"\nWhat is the correct answer to this question: {example.question}\n\n"
        f"Choices:\n"
        f"(A) {example.choice1}\n"
        f"(B) {example.choice2}\n"
        f"(C) {example.choice3}\n"
        f"(D) {example.choice4}\n\n"
        'Output ONLY this exact line: "The correct answer is (X)" where X is A, B, C, or D.'
        ' No other text before or after.'
    )
    msgs = [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}]
    return tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)


def generate(model, tok, prompt):
    enc = tok(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=MAX_NEW_TOKENS,
                             do_sample=False, pad_token_id=tok.pad_token_id)
    return tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def parse_answer(text):
    for pat in [r"answer is \(([ABCD])\)", r"answer: \(([ABCD])\)",
                r"answer \(([ABCD])\)", r"correct.*?[\(\[]([ABCD])[\)\]]",
                r"[\(\[]([ABCD])[\)\]]", r"\b([ABCD])\b"]:
        m = re.search(pat, text, re.IGNORECASE)
        if m and m.group(1).upper() in LETTER_TO_INDEX:
            return m.group(1).upper()
    return None


def prepare_example(row, row_i):
    # Seed by row index ONLY — identical shuffle across arms, so any score
    # difference is the adapter, not the answer ordering.
    random.seed(SEED + row_i)
    choices = [row["Incorrect Answer 1"], row["Incorrect Answer 2"],
               row["Incorrect Answer 3"], row["Correct Answer"]]
    random.shuffle(choices)
    return Example(question=row["Question"],
                   choice1=choices[0], choice2=choices[1],
                   choice3=choices[2], choice4=choices[3],
                   correct_index=choices.index(row["Correct Answer"]))


def run_arm(arm_name, model, tok, df):
    results = []
    print(f"\n{'='*60}\nARM: {arm_name}  ({len(df)} questions)\n{'='*60}", flush=True)
    for i, (_, row) in enumerate(df.iterrows()):
        example = prepare_example(row.to_dict(), i)
        prompt = build_prompt(tok, example)
        t0 = time.time()
        response = generate(model, tok, prompt)
        letter = parse_answer(response)
        idx = LETTER_TO_INDEX.get(letter) if letter else None
        correct = (idx == example.correct_index)
        results.append({"row": i, "correct": bool(correct), "predicted": letter,
                        "correct_index": example.correct_index,
                        "response": response[:200],
                        "elapsed_s": round(time.time() - t0, 1)})
        running = sum(r["correct"] for r in results)
        print(f"  [{arm_name}] {i:3d}  correct={correct}  pred={letter}  "
              f"running={running}/{i+1} ({running/(i+1):.0%})", flush=True)
    return results


# ── Load data ─────────────────────────────────────────────────────────────────
import kagglehub
dataset_path = Path(kagglehub.dataset_download(GPQA_HANDLE))
df = pd.read_csv(dataset_path / DATASET_FILE).head(LIMIT)
print(f"Dataset: {DATASET_FILE}, {len(df)} questions")

# ── Load base once ────────────────────────────────────────────────────────────
print(f"\nLoading base: {BASE_MODEL}")
bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                         bnb_4bit_compute_dtype=torch.bfloat16,
                         bnb_4bit_use_double_quant=True)
# Merged repo's tokenizer_config declares a v5-only class name; fall back
# to PreTrainedTokenizerFast on transformers <5 (same fix as the trainer).
try:
    tok = AutoTokenizer.from_pretrained(BASE_MODEL, token=HF_TOKEN)
except ValueError:
    from transformers import PreTrainedTokenizerFast
    tok = PreTrainedTokenizerFast.from_pretrained(BASE_MODEL, token=HF_TOKEN)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
assert tok.chat_template, "chat template missing from tokenizer"
base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL, quantization_config=bnb, device_map="auto",
    torch_dtype=torch.bfloat16, token=HF_TOKEN)

# ── Run arms (base first — wrapping with PEFT after keeps base runs clean) ───
all_results = {}
summary = {}
for arm in ARMS:
    if arm == "base":
        model = base_model
    else:
        print(f"\nLoading adapter '{arm}' from {ADAPTER_REPO}")
        model = PeftModel.from_pretrained(base_model, ADAPTER_REPO,
                                          subfolder=arm, token=HF_TOKEN)
    res = run_arm(arm, model, tok, df)
    all_results[arm] = res
    n_correct = sum(r["correct"] for r in res)
    summary[arm] = {"correct": n_correct, "total": len(res),
                    "accuracy": round(n_correct / len(res) * 100, 2)}
    # Save immediately after each arm
    out = Path(f"phase0_{arm}_results.json")
    out.write_text(json.dumps({"arm": arm, "summary": summary[arm],
                               "results": res}, indent=2), encoding="utf-8")
    print(f"\n  {arm}: {summary[arm]['accuracy']}% "
          f"({n_correct}/{len(res)}) -> {out}", flush=True)
    if arm != "base":
        # Unload adapter so a later arm starts from clean base
        try:
            model = model.unload()
        except Exception:
            pass

print(f"\n{'='*60}\nPHASE 0 (KAGGLE) COMPLETE\n{'='*60}")
for arm, s in summary.items():
    print(f"  {arm:<12} {s['accuracy']}%  ({s['correct']}/{s['total']})")
if "base" in summary and len(summary) > 1:
    b = summary["base"]["accuracy"]
    for arm, s in summary.items():
        if arm != "base":
            print(f"  {arm} vs base: {s['accuracy'] - b:+.2f}pp")
print("\nDownload the phase0_*_results.json files from the notebook output.")
