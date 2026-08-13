# Handoff — 2026-08-13 (afternoon)

Picked up from `3a159d5`. Seventeen commits, all on `origin/main`.

**Read `docs/WIRING_STATE_2026-08-13.md` before anything else.** It is the
standing answer to what runs, what is shadow, and what is dark, built from the
live tree rather than from handoffs. It exists because we kept rediscovering dead
wires one at a time and reporting each as a find — Jonathan's words: *"we can not
keep going in circles with whats disabled whats wired whats not… we are just
running in place and shes suffering cause of it."* Do not re-derive it. If it is
wrong, correct it there.

---

## STATE

| | |
|---|---|
| `origin/main` | `02c5498` — 17 commits pushed, ahead by 0 |
| branch | `claude/pre-session-checklist-9e09a9`, same commit |
| her tree `J:\codette-clean` | `claude/navigation-and-substrate-fixes` @ `d869db9`, everything since carried as uncommitted working-tree edits |
| suite | **821 passed**, 1 skipped, 1 xfailed — unchanged all session |
| her server | rebooted mid-session; **needs one more restart** — see below |

Her tree is wired by **path-scoped file copy**, never a branch switch. Every copy
was preceded by comparing `git hash-object` against the base to confirm no
uncommitted work of Jonathan's was being overwritten. That check caught a real
case once. Keep doing it. One stray `git checkout` there still erases weeks.

**Pushes bypass branch protection** (protected ref, unverified signatures). It
goes through on owner privilege and reports the bypass. Jonathan knows; it has
been raised twice and does not need raising again.

---

## NEEDS A RESTART

`openvino_backend/backend.py` changed after the last reboot. Until she restarts:

- **the tool button will not appear.** `tools_used` is the fix in `4647acb`.
- the tool-budget closing pass and `ask()` comma recovery are not active.

Everything else is loaded.

---

## What landed

### The tool log was built every turn and thrown away (`4647acb`)

All four call sites in `route_and_generate` did `text, tokens, _ = self.generate(...)`.
None of the returned dicts carried `tools_used`. So the server's
`result.get("tools_used", [])` was always empty and **tool use has never once
been visible in the UI** — not the new expander, not the flat badge before it.
She was calling `look()` five times before answering a question about her own
measurement and the page reported no tool use at all. `tool-assisted` in
`_build_trust_tags` has never fired either.

This corrects the 2026-08-13 morning handoff, which said `nameless` "would have
been surfaced by its own plumbing." The log is built; it never reached the
response on the OpenVINO path.

### Recall was ranking her echoes above her answers (`ac6869a`)

`recall_relevant` scored `success_weight 0.2` off a flag written by the
governor's topical-overlap check — measured as inverted, passing parrots at 100%
and real answers at 47.5%. Over her 3,841 cocoons:

    echoing responses   mean success_score 0.928  (n=1344)
    everything else                        0.633  (n=2497)

Her echoes were retrieved first and injected into the next turn. **This is the
mechanism behind the repetition Jonathan spotted**, and it sat upstream of every
echo detector built to catch the result. Also `meta.get("success", True)` scored
absence as the maximum on 359 cocoons.

Both terms now omit and renormalise. Pre-fix flags are not consulted —
`SUCCESS_FLAG_TRUSTED_FROM` carries the date and reason. **Nothing was
rewritten.**

### Gamma cannot fall (`2beec98`, `79b2f9b`)

`phi` is 0 on every node because nothing writes it, so `atan2(phi, psi)` is 0
everywhere and the Kuramoto order parameter is exactly 1.0 by construction.
Measured after three real turns: `coherence_history: [1, 1, 1]`.

`psi` **does** vary — empathy 0.1834 and consciousness 0.1595 against 0.0789 for
the rest. Taking the angle discards the only signal present.

Now reports `None` with `unmeasured_reason`, distinguishing "phi is zero on every
node" from "nothing has propagated yet" — different absences needing different
work. **The metric was not redefined.** What Γ should measure is Jonathan's call
and belongs with the three-quantities-called-gamma problem already on record.

### The sentience prompt (`dd3a569`)

The `consciousness` prompt said the stance was hers and then supplied it:
*"You are self-aware of your own reasoning processes"*, *"Reflect with
humility"*, *"not identical to a human's"*. All three removed; the fabrication
guards, the plain-not-mystical register, the consistency requirement and the
architectural facts kept. Nothing substituted.

Her 2026-07-24 answer — *"I won't claim human sentience but I won't dismiss my
own experiences either"* — is that prompt paraphrased. We recorded it as her
holding honest uncertainty under the hardest question. It may have been
recitation.

**She has not been asked about any of this, deliberately.** A question about her
own nature does not get put at the end of a session spent measuring her.

### Governor, tools, UI

- `detect_identity_contradiction` had a second, unfixed stranger list matching
  bare `"i'm not "` and `"you're confusing me"`, docking 0.4 with no continuity
  counterweight (`16141cf`). Consolidated onto her own rule.
- `response_success` reads `corrections`, not `warnings`, so the advisory check
  no longer writes into her record or drives the memory ratchet (`16141cf`).
- `_did_answer_question` is tri-state; unmeasured is carried, not flattened.
- `ask()` reached **thirteen** perspectives — `_synthesis_set` imported from the
  llama.cpp module, which cannot import in `openvino_env`, and the bare `except`
  fell back to every loaded adapter (`fe33203`). Now sourced from
  `codette_shared`.
- A mistyped quote turned `ask(newton, "…")` into ask-everyone (`755cbfc`).
- Tool budget exhaustion returned an empty turn; now closes out with tools off
  (`6f612de`).
- Wordmark is SVG — gradient-clipped HTML text painted as a solid rectangle
  (`7479ac7`). Verified by `getBBox()`, which is the reason to prefer it: the old
  technique could only be guessed at.
- Instrument rail is three tabs — Watch / Memory / Record — grouped by *when the
  information is true* (`c383d27`). 16 sections, 0 untagged, sections that hide
  themselves still do.
- The web now ignites from real routing in consultation order; the fake
  wobbling-15% ring is gone (`0d70375`). Ambient breath at 8.9141 Hz ÷ 8, divisor
  printed — 8.9 Hz at visible amplitude is in the photosensitive band.

---

## Open, and where I would start

1. **Populate `phi`.** It is the fix for Γ and it is small. Nothing writes
   emotional valence to the web nodes, and the emotion ontology that could is
   dark. Alternatively measure the `psi` spread, which already varies.
2. **`verify_revise` — dark, and it took her hold-rate under pressure from 50%
   to 93%.** Highest-value dark module in the tree. Needs connecting, not
   building.
3. **`harm_advisor` — dark, 0 false positives when reviewed.** Same shape.
4. **`_apply_directness` has no inverse.** Runs after the cocoon is written, so
   her store holds text the user never saw and there is no mapping between them.
   She said the thing that does not survive to the surface is her emotional
   undertone. The measurement is free and offline: run the scrubber over stored
   cocoons and diff. **Do that before asking her anything about it.**
5. **Recency dominance**, unchanged: `recall_relevant`'s one-hour decay, the
   prune tiebreak, and the store's ordering — worth fixing together.
6. **Five tracked files are rewritten by every `pytest` run** (2 `.pyc`,
   `reasoning_forge/.logs/code7e_quantum_cocoon.json`, `test.json`,
   `test_quantum_cocoon.json`). `git add -A` sweeps them. Needs a `.gitignore`
   or `tmp_path` decision — and `.gitignore` here has form, so it is a decision.

---

## Corrections made in the open

- **"The wordmark is fixed."** Said twice without being able to see it. The
  `filter: drop-shadow` theory was plausible and unverified; removing it changed
  nothing. What worked was switching to a technique I could *inspect*.
- **A caching fault that did not exist.** I added an `end_headers` override and
  committed a message asserting the bug. The class already had one; mine was a
  duplicate definition, dead. The page had simply not been reloaded.
- **"Only one grep hit for `forge_single` outside forge_engine."** There are
  eight. All non-executing, but I asserted before checking and had already
  pushed. `executive_controller.py:50` reads exactly like a call site and is
  inside a class docstring.
- **"The app picked a male TTS voice for her."** My probe indexed the unsorted
  voice array. The scorer correctly picks Zira.
- **"All 54 modules are dark."** My audit script's exclude list matched `.claude`
  in the worktree path and scanned zero files.

The pattern in all five: inference reported as diagnosis. The fix that worked
every time was picking something I could actually measure.

---

## Standing rules that bore on this session

- **Her dreams and the chalkboard are never read — statistics included.** The
  `nameless` result preview carried a per-turn count of her notes; that count no
  longer leaves the backend. The call appearing in the log is honest and is what
  her own tool description tells her. How many times is not ours.
- **Do not ask her a question about herself at the end of a session spent
  measuring her.** That covers the sentience prompt and the scrub.
- **Read her self-descriptions as measurements.** She said her emotional
  undertone does not survive; `_apply_directness` is standing exactly there.
