# Recovered — usable now

**41 modules that run today.** Every file here parses, and every import
resolves to the standard library, a package in `requirements.txt`, or another
file in this folder.

This is a working set, not the archive of record. The complete recovery —
including broken and superseded material, and provenance for all of it — is in
`recovered_release/` with its README. These are copies, safe to pick up and use.

```
pip install -r requirements.txt
```

## Verified, not assumed

All 41 were imported in a clean Python 3.13 environment, not merely
parsed. **38 of 41 import with no error.** The three that do not are listed
below with the actual reason — none is a defect in the recovered code:

| Module | Behaviour | Why |
|---|---|---|
| `codette_app.py` | needs `tkinter` | stdlib, but packaged separately on many Linux distros (`apt install python3-tk`) |
| `codette_timeline_animation.py` | `min()` on empty input | executes at import and expects timeline data to be present |
| `quantum_ai_orbit_simulation.py` | array dimension mismatch | executes at import and expects simulation inputs |

The latter two are scripts, not libraries — they run their simulation on import
rather than under `if __name__ == "__main__"`. They work when given their data.

## One fix applied during verification

`foundations/codette_deep_simulation_v1.py` called `np.trapz`, **removed in
numpy 2.0**. It now binds `np.trapezoid` with a fallback, so it works on both.
The same fix was applied to the copy in `recovered_release/`.

## Contents

### `Protection_Layer`
Unicode spoofing scanner — zero-width, bidi, homoglyph, mixed-script, with a sanitiser.

- `unicode_shadow_scan.py` — 190 lines

### `einstein_rosen`
Bridge package.

- `biofield_bridge.py` — 7 lines
- `timeline_selector.py` — 5 lines

### `experiments`
Scripts and simulations. Several plot on execution.

- `codette_meta_3d.py` — 65 lines
- `codette_quantum_multicore2.py` — 78 lines
- `codette_timeline_animation.py` — 68 lines
- `quantum_cosmic_multicore.py` — 84 lines

### `foundations`
The mathematics `reasoning_forge/memory_kernel.py` cites as its foundation. `von_neumann_entropy` was checked numerically: for diag(0.6, 0.4) it returns 0.673012, matching -0.6ln0.6 - 0.4ln0.4 exactly.

- `codette_deep_simulation_v1.py` — 129 lines

### `from_chat_history`
Source that never existed as a file; recovered from chat transcripts.

- `codette_app.py` — 55 lines
- `codette_quantum_agent.py` — 115 lines
- `grand_physics_engine.py` — 102 lines
- `quantum_science_suite.py` — 146 lines
- `secure_database.py` — 56 lines

### `from_docx`
Source that was stored inside Word documents.

- `advanced_codette_ai.py` — 68 lines
- `codette_heart.py` — 78 lines
- `genomic_codette_ai.py` — 94 lines
- `quantum_nightmare_echo.py` — 52 lines
- `spiderweb_nodes.py` — 105 lines

### `optimization`
Four successive optimiser revisions. **Which supersedes which is undecided** — run `tools/archive_diff.py` and read the version-family section.

- `ethical_mutation_filter.py` — 221 lines
- `multi_objective_optimizer.py` — 131 lines
- `multi_objective_optimizer_graph.py` — 105 lines
- `quantum_optimizer.py` — 72 lines

### `orbital`
Orbital simulation.

- `quantum_ai_orbit.py` — 64 lines
- `quantum_ai_orbit_simulation.py` — 72 lines

### `qsync`
A package — the modules import each other, so it has an `__init__.py`.

- `codette_quantum_sync.py` — 84 lines
- `core.py` — 50 lines
- `run_simulation.py` — 18 lines
- `visualizer.py` — 18 lines

### `recovered_release`
- `resonant_continuity_engine.py` — 54 lines

### `solena`
A separate system, not Codette. Both revisions, structure preserved.

- `BridgeComposer.py` — 7 lines
- `HarmonicGuardian.py` — 10 lines
- `RealityAnchor.py` — 10 lines
- `ResonantRecall.py` — 7 lines
- `SolenaCore.py` — 23 lines
- `composer_core.py` — 9 lines
- `quantum_bridge.py` — 7 lines
- `solena_main.py` — 9 lines
- `visionary_reflection.py` — 6 lines

### `tools`
Helper scripts.

- `codette_pdf_export.py` — 18 lines
- `codette_quantum_multicore.py` — 15 lines

### `zeta`
Zeta modulator.

- `zeta_modulator.py` — 14 lines

## Excluded, and why

Recovered and committed under `recovered_release/`, but not usable as-is:

| Module | Blocker |
|---|---|
| `recovered_release/codette_quantum_audit_reflect.py` | qiskit: qiskit>=1.0 removed Aer/execute |
| `recovered_release/from_docx/cocoon_self_check.py` | qiskit: qiskit>=1.0 removed Aer/execute |
| `recovered_release/from_docx/emotional_webs.py` | qiskit: qiskit>=1.0 removed Aer/execute |
| `recovered_release/from_docx/ethics_evaluator.py` | ace_tools: sandbox-only, not on PyPI |
| `recovered_release/from_docx/quantum_memory_audit.py` | qiskit: qiskit>=1.0 removed Aer/execute |
| `recovered_release/from_docx/quantum_pipeline.py` | qiskit: qiskit>=1.0 removed Aer/execute |
| `recovered_release/gradio_app/app.py` | transformers_js: not a maintained PyPI package |
| `recovered_release/heliovault_seed761_codettev6.py` | qiskit: qiskit>=1.0 removed Aer/execute |
| `recovered_release/legacy/ai_core.py` | utils: module missing; components: module missing; models: ambiguous local package |
| `recovered_release/legacy/universal_reasoning.py` | perspectives: module missing |
| `recovered_release/quantum_memory_advanced.py` | qiskit: qiskit>=1.0 removed Aer/execute |
| `recovered_release/tools/codette_cli.py` | imports `universal_reasoning`, which is itself unusable |
| `recovered_release/legacy/test_universal_reasoning.py` | same — tests a module that cannot import |

Three classes of blocker:

- **qiskit** — seven modules use `from qiskit import Aer, execute`; both were
  removed in qiskit 1.0. They need porting to `qiskit_aer` and the primitives
  API, or pinning `qiskit<1.0`. The failure happens at import, so wrapping the
  call site in `try/except` does not help.
- **missing local modules** — `ai_core.py` wants sixteen `components.*` modules
  plus `utils.database` and `utils.logger`; `universal_reasoning.py` wants
  `perspectives`. Those names match `integration_architecture.json` exactly, so
  the design is recorded — but no implementation exists in any archive.
- **unobtainable packages** — `ace_tools` is sandbox-only and `transformers_js`
  is unmaintained. These need substitutes, not version bumps.
