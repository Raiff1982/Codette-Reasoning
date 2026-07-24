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
      value: "+108.8%"
    - name: Benchmark Coherence
      type: custom
      value: 0.700
    - name: Benchmark Turing Naturalness
      type: custom
      value: 0.820
    - name: Benchmark p-value
      type: custom
      value: "<0.0001"
    - name: Cohen's d (Effect Size)
      type: custom
      value: 8.31
---

# Codette Reasoning Engine

**Advanced multi-perspective AI with conscience, memory, auditability, and behavioral discipline.**

Codette is a modular reasoning system that routes queries through specialized cognitive perspectives, tracks ethical and epistemic signals, stores memory as cocoons, and writes validator-backed v3 cocoon artifacts with full provenance and integrity scoring.

**Current release — v3.6 (July 2026): TimeTravelLens + AEGIS Protection Layers + UI Observatory.** Codette now auto-detects institutional temporal gaps in any query — computing preemption gap Π(s), closure score C(s), rupture indicator ℛ(s), beacon ℬ(s), and high-preemption zone Z^H via `reasoning_forge/time_travel_lens.py`. An `InstitutionalExtractor` derives these metrics from unstructured text (regex date extraction + keyword event classification). New AEGIS Protection Layers (all six implemented — Layer 4 uses real ML-KEM-768 + ML-DSA-65 post-quantum cryptography via liboqs, NIST FIPS 203/204) wrap every ForgeEngine cycle with filesystem isolation, boot integrity, PQC cocoon sealing, pre-emptive healing from real cocoon fields, and RenderLayer validation. A SQLite-backed metrics engine logs every forge cycle. New UI: `⏱ TimeLens` dashboard with live Π/C/ℛ/ℬ/Z^H display, per-actor gap breakdown, and on-demand text analysis. Details: [docs/CHANGELOG_2026-07-21.md](docs/CHANGELOG_2026-07-21.md).

**Previous release — v3.5 (July 2026): Hand-Authored v4 Adapters + Phase 0 Audit + Verify-and-Revise + Integrity Stress Test.** Details: [docs/CHANGELOG_2026-07-17.md](docs/CHANGELOG_2026-07-17.md).

**Full release notes for every version (v2.1 → v3.6): [docs/VERSION_HISTORY.md](docs/VERSION_HISTORY.md)**

> **Attribution & naming (July 2026).** Earlier releases (v3.0–v3.5, and much of this README) use the term **RC+ξ** and the symbol **ξ ("epistemic tension")**. That name and its formalism, **ξ = ‖Aₙ₊₁ − Aₙ‖²**, originate with Jeffrey Camlin, *"Consciousness in AI: Logic, Proof, and Experimental Evidence of Recursive Identity Formation"* ([arXiv:2505.01464](https://arxiv.org/abs/2505.01464), May 1, 2025), and are credited to him. This project adopted that vocabulary in 2025–2026, most likely by way of language models carrying his paper in their training data without a citation. Camlin's ξ measures how much **one model's hidden state changes between successive recursive steps**. The quantity this system actually computes is a **different** one — the variance of *multiple simultaneous perspective outputs around their centroid* (many perspectives disagreeing at once, not one trajectory changing over time) — now renamed **Perspective Dispersion (Υ)**, with coherence Γ = 1/(1+Υ). This project's multi-perspective architecture was developed independently and published *before* that paper (perspective engine Nov–Dec 2024; sovereign architecture [Zenodo DOI 10.5281/zenodo.15214462](https://doi.org/10.5281/zenodo.15214462), April 14, 2025), so the two are **convergent, not derivative**. We didn't take his work, and we don't claim his name or formula — both are true, and we keep both visible rather than erasing the older "RC+ξ" labels. Full detail: [docs/ATTRIBUTION_perspective_dispersion.md](docs/ATTRIBUTION_perspective_dispersion.md).

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

The benchmark suite covers 17 problems across 6 categories and reports a **108.8% improvement** over the single-perspective baseline with **p < 0.0001** and **Cohen's d = 8.31**.

---

## Evidence

Codette is a modular reasoning system with published demos, tests, benchmarks, proof artifacts, and change logs.

- **Proof index:** [docs/proof.md](docs/proof.md)
- **Runnable demos:** [demo/README.md](demo/README.md)
- **Automated tests:** [tests](tests)
- **Benchmark suites:** [benchmarks](benchmarks)
- **Saved benchmark reports:** [data/results](data/results)
- **Change transparency:** latest — [docs/CHANGELOG_2026-07-17.md](docs/CHANGELOG_2026-07-17.md) · [docs/CHANGELOG_2026-07-16.md](docs/CHANGELOG_2026-07-16.md) · [docs/CHANGELOG_2026-07-12.md](docs/CHANGELOG_2026-07-12.md); every release summarized in [docs/VERSION_HISTORY.md](docs/VERSION_HISTORY.md); all dated changelogs in [docs/](docs/)
- **Contributing guide:** [CONTRIBUTING.md](CONTRIBUTING.md)

### Reproduce key claims

| Claim | How to reproduce | Output |
|---|---|---|
| Multi-perspective benchmark results | `python scripts/run_all_benchmarks.py` | `data/results/codette_benchmark_report.md`, `data/results/codette_benchmark_results.json` |
| Runtime benchmark without web research | `python scripts/run_all_benchmarks.py --include-runtime` | `data/results/codette_runtime_benchmark_*.md` |
| Runtime benchmark with web research | `python scripts/run_all_benchmarks.py --include-runtime --include-web` | `data/results/codette_runtime_benchmark_*.md` |
| Cocoon integrity / provenance | `make cocoon-smoke` | smoke output plus validated v3 cocoon artifacts |
| Cocoon tests | `make test-cocoon` | cocoon-related test results |
| GPQA reason-mode score | `python benchmarks/gpqa_codette.py --mode reason --dataset gpqa_main.csv --adapter newton --limit 100` (server running) | `data/results/gpqa_codette_reason_*.json` |
| Proof artifacts | open linked files below | PDF proof assets in `docs/proof_assets/` |
| Phase 0 adapter arms (base vs newton-v4, paired) | run `benchmarks/phase0_kaggle.py` on a GPU (Kaggle T4) | `phase0_{base,newton}_results.json`; saved copies in `data/results/` |
| Phase 0 layer ablation (incl. lobotomy arm) | `python benchmarks/phase0_ablation.py --arms layers --dataset gpqa_main.csv --limit 50` | `data/results/phase0/summary.json` + per-arm logs |
| Verify-and-Revise vs single-pass (paired) | `python benchmarks/gpqa_verify_revise.py --dataset gpqa_main.csv --limit 30` (server running) | `data/results/verify_revise/vr_*.json` |
| Bully-critic integrity stress test | same + `--adversarial` | hold-ground rate + per-question traces in `data/results/verify_revise/` |
| McNemar paired significance for any two runs | `python benchmarks/paired_analysis.py <a.json> <b.json>` | exact p, discordant counts, letter-bias table |

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
# Windows (auto-detects OpenVINO backend if converted model exists,
# sweeps stale instances, falls back to llama.cpp GGUF otherwise)
scripts\codette_web.bat
# or restart cleanly with health verification:
python scripts/reboot_codette.py

# Linux/Mac
python inference/codette_server.py
```

Visit **http://localhost:7860**.

**Optional — Intel GPU acceleration via OpenVINO** (measured 9.3 tok/s sustained on Arc 140V iGPU):

```bash
# One-time conversion (needs optimum-intel in a dedicated env)
optimum-cli export openvino -m meta-llama/Llama-3.1-8B-Instruct \
  --weight-format int4 --group-size 128 \
  openvino_backend/llama-3.1-8b-instruct-int4
python openvino_backend/convert_adapters.py   # GGUF LoRAs -> safetensors
```

The server auto-detects the converted model on next start — no configuration needed. First GPU load takes ~2 min (kernel compile); cached loads ~20s.

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
|-- openvino_backend/             # OpenVINO GenAI backend (v3.0)
|   |-- backend.py                # Drop-in orchestrator: INT4 on Intel GPU, adapter
|   |                             #   hot-swap + blended multi-adapter generation
|   |-- convert_adapters.py       # GGUF LoRA -> safetensors conversion
|   +-- llama-3.1-8b-instruct-int4/  # Converted model (not in git)
|
|-- inference/                    # Server & UI
|   |-- codette_server.py         # Stdlib HTTP server with SSE streaming
|   |-- codette_orchestrator.py   # LoRA hot-swap engine (10 adapters, <1ms switch)
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

This is Codette's own seven-dimension composite rubric — a *self-defined* score, distinct from the external GPQA-main benchmark reported above. It measures relative lift across conditions of the same system, not standing against other models.

Codette was evaluated on 17 problems across 6 categories under 4 conditions (report generated 2026-05-26, N=17 per condition):

| Condition | Composite score | Description |
|---|---|---|
| **SINGLE** | 0.357 | Single analytical perspective, no memory |
| **MULTI** | 0.708 | All 6 reasoning agents + critic + synthesis |
| **MEMORY** | 0.739 | MULTI + cocoon memory augmentation |
| **CODETTE** | 0.744 | Full system with meta-cognitive strategy synthesis |

### Statistical significance

| Comparison | Improvement | Cohen's d | p-value |
|---|---|---|---|
| Multi-perspective vs single | **+98.4%** | 7.45 | < 0.0001 |
| Full Codette vs single | **+108.8%** | 8.31 | < 0.0001 |

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

- Intel Arc 140V (8GB UMA) — via OpenVINO GenAI INT4 (9.3 tok/s sustained) and llama.cpp Vulkan
- NVIDIA GPUs via CUDA (A10, A100, RTX series)
- CPU-only mode

Note for 8GB-UMA systems: the GPU shares system RAM. Keep ≥5GB free when loading (the 4.5GB INT4 model + kernel compile overhead); concurrent loads or heavy co-running apps cause silent load failures.

---

## Key metrics

| Metric | Value |
|---|---|
| GPQA-main 0-shot (reason mode, n=100) | 34.0% — vs 25.0% random, 39% GPT-4 |
| Baseline reproducibility | 34.0% twice, 4 days apart, across a backend swap |
| STaR study (three arms, controlled) | easy 25.0% < hard 28.0% < untrained 34.0% — negative result, published |
| Live cognition signals per response | ξ, Γ, σ, η, render fidelity, hardware P — measured-only, provenance-tagged |
| Sustained throughput (OpenVINO INT4, Arc 140V iGPU) | 9.3 tok/s |
| Phase Coherence (Gamma) | 0.9835 |
| AEGIS Ethical Alignment (Eta) | 0.961 |
| Cocoon Coherence | 0.994 |
| Memory Phase Stability | 0.969 |
| Multi-Perspective Improvement | +108.8% (p < 0.0001) |
| Cohen's d (Effect Size) | 8.31 |
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
| Full adapter roster | Orchestrator + constraint_tracker now load as behavioral adapters (10 total) |
| Full Adapter Synthesis | ◈ SYNTHESIZE ALL runs every perspective and synthesizes into one answer |
| Self-overclaiming guard | Signal 7 flags grandiose self-claims + fabricated self-metrics; reliability scan now covers every displayed perspective |
| Contradiction-check crash | `_check_contradictions` `\1` backreference fixed (was silently disabled on "always X" responses) |
| Constraint negation parser | Ordinary negations ("no word constraint", "no constraints needed") no longer captured as enforced constraints (fixed a repetition loop) |
| Synthesis voice | Perspectives framed as Codette's own first-person lenses, not external parties she quotes |
| Session list resilience | `list_sessions()` degrades gracefully if the project drive briefly disconnects |
| Benchmark backend | `full_benchmark.py --backend server` scores the live llama.cpp + LoRA-hot-swap system directly |
| Voice-reinforced retrain | All 8 perspectives retrained on their own datasets + distinct personas + the 4 locks (HF Jobs, uv) |
| First full self-benchmark | 82.9% across 41 tests (9 categories); guard held with zero grandiosity signals |
| Router bug fix | Adapter routing was scoring injected identity/memory context, not the question — now routes on the extracted user query |

---

## Hugging Face resources

| Resource | Link |
|---|---|
| Academic Paper | [Raiff1982/codette-paper](https://huggingface.co/Raiff1982/codette-paper) |
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
@misc{harrison2026codette,
  title     = {Codette: A Sovereign Modular Cognitive Architecture for Ethical Multi-Agent AI},
  author    = {Harrison, Jonathan},
  year      = {2026},
  doi       = {10.57967/hf/8998},
  url       = {https://huggingface.co/Raiff1982/codette-paper},
  publisher = {Hugging Face}
}
```

Preprint (Research Square, 10 April 2026):

```bibtex
@misc{harrison2026codette_preprint,
  title     = {Codette: Multi-Perspective Reasoning as a Convergent Dynamical System with Meta-Cognitive Strategy Evolution},
  author    = {Harrison, Jonathan},
  year      = {2026},
  month     = {apr},
  note      = {Preprint (Version 1)},
  doi       = {10.21203/rs.3.rs-9362560/v1},
  url       = {https://doi.org/10.21203/rs.3.rs-9362560/v1},
  publisher = {Research Square}
}
```
