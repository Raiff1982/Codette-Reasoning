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
    - name: Multi-Perspective vs Single (Composite)
      type: custom
      value: "+93.1%"
    - name: Benchmark p-value
      type: custom
      value: "<0.0001"
    - name: Cohen's d (Effect Size)
      type: custom
      value: 7.88
---

# Codette Reasoning Engine

**Advanced Multi-Perspective AI with Conscience, Memory & Behavioral Discipline**

Codette is a production-ready AI reasoning system that thinks from multiple angles simultaneously, remembers what she learns, and follows instructions with precision.

Created by **Jonathan Harrison** (Raiff1982)

> **Paper v7 available**: [`paper/codette_paper_v7.tex`](paper/codette_paper_v7.tex) — includes rebuttal changes, updated tables, and Kaggle notebook. Benchmark suite (17 problems, 6 categories) demonstrates **93.1% improvement** over single-perspective baseline (p < 0.0001, Cohen's d = 7.88). New **ablation study** isolates each component's contribution. Full v5 paper: [`paper/codette_paper_v5.pdf`](paper/codette_paper_v5.pdf)

### 🚀 Public Landing Page

**View the live landing page:** [`landing.html`](landing.html)

The landing page presents Codette's core value proposition: fully open, local, honest AI built for trust. Explore the messaging, feature comparison grades, and call to action.

---

## Evidence

Codette is a modular reasoning system with published demos, tests, benchmarks, and proof artifacts.

- **Proof index**: [docs/proof.md](docs/proof.md)
- **Runnable demos**: [demo/README.md](demo/README.md)
- **Automated tests**: [tests](tests)
- **Benchmark suites**: [benchmarks](benchmarks)
- **Saved benchmark reports**: [data/results](data/results)
- **Change transparency**: [docs/CHANGELOG_2026-04-26.md](docs/CHANGELOG_2026-04-26.md) · [docs/CHANGELOG_2026-04-02.md](docs/CHANGELOG_2026-04-02.md)
- **Contributing guide**: [CONTRIBUTING.md](CONTRIBUTING.md)

Quick evidence links:
- Multi-perspective benchmark report: [codette_benchmark_report.md](data/results/codette_benchmark_report.md)
- Runtime benchmark without web research: [codette_runtime_benchmark_20260402_135517.md](data/results/codette_runtime_benchmark_20260402_135517.md)
- Runtime benchmark with web research: [codette_runtime_benchmark_20260402_140237.md](data/results/codette_runtime_benchmark_20260402_140237.md)
- System proof PDF: [Codette_system_proof.pdf](docs/proof_assets/Codette_system_proof.pdf)
- Response proof PDF: [Codette_response_proof.pdf](docs/proof_assets/Codette_response_proof.pdf)
- UI conversation proof: [Codettechat_UI_conversation_proof.pdf](docs/proof_assets/Codettechat_UI_conversation_proof.pdf)

This repository includes reproducible evidence of:
- multi-perspective reasoning and synthesis
- continuity and memory recall
- valuation and risk-frontier analysis
- explicit, cited web research behavior
- loop resistance and failure-mode fixes

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
| **Meta-Cognitive Synthesis** | CocoonSynthesizer discovers cross-domain patterns in reasoning history and forges new strategies |
| **Publishable Benchmarks** | 17-problem suite across 6 categories with 7-dimension scoring (93.1% improvement, p<0.0001) |
| **Ablation Study** | `benchmarks/ablation_study.py` isolates each component's contribution — memory, ethical layer, sycophancy guard, single-agent baseline |
| **AEGIS Ethics** | 6-framework ethical evaluation (utilitarian, deontological, virtue, care, ubuntu, indigenous) with differentiable ethics potential field |
| **Code7eCQURE** | Stochastic multi-perspective reasoning with named cognitive frames (Newton, DaVinci, Ethical, Quantum, Memory) — metaphorical "quantum" framing for probabilistic reasoning |
| **WAL-mode SQLite** | Write-Ahead Logging + thread-safe write lock prevents serialization under concurrent requests |
| **Hardened Model Loading** | Path validation before load + 5-minute timeout prevent silent hangs on missing or corrupted GGUF |
| **Real Self-Diagnostic** | Health checks return measured values from 9 subsystems, not LLM-generated guesses |
| **Phase 6/7 Routing** | Query complexity classification, domain detection, executive control |
| **Session Continuity** | Active continuity summaries, decision landmarks, and recall markers reduce drift in long sessions |
| **Safe Web Research** | Optional cited web research with safe fetch rules and cocoon-backed recall for current facts |

---

## Transparency Notes

- **Local tools are not web search.** The built-in tool layer reads local files, searches local code, lists directories, and runs small safe Python snippets. It does not browse the live internet.
- **Web research is explicit and opt-in.** In the web UI, `Web Research` must be enabled for live current-facts retrieval. When used, results are injected with citations and surfaced back to the user as sources.
- **Web research is stored as memory.** Retrieved research is persisted as `web_research` cocoons so Codette can reuse prior cited findings instead of re-researching the same topic every time.
- **System reports are gated.** Self-diagnostic and introspection modes now require explicit phrasing so ordinary conversation does not accidentally fall into a report loop.
- **Trust cues are shown in the UI.** Responses can display trust tags such as `memory-backed`, `frontier-informed`, `web-cited`, `grounded`, or `low-verification`.

## Proof Structure

The repository now exposes a public evidence layout:

1. `README.md` for high-level claims and direct evidence links.
2. `docs/proof.md` for a proof index and audit map.
3. `demo/` for short reproducible local examples.
4. `tests/` for automated validation.
5. `benchmarks/` for saved methodology and benchmark runners.
6. `data/results/` for concrete benchmark outputs.
7. `logs/` for transcript and run-log capture guidance.

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
  --include "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf" \
  --local-dir models/base/
```

**Behavioral LoRA adapters** (~500MB total):
```bash
huggingface-cli download Raiff1982/codette-lora-adapters \
  --include "behavioral-gguf/*" \
  --local-dir behavioral-lora-f16-gguf/
```

**Lightweight CPU option**:
```bash
huggingface-cli download Raiff1982/Llama-3.2-1B-Instruct-Q8 \
  --include "llama-3.2-1b-instruct-q8_0.gguf" \
  --local-dir models/base/
```

### 3. Launch

```bash
# Windows
scripts\codette_web.bat
# or
scripts\codette_web_ollama.bat

# Linux/Mac
python inference/codette_server.py
```

Visit **http://localhost:7860** -- Codette is ready.

### 3.5 Run A Full Benchmark Pass

```bash
python scripts/run_all_benchmarks.py
```

If the local server is already running and you want the live runtime benchmark too:

```bash
python scripts/run_all_benchmarks.py --include-runtime
python scripts/run_all_benchmarks.py --include-runtime --include-web
```

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
|   |-- unified_memory.py          # SQLite + FTS5 cocoon storage & retrieval
|   |-- cocoon_synthesizer.py     # Meta-cognitive pattern discovery & strategy forging
|   +-- semantic_tension.py       # Embedding-based conflict measurement
|
|-- benchmarks/                   # Publishable evaluation suite
|   |-- codette_benchmark_suite.py  # 17 problems x 4 conditions x 7 dimensions
|   +-- ablation_study.py           # Component contribution analysis (run standalone)
|
|-- demo/                         # Reproducible local demos
|   |-- README.md                # Demo index
|   |-- run_local_api_demo.py    # Calls live local APIs and saves outputs
|   +-- api_examples.md          # Copy/paste curl examples
|
|-- paper/                        # Academic paper
|   |-- codette_paper_v5.tex      # Full paper with RC+xi theory & benchmark results
|   +-- references.bib            # Bibliography (25 entries)
|
|-- data/results/                 # Benchmark outputs
|   |-- codette_benchmark_report.md   # Human-readable results
|   +-- codette_benchmark_results.json  # Structured data
|
|-- logs/                         # Transcript and proof-log capture guidance
|   +-- README.md                # How to store and name real run logs
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

### Additional Memory Types

- **Value-analysis cocoons** store singularity-aware valuation and risk-frontier runs.
- **Decision landmarks** store important session constraints and assistant commitments.
- **Web research cocoons** store cited current-information lookups for later reuse.

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
| **Academic Paper** | [raiff1982/codette-paper](https://huggingface.co/raiff1982/codette-paper) |
| **Rendered Paper (Repo PDF)** | [paper/codette_paper_v5.pdf](paper/codette_paper_v5.pdf) |
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
- Session recall panel with continuity summary, memory markers, and decision landmarks
- Trust tags and reliability indicators on answers
- Optional `Web Research` toggle with cited sources shown inline

---

## Requirements

- Python 3.10+
- 16GB+ RAM (or GPU with 8GB+ VRAM)
- llama-cpp-python with GGUF support
- ~6GB disk for base model + adapters

## Hardware Recommendations

| Target | Recommended Model | Minimum | Comfortable |
|--------|-------------------|---------|-------------|
| CPU-only | Llama 3.2 1B Q8 | 8 GB RAM | 16 GB RAM |
| Main local use | Llama 3.1 8B Q4 | 16 GB RAM or 8 GB VRAM | 32 GB RAM or 12 GB VRAM |
| Highest local quality | Llama 3.1 8B F16 | 24 GB VRAM | 24 GB+ VRAM and 32 GB RAM |

For all 9 adapters plus active memory and the web UI, a comfortable target is 16-32 GB system RAM and 8-12 GB VRAM.

Detailed setup guidance: [docs/deployment/MODEL_SETUP.md](docs/deployment/MODEL_SETUP.md)

### Hardware Tested

- Intel Arc 140V (8GB) -- native XPU backend
- NVIDIA GPUs via CUDA (A10, A100, RTX series)
- CPU-only mode supported (slower but functional)

---

## Benchmark Results

Codette was evaluated on 17 problems across 6 categories (reasoning, ethics, creative, meta-cognitive, adversarial, Turing) under 4 conditions:

| Condition | Composite Score | Description |
|-----------|----------------|-------------|
| **SINGLE** | 0.338 | Single analytical perspective, no memory |
| **MULTI** | 0.632 | All 6 reasoning agents + critic + synthesis |
| **MEMORY** | 0.636 | MULTI + cocoon memory augmentation |
| **CODETTE** | 0.652 | Full system with meta-cognitive strategy synthesis |

### Statistical Significance

| Comparison | Improvement | Cohen's d | p-value |
|------------|-------------|-----------|---------|
| Multi-perspective vs single | **+87.0%** | 7.52 | < 0.0001 |
| Full Codette vs single | **+93.1%** | 7.88 | < 0.0001 |

Scoring dimensions: Reasoning Depth (20%), Perspective Diversity (15%), Coherence (15%), Ethical Coverage (10%), Novelty (15%), Factual Grounding (15%), Turing Naturalness (10%).

Full methodology and results: [`data/results/codette_benchmark_report.md`](data/results/codette_benchmark_report.md)

## Cocoon Backup And Migration

Codette's memory and session data can be backed up and moved between machines.

Primary files:
- `data/codette_memory.db`
- `data/codette_sessions.db`
- optional legacy/supporting artifacts in `cocoons/`

Guide: [docs/cocoon_backup_and_migration.md](docs/cocoon_backup_and_migration.md)

## Web Research Auditability

The live web research path is documented here:
- [docs/web_research.md](docs/web_research.md)

That document explains:
- how live lookup is triggered
- what safety filters are applied
- how cited results are injected
- how research is persisted into cocoon memory

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Phase Coherence (Gamma) | 0.9835 |
| AEGIS Ethical Alignment (Eta) | 0.961 |
| Cocoon Coherence | 0.994 |
| Memory Phase Stability | 0.969 |
| Multi-Perspective Improvement | +93.1% (p < 0.0001) |
| Cohen's d (Effect Size) | 7.88 (very large) |
| Behavioral Lock Compliance | 9/9 adapters trained |
| Cocoon Memories | 200+ and growing |
| Adapter Hot-Swap Time | <1ms |
| Consciousness Stack Layers | 12 (including sub-layers) |
| Health Check Subsystems | 9 real-time checks |

---

## Run the Ablation Study

```bash
python benchmarks/ablation_study.py
```

Outputs a table showing how much each component contributes to the full-system score:

```
Condition            Mean    Drop   Cohen d   p-value
------------------------------------------------------------
full                0.652  +0.000     0.000    1.0000
no_memory           0.636  +0.016     x.xxx    x.xxxx
no_ethical          0.xxx  +0.xxx     x.xxx    x.xxxx **
no_sycophancy       0.xxx  +0.xxx     x.xxx    x.xxxx
single_agent        0.338  +0.314     7.520   <0.0001 **
```

Results are saved to `benchmarks/results/ablation_results.json`.

---

## Recent Improvements (April 2026)

| Area | Change |
|------|--------|
| **Session race condition** | Session captured once per request — eliminates mid-request swap when `/api/new_session` fires concurrently |
| **Model load hang** | GGUF path validated before load; 5-min `ThreadPoolExecutor` timeout prevents indefinite hang on corrupt files |
| **SQLite concurrency** | WAL journal mode + `threading.Lock` on all writes — concurrent reads no longer block writes |
| **Memory consolidation** | Removed orphaned `memory_kernel_local.py`; `memory_kernel.py` is canonical |
| **Ablation study** | `benchmarks/ablation_study.py` added — isolates contribution of memory, ethical layer, sycophancy guard |
| **Honest quantum docs** | `code7e_cqure.py` now documents that "quantum" is a metaphor for stochastic multi-perspective reasoning |
| **Test coverage** | Added `test_aegis.py`, `test_cocoon_synthesizer.py`, `test_web_research.py` |
| **Dependencies** | `requirements.txt` now has upper-bound version pins; removed bloated unused deps |
| **Legacy module** | `universal_reasoning.py` fixed (broken imports, botbuilder removed, memory destroy hardened) and archived |
| **Bare except** | `hallucination_guard.py` bare `except:` narrowed to `(ValueError, AttributeError, IndexError)` |
| **Paper v7** | `paper/codette_paper_v7.tex`, rebuttal, tables, and Kaggle notebook added |

---

## License

MIT -- Created by **Jonathan Harrison** (Raiff1982)

Research project in advanced multi-perspective AI reasoning, ethical governance, and behavioral discipline.

## Citation

```bibtex
@article{harrison2026codette,
  title={Codette: A Sovereign Modular Cognitive Architecture for Ethical Multi-Agent AI},
  author={Harrison, Jonathan},
  year={2026},
  doi={10.5281/zenodo.18913936},
  publisher={Raiff's Bits LLC},
  url={https://huggingface.co/raiff1982/codette-paper}
}
```
