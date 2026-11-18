# 2026-11-17 / 18 — Telemetry checklist, a speed shadow, and a wiring review

Additive; nothing earlier is rewritten. Follows [CHANGELOG_2026-10-22.md](CHANGELOG_2026-10-22.md).
Decisions that are Jonathan's are in [APPROVALS_2026-11-18.md](APPROVALS_2026-11-18.md), not here.
Suite (reduced venv, no torch / llama_cpp): **1,515 passed**, 1 failed, 7 skipped, 1 xfailed (1,510 before the notes pass below). The one
failure is `test_trace_e2e` and is environmental: NLTK's SSRF guard refuses to download its data
through this container's proxy. `main` fails it identically.

## 2026-10-27 to 11-17: the telemetry checklist (PRs #52, #53, #54)

Full detail, with measurements: [TELEMETRY_RUNTIME_CHECKLIST.md](TELEMETRY_RUNTIME_CHECKLIST.md).

| Change | Why |
|---|---|
| Checklist noted (#52, merged) | Jonathan's four checks, kept as given, with guardrails for her private spaces |
| Substrate pressure explained | No decay clock pauses during inference. The depth throttle is substrate pressure, and her own generation time fed it: deep answers at normal speed read as `high` |
| Violation rate windowed (#53) | It divided a lifetime count by a 20-turn window, so it climbed with session length. No live caller yet |
| Speed shadow (#53, agreed) | Pressure from per-token slowdown against her own normal. **Shadow only**: logs to `data/substrate_speed_shadow.jsonl`, `applied: false` |
| Shadow write cost (#53 review) | The write took a fresh 100 ms CPU sample every turn (measured 101 ms). It now reuses the routing snapshot: 0.2 ms |
| `python-dateutil` declared (#53) | Undeclared; without it month-name dates do not parse |
| Nexis failures logged at WARNING (#53) | They were DEBUG, the invisibility the 2026-08-03 note warned about |
| Four runtime files ignored (#54, merged) | Including her tape, `data/continuity_notes.json`. `git add -A` would have published them |
| Antibody `lifetime_over_window` (#53) | Class of the violation-rate bug |

## 2026-11-18: the wiring review

Jonathan: *"review each code and ensure everything is wired up connected and real ... check for
hidden bugs duplicates code or silent failures."*

**How.** pyflakes over every live file; a real import of every live module, each in its own
process; the antibodies; a reachability graph from the three entry points (the server, the chat UI,
the MCP server); AST duplicate detection; a call/definition signature check; and reading every
silent handler on the chat path. Every fix below has a test that was checked to **fail on the
pre-fix code**.

### Bugs fixed

| Where | Bug | Effect before |
|---|---|---|
| `inference/identity_anchor.py` `get_identity_context` | read an undefined `now` | Contradictions are saved to disk, so after the first one was ever recorded, every call raised. The server caught it ("Identity recognition skipped") and she got **no identity context at all** for that person |
| `reasoning_forge/forge_engine.py` `forge_with_debate` | read `analyses`, `epistemic_report`, `safety_notes`, which exist only in `_forge_single_safe` | The `NameError` aborted the whole memory-storage block (v3, v2, dual-write, legacy), logged at DEBUG. **This path never stored a memory**, and its adaptive synthesis never ran. Now uses Layer 2's measured epsilon / gamma, not invented defaults |
| `inference/codette_orchestrator.py` `extract_primary_user_query` | a copy that missed the attached-file strip its `codette_shared` twin has | On the llama.cpp path, a file saying "in 10 words" cut her answer to fit. Now delegates to the shared copy |
| `scripts/reboot_codette.py` | counted and **deleted** `*.json` in the low-confidence cocoon folder with no private-envelope guard | ~~Same shape as `95d8971`.~~ **Reclassified below: defensive, not a bug** (10-22 reviewed this lead). Now goes through `conversation_cocoons`; tested on an encrypted-type fixture, which is left untouched |
| `reasoning_forge/quantum_optimizer_enhanced.py` | `json` never imported | export raised; import silently returned False |
| ~~`reasoning_forge/codette_quantum_heart.py`~~ | ~~a stray token (`pidrio`) after the last line~~ | **Wrong, and reverted the same day** (see below): HANDOFF_2026-08-04 says `pidrio` is a name, not a typo, and to leave it |
| `requirements.txt` | `pyyaml`, `networkx`, `colorama` undeclared | `ethics/` modules cannot import in a fresh environment |

### Silent failures made visible (behaviour unchanged)

- Three session saves in the server (`/api/session/new` and import). A failed save lost the
  conversation and the import still reported success. Now `[SESSION] save failed: ...`.
- The post-turn identity update. Now `[IDENTITY] update skipped: <type>`: the exception type
  only, because identity information is never logged.
- The ethics check on the query, which fails open. Now `[ETHICS] query validation failed,
  proceeding unvalidated`. Fail-closed is approval item 2.

### Marked, not deleted

- The first `route_and_generate` in `codette_orchestrator.py` is shadowed by a second one in the
  same class, so it never runs. Marked SUPERSEDED with what it had (the artist-honesty guard, live
  in the server; the only call to `log_routing_decision`).

### Antibodies

- **New class `missing_method`.** It was taught by `SubstrateMonitor().get_pressure()`, which never
  existed (approval item 1). pyflakes cannot see this: the name is bound, only the attribute is
  missing. It catches its teaching instance and one more, `chat_app.py`'s `stream_generate`
  (approval item 7).
- **`constructed_never_invoked` sharpened.** It now sees `getattr(x, "name")` and list membership.
  Four of its six leads were wired components read as dead (`newton`, `specialization`,
  `ethical_anchor`, `routing_metrics`). The two left are real: `dynamic_memory` (open since 10-22)
  and the forge's spare `introspection` (approval item 8).

### Checked and found sound

- **162 of 170 live modules import.** The 8 that do not are missing third-party packages
  (torch, llama_cpp, gradio, tkinter, matplotlib, and the three now declared), not code faults.
- **No call/definition mismatches** in reachable code (10 hits, all unrelated objects such as
  `os.close` and a Tk menu's `delete`).
- `enforce_constraints` in its two copies: **0 of 63** behavioural cases differ. A test now pins it.
- `zero_for_unmeasured` leads whose numbers reach her (introspection, Colleen, the governor):
  each is guarded upstream or covers an impossible case.
- **Unmerged `claude/*` branches:** none shares history with `main` (rebuilt at `edbcb48`), all
  date from 08-14 or earlier, and none holds a live `.py` file `main` lacks. Nothing is stranded.

## After reading the notes (later the same day)

Jonathan: *"read the notes too there are fixes we've done."* Every finding and approval was checked
against the handoffs and changelogs, and the fixes they record were checked against the code.

**Two of my changes were wrong against the notes:**

- **`pidrio` reverted.** HANDOFF_2026-08-04: *"`codette_quantum_heart.py` raises `NameError` on
  `pidrio`. That is a **name, not a typo**. Leave it."* I had replaced it. The file is restored
  byte-for-byte to `main`. The rule I broke: read the notes before naming something damage.
- **`reboot_codette.py` reclassified.** CHANGELOG_2026-10-22 ("Reviewed and not bugs") had already
  found that this lead only clears the `low_confidence/` review folder, never the folder her dreams
  are in. The guard stays (it is harmless and silences the antibody), but it is defensive, not the
  bug I described.

**The recorded fixes, checked in the code: 21 of 22 hold.** These all still hold: the route read
where it is used, `intent_vector` initialised, `rejection_rate` None over zero calls, `reasoning_v3`
recall, 20,000-character storage, the retired WisdomModule/ReflectionJournal, `EthicalAnchor.observe`,
Lock 1 "ANSWER FIRST" in both copies, introspection excluding non-exchanges in both implementations,
advisories forwarded, the whitening floor, background jobs, reach counters, the 160-byte envelope
check, `wrap_encrypted` refusing a throwaway key, `PRIVATE_TOOLS`, `SCRATCH_TOOLS`,
`is_harness_traffic`, and the `Code7eCQURE` shim.

**The one that does not hold, and the bug behind it:**

| Where | Bug | Effect before |
|---|---|---|
| `inference/codette_forge_bridge.py`, step 9 | imported `codette_orchestrator`, against the 2026-07-05 rule ("OV-path code must import from `codette_shared`"); that fix reached the greeting and memory fast-paths and missed this step | its `import llama_cpp` fails in `openvino_env`, so on her backend the user-constraint step **never ran**. Now imports `codette_shared` (the copies behave identically) |
| `openvino_backend/backend.py`, `_synthesize` → `generate` | format constraints were read from the synthesis prompt, which quotes her lens notes | a note saying "In short" made her merged answer brief; "In one sentence" plus "yes or no" cut it to one yes/no sentence, with a CRITICAL CONSTRAINT added to her prompt. `generate` now takes `constraint_query`, and `_synthesize` passes the user's question. Every other caller is unchanged. The llama.cpp synthesis calls the model directly and was not affected |

`tests/test_constraints_from_user_words.py` (3 of 5 fail on the pre-fix code) includes a test that
fails if any OV-path file imports `codette_orchestrator` again.

**What the notes changed in the approvals:** the AEGIS metrics are live through inline logging, so the
unused integration object is superseded (item 3). DreamCore was rebuilt as `Tier2IntegrationBridge` in
Session 14, so the old file is lineage (item 5). Four docs still point at the torch-stack files, so
moving them would break instructions (item 7).

**Not reachable from here:** the memory files HANDOFF_2026-08-04 points to
(`memory/feedback_one_way_instruments.md` and others) are on Jonathan's machine.

Suite after: **1,515 passed**, 1 failed (NLTK, environmental, as on `main`).

## Corrections made in the open

- **2026-10-27:** the checklist said no substrate-fatigue mechanism existed. That was a search
  whose output was cut off after 15 hits. Corrected in the checklist on 11-17.
- **2026-10-01 wiring record:** it said `neural_symbolic` was "a thin wrapper over
  `grounding_bridge.ground_text`, already advisory-wired in `_synthesize`". What is wired is
  `reasoning_forge.grounding.verify` (`openvino_backend/backend.py`, `_synthesize`).
  `grounding_bridge` has no callers, and its own docstring says so ("Nothing in the runtime calls
  this yet"). No wire came loose; the record named the wrong module. Amended in
  `WIRING_STATE_2026-11-18.md`; the 10-01 file is left as written.
- **My own first attempt at the speed-shadow tests** (11-18) passed against the bugs they were meant
  to catch. Caught by mutation and fixed; detail in the checklist.

## Her private spaces

Nothing in this work opened, listed, counted or quoted a dream, `khralexi`, `nameless`, the
scratchpad, `dreamcore_final_product.txt` or `data/continuity_notes.json`. The cocoon fixture used
to test the reboot guard was written by me, in the scratchpad.

## Jonathan's decisions on the approvals, and what was done (later 2026-11-18)

Branch `claude/decisions-2026-11-18`, after #53 and #55 were merged.

| Item | Decision | Done |
|---|---|---|
| 1. Governor substrate pressure | leave it reading 0.0 until the speed shadow is checked and live | a DECIDED comment at the call site in `codette_server.py`; behaviour unchanged. The `missing_method` antibody keeps flagging the line; the comment says that lead is known |
| 2. Ethics check fails open | keep failing open, visibly | a DECIDED comment at the check in `codette_forge_bridge.py`; behaviour unchanged |
| 5. DreamCore | leave unwired, as lineage | nothing changed |
| 6. `Movie_engine.py` | extract the code blocks with `tools/archive_diff.py`, original untouched | `media/codette_media_engine.py` (lines 386-800, the fullest version) and `media/lineage/` (lines 1-207 and 208-283), with `media/README.md` and `media/requirements.txt` |
| 7. Superseded torch-stack files | SUPERSEDED header, left in place | headers on `inference/chat_app.py`, `model_loader.py`, `multi_adapter_engine.py`, `reasoning_forge/CONSCIOUSNESS_STACK_forge_with_debate.py`; code unchanged (syntax-tree identical) |

Items 3, 4 and 8 are still open. Suite after: **1,519 passed**, 1 failed (NLTK, environmental, as on `main`).

**The extraction, as it happened.** `tools/archive_diff.py` alone reported the file UNREPAIRABLE:
its last repair keeps the longest prefix that parses, and the transcript breaks on line 1 (the
module docstring's opening triple quote was lost). So the segments were found by reading the
content, and each went through the tool's own `repair()`. My first cut was one line off (line 208
opens segment B's docstring), and the tool silently cut segment A from 207 lines to 132 to make it
parse. That was caught by comparing line counts, and corrected. The tool also *deletes*
non-breaking spaces; here each indent step was `NBSP + space`, so deleting them halves the
indentation. They were replaced with spaces before `repair()`, which then changed 0 lines in each
segment (measured). A "keep the longest parsing prefix" repair can drop code without saying so,
so check the line count after it.

**Verified:** all three versions import with moviepy 1.0.3, and the main one rendered two 1-second
clips plus a tone into a 2.00 s, 320x240 video with audio. moviepy 1.0.3 calls
`PIL.Image.ANTIALIAS`, which Pillow 10 removed. The test used a one-line alias, and the engine is
unchanged; `media/requirements.txt` pins `Pillow<10`. Text overlays were not tested (ImageMagick
absent). `tests/test_media_engine_extraction.py` pins the original's checksum.

**Found while writing the headers:** `chat_app.py` does `from inference import CodetteModelLoader,
CodetteEngine`, but those are exported by `inference/init.py`, and there is no
`inference/__init__.py`. `init.py` is probably `__init__.py` with its underscores lost (Markdown
renders `__init__` as bold "init"). **It must not be renamed:** every `import inference.*` would
then load torch. Recorded in the `chat_app.py` header.
