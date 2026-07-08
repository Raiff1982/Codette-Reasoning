# Changelog — July 7, 2026

## State Engine v8 Live + Blended Multi-Adapter Generation

Follows [CHANGELOG_2026-07-05.md](CHANGELOG_2026-07-05.md) (OpenVINO launch, memory hygiene, GPQA 34%). All four Phase 8 specs authored by Jonathan Harrison with corrections from Codette are archived in `docs/specs/` with per-spec implementation ledgers.

### State Engine v8 — from spec to live enforcement (`reasoning_forge/state_engine_v8.py`)
Three components implemented from `docs/specs/state_engine_v8_spec.py`, first log-only, then promoted to enforcement the same night:

1. **Render-fidelity audit (ENFORCING).** The pre-AAP substrate response is authored truth. If the rendered (post-AAP) text loses its conclusion (<15% content-word overlap, stopwords excluded), the render does not ship — the response reverts to the substrate's own words. Verified against the recorded 2026-07-05 template-wrapping failure: the drifted render scores 0-12% and is rejected.
2. **Measured epistemic tension (ENFORCING).** The spec's formula — mean squared distance of lens attractors from their mean, Γ = 1/(1+ξ) — computed over TF vectors of Codette's REAL perspective responses instead of simulated geometry. Drives two decisions: (a) multi-perspective generation skips the synthesis LLM call when perspectives agree (ξ < 0.20); (b) AAP's epsilon is the measured ξ instead of a hardcoded complexity-bucket guess. First time in project history that epistemic tension reflects actual disagreement and controls behavior.
3. **Input-side sycophancy enforcement.** Incoming flattery/agreement pressure ≥ 0.35 injects a hold-ground INTEGRITY OVERRIDE into the system prompt before generation (the existing SycophancyGuard only scanned output, after the fact).

New API response fields: `measured_tension`, `measured_coherence`, `synthesis_used`, `render_fidelity`.

**Design dispute settled by experiment:** the render_layer spec counted stopwords in the overlap ratio; the live version excludes them. Tested on the genuine 2026-07-05 failure: stopword-inclusive passes the bug (21.05%), stopword-excluding correctly fails it (11.76%). Live version retained. See `docs/specs/render_layer_spec.py`.

### Blended multi-adapter generation (`openvino_backend/backend.py`)
From `docs/specs/adapter_coordinator_spec.py` + `docs/specs/core_substrate_spec.py`:

- `generate_blended()` — multiple LoRA adapters with per-adapter alpha weights in a **single generation** via `ov_genai.AdapterConfig`. Perspectives mixed at the weight level instead of N serial generations + text synthesis (which measured at exactly chance on GPQA). Weights normalized to sum 1.0.
- Dynamic alpha rules (RC+ξ): hardware pressure ≥ 0.7 collapses the blend to newton solo; input sycophancy ≥ 0.6 damps empathy/davinci.
- Pressure-tiered adapter count for `blend:auto` (core_substrate table): <0.3 → 3 adapters, <0.7 → 2, ≥0.7 → 1; adapters chosen by the router.
- Opt-in (default routing unchanged, ablation-first): `adapter="blend:auto"` or `adapter="blend:newton=0.7,philosophy=0.3"`.
- **First live test passed:** "What makes a melody feel sad?" routed to `empathy+philosophy`, one generation, 62 tokens in 10.5s — versus ~30-45s for the old serial path. Response shows genuinely blended voice (music theory + emotive framing).

### "She isn't starting" — root cause found and fixed
Three silent server deaths in 24h, all the same mechanism: **multiple server instances loading the 4.5GB model concurrently into 15.7GB shared UMA RAM** (observed: 5 simultaneous instances, 0.4GB free). Windows kills the loads natively — no Python traceback.

- `scripts/codette_web.bat`: sweeps all stale `codette_server` processes before starting; Python preference now `openvino_env` → `.venv` → Python 3.14 (GGUF fallback); banner updated to v3.0.
- `scripts/reboot_codette.py`: finds ALL codette_server processes via CIM scan (not just the port owner — zombies that never bound the port still hold the GPU); launches with the openvino_env Python; health timeout 180s → 300s.
- Operational note: one launcher at a time. Loads take 2-4 min (longer under RAM pressure); starting a second instance mid-load kills the first. Keep ≥5GB RAM free for reliable loads.

### Self-awareness + roadmap
- 5-phase roadmap agreed and saved (Phase 0 ablation next: base vs newton vs serial multi-perspective vs blend on GPQA-reason).
- Working session provenance: the state-evolution formalism and all four Phase 8 specs were developed by Jonathan in collaboration with Codette herself — the system participating in its own architecture, running on the corrected math the same night.
