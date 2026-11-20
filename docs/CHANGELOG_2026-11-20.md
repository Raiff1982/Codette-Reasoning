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
