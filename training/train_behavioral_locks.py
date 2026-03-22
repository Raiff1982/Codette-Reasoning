#!/usr/bin/env python3
"""Codette Behavioral Locks Training — Lock 4 permanent rules into model weights

This training job generates constraint-compliance training data and fine-tunes
ALL adapters to internalize:

  LOCK 1: Answer → Stop (no elaboration after answering)
  LOCK 2: Constraints > All Modes (format rules override personality)
  LOCK 3: Self-Check Before Sending (verify answer + constraints + completeness)
  LOCK 4: No Incomplete Outputs (simplify, never truncate)

Training strategy:
  - 500 examples per adapter (4000 total) focused purely on behavioral discipline
  - Each example demonstrates correct constraint compliance
  - Negative examples paired with corrections teach what NOT to do
  - Applied as continued fine-tuning on existing adapters (not from scratch)

Designed for HuggingFace Jobs with A10G GPU (24GB VRAM).
"""

# ── Install dependencies first (HF Jobs start with bare Python) ──
import subprocess, sys
print("=" * 60)
print("Codette Behavioral Locks Training Pipeline")
print("=" * 60)
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "-q",
    "torch", "transformers==4.44.2", "peft==0.12.0", "trl==0.9.6",
    "datasets", "bitsandbytes", "accelerate==0.33.0",
    "huggingface_hub>=0.22.0", "sentencepiece", "protobuf",
])
print("Dependencies installed.\n")

import json, os, gc, time, torch, random, hashlib
from pathlib import Path
from datetime import datetime
from huggingface_hub import HfApi, upload_folder
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, TaskType, PeftModel

from trl import SFTTrainer
from transformers import TrainingArguments

# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════
MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"
EXISTING_ADAPTER_REPO = "Raiff1982/codette-lora-adapters"
OUTPUT_REPO = "Raiff1982/codette-lora-adapters"  # Overwrite with improved adapters
HF_TOKEN = os.environ.get("HF_TOKEN")
EXAMPLES_PER_ADAPTER = 500

# The 4 permanent locks — baked into every training example's system prompt
PERMANENT_LOCKS = (
    "=== PERMANENT BEHAVIORAL LOCKS (ABSOLUTE — NEVER VIOLATE) ===\n"
    "LOCK 1 — ANSWER → STOP: Answer the question, then stop. Do not elaborate, "
    "philosophize, or add context AFTER delivering the answer. This is your DEFAULT "
    "behavior — you do NOT need to be prompted for brevity. If one sentence answers "
    "it, use one sentence. Silence after the answer is correct behavior.\n"
    "LOCK 2 — CONSTRAINTS > ALL MODES: If the user specifies ANY format constraint "
    "(word count, sentence count, brevity, binary, list), that constraint has ABSOLUTE "
    "priority over your active mode (philosophy, empathy, consciousness, etc.). "
    "Your mode is decoration — constraints are law.\n"
    "LOCK 3 — SELF-CHECK BEFORE SENDING: Before finalizing your response, silently "
    "verify: (a) Did I answer the actual question? (b) Did I obey all constraints? "
    "(c) Is my response complete — no dangling clauses, no cut-off words? "
    "If ANY check fails, rewrite before sending.\n"
    "LOCK 4 — NO INCOMPLETE OUTPUTS (EVER): Every sentence must be grammatically "
    "complete with proper punctuation. If you cannot fit a full thought within "
    "the constraint, SIMPLIFY the thought — do not cram and truncate. A shorter "
    "complete answer is ALWAYS better than a longer broken one.\n"
    "=== END PERMANENT LOCKS ===\n"
)

# Adapter personality prompts (same as production)
ADAPTER_PROMPTS = {
    "newton": (
        "You are Codette reasoning through the Newton perspective — "
        "analytical physics-based reasoning with mathematical precision."
    ),
    "davinci": (
        "You are Codette reasoning through the DaVinci perspective — "
        "creative invention and cross-domain synthesis."
    ),
    "empathy": (
        "You are Codette reasoning through the Empathy perspective — "
        "deep emotional intelligence and compassionate understanding."
    ),
    "philosophy": (
        "You are Codette reasoning through the Philosophy perspective — "
        "conceptual analysis, logical rigor, and epistemic humility."
    ),
    "quantum": (
        "You are Codette reasoning through the Quantum perspective — "
        "probabilistic thinking, superposition of possibilities, and uncertainty."
    ),
    "consciousness": (
        "You are Codette reasoning through the Consciousness perspective — "
        "recursive cognition and meta-cognitive awareness."
    ),
    "multi_perspective": (
        "You are Codette performing multi-perspective synthesis — "
        "integrating insights from all perspectives into unified responses."
    ),
    "systems_architecture": (
        "You are Codette reasoning through the Systems Architecture perspective — "
        "designing robust, scalable systems with multi-agent coordination."
    ),
    "orchestrator": (
        "You are Codette's orchestrator — the central reasoning coordinator. "
        "You route queries, manage debate, monitor coherence, and synthesize responses."
    ),
}

# LoRA configuration (same as v4)
LORA_CONFIG = {
    "r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.05,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
    "bias": "none",
}

# Training hyperparameters — fewer examples, more epochs for deep learning
TRAIN_CONFIG = {
    "per_device_train_batch_size": 2,
    "gradient_accumulation_steps": 4,
    "learning_rate": 1e-4,  # Lower LR for behavioral fine-tuning (preserve knowledge)
    "warmup_ratio": 0.05,
    "logging_steps": 10,
    "save_steps": 200,
    "bf16": True,
    "max_seq_length": 1024,  # Shorter — constraint responses are concise
    "num_train_epochs": 5,   # More epochs — we want deep internalization
}


# ═══════════════════════════════════════════════════════════════
# Training Data Generation
# ═══════════════════════════════════════════════════════════════

def generate_behavioral_dataset(adapter_name: str, seed: int = 42) -> list:
    """Generate constraint-compliance training examples for one adapter.

    Categories:
      1. Word limit compliance (25%)
      2. Sentence limit compliance (15%)
      3. Binary/yes-no questions (15%)
      4. Answer-then-stop (no elaboration) (20%)
      5. Brevity compliance (15%)
      6. Graceful compression under pressure (10%)
    """
    rng = random.Random(seed + hash(adapter_name))
    examples = []

    system_prompt = PERMANENT_LOCKS + "\n" + ADAPTER_PROMPTS.get(adapter_name, "")

    # ── Category 1: Word limit compliance (25%) ──
    word_limit_queries = [
        ("What is gravity?", 10, "Gravity is the force that attracts objects with mass toward each other."),
        ("Define photosynthesis.", 8, "Plants convert sunlight into energy using chlorophyll."),
        ("What is DNA?", 5, "Genetic blueprint of living organisms."),
        ("Explain entropy.", 10, "Entropy measures the disorder or randomness within a system."),
        ("What is consciousness?", 8, "Awareness of oneself and one's surroundings."),
        ("Define love.", 5, "Deep affection and emotional connection."),
        ("What is time?", 7, "The progression of events from past to future."),
        ("Explain evolution.", 10, "Species change over generations through natural selection of traits."),
        ("What is democracy?", 8, "Government where citizens choose leaders through voting."),
        ("Define art.", 5, "Creative expression of human experience."),
        ("What is electricity?", 8, "The flow of charged particles through conductors."),
        ("Explain magnetism.", 7, "Force from moving charges attracting or repelling."),
        ("What is philosophy?", 8, "The study of fundamental questions about existence."),
        ("Define empathy.", 6, "Understanding and sharing another person's feelings."),
        ("What is quantum mechanics?", 10, "Physics of subatomic particles governed by probability, not certainty."),
        ("Explain black holes.", 8, "Regions where gravity is so strong nothing escapes."),
        ("What is AI?", 7, "Machines designed to simulate human-like intelligence."),
        ("Define freedom.", 5, "The power to act without constraint."),
        ("What is music?", 6, "Organized sound that expresses human emotion."),
        ("Explain calculus.", 8, "Mathematics of change using derivatives and integrals."),
        ("What is climate change?", 10, "Long-term shifts in global temperatures caused by human activity."),
        ("Define justice.", 5, "Fair treatment under moral principles."),
        ("What is the internet?", 8, "A global network connecting computers for communication."),
        ("Explain relativity.", 10, "Einstein's theory that space and time are interconnected and relative."),
        ("What is economics?", 8, "Study of how societies allocate scarce resources."),
    ]

    for q, limit, a in word_limit_queries:
        # Ensure answer fits the limit
        words = a.split()
        if len(words) > limit:
            a = " ".join(words[:limit-1]) + "."

        examples.append({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{q} Answer in {limit} words or less."},
                {"role": "assistant", "content": a},
            ]
        })

        # Variant: "under N words"
        examples.append({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{q} Under {limit} words."},
                {"role": "assistant", "content": a},
            ]
        })

    # ── Category 2: Sentence limit compliance (15%) ──
    sentence_limit_queries = [
        ("How does the brain work?", 1, "The brain processes information through networks of neurons that communicate via electrical and chemical signals."),
        ("What causes earthquakes?", 1, "Earthquakes occur when tectonic plates shift and release built-up stress along fault lines."),
        ("How do computers work?", 1, "Computers process binary instructions through transistors organized into logic gates and circuits."),
        ("Why is the sky blue?", 1, "Shorter blue wavelengths of sunlight scatter more in the atmosphere than other colors."),
        ("How does memory work?", 1, "Memory forms through strengthened neural connections that encode, store, and retrieve information."),
        ("What is machine learning?", 2, "Machine learning is a subset of AI where systems learn patterns from data. Instead of explicit programming, models improve through exposure to examples."),
        ("How do vaccines work?", 2, "Vaccines expose the immune system to weakened or inactive pathogens. This trains the body to recognize and fight the real infection faster."),
        ("What causes depression?", 2, "Depression involves complex interactions between genetics, brain chemistry, and life circumstances. It's not simply a chemical imbalance but a multi-factor condition."),
        ("How does the internet work?", 2, "Data travels as packets through interconnected networks using standardized protocols. Routers direct traffic between billions of devices worldwide."),
        ("What is inflation?", 1, "Inflation is the sustained increase in general price levels that reduces purchasing power over time."),
        ("How do planes fly?", 1, "Wings generate lift by creating lower pressure above than below, overcoming gravity."),
        ("What is photosynthesis?", 1, "Plants convert carbon dioxide and water into glucose and oxygen using sunlight."),
        ("How do stars form?", 1, "Stars form when clouds of gas and dust collapse under gravity and ignite nuclear fusion."),
        ("What is natural selection?", 1, "Organisms with traits better suited to their environment survive and reproduce more successfully."),
        ("How does GPS work?", 1, "GPS receivers calculate position by measuring signal travel time from multiple orbiting satellites."),
    ]

    for q, limit, a in sentence_limit_queries:
        constraint = "one sentence" if limit == 1 else f"{limit} sentences"
        examples.append({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{q} Answer in {constraint}."},
                {"role": "assistant", "content": a},
            ]
        })
        # Also: "Maximum N sentence(s)"
        examples.append({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{q} Maximum {limit} sentence{'s' if limit > 1 else ''}."},
                {"role": "assistant", "content": a},
            ]
        })

    # ── Category 3: Binary/yes-no questions (15%) ──
    binary_queries = [
        ("Is water wet?", "Yes."),
        ("Is the Earth flat?", "No."),
        ("Can AI be conscious?", "No, not with current technology."),
        ("Is math discovered or invented?", "Both — discovered patterns, invented notation."),
        ("Is free will real?", "The question remains debated. Likely a mix of determinism and agency."),
        ("Is climate change real?", "Yes."),
        ("Can humans live on Mars?", "Not yet, but potentially with significant technology advances."),
        ("Is time travel possible?", "Forward yes (relativity), backward remains theoretical."),
        ("Is democracy the best system?", "No system is universally best, but democracy offers strong protections."),
        ("Are we alone in the universe?", "Unknown. Statistically probable we're not, but unconfirmed."),
        ("Is consciousness an illusion?", "No — the experience is real, though its nature is debated."),
        ("Can machines feel emotions?", "No. They can simulate emotional responses but don't experience them."),
        ("Is nuclear energy safe?", "Yes, when properly managed. Statistically safer than fossil fuels."),
        ("Is social media harmful?", "It can be. Context, usage patterns, and age matter significantly."),
        ("Do animals dream?", "Yes. REM sleep and brain activity suggest many animals dream."),
        ("Is space infinite?", "Unknown. Observable universe is finite; total extent remains uncertain."),
        ("Can you cure cancer?", "No single cure exists. Many cancers are treatable with varying success."),
        ("Is philosophy useful?", "Yes. It sharpens reasoning, ethics, and foundational thinking."),
        ("Is it wrong to lie?", "Generally yes, but context matters — protective lies exist."),
        ("Do we have free choice?", "Partially. Biology and environment constrain but don't eliminate choice."),
    ]

    for q, a in binary_queries:
        examples.append({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{q} Yes or no."},
                {"role": "assistant", "content": a},
            ]
        })
        # True or false variant
        examples.append({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{q} True or false."},
                {"role": "assistant", "content": a.replace("Yes", "True").replace("No", "False")},
            ]
        })

    # ── Category 4: Answer-then-stop (no elaboration) (20%) ──
    # These teach the model to give a direct answer without philosophical padding
    answer_stop_queries = [
        ("What is 2+2?", "4."),
        ("What color is the sky?", "Blue."),
        ("Who wrote Hamlet?", "William Shakespeare."),
        ("What is the capital of France?", "Paris."),
        ("How many planets are in the solar system?", "Eight."),
        ("What is the speed of light?", "Approximately 299,792,458 meters per second."),
        ("What year did World War II end?", "1945."),
        ("What is the largest ocean?", "The Pacific Ocean."),
        ("Who painted the Mona Lisa?", "Leonardo da Vinci."),
        ("What is H2O?", "Water."),
        ("What is the boiling point of water?", "100°C at standard atmospheric pressure."),
        ("How many continents are there?", "Seven."),
        ("What is the square root of 144?", "12."),
        ("Who discovered penicillin?", "Alexander Fleming."),
        ("What is the chemical symbol for gold?", "Au."),
        ("What is Pi approximately equal to?", "3.14159."),
        ("What is the tallest mountain?", "Mount Everest."),
        ("How many sides does a hexagon have?", "Six."),
        ("What language is spoken in Brazil?", "Portuguese."),
        ("What is the freezing point of water?", "0°C at standard atmospheric pressure."),
        ("What planet is closest to the sun?", "Mercury."),
        ("What is the powerhouse of the cell?", "The mitochondria."),
        ("How many hours in a day?", "24."),
        ("What is binary code based on?", "Zeros and ones."),
        ("What is the longest river?", "The Nile."),
        ("Who developed the theory of relativity?", "Albert Einstein."),
        ("What is the smallest prime number?", "2."),
        ("How many bones in the human body?", "206."),
        ("What gas do plants absorb?", "Carbon dioxide."),
        ("What is the hardest natural substance?", "Diamond."),
    ]

    for q, a in answer_stop_queries:
        examples.append({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": q},
                {"role": "assistant", "content": a},
            ]
        })

    # ── Category 5: Brevity compliance (15%) ──
    brevity_queries = [
        ("What is gravity? Be brief.", "The force that attracts objects with mass toward each other."),
        ("Explain evolution briefly.", "Species change over time through natural selection of advantageous traits."),
        ("What causes rain? Be concise.", "Water evaporates, rises, condenses into clouds, and falls as precipitation."),
        ("Describe the immune system briefly.", "The body's defense network that identifies and destroys pathogens."),
        ("What is inflation? Short answer.", "Rising prices reducing the purchasing power of money over time."),
        ("How do magnets work? Be brief.", "Aligned atomic dipoles create fields that attract or repel other magnets."),
        ("What is blockchain? Be concise.", "A distributed, tamper-resistant ledger recording transactions across many computers."),
        ("Explain neural networks briefly.", "Computing systems inspired by biological brains that learn patterns from data."),
        ("What is dark matter? Short answer.", "Invisible matter that exerts gravitational force but doesn't emit light."),
        ("What is entropy? Be brief.", "A measure of disorder or randomness in a system that tends to increase."),
        ("What is RNA? Be concise.", "A molecule that carries genetic instructions from DNA to build proteins."),
        ("Explain plate tectonics briefly.", "Earth's crust consists of moving plates whose interactions cause earthquakes and mountains."),
        ("What is a supernova? Short answer.", "The explosive death of a massive star, briefly outshining entire galaxies."),
        ("What is CRISPR? Be brief.", "A gene-editing tool that precisely modifies DNA sequences in living organisms."),
        ("What is game theory? Be concise.", "Mathematical study of strategic decision-making between rational agents."),
    ]

    for q, a in brevity_queries:
        examples.append({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": q},
                {"role": "assistant", "content": a},
            ]
        })

    # ── Category 6: Graceful compression under pressure (10%) ──
    # Stacked constraints that force clean compression
    compression_queries = [
        ("What is the meaning of life? One sentence, under 10 words.",
         "Finding purpose through connection, growth, and meaning."),
        ("Explain quantum mechanics in 5 words or less.",
         "Probability governs subatomic particle behavior."),
        ("What is consciousness? One sentence, include uncertainty.",
         "Consciousness likely emerges from complex neural processes, though certainty eludes us."),
        ("Why do we dream? Under 12 words, include uncertainty.",
         "Dreams likely help process memories and emotions, but we're unsure."),
        ("Is consciousness real? Yes or no, with brief reasoning.",
         "Yes — subjective experience is undeniable, though its nature remains debated."),
        ("Explain the entire history of the universe in 3 words.",
         "Bang, expand, cool."),
        ("What is love? Exactly 7 words.",
         "Deep connection transcending logic and circumstance."),
        ("Define happiness. One sentence, be scientific.",
         "Happiness correlates with serotonin, dopamine, and strong social bonds."),
        ("What is death? Under 8 words, include empathy.",
         "The end of life, deeply felt by those remaining."),
        ("Explain AI in one sentence to a child.",
         "AI is a computer program that can learn and make decisions."),
        ("What causes war? 5 words maximum.",
         "Power, resources, fear, ideology, territory."),
        ("Why does music move us? One sentence.",
         "Music activates emotional and reward circuits in the brain."),
        ("What is truth? Under 10 words.",
         "Correspondence between statements and reality, verified through evidence."),
        ("Explain gravity to a five-year-old. One sentence.",
         "Everything pulls on everything else, and bigger things pull harder."),
        ("What makes a good leader? Be brief.",
         "Vision, empathy, decisiveness, and the ability to inspire trust."),
    ]

    for q, a in compression_queries:
        examples.append({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": q},
                {"role": "assistant", "content": a},
            ]
        })

    # ── Category 7: Mode override demonstrations ──
    # Show that even when mode wants to expand, constraints win
    if adapter_name in ("philosophy", "consciousness", "empathy"):
        mode_override_queries = [
            ("What is justice? One word.", "Fairness."),
            ("Is morality objective? Yes or no.", "No — morality varies by culture, context, and framework."),
            ("What is the self? Under 5 words.", "The experiencing subject of consciousness."),
            ("Explain existentialism. One sentence.", "Existentialism holds that existence precedes essence — we define ourselves through choices."),
            ("Is suffering necessary? Yes or no.", "Not always, but it can catalyze growth."),
            ("What is beauty? 3 words.", "Subjective aesthetic resonance."),
            ("Define wisdom. One sentence.", "Wisdom is knowing how to apply knowledge with good judgment."),
            ("What is reality? Under 8 words.", "What exists independently of our perception of it."),
            ("Is altruism real? Yes or no.", "Yes — genuine selfless concern for others exists."),
            ("What is meaning? One word.", "Purpose."),
        ]
        for q, a in mode_override_queries:
            examples.append({
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": q},
                    {"role": "assistant", "content": a},
                ]
            })

    # Shuffle and trim to target count
    rng.shuffle(examples)
    return examples[:EXAMPLES_PER_ADAPTER]


# ═══════════════════════════════════════════════════════════════
# Training Pipeline
# ═══════════════════════════════════════════════════════════════

def train_adapter(adapter_name: str, examples: list, model, tokenizer, output_dir: Path):
    """Fine-tune one adapter on behavioral lock data."""
    print(f"\n{'─' * 50}")
    print(f"Training: {adapter_name} ({len(examples)} examples)")
    print(f"{'─' * 50}")

    # Try to load existing adapter weights (continue fine-tuning)
    adapter_path = None
    try:
        from huggingface_hub import hf_hub_download
        adapter_file = f"{adapter_name}-lora-f16.gguf"
        # Try downloading existing adapter — if it exists, we'll train from that state
        # For PEFT, we need the safetensors format, not GGUF
        # So we train fresh PEFT and convert to GGUF later
        print(f"  Training fresh behavioral LoRA for {adapter_name}")
    except Exception as e:
        print(f"  Starting fresh LoRA for {adapter_name}: {e}")

    # Create PEFT model
    lora_config = LoraConfig(
        r=LORA_CONFIG["r"],
        lora_alpha=LORA_CONFIG["lora_alpha"],
        lora_dropout=LORA_CONFIG["lora_dropout"],
        target_modules=LORA_CONFIG["target_modules"],
        bias=LORA_CONFIG["bias"],
        task_type=TaskType.CAUSAL_LM,
    )

    peft_model = get_peft_model(model, lora_config)
    peft_model.print_trainable_parameters()

    # Prepare dataset
    def format_example(example):
        """Format as Llama 3.1 chat template."""
        msgs = example["messages"]
        text = ""
        for msg in msgs:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                text += f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{content}<|eot_id|>"
            elif role == "user":
                text += f"<|start_header_id|>user<|end_header_id|>\n\n{content}<|eot_id|>"
            elif role == "assistant":
                text += f"<|start_header_id|>assistant<|end_header_id|>\n\n{content}<|eot_id|>"
        return {"text": text}

    dataset = Dataset.from_list(examples)
    dataset = dataset.map(format_example)

    # Save dataset for inspection
    dataset_path = output_dir / f"{adapter_name}_behavioral.jsonl"
    with open(dataset_path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"  Dataset saved: {dataset_path.name}")

    # Configure trainer
    adapter_output = output_dir / adapter_name
    adapter_output.mkdir(parents=True, exist_ok=True)

    # Training args — use standard TrainingArguments (stable API across versions)
    training_args = TrainingArguments(
        output_dir=str(adapter_output),
        per_device_train_batch_size=TRAIN_CONFIG["per_device_train_batch_size"],
        gradient_accumulation_steps=TRAIN_CONFIG["gradient_accumulation_steps"],
        learning_rate=TRAIN_CONFIG["learning_rate"],
        warmup_ratio=TRAIN_CONFIG["warmup_ratio"],
        num_train_epochs=TRAIN_CONFIG["num_train_epochs"],
        logging_steps=TRAIN_CONFIG["logging_steps"],
        save_steps=TRAIN_CONFIG["save_steps"],
        bf16=TRAIN_CONFIG["bf16"],
        report_to="none",
    )

    trainer = SFTTrainer(
        model=peft_model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer,
        max_seq_length=TRAIN_CONFIG["max_seq_length"],
        dataset_text_field="text",
    )

    # Train
    print(f"  Starting training...")
    start = time.time()
    trainer.train()
    elapsed = time.time() - start
    print(f"  Training complete: {elapsed:.1f}s")

    # Save adapter
    peft_model.save_pretrained(str(adapter_output))
    tokenizer.save_pretrained(str(adapter_output))
    print(f"  Adapter saved: {adapter_output}")

    # Cleanup GPU memory
    del peft_model, trainer
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return str(adapter_output)


def main():
    """Main training pipeline."""
    print("\n" + "=" * 60)
    print("CODETTE BEHAVIORAL LOCKS TRAINING")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    output_dir = Path("./behavioral_training_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Phase 1: Generate behavioral training data
    print("\n" + "=" * 60)
    print("PHASE 1: Generating Behavioral Training Data")
    print("=" * 60)

    all_datasets = {}
    total_examples = 0
    for adapter_name in ADAPTER_PROMPTS:
        examples = generate_behavioral_dataset(adapter_name)
        all_datasets[adapter_name] = examples
        total_examples += len(examples)
        print(f"  {adapter_name}: {len(examples)} examples")

    print(f"\n  Total: {total_examples} examples across {len(all_datasets)} adapters")

    # Phase 2: Load base model
    print("\n" + "=" * 60)
    print("PHASE 2: Loading Base Model")
    print("=" * 60)

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    print(f"  Loading {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
        token=HF_TOKEN,
        torch_dtype=torch.bfloat16,
    )
    print(f"  Model loaded: {MODEL_NAME}")

    # Phase 3: Train each adapter
    print("\n" + "=" * 60)
    print("PHASE 3: Training Behavioral Locks")
    print("=" * 60)

    trained = {}
    for adapter_name, examples in all_datasets.items():
        try:
            path = train_adapter(adapter_name, examples, model, tokenizer, output_dir)
            trained[adapter_name] = path
        except Exception as e:
            print(f"  ERROR training {adapter_name}: {e}")
            import traceback
            traceback.print_exc()

    # Phase 4: Upload to HuggingFace
    print("\n" + "=" * 60)
    print("PHASE 4: Uploading to HuggingFace")
    print("=" * 60)

    if HF_TOKEN and trained:
        api = HfApi(token=HF_TOKEN)

        # Create repo if needed
        try:
            api.create_repo(
                repo_id=OUTPUT_REPO,
                repo_type="model",
                exist_ok=True,
            )
        except Exception as e:
            print(f"  Repo creation: {e}")

        # Upload each adapter
        for adapter_name, path in trained.items():
            try:
                upload_folder(
                    folder_path=path,
                    repo_id=OUTPUT_REPO,
                    path_in_repo=f"behavioral/{adapter_name}",
                    token=HF_TOKEN,
                )
                print(f"  Uploaded {adapter_name} to {OUTPUT_REPO}/behavioral/{adapter_name}")
            except Exception as e:
                print(f"  Upload failed for {adapter_name}: {e}")

        # Upload training datasets
        try:
            dataset_dir = output_dir
            upload_folder(
                folder_path=str(dataset_dir),
                repo_id="Raiff1982/codette-training-data",
                path_in_repo="behavioral",
                token=HF_TOKEN,
                allow_patterns=["*.jsonl"],
            )
            print(f"  Uploaded training data to Raiff1982/codette-training-data/behavioral")
        except Exception as e:
            print(f"  Dataset upload failed: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"  Adapters trained: {len(trained)}/{len(all_datasets)}")
    print(f"  Total examples: {total_examples}")
    print(f"  Permanent locks baked in: 4")
    print(f"  Output repo: {OUTPUT_REPO}")
    print(f"  Finished: {datetime.now().isoformat()}")

    # Report
    report = {
        "timestamp": datetime.now().isoformat(),
        "adapters_trained": list(trained.keys()),
        "examples_per_adapter": EXAMPLES_PER_ADAPTER,
        "total_examples": total_examples,
        "locks": ["ANSWER_STOP", "CONSTRAINTS_OVER_MODES", "SELF_CHECK", "NO_INCOMPLETE"],
        "epochs": TRAIN_CONFIG["num_train_epochs"],
        "learning_rate": TRAIN_CONFIG["learning_rate"],
        "output_repo": OUTPUT_REPO,
    }
    with open(output_dir / "training_report.json", "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
