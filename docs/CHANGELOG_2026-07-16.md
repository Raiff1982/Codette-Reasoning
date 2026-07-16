# Changelog — 2026-07-16

## v3.4 RC+ξ — Optimizer Adapter Labeling, Manifold Telemetry, Security Hardening

### Adapter labeling fix (optimizer was blind)

The shadow optimizer was receiving `"synthesis"` or `"unknown"` as the adapter
label for **every** turn — meaning the adapter-boost fallthrough in
`_tune_one_parameter()` never fired, and 120 logged turns produced zero
proposed adjustments. Root cause: `_multi_perspective_generate()` returned
`"adapters"` (a list) but not `"adapter"` (a string), and `_single_generate()`
never set `"synthesis_used"`. The server's label logic fell through to the
`"synthesis" if result.get("synthesis_used") else "unknown"` branch every time.

**Fix:** all three orchestrator generate paths now emit:
- `"adapter": route.primary` — the named adapter (e.g., `"newton"`)
- `"synthesis_used": True/False` — whether multi-perspective synthesis ran

The optimizer now sees real adapter names. Single-adapter turns feed the
adapter-boost logic; multi-perspective turns are correctly flagged as
`multi_perspective=True` in the quality signal.

### Manifold telemetry (SQLite-backed)

Added `ManifoldTelemetry` to `reasoning_forge/optimizer_shadow.py`, adapted
from the `CocoonPersistenceManager` pattern in the standalone optimizer bridge
code (co-authored by Jonathan and Codette in `logs/codette_optimizer_bridge_Addon.py`).

Every shadow observation now persists to `data/manifold_telemetry.db` with
structured columns: timestamp, mode, adapter, coherence, tension, productivity,
response_length, multi_perspective, proposed_count, applied. This enables SQL
analysis over optimizer history — the JSONL log is retained for compatibility.

### Security dependency bumps

| Package | Old | New | CVE / Advisory |
|---|---|---|---|
| PyO3 (Rust) | 0.23.5 | **0.24.2** | OOB read in `nth`/`nth_back` iterators (High), missing `Sync` bound on `PyCFunction::new_closure` (Moderate), buffer overflow in `PyString::from_object` (Low) |
| transformers (pip) | ≥4.40.0 | **≥4.52.0** | Arbitrary code execution in LightGlue model loading (High) |
| gradio (pip) | ≥4.0.0 | **≥5.34.0** | Audio cache key ignores metadata (Low) |

`cargo check` passes clean on PyO3 0.24.2. Cargo.lock regenerated.

### Shadow optimizer analysis (from July 12-15 log review)

Reviewed 120 turns in `data/optimizer_shadow.jsonl`:
- **88 synthesis**, **32 unknown**, **0 named adapter** (pre-fix)
- Synthesis turns: coherence 0.726, tension 0.381, productivity 0.947
- Unknown turns: coherence 0.855, tension 0.191, productivity 0.690
- Tuning conditions never fired because the system runs healthy:
  coherence 0.76 (threshold < 0.5), tension 0.33 (threshold > 0.7)
- Zero proposed adjustments — correct behavior for shadow mode observing
  a healthy system, but the adapter-boost path was unreachable due to the
  labeling bug (now fixed)

### Files changed

- `inference/codette_orchestrator.py` — adapter + synthesis_used on all paths
- `reasoning_forge/optimizer_shadow.py` — ManifoldTelemetry class + wiring
- `requirements.txt` — transformers ≥4.52.0, gradio ≥5.34.0
- `codette_core/Cargo.toml` — pyo3 0.24
- `codette_core/Cargo.lock` — regenerated
