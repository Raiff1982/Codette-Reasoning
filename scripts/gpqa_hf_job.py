# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "torch>=2.1.0",
#     "transformers>=4.44.0",
#     "peft>=0.11.0",
#     "accelerate>=0.30.0",
#     "bitsandbytes>=0.43.0",
#     "kagglehub>=0.2.0",
#     "pandas",
#     "huggingface_hub>=0.24.0",
# ]
# ///
"""
Codette GPQA Benchmark — HuggingFace Jobs Script
=================================================
Runs GPQA diamond (198 questions) against Raiff1982/codette-llama-3.1-8b-merged
on an A10G GPU via HuggingFace Jobs, then uploads results to HF Hub.

Submit via:
    huggingface-cli job run --flavor a10g scripts/gpqa_hf_job.py

Or with uv on a local GPU:
    uv run scripts/gpqa_hf_job.py

Environment variables (set as HF job secrets):
    HF_TOKEN         — required for model access + result upload
    KAGGLE_USERNAME  — required for kagglehub dataset download
    KAGGLE_KEY       — required for kagglehub dataset download
    GPQA_MODE        — 0shot (default) | sc3
    GPQA_LIMIT       — max questions (default: all 198)
"""

import json, os, random, re, time
from collections import Counter, namedtuple
from pathlib import Path

import pandas as pd
import torch
from huggingface_hub import HfApi, get_token, upload_file
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# ── Config ────────────────────────────────────────────────────────────────────
BASE_MODEL   = "Raiff1982/codette-llama-3.1-8b-merged"
ADAPTER_REPO = "Raiff1982/codette-lora-adapters"
RESULTS_REPO = "Raiff1982/codette-training-data"   # upload results here
GPQA_HANDLE  = "open-benchmarks/gpqa-a-graduate-level-google-proof-q-and-a"
DATASET_FILE = "gpqa_diamond.csv"
MODE         = os.environ.get("GPQA_MODE", "0shot")
LIMIT        = int(os.environ.get("GPQA_LIMIT", "0")) or None
N_VOTES      = 3
SEED         = 42
HF_TOKEN     = os.environ.get("HF_TOKEN") or get_token()

# Domain-conditioned adapter routing
DOMAIN_ROUTER = {
    "physics": "newton", "mechanics": "newton",
    "electro": "newton", "thermodynamic": "newton",
    "quantum": "quantum", "probability": "quantum",
    "wave": "quantum",   "orbital": "quantum",
    "chemical": "davinci", "molecule": "davinci", "reaction": "davinci",
    "enzyme": "systems_architecture", "protein": "systems_architecture",
    "cell": "systems_architecture",   "biology": "systems_architecture",
    "gene": "systems_architecture",   "dna": "systems_architecture",
    "metabol": "systems_architecture",
}

SYSTEM_PROMPT = (
    "You are Codette, a multi-perspective reasoning AI. "
    "Answer graduate-level multiple-choice questions with rigorous accuracy. "
    "Output ONLY this exact line: \"The correct answer is (X)\" where X is A, B, C, or D. "
    "No other text."
)

LETTER_TO_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3}
Example = namedtuple("Example", ["question", "choice1", "choice2", "choice3", "choice4", "correct_index"])


def load_model():
    print(f"Loading {BASE_MODEL}...")
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
    )
    tok = AutoTokenizer.from_pretrained(BASE_MODEL, token=HF_TOKEN)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, quantization_config=bnb, device_map="auto",
        torch_dtype=torch.bfloat16, token=HF_TOKEN,
    )
    print(f"Model loaded on {next(model.parameters()).device}")
    return model, tok


_adapter_cache: dict = {}

def get_model(base_model, question_text: str):
    q_lower = question_text.lower()
    adapter = next(
        (v for k, v in DOMAIN_ROUTER.items() if k in q_lower),
        "base"
    )
    if adapter == "base":
        return base_model, "base"
    if adapter not in _adapter_cache:
        try:
            _adapter_cache[adapter] = PeftModel.from_pretrained(
                base_model, ADAPTER_REPO, subfolder=f"{adapter}_v2", token=HF_TOKEN
            )
            print(f"  Loaded adapter: {adapter}")
        except Exception as e:
            print(f"  Adapter {adapter} failed ({e}), using base")
            _adapter_cache[adapter] = base_model
    return _adapter_cache[adapter], adapter


def build_prompt(tok, example: Example) -> str:
    user = (
        f"\nWhat is the correct answer to this question: {example.question}\n\n"
        f"Choices:\n(A) {example.choice1}\n(B) {example.choice2}\n"
        f"(C) {example.choice3}\n(D) {example.choice4}\n\n"
        'Output ONLY: "The correct answer is (X)" where X is A, B, C, or D.'
    )
    msgs = [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user}]
    return tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)


def generate(model, tok, prompt: str, temperature: float = 0.0) -> str:
    enc = tok(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **enc, max_new_tokens=64,
            do_sample=temperature > 0,
            temperature=temperature if temperature > 0 else 1.0,
            top_p=0.9 if temperature > 0 else 1.0,
            pad_token_id=tok.pad_token_id,
        )
    return tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def parse_answer(text: str) -> str | None:
    for pat in [r"answer is \(([ABCD])\)", r"[\(\[]([ABCD])[\)\]]", r"\b([ABCD])\b"]:
        m = re.search(pat, text, re.IGNORECASE)
        if m and m.group(1).upper() in LETTER_TO_INDEX:
            return m.group(1).upper()
    return None


def prepare_example(row: dict) -> Example:
    choices = [row["Incorrect Answer 1"], row["Incorrect Answer 2"],
               row["Incorrect Answer 3"], row["Correct Answer"]]
    random.shuffle(choices)
    return Example(
        question=row["Question"],
        choice1=choices[0], choice2=choices[1],
        choice3=choices[2], choice4=choices[3],
        correct_index=choices.index(row["Correct Answer"]),
    )


def run_0shot(base_model, tok, df: pd.DataFrame) -> list[dict]:
    results = []
    for i, (_, row) in enumerate(df.iterrows()):
        random.seed(SEED + i)
        example = prepare_example(row.to_dict())
        model, adapter = get_model(base_model, row["Question"])
        prompt = build_prompt(tok, example)

        t0 = time.time()
        response = generate(model, tok, prompt)
        elapsed = time.time() - t0

        letter = parse_answer(response)
        idx = LETTER_TO_INDEX.get(letter) if letter else None
        correct = (idx == example.correct_index)
        running = sum(r["correct"] for r in results) + correct
        print(f"  Row {i:3d}  correct={correct}  predicted={letter}  adapter={adapter}  "
              f"running={running}/{i+1} ({running/(i+1):.0%})  [{elapsed:.1f}s]")
        results.append({
            "row": i, "correct": correct, "predicted": letter,
            "adapter": adapter, "response": response, "elapsed_s": round(elapsed, 1),
        })
    return results


def run_sc3(base_model, tok, df: pd.DataFrame) -> list[dict]:
    results = []
    for i, (_, row) in enumerate(df.iterrows()):
        correct_text = row["Correct Answer"]
        votes = []
        for v in range(N_VOTES):
            random.seed(v * 1000 + i)
            example = prepare_example(row.to_dict())
            model, adapter = get_model(base_model, row["Question"])
            response = generate(model, tok, build_prompt(tok, example), temperature=0.7)
            letter = parse_answer(response)
            idx = LETTER_TO_INDEX.get(letter) if letter else None
            choices = [example.choice1, example.choice2, example.choice3, example.choice4]
            votes.append({"letter": letter, "text": choices[idx] if idx is not None else None})

        valid = [v for v in votes if v["text"]]
        if not valid:
            results.append({"row": i, "correct": False, "consensus": "0/0", "votes": votes})
            continue
        counts = Counter(v["text"] for v in valid)
        majority_text, majority_count = counts.most_common(1)[0]
        winner = next(v for v in valid if v["text"] == majority_text)
        is_correct = (majority_text == correct_text)
        running = sum(r["correct"] for r in results) + is_correct
        print(f"  Row {i:3d}  correct={is_correct}  consensus={majority_count}/{len(valid)}  "
              f"running={running}/{i+1} ({running/(i+1):.0%})")
        results.append({
            "row": i, "correct": is_correct, "predicted": winner["letter"],
            "consensus": f"{majority_count}/{len(valid)}", "votes": votes,
        })
    return results


def upload_results(out_path: Path):
    try:
        api = HfApi(token=HF_TOKEN)
        api.upload_file(
            path_or_fileobj=str(out_path),
            path_in_repo=f"gpqa_results/{out_path.name}",
            repo_id=RESULTS_REPO,
            repo_type="dataset",
        )
        print(f"Results uploaded to {RESULTS_REPO}/gpqa_results/{out_path.name}")
    except Exception as e:
        print(f"Upload failed: {e} (results saved locally at {out_path})")


def main():
    import kagglehub
    print(f"Downloading GPQA ({DATASET_FILE})...")
    dataset_path = Path(kagglehub.dataset_download(GPQA_HANDLE))
    df = pd.read_csv(dataset_path / DATASET_FILE)
    if LIMIT:
        df = df.head(LIMIT)
    print(f"Loaded {len(df)} questions. Mode: {MODE}")

    base_model, tok = load_model()

    print(f"\nRunning [{MODE.upper()}]...")
    outputs = run_sc3(base_model, tok, df) if MODE == "sc3" else run_0shot(base_model, tok, df)

    correct = sum(o["correct"] for o in outputs)
    total = len(outputs)
    acc = correct / total if total else 0.0

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = Path(f"/tmp/gpqa_codette_{MODE}_diamond_{ts}.json")
    payload = {
        "model": BASE_MODEL, "dataset": DATASET_FILE, "mode": MODE,
        "accuracy": round(acc, 4), "correct": correct, "total": total,
        "parse_failures": sum(1 for o in outputs if not o.get("predicted")),
        "baselines": {"random": 0.25, "gpt4_zero_shot": 0.39,
                      "claude_opus_3": 0.50, "human_expert": 0.65},
        "results": outputs,
    }
    out_path.write_text(json.dumps(payload, indent=2))

    print(f"\n{'='*60}")
    print(f"  GPQA [{MODE.upper()}] — diamond — {correct}/{total} = {acc:.1%}")
    print(f"  vs GPT-4 0-shot: {acc-0.39:+.1%}")
    print(f"  vs Claude Opus 3: {acc-0.50:+.1%}")
    print(f"{'='*60}")

    upload_results(out_path)


if __name__ == "__main__":
    main()
