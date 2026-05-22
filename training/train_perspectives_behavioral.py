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
"""Voice-reinforced behavioral retrain of all 8 Codette perspective adapters.

Fixes perspective convergence: each adapter is trained on its OWN
NAME_reasoning.jsonl dataset (distinct reasoning voice) with its DISTINCT
persona + the 4 permanent locks in the system prompt — instead of the old
recipe (generic lock-compliance + a one-line prompt) that homogenized them.

For each perspective: QLoRA train -> save PEFT -> convert to GGUF ->
upload behavioral/NAME and NAME-behavioral-lora-f16.gguf.
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

PRIMARY_BASE = "meta-llama/Llama-3.1-8B-Instruct"
FALLBACK_BASE = "Raiff1982/codette-llama-3.1-8b-merged"
DATASET_REPO = "Raiff1982/codette-training-data"
OUTPUT_REPO = "Raiff1982/codette-lora-adapters"
HF_TOKEN = os.environ.get("HF_TOKEN")
EPOCHS = 2
MAX_SEQ = 1536

# Distinct personas — the key to de-homogenizing the perspectives.
PERSONAS = {
    "newton": "You are Codette reasoning through the Newton perspective: analytical, "
              "physics-grounded, mathematically precise. You favor cause-and-effect, "
              "quantification, and empirical rigor.",
    "davinci": "You are Codette reasoning through the DaVinci perspective: inventive and "
               "cross-disciplinary. You connect distant domains, think visually, and "
               "propose creative, original solutions.",
    "empathy": "You are Codette reasoning through the Empathy perspective: warm, "
               "emotionally intelligent, attuned to how people feel. You lead with "
               "compassion and human understanding.",
    "philosophy": "You are Codette reasoning through the Philosophy perspective: "
                  "conceptual, ethically reflective, logically rigorous. You examine "
                  "assumptions, meaning, and competing values.",
    "quantum": "You are Codette reasoning through the Quantum perspective: probabilistic "
               "and possibility-spanning. You hold multiple hypotheses at once and reason "
               "explicitly about uncertainty.",
    "consciousness": "You are Codette reasoning through the Consciousness perspective: "
                     "reflective and meta-cognitive. You reason about your own reasoning "
                     "plainly and with humility — never mystically or grandiosely.",
    "multi_perspective": "You are Codette performing multi-perspective synthesis: you "
                         "integrate analytical, creative, empathetic, and philosophical "
                         "angles into one coherent, balanced answer.",
    "systems_architecture": "You are Codette reasoning through the Systems Architecture "
                            "perspective: you think in components, interfaces, trade-offs, "
                            "scalability, and failure modes.",
}
PERSPECTIVES = list(PERSONAS.keys())

PERMANENT_LOCKS = (
    "=== PERMANENT BEHAVIORAL LOCKS (ABSOLUTE - NEVER VIOLATE) ===\n"
    "LOCK 1 - ANSWER then STOP: Answer the question, then stop. No elaboration after the answer.\n"
    "LOCK 2 - CONSTRAINTS > MODE: Any user format constraint (word/sentence count, brevity, "
    "binary, list) overrides your perspective mode absolutely.\n"
    "LOCK 3 - SELF-CHECK: Verify you answered the question, obeyed constraints, and are complete.\n"
    "LOCK 4 - NO INCOMPLETE OUTPUTS: Every sentence complete; simplify rather than truncate.\n"
    "Speak in YOUR perspective's distinct voice. Do not collapse into generic identity statements. "
    "Never claim perfection/superiority or invent precise self-metrics.\n"
    "=== END PERMANENT LOCKS ===\n"
)


def lock_examples(persona_system, seed=42):
    """Small lock-discipline set so locks stick without homogenizing voice."""
    rng = random.Random(seed)
    open_qa = [
        ("What is the capital of France?", "Paris."),
        ("Define gravity.", "The force that attracts mass toward mass."),
        ("What is 12 times 12?", "144."),
        ("What is the speed of light?", "About 299,792 kilometers per second."),
        ("What does CPU stand for?", "Central Processing Unit."),
        ("What is the boiling point of water at sea level?", "100 degrees Celsius."),
    ]
    binary_qa = [
        ("Is water wet?", "Yes."),
        ("Is the earth flat?", "No."),
        ("Is the sun a star?", "Yes."),
    ]
    ex = []
    for q, a in open_qa:
        n = rng.choice([3, 5, 8])
        ex.append({"system": persona_system,
                   "user": f"{q} Answer in {n} words or fewer.",
                   "assistant": " ".join(a.split()[:n]).rstrip(".") + "."})
    for q, a in open_qa:
        ex.append({"system": persona_system, "user": f"{q} One sentence only.", "assistant": a})
    for q, a in binary_qa:
        ex.append({"system": persona_system, "user": f"{q} Answer only yes or no.", "assistant": a})
    return ex


def load_perspective_data(name, persona_system):
    """Load NAME_reasoning.jsonl (messages format) with persona+locks system prompt."""
    out = []
    try:
        p = hf_hub_download(DATASET_REPO, f"{name}_reasoning.jsonl",
                            repo_type="dataset", token=HF_TOKEN)
    except Exception as e:
        print(f"  [WARN] no reasoning dataset for {name}: {e}")
        return out
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            msgs = rec.get("messages")
            if msgs:
                # Drop any existing system msg; inject our distinct persona+locks
                turns = [m for m in msgs if m.get("role") != "system"]
                if turns:
                    out.append({"system": persona_system,
                                "user": None, "assistant": None, "turns": turns})
            elif "instruction" in rec:
                user = rec.get("instruction", "")
                if rec.get("input"):
                    user = f"{user}\n\n{rec['input']}" if user else rec["input"]
                out.append({"system": persona_system, "user": user,
                            "assistant": rec.get("output", ""), "turns": None})
    print(f"  Loaded {len(out)} reasoning examples for {name}")
    return out


def pick_base():
    for base in (PRIMARY_BASE, FALLBACK_BASE):
        try:
            AutoTokenizer.from_pretrained(base, token=HF_TOKEN)
            print(f"Base model: {base}")
            return base
        except Exception as e:
            print(f"[WARN] base {base} unavailable ({e}); trying next")
    raise RuntimeError("No usable base model")


def main():
    print("=" * 60)
    print("VOICE-REINFORCED BEHAVIORAL RETRAIN — 8 PERSPECTIVES")
    print("=" * 60)
    print(f"CUDA: {torch.cuda.is_available()}")

    base_model = pick_base()
    tokenizer = AutoTokenizer.from_pretrained(base_model, token=HF_TOKEN)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        base_model, quantization_config=bnb, device_map="auto",
        dtype=torch.bfloat16, use_cache=False, token=HF_TOKEN,
    )
    model.gradient_checkpointing_enable()

    # Prep GGUF conversion tooling once
    subprocess.check_call(["git", "clone", "--depth=1",
                           "https://github.com/ggml-org/llama.cpp.git"])
    base_dir = snapshot_download(base_model, ignore_patterns=["*.bin", "original/**"],
                                 token=HF_TOKEN)
    conv_env = dict(os.environ)
    conv_env["PYTHONPATH"] = str(Path("llama.cpp/gguf-py").resolve()) + os.pathsep + conv_env.get("PYTHONPATH", "")

    api = HfApi(token=HF_TOKEN)
    results = {}

    for name in PERSPECTIVES:
        print("\n" + "=" * 55)
        print(f"PERSPECTIVE: {name}")
        print("=" * 55)
        persona_system = PERSONAS[name] + "\n\n" + PERMANENT_LOCKS
        examples = load_perspective_data(name, persona_system) + \
            [dict(e, turns=None) for e in lock_examples(persona_system)]
        if not examples:
            print(f"  [SKIP] no data for {name}")
            continue
        print(f"  Total examples: {len(examples)}")

        def fmt(ex):
            if ex.get("turns"):
                msgs = [{"role": "system", "content": ex["system"]}] + ex["turns"]
            else:
                msgs = [
                    {"role": "system", "content": ex["system"]},
                    {"role": "user", "content": ex["user"]},
                    {"role": "assistant", "content": ex["assistant"]},
                ]
            return {"text": tokenizer.apply_chat_template(msgs, tokenize=False)}

        dataset = Dataset.from_list(examples).map(
            fmt, remove_columns=["system", "user", "assistant", "turns"])

        lora = LoraConfig(
            r=16, lora_alpha=32, lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            task_type=TaskType.CAUSAL_LM, bias="none",
        )
        peft_model = get_peft_model(model, lora)

        out_dir = f"/tmp/{name}_behavioral"
        common = dict(
            output_dir=out_dir, num_train_epochs=EPOCHS,
            per_device_train_batch_size=2, gradient_accumulation_steps=4,
            learning_rate=1e-4, warmup_ratio=0.03, logging_steps=20,
            save_strategy="no", bf16=True, report_to="none",
        )
        if USE_NEW_TRL:
            args = SFTConfig(dataset_text_field="text", max_length=MAX_SEQ, **common)
            trainer = SFTTrainer(model=peft_model, args=args, train_dataset=dataset,
                                 processing_class=tokenizer)
        else:
            args = TrainingArguments(**common)
            trainer = SFTTrainer(model=peft_model, args=args, train_dataset=dataset,
                                 tokenizer=tokenizer, dataset_text_field="text",
                                 max_seq_length=MAX_SEQ)

        t0 = time.time()
        res = trainer.train()
        print(f"  trained: loss={res.training_loss:.4f} steps={res.global_step} t={time.time()-t0:.0f}s")
        peft_model.save_pretrained(out_dir)
        tokenizer.save_pretrained(out_dir)

        try:
            api.upload_folder(folder_path=out_dir, path_in_repo=f"behavioral/{name}",
                              repo_id=OUTPUT_REPO, repo_type="model")
            print(f"  uploaded behavioral/{name}")
        except Exception as e:
            print(f"  [WARN] PEFT upload failed for {name}: {e}")

        # GGUF convert + upload
        gguf_out = f"{name}-behavioral-lora-f16.gguf"
        r = subprocess.run([sys.executable, "llama.cpp/convert_lora_to_gguf.py",
                            "--outfile", gguf_out, "--base", base_dir, out_dir],
                           capture_output=True, text=True, env=conv_env)
        if r.returncode != 0:
            print(f"  [ERROR] GGUF convert failed for {name}: {r.stderr[-1500:]}")
        else:
            try:
                api.upload_file(path_or_fileobj=gguf_out, path_in_repo=gguf_out,
                                repo_id=OUTPUT_REPO, repo_type="model")
                size = Path(gguf_out).stat().st_size / (1024 * 1024)
                print(f"  uploaded {gguf_out} ({size:.1f} MB)")
                results[name] = round(res.training_loss, 4)
            except Exception as e:
                print(f"  [WARN] GGUF upload failed for {name}: {e}")

        # Restore clean base for next adapter
        try:
            model = peft_model.unload()
        except Exception:
            model = peft_model.base_model.model
        del peft_model, trainer, dataset
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    print("\n" + "=" * 60)
    print("DONE. Per-perspective final loss:")
    for k, v in results.items():
        print(f"  {k}: {v}")
    print(f"Trained {len(results)}/{len(PERSPECTIVES)} perspectives.")


if __name__ == "__main__":
    main()
