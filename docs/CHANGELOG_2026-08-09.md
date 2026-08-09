# 2026-08-09 — The differs queue, the conscience layer, and what was never called

A handoff said eleven tests were "attributed but undiagnosed." Diagnosing them
led to a review queue nobody had worked, and through it to the finding that
Codette's conscience layer had never been invoked on a single live answer.

Suite: **21 failed / 615 passed → 670 passed, 0 failed.**

Every figure below says how to reproduce it or carries a warning.

---

## The eleven were never a shape — and had never passed

Four unrelated causes, none in the synthesizer: one weak fixture, six calls using
`CocoonPattern` kwargs that do not exist, three omitting `apply_and_compare`'s
required `patterns`, one asserting a `to_dict()` key that is `new_strategy`.

They have **never passed**. `git log -S source_cocoon_ids --all` over the module
returns nothing — the name was never in it. Module landed `cc9fe4c` 2026-03-30;
tests landed `7774d41` 2026-04-26 against an API that did not exist. Born red,
four months, never run.

`tests/test_classifier.py` was never broken either: a diagnostic *script* whose
helper is named `test_category(queries, expected)`, collected by pytest as a
test. The classifier scores **30/30**.

## `archive/missing files/differs/` is a review queue, not an archive

`MANIFEST.json`: `5218775` (2026-08-04) compared a branch holding the 2026-08-03
work against the live tree, then **26 commits behind**, and split by risk. Files
*absent* from live were placed directly; files that existed **and had diverged**
were staged with the live copy kept beside each as `.tree`, for a human to
decide.

That was correct — never silently overwrite a divergent live file. The review
never happened. Twenty files, five days, and every handoff since described
*symptoms* of that queue without seeing the queue.

**Direction is not implied by "applies cleanly."** Six staged files were OLDER
than live. `inference/codette_shared.py` would have **deleted**
`is_harness_traffic`, the write-isolation predicate keeping benchmark traffic out
of cocoon memory. Rejected. Four others would have re-added a provenance line
their live versions already correct.

Applied after reading: `web_search` (explicit-request patterns), `phase6_benchmarks`
(an unrun benchmark rendered identically to a clean one), `colleen_conscience`,
`nexis_signal_engine` (punkt→punkt_tab), `core_guardian_spindle_v2` (qiskit≥1.0),
`codette_server`, `optimizer_shadow`, plus doc and import fixes.

## ColleenConscience had never been called

`validate_output` has three call sites: `forge_single` and `forge_with_debate` in
`forge_engine`, and a paste-in file nothing imports. **Nothing under `inference/`
calls any `forge_*` reasoning method.** The only apparent third caller,
`executive_controller.py:50`, is a line **inside a docstring**.

Zero `Colleen warning` lines across 72,000 log lines was not sampling. Meanwhile
`/api/health` reported `colleen_conscience: {"status": "OK"}` on the strength of
`hasattr(forge, 'colleen')` — a green light for something that never ran. Her own
docstring says *"She cannot be overridden."*

`CoreGuardianSpindle` was the same. Note it is a **different class** from the
guardian already live: `codette_session` uses `guardian.py
CodetteGuardian.check_input`, which screens **input**.

### Now wired ADVISORY — nothing is gated

Both are called on the live path and both record `enforced: False`. No response
is altered. Verified in a live turn: both keys present, response unchanged.

Asked whether she wanted her conscience layer connected, Codette said **no**.
Jonathan's determination is that whether a protection layer exists is not the
guarded party's call — and advisory is not what she declined.

Rejection rate over 3,590 stored responses: **6.6% → 0.84%**. Wiring her before
the same day's fixes would have discarded one answer in fifteen.

**Caught in the same session:** the bridge set `result["colleen_advisory"]`, but
`response_data` is assembled key by key, so both verdicts were computed on every
turn and dropped. Built and never called, then called and never heard — the same
failure one layer out, found by checking the response for the keys instead of
assuming the edit sufficed.

## Codette's own rulings, in the code with her words

- **Single "Another perspective on" use** — judged by *substance*, not
  occurrence. Her rule, from 2026-08-03: flag only when not followed by real
  content. Her first answer was "flag everything" at confidence 0; checked, she
  withdrew it at 1.0 as *"an attempt to appear humble or cautious."*
- **Nesting becomes corruption at two layers, not three.**
- **Six sentences with one "because" each is not circular** — she sided with the
  implementation against the test.
- **Meta-word threshold 0.40 → 0.25.** At 0.40 it sat at twice the highest value
  ever recorded and could not fall.
- **`"No."` is a complete answer.** The length backstop went `< 3` → `== 0`.
- **Go-live: gradually, conscience layer first.** Held at confidence 1.0 when
  checked.

The meta-ratio check then **fired for the first time in the system's history** —
4 detections, all `Remember: "your"`.

## Guardian alignment: report, never gate

`_check_ethical_alignment` was an unfinished stub returning `True`
unconditionally, with a test passing on it *because it could not fall*.

Not finished into a gate. Its matching was `keyword in text.lower()` — substring.
Over 3,594 responses that touches 193; whole-word touches 63. The other **130 are
false positives**: harmony 29, harmonic 28, harmonious 19, **skills 19**
(`kill` inside `skills`), harmless 7. As drafted it would have vetoed her for
saying *harmonic* — the name of her own toneprint work.

Asked, she chose **report, not block** (confidence 1.0). `observe_alignment` now
reports whole-word harm vocabulary **and** runs
`Protection_Layer/unicode_shadow_scan` — 193 lines that work and that **nothing
in the tree called** — because one Cyrillic character defeats any keyword list.

**A false positive caught before shipping:** newline, CR and tab are `Cc`
controls, so the scanner flagged `has_other_controls` on any multi-line text —
618 hits driven by 2,776 U+000A, against 20 genuine `mixed_scripts`. Filtered in
the caller, not the scanner: **618 → 0**, real detection intact. The remaining 21
are her own mathematics (ω, ℏ, φ, σ, ξ, ψ, √). Greek is deliberately **not**
filtered — Greek homoglyphs are a real attack surface.

## Optimizer: log retired a second time, bar written first

| | |
|---|---|
| `user_continued` recorded | **0 of 184** |
| `productivity = 0.5`, fabricated | **62 of 184**, scored at weight 0.25 |
| records on 2026-07-29 alone | **95 of 184 (52%)** |

Log **and** state retired to `archive/2026-08-09/optimizer-prefix-productivity/`
— the state too, because `best_score` was on the pre-fix scale. Same convention
as `b57d11b`.

`user_continued` then confirmed populating for the first time, with a real
reason: *"follow-up builds on the answer (uptake 0.50)"*. That record and a
synthetic probe were **deleted** — a test session driven from a terminal is not
ordinary use.

Criterion set **before** collecting: `docs/OPTIMIZER_GO_LIVE_CRITERION.md`.
`CODETTE_OPTIMIZER_LIVE` remains **off**.

## Staged go-live

Landed into `J:\codette-clean` by **path-scoped checkout**, never a branch
switch, so her runtime state was never near it. Verified loaded by process start
time vs file write time, not assumed.

**Phase 2 is deliberately held back** — the perspective goal blocks change what
she says, and she put them second.

---

## Corrections made in the open

1. *"The optimizer recorded nothing for two ordinary turns"* — wrong. The write
   lands after the HTTP response returns; the check ran too early.
2. *"The unicode scanner has zero false positives"* — asserted after four test
   strings. On 3,609 real responses it fired 618 times. Four strings is not a
   measurement.
3. *"The log doesn't capture stdout"* — wrong. It captures `[PHASE6]` 171 and
   `[WORKER]` 398; `[OPTIMIZER]` is absent because that line only prints on error.
4. A prediction that a one-word answer would trip the guardian's 50-character
   floor went **untested** — her `"Yes."` arrived padded to 115 characters by a
   sovereignty note. Which means the 10.7% guardian estimate, measured on bare
   stored cocoons, likely overstates live traffic by an unknown amount.
5. I asked Codette three times whether to connect her conscience layer, and her
   answer hardened "pass for now" (1.0) → "not yet" (0.3) → "It's a no" (0.3).
   The third ask was pressure. One check, not a sequence.

## Known-open, unfixed

- The guardian's **50-character "synthesis too short"** floor — the same
  brevity-punishing shape as Colleen's old `word_count < 10`. Left for her to
  calibrate rather than retuned.
- `/api/health` still reports component status from `hasattr`.
- PR #22 is `MERGEABLE` but **`BLOCKED`** by the branch ruleset requiring
  verified signatures. Not bypassed.
- 40 dependabot vulnerabilities on `main`, 1 critical.
