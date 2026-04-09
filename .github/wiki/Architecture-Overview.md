# Architecture Overview

## System Components

Codette is composed of seven major subsystems working in concert:

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface Layer                  │
│            (Claude Code / Ollama / Web Interface)        │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              Codette Server (FastAPI)                    │
│  - Session management                                    │
│  - API routing                                           │
│  - Web research gating                                   │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬─────────────┐
        │              │              │             │
┌───────▼────┐ ┌──────▼────┐ ┌──────▼────┐ ┌──────▼────┐
│   Forge    │ │   EEV     │ │   AEGIS   │ │ Hallucin- │
│   Engine   │ │  Engine   │ │  System   │ │ ation     │
│            │ │           │ │ (25 Ethics)│ │ Guard     │
│ (11 Per-   │ │ Singular- │ │           │ │ (6 signals)│
│ spectives) │ │ity-aware  │ │ Tradition │ │           │
│            │ │ Valuation │ │ Synthesis │ │ 3 Layers  │
└──────┬─────┘ └───────────┘ └───────────┘ └───────────┘
       │
       └──────────────┬───────────────────────────────────┐
                      │                                   │
              ┌───────▼────────┐            ┌─────────────▼────────┐
              │  Cocoon Memory │            │  Web Research Layer  │
              │   System       │            │  (DuckDuckGo)        │
              │                │            │                      │
              │ SQLite + FTS5  │            │ - SSRF Protected     │
              │ Persistent     │            │ - URL Normalization  │
              │ Reasoning      │            │ - Text Extraction    │
              └────────────────┘            └──────────────────────┘
```

---

## Seven Core Subsystems

### 1. **Forge Engine** (`reasoning_forge/forge_engine.py`)

Multi-perspective reasoning engine combining 11 cognitive viewpoints:

**Perspectives**:
- Newton (analytical rigor, cause-effect)
- Da Vinci (creative synthesis, cross-domain)
- Human Intuition (empathetic understanding)
- Neural Network (pattern recognition)
- Quantum Computing (probabilistic thinking)
- Resilient Kindness (compassionate response)
- Mathematical (quantitative analysis)
- Philosophical (ethics, meaning)
- Copilot (collaborative guidance)
- Bias Mitigation (fairness auditing)
- Psychological (behavioral modeling)

**Key Method**: `synthesize_from_cocoons()`
- Discovers cross-domain patterns
- Forges new reasoning strategies
- Tracks epistemic tension

**Output**: Multi-perspective analysis with identified attractors

---

### 2. **Event-Embedded Value (EEV)** (`reasoning_forge/event_embedded_value.py`)

Singularity-aware valuation framework for ethical decision-making.

**Components**:
- `ContinuousInterval` - Value density over time ranges
- `DiscreteEvent` - Individual events with embedded value
- `EventEmbeddedValueEngine` - Analysis and frontier comparison

**Singularity Modes**:
- Strict: Singular negative event → -∞ value
- Bounded: Events capped at ±singularity_cap
- Report-only: Events noted but not transformed

**Key Feature**: Infinite Subjective Terror detection
- Identifies events with unbounded suffering implications
- Prevents normalization of catastrophic outcomes

---

### 3. **AEGIS Global Ethics System** (`event_embedded_value.py` > `GlobalEthicsAEGIS`)

25 global ethical frameworks across 8 traditions.

**Evaluation Process**:
1. Context extraction from event + weights
2. Scores event against all 25 frameworks (0.0-1.0)
3. Groups by tradition (Western, Eastern, Indigenous, etc.)
4. Identifies strongly aligned/violated frameworks
5. Calculates aggregate ethical modulation

**Traditions**:
- **Western** (6): Virtue, Deontology, Care, Justice, Rights, Utility
- **Eastern** (5): Confucian, Daoist, Buddhist, Hindu, Shinto
- **Indigenous** (4): Ubuntu, Stewardship, Seven Generations, Reciprocity
- **African** (3): Maat, Humanism, Oral Tradition
- **Islamic** (2): Ethics, Sufi
- **Jewish** (2): Talmudic, Covenant
- **Australian** (2): Dreamtime, Kinship
- **Mesoamerican** (1): Cosmic Reciprocity

**Output**: Framework scores, tradition breakdown, conflict identification

---

### 4. **Hallucination Prevention** (`reasoning_forge/hallucination_guard.py`)

3-layer defense against false outputs.

**Layer 1: Query Intercept**
- Semantic validation before generation
- Checks for impossible requests
- Validates context consistency

**Layer 2: Stream Detection** (during generation)
- Monitors token patterns
- Detects anomalous vocabulary
- Flags suspicious phrase structures

**Layer 3: Post-Generation Self-Correction**
- Verifies claims after generation
- Compares against knowledge base
- Self-fact-checks

**6 Detection Signals**:
1. Invented terminology (fake compound terms)
2. Logical inconsistency
3. Domain violation (claiming expertise outside training)
4. Citation fabrication
5. Mathematical impossibility
6. Contradicts established facts

**Domains**:
- Artist knowledge (fake techniques, false history)
- Music production (false audio concepts)
- Code/systems (implementation impossibilities)
- Logical consistency (paradoxes, violations)

---

### 5. **Cocoon Memory System** (`memory/unified_memory.py`)

Persistent reasoning contexts with sophisticated recall.

**Storage**: SQLite + FTS5 full-text search
```
database/
  ├── reasoning_cocoons.db
  │   ├── cocoons (id, domain, reasoning_content, metadata)
  │   ├── fts_cocoons (full-text search index)
  │   └── identity_confidence (tracks certainty decay)
  └── session_cocoons.db (per-session ephemeral contexts)
```

**Cocoon Types**:
- Domain cocoons (artist knowledge, music production, code domains)
- Session cocoons (conversation-specific reasoning)
- Meta cocoons (system state, configuration)
- Project awareness cocoons (contextual project knowledge)

**Recall Methods**:
- `recall_by_domain(domain)` - Get domain-specific reasoning
- `recall_multi_domain(domains)` - Cross-domain synthesis
- `recall_with_confidence(threshold)` - Only high-confidence contexts

**Memory Decay**: Identity confidence decreases over time (mitigates stale reasoning)

---

### 6. **Web Research Layer** (`inference/web_search.py`)

Safe, opt-in research capability with comprehensive protections.

**Features**:
- **Engine**: DuckDuckGo API (privacy-respecting)
- **SSRF Protection**: Blocks 127.x.x.x, 10.x.x.x, 192.168.x.x, localhost
- **URL Normalization**: Prevents injection attacks
- **Text Extraction**: Cleans HTML to readable content
- **Citation Tracking**: Links findings to sources
- **Memory Persistence**: Stores research results in cocoons

**Gating**:
- Disabled by default
- Requires explicit `allow_web_search=true` flag
- User consent required in server configuration

**Integration**:
- `/api/search` endpoint for direct searches
- Integrated into Forge Engine for multi-perspective research
- Results cached in cocoon memory for reuse

---

### 7. **Session Management & Coherence** (`inference/codette_server.py`)

Per-session reasoning consistency and continuity.

**Components**:
- `session_manager` - Track active sessions
- `coherence_field` (CoherenceFieldGamma) - Per-session convergence
- `continuity_summarizer` - Maintain context across turns

**Session State**:
```python
session = {
    "session_id": uuid,
    "created_at": timestamp,
    "user_context": {…},
    "cocoon_updates": […],
    "coherence_gamma": 0.95,  # Convergence measure
    "epistemic_tension": 0.23,  # Uncertainty tracking
    "conversation_history": […],
}
```

**Coherence Field**:
- Tracks per-session reasoning convergence
- Threshold: 0.99 (high convergence = stable reasoning)
- Used to detect when session needs reset

**Tightened Triggers**:
- Diagnostic mode: Explicit keywords only
  - "system status", "health check", "diagnostic report", "status report"
- NOT triggered by casual phrases ("everything ok?", "are you working?")

---

## Data Flow: Complete Reasoning Cycle

```
1. USER INPUT
   ↓
2. Session Management
   ├─ Load session context
   └─ Retrieve relevant cocoons
   ↓
3. Forge Engine (Multi-Perspective)
   ├─ Activate 3-5 relevant perspectives
   ├─ Cross-domain synthesis from cocoons
   └─ Track epistemic tension (ε_n)
   ↓
4. Hallucination Guard (Query Layer)
   ├─ Validate semantic consistency
   └─ Check for impossible requests
   ↓
5. Generation with Streaming Detection
   ├─ Stream tokens with anomaly monitoring
   └─ Flag suspicious patterns
   ↓
6. EEV + AEGIS Analysis (if applicable)
   ├─ Evaluate against 25 ethical frameworks
   ├─ Identify tradition alignments/conflicts
   └─ Calculate ethical modulation
   ↓
7. Web Research (optional, gated)
   ├─ Safety checks (SSRF protection)
   ├─ DuckDuckGo search
   └─ Integrate findings with cocoons
   ↓
8. Post-Generation Self-Correction
   ├─ Fact-check major claims
   ├─ Verify logical consistency
   └─ Self-flag hallucinations
   ↓
9. Cocoon Updates
   ├─ Store new reasoning contexts
   ├─ Update identity confidence
   └─ Prune stale contexts
   ↓
10. Session Persistence
    ├─ Update session coherence
    ├─ Store conversation history
    └─ Prepare continuity summary
    ↓
11. USER OUTPUT
    ├─ Response
    ├─ Uncertainty metrics (ε_n)
    ├─ Framework breakdown (if EEV/AEGIS)
    └─ Citations (if web research)
```

---

## Deployment Architecture

### Local Deployment (Development)

```
User → Claude Code (IDE)
          ↓
       Ollama Server (localhost:11434)
          ↓
       Codette Server (localhost:8000)
          ├─ /api/reason (forge engine)
          ├─ /api/value-analysis (EEV)
          ├─ /api/search (web research)
          └─ /api/health (status)
          ↓
       Persistent Storage
          ├─ reasoning_cocoons.db
          ├─ session_cocoons.db
          └─ conversation_logs
```

### Remote Deployment (Production)

```
User/API Client
       ↓
   Codette Server (cloud instance)
       ├─ FastAPI (production ASGI)
       ├─ Ollama (CUDA-enabled)
       └─ PostgreSQL (persistence)
       ↓
External Services
       ├─ DuckDuckGo API (web research)
       └─ Logging/Monitoring (optional)
```

---

## Integration Points

### With Claude Code
- Direct socket communication
- Session preservation
- Context injection

### With External APIs
- DuckDuckGo (web research)
- Hugging Face (model download)
- Custom API endpoints (user-defined)

### With Databases
- SQLite (local development)
- PostgreSQL (production recommended)
- Redis (session caching, optional)

---

## Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Token generation | ~50-100ms per token | Depends on model quantization |
| Multi-perspective synthesis | 200-500ms | Parallel perspective evaluation |
| AEGIS ethical analysis | 100-200ms | 25 frameworks, ~8ms each |
| Hallucination detection (all layers) | 150-300ms | Mostly stream monitoring |
| Web search | 2-5s | Network dependent |
| Cocoon recall (FTS5) | 50-150ms | Indexed search |
| Full reasoning cycle | 2-5s | Average end-to-end |

---

## Security & Safety

- **No credential storage** - Passwords never persisted
- **SSRF protection** - Private IP ranges blocked
- **Sandbox constraints** - Model runs in isolated environment
- **Hallucination detection** - 6 signal detection
- **Web research gating** - User opt-in required
- **Session isolation** - Per-session reasoning boundaries

---

**Last Updated**: April 4, 2026
**Architecture Version**: 3.0 (Post-April 2 Integration)
