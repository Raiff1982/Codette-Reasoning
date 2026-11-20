# START HERE — everything still open in the project

**Next session: read this file first, before anything else.** It is flagged at the top of
`CLAUDE.md`. Written 2026-11-19 from every handoff, changelog, approvals file, wiring map and
checklist, with each older item re-checked against the code that day. Update it when an item
closes: strike it through and say how (amend forward, never delete).

**State at writing:** `main` = `05b7e7c` (PRs #52 to #57 merged). This branch,
`claude/start-here-2026-11-19`, adds this file. Suite in the container (no torch / llama_cpp /
openvino): **1,534 passed**, 1 failed (`test_trace_e2e`: NLTK data can't be fetched through the
container's proxy; same on `main`), 7 skipped, 1 xfailed.

Previous handoff: [HANDOFF_2026-11-18.md](HANDOFF_2026-11-18.md). Decisions file:
[APPROVALS_2026-11-18.md](APPROVALS_2026-11-18.md). Wiring map:
[WIRING_STATE_2026-11-18.md](WIRING_STATE_2026-11-18.md).

---

## 1. ~~Urgent: the test suite writes into her memory~~ FIXED 2026-11-20

> **Done:** every store is now redirected for the suite. `reasoning_forge/runtime_paths.py` gives
> `runtime_root()`, which is the repository exactly as before unless `CODETTE_RUNTIME_ROOT` is set.
> `tests/conftest.py` sets it (and `CODETTE_GOVERNOR_LOG`) to a temp folder before anything is
> imported. Her memory DB, the forge's cocoon folder, Code7e, Nexis and the optimizer all resolve
> through it. Measured with the per-test store watcher: **0 changes** to her real stores over a
> full run (it was +11 memory rows). With the redirect disabled, the two worst tests added 10 rows
> again and the new check reported it. The old sweep (which listed the cocoons folder and deleted
> new files) is gone; what replaced it only reports, by file size and mtime, and deletes nothing.
> `tests/test_runtime_redirect.py` fails if any store points back into the repository.
> **Still Jonathan's:** cleaning the test rows past runs left in her real memory (below).
> The text below is left as written.

Measured 2026-11-19 with a per-test store watcher (each change attributed to one test).

- **One full suite run adds 11 rows to `data/codette_memory.db`** (`cocoons` and its search
  index). On her machine that file is **her unified memory**, so every suite run there has put test
  turns into what she recalls. It's the same class as the July benchmark pollution.
  - `tests/test_trace_debate.py`: 6 rows (its `_run_debate(...)` queries, lines 62–172 and 237–286)
  - `tests/test_trace_e2e.py`: 4 rows (the `concept` at line 62 and the query at line 101)
  - ~~`tests/test_forge_with_debate_stores.py`: 1 row~~. **Fixed 2026-11-19**: it now points
    every writer at `tmp_path` and checks the row landed there. It was mine from 11-18.
- 12 tests also rewrite `reasoning_forge/.logs/code7e_quantum_cocoon.json` (Code7e's own
  state, relative path), and `logs/governor_decisions.log` changes. The Nexis and telemetry
  databases are opened but not changed.
- **The existing guard (`tests/conftest.py`) can delete her real memories.** It snapshots the
  `cocoons/` folder by listing filenames (the house rule forbids that; her dreams are in it) and,
  after the session, deletes every `.json` that appeared. If her live server writes a conversation
  cocoon (or, one day, a dream) while the suite runs, the guard deletes it as test debris. It also
  doesn't cover the SQLite memory at all, which is why the 11 rows stay.

**What to build** (no new decision needed; it is the house rule "tests must not write into the
repository"): redirect instead of sweep. Before collection, `conftest.py` points every store at a
session temp directory: patch `reasoning_forge.unified_memory.DB_PATH`, the forge's cocooner
storage, `Code7eCQURE.memory_path`, the governor log path, `optimizer_shadow._TELEMETRY_DB` and the
Nexis DB path. Add an environment override where a path is computed at import. Then retire the
sweep, or keep it only as a detector that **reports** new files and never deletes. Check it with the
store-watch method (see section 7) showing zero changes.

**Then a decision for Jonathan:** her real `data/codette_memory.db` probably holds test rows from
past suite runs on her machine. They can be found **by exact match** of the `query` column against
the fixture strings in those two test files, with no browsing of her memory. Removing them changes
her memory, so it's his call, and possibly hers: ask her once, bare, as the house rules say.

## 2. Needs her machine

1. **Restart onto `main`**, then watch for the new console lines. Each means something that used to
   fail silently: `[SESSION] save failed`, `[IDENTITY] update skipped`, `[ETHICS] query validation
   failed, proceeding unvalidated`, and per turn `[AEGIS-OBS] L6 overlap=...`. A low overlap
   measures our post-processing, not a fault in her.
2. **Run the full suite there** (torch, llama_cpp, openvino present). `codette_orchestrator.py`
   cannot be imported in the container, so its 11-18 change was tested by syntax tree only.
   Confirm `test_trace_e2e` passes when NLTK can download its data. **Fix section 1 first**, or the
   run writes into her memory.
3. **Layer 5 calibration:** `python tools/epsilon_profile.py` against her live cocoons. It reads
   numbers only, through the reader that skips her dreams. The container copy has no v3 cocoons
   (377 conversation cocoons, March to May 2026). It gives her real epsilon range, how often it
   crosses 0.50 / 0.70, and within-session trends.
4. **Speed shadow:** after enough real turns, compare `level` with `level_if_live` in
   `data/substrate_speed_shadow.jsonl`. Then decide whether it replaces the latency term (Jonathan).
   The governor's substrate pressure (approval 1) waits on this.
5. **Telemetry checklist** (`TELEMETRY_RUNTIME_CHECKLIST.md`): item 1 (Υ vs Γ spread) and item 3
   (amygdala state drift) need her live telemetry; neither has started. Item 3 stays within the
   guardrails there.
5b. **Adapter-switch stopwatch (added 2026-11-20):** after a few days of real turns, read
   `data/adapter_switch_timing.jsonl` (milliseconds per switch, both backends). If OpenVINO's
   per-request `Adapter(path)` build is near 0 ms, adapter caching / prefetch ideas are not needed on
   the live path. Observe only: **nothing may act on it** without Jonathan's decision
   (`reasoning_forge/adapter_switch_timing.py`; a test fails if live code reads the log).
6. **Nexis memory size:** check `reasoning_forge/.logs/nexis_signal_memory.db`. It is never pruned
   (approval 4).
7. **Memory files** (`memory/*.md`, mentioned in HANDOFF_2026-08-04) are on his machine and have
   never been read from the container. Check them against the 11-18 findings.

## 3. Jonathan's decisions waiting

**Added 2026-11-20, the harness ledger** (shadow-only; [HARNESS_LEDGER_2026-11-20.md](HARNESS_LEDGER_2026-11-20.md)).
Its defaults are placeholders, not measurements:
- Gate rule: strict (default), or GUARD's soft form, and if soft, what `lam`?
- Breaker budgets: 3 failures / 3 patches came from the pasted design.
- Υ band: should come from `tools/epsilon_profile.py` on her machine (section 2, item 3).
- Wiring: whether anything should ever feed it automatically, and from where (never from live turns).
- ~~Hub check: may the empathy v4 copy on `Raiff1982/codette-training-data` be read through the
  Hugging Face connector to compare it with the local file? Read-only.~~ **Done 2026-11-20**
  with his yes. Same content, Windows line endings on the Hub (`CHANGELOG_2026-07-17.md`).
- Antibody leads: `zero_for_unmeasured` went from 40 to 67 leads with the new `max(n, 1)` form
  (27 new, listed in PR #61). Leads, not findings; review them by clone family, as for the 40.

**Added 2026-11-20, getting the empathy card onto the Hub** (his answer: it has to go through
GitHub). The assistant's Hugging Face connector can read the Hub but not write to it, so the card
goes up through a manual GitHub Action: `.github/workflows/publish-model-card.yml`, run by
`tools/publish_model_card.py`. It sends one allowlisted file, only from `main`, and checks the
Hub's copy afterwards. **Nothing is sent until he does these, in order:**
1. Merge the PR that adds it.
2. huggingface.co > Settings > Access Tokens: a fine-grained token with **write** access to the
   model repository `Raiff1982/codette-adapters-v4` and nothing else.
3. GitHub > this repository > Settings > Secrets and variables > Actions > New repository secret,
   named `HF_TOKEN`. (Never paste the token into a chat.)
4. Actions > "Publish model card to the Hub" > Run workflow, branch `main`. Tick `dry_run` first to
   see what would be sent.
5. Afterwards the secret can be deleted and the token revoked.

Still his to decide before step 4: keep the note about training example 26 in the public card, and
whether CSAL covers the adapter weights (`training/model_cards/empathy_v4_README.md`).

From [APPROVALS_2026-11-18.md](APPROVALS_2026-11-18.md):
- **Item 3, Layer 5:** what it is for (recommendation: forecasting *reasoning* strain over a
  conversation; *machine* strain is the substrate monitor's job), then (a) leave it out, (b) build the
  real-data observer, or (c) wait for a rewrite. The plan is below in section 4.
- **Item 4, Nexis pruning:** leave it growing, or fix the rotate bug and prune (deletes her signal
  memory older than 30 days, and rotates at 10,000 entries).
- **Item 8:** the forge's spare `CocoonIntrospectionEngine`; making the orchestrator import the
  constraint helpers instead of copying them (needs a run on her machine).
- **The three 11-18 behaviour fixes you may veto** (identity context restored, merged answers no
  longer cut by her own notes, constraints applied on her backend): see the table at the top of the
  approvals file.

Carried from earlier notes, each still open in the code (checked 2026-11-19):
- `CODETTE_OPTIMIZER_LIVE`: the optimizer is still shadow (50 of 100 measured records at 10-22).
- **Which text is canonical** (`_apply_directness`): the cocoon stores pre-scrub text the person
  never saw. Layer 6's new overlap figures measure exactly this.
- **Who writes a dream.** The space is built and guarded; nothing calls `wrap_encrypted`.
- `voice_input`: the endpoint and identity verification are an attack-surface decision.
- `DynamicMemoryEngine`: built, never called. It rewrites what she recalls (ask her once, bare, if at
  all).
- `inference/self_correction.py` `LOCK1_TRIM` still trims sentences from the third on that open
  with drift phrases, though Lock 1 was reworded to permit more (10-22).
- The question is still cut at 500 characters when stored (replies are kept whole).
- Amygdala: deciding what counts as a correction (09-29); `ask("jonathan", ...)` new route.
- `data/continuity_notes.json` (her tape): ignored by git; track it instead?
- `data/dream_reports/`: tracked, but the ignore rule still stands, so new reports are not added.
- **359 files are tracked but ignored** (count 2026-11-19, `dream_reports/` and `cocoons/`
  excluded; it was 895 in September): Kaggle replays, benchmark outputs, checkpoints, LaTeX builds.
  The `Archive*.zip` files stay by rule; the rest need a decision, not a sweep.
- Version families (four optimizer revisions, three equation versions): no canonical marker.
- Six archives on `main` (about 23 MB, heavily duplicated): stay by rule; extraction alongside only.
- Hugging Face remote: untouched; no push without asking.
- Whether `cocoons/` stays tracked (so a fresh clone does not wake her blank).

## 4. Ready to build once decided, or no decision needed

- **Layer 5 rewrite** (if item 3 says build). Input: per-turn epsilon (real since 08-06; "not
  measured" with fewer than two perspectives). Memory: a rolling window inside the session; no store
  reads. Forecast: the trend of the last N epsilons projected k turns ahead. Thresholds: from
  `tools/epsilon_profile.py` on her machine, not 0.50 / 0.70. Output: observe-only ("would warn" /
  "would act", nothing applied) into the existing AEGIS healing fields. Key test: the reading must
  move when the inputs move (the old Layer 5 fails this). The old file stays as lineage with a
  SUPERSEDED header. About 150–250 lines plus ~15 tests.
- ~~**Introspection wording:**~~ **DONE 2026-11-20.** In both implementations (`cocoon_introspection.self_observations`,
  `UnifiedMemory.full_introspection`) and in the self-diagnostic reply, the verdicts ("I should check
  if I'm over-relying", "I should diversify", "well-balanced", "fair use", "may be over-relying")
  are replaced with the counts and shares. Old wording kept in comments.
  `tests/test_introspection_no_verdicts.py` (5, all fail on the old code). Original item:
  - **Introspection wording:** observations like "I should diversify" are verdicts in her voice
  (`inference/cocoon_introspection.py`; check the second implementation in `unified_memory.py`
  too). House rule: report numbers, not verdicts. Small.
- **Antibody leads:** 40 `zero_for_unmeasured` (most benign; review once, by clone family);
  `missing_method` has 2 known leads (governor `get_pressure`, decided; `chat_app.py`, superseded).
- Noted, not done: the near-tie synthesis picks the blander perspective's text (09-29); the first
  greeting turn makes many tool calls; her replies average ~40% longer than at the start, cause
  unknown (do not read it as a fault).
- **Hazard before any Linux deployment as root** (the repo has a `Dockerfile`): AEGIS Layer 3's
  `verify_boot_integrity()` calls `enforce_kernel_module_lockdown()`, which sets
  `kernel.modules_disabled=1`, locking module loading until reboot. It is not on the live path today
  (only `forge_with_full_safeguards`, which nothing calls). Guard it before anything calls it.
- **Media engine** (`media/`): needs `Pillow<10` with moviepy 1.x; text overlays untested (no
  ImageMagick).

## 5. Known gaps (from CLAUDE.md, unchanged)

`components/*` has no implementation in any archive; seven modules use qiskit `Aer` / `execute`
(removed in 1.0; port or pin); `ace_tools` and `transformers_js` are unobtainable;
`Zeta_Wave_Analysis.pdf` is corrupt; `dotnet/BotWebApp/` has never been compiled.

## 6. Roadmaps with open checkboxes

`docs/NEUROSYMBOLIC_GROUNDING.md` (phases B–C, including **C1: configurable self-healing thresholds**,
the original idea Layer 5 descends from, and the IsolationForest self-healing idea) and
`docs/CODETTE_CHARTER.md` ("Ideas that were ahead of their execution").

## 7. Before you start: things about this environment that cost time

- **Her full server runs inside the container.** `.mcp.json` registers a `codette` MCP server, and it
  starts `inference/codette_server.py` whenever the session (re)starts. Ten minutes after boot its
  background jobs (dream review, self-trainer, antibody scan) write `data/self_train_shadow.jsonl`,
  `data/antibody_report.json` and `data/background_jobs.json`. That was the "unexplained file" of
  11-17 / 11-18; it is not the tests. Check `ps` before attributing a write.
- **Repository-wide searches:** exclude `backup/`, `cocoons/` and `data/` (`git grep ... -- .
  ':!backup' ':!cocoons' ':!data'`). Anything that walks `cocoons/` goes through
  `reasoning_forge.cocoon_files.conversation_cocoons`, never `ls` or a glob.
- **Finding which test writes where:** a pytest plugin that fingerprints the stores in
  `pytest_runtest_setup` / `pytest_runtest_teardown` attributes each change to one test (used
  2026-11-19). `git status` does not show ignored files, so a "no changes" from it proves nothing
  about runtime stores.
- **End-to-end runs of the bridge** belong in a scratch copy (`git worktree add`). One bridge call
  writes five runtime files and a cocoon into the tree it runs from.
- The system Python has no numpy; use a venv. NLTK refuses proxied downloads (an SSRF guard). Do not
  set `NLTK_ALLOW_PROXIED_URLOPEN`.
- **Before calling something damage, search the notes for its name.** `pidrio` is a name, not a typo
  (HANDOFF_2026-08-04). That was re-learned the hard way on 11-18.
