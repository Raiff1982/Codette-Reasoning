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
