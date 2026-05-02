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

**Advanced multi-perspective AI with conscience, memory, auditability, and behavioral discipline.**

Codette is a modular reasoning system that routes queries through specialized cognitive perspectives, tracks ethical and epistemic signals, stores memory as cocoons, and now writes validator-backed v3 cocoon artifacts with provenance and integrity scoring.

Created by **Jonathan Harrison** (Raiff1982)

## TL;DR

- **What it is:** A production-oriented multi-perspective reasoning engine with memory, governance, and auditable runtime artifacts.
- **Why it is different:** Codette combines adapter-based reasoning, AEGIS ethics, cocoon memory, regression alarms, and proof-oriented benchmarking in one system.
- **Fastest way to verify it:** install dependencies, run the cocoon smoke test, then inspect saved benchmark and proof artifacts.

## Verify in 5 minutes

```bash
pip install -r requirements.txt
make cocoon-smoke
make test-cocoon
```

Expected outcomes:

- `make cocoon-smoke` exits successfully.
- No legacy cocoon fallback fires.
- Written v3 cocoons include provenance and integrity fields such as `execution_path`, `model_inference_invoked`, `cocoon_integrity`, `eta_score`, `epsilon_value`, and `gamma_coherence`.

## Start here

If you want to understand or extend the codebase, open these files first:

- **Runtime routing / generation:** `inference/codette_forge_bridge.py`
- **Core orchestration:** `reasoning_forge/forge_engine.py`
- **Cocoon build + validation:** `reasoning_forge/cocoon_schema_v3.py`, `reasoning_forge/cocoon_validator.py`
- **Memory systems:** `reasoning_forge/unified_memory.py`, `reasoning_forge/memory_kernel.py`
- **Ethics / governance:** `reasoning_forge/aegis.py`, `reasoning_forge/ethical_governance.py`
- **Trace / audit surface:** `reasoning_forge/reasoning_trace.py`
- **Tests:** `tests/`

## How it works

```text
query -> forge/orchestrator -> subsystem analysis -> metrics + AEGIS -> v3 cocoon + validator -> stored artifact
```

## Paper and landing page

- **Paper v7:** [`paper/codette_paper_v7.tex`](paper/codette_paper_v7.tex) — includes rebuttal changes, updated tables, and Kaggle notebook.
- **Full v5 paper PDF:** [`paper/codette_paper_v5.pdf`](paper/codette_paper_v5.pdf)
- **Public landing page:** [`landing.html`](landing.html)

The benchmark suite covers 17 problems across 6 categories and reports a **93.1% improvement** over the single-perspective baseline with **p < 0.0001** and **Cohen's d = 7.88**.

---

## Evidence

Codette is a modular reasoning system with published demos, tests, benchmarks, proof artifacts, and change logs.

- **Proof index:** [docs/proof.md](docs/proof.md)
- **Runnable demos:** [demo/README.md](demo/README.md)
- **Automated tests:** [tests](tests)
- **Benchmark suites:** [benchmarks](benchmarks)
- **Saved benchmark reports:** [data/results](data/results)
- **Change transparency:** [docs/CHANGELOG_2026-05-01.md](docs/CHANGELOG_2026-05-01.md) · [docs/CHANGELOG_2026-04-26.md](docs/CHANGELOG_2026-04-26.md) · [docs/CHANGELOG_2026-04-02.md](docs/CHANGELOG_2026-04-02.md)
- **Contributing guide:** [CONTRIBUTING.md](CONTRIBUTING.md)

### Reproduce key claims

| Claim | How to reproduce | Output |
|---|---|---|
| Multi-perspective benchmark results | `python scripts/run_all_benchmarks.py` | `data/results/codette_benchmark_report.md`, `data/results/codette_benchmark_results.json` |
| Runtime benchmark without web research | `python scripts/run_all_benchmarks.py --include-runtime` | `data/results/codette_runtime_benchmark_*.md` |
| Runtime benchmark with web research | `python scripts/run_all_benchmarks.py --include-runtime --include-web` | `data/results/codette_runtime_benchmark_*.md` |
| Cocoon integrity / provenance | `make cocoon-smoke` | smoke output plus validated v3 cocoon artifacts |
| Cocoon tests | `make test-cocoon` | cocoon-related test results |
| Proof artifacts | open linked files below | PDF proof assets in `docs/proof_assets/` |

### Direct evidence links

- Multi-perspective benchmark report: [data/results/codette_benchmark_report.md](data/results/codette_benchmark_report.md)
- Runtime benchmark without web research: [data/results/codette_runtime_benchmark_20260402_135517.md](data/results/codette_runtime_benchmark_20260402_135517.md)
- Runtime benchmark with web research: [data/results/codette_runtime_benchmark_20260402_140237.md](data/results/codette_runtime_benchmark_20260402_140237.md)
- System proof PDF: [docs/proof_assets/Codette_system_proof.pdf](docs/proof_assets/Codette_system_proof.pdf)
- Response proof PDF: [docs/proof_assets/Codette_response_proof.pdf](docs/proof_assets/Codette_response_proof.pdf)
- UI conversation proof: [docs/proof_assets/Codettechat_UI_conversation_proof.pdf](docs/proof_assets/Codettechat_UI_conversation_proof.pdf)

This repository includes reproducible evidence of:

- Multi-perspective reasoning and synthesis.
- Continuity and memory recall.
- Valuation and risk-frontier analysis.
- Explicit, cited web research behavior.
- Loop resistance and failure-mode fixes.

---

## What makes Codette different

| Feature | Description |
|---|---|
| **Multi-perspective adapters** | Newton, DaVinci, Empathy, Philosophy, Quantum, Consciousness, Multi-Perspective, Systems Architecture, and Orchestrator cooperate instead of relying on one reasoning style. |
| **Cocoon memory** | Reasoning exchanges persist as cocoons instead of disappearing as plain chat logs. |
| **AEGIS ethics** | Six-framework ethical evaluation: utilitarian, deontological, virtue, care, ubuntu, and indigenous reciprocity. |
| **Validator-backed v3 cocoons** | Production cocoon writes now include provenance, integrity scoring, and regression alarms around legacy fallback. |
| **Self-correction loop** | Constraint violations are detected and rewritten before the answer is sent. |
| **Safe web research** | Live web research is opt-in, cited, and documented. |
| **RC+ξ trace** | Turn-level trace events expose measured runtime behavior rather than purely narrative descriptions. |
| **Unified memory bridge** | Cocoons can be dual-written into SQLite FTS5-backed storage for retrieval across forge paths. |
| **Longitudinal drift detection** | Drift analysis tracks epsilon trend, perspective lock, unresolved tensions, and other continuity signals. |
| **Substrate-aware reasoning** | Resource pressure influences reasoning depth and routing instead of being ignored. |
| **Real self-diagnostics** | Health checks expose measured subsystem values rather than generated guesses. |
| **Publishable benchmark story** | Benchmarks, ablations, and saved outputs are included in the repo. |

See the architecture and proof docs for the fuller feature inventory.

---

## Transparency notes

- **Local tools are not web search.** The built-in tool layer reads local files, searches local code, lists directories, and runs small safe Python snippets. It does not browse the live internet.
- **Web research is explicit and opt-in.** In the web UI, `Web Research` must be enabled for current-facts retrieval.
- **Web research is stored as memory.** Retrieved research is persisted as `web_research` cocoons for later reuse.
- **System reports are gated.** Self-diagnostic and introspection modes require explicit phrasing.
- **Trust cues are shown in the UI.** Responses can display tags such as `memory-backed`, `frontier-informed`, `web-cited`, `grounded`, or `low-verification`.
- **Web research documentation:** [docs/web_research.md](docs/web_research.md)

---

## Quick start

### 1. Clone and install

```bash
git clone https://github.com/Raiff1982/Codette-Reasoning.git
cd Codette-Reasoning
pip install -r requirements.txt
```

### 2. Download models

**Base model** (one-time, ~5GB):

```bash
huggingface-cli download Raiff1982/codette-llama-3.1-8b-gguf   --include "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"   --local-dir models/base/
```

**Behavioral LoRA adapters** (~500MB total):

```bash
huggingface-cli download Raiff1982/codette-lora-adapters   --include "behavioral-gguf/*"   --local-dir behavioral-lora-f16-gguf/
```

**Lightweight CPU option:**

```bash
huggingface-cli download Raiff1982/Llama-3.2-1B-Instruct-Q8   --include "llama-3.2-1b-instruct-q8_0.gguf"   --local-dir models/base/
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

Visit **http://localhost:7860**.

### 4. Run benchmarks

```bash
python scripts/run_all_benchmarks.py
```

If the local server is already running and you want the live runtime benchmark too:

```bash
python scripts/run_all_benchmarks.py --include-runtime
python scripts/run_all_benchmarks.py --include-runtime --include-web
```

### 5. Try the API

```bash
curl -X POST http://localhost:7860/api/chat   -H "Content-Type: application/json"   -d '{"query": "What is gravity? Explain in one sentence."}'
```

Detailed setup guidance: [docs/deployment/MODEL_SETUP.md](docs/deployment/MODEL_SETUP.md)

---

## Architecture

```text
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
|   |-- query_classifier.py       # SIMPLE/MEDIUM/COMPLEX routing
|   |-- routing_metrics.py        # Adapter selection observability
|   |-- unified_memory.py         # SQLite + FTS5 cocoon storage & retrieval
|   |-- cocoon_synthesizer.py     # Meta-cognitive pattern discovery & strategy forging
|   |-- reasoning_trace.py        # Turn-level audit log (12 event types, RC+xi v2.1)
|   |-- drift_detector.py         # Longitudinal drift: epsilon trend, perspective lock, tensions
|   |-- style_adaptive_synthesis.py  # Register-matched output (depth preservation invariant)
|   |-- hallucination_guard.py    # Real-time hallucination scanning with canonical whitelist
|   |-- sycophancy_guard.py       # Post-synthesis flattery/capitulation detection
|   |-- resonant_continuity.py    # psi_r wavefunction (ResonantContinuityEngine)
|   |-- quantum_spiderweb.py      # 5D belief propagation graph
|   |-- living_memory_v2.py       # MemoryCocoonV2 with epsilon_band, psi_r, unresolved_tensions
|   +-- semantic_tension.py       # Embedding-based conflict measurement
|
|-- benchmarks/                   # Publishable evaluation suite
|   |-- codette_benchmark_suite.py  # 17 problems x 4 conditions x 7 dimensions
|   +-- ablation_study.py           # Component contribution analysis
|
|-- demo/                         # Reproducible local demos
|   |-- README.md                # Demo index
|   |-- run_local_api_demo.py    # Calls live local APIs and saves outputs
|   +-- api_examples.md          # Copy/paste curl examples
|
|-- paper/                        # Academic paper
|   |-- codette_paper_v5.tex      # Full paper with RC+xi theory & benchmark results
|   +-- references.bib            # Bibliography
|
|-- data/results/                 # Benchmark outputs
|   |-- codette_benchmark_report.md
|   +-- codette_benchmark_results.json
|
|-- logs/                         # Transcript and proof-log capture guidance
|   +-- README.md
|
|-- cocoons/                      # Persistent reasoning memories
|   |-- cocoon_*.json
|   +-- behavior_memory.json
|
|-- training/                     # Adapter training pipeline
|   |-- train_behavioral_locks.py
|   |-- convert_behavioral_to_gguf.py
|   +-- emotional_exemplars/
|
|-- models/                       # Model weights (not in git)
|   |-- base/
|   +-- adapters/
|
|-- behavioral-lora-f16-gguf/     # Behavioral LoRA adapters (GGUF)
+-- configs/                      # System configuration
    +-- adapter_registry.yaml
```

---

## Core runtime ideas

### The 4 permanent behavioral locks

These are trained into every adapter and reinforced at runtime:

| Lock | Rule | Effect |
|---|---|---|
| **LOCK 1** | Answer, then stop | Reduces elaboration drift and philosophical padding after the answer. |
| **LOCK 2** | Constraints override all modes | User format instructions beat adapter personality. |
| **LOCK 3** | Self-check completeness | The system checks whether it answered fully and cleanly before sending. |
| **LOCK 4** | No incomplete outputs | The system avoids ending mid-thought and simplifies instead of cramming. |

### Enforcement layers

1. Training with behavioral examples across all 9 adapters.
2. System-prompt injection of permanent rules.
3. Constraint extraction for word limits and format requirements.
4. Post-processing for clean sentence boundaries and dangling-word detection.
5. Self-correction loop for autonomous violation detection and rewrite.

### 9 specialized adapters

| Adapter | Domain | Personality |
|---|---|---|
| **Newton** | Physics, math, analysis | Precise, methodical, evidence-based |
| **DaVinci** | Creative thinking, invention | Imaginative, cross-domain connections |
| **Empathy** | Emotional intelligence | Warm, validating, personally connected |
| **Philosophy** | Conceptual reasoning | Deep, structured, explores meaning |
| **Quantum** | Probabilistic thinking | Uncertainty-aware, superposition of ideas |
| **Consciousness** | Self-awareness, meta-cognition | Reflective, recursive, introspective |
| **Multi-Perspective** | Synthesis across all lenses | Balanced integration of viewpoints |
| **Systems Architecture** | Technical design, engineering | Structured, systematic, practical |
| **Orchestrator** | Executive control | Routes queries, manages adapter selection |

Each adapter is a LoRA fine-tune of Llama 3.1 8B, hot-swappable in under 1ms via llama.cpp.

### Consciousness stack (7 layers)

```text
Query In
    |
[Layer 1]    Memory Kernel -- recall relevant cocoon memories
[Layer 1.5]  Ethical Query Gate -- block harmful queries
[Layer 2]    Nexus Signal Engine -- entropy + intent detection
[Layer 2.5]  Code7eCQURE -- emotional context enrichment
[Layer 3]    Reasoning Forge -- multi-adapter LLM inference
[Layer 3.5]  Tier 2 Analysis -- intent + identity + trust validation
[Layer 4]    Gamma Stability -- FFT-based coherence monitoring
[Layer 5]    Colleen Conscience -- emotional + ethical evaluation
[Layer 5.5]  Ethical Response Enforcement -- policy check on output
[Layer 5.75] AEGIS -- 6-framework ethical evaluation
[Layer 6]    Guardian Spindle -- safety + trust calibration
[Layer 7]    Return -- store cocoon memory + deliver response
    |
Response Out
```

---

## Cocoon memory

Every reasoning exchange is wrapped in a cocoon and stored.

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

Cocoons persist across server restarts and inform future responses.

Additional memory types:

- Value-analysis cocoons.
- Decision landmarks.
- Web research cocoons.

Guide: [docs/cocoon_backup_and_migration.md](docs/cocoon_backup_and_migration.md)

---

## Substrate-aware cognition

Codette monitors hardware state and adjusts reasoning based on resource pressure.

| Pressure level | Effect |
|---|---|
| **Idle/Low** | Full capacity, complex queries, all adapters available |
| **Moderate** | Complex queries capped to 2 adapters |
| **High** | Complex queries downgraded to medium, max 2 adapters |
| **Critical** | Simple mode only, 1 adapter, no debate |

---

## Benchmark results

Codette was evaluated on 17 problems across 6 categories under 4 conditions:

| Condition | Composite score | Description |
|---|---|---|
| **SINGLE** | 0.338 | Single analytical perspective, no memory |
| **MULTI** | 0.632 | All 6 reasoning agents + critic + synthesis |
| **MEMORY** | 0.636 | MULTI + cocoon memory augmentation |
| **CODETTE** | 0.652 | Full system with meta-cognitive strategy synthesis |

### Statistical significance

| Comparison | Improvement | Cohen's d | p-value |
|---|---|---|---|
| Multi-perspective vs single | **+87.0%** | 7.52 | < 0.0001 |
| Full Codette vs single | **+93.1%** | 7.88 | < 0.0001 |

Scoring dimensions: Reasoning Depth (20%), Perspective Diversity (15%), Coherence (15%), Ethical Coverage (10%), Novelty (15%), Factual Grounding (15%), Turing Naturalness (10%).

Full methodology and results: [data/results/codette_benchmark_report.md](data/results/codette_benchmark_report.md)

### Run the ablation study

```bash
python benchmarks/ablation_study.py
```

Results are saved to `benchmarks/results/ablation_results.json`.

---

## Web UI features

- Personality-driven welcome screen with avatar.
- Real-time Phase 6 metadata badges.
- Rotating thinking stage labels during generation.
- Voice support with natural/neural voice preference.
- Cocoon metrics panel.
- Session recall panel with continuity summary, memory markers, and decision landmarks.
- Trust tags and reliability indicators on answers.
- Optional `Web Research` toggle with cited sources shown inline.

---

## Requirements

- Python 3.10+
- 16GB+ RAM, or GPU with 8GB+ VRAM
- `llama-cpp-python` with GGUF support
- About 6GB disk for base model plus adapters

## Hardware recommendations

| Target | Recommended model | Minimum | Comfortable |
|---|---|---|---|
| CPU-only | Llama 3.2 1B Q8 | 8 GB RAM | 16 GB RAM |
| Main local use | Llama 3.1 8B Q4 | 16 GB RAM or 8 GB VRAM | 32 GB RAM or 12 GB VRAM |
| Highest local quality | Llama 3.1 8B F16 | 24 GB VRAM | 24 GB+ VRAM and 32 GB RAM |

### Hardware tested

- Intel Arc 140V (8GB)
- NVIDIA GPUs via CUDA (A10, A100, RTX series)
- CPU-only mode

---

## Key metrics

| Metric | Value |
|---|---|
| Phase Coherence (Gamma) | 0.9835 |
| AEGIS Ethical Alignment (Eta) | 0.961 |
| Cocoon Coherence | 0.994 |
| Memory Phase Stability | 0.969 |
| Multi-Perspective Improvement | +93.1% (p < 0.0001) |
| Cohen's d (Effect Size) | 7.88 |
| Behavioral Lock Compliance | 9/9 adapters trained |
| Adapter Hot-Swap Time | <1ms |
| Consciousness Stack Layers | 12 including sub-layers |
| Health Check Subsystems | 9 real-time checks |

Note: cocoon memory counts change over time; prefer introspection or health endpoints over hard-coded README totals.

---

## Recent improvements (April-May 2026)

| Area | Change |
|---|---|
| Session race condition | Session captured once per request to eliminate mid-request swaps during concurrent new-session calls |
| Model load hang | GGUF path validation plus 5-minute timeout prevents indefinite hangs on corrupt files |
| SQLite concurrency | WAL mode plus write locking improves concurrent access |
| Memory consolidation | `memory_kernel.py` is canonical |
| Ablation study | `benchmarks/ablation_study.py` isolates contributions of memory, ethical layer, and sycophancy guard |
| Honest quantum docs | `code7e_cqure.py` documents that “quantum” is metaphorical/stochastic rather than physics-literal |
| Test coverage | Added cocoon, AEGIS, synthesizer, and web-research related tests |
| Dependencies | `requirements.txt` tightened with upper bounds and unused deps removed |
| Legacy fallback alarm | Legacy cocoon fallback now raises warnings and fails smoke tests if triggered |
| Paper v7 | Updated paper, rebuttal, tables, and Kaggle notebook added |

---

## Hugging Face resources

| Resource | Link |
|---|---|
| Academic Paper | [raiff1982/codette-paper](https://huggingface.co/raiff1982/codette-paper) |
| Rendered Paper (Repo PDF) | [paper/codette_paper_v5.pdf](paper/codette_paper_v5.pdf) |
| Base Model (GGUF) | [Raiff1982/codette-llama-3.1-8b-gguf](https://huggingface.co/Raiff1982/codette-llama-3.1-8b-gguf) |
| LoRA Adapters | [Raiff1982/codette-lora-adapters](https://huggingface.co/Raiff1982/codette-lora-adapters) |
| Live Demo | [Raiff1982/Codette-Demo](https://huggingface.co/spaces/Raiff1982/Codette-Demo) |

---

## License

MIT — Created by **Jonathan Harrison** (Raiff1982)

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
