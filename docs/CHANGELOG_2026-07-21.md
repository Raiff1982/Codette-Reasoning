# Changelog — 2026-07-21

## v3.6 — TimeTravelLens + AEGIS Protection Layers + UI Observatory

Two major systems integrated in one session: a new institutional temporal-gap analysis framework (TimeTravelLens) wired into every chat turn, and a suite of production protection layers (AEGIS Layers 2–6 + metrics engine) built solo and integrated. One labeling error fixed. One long-standing push blocker documented.

---

### TimeTravelLens — institutional preemption gap analysis

**New theory.** Codette can now measure the temporal gap between when an institution *knew about* a problem (t_op) and when they formally *disclosed* it (t_inst), across a ClosureClass taxonomy derived from evidence signals.

Core formalism (`reasoning_forge/time_travel_lens.py`):

| Metric | Formula | Meaning |
|---|---|---|
| Preemption gap | Π(s) = t_inst − t_op | Days between material action and formal registration |
| Closure score | C(s) ∈ {0.00, 0.24, 0.67, 1.00} | Epistemic closure: INEXPRESSIBLE → CLOSED |
| Rupture indicator | ℛ(s) = 1 iff t_op finite ∧ C(s) < 1.0 | Institution acted without disclosure |
| Beacon indicator | ℬ(s) = 1 iff ℛ ∧ Σ influence > τ_I | High-influence rupture event |
| High preemption zone | Z^H: Π > τ_Π ∧ C < τ_C ∧ var(Π_i) > τ_V | All three severity conditions met |
| Actor preemption gaps | Π_i(s) = t_inst_i − t_op_i | Per-actor breakdown |

ClosureClass taxonomy: `CLOSED` (1.00) / `DRIFT` (0.67) / `SUPPRESSED` (0.24) / `INEXPRESSIBLE` (0.00)

**InstitutionalExtractor** (`reasoning_forge/institutional_extractor.py`): Text-to-InstitutionalState pipeline. Stage 1 extracts dates via five regex patterns + dateutil fallback. Stage 2 classifies event types (material action vs. formal registration), infers ClosureClass from keyword density, and builds per-actor gaps. Confidence rubric: each of t_op, t_inst, closure_class, actors contributes 0.25 × closure_confidence.

**Tests**: `tests/test_time_travel_lens.py` — 33 tests, 0 failures, 0.012s.

**Integration:**

- **Layer 5.8** inserted into `forge_engine.forge_with_debate()` (between AEGIS at 5.75 and Ψ_r computation). Runs when `InstitutionalContextDetector.is_relevant(query)` fires (≥2 institutional keywords; ~0.1ms gate). Full run: ~5–20ms.
- **CocoonV3** extended with `time_travel_metrics: Optional[dict]` field (`cocoon_schema_v3.py`). Stored when confidence ≥ 0.3.
- **Server-level trigger** added to `_handle_chat_sse()` post-response processing — runs the same lens on every completed chat turn, stores result in `response_data["time_travel"]` and a module-level `_last_time_travel_result`.
- **Two new API endpoints:** `/api/time_travel/last` (returns most recent auto-triggered observation) and `/api/time_travel/analyze?text=...` (on-demand analysis of any text string).
- **AEGIS supplementary context:** when `high_preemption_zone=True`, the result is also injected into `aegis_result["supplementary_context"]["time_travel"]` for the deontological framework.
- Controlled by `CODETTE_TIME_TRAVEL` env var (default `"1"` = on). Set to `"0"` to disable for Phase 0 ablation.

**UI panel** (`inference/static/index.html`): `⏱ TimeLens` button in the header opens the TimeTravelLens dashboard showing Π, C, ℛ, ℬ, Z^H, per-actor gaps, confidence, and status banner (red alert on high preemption zone). Includes on-demand text analysis textarea. Auto-polls every 15s when tab is open. Manual `Analyze` button hits `/api/time_travel/analyze`.

**Theory files**: `Theory/timelens.txt`, `Theory/timelens2.txt`, `Theory/howitworks.txt` (Jonathan's original concept documents, preserved as-is).

---

### AEGIS Protection Layers — multi-layer ForgeEngine safeguards

Jonathan built these solo without credits and integrated them. Assessment: Layers 2, 5, 6, and the metrics engine are production-quality Python with real behavior.

| Layer | File | Status |
|---|---|---|
| Layer 2 | `aegis_layer2_complete.py` (428 lines) | ✓ Landlock (Linux) + Windows DACL filesystem isolation |
| Layer 3 | `aegis_layer3_complete.py` (456 lines) | ✓ TPM 2.0 + Secure Boot verification; degrades gracefully on non-Linux |
| Layer 4 | *(concept only — .txt files)* | PLACEHOLDER — SHA3-HMAC labeled as ML-KEM-768; **NOT real PQC** |
| Layer 5 | `aegis_layer5_complete.py` (496 lines) | ✓ Pre-emptive healing using real cocoon fields (ε, γ, pairwise tensions) |
| Layer 6 | `aegis_layer6_complete.py` (504 lines) | ✓ RenderLayer validation: CocoonV3 schema gate + 15% word-overlap gate |
| Orchestrator | `aegis_orchestrator.py` (376 lines) | ✓ Full pipeline wrapper |
| Metrics engine | `aegis_metrics_engine.py` | ✓ SQLite-backed forge call logging with real cocoon field reads |
| Dashboard | `inference/static/index.html` (pre-existing) | ✓ Live metrics grid, healing events log, forge execution log |

Layer 5 reads **real** cocoon fields — ε (epistemic tension), γ (coherence), pairwise tensions — NOT random noise. The metrics engine provides historical healing rates, rejection rates, and overlap percentages via `/api/aegis/*` endpoints.

**Layer 4 PQC disclaimer fix** (`aegis_orchestrator.py` line 11): The docstring previously called SHA3-HMAC a "Hybrid SHA3/liboqs" substrate, implying real lattice crypto. Fixed to explicitly mark it as a design placeholder with the actual fix needed (`liboqs.kem.Kem("Kyber768")`).

---

### Git push blocker — `results.zip` in history

The push to `origin/main` fails because a `results.zip` file (619MB, exceeds GitHub's 100MB limit) exists in the commit history being pushed. The file is already removed in the working tree (`2ecb0f8 chore: remove large results.zip file`), but GitHub's pre-receive hook rejects pushes containing it anywhere in history.

**To fix** (Jonathan must run — history rewrite):
```bash
# Option 1: git-filter-repo (recommended, install once)
pip install git-filter-repo
git filter-repo --path results.zip --invert-paths
git push origin main --force

# Option 2: BFG Repo Cleaner
java -jar bfg.jar --delete-files results.zip
git reflog expire --expire=now --all && git gc --prune=now --aggressive
git push origin main --force
```

This rewrites history. All local clones will need `git fetch --all && git reset --hard origin/main` afterward.

---

### Files changed

**New:**
- `reasoning_forge/time_travel_lens.py` — TimeTravelLens + InstitutionalState + ClosureClass + InstitutionalContextDetector
- `reasoning_forge/institutional_extractor.py` — text-to-InstitutionalState pipeline
- `tests/test_time_travel_lens.py` — 33 tests
- `Theory/timelens.txt`, `Theory/timelens2.txt`, `Theory/howitworks.txt`

**Modified:**
- `reasoning_forge/cocoon_schema_v3.py` — `time_travel_metrics` field + `build_cocoon_v3()` param
- `reasoning_forge/forge_engine.py` — Layer 5.8 block + return dict includes `time_travel_metrics`
- `inference/codette_server.py` — TTLens server trigger + two new endpoints
- `inference/static/index.html` — `⏱ TimeLens` button + full TimeTravelLens dashboard tab + JS
- `Protection_Layer/aegis_orchestrator.py` — Layer 4 PQC mislabeling fixed

**AEGIS files (committed with previous session):**
- `Protection_Layer/aegis_layer2_complete.py`
- `Protection_Layer/aegis_layer3_complete.py`
- `Protection_Layer/aegis_layer5_complete.py`
- `Protection_Layer/aegis_layer6_complete.py`
- `Protection_Layer/aegis_orchestrator.py`
- `Protection_Layer/aegis_metrics_engine.py`
- `Protection_Layer/aegis_forge_integration.py`
- `Protection_Layer/aegis_codette_integration.py`
