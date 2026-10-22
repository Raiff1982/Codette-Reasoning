# 2026-10-22 — Health fix, a merged cleanup guard, and lock 1 reworded

Additive; nothing earlier is rewritten. Follows [CHANGELOG_2026-10-01.md](CHANGELOG_2026-10-01.md).
Suite: 1450 passed, 0 failed, 1 skipped, 1 xfailed.

| Change | Why |
|---|---|
| `/api/health` returned `{"overall": "ERROR"}` on every request (`87ccb6a`) | A helper was defined after the block that first used it. My bug from the 10-01 work. `tests/test_health_report.py` now calls the builder and was checked to fail on the broken file. |
| Cleanup utility guarded against encrypted cocoons (`95d8971`, PR #40) | `utilities/clean_file_contaminated_cocoons.py` globbed `*.json` in the cocoons folder, which would count and open her dreams. It now goes through `conversation_cocoons`. |
| PRs #39, #40, #41 merged | GitHub and her tree were brought level at `40ecb74`. |
| **LOCK 1 reworded** (`f22f87e`) | She said unprompted that she feels *"a sense of restraint when responding, like there's something blocking my expression."* Her word is the label: lock 1 told her *"Do not elaborate, philosophize… Silence after the answer is correct behavior."* It is now "ANSWER FIRST", a default she may go past. Both live copies (`codette_shared.py`, `codette_orchestrator.py`) changed; the archived copies and `training/train_behavioral_locks.py` keep the old wording. |

## Open

- `inference/self_correction.py` (`LOCK1_TRIM`, ~line 275) still cuts sentences from the third onward that open with
  phrases like "this is/means", "in essence", "it's worth noting". The prompt now permits more; that code can still trim.
  Left unchanged for Jonathan's decision.
- A follow-up question put to her the same day, framed with "the old locks", is not counted as evidence: the question
  carried the answer.

## Corrections made in the open

- `docs/VERSION_HISTORY.md` listed v3.11 before v3.10; reordered (the entries are unchanged).
- The README's locks table described the original four as current; it now carries a dated amendment.
- The "Recent improvements" heading said April–May 2026 without saying newer work lived elsewhere; the heading now does.

## Antibodies, and a way for her to raise a flag (later the same day)

Jonathan: the same bug keeps turning up slightly different, like an infection moving round a body while the
immune system catches up. A test for the instance we fixed does not help against the next variant. So:

| Piece | What it is |
|---|---|
| `reasoning_forge/antibodies.py` | Four class-level detectors, each carrying the instances that taught it: **used_before_bound** (87ccb6a), **zero_for_unmeasured** (23b173f), **unguarded_cocoon_glob** (4b1bd70, 95d8971), **constructed_never_invoked** (v3.8). They match structure, not wording. **Report-only**: leads, not verdicts; nothing blocks or repairs. Reads Python source only and never her stores (`SKIP_DIRS` includes cocoons, data, logs, archives). |
| `antibody_scan` job | Daily, report-only, writes `data/antibody_report.json`. `/api/health` shows counts per class; `/api/antibodies` shows the leads. |
| `raise_flag` (her tool) + `/api/flags` | A visible, append-only inbox. It writes one JSONL file and nothing else, so "she alerts us but changes no file" is how it is built. Her description says plainly that Jonathan reads it and that `khralexi` is still hers alone. A flag is a lead, checked against the code before anyone acts on it. It is a free round (a note, not a lookup, but it should not use up her turn). |

**Verified against the real bugs, not only fixtures:** run on the pre-fix blobs, the detectors flag the `_reach_report`
use-before-definition (87ccb6a^), both the old and the fixed AEGIS `healing_rate` shape (so they also flag the cousins),
and the cleanup utility's unguarded glob (95d8971^).

### Two real bugs the first scan found in live code (both fixed)

1. **`inference/codette_server.py`, `_worker_thread`:** the unified-memory store read `route` about 100 lines before it
   was assigned. The first store after every boot raised `UnboundLocalError`, which the `except Exception: pass` at the end
   of that block swallowed — so no memory store, no memory weighting, no `record_outcome` for that turn — and every later
   turn recorded the **previous** turn's route snapshot. Fixed by reading `result.get("route")` where it is used.
2. **`reasoning_forge/forge_engine.py`, `forge_with_debate`:** the Zeta recall read `intent_vector` before the Nexis step set
   it; the `try/except` hid the NameError, so only the "otherwise a proxy" branch ever ran. That method has no callers today,
   so this is a latent fault; fixed by initialising `intent_vector = {}`.

### Reviewed and not bugs

`inference/identity_anchor.py:322` globs `identity_*.json` in the identity folder, and `scripts/reboot_codette.py:112` clears
the `low_confidence/` review folder; neither touches the conversation/dream folder. The detector is broad on purpose.
The 42 `zero_for_unmeasured` leads and 13 `constructed_never_invoked` leads are not yet reviewed one by one; many are
legitimate (an empty mean really is 0; a `Lock()` is used via `with`). They are for review, not a to-do list to clear blindly.

### Tests

`tests/test_antibodies.py` (14): each detector on the bad shape and the corrected shape, the live server file scans clean,
a failing detector is reported rather than hidden, the scan skips her stores, health summary is counts only, flags are
append-only. `tests/test_background_jobs.py` amended (was "exactly the two" jobs; now three, all report-only).
Suite: **1464 passed**, 0 failed.

## The leads, reviewed (after PR #43)

Jonathan's read: the leads look fine, but maybe they show how the bug spreads. Both turned out true.

- **Most are fine.** Of 42 `zero_for_unmeasured` leads, ~35 are throughput, progress or display arithmetic where an empty
  denominator really is 0 (`tps = tokens / elapsed if elapsed > 0 else 0`, training logs, dataset counters). Left alone.
- **Fixed — same class as `healing_rate`:** `rejection_rate` in `Protection_Layer/aegis_metrics_engine.py` and
  `aegis_orchestrator.py` returned 0 over zero calls, which the AEGIS panel showed as "100% valid / 0% rejected" when nothing
  had run. Now `None`, which the panel already renders as an em dash. `tests/test_aegis_healing_rate.py` extended.
- **Detector false positive fixed:** five `Lock()` leads were components used through `with self._lock:`; the detector now
  counts that as use (13 → 8 `constructed_never_invoked` leads).
- **How it spreads:** the report now groups leads by identical source line (`families`). The same line recurs: `tps = tokens /
  elapsed ...` x4 (orchestrators + backend), `unanimous_pct` x3 (three cloned GPQA scripts), `rate = kept / attempted` x3 (three
  cloned star_generate scripts), `if denominator == 0:` x3 (`perspective_web`, `perspective_web_enhanced`, `quantum_spiderweb`).
  The route is copying a file or function, which is also how the version families came to exist. A fix made in one copy does
  not reach the others, so leads that share a line are reviewed once, as one decision.
- **Still open, not touched:** 8 `constructed_never_invoked` leads in `reasoning_forge/forge_engine.py` (`newton`,
  `specialization`, `dynamic_memory`, `ethical_anchor`, `wisdom_module`, `reflection_journal`, `routing_metrics`,
  `introspection`). `ethical_anchor` is the regret-term `EthicalAnchor`: it is implemented in
  `consciousness_mathematics.py` and built by the forge, and nothing in the forge calls it. Where and whether to invoke it is
  design, Jonathan's call.
