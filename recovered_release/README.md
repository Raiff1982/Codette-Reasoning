# Recovered release modules

Source recovered from the `Archive*.zip` uploads on `main` — specifically the
nested `codette_full_release.zip` (Archive 2) and `untitled folder 6`
(Archives 5 and 6). None of this had ever been committed to this repository in
any form; that was verified against the full commit history, not just the
working tree.

Nothing here is wired into `reasoning_forge`. It is committed so the work is
under version control and reviewable, not because it is integrated.

Archives 5 and 6 overlap heavily: 173 files, 115 unique. Duplicate ` 2` and
`(1)` copies were dropped.

## `optimization/`

A family of related optimisers, apparently successive revisions. All four are
self-contained (`numpy`, `matplotlib`, stdlib) and parse clean.

| File | Class | Notes |
|---|---|---|
| `quantum_optimizer.py` | `QuantumInspiredOptimizer` | single-objective; earliest |
| `multi_objective_optimizer.py` | `QuantumInspiredMultiObjectiveOptimizer` | |
| `multi_objective_optimizer_graph.py` | `QuantumInspiredMultiObjectiveOptimizer` | adds plotting |
| `ethical_mutation_filter.py` | `QuantumInspiredMultiObjectiveOptimizer`, `EthicalMutationFilter` | most developed |

Kept separate rather than merged: which revision supersedes which is the
author's call, and collapsing them would destroy that history.

## `legacy/`

**These do not import as-is.** Each depends on sibling modules absent from the
archive:

| File | Missing dependency |
|---|---|
| `universal_reasoning.py` | `perspectives` |
| `ai_core.py` | `components`, `utils` |
| `test_universal_reasoning.py` | imports `universal_reasoning` (upstream filename was `UniversalReasoning.py` — the case differs) |

`reasoning_forge/perspective_registry.py` records its origin as
`universal_reasoning.py`, but the two share **no symbols** — the registry was
rebuilt conceptually, not copied. So `universal_reasoning.py` still holds
distinct code (`CustomRecognizer`, `RecognizerResult`, `Element`,
`analyze_question`, `execute_defense_function`) found nowhere else here.

## `solena/`

**A different system, not Codette.** "Solena" appears nowhere else in this
repository. Both revisions are preserved:

- `original/` — `solena_main.py`, `composer_core.py`, `quantum_bridge.py`,
  `visionary_reflection.py`, `identity.yaml`
- `refactored/` — `SolenaCore.py`, `RealityAnchor.py`, `HarmonicGuardian.py`,
  `BridgeComposer.py`, `ResonantRecall.py`

Small modules (5–22 lines each); a scaffold rather than a finished system.

## Loose modules

- `codette_quantum_audit_reflect.py` — cocoon audit pass; `quantum_select_node`
  variant of the selection used in `ethics/core_guardian_spindle_v2.py`
- `quantum_memory_advanced.py` — same lineage as `core_guardian_spindle_v2.py`
  but neither is a superset: this one has logger setup and a `try/except`
  fallback around the qiskit call, while the repository's has `sanitize_url`
- `heliovault_seed761_codettev6.py` — a `CoreConscience` variant adding
  `quantum_walk`

Note: all three call `from qiskit import Aer, execute`, removed in qiskit >= 1.0.
They will not import against a current qiskit.

## Deliberately not taken

- `core_guardian_spindle.py` (Archives 5/6) — the v1 ancestor of
  `ethics/core_guardian_spindle_v2.py`, identical symbol set; redundant
- `cognition_cocooner.py` (Archive 2) — 71 lines against the repository's 338
- `universal_reasoning_clean.py` — a two-line placeholder

## Related, filed elsewhere

- `experiments/quantum_cosmic_multicore.py` — extracted from inside
  `QuantumCosmicMulticore.md`, where the script was embedded in the prose
- `experiments/codette_quantum_multicore2.py` — executes three calls at import
- `experiments/codette_meta_3d.py` — the `CodetteMeta3D` referenced by
  `integration_architecture.json`
- `experiments/codette_timeline_animation.py`
- `paper/citizen_science_quantum_chaos.tex` — recovered from a file named
  `Codette` with no extension
- `paper/codette_quantum_module.tex`, `paper/QuantumAI.bib`
- `recovered_release/cocoons/quantum_space_trial_*.cocoon` — recorded quantum
  and chaos state vectors from `quantum_space_trial` runs. Both have
  `stardust_input.pl_hostname` set to `"unknown"`, so no star was resolved on
  these particular runs. Kept here rather than in `cocoons/`, which .gitignore
  reserves for runtime state.
- `consciousness/colleen_identity_seed.txt`
- `dotnet/BotWebApp/` — an ASP.NET Core application whose source was stored in
  `new 3.txt`, `new 5.txt`, `new 10.txt`, `new 14.txt`, `new 16.txt`,
  `new 20.txt`. **Never compiled** — no .NET SDK was available during recovery.

---

# Second pass — `untitled folder 3.zip`

183 files, 20 MB, heavily nested (zips inside zips, three levels deep). 385
files after recursive unpacking, 170 unique by content.

The archive ships `Codette_Core_Universal_Files_checksums.txt`. All three
SHA-256 checksums were **verified** against the extracted parts — the archive is
intact.

## `foundations/`

`codette_deep_simulation_v1.py` — **this is the file
`reasoning_forge/memory_kernel.py` cites in its docstring as "Mathematical
foundation", and it had never been in this repository.**

It is real, correctly-implemented math, not notation:

- `von_neumann_entropy` — `-Σ λ log λ` over the positive eigenvalues of the
  density matrix
- `information_energy_duality` — `ℏω + η·S`, using the actual reduced Planck
  constant (1.054571817e-34)
- `dynamic_resonance_windowing` — windowed Fourier transform by trapezoidal
  integration
- `reinforced_intent_modulation`, `nonlinear_dream_coupling`,
  `cocoon_stability_field`

`paper/codette_research_equations.txt` states the same relations in LaTeX, and
`experiments/codette_deep_simulation_v1.ipynb` is the accompanying notebook
(5 cells).

## Other new modules

| Path | Contents |
|---|---|
| `orbital/` | `quantum_ai_orbit.py`, `quantum_ai_orbit_simulation.py` |
| `qsync/` | `codette_quantum_sync.py` plus the `codette_qsync` package (`core`, `run_simulation`, `visualizer`) |
| `zeta/` | `zeta_modulator.py` and its computed `zeta_equilibrium_solution.json` |
| `einstein_rosen/` | `biofield_bridge.py`, `timeline_selector.py` |
| `tools/` | `codette_cli.py`, `codette_pdf_export.py`, `codette_quantum_multicore.py` |
| `resonant_continuity_engine.py` | continuity engine |

## `schemas/`

Two OpenAI-style tool schemas that were stored as `.txt`:

- `codettes_tool_schema.json` — valid JSON
- `codette_universal_reasoning_schema.json.truncated` — **truncated mid-object**
  at character 2176. Kept with the `.truncated` suffix so it is not mistaken for
  loadable config.

## Extraction damage repaired

The four `codette_memory_kernel*.py` variants had `\n` escapes inside f-strings
converted into real newlines, splitting the literals across lines so none of
them parsed. Re-escaping and rejoining recovered all four, revealing a clean
progression: `MemoryCocoon` + `LivingMemoryKernel` (64 lines) → `WisdomModule`
(96) → `DynamicMemoryEngine` (116) → `ReflectionJournal` (147).

**None were taken.** `reasoning_forge/memory_kernel.py` (487 lines) is already a
superset of the largest variant and adds `EthicalAnchor`. They were repaired
only to confirm that.

Also skipped as already present or superseded: `SolenaAI` (both revisions, taken
in the first pass), `cognition_cocooner.py`, `universal_reasoning_clean.py`, and
a 27-line `universal_reasoning.py` stub distinct from the 255-line version in
`legacy/`.

---

# Third pass — code stored inside Word documents

Across all archives, **43 unique `.docx` files contain Python source**, not
prose. They were invisible to every earlier sweep because those looked at file
extensions. The filenames do not describe the contents: `balls.docx`,
`podbay.docx`, `readyplayer1.docx`, `whattowwtchoutfor1.docx`, `6 copy.docx`.

Of the 43, ten hold code found nowhere else in this repository. They are in
`from_docx/`, renamed for what they actually do, with the original filename
recorded in each module docstring.

| Module | Recovered from | Defines |
|---|---|---|
| `quantum_pipeline.py` | `allforone.docx` | `codette_quantum_pipeline`, `codette_spiderweb_synthesis`, `funnel_to_webs`, `quantum_walk_web` |
| `emotional_webs.py` | `balls.docx` | `build_emotional_webs`, `run_quantum_spiderweb` |
| `spiderweb_nodes.py` | `Document (12) copy.docx` | `SpiderNode`, `TensionSpike` |
| `cocoon_self_check.py` | `conpleteweb.docx` | `self_check_cocoon` |
| `genomic_codette_ai.py` | `Document626.docx` | `GenomicCodetteAI` and its agent functions |
| `codette_heart.py` | `heart2.docx` | `CodetteHeart` (distinct from `CodetteQuantumHeart`) |
| `advanced_codette_ai.py` | `cleanup.docx` | `AdvancedCodetteAI` — multi-agent null repair, recursion control |
| `ethics_evaluator.py` | `Documenttestrun.docx` | `evaluate_ethics` |
| `quantum_memory_audit.py` | `adit2.docx` | `quantum_memory_audit` |
| `quantum_nightmare_echo.py` | `6 copy.docx` | `QuantumNightmareEcho`, `NightmareSimulator`, `EchoPulse`, `CollapseDetected` |

The other 33 duplicate material already recovered — `error1`, `harmonics1`,
`heart`, `memory1`, `qbert`, `head`, `testing1`, and so on — or are alternate
drafts of each other (`readyplayer1` = `cleanup`, `randomfakecodeagain` =
`error1`, `universalweb` = `headbox2`, `Documenttest` = `Documenteorkw`).

## Damage patterns found in this pass

Four documents needed repair beyond the usual glyph substitution:

- **Trailing prose appended to source.** `cleanup.docx` and `readyplayer1.docx`
  end with narrative after the last code line. Recovered by keeping the longest
  parsing prefix — 61 of 63 lines, and 54 of 56.
- **Fenced blocks inside narrative.** `copilotsweb.docx` is prose wrapping three
  fenced blocks; only the `python` one is source.
- **Non-breaking spaces (U+00A0) and smart quotes** used where ASCII was meant.

`Document (14).docx` was reclassified out of the code set entirely: it is a
system prompt, not source.
