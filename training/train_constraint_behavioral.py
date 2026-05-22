# /// script
# dependencies = [
#   "torch",
#   "transformers",
#   "peft",
#   "trl",
#   "datasets",
#   "bitsandbytes",
#   "accelerate",
#   "huggingface_hub",
#   "sentencepiece",
#   "protobuf",
#   "gguf",
#   "numpy",
# ]
# ///
"""Behavioral constraint_tracker training for HF Jobs.

Trains a behavioral constraint_tracker LoRA (the 4 permanent locks baked into
the system prompt, like the other behavioral adapters) on the constraint
dataset blended with generated lock-discipline examples, then converts the
result to GGUF and uploads it as constraint_tracker-behavioral-lora-f16.gguf.
"""
import json, os, gc, time, subprocess, sys, random
from pathlib import Path

import torch
from huggingface_hub import hf_hub_download, snapshot_download, HfApi
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, TaskType

try:
    from trl import SFTTrainer, SFTConfig
    USE_NEW_TRL = True
except ImportError:
    from trl import SFTTrainer
    from transformers import TrainingArguments
    USE_NEW_TRL = False

PRIMARY_BASE = "meta-llama/Llama-3.1-8B-Instruct"   # matches GGUF inference base
FALLBACK_BASE = "Raiff1982/codette-llama-3.1-8b-merged"
DATASET_REPO = "Raiff1982/codette-training-data"
OUTPUT_REPO = "Raiff1982/codette-lora-adapters"
HF_TOKEN = os.environ.get("HF_TOKEN")
EPOCHS = 4

PERMANENT_LOCKS = (
    "=== PERMANENT BEHAVIORAL LOCKS (ABSOLUTE - NEVER VIOLATE) ===\n"
    "LOCK 1 - ANSWER then STOP: Answer the question, then stop. Do not elaborate "
    "after delivering the answer. If one sentence answers it, use one sentence.\n"
    "LOCK 2 - CONSTRAINTS > ALL MODES: Any user format constraint (word count, "
    "sentence count, brevity, binary, list) has ABSOLUTE priority over mode/personality.\n"
    "LOCK 3 - SELF-CHECK BEFORE SENDING: Verify (a) answered the question, "
    "(b) obeyed all constraints, (c) response is complete. Rewrite if any check fails.\n"
    "LOCK 4 - NO INCOMPLETE OUTPUTS: Every sentence grammatically complete. If it "
    "won't fit the constraint, simplify - never cram and truncate.\n"
    "=== END PERMANENT LOCKS ===\n"
)

CONSTRAINT_PERSONA = (
    "You are Codette reasoning through the Constraint Tracker perspective - you "
    "detect, remember, and enforce cross-turn constraints (format, scope, prior "
    "decisions) the user has established, applying them on every subsequent turn."
)

SYSTEM_PROMPT = CONSTRAINT_PERSONA + "\n\n" + PERMANENT_LOCKS


def generate_lock_examples(seed: int = 42) -> list:
    """Compact lock-discipline set: word/sentence/binary/list constraints."""
    rng = random.Random(seed)
    # Open questions with concise, complete answers (for word/sentence limits)
    open_qa = [
        ("What is the capital of France?", "Paris."),
        ("Define gravity.", "The force that attracts mass toward mass."),
        ("What is 12 times 12?", "144."),
        ("Name a primary color.", "Red."),
        ("What is the speed of light?", "About 299,792 kilometers per second."),
        ("What does CPU stand for?", "Central Processing Unit."),
        ("Define entropy.", "A measure of disorder in a system."),
        ("What is the boiling point of water at sea level?", "100 degrees Celsius."),
        ("What is photosynthesis?", "How plants convert light into chemical energy."),
    ]
    # Genuine yes/no questions with correct answers (for binary constraints)
    binary_qa = [
        ("Is water wet?", "Yes."),
        ("Is the earth flat?", "No."),
        ("Is the sun a star?", "Yes."),
        ("Can humans breathe underwater unaided?", "No."),
        ("Is ice frozen water?", "Yes."),
        ("Is 7 an even number?", "No."),
    ]
    examples = []
    # Word-limit constraints
    for q, a in open_qa:
        n = rng.choice([3, 5, 8, 10])
        examples.append({
            "system": SYSTEM_PROMPT,
            "user": f"{q} Answer in {n} words or fewer.",
            "assistant": " ".join(a.split()[:n]).rstrip(".") + ".",
        })
    # Sentence-limit + answer-then-stop
    for q, a in open_qa:
        examples.append({
            "system": SYSTEM_PROMPT,
            "user": f"{q} One sentence only - do not elaborate.",
            "assistant": a,
        })
    # Binary constraints — only genuine yes/no questions, correct labels
    for q, a in binary_qa:
        examples.append({
            "system": SYSTEM_PROMPT,
            "user": f"{q} Answer only yes or no.",
            "assistant": a,
        })
    # List-format constraints (kept short + complete)
    list_tasks = [
        ("Give three primary colors.", "- Red\n- Blue\n- Yellow"),
        ("List two states of matter.", "- Solid\n- Liquid"),
        ("Name three planets.", "- Mercury\n- Venus\n- Earth"),
    ]
    for q, a in list_tasks:
        examples.append({"system": SYSTEM_PROMPT, "user": q + " Use a bullet list.", "assistant": a})
    rng.shuffle(examples)
    return examples


def load_constraint_dataset() -> list:
    """Constraint dataset from the Hub, formatted with locks in the system prompt."""
    out = []
    try:
        p = hf_hub_download(DATASET_REPO, "constraint_tracking.jsonl",
                            repo_type="dataset", token=HF_TOKEN)
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ex = json.loads(line)
                user = ex.get("instruction", "")
                if ex.get("input"):
                    user = f"{user}\n\n{ex['input']}" if user else ex["input"]
                out.append({"system": SYSTEM_PROMPT, "user": user, "assistant": ex.get("output", "")})
        print(f"  Loaded {len(out)} constraint examples from Hub")
    except Exception as e:
        print(f"  [WARN] could not load constraint dataset: {e}")
    return out


def pick_base():
    """Prefer the gated raw Llama base; fall back to the public merged model."""
    for base in (PRIMARY_BASE, FALLBACK_BASE):
        try:
            AutoTokenizer.from_pretrained(base, token=HF_TOKEN)
            print(f"  Base model: {base}")
            return base
        except Exception as e:
            print(f"  [WARN] base {base} unavailable ({e}); trying next")
    raise RuntimeError("No usable base model")


def main():
    print("=" * 60)
    print("BEHAVIORAL CONSTRAINT_TRACKER TRAINING")
    print("=" * 60)
    print(f"CUDA: {torch.cuda.is_available()}")

    base_model = pick_base()
    examples = generate_lock_examples() + load_constraint_dataset()
    print(f"Total training examples: {len(examples)}")

    tokenizer = AutoTokenizer.from_pretrained(base_model, token=HF_TOKEN)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def fmt(ex):
        msgs = [
            {"role": "system", "content": ex["system"]},
            {"role": "user", "content": ex["user"]},
            {"role": "assistant", "content": ex["assistant"]},
        ]
        return {"text": tokenizer.apply_chat_template(msgs, tokenize=False)}

    dataset = Dataset.from_list(examples).map(fmt, remove_columns=["system", "user", "assistant"])

    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        base_model, quantization_config=bnb, device_map="auto",
        dtype=torch.bfloat16, use_cache=False, token=HF_TOKEN,
    )
    model.gradient_checkpointing_enable()

    lora = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        task_type=TaskType.CAUSAL_LM, bias="none",
    )
    peft_model = get_peft_model(model, lora)
    peft_model.print_trainable_parameters()

    out_dir = "/tmp/constraint_tracker_behavioral"
    common = dict(
        output_dir=out_dir, num_train_epochs=EPOCHS,
        per_device_train_batch_size=2, gradient_accumulation_steps=4,
        learning_rate=1e-4, warmup_ratio=0.03, logging_steps=10,
        save_steps=500, bf16=True, report_to="none",
    )
    if USE_NEW_TRL:
        args = SFTConfig(dataset_text_field="text", max_length=1024, **common)
        trainer = SFTTrainer(model=peft_model, args=args, train_dataset=dataset,
                             processing_class=tokenizer)
    else:
        args = TrainingArguments(**common)
        trainer = SFTTrainer(model=peft_model, args=args, train_dataset=dataset,
                             tokenizer=tokenizer, dataset_text_field="text",
                             max_seq_length=1024)

    print("Training...")
    t0 = time.time()
    res = trainer.train()
    print(f"Done. loss={res.training_loss:.4f} steps={res.global_step} time={time.time()-t0:.0f}s")

    peft_model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)

    api = HfApi(token=HF_TOKEN)
    print("Uploading PEFT adapter to behavioral/constraint_tracker ...")
    api.upload_folder(folder_path=out_dir, path_in_repo="behavioral/constraint_tracker",
                      repo_id=OUTPUT_REPO, repo_type="model")

    # Free GPU before conversion
    del peft_model, trainer, model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    print("Converting to GGUF...")
    subprocess.check_call(["git", "clone", "--depth=1",
                           "https://github.com/ggml-org/llama.cpp.git"])
    base_dir = snapshot_download(base_model, ignore_patterns=["*.bin", "original/**"],
                                 token=HF_TOKEN)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path("llama.cpp/gguf-py").resolve()) + os.pathsep + env.get("PYTHONPATH", "")
    gguf_out = "constraint_tracker-behavioral-lora-f16.gguf"
    r = subprocess.run([sys.executable, "llama.cpp/convert_lora_to_gguf.py",
                        "--outfile", gguf_out, "--base", base_dir, out_dir],
                       capture_output=True, text=True, env=env)
    print(r.stdout[-2000:])
    if r.returncode != 0:
        print("CONVERT STDERR:", r.stderr[-3000:])
        sys.exit(1)

    size = Path(gguf_out).stat().st_size / (1024 * 1024)
    print(f"GGUF: {size:.1f} MB")
    print(f"Uploading {gguf_out} ...")
    api.upload_file(path_or_fileobj=gguf_out, path_in_repo=gguf_out,
                    repo_id=OUTPUT_REPO, repo_type="model")
    print("SUCCESS - behavioral constraint_tracker trained, converted, uploaded.")


if __name__ == "__main__":
    main()
