# Changelog — 2026-05-01

RC+ξ v2.1 architecture completion wave. Focus areas: full trace wiring,
depth-extension modules (style adaptation, drift detection, cross-system search),
hallucination coverage gap, and structural test coverage.

---

## RC+ξ v2.1 Wiring (Architecture Complete)

### ReasoningTrace — all 12 event types live
All event types now emit real measured values on every inference turn:

| Event | Subsystem | Path |
|-------|-----------|------|
| `SPIDERWEB_UPDATE` | QuantumSpiderweb | `forge_with_debate` |
| `GUARDIAN_CHECK` | EthicalAIGovernance + Guardian | both |
| `NEXUS_SIGNAL` | NexisSignalEngine | both |
| `EPISTEMIC_METRICS` | EpistemicMetrics | both |
| `PERSPECTIVE_SELECTED` | ForgeEngine domain routing | `forge_with_debate` |
| `AEGIS_SCORE` | AEGIS 6-framework ethics | both |
| `HALLUCINATION_FLAG` | HallucinationGuard (PAUSE/INTERRUPT only) | both |
| `SYNTHESIS_RESULT` | SynthesisEngine + StyleAdaptiveSynthesis | both |
| `SYCOPHANCY_FLAG` | SycophancyGuard | both |
| `PSI_UPDATE` | ResonantContinuityEngine | both |
| `MEMORY_WRITE` | LivingMemoryKernelV2 | both |

### Early-return trace gap fixed
All three fallback exits in `forge_with_debate()` (stability halt, Colleen reject,
Guardian reject) previously returned without calling `_trace.finalise()`. Events
recorded before the exit (including PSI_UPDATE at L5.75) were silently dropped.
Fix: all fallback returns now call `_trace.finalise()` and include `reasoning_trace`
in the metadata dict.

---

## New Modules

### `reasoning_forge/drift_detector.py`
Longitudinal drift analysis over `LivingMemoryKernelV2`:

- **Epsilon trend** — least-squares slope over last 10 cocoons (epsilon_band → float);
  classified as `rising` / `falling` / `stable` (±0.05 band)
- **Perspective lock** — fires when one perspective exceeds 60% of usage
- **Recurring tensions** — unresolved_tensions appearing in ≥3 cocoons
- **Open hook accumulation** — count + 5-item sample from `recall_with_hooks()`

`DriftReport.summary()` returns a human-readable paragraph.
`DriftReport.to_dict()` is JSON-serialisable (used by `/api/drift`).

Wired into `ForgeEngine.__init__` as `self.drift_detector`.
Exposed at `GET /api/drift` in `codette_server.py`.
Polled every 60s in the UI; "Longitudinal Drift" side panel shows
ε trend, perspective lock, recurring tension count, open hook count.

### `reasoning_forge/style_adaptive_synthesis.py` (previously unwired)
Now wired into `_forge_single_safe()` post-synthesis (after sycophancy scan).

- Detects conversational register from query context: CASUAL / TECHNICAL / EMOTIONAL / FORMAL / EXPLORATORY
- Blends into 6-dimensional style vector (formality, compression, hedging, structure, first_person, variety)
- Applies up to 5 surface transformations: structure collapse, contraction expansion/compression, hedging injection/removal, filler stripping, first-person shift
- **Depth preservation invariant**: adapted depth ≥ 0.85 × original; partial or full revert if violated
- `SYNTHESIS_RESULT` trace event enriched with `style_register`, `style_depth_preserved`, `style_transforms`

---

## Bug Fixes

### `_forge_single_safe()` synthesis tuple unpack
`SynthesisEngine.synthesize()` returns `tuple[str, CognitiveStateTrace]`.
The caller was assigning the whole tuple to `synthesized_response`, which caused
`AttributeError: 'tuple' object has no attribute 'lower'` in epistemic_metrics.
Fixed by unpacking: `synthesized_response, _synth_trace = _synth_result`.

### HallucinationGuard false positives on short words
`_check_code_hallucinations()` regex with `re.IGNORECASE` matched common English
words: `"in"` → Unknown language, `"and"` → Unknown framework.
Fixed by minimum length guards: `len(lang_name) >= 3`, `len(framework_name) >= 4`.

### HallucinationGuard false positives on Codette vocabulary
Terms like `"quantum cognition"`, `"epistemic tension"`, `"consciousness stack"` were
triggering the invented-terminology check. Fixed with `CODETTE_CANONICAL_TERMS`
frozenset whitelist in `_check_invented_terminology()`.

### `_MockOrchestrator` missing `route_and_generate()`
`forge_with_debate()` calls `orchestrator.route_and_generate()` (not `.generate()`).
Test mocks without this method fell back to Code7E templates silently, making
hallucination tests test the wrong output. Fixed: `_ConfabulatingOrchestrator`
now implements both methods.

---

## Bridges

### UnifiedMemory ↔ LivingMemoryKernelV2 dual-write
After each `store_v2_cocoon()` call in both forge paths, a second write goes to
`self.unified_memory.store()` with `cocoon_id`, `epsilon`, `gamma`, `psi_r` in
metadata. This enables FTS5 full-text search (CocoonSynthesizer, adapter learning
signals) to index RC+ξ outputs without schema changes to either system.

### `SycophancyGuard.reset_session()` on new session
`_handle_new_session()` in `codette_server.py` now calls `reset_session()` so
position memory and agreement-loop counters clear between conversations.

---

## Test Coverage

| File | Tests | What's covered |
|------|-------|---------------|
| `tests/test_trace_e2e.py` | 4 | `_forge_single_safe()` — all 8 expected events fire, psi_r non-zero, problem_type populated, full trace dump |
| `tests/test_trace_debate.py` | 7 | `forge_with_debate()` — schema, trace presence, SPIDERWEB_UPDATE, PERSPECTIVE_SELECTED, PSI_UPDATE on fallback path; HALLUCINATION_FLAG fires on confabulated input, absent on clean hedged input |
| `tests/test_drift_detector.py` | 13 | DriftDetector — null safety, rising/falling/stable epsilon, perspective lock detection, balanced perspectives, recurring tensions ≥3, rare tensions excluded, open hook count, summary string, JSON serialisation |

**Total: 26 tests, all passing.**

---

## UI

- `inference/static/index.html`: Added "Longitudinal Drift" side panel section
  (`section-drift`) with ε trend, perspective lock, dominant perspective, recurring
  tension count, open hook count. Hidden until first `/api/drift` response.
- `inference/static/app.js`: `pollDriftDashboard()` polls `/api/drift` every 60s
  starting 15s after page load; colours ε trend indicator (quantum=rising, empathy=falling);
  shows lock percentage and dominant perspective name.
- `scripts/codette_web.bat`: Updated to v2.1 with full RC+ξ subsystem inventory.
