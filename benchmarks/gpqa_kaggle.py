"""
Codette GPQA Benchmark — Kaggle/HuggingFace Inference
======================================================
Runs the full GPQA diamond (198 questions) against Raiff1982/codette-llama-3.1-8b-merged
directly via transformers + PEFT, bypassing the local server.

Designed to run on:
  - Kaggle notebook (GPU T4/P100 — free tier)
  - HuggingFace Spaces / local GPU
  - Any machine with 8+ GB VRAM or 16+ GB RAM

Usage (Kaggle):
  Set HF_TOKEN as a Kaggle secret, attach the GPQA dataset, run all cells.

Usage (local):
  pip install torch transformers peft accelerate bitsandbytes kagglehub pandas
  HF_TOKEN=hf_... python benchmarks/gpqa_kaggle.py

Modes:
  0shot   — single-pass, answer only
  sc3     — 3-vote self-consistency, vote by answer text
"""

# ── Install deps (needed for Kaggle kernel cold-start) ──────────────────────
import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q",
    "torch", "transformers>=4.44.0", "peft>=0.11.0", "accelerate>=0.30.0",
    "bitsandbytes>=0.43.0", "kagglehub[pandas-datasets]", "pandas",
    "huggingface_hub>=0.24.0",
])

# ── Imports ──────────────────────────────────────────────────────────────────
import json, os, random, re, time
from collections import Counter, namedtuple
from pathlib import Path

import pandas as pd
import torch
from huggingface_hub import get_token
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# ── Config ───────────────────────────────────────────────────────────────────
BASE_MODEL  = "Raiff1982/codette-llama-3.1-8b-merged"
ADAPTER_REPO = "Raiff1982/codette-lora-adapters"
GPQA_HANDLE  = "open-benchmarks/gpqa-a-graduate-level-google-proof-q-and-a"
DATASET_FILE = "gpqa_diamond.csv"
MODE         = os.environ.get("GPQA_MODE", "0shot")       # 0shot | sc3
N_VOTES      = 3                                            # for sc3
SEED         = 42
MAX_NEW_TOKENS = 64
TEMPERATURE    = 0.0  # greedy for 0shot; sc3 uses temp=0.7 per vote
# Load HF token — Kaggle exposes secrets via UserSecretsClient, not os.environ
def _load_hf_token() -> str | None:
    try:
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret("HF_TOKEN")
    except Exception:
        pass
    return os.environ.get("HF_TOKEN") or get_token()

HF_TOKEN = _load_hf_token()

# Authenticate so all HF calls use the token automatically
if HF_TOKEN:
    from huggingface_hub import login
    login(token=HF_TOKEN, add_to_git_credential=False)

# Domain-conditioned adapter routing for GPQA (physics/chem/bio)
DOMAIN_ROUTER = {
    # keywords → adapter subfolder in ADAPTER_REPO
    "physics":         "newton",
    "mechanics":       "newton",
    "electro":         "newton",
    "thermodynamic":   "newton",
    "quantum":         "quantum",
    "probability":     "quantum",
    "wave":            "quantum",
    "orbital":         "quantum",
    "chemical":        "davinci",
    "molecule":        "davinci",
    "reaction":        "davinci",
    "enzyme":          "systems_architecture",
    "protein":         "systems_architecture",
    "cell":            "systems_architecture",
    "biology":         "systems_architecture",
    "organism":        "systems_architecture",
    "gene":            "systems_architecture",
    "dna":             "systems_architecture",
    "metabol":         "systems_architecture",
}

SYSTEM_PROMPT = (
    "You are Codette, a multi-perspective reasoning AI. "
    "Answer graduate-level multiple-choice questions with rigorous accuracy. "
    "Output ONLY this exact line: \"The correct answer is (X)\" where X is A, B, C, or D. "
    "No other text."
)

LETTER_TO_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3}
Example = namedtuple("Example", ["question", "choice1", "choice2", "choice3", "choice4", "correct_index"])


# ── Model loading ─────────────────────────────────────────────────────────────

def load_base_model():
    print(f"\nLoading base model: {BASE_MODEL}")
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    tok = AutoTokenizer.from_pretrained(BASE_MODEL, token=HF_TOKEN)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        token=HF_TOKEN,
    )
    print("Base model loaded.")
    return model, tok


_adapter_cache: dict[str, PeftModel] = {}

def get_model_for_question(base_model, tok, question_text: str):
    """Return (model, adapter_name) — apply domain-conditioned adapter if available."""
    q_lower = question_text.lower()
    adapter = "base"
    for keyword, adapter_name in DOMAIN_ROUTER.items():
        if keyword in q_lower:
            adapter = adapter_name
            break

    if adapter == "base":
        return base_model, "base"

    if adapter not in _adapter_cache:
        print(f"  Loading adapter: {adapter}", end="... ", flush=True)
        try:
            adapted = PeftModel.from_pretrained(
                base_model, ADAPTER_REPO, subfolder=f"{adapter}_v2", token=HF_TOKEN
            )
            _adapter_cache[adapter] = adapted
            print("OK")
        except Exception as e:
            print(f"FAILED ({e}) — falling back to base")
            _adapter_cache[adapter] = base_model
    return _adapter_cache[adapter], adapter


# ── Inference ─────────────────────────────────────────────────────────────────

def build_prompt(tok, example: Example) -> str:
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
    msgs = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_content},
    ]
    return tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)


def generate(model, tok, prompt: str, temperature: float = 0.0) -> str:
    enc = tok(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **enc,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=(temperature > 0),
            temperature=temperature if temperature > 0 else 1.0,
            top_p=0.9 if temperature > 0 else 1.0,
            pad_token_id=tok.pad_token_id,
        )
    return tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def parse_answer(text: str) -> str | None:
    patterns = [
        r"answer is \(([ABCD])\)",
        r"answer: \(([ABCD])\)",
        r"answer \(([ABCD])\)",
        r"correct.*?[\(\[]([ABCD])[\)\]]",
        r"[\(\[]([ABCD])[\)\]]",
        r"\b([ABCD])\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m and m.group(1).upper() in LETTER_TO_INDEX:
            return m.group(1).upper()
    return None


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
        choice1=choices[0], choice2=choices[1],
        choice3=choices[2], choice4=choices[3],
        correct_index=choices.index(row["Correct Answer"]),
    )


# ── Benchmark runners ─────────────────────────────────────────────────────────

def run_0shot(base_model, tok, df: pd.DataFrame) -> list[dict]:
    results = []
    for i, (_, row) in enumerate(df.iterrows()):
        random.seed(SEED + i)
        example = prepare_example(row.to_dict())
        model, adapter = get_model_for_question(base_model, tok, row["Question"])
        prompt = build_prompt(tok, example)

        t0 = time.time()
        response = generate(model, tok, prompt, temperature=0.0)
        elapsed = time.time() - t0

        letter = parse_answer(response)
        idx = LETTER_TO_INDEX.get(letter) if letter else None
        correct = (idx == example.correct_index)

        running_correct = sum(r["correct"] for r in results) + correct
        print(f"  Row {i:3d}  correct={correct}  predicted={letter}  adapter={adapter}  "
              f"running={running_correct}/{i+1} ({running_correct/(i+1):.0%})  [{elapsed:.1f}s]")

        results.append({
            "row": i, "correct": correct,
            "predicted": letter, "adapter": adapter,
            "answer_index": idx, "correct_index": example.correct_index,
            "response": response, "elapsed_s": round(elapsed, 1),
        })
    return results


def run_sc3(base_model, tok, df: pd.DataFrame) -> list[dict]:
    results = []
    for i, (_, row) in enumerate(df.iterrows()):
        correct_text = row["Correct Answer"]
        votes = []
        for vote_i in range(N_VOTES):
            random.seed(vote_i * 1000 + i)
            example = prepare_example(row.to_dict())
            model, adapter = get_model_for_question(base_model, tok, row["Question"])
            prompt = build_prompt(tok, example)
            response = generate(model, tok, prompt, temperature=0.7)
            letter = parse_answer(response)
            idx = LETTER_TO_INDEX.get(letter) if letter else None
            choices = [example.choice1, example.choice2, example.choice3, example.choice4]
            text = choices[idx] if idx is not None else None
            votes.append({"letter": letter, "idx": idx, "text": text, "adapter": adapter})

        valid = [v for v in votes if v["text"]]
        if not valid:
            results.append({"row": i, "correct": False, "votes": votes, "consensus": "0/0"})
            continue

        counts = Counter(v["text"] for v in valid)
        majority_text, majority_count = counts.most_common(1)[0]
        winner = next(v for v in valid if v["text"] == majority_text)
        is_correct = (majority_text == correct_text)

        running_correct = sum(r["correct"] for r in results) + is_correct
        print(f"  Row {i:3d}  correct={is_correct}  consensus={majority_count}/{len(valid)}  "
              f"running={running_correct}/{i+1} ({running_correct/(i+1):.0%})")

        results.append({
            "row": i, "correct": is_correct,
            "predicted": winner["letter"], "adapter": winner["adapter"],
            "consensus": f"{majority_count}/{len(valid)}",
            "votes": [{"letter": v["letter"], "text": v["text"]} for v in votes],
        })
    return results


# ── Save results ──────────────────────────────────────────────────────────────

def save_results(outputs: list[dict], mode: str) -> Path:
    correct = sum(o["correct"] for o in outputs)
    total = len(outputs)
    acc = correct / total if total else 0.0

    payload = {
        "model": BASE_MODEL,
        "dataset": DATASET_FILE,
        "mode": mode,
        "accuracy": round(acc, 4),
        "correct": correct,
        "total": total,
        "parse_failures": sum(1 for o in outputs if o.get("predicted") is None),
        "baselines": {
            "random": 0.25,
            "gpt4_zero_shot": 0.39,
            "claude_opus_3": 0.50,
            "human_expert": 0.65,
        },
        "results": outputs,
    }

    if mode == "sc3":
        unanimous = sum(1 for o in outputs if o.get("consensus") == "3/3")
        payload["sc3_stats"] = {
            "unanimous_3_3": unanimous,
            "unanimous_pct": round(unanimous / total, 3) if total else 0,
        }

    ts = time.strftime("%Y%m%d_%H%M%S")
    # Kaggle output goes to /kaggle/working/; local goes to data/results/
    out_dir = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path("data/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"gpqa_codette_{mode}_diamond_{ts}.json"
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  Codette GPQA Results  ({mode.upper()} — diamond)")
    print(f"{'='*60}")
    print(f"  Questions:      {total}")
    print(f"  Correct:        {correct}")
    print(f"  Accuracy:       {acc:.1%}")
    print(f"  vs Random:      +{acc-0.25:.1%}")
    print(f"  vs GPT-4:       {acc-0.39:+.1%}")
    print(f"  vs Claude Opus3:{acc-0.50:+.1%}")
    print(f"  Saved:          {out_path}")
    print(f"{'='*60}")
    return out_path


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import kagglehub
    from kagglehub import KaggleDatasetAdapter
    print(f"Loading GPQA ({DATASET_FILE})...")
    df = kagglehub.load_dataset(
        KaggleDatasetAdapter.PANDAS,
        GPQA_HANDLE,
        DATASET_FILE,
    )
    print(f"Loaded {len(df)} questions.")

    base_model, tok = load_base_model()

    print(f"\nRunning GPQA [{MODE.upper()}] on {len(df)} questions...")
    if MODE == "sc3":
        outputs = run_sc3(base_model, tok, df)
    else:
        outputs = run_0shot(base_model, tok, df)

    save_results(outputs, MODE)


if __name__ == "__main__":
    main()
