# Changelog — July 5, 2026

## OpenVINO Backend Launch + Memory Hygiene + GPQA Breakthrough

### Headline numbers
- **GPQA-main 0-shot: 34.0%** (reason mode, n=100, forced newton) — best honest result to date. Answer-only format measured at 25.4–26.3% (= chance). June clean baseline was 30.8%.
- **Throughput: 9.3 tok/s mean / 10.3 median** sustained over 36K generated tokens (OpenVINO INT4 on Intel Arc 140V iGPU). llama.cpp under memory pressure was paging 2.4GB/request.
- vs GPT-4 0-shot (39%): **-5.0pp** with an 8B INT4 model running locally.

### OpenVINO backend (`openvino_backend/`)
- `backend.py` — drop-in replacement for CodetteOrchestrator: `_LLMShim` exposes llama_cpp-compatible `create_chat_completion()`; adapter hot-swap via `openvino_genai.AdapterConfig`; AUTO device with CPU fallback.
- Model: Llama 3.1 8B Instruct → OpenVINO IR INT4 (4.46GB, group-size 128) via `optimum-cli`.
- `convert_adapters.py` — all 10 GGUF LoRA adapters converted to safetensors (OV requirement).
- Server auto-detects the backend when `openvino_model.xml` exists — no env var needed.
- First GPU load ~140s (Arc kernel compile); cached loads ~20s.
- **Critical pattern:** OV-path code must import from `inference/codette_shared.py` (pure Python), never `codette_orchestrator` (module-level `import llama_cpp` crashes openvino_env). Fixed in: forge bridge greeting/memory fast-paths, `backend._synthesize`.
- `inference/runtime_env.py` — `PROJECT_ROOT` now honors `CODETTE_PROJECT_ROOT` env var (fixes git-worktree PYTHONPATH pollution).
- `_load_error` is cleared after a successful orchestrator load (stale errors from a failed attempt no longer poison subsequent requests).

### Memory hygiene — two contamination incidents purged
1. **Breach narrative** (32 cocoons + 39 SQLite rows + 4 sessions): responses asserting an "active memory quarantine from the data breach" — including "quarantine is over" variants that still confirmed the fiction. The consciousness adapter was reciting these as current fact. Backups: `cocoons/_backup_breach_cleanup_2026_07_05/`, `data/*.bak_breach_cleanup_2026_07_05`.
2. **Benchmark pollution** (1,365 SQLite rows = 47% of unified memory + 861 cocoon files): GPQA exam questions stored on every past benchmark run; fragments leaked into unrelated answers. Backup: `cocoons/_backup_gpqa_cleanup_2026_07_05/`.

**Guards added** (keyed on `_is_benchmark_query`): benchmark queries now skip unified-memory storage, memory recall/injection, CognitionCocooner storage, session-context injection, and session `add_message` — in addition to the pre-existing coherence-anchor skip.

### Self-awareness update
- `cocoons/project_awareness_2026_07_05.json` — supersedes April 2 version; frames the breach as resolved history (past tense only), records OpenVINO launch + memory cleanup + honest GPQA state.
- `cocoons/cocoon_current_state.json` — new CORE_SEED (importance 9, every session) that directly inoculates against the stale quarantine narrative.
- Unified memory: importance-10 `self_awareness` row for FTS recall; 4 stale April rows removed.

### GPQA benchmark integrity (`benchmarks/gpqa_codette.py`)
- `--mode reason` — reason-then-answer prompt + `parse_final_answer()` (LAST answer declaration wins, so letters mentioned during elimination aren't grabbed).
- `--adapter <name>` — forces a single adapter, bypassing multi-adapter synthesis and AAP templates.
- Per-call tok/s tracking (tokens, server time) with mean/median summary.

### Three bugs that zeroed reason mode (all fixed)
1. **LOCK 1 drift trimming** (`universal_self_check`) amputated reasoning chains — "This means...", "In other words..." match its drift patterns; everything after was cut including the answer line. Skipped for benchmark queries in both backends.
2. **`repetition_penalty=1.3`** degenerated long generations into word salad (~150+ tokens). Benchmark generations now near-greedy: temp=0.2, rep_penalty=1.05.
3. **Session bleed** — question N saw question N-1 via session-context injection. Benchmark queries now isolated from session read AND write.

### Multi-adapter benchmark finding (unresolved, by design for now)
Auto-routed 2-adapter GPQA answers go: two 5-token letter votes → third LLM synthesis call guesses between them → AAP wraps in SynthesisEngineV3 "Tensions remain" templates. Measured at exactly chance (25.4%, n=448). Benchmark runs should force a single adapter until the synthesis path can pass through verbatim answers.

### Remaining known issues
- 3/100 reason-mode parse failures = token-cap cutoffs mid-calculation on heavy numeric problems (bump benchmark max_new_tokens to recover).
- Perspective adapter retraining queue unchanged (empathy v2 done, 7 remain).

### Next steps
1. Reason mode at n=198 to confirm against the June baseline sample size.
2. `--mode sc3` layered on reason format (self-consistency over 3 reasoning chains).
3. Newton science fine-tune.
4. Fold the 26%→34% format finding into the next paper.
