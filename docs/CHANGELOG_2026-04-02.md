# Changelog — 2026-04-02

This changelog records the April 2, 2026 enhancement wave focused on reliability,
continuity, transparency, portability, and safer current-facts retrieval.

## Core Runtime

- Added a portable runtime bootstrap layer so launch and import behavior no longer depends on one hardcoded machine layout.
- Kept the two web launch paths intact:
  - `scripts\codette_web.bat` for the local `llama_cpp` path
  - `scripts\codette_web_ollama.bat` for the Ollama path
- Updated the launchers to resolve the project root and Python environment relative to the repo instead of fixed `J:\...` locations.

## Memory And Continuity

- Unified more of the runtime around the SQLite cocoon store in `reasoning_forge/unified_memory.py`.
- Added `active_continuity_summary` to the live session layer so long conversations keep a compact working-memory thread.
- Added `decision_landmarks` so important user constraints and assistant commitments become durable recall points instead of getting lost in raw chat history.
- Persisted value analyses and web research as searchable cocoon memory, not one-off calculations.

## Reasoning And Valuation

- Added singularity-aware Event-Embedded Value analysis with interval/event separation, singularity handling modes, AEGIS modulation, and risk-frontier comparison.
- Added valuation-aware cocoon synthesis so `/api/synthesize` can reason directly with event-weighted harm models.
- Added persistence and recall for both value-analysis runs and risk-frontier runs.

## Safety, Confidence, And Loop Resistance

- Integrated confidence and hallucination analysis into the normal chat path.
- Promoted trust tags in the UI so users can see signals such as `memory-backed`, `frontier-informed`, `web-cited`, and `low-verification`.
- Hardened threaded request/session handling in the server to reduce race-condition-style confusion.
- Fixed the self-diagnostic loop trigger by making the bridge inspect the raw user query instead of the fully enriched prompt.
- Tightened diagnostic and introspection triggers so ordinary phrases like `everything ok?` and `status report on this file` do not accidentally enter report mode.

## Tooling Hardening

- Tightened auto-tool triggers in the orchestrator so normal chat is less likely to drift into code/tool mode.
- Replaced the weak string blacklist in `inference/codette_tools.py` with AST-based validation and isolated execution for `run_python()`.
- Fixed package-safe runtime environment imports in the tool layer.
- Clarified that local tools search the workspace and codebase; they are not live web browsing.

## Web Research

- Added a safe, explicit web research path in `inference/web_search.py`.
- Web research is opt-in from the web UI.
- Safe fetch rules now block localhost/private targets, cap page size, and extract plain text only.
- Retrieved web findings can be stored as `web_research` cocoons and reused on future similar queries.
- Web research now returns citations and trust-tag visibility in chat responses.

## Documentation And Transparency

- Updated `README.md` and `docs/HOWTO.md` to document:
  - launcher behavior
  - opt-in web research
  - continuity summaries
  - decision landmarks
  - gated system reports
  - trust tags
- Updated deployment docs to reflect the current launcher paths and runtime behavior:
  - `docs/deployment/PHASE7_WEB_LAUNCH_GUIDE.md`
  - `docs/deployment/SELF_HOST_CODETTE.md`
  - `docs/deployment/PRODUCTION_READY.md`
  - `docs/deployment/LAUNCH_COMPLETE.md`

## Benchmarking

- Added a new live runtime benchmark in `benchmarks/codette_runtime_benchmark.py`.
- This complements the older publishable reasoning benchmark by measuring Codette-specific runtime behavior:
  - grounded correctness
  - continuity retention
  - governance stability
  - valuation reasoning
  - optional cited web research and research-memory reuse
- Added focused unit coverage for the new benchmark helpers in `tests/test_codette_runtime_benchmark.py`.

Run it with:

```bash
python benchmarks/codette_runtime_benchmark.py
python benchmarks/codette_runtime_benchmark.py --include-web
```

Reports are written to `data/results/`.
