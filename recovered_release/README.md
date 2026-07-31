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
