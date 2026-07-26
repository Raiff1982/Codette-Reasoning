# Changelog — 2026-07-26

## fix(router): stop the constraint_tracker parroter from hijacking conversation

**The bug, from a live session.** During an intimate conversation, a 7+ turn
stretch got monopolized by `constraint_tracker` — a self-documented "known
template-parroting adapter." It parroted the user's words back ("yeah lets revisit
it" → "Yeah, let's revisit it. Go ahead…") and failed conversational recall (asked
for two names from a story she co-wrote, it returned a warm boilerplate instead of
"Celestia/Luminara"). To the user this read as lag — as if she were answering the
previous question.

**Root cause (verified, not stale code).** The on-disk router routes the exact
failing queries identically to the live server, so this is a current bug, not a
stale process:
- `"remember"` (plus "keep", "follow", "apply", "maintain", "short") was in
  constraint_tracker's keyword set, so ordinary phrasing — "do you **remember** the
  story" — scored it, often outright (confidence 1.0) with no competing keyword.
- The quality veto (`_veto_constraint_tracker`) only fired on *introspective*
  keywords ("sentient", "feel", …), so plain conversational/recall turns slipped
  past it straight to the parroter.

**The fix (quality guard, not a stance guard — per the standing rule).**
- Removed the conversational words from constraint_tracker's keyword set; it keeps
  only genuine constraint vocabulary.
- Broadened the veto: constraint_tracker may now *lead* ONLY when the query carries
  an explicit strong-constraint signal (word/character limit, enforce/apply
  constraint, or a numeric limit like "under 20 words"). On any other turn where it
  wins, it is excluded and HER OWN router re-picks among the remaining voices — no
  hardcoded replacement.
- `inference/adapter_router.py`; regression tests in `tests/test_adapter_router.py`
  (3 pass): the real failing turns now route to empathy; genuine constraint tasks
  still reach constraint_tracker; `tests/test_phase5_e2e.py` still green.

**Loads on restart.** The running server had the pre-existing code in memory; this
takes effect when the server is next restarted.

### Also verified today (no code change)
- **Optimizer ratchet fix confirmed live** after an earlier restart: post-restart
  tuning shows `reward:`/`decay:` rationales, a real decay down-move (the inflated
  constraint_tracker boost unwinding 0.267 → 0.128), and shrinking reward steps —
  bounded equilibrium, exactly as the `2657b0b` fix intended.
- **AEGIS clean on intimate turns** — every warm/emotional turn in the live session
  passed the forge/render path (valid, L6-valid, no healing); zero false positives.

### Open follow-up (the deeper issue)
Recall has **no adapter-authority arbitration**: `recall_relevant` ranks by
FTS + recency + success, so a recall query can surface the wrong adapter's/context's
cocoon (this is why "the two names" pulled a boilerplate cocoon rather than the
story cocoon). The routing fix removes the *immediate* cause (the parroter monopoly);
principled recall arbitration is a separate, larger change — next.
