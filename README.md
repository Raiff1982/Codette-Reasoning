---
language:
- en
license: mit
tags:
- codette
- multi-perspective-reasoning
- ethical-ai
- lora
- qlora
- llama-3.1
- recursive-cognition
- rc-xi
library_name: peft
base_model: meta-llama/Llama-3.1-8B-Instruct
model-index:
- name: Codette RC+xi Reasoning Adapters
  results:
  - task:
      type: text-generation
      name: Multi-Perspective Reasoning
    metrics:
    - name: Phase Coherence (Gamma)
      type: custom
      value: 0.9835
    - name: AEGIS Ethical Alignment (Eta)
      type: custom
      value: 0.961
    - name: Cocoon Coherence
      type: custom
      value: 0.994
    - name: Memory Phase Stability
      type: custom
      value: 0.969
---

# Codette Adapter Training Lab

Codette is an experimental AI research system for **recursive reasoning, multi-perspective cognition, and ethical AI alignment**, created by **Jonathan Harrison**.

This repository contains the complete training pipeline, inference server, and 8 trained LoRA adapters for the Codette cognitive architecture running on Llama 3.1 8B.

## 🚀 Latest Status (Session 2026-03-20) — PHASE 6 ARCHITECTURAL FIX DEPLOYED

### ✅ 5-Part Architectural Fix: Query Complexity & Soft Agent Gating (Complete)

**Problem Solved**: System was over-activating on simple queries (e.g., "speed of light" generated 71 conflicts, correctness=0.20)

**Solution Deployed**:
1. ✅ **Query Complexity Classifier** (`reasoning_forge/query_classifier.py`)
   - SIMPLE queries (factual) → 1 primary agent, no debate
   - MEDIUM queries → 3 weighted agents
   - COMPLEX queries → full 6-agent debate
   - Prevents unnecessary system activation on straightforward questions

2. ✅ **Conflict Capping at Source** (`reasoning_forge/conflict_engine.py`)
   - max_conflicts_per_pair = 2 (instead of generating 71)
   - max_total_conflicts = 12 (instead of 10-100)
   - Prevents wasteful conflict accumulation

3. ✅ **Confidence Override Logic** (`reasoning_forge/forge_engine.py`)
   - After Round 0 analysis: if SIMPLE + few conflicts + low disagreement → **skip entire debate**
   - Saves computation cycles on high-confidence answers
   - Expected impact: correctness 0.20 → 0.70+ on simple queries

4. ✅ **Semantic Tension Engine** (`reasoning_forge/semantic_tension.py`)
   - Embedding-based conflict strength (continuous 0-1, not discrete)
   - Llama embeddings replace heuristic opposition scores
   - 0.6*semantic + 0.4*heuristic hybrid blending

5. ✅ **Specialization Tracking & Pre-Flight Prediction** (`reasoning_forge/specialization_tracker.py`, `reasoning_forge/preflight_predictor.py`)
   - Per-adapter domain accuracy tracking
   - Pre-flight Spiderweb injection predicts conflicts before debate
   - Recommends optimal adapter selection upfront

### ✅ Agent LLM Integration Complete
All 6 reasoning agents use **real LLM inference** via trained LoRA adapters:
- **Newton** (physics reasoning) → newton adapter
- **Quantum** (probabilistic thinking) → quantum adapter
- **DaVinci** (creative invention) → davinci adapter
- **Philosophy** (conceptual reasoning) → philosophy adapter
- **Empathy** (emotional intelligence) → empathy adapter
- **Ethics** (moral reasoning) → philosophy adapter

**Result**: Agents generate domain-specific, LLM-backed reasoning instead of templates.

### ✅ GPU Acceleration Active
- Model load: ~8-10 seconds (GPU vs 40s CPU)
- Inference: 2-4 sec/query (GPU vs 15-20s CPU)
- Full eval: ~2-3 minutes (GPU vs 7-10 minutes CPU)
- **35/35 layers offloaded** to GPU via llama.cpp

### ✅ Phase 6 Framework Formalized
- **ψ (Psi)**: State vector encoding query domain and complexity (5D)
- **ξ (Xi)**: Semantic tension measurement (continuous, embedding-based)
- **Γ (Gamma)**: Coherence metrics with health monitoring
- **Evaluation**: `run_phase6_evaluation.py` — Compare baseline vs Phase 1-5 vs Phase 6 Full vs Phase 6 -PreFlight

## Model Weights

All 8 adapters are included in two formats:

| Format | Directory | Size | Use Case |
|--------|-----------|------|----------|
| **GGUF (f16)** | `adapters/*.gguf` | ~924 MB | llama.cpp inference with hot-swap |
| **PEFT SafeTensors** | `adapters_peft/*/` | ~79 MB | HuggingFace / transformers fine-tuning |

**Base model required**: `meta-llama/Llama-3.1-8B-Instruct` (or any Llama-3.1-8B variant with hidden_size=4096)

## Key Metrics

| Metric | Value | Context |
|--------|-------|---------|
| Phase Coherence (Gamma) | 0.9835 | 11-agent convergence |
| AEGIS Ethical Alignment (Eta) | 0.961 | 6-framework ethical governance |
| Cocoon Coherence | 0.994 | Memory state stability |
| Memory Phase Stability | 0.969 | Cross-session persistence |
| Tension Decay | 91.2% | 200-agent embodied simulation |

## Cognitive Subsystems (14 active)

| Subsystem | Module | Purpose |
|-----------|--------|---------|
| Reasoning Forge | `reasoning_forge/forge_engine.py` | 6-agent multi-perspective debate + synthesis |
| Query Classifier | `reasoning_forge/query_classifier.py` | Complexity-based agent selection (SIMPLE/MEDIUM/COMPLEX) |
| Semantic Tension | `reasoning_forge/semantic_tension.py` | Embedding-based conflict strength (Phase 6) |
| Specialization Tracker | `reasoning_forge/specialization_tracker.py` | Per-adapter domain expertise tracking (Phase 6) |
| Pre-Flight Predictor | `reasoning_forge/preflight_predictor.py` | Conflict prediction before debate (Phase 6) |
| Framework Definitions | `reasoning_forge/framework_definitions.py` | ψ, ξ, Γ formal definitions (Phase 6) |
| Epistemic Metrics | `reasoning_forge/epistemic_metrics.py` | RC+xi tension/coherence tracking |
| Quantum Spiderweb | `reasoning_forge/quantum_spiderweb.py` | 5D belief propagation + attractor detection |
| Cocoon Sync | `reasoning_forge/cocoon_sync.py` | Fernet-encrypted federated state sync |
| AEGIS | `reasoning_forge/aegis.py` | 6-framework ethical governance (utilitarian, deontological, virtue, care, ubuntu, indigenous) |
| Nexus Signal Engine | `reasoning_forge/nexus.py` | Pre-corruption detection via entropy + FFT + intent vectors |
| Living Memory | `reasoning_forge/living_memory.py` | Emotionally-tagged memory cocoons with SHA-256 anchors |
| Guardian | `reasoning_forge/guardian.py` | 3-layer protection (sanitizer + ethical anchor + trust calibrator) |
| Perspective Registry | `reasoning_forge/perspective_registry.py` | 12 perspectives (8 LoRA-backed + 4 prompt-only with fallback) |

## Architecture

```
codette-training-lab/
├── dataset_engine/          # Dataset generation pipeline
│   ├── template_registry.py # Rich template pools per adapter
│   ├── answer_generator.py  # Structured educational answer generation
│   ├── dataset_generator.py # Main generator with dedup + validation
│   └── templates/           # JSON template definitions
│
├── reasoning_forge/         # Multi-agent reasoning dataset refinement
│   ├── agents/              # Newton, Quantum, Ethics, Philosophy, DaVinci, Empathy
│   ├── critic_agent.py      # Quality evaluation agent
│   ├── synthesis_engine.py  # Multi-perspective synthesis
│   ├── problem_generator.py # Reasoning problem generation
│   └── forge_engine.py      # Orchestrator
│
├── training/                # LoRA training scripts
│   ├── train_adapter.py     # Single adapter training (4-bit LoRA)
│   ├── train_all_adapters.py# Sequential multi-adapter training
│   ├── merge_adapters.py    # Merge LoRA into base model
│   └── configs/             # Training hyperparameters
│
├── evaluation/              # Benchmarks and quality assurance
│   ├── reasoning_metrics.py # Multi-dimensional scoring
│   ├── benchmark_runner.py  # Automated evaluation
│   ├── dataset_validator.py # Dataset quality checks
│   ├── failure_analyzer.py  # Weakness detection
│   └── prompts/             # Benchmark test sets
│
├── observatory/             # Experiment tracking and monitoring
│   ├── metrics_logger.py    # Training run logging
│   ├── performance_tracker.py # Improvement trends
│   ├── dataset_quality_monitor.py
│   └── dashboard.py         # ASCII status dashboard
│
├── research/                # Source research documents
│   ├── papers/              # Published manuscripts
│   ├── frameworks/          # RC+xi, quantum equations, perspectives
│   └── experiments/         # Cocoon simulations, logs
│
├── datasets/                # Generated training datasets (JSONL)
├── adapters/                # Trained LoRA adapters
├── scripts/                 # Pipeline orchestration
│   ├── run_full_pipeline.py # End-to-end pipeline
│   └── hf_job.yaml          # HuggingFace job config
└── configs/                 # System configuration
    ├── adapter_registry.yaml
    └── pipeline_config.yaml
```

## Adapters

| Adapter | Domain | Target Examples | System Prompt |
|---------|--------|----------------|---------------|
| Newton | Analytical physics reasoning | 3000 | Newtonian analytical precision |
| DaVinci | Creative invention thinking | 2500 | Creative inventiveness |
| Empathy | Emotional understanding | 2500 | Deep empathy and EQ |
| Philosophy | Conceptual reasoning | 2000 | Philosophical depth |
| Quantum | Probabilistic thinking | 2000 | Quantum probabilistic thinking |
| RC+xi | Recursive cognition | 3000 | RC+xi framework reasoning |
| Multi-Perspective | Synthesis across lenses | 2500 | Multi-perspective synthesis |
| Systems | AI architecture | 2000 | System architecture design |

## Training Pipeline

```
research documents
      ↓
dataset extraction (template-based generation)
      ↓
synthetic reasoning expansion (counterexamples, variations)
      ↓
dataset validation (dedup, quality filter)
      ↓
reasoning forge (multi-agent critique + refinement)
      ↓
adapter training (4-bit LoRA on Llama 3.1 8B)
      ↓
benchmark evaluation (multi-dimensional reasoning metrics)
      ↓
observatory logging (track improvement over time)
```

## Quick Start

### Install dependencies

```bash
pip install -r requirements.txt
```

### Generate all datasets

```bash
python -m dataset_engine.generate_all
```

### Run full pipeline

```bash
python scripts/run_full_pipeline.py --all
```

### Generate + validate only

```bash
python scripts/run_full_pipeline.py --generate --validate
```

### Train a single adapter

```bash
python -m training.train_adapter \
  --dataset datasets/newton_reasoning.jsonl \
  --adapter-name newton \
  --output-dir adapters/newton
```

### Evaluate Phase 6 Component Impact

Compare 4 conditions to isolate Phase 6 value:
- **Baseline**: Llama only (no routing)
- **Phase 1-5**: Debate system without semantic tension or specialization
- **Phase 6 Full**: All components (semantic tension, specialization, pre-flight)
- **Phase 6 -PreFlight**: Phase 6 without pre-flight prediction

```bash
python run_phase6_evaluation.py
```

Generates statistical analysis and emergent behavior alerts:
- Correctness improvement (expected 0.20 → 0.70+ on simple queries)
- Reasoning depth per domain
- Adapter convergence detection
- Miscalibration warnings

Results exported to `evaluation_results_YYYYMMDD_HHMMSS.json`

## Dataset Format

All datasets use chat-format JSONL:

```json
{
  "messages": [
    {"role": "system", "content": "You are Codette, a recursive multi-perspective reasoning AI."},
    {"role": "user", "content": "Explain the conservation of momentum using a real-world example."},
    {"role": "assistant", "content": "Conservation of momentum states that in a closed system..."}
  ]
}
```

## Reasoning Forge

The Reasoning Forge refines training data through multi-agent debate:

```
concept → problem generator → agent analysis → critic evaluation → synthesis → training example
```

Agents: Newton (physics), Quantum (probability), Ethics (alignment), Philosophy (meaning), DaVinci (creativity), Empathy (emotion)

Each agent analyzes from its perspective, the critic scores quality, and the synthesis engine produces a unified multi-perspective response.

## Base Model

- **Model**: meta-llama/Llama-3.1-8B-Instruct
- **Method**: QLoRA (4-bit quantization)
- **LoRA config**: rank=16, alpha=32, target=q/k/v/o projections

## Research Background

Codette implements the RC+xi (Recursive Convergence + Epistemic Tension) framework for structured multi-perspective reasoning. The system coordinates 11 reasoning perspectives in parallel before synthesizing a final response.

Key research documents in `research/`:
- RC+xi Framework specification
- Quantum Cosmic Multicore experiment
- Codette Research Equations (8 core quantum mathematics)
- Multi-perspective reasoning architecture

## Inference & Evaluation

### Interactive Web UI

Launch the real-time multi-perspective reasoning UI:

```bash
# Launch web interface (default port 5000)
python inference/codette_server.py

# Or use the batch file (Windows)
codette_web.bat
```

Features:
- Real-time adapter hot-swap (0ms switching via llama.cpp LoRA)
- **Real LLM-backed agents** (not templates) generating domain-specific reasoning
- GPU acceleration (35 layers offloaded)
- Quantum spiderweb visualization
- Live AEGIS ethical alignment tracking
- Memory cocoon emotional profiling

### Evaluation & Testing

**Standard Evaluation** (4 conditions × 25 questions):
```bash
python evaluation/run_evaluation_sprint.py --questions 5
```

**Real-Time Agent Thinking** (see agents reasoning in real-time):
```bash
python evaluation/run_evaluation_verbose.py --questions 1
```

Shows:
- Agent mode: ✓ LLM (real inference) or ✗ TEMPLATE (fallback)
- System prompts used
- Token generation
- Domain detection and agent gating
- Conflict detection and capping
- Gamma coherence monitoring
- Final synthesis

**Verbose Logs** with `CODETTE_VERBOSE=1`:
```bash
CODETTE_VERBOSE=1 python evaluation/run_evaluation_verbose.py
```

Shows each agent's thinking step-by-step.

## LoRA Configuration

```yaml
method: QLoRA (4-bit NF4 quantization)
rank: 16
alpha: 32
dropout: 0.05
target_modules: [q_proj, k_proj, v_proj, o_proj]
total_training_examples: 20,500
```

## RC+xi Framework

The core theoretical framework — **Recursive Convergence + Epistemic Tension** — coordinates 11 reasoning perspectives:

1. Newton (analytical physics) → `newton` adapter
2. DaVinci (creative invention) → `davinci` adapter
3. Empathy (emotional intelligence) → `empathy` adapter
4. Philosophy (conceptual reasoning) → `philosophy` adapter
5. Quantum (probabilistic thinking) → `quantum` adapter
6. RC+xi Consciousness → `consciousness` adapter
7. Multi-Perspective Synthesis → `multi_perspective` adapter
8. Systems Architecture → `systems_architecture` adapter
9. Human Intuition → prompt-only (fallback: `empathy`)
10. Resilient Kindness → prompt-only (fallback: `empathy`)
11. AEGIS Ethics → prompt-only (fallback: `consciousness`)

## Requirements

- Python 3.10+
- PyTorch 2.1+ (CUDA, ROCm, or XPU backend)
- 16GB+ RAM (CPU training) or GPU with 8GB+ VRAM
- llama.cpp with GGUF support (for inference server)
- ~1-3 hours per adapter (CPU) or 20-40 min (A10/A100 GPU)

## Hardware Tested

- Intel Arc 140V (8GB) — PyTorch 2.10.0+xpu, native XPU backend
- NVIDIA GPUs via CUDA (A10, A100, RTX series)
- CPU-only mode supported

## License

MIT — Research project by Jonathan Harrison. Experimental AI development.
