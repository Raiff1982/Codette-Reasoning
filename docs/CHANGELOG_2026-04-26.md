# Changelog — 2026-04-26

This changelog records the April 26, 2026 quality and reliability wave.
Focus areas: concurrency safety, test coverage, ablation study for publication,
dependency hygiene, legacy module cleanup, and paper v7.

---

## Bug Fixes

### Session Race Condition (Critical)
- **File**: `inference/codette_server.py`
- **Problem**: `_get_active_session()` was called three separate times during
  one request (lines ~1098, ~1384, ~1572). A concurrent `/api/new_session`
  call between those reads could swap the global session, causing one request
  to read context from session A but write metrics to session B.
- **Fix**: Session captured once (`session = _get_active_session()`) at the
  top of request processing and reused throughout. The three duplicate calls
  were removed.

### Model Load Hang (High)
- **File**: `inference/codette_server.py`
- **Problem**: If the GGUF model path did not exist, the server would start
  successfully but hang indefinitely on the first request (lazy-load blocked
  waiting for a model that could never load). No error was surfaced to the UI.
- **Fix**:
  1. Path existence check added before attempting load — returns a clear error
     message immediately if the file is missing.
  2. `ThreadPoolExecutor` with a 5-minute timeout wraps the `CodetteOrchestrator`
     constructor — a corrupted or stalled GGUF now raises `RuntimeError` instead
     of hanging forever.

### Bare `except:` in Hallucination Guard
- **File**: `reasoning_forge/hallucination_guard.py:242`
- **Problem**: `except:` (no exception type) silently caught `KeyboardInterrupt`
  and `SystemExit` in addition to real parse errors.
- **Fix**: Narrowed to `except (ValueError, AttributeError, IndexError)`.

---

## Concurrency Hardening

### SQLite WAL Mode + Write Lock
- **File**: `reasoning_forge/unified_memory.py`
- **Changes**:
  - Enabled `PRAGMA journal_mode=WAL` on database open — readers no longer
    block writers and writers no longer block readers under concurrent load.
  - Set `PRAGMA synchronous=NORMAL` for a safe balance of durability vs speed.
  - Added `threading.Lock` (`self._write_lock`) wrapping all write operations
    (`store()`, `mark_success()`) — prevents concurrent writes from producing
    corrupted rows when multiple worker threads fire simultaneously.
  - Added `import threading` (was missing).

---

## Code Cleanup

### Removed Orphaned Memory Kernel
- **File removed**: `reasoning_forge/memory_kernel_local.py`
- A 150-line stripped-down duplicate of `memory_kernel.py`. Zero imports
  anywhere in the live codebase. `memory_kernel.py` (410 lines, with disk
  persistence, `EthicalAnchor`, type hints) is the canonical file.

### Fixed and Archived Legacy Entry Point
- **File fixed**: `consciousness/universal_reasoning.py`
  → **Moved to**: `archive/consciousness/universal_reasoning.py`
- This was an old standalone Azure Bot Framework entry point that predated
  the current server architecture. Fixed before archiving:
  - Removed unused `botbuilder` and `dialog_helper` imports (Azure Bot
    Framework, no longer in the system).
  - Replaced missing `perspectives` module with compatibility shims mapping
    old `*Perspective` API → current `reasoning_forge/agents/*Agent` classes.
  - `destroy_sensitive_data()` now overwrites bytearray data before `del`
    (reduces memory exposure window; Python strings are immutable so
    full zero-fill is not possible).
  - Hardcoded `https://api.example.com/data` URL made configurable via
    `config['real_time_data_url']`.
  - Added deprecation header documenting why the file is archived and where
    current equivalents live.

### Documented Code7eCQURE "Quantum" Framing
- **File**: `reasoning_forge/code7e_cqure.py`
- Added module-level docstring clarifying that "quantum" is a **metaphor**
  for stochastic multi-perspective reasoning, not quantum computing.
- Mechanism: named perspective functions apply labeled prefix transforms;
  `random()` and `random.choice()` simulate epistemic uncertainty and
  superposition of outcomes.
- Added inline comments on `quantum_spiderweb()` and `quantum_superposition()`.

---

## New Features

### Ablation Study Runner
- **File**: `benchmarks/ablation_study.py`
- `AblationRunner` class runs 5 experimental conditions, each disabling
  exactly one component from the full system:
  - `full` — all components active (baseline)
  - `no_memory` — cocoon recall disabled
  - `no_ethical` — ethical dimension weight zeroed
  - `no_sycophancy` — sycophancy guard pass skipped
  - `single_agent` — single perspective only (worst-case baseline)
- Reports mean composite score, drop from full, Cohen's d, and p-value per
  condition — ready for inclusion in the paper's ablation section.
- Saves JSON results to `benchmarks/results/ablation_results.json`.
- Run with: `python benchmarks/ablation_study.py`

---

## Test Coverage

### New: `tests/test_aegis.py`
Covers the full AEGIS ethical governance API:
- `evaluate()` — benign content passes, harmful content vetoed, all keys present
- Framework count (6 frameworks verified)
- EMA eta updates across multiple calls
- Veto count and total evaluation tracking
- `quick_check()` — safe content passes, harmful patterns blocked
- `alignment_trend()` — trend after benign vs. mixed inputs
- `to_dict()` / `from_dict()` serialization round-trip
- `get_state()` summary structure

### New: `tests/test_cocoon_synthesizer.py`
Covers the CocoonSynthesizer meta-cognitive engine:
- `extract_patterns()` — cross-domain detection, single-domain produces no
  cross-domain patterns, empty input, field structure validation
- `forge_strategy()` — returns `ReasoningStrategy`, references source patterns,
  default strategy on empty input, strategy history growth
- `apply_and_compare()` — returns `StrategyComparison`, improvement delta,
  readable output, dict serialization
- `run_full_synthesis()` — standalone mode, valuation context embedding,
  with live `UnifiedMemory` (temp DB)

### New: `tests/test_web_research.py`
Covers web research safety and fetch behaviour:
- `_is_safe_url()` — blocks localhost, loopback IPv4/v6, private ranges
  (10.x, 192.168.x, 172.16.x), link-local (169.254.x), file/ftp schemes,
  empty string, missing hostname
- `fetch_url_text()` — unsafe URL returns empty, safe URL returns text,
  network error returns empty, output capped at `max_chars`
- `search_web()` — empty/whitespace query, network error, timeout (all mocked)
- `query_requests_web_research()` — edge cases: lookup phrasing, vague short
  query, internal reflection phrasing
- `query_benefits_from_web_research()` — current events, price queries, static
  knowledge (no benefit), personal questions, recent release queries

---

## Dependencies

### `requirements.txt` — Version Pins Added
- Added upper-bound version constraints to all packages to prevent silent
  breaking changes from major version bumps:
  - `torch>=2.1.0,<3.0.0` (PyTorch 3.x not yet validated)
  - `transformers>=4.40.0,<5.0.0`
  - `peft>=0.10.0,<1.0.0`
  - `numpy>=1.24.0,<2.0.0`
  - etc.
- Added missing core dependencies: `llama-cpp-python`, `trl`, `datasets`,
  `accelerate`, `huggingface-hub`, `aiohttp`.
- Removed bloated/unused deps that were only needed by the archived
  `universal_reasoning.py`: `botbuilder`, `speech_recognition`, `PIL`,
  `nltk`, `numba`, `dataclasses-json`.
- Added comments clarifying which deps are optional (Gradio = demo only,
  vaderSentiment = legacy module only).

---

## .gitignore Updates

Added:
- `.claude/settings.local.json` — machine-specific Claude IDE settings
- `demo/outputs/*.mp4` — large demo recordings
- `*.mp4` — any video files

---

## Paper

- Added `paper/codette_paper_v7.tex` — updated paper with rebuttal changes
- Added `paper/rebuttal_changes.tex` — point-by-point rebuttal document
- Added `paper/tables/` — 10 formatted result tables
- Added `paper/codette_kaggle_notebook.ipynb` — Kaggle submission notebook
- Added `paper/kaggle_writeup.md` — Kaggle competition writeup
- Added `paper/benchmark_tasks/` — 17 individual benchmark task notebooks

---

## Commits This Wave

| Hash | Message |
|------|---------|
| `601d128` | Add benchmark results, paper v7, new reasoning modules, and training pipeline updates |
| `7bcd33d` | Fix session race, model load hang, SQLite concurrency, and add ablation study |
| `2fd8aed` | Fix and archive universal_reasoning.py; patch bare except; update .gitignore |
| *(this wave)* | Tests, README, CHANGELOG, requirements pins |
