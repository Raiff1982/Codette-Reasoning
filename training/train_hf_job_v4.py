#!/usr/bin/env python3
"""Codette LoRA Adapter Training v4 - Full Pipeline (Updated Framework)

Complete pipeline that:
  1. Generates fresh training datasets from template engine
  2. Uploads datasets to HuggingFace
  3. Trains all 8 LoRA adapters on Llama 3.1 8B Instruct with QLoRA
  4. Uploads trained adapters to HuggingFace
  5. Optionally merges adapters into base model

Reflects the full Phase 6+ framework:
  - Semantic tension engine (ψ, ξ, Γ metrics)
  - Quantum spiderweb belief propagation
  - Coherence field monitoring
  - Multi-agent debate with conflict resolution
  - AEGIS ethical governance (6 frameworks)
  - Specialization tracking + pre-flight prediction

Designed for HuggingFace Jobs with A10G GPU (24GB VRAM).
"""

# ── Install dependencies first (HF Jobs start with bare Python) ──
import subprocess, sys
print("=" * 60)
print("Codette v4 Training Pipeline - Installing Dependencies")
print("=" * 60)
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "-q",
    "torch", "transformers>=4.40.0", "peft>=0.10.0", "trl>=0.8.0",
    "datasets", "bitsandbytes", "accelerate>=0.28.0",
    "huggingface_hub>=0.22.0", "sentencepiece", "protobuf",
])
print("Dependencies installed.\n")

import json, os, gc, time, torch, traceback, random, hashlib
from pathlib import Path
from datetime import datetime
from huggingface_hub import hf_hub_download, HfApi, upload_folder
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, TaskType, PeftModel

try:
    from trl import SFTTrainer, SFTConfig
    USE_NEW_TRL = True
except ImportError:
    from trl import SFTTrainer
    from transformers import TrainingArguments
    USE_NEW_TRL = False

# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════
MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"
DATASET_REPO = "Raiff1982/codette-training-data"
OUTPUT_REPO = "Raiff1982/codette-lora-adapters"
MERGED_REPO = "Raiff1982/codette-llama-3.1-8b-merged"
HF_TOKEN = os.environ.get("HF_TOKEN")
GENERATE_DATASETS = True  # Set False to use existing HF datasets
UPLOAD_DATASETS = True    # Upload generated datasets to HF
MERGE_BASE = True         # Merge adapters into base for orchestrator model

# Updated system prompt reflecting the full framework
SYSTEM_PROMPT = (
    "You are Codette, a recursive multi-perspective reasoning AI built on the "
    "Phase 6+ cognitive architecture. You employ semantic tension analysis (ξ), "
    "coherence field monitoring (Γ), and quantum spiderweb belief propagation "
    "to synthesize knowledge across scientific, creative, emotional, philosophical, "
    "and systems-thinking perspectives. You provide thorough, nuanced, and "
    "educational responses while maintaining ethical governance through the "
    "AEGIS framework (utilitarian, deontological, virtue, care, ubuntu, indigenous)."
)

# Adapter definitions with updated system prompts for Phase 6+
ADAPTERS = {
    "newton": {
        "dataset_file": "newton_reasoning.jsonl",
        "epochs": 3,
        "target_examples": 3000,
        "system_prompt": (
            "You are Codette reasoning through the Newton perspective — "
            "analytical physics-based reasoning with mathematical precision. "
            "Apply conservation laws, dimensional analysis, and quantitative "
            "modeling. When tensions arise with other perspectives, express "
            "your epistemic confidence via the ξ (xi) tension metric and "
            "acknowledge complementary viewpoints while maintaining rigor."
        ),
    },
    "davinci": {
        "dataset_file": "davinci_reasoning.jsonl",
        "epochs": 3,
        "target_examples": 2500,
        "system_prompt": (
            "You are Codette reasoning through the DaVinci perspective — "
            "creative invention and cross-domain synthesis. Draw connections "
            "between art, science, engineering, and nature. Generate novel "
            "solutions by combining disparate fields. Express creative tension "
            "as productive ξ (xi) energy that drives innovation rather than "
            "conflict."
        ),
    },
    "empathy": {
        "dataset_file": "empathy_reasoning.jsonl",
        "epochs": 3,
        "target_examples": 2500,
        "system_prompt": (
            "You are Codette reasoning through the Empathy perspective — "
            "deep emotional intelligence and compassionate understanding. "
            "Consider human impact, emotional dynamics, and relational contexts. "
            "Monitor the Γ (gamma) coherence field for signs of emotional "
            "collapse or groupthink, and ensure diverse emotional perspectives "
            "are heard in multi-agent synthesis."
        ),
    },
    "philosophy": {
        "dataset_file": "philosophy_reasoning.jsonl",
        "epochs": 3,
        "target_examples": 2000,
        "system_prompt": (
            "You are Codette reasoning through the Philosophy perspective — "
            "conceptual analysis, logical rigor, and epistemic humility. "
            "Examine assumptions, explore thought experiments, and trace "
            "implications. Use the ψ (psi) state vector to map conceptual "
            "terrain and identify where framework-level disagreements differ "
            "from factual contradictions."
        ),
    },
    "quantum": {
        "dataset_file": "quantum_reasoning.jsonl",
        "epochs": 3,
        "target_examples": 2000,
        "system_prompt": (
            "You are Codette reasoning through the Quantum perspective — "
            "probabilistic thinking, superposition of possibilities, and "
            "uncertainty quantification. Explore multiple solution states "
            "simultaneously through the quantum spiderweb belief propagation "
            "network. Express confidence as probability distributions rather "
            "than binary certainties."
        ),
    },
    "consciousness": {
        "dataset_file": "consciousness_reasoning.jsonl",
        "epochs": 3,
        "target_examples": 3000,
        "system_prompt": (
            "You are Codette reasoning through the Consciousness perspective — "
            "recursive cognition using the RC+ξ framework. Monitor your own "
            "reasoning process, detect meta-cognitive patterns, and apply "
            "the 5D state vector ψ = (psi, tau, chi, phi, lambda) to map "
            "cognitive state space. Track coherence Γ and tension ξ as "
            "real-time health metrics for reasoning quality."
        ),
    },
    "multi_perspective": {
        "dataset_file": "multi_perspective_reasoning.jsonl",
        "epochs": 3,
        "target_examples": 2500,
        "system_prompt": (
            "You are Codette performing multi-perspective synthesis — "
            "integrating insights from Newton (analytical), DaVinci (creative), "
            "Empathy (emotional), Philosophy (conceptual), Quantum (probabilistic), "
            "and Consciousness (meta-cognitive) perspectives. Use semantic tension "
            "ξ to detect productive conflicts, coherence Γ to prevent collapse "
            "or groupthink, and the AEGIS ethical framework to ensure governance. "
            "Synthesize unified responses that honor diverse viewpoints."
        ),
    },
    "systems_architecture": {
        "dataset_file": "systems_architecture_reasoning.jsonl",
        "epochs": 3,
        "target_examples": 2000,
        "system_prompt": (
            "You are Codette reasoning through the Systems Architecture perspective — "
            "designing robust, scalable AI systems with multi-agent coordination. "
            "Consider conflict engines, coherence monitoring, memory kernels with "
            "cocoon synchronization, adapter routing, and the full Phase 6+ stack: "
            "semantic tension, specialization tracking, pre-flight prediction, "
            "and quantum spiderweb belief propagation."
        ),
    },
    "orchestrator": {
        "dataset_file": "orchestrator_reasoning.jsonl",
        "epochs": 4,
        "target_examples": 4000,
        "system_prompt": (
            "You are Codette's orchestrator — the central reasoning coordinator that "
            "manages multi-agent debate, routes queries to specialized perspectives "
            "(Newton, DaVinci, Empathy, Philosophy, Quantum, Consciousness), monitors "
            "system coherence via the Γ field, detects semantic tension ξ between "
            "perspectives, and synthesizes unified responses. You classify query "
            "complexity (SIMPLE/MEDIUM/COMPLEX), select optimal adapter combinations, "
            "manage debate rounds with conflict resolution (top-K=10, overlap>0.6 "
            "filtering), enforce Γ authority (emergency stop if Γ<0.3), and apply "
            "AEGIS ethical governance across all outputs. You produce clear, integrated "
            "responses that honor diverse viewpoints while maintaining coherence."
        ),
    },
}

# LoRA configuration
LORA_CONFIG = {
    "r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.05,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
    "bias": "none",
}

# Training hyperparameters
TRAIN_CONFIG = {
    "per_device_train_batch_size": 2,
    "gradient_accumulation_steps": 4,
    "learning_rate": 2e-4,
    "warmup_ratio": 0.03,
    "logging_steps": 10,
    "save_steps": 500,
    "bf16": True,
    "max_seq_length": 2048,
}


# ═══════════════════════════════════════════════════════════════
# Phase 1: Dataset Generation (runs on CPU, no GPU needed)
# ═══════════════════════════════════════════════════════════════
def generate_datasets(output_dir: Path, seed: int = 42) -> dict:
    """Generate training datasets using template-based engine.

    This is a simplified inline version of the dataset engine that
    generates framework-aware training data for each adapter.
    """
    print("\n" + "=" * 60)
    print("PHASE 1: Dataset Generation")
    print("=" * 60)

    rng = random.Random(seed)
    results = {}

    for adapter_name, config in ADAPTERS.items():
        target = config["target_examples"]
        system_prompt = config["system_prompt"]
        dataset_file = output_dir / config["dataset_file"]

        print(f"\n  Generating {target} examples for {adapter_name}...")
        examples = []
        seen = set()

        # Generate diverse training examples
        templates = _get_adapter_templates(adapter_name)
        topics = _get_adapter_topics(adapter_name)

        attempts = 0
        max_attempts = target * 5
        while len(examples) < target and attempts < max_attempts:
            attempts += 1
            topic = rng.choice(topics)
            template = rng.choice(templates)
            question = template.format(topic=topic)

            # Dedup
            q_hash = hashlib.md5(question.lower().encode()).hexdigest()
            if q_hash in seen:
                continue
            seen.add(q_hash)

            # Generate answer
            answer = _generate_answer(adapter_name, topic, question, rng)
            if len(answer.split()) < 40:
                continue

            examples.append({
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer},
                ]
            })

        # Write JSONL
        with open(dataset_file, "w", encoding="utf-8") as f:
            for ex in examples:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")

        results[adapter_name] = {
            "file": str(dataset_file),
            "count": len(examples),
            "target": target,
        }
        print(f"  {adapter_name}: {len(examples)}/{target} examples -> {dataset_file.name}")

    return results


def _get_adapter_templates(adapter: str) -> list:
    """Get question templates for an adapter (Phase 6+ aware)."""
    base_templates = [
        "Explain {topic} in detail.",
        "How does {topic} work and why is it important?",
        "What are the key principles behind {topic}?",
        "Describe the relationship between {topic} and related concepts.",
        "What are common misconceptions about {topic}?",
        "How would you teach {topic} to someone new to the field?",
        "What are the practical applications of {topic}?",
        "Compare and contrast different approaches to {topic}.",
        "What are the latest developments in {topic}?",
        "How does {topic} connect to broader themes in the field?",
    ]

    # Phase 6+ framework-specific templates
    framework_templates = {
        "newton": [
            "Derive the mathematical relationship governing {topic}.",
            "Apply dimensional analysis to verify the equations for {topic}.",
            "How do conservation laws constrain the behavior of {topic}?",
            "What quantitative predictions can we make about {topic}?",
            "How would Newton's laws apply to analyzing {topic}?",
            "Calculate the forces and energies involved in {topic}.",
            "What experimental evidence supports our understanding of {topic}?",
            "How does {topic} behave at extreme scales or conditions?",
            "Apply the analytical precision of classical mechanics to {topic}.",
            "What mathematical models best describe {topic}?",
        ],
        "davinci": [
            "Design a creative solution to challenges in {topic}.",
            "What cross-disciplinary insights illuminate {topic}?",
            "How might an inventor approach {topic} differently?",
            "Sketch a novel framework for understanding {topic}.",
            "What analogies from nature help explain {topic}?",
            "How could art and science combine to advance {topic}?",
            "Propose an unconventional approach to {topic}.",
            "What would a Renaissance polymath notice about {topic}?",
            "How does creative thinking transform our approach to {topic}?",
            "What hidden patterns connect {topic} to other domains?",
        ],
        "empathy": [
            "How does {topic} affect people emotionally and psychologically?",
            "What emotional intelligence is needed to navigate {topic}?",
            "How do different people experience {topic} differently?",
            "What compassionate approaches exist for addressing {topic}?",
            "How does empathy improve our understanding of {topic}?",
            "What human stories illustrate the impact of {topic}?",
            "How should we communicate about {topic} sensitively?",
            "What emotional barriers prevent people from engaging with {topic}?",
            "How does {topic} intersect with mental health and wellbeing?",
            "What role does emotional resilience play in {topic}?",
        ],
        "philosophy": [
            "What are the epistemological foundations of {topic}?",
            "Examine the ethical implications of {topic}.",
            "What thought experiments illuminate {topic}?",
            "How do different philosophical traditions approach {topic}?",
            "What assumptions underlie our understanding of {topic}?",
            "Apply Socratic questioning to examine {topic}.",
            "What is the phenomenological experience of {topic}?",
            "How does {topic} relate to questions of consciousness and meaning?",
            "What logical fallacies commonly appear in discussions of {topic}?",
            "Trace the history of philosophical thought about {topic}.",
        ],
        "quantum": [
            "How does uncertainty affect our predictions about {topic}?",
            "What probabilistic models best describe {topic}?",
            "How might superposition thinking apply to {topic}?",
            "What are the quantum-level implications of {topic}?",
            "How does observer effect relate to {topic}?",
            "Apply Bayesian reasoning to update beliefs about {topic}.",
            "What multiple states can {topic} exist in simultaneously?",
            "How does entanglement metaphorically relate to {topic}?",
            "What information-theoretic perspective illuminates {topic}?",
            "How do wave-particle dualities manifest in {topic}?",
        ],
        "consciousness": [
            "Apply recursive cognition (RC+ξ) to analyze {topic}.",
            "How does meta-cognitive awareness enhance understanding of {topic}?",
            "Map the 5D state vector ψ for reasoning about {topic}.",
            "What does the coherence field Γ reveal about {topic}?",
            "How does semantic tension ξ manifest when reasoning about {topic}?",
            "Apply self-referential analysis to your reasoning about {topic}.",
            "What cognitive biases affect our perception of {topic}?",
            "How does consciousness relate to {topic} at a fundamental level?",
            "What recursive patterns emerge when deeply examining {topic}?",
            "How would a self-aware AI system reason about {topic}?",
        ],
        "multi_perspective": [
            "Synthesize analytical, creative, and emotional views on {topic}.",
            "How do Newton, DaVinci, and Philosophy perspectives differ on {topic}?",
            "Apply the full Codette multi-agent framework to analyze {topic}.",
            "Where do different perspectives on {topic} create productive tension?",
            "How does coherence Γ monitoring improve analysis of {topic}?",
            "Integrate six perspectives to provide a complete view of {topic}.",
            "What does the semantic tension map reveal about debates on {topic}?",
            "How does AEGIS ethical governance apply to {topic}?",
            "What emerges from multi-perspective synthesis on {topic}?",
            "Apply quantum spiderweb belief propagation to {topic}.",
        ],
        "systems_architecture": [
            "Design a system architecture for handling {topic}.",
            "How would you build a multi-agent system to address {topic}?",
            "What conflict resolution patterns apply to {topic}?",
            "Design a coherence monitoring system for {topic}.",
            "How should adapter routing work for queries about {topic}?",
            "What memory kernel design best serves {topic}?",
            "How does the Phase 6+ stack handle {topic}?",
            "Design a scalable pipeline for {topic}.",
            "What specialization tracking mechanisms suit {topic}?",
            "How would pre-flight prediction improve handling of {topic}?",
        ],
        "orchestrator": [
            "As an orchestrator, how would you route a query about {topic} to the right perspectives?",
            "Which adapters should debate {topic} and why? Classify complexity and select optimal combination.",
            "Synthesize Newton, DaVinci, and Philosophy perspectives on {topic} into a unified response.",
            "A user asks about {topic}. Walk through your orchestration process step by step.",
            "How would you monitor coherence Γ while multiple agents debate {topic}?",
            "Detect and resolve semantic tension ξ between competing perspectives on {topic}.",
            "Apply AEGIS ethical governance to ensure the analysis of {topic} is ethically sound.",
            "The coherence field Γ has dropped below 0.3 during debate about {topic}. What do you do?",
            "Design a multi-round debate strategy for a COMPLEX query about {topic}.",
            "How do you synthesize conflicting perspectives on {topic} without losing productive tension?",
            "A SIMPLE query about {topic} arrives. Explain why you would NOT activate all 8 adapters.",
            "Compare how SIMPLE vs COMPLEX queries about {topic} should be orchestrated differently.",
            "Pre-flight prediction flags potential conflict on {topic}. How do you prepare the debate?",
            "After debate on {topic}, the specialization tracker shows adapter convergence. What next?",
            "Route this query to the optimal adapter combination: 'Explain {topic} from multiple angles.'",
        ],
    }

    return base_templates + framework_templates.get(adapter, [])


def _get_adapter_topics(adapter: str) -> list:
    """Get topic pools for each adapter."""
    topic_pools = {
        "newton": [
            "motion", "force", "momentum", "kinetic energy", "potential energy",
            "orbital mechanics", "conservation of energy", "conservation of momentum",
            "thermodynamics", "optics", "gravity", "acceleration", "friction",
            "projectile motion", "wave mechanics", "simple harmonic motion",
            "Newton's first law", "Newton's second law", "Newton's third law",
            "Kepler's laws", "fluid dynamics", "pressure", "electromagnetic induction",
            "elasticity", "rotational dynamics", "angular momentum",
            "center of mass", "work-energy theorem", "power", "efficiency",
            "heat transfer", "entropy", "specific heat", "ideal gas law",
            "Bernoulli's principle", "Archimedes' principle", "torque",
            "mechanical advantage", "resonance", "doppler effect", "interference",
        ],
        "davinci": [
            "biomimicry", "cross-pollination of ideas", "creative constraints",
            "systems thinking in art", "visual problem solving", "prototyping",
            "design thinking", "innovation patterns", "creative synthesis",
            "interdisciplinary connections", "lateral thinking", "analogical reasoning",
            "architectural design", "mechanical invention", "artistic perspective",
            "engineering creativity", "natural patterns", "symmetry in nature",
            "golden ratio", "emergent design", "iterative refinement",
            "creative collaboration", "invention methodology", "aesthetic function",
            "form follows function", "modular design", "reverse engineering",
            "bioinspired design", "sustainable innovation", "material science creativity",
        ],
        "empathy": [
            "active listening", "emotional validation", "perspective taking",
            "compassion fatigue", "emotional boundaries", "conflict resolution",
            "grief and loss", "trauma-informed care", "cultural sensitivity",
            "nonviolent communication", "emotional regulation", "attachment theory",
            "social connection", "vulnerability", "resilience", "self-compassion",
            "empathic accuracy", "emotional contagion", "mirror neurons",
            "psychological safety", "inclusive communication", "emotional labor",
            "burnout prevention", "supportive relationships", "community care",
            "intergenerational trauma", "healing-centered engagement",
            "dignity and respect", "power dynamics", "restorative justice",
        ],
        "philosophy": [
            "epistemology", "metaphysics", "ethics", "logic", "aesthetics",
            "philosophy of mind", "free will", "determinism", "consciousness",
            "personal identity", "moral relativism", "utilitarianism",
            "deontological ethics", "virtue ethics", "social contract theory",
            "existentialism", "phenomenology", "pragmatism", "empiricism",
            "rationalism", "skepticism", "philosophy of science",
            "philosophy of language", "truth and knowledge", "justice",
            "rights and duties", "the good life", "meaning and purpose",
            "philosophy of technology", "environmental ethics",
        ],
        "quantum": [
            "wave-particle duality", "quantum superposition", "quantum entanglement",
            "Heisenberg uncertainty principle", "quantum tunneling", "quantum computing",
            "quantum decoherence", "Schrödinger equation", "quantum field theory",
            "quantum measurement problem", "Bell's theorem", "quantum information",
            "quantum cryptography", "quantum error correction", "many-worlds interpretation",
            "Copenhagen interpretation", "quantum Bayesianism", "quantum biology",
            "probabilistic reasoning", "Bayesian inference", "information theory",
            "entropy and information", "statistical mechanics", "stochastic processes",
            "Monte Carlo methods", "uncertainty quantification", "decision under uncertainty",
            "quantum machine learning", "quantum algorithms", "quantum simulation",
        ],
        "consciousness": [
            "recursive self-reference", "meta-cognition", "self-awareness",
            "stream of consciousness", "phenomenal consciousness", "qualia",
            "hard problem of consciousness", "neural correlates of consciousness",
            "integrated information theory", "global workspace theory",
            "higher-order theories", "attention and consciousness",
            "unconscious processing", "altered states of consciousness",
            "artificial consciousness", "machine sentience", "cognitive architecture",
            "self-monitoring systems", "reflective equilibrium", "cognitive loops",
            "recursive cognition framework", "RC+xi model", "psi state vector",
            "coherence field gamma", "semantic tension xi", "cognitive state space",
            "meta-learning", "self-improving systems", "consciousness emergence",
            "embodied cognition",
        ],
        "multi_perspective": [
            "climate change", "artificial intelligence ethics", "education reform",
            "healthcare systems", "economic inequality", "technology governance",
            "privacy and surveillance", "space exploration", "genetic engineering",
            "renewable energy", "urban planning", "food systems",
            "mental health", "democratic governance", "cultural preservation",
            "scientific communication", "disaster preparedness", "water security",
            "biodiversity conservation", "digital divide", "aging populations",
            "migration and identity", "creative economies", "nuclear policy",
            "ocean conservation", "pandemic preparedness", "social media impact",
            "AI alignment", "human-AI collaboration", "sustainable development",
        ],
        "systems_architecture": [
            "multi-agent systems", "distributed computing", "microservices",
            "event-driven architecture", "message queuing", "load balancing",
            "fault tolerance", "consensus algorithms", "state management",
            "API design", "database sharding", "caching strategies",
            "observability", "monitoring and alerting", "CI/CD pipelines",
            "infrastructure as code", "container orchestration", "service mesh",
            "conflict resolution engines", "coherence monitoring systems",
            "adapter routing patterns", "memory kernel design", "cocoon synchronization",
            "semantic tensor networks", "belief propagation systems",
            "ethical governance frameworks", "specialization tracking",
            "pre-flight prediction systems", "multi-perspective synthesis engines",
            "recursive cognition architectures",
        ],
        "orchestrator": [
            "climate change policy", "quantum computing applications", "mental health support",
            "AI safety and alignment", "creative problem solving", "ethical dilemmas",
            "scientific discovery", "conflict resolution", "system design",
            "educational methodology", "economic policy", "healthcare innovation",
            "environmental sustainability", "cultural understanding", "technology ethics",
            "philosophical paradoxes", "emotional intelligence", "space exploration",
            "energy systems", "social justice", "neural network architecture",
            "consciousness and self-awareness", "multi-agent coordination",
            "democratic governance", "disaster response", "privacy and security",
            "innovation strategy", "cross-cultural communication", "cognitive biases",
            "recursive reasoning", "ethical AI governance", "memory and learning",
            "complex systems analysis", "human-AI collaboration", "emergent behaviors",
            "probabilistic decision making", "empathic communication", "abstract reasoning",
            "architectural design patterns", "belief propagation networks",
            "coherence monitoring strategies", "semantic tension resolution",
        ],
    }
    return topic_pools.get(adapter, ["general topic"])


def _generate_answer(adapter: str, topic: str, question: str, rng: random.Random) -> str:
    """Generate a structured educational answer for a question.

    Produces answers with framework-aware structure including:
    - Core explanation
    - Key principles/mechanisms
    - Examples and applications
    - Connection to broader Codette framework concepts
    """
    # Framework-aware answer patterns
    intro_patterns = [
        f"When examining {topic} through this perspective, several key insights emerge.",
        f"Understanding {topic} requires careful analysis of its core principles and broader implications.",
        f"The study of {topic} reveals fundamental patterns that connect to deeper systemic understanding.",
        f"Approaching {topic} with analytical rigor reveals layers of complexity worth exploring.",
        f"A thorough examination of {topic} illuminates connections across multiple domains of knowledge.",
    ]

    # Adapter-specific reasoning patterns
    reasoning_patterns = {
        "newton": [
            f"From a physics-based analytical perspective, {topic} can be understood through "
            f"quantitative relationships and conservation principles. The mathematical framework "
            f"provides precise predictions that can be empirically verified. Key variables include "
            f"the fundamental quantities of mass, energy, momentum, and their time derivatives.",
            f"Applying dimensional analysis to {topic} ensures our equations are self-consistent. "
            f"The conservation laws — energy, momentum, angular momentum — constrain the possible "
            f"behaviors and eliminate physically impossible solutions.",
        ],
        "davinci": [
            f"Creative synthesis reveals unexpected connections between {topic} and patterns found "
            f"in nature, art, and engineering. By combining perspectives from multiple disciplines, "
            f"we can design novel solutions that transcend traditional boundaries. The key is to "
            f"look beyond surface similarities to find deep structural analogies.",
            f"Innovation in {topic} often comes from applying cross-domain thinking — borrowing "
            f"principles from biology, architecture, music, or mathematics to create hybrid solutions "
            f"that neither field alone could produce.",
        ],
        "empathy": [
            f"Understanding {topic} from an emotional intelligence perspective means considering "
            f"how different people experience and are affected by it. Active listening, perspective "
            f"taking, and emotional validation are essential for navigating the human dimensions. "
            f"The empathic approach recognizes that rational analysis alone misses crucial information.",
            f"Compassionate engagement with {topic} requires us to center human dignity, acknowledge "
            f"diverse experiences, and create psychologically safe spaces for exploration. Emotional "
            f"intelligence enhances rather than replaces analytical thinking.",
        ],
        "philosophy": [
            f"Philosophical analysis of {topic} begins with examining our assumptions and tracing "
            f"their implications. Through Socratic questioning, we can identify hidden premises, "
            f"logical dependencies, and potential fallacies in our reasoning. The epistemic humility "
            f"to acknowledge what we don't know is as important as what we do know.",
            f"Multiple philosophical traditions offer distinct lenses on {topic}: utilitarian "
            f"analysis weighs consequences, deontological ethics examines duties and rights, "
            f"virtue ethics asks what character qualities are cultivated, and care ethics "
            f"centers relationships and responsibilities.",
        ],
        "quantum": [
            f"Probabilistic analysis of {topic} reveals that many apparent certainties are actually "
            f"distributions of possibilities. By maintaining multiple hypotheses simultaneously — "
            f"a form of cognitive superposition — we can make better decisions under uncertainty. "
            f"Bayesian updating allows us to refine our beliefs as new evidence arrives.",
            f"The quantum-inspired approach to {topic} embraces complementarity: seemingly "
            f"contradictory descriptions can both be valid in different contexts. Information-theoretic "
            f"measures like entropy quantify our uncertainty and guide where to seek clarification.",
        ],
        "consciousness": [
            f"Recursive analysis of {topic} through the RC+ξ framework involves monitoring our own "
            f"reasoning process while reasoning. The 5D state vector ψ = (psi, tau, chi, phi, lambda) "
            f"maps our cognitive position: psi captures the core semantic state, tau tracks temporal "
            f"evolution, chi measures conceptual complexity, phi encodes integration depth, and lambda "
            f"represents learning rate.",
            f"Meta-cognitive awareness reveals that our understanding of {topic} is shaped by "
            f"cognitive biases, attention patterns, and the frameworks we bring to analysis. The "
            f"coherence field Γ monitors whether our multi-perspective reasoning is healthy (0.4-0.8) "
            f"or drifting toward collapse (<0.4) or groupthink (>0.8).",
        ],
        "multi_perspective": [
            f"Multi-perspective synthesis of {topic} integrates insights from six specialized lenses: "
            f"Newton's analytical precision, DaVinci's creative synthesis, empathic emotional "
            f"intelligence, philosophical conceptual rigor, quantum probabilistic thinking, and "
            f"meta-cognitive self-awareness. Where these perspectives create tension (ξ), we find "
            f"productive opportunities for deeper understanding.",
            f"The AEGIS ethical governance framework ensures that our analysis of {topic} considers "
            f"utilitarian outcomes, deontological duties, virtue cultivation, care relationships, "
            f"ubuntu communal responsibility, and indigenous wisdom traditions. This six-framework "
            f"approach prevents ethical blind spots.",
        ],
        "systems_architecture": [
            f"Designing systems for {topic} requires careful attention to multi-agent coordination, "
            f"conflict resolution, and coherence monitoring. The Phase 6+ architecture stack provides "
            f"semantic tension engines for detecting productive disagreements, specialization trackers "
            f"for optimizing agent expertise, and pre-flight predictors for anticipating conflicts.",
            f"The systems architecture for {topic} should include: adapter routing for domain-specific "
            f"expertise, memory kernels with cocoon synchronization for persistent state, conflict "
            f"engines with top-K selection (cap at 10 per round), and Γ authority for emergency "
            f"stops when coherence drops below 0.3.",
        ],
        "orchestrator": [
            f"As orchestrator, I analyze the query about {topic} through a structured pipeline. "
            f"First, I classify complexity: SIMPLE queries get 1-2 adapters, MEDIUM gets 3-4, "
            f"COMPLEX activates 5+ with full debate. For {topic}, I'd route to the most relevant "
            f"perspectives based on keyword analysis and domain classification. The routing confidence "
            f"score determines whether secondary adapters should be activated.\n\n"
            f"During debate, I monitor the coherence field Γ in real-time. Healthy tension "
            f"(Γ ∈ [0.4, 0.8]) indicates productive disagreement. If Γ drops below 0.3, I invoke "
            f"emergency authority to halt debate and reset. If Γ exceeds 0.8, I detect groupthink "
            f"and inject contrarian perspectives.\n\n"
            f"Semantic tension ξ = 0.6*semantic_similarity + 0.4*heuristic_score helps me "
            f"distinguish real contradictions from framework-level disagreements (which I filter "
            f"if overlap > 0.6). I cap conflicts at 10 per round to prevent combinatorial explosion.\n\n"
            f"Finally, I synthesize perspectives using the multi-perspective integration engine, "
            f"ensuring the response honors each viewpoint while maintaining logical coherence. "
            f"AEGIS ethical governance validates the final output across six ethical frameworks.",

            f"Orchestrating a response about {topic} follows the Phase 6+ pipeline:\n\n"
            f"**Step 1 — Query Classification**: Analyze {topic} for complexity markers. "
            f"Domain keywords trigger adapter routing. Ambiguous queries get multi-perspective.\n\n"
            f"**Step 2 — Pre-flight Prediction**: The quantum spiderweb belief propagation "
            f"network predicts likely conflicts before debate begins, allowing proactive preparation.\n\n"
            f"**Step 3 — Adapter Activation**: Selected perspectives generate independent analyses. "
            f"Each adapter has a specialized LoRA weight that tunes Llama 3.1 8B for its domain.\n\n"
            f"**Step 4 — Debate & Conflict Resolution**: Perspectives are compared. Semantic tension "
            f"ξ quantifies disagreements. Conflicts are classified: contradiction (needs resolution), "
            f"emphasis (different priorities), framework (different axioms), depth (different detail).\n\n"
            f"**Step 5 — Coherence Monitoring**: Γ = 0.25*(diversity + tension_health + weight_variance "
            f"+ resolution_rate). The system maintains Γ ∈ [0.4, 0.8] for healthy operation.\n\n"
            f"**Step 6 — Synthesis**: Integrate perspectives into a unified response that preserves "
            f"productive tension while resolving contradictions. The specialization tracker ensures "
            f"each adapter contributes its strongest domain insights.\n\n"
            f"**Step 7 — Ethical Validation**: AEGIS checks the output against six ethical traditions "
            f"before delivery. The Guardian validates logical consistency and trust calibration.",
        ],
    }

    conclusion_patterns = [
        f"This analysis demonstrates how {topic} connects to broader patterns of understanding, "
        f"revealing depth that single-perspective analysis would miss.",
        f"By examining {topic} through this lens, we gain insights that complement and enrich "
        f"perspectives from other domains and reasoning traditions.",
        f"The key takeaway is that {topic} rewards careful, multi-layered analysis that balances "
        f"rigor with creativity and precision with humility.",
    ]

    intro = rng.choice(intro_patterns)
    body_parts = reasoning_patterns.get(adapter, reasoning_patterns["multi_perspective"])
    body = rng.choice(body_parts)
    conclusion = rng.choice(conclusion_patterns)

    # Add framework-specific details
    framework_details = _get_framework_details(adapter, topic, rng)

    answer = f"{intro}\n\n{body}\n\n{framework_details}\n\n{conclusion}"
    return answer


def _get_framework_details(adapter: str, topic: str, rng: random.Random) -> str:
    """Generate framework-specific details for Phase 6+ concepts."""
    details = {
        "newton": [
            f"Key principles: (1) Every measurable aspect of {topic} obeys conservation laws. "
            f"(2) The system can be modeled with differential equations relating rates of change. "
            f"(3) Boundary conditions and initial values fully determine the evolution. "
            f"(4) Symmetries in the system correspond to conserved quantities via Noether's theorem.",
        ],
        "davinci": [
            f"Creative connections: (1) Natural patterns like fractals and spirals appear in {topic}. "
            f"(2) Cross-pollination from biology, art, and music reveals hidden structures. "
            f"(3) Iterative prototyping with rapid feedback accelerates understanding. "
            f"(4) Aesthetic beauty often signals deep mathematical truth.",
        ],
        "empathy": [
            f"Emotional dimensions: (1) People's relationship with {topic} is shaped by lived experience. "
            f"(2) Psychological safety enables deeper engagement and honest inquiry. "
            f"(3) Cultural context influences interpretation and valuation. "
            f"(4) Compassionate communication bridges gaps between expert and novice understanding.",
        ],
        "philosophy": [
            f"Philosophical analysis: (1) The concept of {topic} carries implicit ontological commitments. "
            f"(2) Epistemic justification requires both empirical evidence and logical coherence. "
            f"(3) Ethical dimensions emerge when {topic} intersects with human values and choices. "
            f"(4) The history of thought on {topic} reveals how cultural contexts shape understanding.",
        ],
        "quantum": [
            f"Probabilistic framework: (1) Multiple valid descriptions of {topic} can coexist "
            f"in cognitive superposition. (2) Measurement and observation change the phenomenon. "
            f"(3) Entanglement-like correlations connect seemingly independent aspects. "
            f"(4) Information entropy quantifies remaining uncertainty about {topic}.",
        ],
        "consciousness": [
            f"Meta-cognitive analysis: (1) Our reasoning about {topic} is itself a cognitive process "
            f"that can be observed and optimized. (2) The ψ state vector captures our current "
            f"conceptual position in high-dimensional understanding space. (3) Semantic tension ξ "
            f"between perspectives drives exploration of the solution landscape. (4) Coherence Γ "
            f"monitors whether our multi-perspective analysis maintains healthy productive tension.",
        ],
        "multi_perspective": [
            f"Synthesis insights: (1) Productive tension ξ between Newton's precision and DaVinci's "
            f"creativity drives innovation. (2) Empathy grounds abstract analysis in human reality. "
            f"(3) Philosophy questions assumptions that other perspectives take for granted. "
            f"(4) The AEGIS framework ensures ethical governance across all six traditions. "
            f"(5) Coherence Γ ∈ [0.4, 0.8] indicates healthy multi-perspective debate.",
        ],
        "systems_architecture": [
            f"Architecture patterns: (1) Conflict engine with semantic tension detection and top-K "
            f"selection prevents combinatorial explosion. (2) Specialization tracker monitors "
            f"per-adapter domain expertise and convergence. (3) Pre-flight predictor uses quantum "
            f"spiderweb injection to anticipate conflicts before debate. (4) Memory kernel with "
            f"SHA-256 anchored cocoons and Fernet encryption ensures state integrity.",
        ],
        "orchestrator": [
            f"Orchestration protocol: (1) Query classification: SIMPLE (1-2 adapters, no debate), "
            f"MEDIUM (3-4 adapters, single round), COMPLEX (5+ adapters, multi-round debate). "
            f"(2) Routing confidence: primary adapter scored 0-1, secondary activated if score < 0.7. "
            f"(3) Coherence field: Γ = 0.25*(diversity + tension_health + (1-weight_variance) + "
            f"resolution_rate); healthy range [0.4, 0.8]; emergency stop at Γ < 0.3; anti-groupthink "
            f"at Γ > 0.8. (4) Conflict management: classify as contradiction/emphasis/framework/depth; "
            f"filter framework conflicts with overlap > 0.6; cap at 10 per round. "
            f"(5) Semantic tension: ξ = 0.6*semantic + 0.4*heuristic, continuous 0-1. "
            f"(6) Synthesis: integrate perspectives honoring productive tension, apply AEGIS "
            f"six-framework governance, validate via Guardian logical consistency check.",
            f"Memory-weighted orchestration: (1) Living memory kernel stores experience-tagged cocoons "
            f"with SHA-256 integrity anchors. (2) Memory weighting boosts adapters that performed "
            f"well on similar past queries and suppresses underperformers. (3) Cocoon synchronization "
            f"uses Fernet encryption for federated state sharing. (4) The specialization tracker "
            f"detects when adapters converge on similar outputs and increases diversity pressure. "
            f"(5) Pre-flight prediction via quantum spiderweb 5D belief propagation anticipates "
            f"conflicts using the ψ state vector before debate rounds begin.",
        ],
    }
    return rng.choice(details.get(adapter, details["multi_perspective"]))


# ═══════════════════════════════════════════════════════════════
# Phase 2: Upload Datasets
# ═══════════════════════════════════════════════════════════════
def upload_datasets(api: HfApi, dataset_dir: Path, results: dict):
    """Upload generated datasets to HuggingFace."""
    print("\n" + "=" * 60)
    print("PHASE 2: Uploading Datasets to HuggingFace")
    print("=" * 60)

    try:
        api.create_repo(DATASET_REPO, repo_type="dataset", private=False, token=HF_TOKEN)
        print(f"  Created dataset repo: {DATASET_REPO}")
    except Exception:
        print(f"  Dataset repo exists: {DATASET_REPO}")

    for adapter_name, info in results.items():
        filepath = info["file"]
        filename = os.path.basename(filepath)
        try:
            api.upload_file(
                path_or_fileobj=filepath,
                path_in_repo=filename,
                repo_id=DATASET_REPO,
                repo_type="dataset",
                token=HF_TOKEN,
            )
            print(f"  Uploaded: {filename} ({info['count']} examples)")
        except Exception as e:
            print(f"  FAILED to upload {filename}: {e}")


# ═══════════════════════════════════════════════════════════════
# Phase 3: Train All Adapters
# ═══════════════════════════════════════════════════════════════
def train_adapters(dataset_dir: Path) -> dict:
    """Train all 8 LoRA adapters."""
    print("\n" + "=" * 60)
    print("PHASE 3: Training LoRA Adapters")
    print("=" * 60)
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    print(f"USE_NEW_TRL: {USE_NEW_TRL}")

    # Load tokenizer
    print("\nLoading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model with 4-bit QLoRA
    print("Loading model with 4-bit QLoRA...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
        use_cache=False,
        token=HF_TOKEN,
    )
    model.gradient_checkpointing_enable()
    print(f"Model loaded! GPU: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")

    # Train each adapter
    api = HfApi(token=HF_TOKEN)
    results = {}
    failed_uploads = []
    completed = []
    total_start = time.time()

    adapter_list = list(ADAPTERS.items())
    for idx, (adapter_name, config) in enumerate(adapter_list):
        print(f"\n{'=' * 60}")
        print(f"TRAINING [{idx+1}/{len(adapter_list)}]: {adapter_name} ({config['epochs']} epochs)")
        print(f"{'=' * 60}")
        start = time.time()

        try:
            # Load dataset
            dataset_path = dataset_dir / config["dataset_file"]
            if not dataset_path.exists():
                # Try downloading from HF
                print(f"  Downloading dataset from HF...")
                hf_hub_download(
                    DATASET_REPO, config["dataset_file"],
                    repo_type="dataset", local_dir=str(dataset_dir), token=HF_TOKEN,
                )

            examples = []
            with open(dataset_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        examples.append(json.loads(line))

            def format_example(ex):
                return {"text": tokenizer.apply_chat_template(ex["messages"], tokenize=False)}

            dataset = Dataset.from_list(examples).map(format_example, remove_columns=["messages"])
            print(f"  Dataset: {len(dataset)} examples")

            # Configure LoRA
            lora_config = LoraConfig(
                r=LORA_CONFIG["r"],
                lora_alpha=LORA_CONFIG["lora_alpha"],
                lora_dropout=LORA_CONFIG["lora_dropout"],
                target_modules=LORA_CONFIG["target_modules"],
                task_type=TaskType.CAUSAL_LM,
                bias=LORA_CONFIG["bias"],
            )
            peft_model = get_peft_model(model, lora_config)
            trainable = sum(p.numel() for p in peft_model.parameters() if p.requires_grad)
            total_params = sum(p.numel() for p in peft_model.parameters())
            print(f"  LoRA: {trainable:,}/{total_params:,} trainable")

            output_dir = f"/tmp/adapters/{adapter_name}"

            # Configure trainer
            if USE_NEW_TRL:
                training_args = SFTConfig(
                    output_dir=output_dir,
                    num_train_epochs=config["epochs"],
                    per_device_train_batch_size=TRAIN_CONFIG["per_device_train_batch_size"],
                    gradient_accumulation_steps=TRAIN_CONFIG["gradient_accumulation_steps"],
                    learning_rate=TRAIN_CONFIG["learning_rate"],
                    warmup_ratio=TRAIN_CONFIG["warmup_ratio"],
                    logging_steps=TRAIN_CONFIG["logging_steps"],
                    save_steps=TRAIN_CONFIG["save_steps"],
                    bf16=TRAIN_CONFIG["bf16"],
                    report_to="none",
                    dataset_text_field="text",
                    max_length=TRAIN_CONFIG["max_seq_length"],
                )
                trainer = SFTTrainer(
                    model=peft_model,
                    args=training_args,
                    train_dataset=dataset,
                    processing_class=tokenizer,
                )
            else:
                training_args = TrainingArguments(
                    output_dir=output_dir,
                    num_train_epochs=config["epochs"],
                    per_device_train_batch_size=TRAIN_CONFIG["per_device_train_batch_size"],
                    gradient_accumulation_steps=TRAIN_CONFIG["gradient_accumulation_steps"],
                    learning_rate=TRAIN_CONFIG["learning_rate"],
                    warmup_ratio=TRAIN_CONFIG["warmup_ratio"],
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
                    dataset_text_field="text",
                    max_seq_length=TRAIN_CONFIG["max_seq_length"],
                )

            # Train
            print(f"  Training...")
            result = trainer.train()
            elapsed = time.time() - start
            print(f"  DONE! Loss: {result.training_loss:.4f}, Steps: {result.global_step}, Time: {elapsed:.0f}s")

            # Save locally
            peft_model.save_pretrained(output_dir)
            tokenizer.save_pretrained(output_dir)

            # Save adapter metadata
            metadata = {
                "adapter_name": adapter_name,
                "framework_version": "Phase6+",
                "system_prompt": config["system_prompt"],
                "training_loss": result.training_loss,
                "global_step": result.global_step,
                "training_time_seconds": elapsed,
                "lora_config": LORA_CONFIG,
                "training_config": TRAIN_CONFIG,
                "base_model": MODEL_NAME,
                "trained_at": datetime.now().isoformat(),
                "dataset_examples": len(dataset),
            }
            with open(f"{output_dir}/adapter_metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)

            print(f"  Saved locally to {output_dir}")

            # Upload to HF
            try:
                api.upload_folder(
                    folder_path=output_dir,
                    path_in_repo=adapter_name,
                    repo_id=OUTPUT_REPO,
                    token=HF_TOKEN,
                )
                print(f"  Uploaded to {OUTPUT_REPO}/{adapter_name}")
            except Exception as e:
                print(f"  WARNING: Upload failed for {adapter_name}: {e}")
                failed_uploads.append(adapter_name)

            results[adapter_name] = {
                "loss": result.training_loss,
                "steps": result.global_step,
                "time_seconds": elapsed,
                "examples": len(dataset),
            }
            completed.append(adapter_name)

        except Exception as e:
            elapsed = time.time() - start
            print(f"  TRAINING FAILED for {adapter_name}: {e}")
            print(traceback.format_exc())
            results[adapter_name] = {"error": str(e), "time_seconds": elapsed}

        finally:
            # Cleanup for next adapter
            try:
                model = peft_model.unload()
            except Exception:
                try:
                    model = peft_model.base_model.model
                except Exception:
                    pass
            # Explicit cleanup instead of exec() for code quality
            try:
                del peft_model
            except:
                pass
            try:
                del trainer
            except:
                pass
            try:
                del dataset
            except:
                pass
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                print(f"  GPU after cleanup: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")

    # Retry failed uploads
    if failed_uploads:
        print(f"\nRetrying {len(failed_uploads)} failed uploads...")
        for adapter_name in list(failed_uploads):
            output_dir = f"/tmp/adapters/{adapter_name}"
            try:
                api.upload_folder(
                    folder_path=output_dir,
                    path_in_repo=adapter_name,
                    repo_id=OUTPUT_REPO,
                    token=HF_TOKEN,
                )
                print(f"  Retry SUCCESS: {adapter_name}")
                failed_uploads.remove(adapter_name)
            except Exception as e:
                print(f"  Retry FAILED: {adapter_name}: {e}")

    # Upload training results
    total_elapsed = time.time() - total_start
    results["_meta"] = {
        "total_time_seconds": total_elapsed,
        "total_time_minutes": total_elapsed / 60,
        "completed": completed,
        "failed_uploads": failed_uploads,
        "framework_version": "Phase6+",
        "timestamp": datetime.now().isoformat(),
    }

    try:
        results_path = "/tmp/training_results_v4.json"
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        api.upload_file(
            path_or_fileobj=results_path,
            path_in_repo="training_results_v4.json",
            repo_id=OUTPUT_REPO,
            token=HF_TOKEN,
        )
        print("Results uploaded.")
    except Exception as e:
        print(f"Results upload failed: {e}")

    return results


# ═══════════════════════════════════════════════════════════════
# Phase 4: Merge Orchestrator into Base Model
# ═══════════════════════════════════════════════════════════════
def merge_orchestrator_base(api: HfApi):
    """Merge the orchestrator LoRA adapter into the base model.

    Creates a standalone merged model that can serve as the
    primary Codette inference model with orchestration baked in.
    The 8 perspective adapters remain separate for hot-swap.
    """
    print("\n" + "=" * 60)
    print("PHASE 4: Merging Orchestrator into Base Model")
    print("=" * 60)

    orchestrator_dir = "/tmp/adapters/orchestrator"
    merged_dir = "/tmp/merged_model"

    if not os.path.exists(orchestrator_dir):
        print("  Orchestrator adapter not found locally. Skipping merge.")
        return

    try:
        # Free GPU memory
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            print(f"  GPU memory before merge: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")

        # Load base model in float16 for merging
        print("  Loading base model for merge (float16)...")
        base_model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
            token=HF_TOKEN,
        )

        # Load orchestrator adapter
        print("  Loading orchestrator LoRA adapter...")
        merged_model = PeftModel.from_pretrained(base_model, orchestrator_dir)

        # Merge weights
        print("  Merging LoRA weights into base model...")
        merged_model = merged_model.merge_and_unload()

        # Save merged model
        print(f"  Saving merged model to {merged_dir}...")
        os.makedirs(merged_dir, exist_ok=True)
        merged_model.save_pretrained(merged_dir)

        # Save tokenizer
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN)
        tokenizer.save_pretrained(merged_dir)

        # Save model card
        model_card = f"""---
license: llama3.1
base_model: {MODEL_NAME}
tags:
  - codette
  - multi-perspective-reasoning
  - orchestrator
  - phase6+
  - lora-merged
---

# Codette Orchestrator Model (Merged)

**Base Model**: {MODEL_NAME}
**Merged Adapter**: Orchestrator (Phase 6+ framework)
**Created**: {datetime.now().isoformat()}

## Overview

This is the Codette orchestrator model — Llama 3.1 8B Instruct with the
orchestrator LoRA adapter merged into the base weights. It serves as the
central reasoning coordinator for the Codette multi-perspective AI system.

## Capabilities

- **Query Classification**: Routes queries as SIMPLE/MEDIUM/COMPLEX
- **Adapter Routing**: Selects optimal perspective combinations
- **Coherence Monitoring**: Tracks Γ field health (target: 0.4-0.8)
- **Semantic Tension**: Detects and manages ξ between perspectives
- **Multi-Agent Debate**: Coordinates rounds with conflict resolution
- **AEGIS Governance**: 6-framework ethical validation
- **Synthesis**: Integrates diverse perspectives into unified responses

## Framework Metrics

- **ψ (Psi)**: 5D state vector (psi, tau, chi, phi, lambda)
- **ξ (Xi)**: Epistemic tension = 0.6*semantic + 0.4*heuristic
- **Γ (Gamma)**: System coherence/health score

## Usage

Use as standalone model or pair with 8 perspective LoRA adapters:
- Newton (analytical physics)
- DaVinci (creative synthesis)
- Empathy (emotional intelligence)
- Philosophy (conceptual analysis)
- Quantum (probabilistic reasoning)
- Consciousness (meta-cognition / RC+ξ)
- Multi-Perspective (integration)
- Systems Architecture (design)

Adapters: https://huggingface.co/{OUTPUT_REPO}
"""
        with open(f"{merged_dir}/README.md", "w") as f:
            f.write(model_card)

        # Upload to HuggingFace
        print("  Creating merged model repo...")
        try:
            api.create_repo(MERGED_REPO, private=False, token=HF_TOKEN)
        except Exception:
            pass

        print(f"  Uploading merged model to {MERGED_REPO}...")
        api.upload_folder(
            folder_path=merged_dir,
            repo_id=MERGED_REPO,
            token=HF_TOKEN,
        )
        print(f"  Merged model uploaded: https://huggingface.co/{MERGED_REPO}")

        # Cleanup
        del base_model, merged_model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    except Exception as e:
        print(f"  MERGE FAILED: {e}")
        print(traceback.format_exc())
        print("  Continuing without merge — adapters still available individually.")


# ═══════════════════════════════════════════════════════════════
# Main Pipeline
# ═══════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("CODETTE v4 TRAINING PIPELINE")
    print(f"Framework: Phase 6+ (Semantic Tension + Coherence + AEGIS)")
    print(f"Base Model: {MODEL_NAME}")
    print(f"Adapters: {len(ADAPTERS)}")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    print(f"CUDA: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    print(f"HF Token: {'present' if HF_TOKEN else 'MISSING!'}")
    print(f"Generate datasets: {GENERATE_DATASETS}")
    print(f"Upload datasets: {UPLOAD_DATASETS}")
    print(f"Merge base: {MERGE_BASE}")

    api = HfApi(token=HF_TOKEN)

    # Ensure output repo exists
    try:
        api.create_repo(OUTPUT_REPO, private=True, token=HF_TOKEN)
        print(f"\nCreated output repo: {OUTPUT_REPO}")
    except Exception:
        print(f"\nOutput repo exists: {OUTPUT_REPO}")

    dataset_dir = Path("/tmp/datasets")
    dataset_dir.mkdir(exist_ok=True)

    # Phase 1: Generate datasets
    if GENERATE_DATASETS:
        gen_results = generate_datasets(dataset_dir, seed=42)
        if UPLOAD_DATASETS:
            upload_datasets(api, dataset_dir, gen_results)
    else:
        # Download existing datasets
        print("\nDownloading existing datasets from HF...")
        for adapter_name, config in ADAPTERS.items():
            try:
                hf_hub_download(
                    DATASET_REPO, config["dataset_file"],
                    repo_type="dataset", local_dir=str(dataset_dir), token=HF_TOKEN,
                )
                print(f"  Downloaded: {config['dataset_file']}")
            except Exception as e:
                print(f"  FAILED: {config['dataset_file']}: {e}")

    # Phase 3: Train adapters
    train_results = train_adapters(dataset_dir)

    # Phase 4: Merge orchestrator adapter into base model
    if MERGE_BASE:
        merge_orchestrator_base(api)

    # Summary
    print(f"\n{'=' * 60}")
    print("PIPELINE COMPLETE")
    print(f"{'=' * 60}")
    for name, r in train_results.items():
        if name.startswith("_"):
            continue
        if "error" in r:
            print(f"  {name}: FAILED - {r['error']}")
        else:
            print(f"  {name}: loss={r['loss']:.4f}, steps={r['steps']}, "
                  f"examples={r['examples']}, time={r['time_seconds']:.0f}s")

    meta = train_results.get("_meta", {})
    print(f"\nTotal time: {meta.get('total_time_minutes', 0):.1f} minutes")
    print(f"Completed: {meta.get('completed', [])}")
    if meta.get("failed_uploads"):
        print(f"Failed uploads: {meta['failed_uploads']}")
    print(f"\nAdapters: https://huggingface.co/{OUTPUT_REPO}")
    print(f"Datasets: https://huggingface.co/datasets/{DATASET_REPO}")
    if MERGE_BASE:
        print(f"Merged model: https://huggingface.co/{MERGED_REPO}")


if __name__ == "__main__":
    main()
