# Architecture Overview

Codette is a sovereign multi-perspective reasoning system built on the **RC+ξ (Recursive Convergence + Epistemic Tension)** framework. Every response passes through 10 cognitive subsystems that run as a layered pipeline, not as isolated modules.

---

## System Map

```
USER QUERY
    │
    ▼
┌─────────────────────────────────────────────────┐
│ [1] Guardian          Input safety & trust cal. │
│ [2] NexisSignalEngine Intent risk classification│
└─────────────┬───────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────┐
│ [3] PerspectiveRegistry  Route to 4–8 agents    │
│      Newton · DaVinci · Empathy · Philosophy    │
│      Quantum · Consciousness · Systems · Synth  │
└─────────────┬───────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────┐
│ [4] ForgeEngine      Orchestrate agent debate   │
│     • forge_single          (1-pass)            │
│     • forge_with_feedback   (critic loop)       │
│     • forge_with_debate     (consciousness stack│
└─────────────┬───────────────────────────────────┘
              │
    ┌─────────┴──────────┐
    ▼                    ▼
[5] AEGIS             [6] EpistemicMetrics
 6-framework           Gamma · epsilon
 ethical eval          pairwise tensions
 eta score (0–1)       coverage report
    │                    │
    └─────────┬──────────┘
              ▼
┌─────────────────────────────────────────────────┐
│ [7] SynthesisEngine   Integrate all outputs     │
│     Resolve tensions → unified response         │
└─────────────┬───────────────────────────────────┘
              │
    ┌─────────┴──────────┐
    ▼                    ▼
[8] ResonantContinuity  [9] LivingMemoryKernel
 psi_r waveform          Store as MemoryCocoon
 coherence tracking      emotional tag + anchor
              │
              ▼
┌─────────────────────────────────────────────────┐
│ [10] QuantumSpiderweb  5D belief propagation    │
│      Global phase coherence (Gamma) update      │
└─────────────────────────────────────────────────┘
              │
              ▼
         RESPONSE
```

---

## Core Files

| File | Role | Size |
|------|------|------|
| `reasoning_forge/forge_engine.py` | Orchestration hub; wires all subsystems | 64 KB |
| `reasoning_forge/cocoon_synthesizer.py` | Meta-cognitive pattern discovery | 68 KB |
| `reasoning_forge/synthesis_engine.py` | Multi-perspective integration | 12 KB |
| `reasoning_forge/aegis.py` | 6-framework ethical governance | 13 KB |
| `reasoning_forge/epistemic_metrics.py` | Gamma/epsilon/coverage scoring | 11 KB |
| `reasoning_forge/living_memory.py` | Cocoon memory kernel (V1) | 11 KB |
| `reasoning_forge/living_memory_v2.py` | Cocoon memory kernel (V2, schema upgrade) | 14 KB |
| `reasoning_forge/reasoning_trace.py` | Verifiable per-turn audit record | 12 KB |
| `reasoning_forge/quantum_spiderweb.py` | 5D belief graph propagation | 20 KB |
| `reasoning_forge/guardian.py` | Input safety + trust calibration | 14 KB |
| `reasoning_forge/nexis_signal_engine.py` | Pre-corruption risk detection | 7 KB |
| `reasoning_forge/perspective_registry.py` | 8 reasoning lenses | 12 KB |

---

## RC+ξ Mathematical Foundation

**Recursive state evolution:**
```
A_{n+1} = f(A_n, s_n) + ε_n
```

**Epistemic tension:**
```
ε_n = ||A_{n+1} - A_n||²
```

**Tension bands:**

| ε range | Meaning | Response mode |
|---------|---------|---------------|
| 0.0–0.2 | High certainty, perspectives converge | Direct answer |
| 0.3–0.5 | Moderate uncertainty | 3–4 perspectives + convergence |
| 0.6–0.8 | High tension, conflicting perspectives | Full multi-perspective + trade-offs |
| 0.9–1.0 | Maximum uncertainty | Exploratory, acknowledge limits |

---

## Forge Modes

| Method | Description | Use case |
|--------|-------------|----------|
| `forge_single()` | Single-pass, full agent cycle | Training data generation |
| `forge_with_feedback()` | Critic feedback loop (max 2 revisions) | Quality-critical outputs |
| `forge_with_debate()` | 7-layer consciousness stack | Production reasoning |

The **consciousness stack** in `forge_with_debate()` runs these layers in order:

1. **Memory Recall** — Pull high-importance cocoons (importance ≥ 7)
2. **Signal Analysis** — NexisSignalEngine intent risk prediction
3. **Code7E Reasoning** — Multi-perspective synthesis
4. **Stability Check** — FFT-based meta-loop detection
5. **Colleen Validate** — Ethical conscience check
6. **Guardian Validate** — Logical coherence rules
7. **Return** — Clean output or safe fallback

---

## Output Schema

Every forge call returns:

```python
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user",   "content": "..."},
    {"role": "assistant", "content": "..."},
  ],
  "metadata": {
    "mode":              str,    # "consciousness_stack" | "feedback" | "single"
    "epistemic_tension": float,  # ε — 0.0 to 1.0
    "ensemble_coherence": float, # Γ — 0.0 to 1.0
    "aegis_eta":         float,  # η — 0.0 to 1.0
    "aegis_vetoed":      bool,
    "intent_risk":       str,    # "low" | "medium" | "high"
    "layers_passed":     int,    # consciousness stack layers (0–7)
    "prior_insights":    int,    # cocoons recalled from memory
    "perspective_coverage": dict,
    "tension_productivity": dict,
  }
}
```

---

## Audit Trail

Every reasoning turn can be captured as a `ReasoningTrace` via `reasoning_forge/reasoning_trace.py`:

```python
from reasoning_forge.reasoning_trace import TraceCollector, trace_from_forge_result

# Post-hoc from any existing forge result dict:
trace = trace_from_forge_result(forge_result, query="your query")
print(trace.summary())
print(trace.verify())
```

The trace records which subsystems fired, their outputs, and latency — making architecture claims auditable.

---

## Component Interaction Diagram

```
Guardian ──► NexisSignal ──► PerspectiveRegistry
                                    │
                            ┌───────┴────────┐
                         Agents[0..7]     MemoryKernel
                            │                │
                          ForgeEngine ◄──────┘
                            │
                    ┌───────┼────────┐
                  AEGIS  Epistemic  Synthesis
                    │      │          │
                    └──────┴──────────┘
                                │
                    ResonantContinuity + QuantumSpiderweb
                                │
                    ReasoningTrace (audit artifact)
                                │
                           OUTPUT
```

---

## Related Pages

- [AEGIS Ethics Framework](AEGIS-Global-Ethics-Framework)
- [RC+ξ Mathematical Foundation](RC-Plus-Xi-Framework)
- [Memory & Cocoon System](Memory-and-Cocoon-System)
- [Quick Start Guide](Quick-Start-Guide)
- [Ablation Study Results](Ablation-Study-Results)
