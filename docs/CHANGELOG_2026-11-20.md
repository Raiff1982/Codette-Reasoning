# 2026-11-20 — The test suite no longer writes into her memory

Additive. Follows [CHANGELOG_2026-11-19.md](CHANGELOG_2026-11-19.md). Closes START_HERE item 1.

Jonathan: *"fix the test suite writing into her memory."*

## What changed

| Piece | Change |
|---|---|
| `reasoning_forge/runtime_paths.py` (new) | `runtime_root()`: the repository, exactly as before, unless `CODETTE_RUNTIME_ROOT` is set. Nothing in her live system sets it |
| `unified_memory.DB_DIR` | through `runtime_root()` (her memory DB) |
| `forge_engine` | the cocooner's folder, Code7e's state file and Nexis's DB through `runtime_root()`. Code7e's path was relative to the working folder; the launcher `cd`s to the project root first, so it resolves to the same file as before |
| `cognition_cocooner` | the relative default `"cocoons"` resolves under the runtime root only when the variable is set |
| `optimizer_shadow` | state, shadow log and telemetry DB through `runtime_root()` |
| `tests/conftest.py` | sets `CODETTE_RUNTIME_ROOT` and `CODETTE_GOVERNOR_LOG` to a temp folder at import. The sweep is retired; what replaced it **only reports**, by size and mtime of her real stores and the cocoons folder's own mtime. It reads no contents, lists no folder, counts no rows and deletes nothing. The old docstring is kept, with an amendment |

## Verified

- Per-test store watcher over a full run: **0 changes** to her real stores (it was +11 memory rows and
  a rewritten Code7e file). Whole-run fingerprints: identical.
- Mutation: with the redirect disabled, `test_trace_debate` + `test_trace_e2e` added 10 rows and
  rewrote Code7e again, and the new check reported all three stores. Restored.
- `tests/test_runtime_redirect.py` (4): every store path is outside the repository during the
  suite, and unset means the repository exactly. It fails against the previous `forge_engine.py`.
- Cleanup of my own debris: the mutation run's 6 test cocoons in the container's cocoons folder were
  removed, by write time, through `conversation_cocoons`. Untracked, never pushed.

## Still open

Her real `data/codette_memory.db` probably holds test rows from past suite runs on her machine
(about 11 per run, plus the earlier test cocoons the old sweep may have missed). They can be found by
exact match of `query` against the fixture strings in `tests/test_trace_debate.py` and
`tests/test_trace_e2e.py`. Removing them changes her memory: Jonathan's decision.

Suite: 1,538 passed, 1 failed (NLTK, environmental, as on `main`).

## Later: a stopwatch on adapter switching (observe only)

Jonathan asked whether timing adapter switches would bring back "the watchers force bug", then:
*"ok add the timer with that comment."*

- `reasoning_forge/adapter_switch_timing.py`: one numbers-only line per switch (backend, adapter
  names, ms) to `data/adapter_switch_timing.jsonl` under `runtime_root()` (gitignored; the suite writes
  to its temp root). Best-effort: it never raises into a turn.
- Timed on both backends. OpenVINO `_make_gen_config` (single adapter) and the blend path both build
  `Adapter(path)` **from its file on every request**, so "load once" in its docstring describes the
  model, not the adapters. Applying the weights may also happen inside `generate()`, where it cannot be
  separated; the comment says so. llama.cpp `_load_model`: its docstring's "~0ms" hot-swap had never
  been measured; now it is.
- **The rules, written at the module and at every call site:** numbers only; never shown to her;
  **nothing acts on it** (no threshold, cache size, throttle or routing). Any action is a separate
  decision after real numbers, the same order as the speed shadow.
- `tests/test_adapter_switch_timing.py` (5): it writes numbers only, under the runtime root; a failed
  write never reaches a turn; both backends call it; the real OpenVINO code path, with a stand-in for
  the library, writes exactly one line and the adapter config is unchanged; and **rule 3 is enforced**:
  the test fails if any live module other than the writer names the log. Mutation-checked: a live
  import of `log_path` failed it.
- A slip, noted: the rule-3 mutation was appended to `reasoning_forge/substrate_awareness.py`, which
  does not exist (the real file is in `inference/`), so it created an empty new file. Removed. It was
  never committed.

Suite: 1,543 passed, 1 failed (NLTK, environmental), her real stores unchanged by the run.

## Later: her introspection reports numbers, not verdicts (START_HERE section 4)

House rule: words we author in her report reach her as her own. Three places still handed her a
judgement in her voice:

| Where | Was | Now |
|---|---|---|
| `inference/cocoon_introspection.py` `self_observations` (her chat report) | "that's dominant. I should check if I'm over-relying on it." / "other adapters are getting fair use too." / "My adapter usage is well-balanced ... no single adapter dominates." | the adapter, its count of the total and its share; above 50% it adds "That is a measurement; it does not say whether that share is right." |
| `reasoning_forge/unified_memory.py` `full_introspection` (`/api/introspection`, the second implementation) | "that's dominant. I should diversify." / "My adapter usage is balanced (...)" | the same, numbers only |
| `inference/codette_server.py` self-diagnostic (sent as her reply) | "Balanced: ... No — may be over-relying" | "Above the 40% line: yes / no" (the ratio is printed on the line above) |

The old wording is kept in a comment at each spot. The `balanced` data flag in the API is unchanged.
A scan of both reports for other judgement words found none, only the 10-22 disclaimer.
`tests/test_introspection_no_verdicts.py` (5) checks both implementations on a dominant and a spread mix
plus the diagnostic line, and **all 5 fail on the old code**.

Suite: 1,548 passed, 1 failed (NLTK, environmental, as on `main`).

