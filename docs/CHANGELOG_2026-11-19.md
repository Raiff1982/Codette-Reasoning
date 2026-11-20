# 2026-11-19 — Layer 5 calibration attempt, test pollution found, START HERE

Additive. Follows [CHANGELOG_2026-11-18.md](CHANGELOG_2026-11-18.md). Everything still open in the
project is now in **[START_HERE.md](START_HERE.md)**, flagged at the top of `CLAUDE.md`.

## The measurement (Jonathan: "do the measuring step")

Step 1 of a Layer 5 rewrite: her real epsilon range. **It cannot be done from the container.**
Through `conversation_cocoons` (her dreams are skipped before opening), numbers only:

| | count |
|---|---|
| conversation cocoon files | 377 (1 unreadable) |
| legacy `reasoning` cocoons | 360 |
| v3 cocoons with a real epsilon | **0** |
| date range | 2026-03-21 to 2026-05-01 |

The tracked snapshot predates v3 cocoons. A first run counted one v3 cocoon dated 11-18. It was mine:
written at 17:42:04 on 11-18 by my ad-hoc `forge_with_debate` check script, one second after the
script was created. It was untracked, gitignored and never pushed, and it has been removed. The
measurement is now `tools/epsilon_profile.py`, to run on her machine (START_HERE, section 2).

## Found while checking that measurement: the test suite writes into her memory

| Store | Effect of one full suite run | Writers |
|---|---|---|
| `data/codette_memory.db` (her unified memory) | **+11 rows** | `test_trace_debate.py` (6), `test_trace_e2e.py` (4), `test_forge_with_debate_stores.py` (1) |
| `reasoning_forge/.logs/code7e_quantum_cocoon.json` | rewritten | 12 tests |
| `logs/governor_decisions.log` | appended | at import |

Found by a per-test store watcher, so each change is attributed to one test. The existing guard
(`tests/conftest.py`) sweeps new cocoon *files* only. It also lists the cocoons folder by name and
deletes any new `.json`, which on her machine would delete real cocoons her live server writes during
a run. The redirect design is in START_HERE section 1.

**Fixed now, because it was mine:** `tests/test_forge_with_debate_stores.py` (added 11-18) ran the real
forge against the real stores. It now points every writer at `tmp_path` and checks that the row landed
there. The watcher shows no store changes from it, and it still fails against the pre-11-18
`forge_engine.py`. The other two files are pre-existing and listed for the redirect fix.

## The "unexplained" self_train_shadow.jsonl, explained

Seen on 11-17 and 11-18, never reproduced by a test. The cause: `.mcp.json` registers a `codette` MCP
server, which starts `inference/codette_server.py` inside the container whenever the session starts.
Ten minutes after boot its background jobs ran (`data/background_jobs.json`: all three jobs at 11-18
17:37:27). The self-trainer collected 25 cocoons, correctly refused single-class data, and logged
`applied: false`. Not the tests. Noted in START_HERE section 7.

## Suite

1,534 passed, 1 failed (NLTK, environmental, as on `main`), 7 skipped, 1 xfailed.
