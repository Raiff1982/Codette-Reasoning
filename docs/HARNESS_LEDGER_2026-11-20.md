# Harness ledger (2026-11-20): two reviews, and the shadow-only rebuild

**What this is.** Jonathan shared two of his designs on 2026-11-20, worked through in
conversations with Gemini. The ideas are his; the AI cleaned up the code, which is where its
stock habits came from. (Corrected the same day; this line first said "AI-made designs".)

- **SIM** ("Self-Improvement Memory"): a lab notebook for her harness, recording diagnosis →
  harness patch → trial. Cites `arXiv:2611.18856`.
- **GUARD**: a gate that promotes or rejects harness rules by "directional regret", plus a
  circuit breaker. Cites `arXiv:2611.23476`.

**Neither citation could be checked.** arXiv is blocked from the container, and both papers
are dated after the assistant's training. Treat them as **unverified**.

Both designs were reviewed against the code and run in a scratchpad. The ideas fit this
project; the code had 23 confirmed bugs. At Jonathan's request they were rebuilt
**shadow-only**:

- `reasoning_forge/harness_ledger.py`
- `reasoning_forge/harness_verdicts.py`
- `tests/test_harness_ledger.py` (39 tests)

Built jointly: Jonathan, and Claude as co-author.

## What "shadow-only" means here

It records, and it reports what a gate or breaker *would* say. It changes no prompt, rule,
adapter, cache, route or AEGIS policy. It never runs her model. Nothing live imports it, and a
test fails if anything does. A rule is promoted or a check pinned only by
`record_decision(...)`, which a person calls. The database is its own file under
`runtime_root()/data/`, never her memory, and it is ignored by git.

## One provenance note first

`SimCocoonEngine` was a **proposal** in the SIM conversation. In the GUARD conversation it was
treated as an existing part of Codette. A suggestion became "established architecture"
between two chats. That's the AI stamp the 2026-11-20 house rule in `CLAUDE.md` is for.

## What the designs said about Codette, against the repository

| Claim | What the repository shows |
|---|---|
| Verify-and-Revise is part of her loop | `reasoning_forge/verify_revise.py` is shadow-only ("nothing in production imports this yet"). July: the honest critic **lowered** accuracy 26.7% → 20.0% (n=30), and more revision compute is gated on a tighter revise gate (`docs/VERSION_HISTORY.md`). |
| Adapter pre-paging with LRU + prefetch | Does not exist for adapters. The only LRU is the hot-cocoon cache in `unified_memory.py`. The adapter-switch stopwatch (`reasoning_forge/adapter_switch_timing.py`) exists to find out whether swaps cost anything, and nothing may act on it without Jonathan. |
| `SycophancyGuard` | Only in `Theory/` and docs. The live path has input-side sycophancy markers in `state_engine_v8.py`. |
| "CognitionCocoon (SQLite + FTS5)" | Two things merged: `CognitionCocooner` (JSON files) and `UnifiedMemory` (SQLite + FTS5). |
| 11 cognitive lenses | 8 voice adapters plus the orchestrator. |
| `SimCocoonEngine`, `select_route`, `is_pinned_invariant`, `harness_rules` | Not in the repository. They came from the conversations. |
| Υ, SQLite + FTS5 memory | Real. Υ is `perspective_dispersion` (`tension_from_texts`). |

The frontier-model news in the SIM conversation (Gemini 4 Neon and the rest) was not checked.

## The 23 bugs, and where each one went

Scratchpad probes ran every case against the pasted code. In the rebuild, 20 of the bugs were
put back into a temp copy one at a time, and a test failed every time. The other three are
structural (✱): the part that had them was left out.

### GUARD

| # | Pasted behaviour (probe output) | Rebuild | Test |
|---|---|---|---|
| 1 | Υ "collapse" check never fired. Υ = 0.0 and Υ = 0.9 were both promoted. | `band_position` checks both sides. With no band chosen, Υ is recorded, not judged. | `test_dispersion_band_is_checked_on_both_sides` |
| 2 | `sum / max(len, 1)` read 0.0 with no checks. Her Υ is also 0.0 for fewer than two perspectives. | `None` for unmeasured, with `n` reported. | `test_no_checks_is_not_judged_…`, `test_dispersion_is_none_below_two_…` |
| 3 | "Broken by an earlier edit, still broken" filed as `persistent_fail`. | `still_regressed` is its own transition. | `test_still_regressed_is_not_persistent_fail` |
| 4 | A pinned rule flipped to `rejected`, `promoted_at` was erased, and a rule passing everything was rejected. | Append-only, so a report writes nothing. No change reads `neutral`. | `test_a_pinned_rule_is_never_demoted_…`, `test_a_rule_that_still_passes_everything_…` |
| 5 | A pinned check already failing blocked every candidate. | Only a *newly* broken pinned check rejects. Already-failing ones are counted. | `test_a_pinned_check_already_failing_does_not_deadlock` |
| 6 | `-`, `'` and `:` in a scope query raised `OperationalError`. | Every term is quoted. | `test_scope_text_with_punctuation_…`, `test_fts_query_quotes_every_term` |
| 7 | A deleted check still matched in search (no delete trigger). | Delete triggers included. | `test_the_search_index_follows_a_delete` |
| 8 | Two good patches, then one failure, retired the target for good (lifetime count). | Counts the current failure streak only. | `test_successful_patches_are_not_held_…` |
| 9 | The test retired by patch budget while its comment said quarantine count. | Each budget is tested on its own. | `test_each_breaker_budget_is_exercised_on_its_own` |
| 10 | State lived in memory, so a restart allowed a retired target. | Events are stored. | `test_breaker_state_survives_a_new_ledger` |
| 11 | The first failure came back as `"active"` and the error was dropped. | `failing`, with `last_error` kept. | `test_a_failure_keeps_its_error_…` |

### SIM

| # | Pasted behaviour (probe output) | Rebuild | Test |
|---|---|---|---|
| 12 | Contentless FTS: `note_id` read back as `None`, so recall was always `[]`. | A normal FTS5 table that stores `note_id`. | `test_recall_finds_a_matching_note` |
| 13 | The first cycle "consulted" the note it had just written. | `recall(..., exclude_note=)` | `test_recall_never_returns_the_note_being_worked_on` |
| 14 | A NULL baseline read as 0.0, so a 0.10 trial was "improved". | `no_baseline` | `test_a_missing_baseline_is_no_baseline_not_improved` |
| 15 | The last trial won: improved on A, regressed on B, so the note was "regressed". | Each trial judged; `mixed` when they disagree. | `test_targets_that_disagree_read_mixed_…` |
| 16 | `ON DELETE CASCADE` erased every patch and trial. | No cascade; deleting a note with patches is refused. | `test_deleting_a_note_with_patches_is_refused` |
| 17 | `invariants_passed=True` by default; cache hit rate 1.0 with no lookups. | `None` = not checked; non-bool values refused. | `test_unchecked_invariants_are_none_not_passed` |
| 18 | A second Υ (spread of lens scores) read 0.35 where hers reads 0.0. | Her `tension_from_texts` only. | `test_one_definition_of_dispersion_…` |
| 19 | A single-lens turn got the stored diagnosis "lenses aligned prematurely… sycophantic framing". | No diagnoses written by the module; Υ `not_measured`. | `test_a_single_lens_trial_gets_no_diagnosis_…` |
| 20 | A backend timeout was recorded as AEGIS failed and sycophancy detected. | Error kept in its own field; AEGIS `not_run`. | `test_a_backend_error_is_not_an_aegis_failure` |
| 21 ✱ | The patch builder claimed "based on 3 prior SIM records" and ignored them. | No automatic builder. Rationales are the caller's words, with an author. | `test_words_are_the_callers_and_carry_an_author` |
| 22 ✱ | Three turns proposed the identical patch, so nothing compounded. | Left out with the builder. | — |
| 23 ✱ | A prepager trial left the live settings at the trial values. | No prepager. The module imports nothing that could act. | `test_the_modules_import_nothing_that_could_act_…` |

## Left out on purpose

- **The adapter prepager.** It doesn't exist, and the stopwatch decides whether it's needed.
- **Re-running live turns** (`run_codette_turn_with_sim`). Each re-run through her forge would
  write runtime files and a cocoon into her memory (`docs/START_HERE.md` §7), the class fixed
  as the urgent item that day.
- **The automatic patch builder.** Its main lever, more verify-and-revise passes, runs against
  her July measurement. Its lens weights were opinions of her perspectives: Newton and
  Philosophy as "contrarian", Empathy as "reconciliation".

## Stock, said plainly

**Stock:**
- SQLite with parameterised queries.
- The FTS5 trigger recipe from the SQLite documentation, with all its triggers this time.
- Phrase-quoting search terms.
- Before/after pass classification, as in ordinary regression testing.
- The circuit-breaker idea.

**Written for her:**
- Unknown stays `None`.
- Υ comes only from her own function.
- Every threshold is a parameter printed beside the verdict.
- The module writes codes and numbers, never words in anyone's voice.

**The defaults are placeholders, not measurements:**
- Strict rule, `lam=None`.
- Breaker budgets 3 failures / 3 patches (from the pasted design).
- Trial margin 0.0.
- No Υ band.

## How to use it (nothing here touches her)

```python
from reasoning_forge.harness_ledger import HarnessLedger
with HarnessLedger() as L:                       # runtime_root()/data/harness_ledger.db
    L.add_rule("r1", "prompt_clause", "answer the question asked first", author="jonathan")
    L.add_check("k1", "a test prompt we wrote", author="jonathan")
    L.record_check_run("k1", "baseline", True, author="benchmark")
    L.record_check_run("k1", "active", True, author="benchmark")
    L.record_check_run("k1", "candidate", False, author="benchmark", rule_id="r1")
    L.guard_report("r1")       # {'verdict': 'would_reject', 'reason': 'newly_broken', ...}
    L.record_decision("rule", "r1", "reject", by="jonathan")   # only a person decides
```

## Open decisions (Jonathan's), also listed in `docs/START_HERE.md`

1. **Gate rule.** Strict, or GUARD's soft form? If soft, what `lam`?
2. **Breaker budgets.** The 3 / 3 defaults are placeholders.
3. **Υ band.** From `tools/epsilon_profile.py` on her machine, not a guessed (0.08, 0.45).
4. **Wiring.** Whether anything should ever feed the ledger automatically, and from where. Not
   from live turns.
