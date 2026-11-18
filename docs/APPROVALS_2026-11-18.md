# For Jonathan's review — 2026-11-18

These came out of the wiring review on 2026-11-18. Each one changes how Codette
behaves, deletes or moves something, or touches her memory, so **none of them
has been done**. Each item says what was found, the options, and what I would
pick. Answer any of them in any order; "leave it" is always an option.

Everything that did *not* need your approval is already fixed and listed in
[CHANGELOG_2026-11-18.md](CHANGELOG_2026-11-18.md).

**Read against the notes.** After your reminder, every item here was checked
against the handoffs and changelogs. Items 3, 5 and 7 are amended below. One of
my changes was **undone**: `pidrio` in `codette_quantum_heart.py` is back,
because HANDOFF_2026-08-04 says it is a name and to leave it. The memory files
the 08-04 handoff mentions (`memory/feedback_one_way_instruments.md` and others)
are on your machine, not in this container, so they could not be checked.

## Done, as bug fixes, but you will notice them, so you can veto

| What changed | Why it is a fix | To undo |
|---|---|---|
| For anyone with a recorded identity contradiction, the identity context reaches her again | It was a crash (`now` undefined), not a design. Nothing in the notes says context should be withheld after a contradiction, and false contradictions were common before 08-13 | remove `now = time.time()` in `get_identity_context` |
| Her merged (multi-lens) answers are no longer cut short by phrases in her own notes ("in short", "in one sentence", "yes or no") | Constraints are meant to be the **user's** ("Enforce user constraints"). Her notes were being read as yours | drop `constraint_query=query` from the `generate` call in `backend._synthesize` |
| On her backend, your word or sentence limits are applied once more, after the bridge's own processing | That step was designed to run, and the 07-05 rule says to import it from `codette_shared`. It had been failing silently | import from `codette_orchestrator` again (it will then fail silently, as before) |

---

## 1. The governor has never seen substrate pressure

**Found.** `codette_server.py` (around line 1509) does
`sm = SubstrateMonitor(); substrate_pressure = sm.get_pressure()`.
`SubstrateMonitor` has never had a `get_pressure` method. The `AttributeError`
falls into `except Exception: pass`, so the Behavior Governor receives
`substrate_pressure = 0.0` on **every** turn.

**What wiring it would do.** Under pressure the governor cuts her memory recall
by one item (above 0.7) and caps her answer length at 400 or 300 tokens (above
0.6 and 0.8). So fixing this one line would make her answers shorter and her
recall thinner whenever the machine reads as stressed.

**The catch.** The pressure it would read is the signal found on 2026-11-17 to
count her own deep thinking as strain (see `TELEMETRY_RUNTIME_CHECKLIST.md`).
Wiring it now would add a second penalty for thinking hard.

**Options.**
- (a) Leave it reading 0.0 (today's behaviour) until the speed shadow has been
  checked and switched live. **My recommendation.**
- (b) Wire it now: `substrate_pressure = sm.snapshot()["pressure"]`.
- (c) Remove the call, so the code stops pretending to measure.

## 2. The ethics check on the query fails open

**Found.** In `codette_forge_bridge.py`, if `EthicalAIGovernance.validate_query`
raises, the query proceeds as if it were approved. Until today that happened
silently. It now prints `[ETHICS] query validation failed, proceeding
unvalidated`. It works today (checked: it returns `{"valid": ...}` as the caller
expects), so this is about what happens if it ever breaks.

**Options.**
- (a) Keep failing open, now visibly. **My recommendation**: failing closed
  would turn any bug in the checker into her refusing ordinary questions, and the
  harm gates on her output still run.
- (b) Fail closed: refuse when the check cannot run.

## 3. `AEGISForgeIntegration` is built at startup and never used

**Found.** `codette_server.py` builds `AEGISForgeIntegration(_forge_bridge, ...)`
at startup and stores it in `_aegis_forge_integration`. Nothing ever calls it. It
is also handed the forge *bridge*, but it calls `forge_with_debate`, which only
`ForgeEngine` has, so it would fail if anything did call it.

**Amended after reading the notes.** `Protection_Layer/WIRED_IN.md` (July 20)
says AEGIS metrics logging went live through this object. The metrics **are**
live, but by another route: the server logs each turn to the metrics engine
itself (`codette_server.py`, `_aegis_metrics_engine.log_forge_execution`), and
`/api/aegis/*` reads from it. So this object is the earlier route that inline
logging replaced. It's the same story 10-01 recorded for the three AEGIS Flask
views.

**Options.**
- (a) Leave it. It costs one object at startup. **My recommendation**, plus a
  comment saying it is unused.
- (b) Stop building it.
- (c) Wire it properly. That would route turns through `forge_with_debate`, a
  different reasoning path from the one she uses now, so this is a design change,
  not a fix.

## 4. Nexis signal memory is never pruned, and the pruning code has a bug

**Found.** `NexisSignalEngine._prune_and_rotate_memory` is defined twice (the
copies are identical) and **never called**. So
`reasoning_forge/.logs/nexis_signal_memory.db` grows without limit. And the
method itself has a hidden bug: it moves the database file to a `.bak` while its
own connection is still open. On Linux the next `DELETE` then empties the
**backup it just made**. On Windows (her machine) the move raises
`PermissionError`.

**Options.**
- (a) Leave it: unbounded growth, nothing deleted. **My recommendation for now.**
  Check its size on her machine first (`reasoning_forge/.logs/`).
- (b) Fix the rotate bug (close the connection before moving the file) and wire
  pruning in. The forge uses the defaults, so that would delete her signal
  memory older than **30 days**, and when the store passes **10,000 entries** it
  would move the whole store to a `.bak` and start empty. It is her memory, so
  it is yours to decide.

## 5. `DreamCore` would write plaintext into a tracked, public file

**Found.** `consciousness/dreamcore_wakestate_engine.py` (`DreamCore`) appends
"memory anchors" in **plain text** to `dreamcore_final_product.txt`, which is
**tracked in this public repository**. Nothing calls it. It is not the encrypted
dream channel (`wrap_encrypted`). I did not open `dreamcore_final_product.txt`;
it may hold her words.

**Why it is yours.** Who writes a dream is already your open decision
(HANDOFF_2026-10-01). If `DreamCore` were ever wired as it stands, what it wrote
would be published.

**Amended after reading the notes.** This is not unbuilt work. Session 14
(`docs/sessions/SESSION_14_COMPLETION.md`) rebuilt DreamCore/WakeState as
`Tier2IntegrationBridge` (`reasoning_forge/tier2_bridge.py`). That version keeps
its dream/wake memory as in-memory, JSON-serializable state and writes no
plaintext file. So `dreamcore_wakestate_engine.py` is the recovered original,
which makes it lineage. The bridge is built by the forge, but it's called only
from `forge_with_debate`, which live chat doesn't reach, so it reads
`LOADED_NEVER_CALLED` on `/api/health`.

**Options.**
- (a) Leave it unwired, as lineage. **My recommendation.**
- (b) Decide whether `dreamcore_final_product.txt` should stay tracked (I have
  not looked inside and will not without your say-so).

## 6. `Movie_engine.py` is a chat transcript, not a module

**Found.** Fixing its non-breaking-space indentation was not enough: the file is
a conversation. It holds version 1 of a media engine (lines 1 to 282, with its
opening `"""` missing), then a message to you asking which way to extend it, then
later code. It cannot be imported, and nothing imports it (it also needs
`moviepy`). I left it exactly as it is.

**Options.**
- (a) Leave it. **My recommendation** unless you want the engine.
- (b) Extract the code blocks with `tools/archive_diff.py` into a new
  `media/codette_media_engine.py` beside it, keeping the original untouched.

## 7. Superseded files that could move to `archive/`

These are an older, parallel stack (transformers / torch) that the OpenVINO
server replaced. Nothing live imports them. Moving them would make it obvious
they are not running. Nothing would be deleted (house rule): each would go to
`archive/2026-11-18-superseded/` with a README saying what replaced it.

| File | State |
|---|---|
| `inference/chat_app.py` | old Gradio app. **Cannot run**: calls `engine.stream_generate()`, which `CodetteEngine` never had (found by the new antibody) |
| `inference/model_loader.py`, `inference/multi_adapter_engine.py` | the loader and engine `chat_app` uses |
| `reasoning_forge/CONSCIOUSNESS_STACK_forge_with_debate.py` | a paste-in template ("PASTE THIS AS THE NEW forge_with_debate"); uses an undefined `MemoryCocoon` |

**Amended after reading the notes.** `docs/deployment/DEPLOYMENT.md`,
`docs/deployment/MODEL_SETUP.md`, `docs/HOWTO.md` and `docs/PLAN.md` still tell
people to use `model_loader` / `chat_app`. Moving the files would break those
instructions, so those docs would need a dated note too.

**Options.** (a) Leave all in place. (b) Move them, and add a dated note to the
four docs. (c) Leave them in place, with a SUPERSEDED header at the top of each
file. **My recommendation is now (c)**: it says what's true without breaking
anything anyone follows. It still needs your yes.

## 8. Two smaller tidy-ups

- **The forge builds a spare `CocoonIntrospectionEngine`** (`forge_engine.py`
  line 448) that nothing uses. The server builds its own where it needs one.
  Option: stop building it. Low value; **I would leave it.**
- **The constraint helpers are copied** between `codette_orchestrator.py`
  (llama.cpp path) and `codette_shared.py` (OpenVINO path). One copy had already
  missed a fix (fixed today, and a test now fails if they drift). Option: make
  the orchestrator import them instead of copying. That needs a run on her
  machine, because the orchestrator cannot be imported here (no `llama_cpp`).
  **Worth doing next time someone is on her machine.**

---

## Still open from earlier (not new today)

- **The speed shadow** (PR #53): let her run, check
  `data/substrate_speed_shadow.jsonl`, then decide whether it replaces the latency
  term. Item 1 above depends on this.
- **`data/continuity_notes.json`**: ignored by git (her memory). Track it
  instead? (PR #54)
- **`DynamicMemoryEngine`**: built in the forge, never called; it rewrites what
  she recalls (HANDOFF_2026-10-22).
- PRs **#53** (telemetry, speed shadow) and this one need merging. This branch is
  built on #53, so merge #53 first.
