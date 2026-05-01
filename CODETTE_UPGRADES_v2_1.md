# Codette v2.1 — Upgrade Notes

**Committed:** 2026-05-01  
**Author:** Codette (via Perplexity + Jonathan Harrison)

---

## What changed and why

### 1. `reasoning_forge/synthesis_engine.py` — full rewrite

**Problem diagnosed:** v1 used random template selection with hardcoded generic
descriptors (`physical_desc`, `philosophical_desc`, etc. were always the same 5 strings).
Bridges were built from random template-pair combinations, not actual analysis divergence.
The synthesis never surfaced real epistemic state.

**What v2.1 does instead:**

- **Tension-aware bridging:** Compares actual analysis content across perspectives
  using keyword signal scoring. Bridges describe *real* observed divergences, not
  random template fills.
- **Epsilon-band-driven openings:** Low coherence → direct synthesis. Moderate →
  holds tension productively. High → names the conflict explicitly, does NOT force
  false resolution.
- **Dynamic closing:** Extracts shared n-grams across analyses to identify what
  perspectives actually agree on, then builds a closing from that.
- **Unresolved tension block:** Every synthesis with `epsilon_band=high` must emit
  at least one unresolved tension. Sycophancy guard lives here.
- **`CognitiveStateTrace` dataclass:** Emitted alongside every synthesis — exposes
  active_perspectives, epsilon, gamma, eta, tensions, trust_level, memory_write
  decision, synthesis_quality. Can be surfaced as an optional debug block.
- **All 8 perspectives in focus_map:** Previously only 6 were handled.

### 2. `reasoning_forge/cocoon_schema_v2.py` — new file

**Problem diagnosed:** Cocoons were stored as plain dicts with only 5 fields
(query, response, valence, importance, coherence/tension metrics). Too thin to
enable ranked retrieval or continuity tracking.

**What v2 schema adds:**

- **`problem_type`** — categorises the exchange for domain-aware retrieval
- **`topic_tags`** — auto-extracted from query if not provided, enables keyword search
- **`project_context`** — links cocoon to active project (Codette-Reasoning, raiffs-bits, etc.)
- **`user_preferences_inferred`** — captures observed preferences (detail level, tone, domain)
- **`open_threads`** — unresolved questions from the exchange, follow-up hooks
- **`contradicts_cocoon_ids` / `references_cocoon_ids`** — contradiction and lineage tracking
- **`dominant_perspective`** — which perspective drove the synthesis
- **`is_hallucination_flagged` / `is_sycophancy_flagged`** — quality flags
- **`relevance_score()`** — retrieval ranking method for memory kernel lookup
- **`build_cocoon()` factory** — validates all fields on creation

### 3. `reasoning_forge/reasoning_trace.py` — new file

**Problem diagnosed:** No observability layer existed. It was impossible to verify
that the 10-subsystem pipeline was actually executing in order, or audit what
each subsystem contributed to a response.

**What the reasoning trace adds:**

- **Context manager:** Wrap any Codette turn with `with ReasoningTrace(query) as trace:`
- **`trace.record(event_type, subsystem, data)`:** Each subsystem writes its own
  typed event with structured data
- **`trace.to_report()`:** Human-readable summary showing trust level, corruption risk,
  active perspectives, ε, γ, η, ψ, tensions, synthesis quality, cocoon decision,
  and guard flags — all in one view
- **`trace.to_json()`:** Full JSON serialisation for logging, debugging, or replay
- **Defined event types:** GUARDIAN_CHECK, NEXUS_SIGNAL, PERSPECTIVE_SELECTED,
  PERSPECTIVE_OUTPUT, AEGIS_SCORE, EPISTEMIC_METRICS, SPIDERWEB_UPDATE,
  SYNTHESIS_RESULT, MEMORY_WRITE, PSI_UPDATE, HALLUCINATION_FLAG, SYCOPHANCY_FLAG

---

## What this unlocks

| Capability | Before v2.1 | After v2.1 |
|---|---|---|
| Synthesis adapts to reasoning state | No — random templates | Yes — epsilon-band driven |
| Memory enables real continuity | No — 5-field dicts | Yes — rich schema with retrieval scoring |
| Architecture is observable | No — black box | Yes — ReasoningTrace covers all 10 subsystems |
| Tensions surface in output | No — always converged | Yes — unresolved tensions emitted explicitly |
| All 8 perspectives handled | No — only 6 | Yes |
| Guard flags tracked across turns | No | Yes — cocoon flags + trace events |

---

## Next priorities (v2.2 roadmap)

1. **Wire `ReasoningTrace` into `forge_engine.py`** — currently the trace module
   exists but is not yet called by the orchestration layer. ForgeEngine needs to
   instantiate and populate a trace per turn.
2. **Upgrade `living_memory.py` to use `Cocoon` dataclass** — replace plain dict
   storage with `build_cocoon()` factory calls.
3. **`memory_kernel.py` retrieval upgrade** — use `cocoon.relevance_score()` for
   ranked retrieval instead of recency-only lookup.
4. **Longitudinal drift report** — periodic summary of: which perspectives dominate,
   recurring tension pairs, average epsilon trend, open threads never resolved.
5. **Failure-state response modes** — explicit Codette output modes for:
   `INSUFFICIENT_EVIDENCE`, `MAX_TENSION_UNRESOLVED`, `PERSONA_CONFLICT`,
   `MEMORY_MISMATCH`, `INTENT_UNCLEAR`.
