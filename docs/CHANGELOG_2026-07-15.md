# Changelog — 2026-07-15

## Gemini damage reverted + new components integrated

A session with Gemini stripped ~4,000 lines of comments, context, and
behavioral logic from the core tracked files — including the LOCK prompts,
state engine v8 guards, and routing logic that drove the 34% GPQA score.
GPQA dropped to 23% under the damaged code. All tracked files reverted to
their last committed state; your improvements merged surgically from archive
backups and new enhanced files.

### Reverted files (Gemini damage undone)

| File | Lines restored |
|---|---|
| `inference/codette_orchestrator.py` | 1,556 (full LOCKs, routing, state engine v8) |
| `reasoning_forge/forge_engine.py` | 2,501 |
| `openvino_backend/backend.py` | 783 (STaR adapters, rep_penalty 1.1, chat cap 600) |
| `reasoning_forge/dream_reweaver.py` | 378 (creative bridges, dream field evolution) |
| `inference/codette_tools.py` | restored (had been deleted) |
| `dataset_engine/perspectives_dataset_v2.py` | restored |
| `benchmarks/gpqa_kaggle.py` | restored |
| `scripts/gpqa_hf_job.py` | restored |

### Enhanced cognition modules — merged

Three enhanced versions of cognition modules merged into their committed
counterparts, keeping all existing functionality and adding new features:

**`reasoning_forge/quantum_optimizer.py`** — all additive:
- `TuningState.validate()` — bounds-checks all parameters
- Momentum tracking across tuning steps with configurable decay
- Adaptive learning rate based on quality window variance
- Exploration vs exploitation branching (`_explore_parameters()`)
- Pluggable quality evaluator via `set_quality_function()`
- `QualitySignal` gains `latency_ms` and `error_rate` fields
- `OptimizationStep` gains `temperature` and `step_type` fields
- Quality weights rebalanced (25/25/15/15/10/10) to include latency + error
- Bounded histories via `deque(maxlen=100)` signals, `deque(maxlen=20)` quality window
- `best_state` serialized in persistence

**`reasoning_forge/quantum_spiderweb.py`** — numpy vectorization + graph analysis:
- `NodeState.distance_to()`, `NodeState.normalize()` helpers
- `WebNode` gains `last_updated`, `activation_level` fields
- `neighbors` → `Set[str]`, `tension_history` → `deque(maxlen=50)`
- `connect()` gains `bidirectional` param, self-loop rejection, returns `bool`
- `disconnect()` method for edge removal
- `build_from_agents()` gains `fully_connected` param
- `propagate_belief()` gains `attenuation_model` param (exponential/linear/inverse) + timing
- `entanglement_sync()` — complex phase with rotation matrix
- `intent_modulation()` — adaptive kappa, modulates chi and phi in addition to psi
- `phase_coherence()` — circular statistics via numpy
- `_compute_centrality()` — degree, betweenness, closeness centrality
- `_shortest_path()`, `_shortest_distance()`, `_avg_path_length()` graph helpers
- `web_analysis()` — comprehensive topology/energy/tension/centrality report
- `_propagation_stats` running statistics dict
- `to_dict()`/`from_dict()` PRESERVED — serialization intact

**`reasoning_forge/perspective_web.py`** — selective merge preserving calibrated metrics:
- `SpiderwebNode.neighbors` → `Set[str]`, `tension_history` → `deque(maxlen=50)`
- `PropagationResult` gains `propagation_time` field
- Embedding propagation during BFS with attenuation + timing
- `SessionGlyphTracker._perspective_vectors` dict for per-turn tracking
- Deque-based history removes need for manual truncation
- PRESERVED: `build_web_from_perspectives()` (dual-mode semantic/lexical), cosine
  tension formula `(1-cos)/2`, `from_text()` with `_tf_vector`, all provenance docstrings

### New files — unified pipeline + tools + evaluation

**`reasoning_forge/WOSME.py`** — Unified Pipeline Harness (RC+ξ Integration Engine):
- `CodetteRuntimePipeline` wires Orchestrator, Spiderweb, ManifoldEngine, and
  AEGIS sub-layers into a single 6-phase cognitive cycle:
  routing → generation → manifold resolution → synthesis → AEGIS veto → optimizer feedback
- Imports fixed to match repo module structure
- AEGIS tries real module before falling back to placeholder scores

**`inference/codette_tool_system.py`** — Tool System v2.1:
- Drop-in replacement / complement to `codette_tools.py`
- Sandboxed file/code/directory operations with AEGIS awareness
- Embedded Cycle Double Cover DFS solver as a callable tool
- Zero-allocation iterative DFS with configurable state ceiling

**`evaluation/impossablemath.py`** — Cycle Double Cover Conjecture Solver:
- Multi-perspective swarm analysis (Systematic/Creative/Algebraic) as front-end
- DFS backtracking with topological validation and chromatic profiling
- Applies Codette's multi-perspective philosophy to a concrete graph theory problem

**`evaluation/impossablemathGPU.py`** — GPU-optimized CDC variant:
- Edge-XOR symmetric difference cycle expansion
- Eulerian network walker for cycle reconstruction
- Numpy-based cycle matrix construction

**`benchmarks/gpqa_codette_batched.py`** — Batched GPQA Runner:
- Auto-restarts server between batches to manage 8GB RAM pressure
- Resume support (`--resume`) — skips completed batches
- Merges all batch results into single output file

### Training pipeline (v3 adapters)

- `dataset_engine/v3/` — hand-authored v3 perspective training data
  (newton, quantum, multi_perspective)
- `training/train_perspectives_v3_uv.py` — one-shot Kaggle QLoRA training
- `training/convert_perspectives_v3_gguf_uv.py` — GGUF conversion pipeline
- `scripts/hf_update_cards.py` — HuggingFace model card updater

### Utility

- `utilities/gemini-code-1781069130675.py` — Hardware memory telemetry
  tracker (psutil-based RSS/VMS/system monitoring)
