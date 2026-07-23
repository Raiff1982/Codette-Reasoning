# Archive — 2026-07-23

Working-tree cleanup after the Phase 0 write-up landed (commit `a5398f8`).
Nothing here is referenced by running code. Kept rather than deleted because
each item is either a record of something that happened or a rollback artifact.

## git-history-scripts/
One-off tools written 2026-07-20 to purge `results.zip` from git history and
force-push the rewritten branch. That job is done. **Do not re-run these** —
they perform history rewrites and force-pushes against `origin/main`.

## gpqa-n10-smoketest/
The four n=10 GPQA runs from 2026-07-22 (05:30–06:24). These are the accidental
smoke test that ran while the real study was already complete. They independently
reproduced the parse-fail mechanism (no_locks 10% w/ 3 parse-fails vs control 30%),
so they are kept as a replication record — but they are **not** the study data.

The study data is the July 17 n=50 arms in `data/results/gpqa_codette_reason_2026071*.json`
(tracked) and `data/results/phase0/` (tracked). This smoke test previously
overwrote the `phase0/` bench files with n=10 output; that was reverted from HEAD
on 2026-07-23. See `paper/phase0_ablation.md`.

Note: the `no_complexity` arm here died mid-run (server connection lost after
row 1) and is incomplete.

## superseded-binaries/
`codette_core.pyd.v024backup` — the pre-rebuild Rust extension (pyo3 0.24.2),
kept as rollback when the extension was rebuilt against pyo3 0.29.0 for the
Dependabot advisories (commits `2ffa429`, `c73047e`). The 0.29.0 build has been
in service since and is loading fine ("Rust extension loaded — FFT running at
native speed"). Safe to delete once you're confident there's no regression.

## optimizer-contaminated-run/
The first router self-tuner shadow collection (2026-07-12 → 07-22, 476 turns) and
the state it learned. **Retired, not deleted — do not feed this back in.**

Review finding: the collection is 52% benchmark traffic from a single day. All
155 `adapter_boost_newton` proposals fired on GPQA days (07-17: 246 turns, 100%
newton, 146 boosts; 07-22: 33 turns, 9 boosts). On the eight non-benchmark days:
**0 boost proposals**. Applying the run would have raised newton by **+2.83** —
a conversational routing preference learned entirely from multiple-choice exams.
GPQA routes to newton by design, so the optimizer was reading its own benchmark
harness as evidence about how Codette should think.

Two defects fixed on 2026-07-23 before re-collection:
1. No benchmark guard on the optimizer feed. The `_is_benchmark` exclusion already
   protected cocooning, coherence anchors, and continuity summaries; the optimizer
   was never added to that perimeter. Now guarded at both feed sites
   (`codette_session.update_after_response`, `optimizer_shadow.observe`).
2. `user_continued` was hardcoded `True` — a constant +0.10 on every quality score,
   claiming an engagement measurement never taken. Now `Optional[bool] = None`,
   omitted from the reward with weights renormalized.

`optimizer_state.json` here is additionally invalid because its `best_score`
(0.89983775) was computed on the pre-fix inflated scale. Re-collection starts from
zero state. Nothing was ever applied — the whole run was shadow (`applied: false`
on all 476 records), which is the reason this was caught before it touched routing.

`*.prefix_bak` / `*.synthetic_bak` are older backups swept up in the same reset.

## test-artifacts/
Small scratch outputs from 2026-07-21 (`test.json`, `test_quantum_cocoon.json`).
No known consumer.

---

**Not archived, deliberately:** `aegis_metrics.db` stays at repo root — it is live
runtime state created by `inference/codette_server.py:510` on startup, not junk.
It is regenerable (delete + restart clears metrics) and is now gitignored.
