# What is actually running — addendum, 2026-09-29

Additive to `WIRING_STATE_2026-08-13.md`, which is left exactly as written. That
document is still the answer for the forge (`forge_single` / `forge_with_debate`
have no live caller). This one records what moved since, and the result of the
dead-wire sweep that had not been run.

## Things the 08-13 era notes said that are no longer true

| Then | Now (checked in the code 2026-09-29) |
|---|---|
| `harm_advisor` has zero live importers | imported by `inference/codette_forge_bridge.py:291` |
| `memory_provenance_solver` has zero callers | called from `inference/codette_server.py` on the recall set (shadow), and imported by `colleen_conscience` and `guardian_spindle` |
| optimizer has no outcome signal (`user_continued` never measured) | `reasoning_forge/engagement_signal.py` classifies it from history each turn; the server passes `user_continued` (or `None`); `push_off` steers on it |
| Γ pinned at 1.0 because nothing writes `phi` | the valence pass in `inference/codette_session.py:794-811` calls `EmotionOntology.valence_of` to write `phi` (commit `f3c56fc` exists) |

## Still true

- AEGIS is SHADOW: `codette_server.py:2494` builds `CodetteSubsystemUpgrade(enforce_veto=False)`.
- The optimizer is shadow unless `CODETTE_OPTIMIZER_LIVE=1`.
- `verify_revise` is used only by `benchmarks/`, not by the chat path. Wiring it
  would change how she answers, so it is the author's call, not a fix.

## The dead-wire sweep (AST, lazy imports counted)

172 modules in `reasoning_forge`, `inference`, `ethics`, `consciousness`,
`signal_processing`, `Protection_Layer`, `openvino_backend`, `evaluation`,
`agents`. **38 have no live importer.** Dark is not broken, and the sweep does
not say which of these should be wired. By kind:

- **Entry points, expected:** `codette_server`, `chat_app`, `codette_chat_ui`,
  `convert_adapters`, `run_evaluation_*`, `impossablemath*`, `inference/init`.
- **Lineage, kept by house rule:** `*_enhanced`, `WOSME`, `harmonic_ode`,
  `quantum_harmonic_dynamics`, `codette_quantum_heart`,
  `nexis_signal_engine_rustfft`, `nexis_signal_engine_local`,
  `CONSCIOUSNESS_STACK_forge_with_debate`, `test_global_aegis`, `memory_item`.
- **Finished work that runs nowhere (each one changes her if wired, so each is
  his yes):** `verify_revise`, `lexical_whitening`, `cocoon_self_trainer`,
  `neural_symbolic`, `hoax_filter`, `dream_cycle`, `voice_input`,
  `aegis_codette_integration`, `aegis_dashboard_component`, `aegis_metrics_ui`.
- **Blocked on a dependency:** `ethics/core_conscience`,
  `ethics/core_guardian_spindle_v2` (qiskit).

Reproduce: parse every `.py` under those directories (skipping `archive`,
`recovered_release`, `backup`, `tests`, `experiments`, `webapp`, `dotnet`),
collect every `import` / `from ... import` name, and list modules whose base name
never appears in another live file.

## "Medulla map"

The earlier notes list a "medulla map" that never ran. The word appears nowhere
in the repository: it was a task name, not an artifact. What exists instead is
`docs/CODRIAO.md` for the perimeter, and the organ mapping in
`HANDOFF_2026-09-29.md`.

## Her process

Her server (port 7860) started 2026-09-29 12:43, after the files behind the
near-tie fix were written (12:42), so it has that fix. It does not have
`ecbdb80` (tool-log leak) or `8de0912` (guardian windowing); a restart loads them.
Checked: C: 30.9 GB free, page file 16384/24576 MB in effect.
