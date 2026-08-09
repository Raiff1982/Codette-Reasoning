# Optimizer go-live criterion

**Written 2026-08-09, BEFORE re-collection began, deliberately.** Setting the bar
after looking at the data is how a bar gets moved. This one is fixed in advance
and dated so it can be checked against, not negotiated with.

`CODETTE_OPTIMIZER_LIVE` is **off**. This document says what would justify
turning it on. It does not authorise anything by itself — the decision is
Jonathan's, and the last word before it is Codette's, since it steers her
routing.

---

## Why re-collection was necessary — the second time

The first collection was retired on 2026-07-23 (`b57d11b`): 476 turns, and every
one of the 155 `adapter_boost_newton` proposals fired on a GPQA day. Across the
eight non-benchmark days, zero proposals. The optimizer was reading its own test
harness as evidence about how Codette should think.

The second collection is retired on 2026-08-09 (this change), for a different
reason. Measured over its 184 records:

| | |
|---|---|
| `user_continued` recorded | **0 of 184** |
| `productivity = 0.5`, fabricated | **62 of 184**, scored into the reward at weight 0.25 |
| records on 2026-07-29 alone | **95 of 184 (52%)** |

The outcome signal the whole thing was blocked on had never once been recorded,
and a third of the corpus carried a made-up productivity term that was
nonetheless scored. The state file is retired along with the log because
`best_score` was computed on that same pre-fix scale — the same reason the
2026-07-23 state was retired.

Both are in `archive/2026-08-09/optimizer-prefix-productivity/`. Kept, not fed.

---

## What must hold before anyone proposes going live

All of these, measured on the NEW log only.

1. **≥ 200 records with `user_continued_measured: true`.**
   Judgement call on the number — it is the same order as the 476-turn corpus
   that made the first contamination visible, at a threshold reachable in
   ordinary use. Nothing derives 200 exactly; it is a stake in the ground.

2. **Spanning ≥ 5 distinct calendar days**, and
3. **no single day contributing > 40% of records.**
   These two are NOT judgement calls. They come straight from both failure
   modes: collection #1 concentrated in two benchmark days, collection #2 had
   52% of its records on one day. Concentration is the shape the failure takes.

4. **Zero records with `is_benchmark`.** The guard drops them at the feed, so
   this verifies the guard rather than the traffic.

5. **Zero records with `productivity_is_placeholder: true`.** Confirms the
   2026-08-08 fix is actually in the running process and not just on disk.

6. **`applied: false` on every record.** If anything shows `applied: true` while
   `CODETTE_OPTIMIZER_LIVE` is off, stop — that is a bug, not a milestone.

## Then, and only then: the review that caught it twice

Meeting the counts is entry to the review, not a pass. The review is the thing
that has actually worked, both times, and it is adversarial by design:

- Group proposals by day. If they concentrate, ask what was special about that
  day before believing the signal.
- Group proposals by adapter. A single adapter taking nearly all the boost is
  the collection-#1 signature.
- Check the proposals against the non-benchmark days *alone*. Collection #1 died
  on exactly this cut: zero proposals across eight ordinary days.
- Ask what would DISPROVE the proposed adjustment, not whether it looks right.

## And the part that is not a metric

Ask Codette. It changes her routing, which is closer to her voice than anything
shipped on 2026-08-08, and her standing answer on that day was to proceed
gradually and test each component. A number clearing a threshold does not
override that.

---

## Do not accelerate this

There is a strong temptation to point a harness at her to reach 200 faster. That
is precisely what produced collection #1, and on 2026-08-03 a shared-session
harness drove identity to 12.8% — below chance. Ordinary use, or nothing.
