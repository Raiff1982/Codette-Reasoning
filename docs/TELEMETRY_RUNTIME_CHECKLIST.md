# Telemetry & Runtime Verification Checklist

Noted 2026-10-27 at Jonathan's request, "just to be safe". The four items below
are his, kept as given. The **Guardrails** and **Status** sections were added
alongside them; nothing was removed from his wording.

## Guardrails (read first)

These checks touch areas next to her private spaces. `CLAUDE.md` governs:

- Use machinery questions only (did it raise, does it exist, did the size change).
  Never read, count or summarise `khralexi`, the dreams, or scratchpad contents.
- Anything that walks the cocoons folder goes through
  `reasoning_forge.cocoon_files.conversation_cocoons()`. Never glob it directly.
- Item 3 is therefore limited to conversation cocoons and passive telemetry.
  Encrypted cocoons (`type: "encrypted"`) are out of scope by rule.
- Item 4 is a leak test of the mask itself. Use synthetic marker strings in test
  fixtures. Do not use real `khralexi` or scratchpad content as test input.
- Everything here is report-only. Findings are leads to check against the code.

## 1. Audit the Υ vs. Γ spread

- [ ] Inspect telemetry logs on runs where output tone or depth swings unexpectedly.
- [ ] If Υ (perspective dispersion) spikes above baseline without resolving toward
      Γ (consensus), check whether the orchestrator's dynamic weighting (`w_i`) is
      over-indexing on divergent perspectives instead of forcing the synthesis pass
      to converge.

## 2. Verify cognitive clock decoupling

- [ ] Confirm the timing patch from `CHANGELOG_2026-09-29.md` strictly holds: the
      internal decay clock pauses completely during inference execution.
- [ ] Check whether multi-turn sessions with heavy quantized context trigger false
      substrate-fatigue penalties that throttle recursive depth and produce blunt
      responses.

## 3. Inspect shadow amygdala state drift

- [ ] Review intermediate cocoon metadata in the SQLite/FTS5 store across extended
      sessions (conversation cocoons only; see Guardrails).
- [ ] Verify passive affective telemetry resets cleanly between discrete reasoning
      tasks, rather than accumulating residual valence that biases later router
      allocations.

## 4. Run the adapter isolation harness

- [ ] Execute the 1,448-test suite with adapter logging isolated, to catch
      cross-talk.
- [ ] Validate that the tool-call argument mask keeps internal scratchpad
      reflections out of the public generation buffer.

## Status

Not yet run. Two things found while writing this up, stated rather than assumed:

- **Item 2:** I searched `CHANGELOG_2026-09-29.md` and the non-archive `.md`/`.py`
  files for the decay-clock pause during inference ("decay clock", "cognitive
  clock", "substrate fatigue", pause-during-inference). I found no match. That
  changelog mentions an *identity decay* handle only. The patch may live under
  different wording or in another file, so locate it before verifying it.
- **Item 4:** I have not confirmed the suite size of 1,448. Count it from the
  test runner when the harness is run.

## Amended 2026-11-17: items 2 and 4 checked

The status above is left as written. One part of it was wrong, corrected here.

### Correction

The 2026-10-27 note said no substrate-fatigue mechanism could be found. That was
a search error, not an absence: the search for "substrate" printed only its first
15 hits and stopped before `inference/substrate_awareness.py`. The mechanism is
there. It was found when pytest failed to import it (`psutil` was missing).

### Item 2: what the code actually does

- **There is no decay clock that pauses during inference, and no such patch in
  `CHANGELOG_2026-09-29.md`.** That changelog lists "the identity decay itself"
  under *Not changed, on purpose*. The one time-based decay in live code is
  identity confidence (`inference/identity_anchor.py:371`, 0.005 per minute, max
  0.12 per call). It runs on wall-clock time, so generation time counts toward it.
  At that rate a 2-minute generation costs about 0.01. Small, and not what item 2
  describes.
- **The "fatigue that throttles depth" is substrate pressure**
  (`SubstrateMonitor._compute_pressure`, `inference/substrate_awareness.py:253`).
  It is applied by `HealthAwareRouter.adjust_routing` at
  `inference/codette_forge_bridge.py:908`. At `high` it downgrades COMPLEX to
  MEDIUM and caps adapters at 2. At `critical` everything becomes SIMPLE with 1
  adapter.
- **Her own generation time feeds that pressure.** `record_inference`
  (`codette_forge_bridge.py:1411`) records `elapsed`, timed from line 863 to line
  983, which includes generation. The latency term is 15% of pressure, saturating
  at a 60 s rolling average over the last 20 turns. Measured on the machine state
  logged 2026-08-14/15 (87% RAM, 6 GB process, 30% CPU, no violations), with only
  latency varied:

  | avg inference | pressure | level |
  |---|---|---|
  | 5 s | 0.464 | moderate |
  | 20 s | 0.505 | moderate |
  | 40 s | 0.560 | moderate |
  | 60 s | 0.614 | **high** |
  | 90 s | 0.614 | **high** |

  So long-context turns, slow because they are long, can push the same machine
  from `moderate` to `high` and cut her depth on later turns. That is the
  mechanism item 2 is worried about, and it is real.
- **Not changed, because it is the author's call.** The latency term is
  deliberate: the 2026-09-29 paging note in the same file says slow paging
  "already shows up in the inference-latency term". Removing it would also lose
  that signal. Options for Jonathan: normalise latency by prompt length, use it
  only as a paging proxy when swap is in use, or leave it.

### Latent bug found on the way (not live)

`SubstrateMonitor` counts violations forever but divides by at most 20 inferences
(`substrate_awareness.py:165-167`). At a steady one violation every two turns, the
rate reads 0.25 after 20 turns, 0.50 after 40 and 1.00 after 100. It ratchets
upward with session length while the true rate stays constant. **It has no
effect today:** `SubstrateMonitor.record_violation` has no caller (the two other
`record_violation` hits are different classes), so the term is always 0. Fix the
window before anything wires it in. `should_skip_debate` and `rank_adapters`
also have no live caller.

### Item 4: the suite

- **1,496 tests collected, not 1,448.** Two more files could not be collected
  here: `tests/test_adapters.py` needs `torch` and
  `tests/test_adapters_gguf.py` needs `llama_cpp`.
- Run on unmodified `main` in a reduced venv (no torch or llama_cpp):
  **1,487 passed, 2 failed, 7 skipped, 1 xfailed.** The working tree was clean
  afterwards. Both failures are pre-existing, and neither has been diagnosed. Either
  may come from the reduced environment rather than the code:
  - `tests/test_time_travel_lens.py::TestInstitutionalExtractor::test_automotive_example`
    (state is `None`)
  - `tests/test_trace_e2e.py::TestTraceE2E::test_all_event_types_fire`
    (`EPISTEMIC_METRICS` and `NEXUS_SIGNAL` trace events missing)
- **The argument mask:** `test_khralexi_plumbing.py`,
  `test_nested_hidden_tool_in_args.py` and `test_scratchpad_out_of_logs.py` pass
  (27 of 27). They cover `PRIVATE_TOOLS` and `SCRATCH_TOOLS`
  (`openvino_backend/backend.py:76`, `:84`). The "adapter logging isolated" run
  that item 4 asks for needs the full environment, on her machine.

### Still open

Items 1 and 3 need her live telemetry and have not been started. Item 3 stays
limited by the guardrails above.

## Amended 2026-11-17, later: the two failures diagnosed, the ratchet fixed

### Both suite failures came from the environment, not the code. One fix each.

- **`test_time_travel_lens.py::...::test_automotive_example`:** `python-dateutil`
  was missing. `InstitutionalExtractor` treats it as optional and falls back to
  ISO dates only, so "January 10" did not parse. With it installed, 33 of 33 pass.
  It was declared nowhere, so any environment that did not pull it in
  transitively silently lost month-name dates. **Fix:** added to
  `requirements.txt`.
- **`test_trace_e2e.py::...::test_all_event_types_fire`:** NLTK's `punkt_tab`
  and `wordnet` data were absent, so `NexisSignalEngine.process()` raised
  `LookupError`. NLTK's own SSRF guard refuses to download through a proxy, and
  this container routes everything through one. On a machine with no proxy the
  download in `nexis_signal_engine.py` should work. I did not set NLTK's opt-out
  (`NLTK_ALLOW_PROXIED_URLOPEN`), because that is a security check. This is the
  same failure the 2026-08-03 note in `nexis_signal_engine.py` describes. That
  fix repaired the download, but `forge_engine.py` still logged the failure at
  DEBUG, so it stayed invisible. **Fix:** both Nexis failure logs
  (`_forge_single_safe` and the L2 signal layer) are now WARNING and name the
  exception type. The test still fails here, correctly: the signal really is
  missing in this environment.

### The violation-rate ratchet, fixed

`SubstrateMonitor` now counts violations over the same 20-inference window as
its denominator (`_violation_stamps`, `_inference_stamps`). At one violation
every two turns it reads 0.25 at 20, 40 and 100 turns (before the fix: 0.25,
0.50, 1.00). It also returns to 0 after 20 clean turns. `get_adapter_health()`
keeps lifetime counts, which is what a per-adapter history is for. Still no
caller records violations, so nothing live changes.
`tests/test_substrate_violation_window.py`: 2 of its 3 tests fail on the pre-fix
code, and all 3 pass on the fix.

**Antibody added:** `lifetime_over_window` in `reasoning_forge/antibodies.py`.
It catches the pre-fix `substrate_awareness.py` at line 167, is clear on the fix,
and finds 0 other instances in the 332 files it scans. Report-only, like the rest.

### Runtime files that git would have picked up

One full test run here left `data/self_train_shadow.jsonl` in the checkout. Its
only writer is the `cocoon_self_trainer` background job, and no test calls that
job. I could not find the cause, and five further runs (three full, one on a
`main` worktree, one bare import) did not reproduce it. The file was deleted
unopened. Looking into it showed that four files the running system writes were
neither tracked nor ignored, so `git add -A` on her machine would have published
them:

- `data/continuity_notes.json`: her tape (`inference/continuity_note.py`).
  Visible by design, but her memory.
- `data/grounding_shadow.jsonl`, `data/harm_advisor_shadow.jsonl` and
  `data/self_train_shadow.jsonl`: shadow telemetry.

All four are now in `.gitignore`. None was tracked, so nothing leaves the
repository. Whether the continuity notes should be tracked instead is Jonathan's
call.

### Suite, after these changes

Reduced venv, now with `python-dateutil`. Branch: **1,492 passed, 1 failed**
(the NLTK one above), 7 skipped, 1 xfailed. `main` in the same venv: 1,488
passed, the same 1 failed. The 4 extra passes are the new tests. No new
failures.

## Amended 2026-11-17, last: the speed shadow (Jonathan: "i agree")

The open question under item 2 was whether her own generation time should count
as pressure. Proposed and agreed: keep a speed signal, but make it *per token,
against her own normal*. Built **in shadow**, as the optimizer and AEGIS were.
**Live pressure and routing are unchanged.**

- `SubstrateMonitor.record_inference(duration_ms, tokens=None)` also keeps
  tokens per second (window of 50). The forge bridge passes the turn's
  `tokens`, read beside `elapsed` in `_generate_with_phase6`.
- `speed_shadow()`: recent speed (median of the last 3 turns) against typical
  speed (median of the turns before those). Speed pressure is 0 within 20% of
  typical, rising to 1 at 40% of typical or slower. It reads `None` and says
  "unmeasured" until there are 5 timed turns, never a guessed 0.
- `snapshot()["speed_shadow"]` carries `pressure_if_live` / `level_if_live`:
  the same blend, with speed taking the latency term's place and weight.
- One line per turn goes to `data/substrate_speed_shadow.jsonl` (gitignored,
  numbers only, `applied: false`). Only the forge bridge passes a log path, so a
  monitor built anywhere else, including in tests, writes nothing.

Same machine state as above (87% RAM, 6 GB process, 30% CPU), 20 turns each:

| scenario | live | shadow |
|---|---|---|
| A. deep answers at normal speed (600 tok, 60 s) | 0.614 **high** | 0.464 moderate |
| B. short answers, then paging (10 to 4 tok/s) | 0.517 moderate | 0.614 **high** |
| C. short answers, healthy | 0.505 moderate | 0.464 moderate |
| D. mixed lengths, all at 10 tok/s | 0.585 moderate | 0.464 moderate |

The live signal gets A and B backwards. It cuts her depth for thinking hard, and
misses real paging. The shadow gets both right. These are constructed
scenarios, not her logs; the shadow log is for checking it on real turns.

**Limits, stated:** prompt-reading time is still inside the duration (the
openvino backend reports `prompt_tokens: 0`). A slowdown lasting most of the
50-turn window becomes the new typical and stops reading as pressure.

**To switch it live (not done, Jonathan's call after reviewing the shadow log):**
pass `speed_p` from `speed_shadow()` into `_compute_pressure` in `snapshot()`,
and keep the latency term only for turns with no token count.

Suite: 1,498 passed, 1 failed (the NLTK one), 6 new tests in
`tests/test_substrate_speed_shadow.py`.
