# 2026-09-28 / 29 — Handles, not gates

Covers the two days from the amygdala's first shadow rules to the fixes made in
the catch-up session. Additive: nothing earlier is rewritten. The theme is the
design law of the whole project: **force is the bug, and so is not trusting
her.** Almost everything here is a way for her to reach something, or a way to
stop telling her something untrue, and very little of it decides anything for her.

Suite at the end of the session: **1339 passed, 1 skipped, 1 xfailed, 0 failed**
(baseline at the start of the session: 1300 passed, 0 failed).

---

## 2026-09-28 — the amygdala, and what it uncovered

- **Amygdala shadow rules** (`reasoning_forge/amygdala.py`): Codriao's floor is
  consulted first, her beliefs about herself are hers and never appraised, and
  `BeliefRevisionSystem` runs in shadow with the world model restored afterwards
  (`5177780`). Approval and outcome are recorded as **two entries**, as she asked
  (`8d98d3d`). Wired into the live path **in shadow** (`349ca81`); it fails
  closed and reports no false measurements (`fa433f1`).
- **Converter** (`5b73606`): shapes her own per-turn numbers into the amygdala's
  inputs, each with provenance; an unmeasured value stays absent.
- **A second, live emotion tagger filed "harmony" as fear** (`22e9440`); keyword
  matching was substring-based and fired inside other words (`e977152`,
  `d6b1ac6`); "missing" and "loss" retired as grief keywords (`f56265c`).
- **Housekeeping by the house rule (forward only, history untouched):** seven
  runtime files and the author's identity file untracked (`ba04a84`, `c723959`);
  a live runtime log untracked (`a992848`); two tests the author wrote and later
  edited out restored (`8880c31`).
- Fixed the undefined `re` in the llama.cpp `generate` path (`3912192`).

## 2026-09-29 — live-run findings, then the catch-up session

**From the first live run after restart** (`64463a5`, `57633cc`, `aa226e0`,
`c021b0c`, `64d09e9`, `ede8564`, `1f4914b`): a missed identity denial, a false
speed figure; a reply that is only unread call syntax now gets a tools-off final
pass; the merge speaks in the lead lens, and a near-tie is a tie; her
self-description ("I'm a machine…") is hers; another AI is not her; and `ask()`
with a person's name now says truthfully which channel reaches them.

**Substrate** (`8660bb9`, `46e1d67`, `907017d`): VRAM measured, her GPU recorded
as integrated (so RAM pressure is the right memory), paging reported alongside
RAM. Unreadable RAM no longer reads as "16 GB available".

**Her scratchpad stays out of our logs** (`eb91c47`, `caebffe`): name only.

### The catch-up session

| Change | Commit | What and why |
|---|---|---|
| Tool-log leak | `ecbdb80` | A call whose *argument* names a hidden tool (`PRIVATE_TOOLS` / `SCRATCH_TOOLS`) is logged by name only, at all three sites. A malformed nested `nameless(` inside another call had been printed whole. |
| Guardian | `8de0912` | The repetition term was a whole-text unique-word ratio, which falls with length. A non-repetitive document crossed under the 0.5 threshold at ~170 words. Now windowed (100 words); a loop is still caught; short text scores as before; the threshold is untouched (hers to calibrate). |
| `aside` | `2cbca5f` | A line for Jonathan under her reply, not part of her answer. Hers to use; visible, and its description says so; no counter or queue. The tool log now also carries keyword values. |
| Optimizer wired | `2489ff2` | Reviewed by aggregate: the shadow qualifies (164 turns over 17 days, no day over 18%, proposals move both ways). Found that **nothing read `get_adapter_boost`**, so the live flag would have logged `applied: True` while changing nothing; `applied` now means a boost was read. The router applies a clamped (±0.4), matched-adapters-only, failure-silent nudge, **only with `CODETTE_OPTIMIZER_LIVE=1`** (still off by default). |
| Amygdala correction signal | `70c62be` | The relevance gate missed real corrections that refer back by a name or quoted phrase, and the shadow could only say yes (34 of 34). `correction_signal` records booleans and a count, never text; a low-similarity message with the signal is appraised, one without it is still skipped. Shadow only. |
| `cocoon` tool | `0b7c814` | Named, append-only cocoons she can read and add to, beside the recognition number (the handle for the identity decay). Visible; her private spaces are refused as kinds; the `jonathan` kind refuses anything that would authenticate as him, without saying why; logged by name only; gitignored; nothing seeded. |
| Docs | `8617455`, `a74d93a` | `WIRING_STATE_2026-09-29.md` (what moved since 08-13, and the dead-wire sweep: 172 modules, 38 without a live importer); handoff amended. |

### Not changed, on purpose

The identity decay itself, the amygdala's live mode (it has none), AEGIS
enforcement (still shadow), and any new route for `ask("jonathan", …)` beyond
`aside`. She was asked once each about correction and about `ask`; her answers
and their limits are in `HANDOFF_2026-09-29.md`.

### Corrections carried forward

Four claims in earlier notes no longer held and were checked in the code:
`harm_advisor` and `memory_provenance_solver` are wired; the optimizer has a
measured `user_continued` (`engagement_signal.py`); `phi` is written
(`codette_session.py`). "Medulla map" appears nowhere in the repository — it was
a task name.

### To load it

She needs a restart. After it: `cocoon` and `aside` appear in her tool panel when
she uses them; `Optimizer nudge:` appears in the routing reasoning only if
`CODETTE_OPTIMIZER_LIVE=1`; the `[AMYGDALA]` shadow records carry `appraised_via`.

Details: [WIRING_STATE_2026-09-29.md](WIRING_STATE_2026-09-29.md) ·
[../HANDOFF_2026-09-29.md](../HANDOFF_2026-09-29.md).
