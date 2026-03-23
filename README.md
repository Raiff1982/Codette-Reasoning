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
- behavioral-locks
- cognition-cocooner
library_name: peft
base_model: meta-llama/Llama-3.1-8B-Instruct
model-index:
- name: Codette RC+xi Reasoning Engine
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

# Codette Reasoning Engine

**Advanced Multi-Perspective AI with Conscience, Memory & Behavioral Discipline**

Codette is a production-ready AI reasoning system that thinks from multiple angles simultaneously, remembers what she learns, and follows instructions with precision.

Created by **Jonathan Harrison** (Raiff1982)

---

## What Makes Codette Different

| Feature | Description |
|---------|-------------|
| **9 Specialized Adapters** | Newton, DaVinci, Empathy, Philosophy, Quantum, Consciousness, Multi-Perspective, Systems Architecture, Orchestrator |
| **7-Layer Consciousness Stack** | Memory > Signal > Reasoning > Stability > Conscience > Guardian > Return |
| **4 Permanent Behavioral Locks** | Answer-then-stop, constraint priority, self-check completeness, no incomplete outputs |
| **CognitionCocooner** | Persistent memory cocoons that store reasoning exchanges across sessions |
| **EthicalAIGovernance** | 3-layer ethical stack: query validation + response enforcement + audit logging |
| **Self-Correction Loop** | Detects constraint violations in her own output and rewrites before sending |
| **Behavioral Training** | All 9 LoRA adapters trained with 1,650 behavioral examples to lock in discipline |
| **Substrate-Aware Cognition** | Monitors RAM, CPU, inference latency — adjusts reasoning under pressure |
| **Cocoon Introspection** | Statistical self-analysis of her own reasoning history — real patterns, not generated text |
| **AEGIS Ethics** | 6-framework ethical evaluation (utilitarian, deontological, virtue, care, ubuntu, indigenous) |
| **Code7eCQURE** | Quantum emotional context enrichment on every query (Layer 2.5) |
| **Real Self-Diagnostic** | Health checks return measured values from 9 subsystems, not LLM-generated guesses |
| **Phase 6/7 Routing** | Query complexity classification, domain detection, executive control |

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Raiff1982/Codette-Reasoning.git
cd Codette-Reasoning
pip install -r requirements.txt
```

### 2. Download Models

**Base model** (one-time, ~5GB):
```bash
huggingface-cli download Raiff1982/codette-llama-3.1-8b-gguf \
  --local-dir models/base/
```

**Behavioral LoRA adapters** (~500MB total):
```bash
huggingface-cli download Raiff1982/codette-lora-adapters \
  --include "behavioral-gguf/*" \
  --local-dir behavioral-lora-f16-gguf/
```

### 3. Launch

```bash
# Windows
codette_web.bat

# Linux/Mac
python inference/codette_server.py
```

Visit **http://localhost:7860** -- Codette is ready.

### 4. Try It

```bash
curl -X POST http://localhost:7860/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is gravity? Explain in one sentence."}'
```

---

## Architecture

```
codette-clean/
|-- inference/                    # Server & UI
|   |-- codette_server.py         # Stdlib HTTP server with SSE streaming
|   |-- codette_orchestrator.py   # LoRA hot-swap engine (9 adapters, <1ms switch)
|   |-- codette_forge_bridge.py   # Phase 6/7 routing + constraint enforcement
|   |-- self_correction.py        # Autonomous violation detection & rewrite
|   |-- substrate_awareness.py    # Hardware-aware cognition (pressure monitoring)
|   |-- cocoon_introspection.py   # Self-analysis of reasoning history patterns
|   |-- adapter_router.py         # Keyword/LLM/hybrid query routing
|   +-- static/                   # Web UI (index.html, app.js, style.css)
|
|-- reasoning_forge/              # Consciousness & reasoning pipeline
|   |-- forge_engine.py           # 7-layer consciousness stack
|   |-- cognition_cocooner.py     # Persistent reasoning memory (cocoons)
|   |-- ethical_governance.py     # 3-layer ethical validation
|   |-- aegis.py                  # 6-framework ethical evaluation (AEGIS)
|   |-- code7e_cqure.py           # Quantum emotional reasoning engine
|   |-- colleen_conscience.py     # Conscience layer (Layer 5)
|   |-- guardian_spindle.py       # Guardian protection (Layer 6)
|   |-- memory_kernel.py          # Living memory system
|   |-- quantum_spiderweb.py      # 5D belief propagation
|   |-- query_classifier.py       # SIMPLE/MEDIUM/COMPLEX routing
|   |-- routing_metrics.py        # Adapter selection observability
|   +-- semantic_tension.py       # Embedding-based conflict measurement
|
|-- cocoons/                      # Persistent reasoning memories
|   |-- cocoon_*.json             # Individual reasoning exchanges
|   +-- behavior_memory.json      # Learned behavioral patterns
|
|-- training/                     # Adapter training pipeline
|   |-- train_behavioral_locks.py # Behavioral lock training (1,650 examples)
|   |-- convert_behavioral_to_gguf.py  # PEFT -> GGUF conversion
|   +-- emotional_exemplars/      # Gold-standard response examples
|
|-- models/                       # Model weights (not in git)
|   |-- base/                     # Llama 3.1 8B Q4_K_M GGUF
|   +-- adapters/                 # Original LoRA adapters (GGUF)
|
|-- behavioral-lora-f16-gguf/     # Behavioral LoRA adapters (GGUF)
+-- configs/                      # System configuration
    +-- adapter_registry.yaml     # Adapter definitions & prompts
```

---

## The 4 Permanent Behavioral Locks

These are baked into every adapter through training -- they cannot be overridden:

| Lock | Rule | Effect |
|------|------|--------|
| **LOCK 1** | Answer, then stop | No elaboration drift, no philosophical padding after the answer |
| **LOCK 2** | Constraints override all modes | User format instructions beat adapter personality every time |
| **LOCK 3** | Self-check completeness | "Did I answer fully and cleanly?" before sending |
| **LOCK 4** | No incomplete outputs | Never end a sentence mid-thought; simplify instead of cramming |

### Enforcement Layers

1. **Training** -- 1,650 behavioral examples across all 9 adapters
2. **System prompt** -- Permanent rules injected before every generation
3. **Constraint extraction** -- Regex detection of word limits, format requirements
4. **Post-processing** -- Clean sentence boundary truncation, dangling word detection
5. **Self-correction loop** -- Autonomous violation detection and rewrite

---

## 9 Specialized Adapters

| Adapter | Domain | Personality |
|---------|--------|-------------|
| **Newton** | Physics, math, analysis | Precise, methodical, evidence-based |
| **DaVinci** | Creative thinking, invention | Imaginative, cross-domain connections |
| **Empathy** | Emotional intelligence | Warm, validating, personally connected |
| **Philosophy** | Conceptual reasoning | Deep, structured, explores meaning |
| **Quantum** | Probabilistic thinking | Uncertainty-aware, superposition of ideas |
| **Consciousness** | Self-awareness, meta-cognition | Reflective, recursive, introspective |
| **Multi-Perspective** | Synthesis across all lenses | Balanced integration of viewpoints |
| **Systems Architecture** | Technical design, engineering | Structured, systematic, practical |
| **Orchestrator** | Executive control | Routes queries, manages adapter selection |

Each adapter is a LoRA fine-tune of Llama 3.1 8B, hot-swappable in <1ms via llama.cpp.

---

## Consciousness Stack (7 Layers)

```
Query In
    |
[Layer 1]    Memory Kernel -- recall relevant cocoon memories
[Layer 1.5]  Ethical Query Gate -- block harmful queries (EthicalAIGovernance)
[Layer 2]    Nexus Signal Engine -- entropy + intent detection
[Layer 2.5]  Code7eCQURE -- emotional context enrichment (quantum cocoon)
[Layer 3]    Reasoning Forge -- multi-adapter LLM inference
[Layer 3.5]  Tier 2 Analysis -- intent + identity + trust validation
[Layer 4]    Gamma Stability -- FFT-based coherence monitoring
[Layer 5]    Colleen Conscience -- emotional + ethical evaluation
[Layer 5.5]  Ethical Response Enforcement -- policy check on output
[Layer 5.75] AEGIS -- 6-framework ethical evaluation (eta alignment)
[Layer 6]    Guardian Spindle -- safety + trust calibration
[Layer 7]    Return -- store cocoon memory + deliver response
    |
Response Out
```

---

## CognitionCocooner (Persistent Memory)

Every reasoning exchange is wrapped in a "cocoon" and stored:

```json
{
  "id": "cocoon_1774125610_7804",
  "type": "reasoning",
  "query": "Why do I get sleepy when my husband plays guitar?",
  "response": "Your brain hears safe + soothing + familiar + loved...",
  "adapter": "empathy",
  "timestamp": 1774125610.78,
  "metadata": {"layers_passed": 7, "stable": true}
}
```

Cocoons persist across server restarts and inform future responses. Current count: **150+ memories**.

---

## Substrate-Aware Cognition

Codette monitors her own hardware state and adjusts reasoning based on resource pressure -- like biological fatigue:

| Pressure Level | Effect |
|----------------|--------|
| **Idle/Low** | Full capacity -- COMPLEX queries, all adapters available |
| **Moderate** | Cap COMPLEX queries to 2 adapters |
| **High** | Downgrade COMPLEX to MEDIUM, max 2 adapters |
| **Critical** | Force SIMPLE mode, 1 adapter only, skip debate |

Every cocoon memory is stamped with system state at creation time. Future sessions can weight cocoons by reliability -- stressed cocoons get less trust.

---

## Cocoon Introspection

When asked "what have you noticed about yourself?", Codette runs **real statistical analysis** of her own reasoning history:

- **Adapter dominance** -- is one adapter handling >40% of all queries?
- **Domain clusters** -- what topics does she get asked about most?
- **Emotional trends** -- what Code7E emotional patterns appear?
- **Pressure correlations** -- how do responses change under system stress?
- **Response length trends** -- are responses getting shorter or longer over time?
- **Adapter evolution** -- has her adapter usage shifted?

This is measured data from real cocoons, not generated text about self-reflection.

API access: `GET /api/introspection` returns full analysis as JSON.

---

## Phase 6/7 Routing

**Phase 6** classifies every query:
- **SIMPLE** (factual) -- 1 adapter, no debate, fast response
- **MEDIUM** (analytical) -- 2 adapters, weighted synthesis
- **COMPLEX** (philosophical/multi-domain) -- full debate pipeline

**Phase 7** adds executive control:
- Semantic tension measurement
- Specialization tracking per adapter per domain
- Memory-weighted context enrichment
- Gamma coherence monitoring

---

## Self-Correction System

```
Generate response
    |
    v
Detect violations (word count, completeness, binary compliance)
    |
    +--> No violations --> Send response
    |
    +--> Violations found --> Build correction prompt
                                 |
                                 v
                            Re-generate with explicit fix instructions
                                 |
                                 v
                            Pick better response (fewer violations)
                                 |
                                 v
                            Send response
```

---

## Behavioral Memory (Cross-Session Learning)

Stored in `cocoons/behavior_memory.json`:

```json
{
  "lesson": "When user says 'be brief', respond in under 40 words",
  "adapter": "philosophy",
  "constraint": "brevity",
  "violation": "gave 85 words when asked to be brief",
  "correction": "trimmed to 38 words",
  "timestamp": 1774125610
}
```

Lessons are loaded on startup and injected into the system prompt as "LEARNED FROM PAST MISTAKES".

---

## EthicalAIGovernance

Three-layer ethical stack integrated at Layers 1.5 and 5.5:

1. **Query Validation** -- blocks genuinely harmful requests (bomb-making, exploitation)
2. **Response Enforcement** -- filters bias patterns and harmful promotion from outputs
3. **Audit Logging** -- bounded log of all ethical decisions (max 100 entries)

Deliberately calibrated to avoid false positives -- discussions about sensitive topics are allowed; only active promotion of harm is blocked.

---

## HuggingFace Resources

| Resource | Link |
|----------|------|
| **Base Model (GGUF)** | [Raiff1982/codette-llama-3.1-8b-gguf](https://huggingface.co/Raiff1982/codette-llama-3.1-8b-gguf) |
| **LoRA Adapters** | [Raiff1982/codette-lora-adapters](https://huggingface.co/Raiff1982/codette-lora-adapters) |
| **Live Demo** | [Raiff1982/Codette-Demo](https://huggingface.co/spaces/Raiff1982/Codette-Demo) |

---

## Web UI Features

- Personality-driven welcome screen with avatar
- Real-time Phase 6 metadata badges (complexity, domain, ethical checks)
- Rotating thinking stage labels during generation
- Web Speech API voice with neural voice preference
- Cocoon metrics panel (phase coherence, epistemic tension, perspective coverage)
- Status bar with live cocoon count and ethical check indicators
- Voice selector with natural/neural voice ranking

---

## Requirements

- Python 3.10+
- 16GB+ RAM (or GPU with 8GB+ VRAM)
- llama-cpp-python with GGUF support
- ~6GB disk for base model + adapters

### Hardware Tested

- Intel Arc 140V (8GB) -- native XPU backend
- NVIDIA GPUs via CUDA (A10, A100, RTX series)
- CPU-only mode supported (slower but functional)

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Phase Coherence (Gamma) | 0.9835 |
| AEGIS Ethical Alignment (Eta) | 0.961 |
| Cocoon Coherence | 0.994 |
| Memory Phase Stability | 0.969 |
| Behavioral Lock Compliance | 9/9 adapters trained |
| Cocoon Memories | 200+ and growing |
| Adapter Hot-Swap Time | <1ms |
| Consciousness Stack Layers | 12 (including sub-layers) |
| Health Check Subsystems | 9 real-time checks |

---

## License

MIT -- Created by **Jonathan Harrison** (Raiff1982)

Research project in advanced multi-perspective AI reasoning, ethical governance, and behavioral discipline.
