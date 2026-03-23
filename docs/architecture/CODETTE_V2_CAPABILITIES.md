# Codette v2.0 — Multi-Perspective AI Reasoning System

## Overview

Codette v2.0 is a production-ready multi-agent reasoning system that combines analytical depth with controlled debate. It routes queries to specialized reasoning adapters, orchestrates multi-perspective discussion, detects and manages epistemic tension, and synthesizes nuanced conclusions.

**Version**: 2.0 (Phase 6 + Stability Patches)
**Model**: Llama 3.1 8B quantized with LoRA adapters
**Memory**: Cocoon-backed persistent session state (encrypted)
**Deployment**: Zero-dependency local web server (Python stdlib)

---

## Core Capabilities

### 1. Domain-Aware Agent Routing (Phase 6, Patch 5)
- **Automatic domain detection** from query keywords
- **Selective agent activation** — only relevant perspectives participate
- **Domain-to-agent mapping**:
  - **Physics** → Newton, Quantum
  - **Ethics** → Philosophy, Empathy
  - **Consciousness** → Philosophy, Quantum
  - **Creativity** → DaVinci, Quantum
  - **Systems** → Quantum, Philosophy

**Why it matters**: Reduces noise, improves reasoning quality, prevents irrelevant agents from cluttering debate.

### 2. Semantic Conflict Detection & Analysis (Phase 6)
- **Embedding-based tension scoring** (1.0 - cosine_similarity of Llama embeddings)
- **Hybrid opposition scoring** = 60% semantic + 40% heuristic pattern matching
- **Conflict types classified**:
  - **Contradiction** (direct negation)
  - **Emphasis** (different framing, same core)
  - **Framework** (operating from different models)
  - **Depth** (shallow vs. detailed treatment)

**Key metric**: ξ (Xi) — Epistemic Tension (0-1, continuous, not discrete)

**Why it matters**: Real semantic disagreement vs. surface-level differences — enables productive debate.

### 3. Controlled Multi-Round Debate (Phase 6, Patch 2, Patch 4)
- **Round 0**: All agents analyze query independently
- **Rounds 1-3**: Debate between selected pairs, seeing peer responses
- **Conflict capping** (Patch 2): Hard limit of top 10 conflicts per round
  - Prevents combinatorial explosion (214-860 conflicts → capped at 10)
- **Gamma authority** (Patch 4): Hard stop if system coherence drops below 0.3
  - Allows healthy debate while preventing runaway
  - Previously: 0.5 threshold was too aggressive
  - Now: 0.3 threshold balances stability with reasoning depth

**Why it matters**: Debate amplifies reasoning quality without spiraling into infinite disagreement.

### 4. Real-Time Coherence Monitoring (Phase 5A)
- **Γ (Gamma) metric** = system health score (0-1)
  - 0.3-0.7: Healthy debate (tension + diversity)
  - >0.8: Groupthink (approaching false consensus)
  - <0.3: Collapse (emergency stop triggered)
- **Components measured**:
  - Average conflict strength
  - Perspective diversity
  - Adapter weight variance
  - Resolution rate (conflict closure over rounds)

**Why it matters**: Detects emergent pathologies before they corrupt reasoning.

### 5. Multi-Phase Conflict Evolution Tracking (Phase 3)
- Tracks conflicts across debate rounds
- Measures resolution effectiveness
- **Resolution types**:
  - Hard victory (one perspective wins)
  - Soft consensus (integrated understanding)
  - Stalled (unresolved)
  - Worsened (debate amplified conflict)
- **Metrics**: trajectory slope, resolution rate, time-to-resolution

**Why it matters**: Understands whether debate actually improves reasoning or creates noise.

### 6. Experience-Weighted Adapter Selection (Phase 2, Phase 4)
- **Memory-based learning**: Tracks adapter performance historically
- **Dynamic weight adjustment** (0-2.0 scale):
  - High-performing adapters get boosted
  - Low-performers get suppressed
  - Soft boost: modulates router confidence ±50%
- **Learning signals**:
  - Resolution rate > 40% → boost +0.08
  - Soft consensus → boost +0.03
  - Conflicts worsened → penalize -0.08
- **Recency decay**: 7-day half-life (recent performance weighted higher)

**Why it matters**: System improves over time; learns which adapters work for which questions.

### 7. Specialization Tracking (Phase 6)
- Per-adapter, per-domain performance monitoring
- **Specialization score** = domain_accuracy / usage_frequency
- **Convergence detection**: Alerts if adapter outputs >0.85 similar
- Prevents semantic monoculture (adapters doing same work)

**Why it matters**: Ensures adapters maintain functional specialization despite weight drift.

### 8. Ethical Governance & Safety (AEGIS, Nexus)
- **AEGIS module**: Evaluates outputs for:
  - Factual accuracy (known unknowns flagged)
  - Harmful content detection
  - Bias detection
  - Alignment with user intent
- **Nexus signal intelligence**: Cross-checks for contradictions between adapters
- **Guardian input check**: Sanitizes input before routing

**Why it matters**: AI that reasons deeply also reasons responsibly.

### 9. Living Memory with Cocoon Storage (Phase 2)
- **Persistent session state** across conversations
- **Cocoon storage**: Encrypts, deduplicates, and compresses memories
- **Conflict replay**: Top 5 conflicts per debate stored for learning
- **Memory footprint**: ~5KB per conflict (highly efficient)

**Why it matters**: Conversation context persists; system builds understanding within and across sessions.

### 10. Pre-Flight Conflict Prediction (Phase 6)
- **Spiderweb injection** before debate starts
- **5D state encoding** of queries:
  - ψ (psi): concept magnitude
  - τ (tau): temporal progression
  - χ (chi): processing velocity
  - φ (phi): emotional valence
  - λ (lambda): semantic diversity
- **Conflict profiling**: Predicts which adapter pairs will clash and along which dimensions
- **Router recommendations**: Pre-select stabilizing adapters

**Why it matters**: Reduces wasted debate cycles by predicting conflicts before they happen.

---

## Phase 6 Stability Patches

Three critical patches address the "thinking but not stopping" pathology:

### Patch 1: Conflict Filtering (Framework Differences)
```
if conflict_type == "framework" and semantic_overlap > 0.6:
    discard_conflict()
```
High-overlap framework disagreements aren't worth debating.

### Patch 2: Top-K Conflict Selection (Hard Cap)
```
conflicts = sorted(conflicts, key=lambda x: x.strength)[:10]
```
Prevents combinatorial explosion. Alone fixes ~80% of the explosion problem.

### Patch 3: Gamma Authority with Tuned Threshold
```
if gamma < 0.3:  # Changed from 0.5 to allow more debate
    stop_debate = True
```
Hard stop only when truly collapsing. Allows healthy multi-round debate.

**Result**: Conflicts down to 10-30 per round (from 1500+), gamma stable at 0.7-0.9, reasoning depth preserved.

---

## Example Queries & Expected Behavior

### Physics Question
**Query**: "What is the speed of light and why does it matter?"
- **Domain detected**: physics
- **Agents activated**: Newton (analytical), Quantum (relativistic)
- **Debate**: Newton discusses classical mechanics; Quantum discusses relativistic invariance
- **Coherence**: High (0.75+) — complementary perspectives
- **Synthesis**: Unified explanation covering both scales

### Ethics Question
**Query**: "How should we balance accuracy and explainability in AI systems?"
- **Domain detected**: ethics
- **Agents activated**: Philosophy (frameworks), Empathy (stakeholder impact)
- **Debate**: Philosophy discusses deontological vs. consequentialist trade-offs; Empathy discusses user understanding needs
- **Coherence**: Medium (0.65-0.75) — genuine tension between values
- **Synthesis**: Nuanced trade-off analysis acknowledging incommensurable values

### Consciousness Question
**Query**: "What would it mean for a machine to genuinely understand?"
- **Domain detected**: consciousness
- **Agents activated**: Philosophy (conceptual), Quantum (probabilistic modeling)
- **Debate**: Philosophy questions definitions of understanding; Quantum discusses computational capacity
- **Coherence**: May trend low (0.5-0.65) — hard problem, genuine disagreement
- **Synthesis**: Honest assessment of philosophical limits and empirical gaps

---

## Architecture Diagram

```
Query Input
    ↓
[Domain Detection] → Classify physics/ethics/consciousness/creativity/systems
    ↓
[Agent Gating] (Patch 5) → Activate 2-3 relevant agents only
    ↓
Round 0: Independent Analysis
    ↓
[Conflict Detection] → Semantic tension + heuristic opposition
    ↓
[Conflict Capping] (Patch 2) → Top 10 by strength
    ↓
Debate Rounds (1-3):
    ├─ Agent pairs respond to peer perspectives
    ├─ [Conflict Evolution Tracking] → measure resolution
    ├─ [Experience-Weighted Routing] → boost high-performers
    ├─ [Gamma Monitoring] → coherence health check
    └─ [Gamma Authority] (Patch 4) → stop if γ < 0.3
    ↓
[Synthesis Engine] → Integrate debate + memory
    ↓
[AEGIS Evaluation] → Safety/alignment check
    ↓
Response Stream (SSE)
    ↓
[Cocoon Storage] → Remember conflict + resolution
```

---

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| Model size | 8.5GB (quantized) | Llama 3.1 8B F16 |
| Load time | ~60s | First inference takes longer |
| Query latency | 10-30s | Includes 1-3 debate rounds |
| Max debate rounds | 3 | Configurable per query |
| Conflicts per round | ~10 (capped) | From 200-800 raw |
| Memory per session | 1-5MB | Cocoon-compressed |
| Adapter count | 8 (expandable) | Newton, DaVinci, Empathy, Philosophy, Quantum, Consciousness, Systems, Multi-Perspective |

---

## Deployment

### Local Web UI
```bash
# Double-click to launch
codette_web.bat

# Or command line
python inference/codette_server.py [--port 8080] [--no-browser]
```

**URL**: http://localhost:7860
**Features**:
- Streaming responses (SSE)
- Session persistence
- Export/import conversations
- Cocoon dashboard
- Spiderweb visualization

### Programmatic API
```python
from reasoning_forge.forge_engine import ForgeEngine

forge = ForgeEngine(enable_memory_weighting=True)
result = forge.forge_with_debate(
    concept="Is consciousness computational?",
    debate_rounds=2
)

print(result['synthesis'])
print(f"Coherence: {result['metadata']['gamma']}")
```

---

## Known Limitations & Future Work

### Current Limitations
- **Debate can be noisy on hard problems**: Consciousness, abstract philosophy still generate high tension (expected)
- **Pre-flight predictor not yet suppressing agents**: Predicts conflicts but doesn't yet prevent them (Phase 7)
- **No knowledge cutoff management**: Doesn't distinguish between known unknowns and hallucinations

### Phase 7 (Research Direction)
- Semantic drift prevention (adapter convergence < 0.70)
- Client-side preference learning (user ratings → memory boost)
- Multi-turn question refinement
- Confidence calibration (reported ≠ actual correctness)
- Cross-domain synthesis (combining insights from different domains)

---

## Citation & Attribution

**Creator**: Jonathan Harrison
**Framework**: RC+ξ (Reasoning & Conflict + Epistemic Tension)
**Version**: Codette v2.0, Session 2026-03-19
**Components**: 6 years of multi-agent reasoning research, formalized in 2026

---

## Getting Started

1. **Launch the UI**:
   ```bash
   double-click codette_web.bat
   ```

2. **Ask a Question**:
   - Type in the chat box or select a suggested question
   - Codette automatically routes to relevant adapters
   - Watch the Cocoon dashboard for real-time metrics

3. **Save & Resume**:
   - Conversations auto-save with Cocoon storage
   - Sessions persist across browser closures
   - Export for sharing or analysis

4. **Dive Deeper**:
   - Read `PHASE6_CONTROL_PATHOLOGY.md` for system design insights
   - Check `evaluation_results.json` for empirical validation data
   - Explore memory with the "Cocoon" panel

---

**Welcome to Codette v2.0. What would you like to think through today?**
