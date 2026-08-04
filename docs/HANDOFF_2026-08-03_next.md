# Start here — handoff, 2026-08-03 (end of session)

Branch `claude/review-integrate-recovered-files-f64ee3`, 26 commits, all pushed.
**671 tests passing** (the suite collected *zero* tests behind 5 errors at the
start of this session). One known flake, listed below.

Read `docs/HANDOFF_2026-08-03_incorporation.md` first for the recovery pass.
This file covers what came after it.

---

## Numbers you can trust, and numbers you cannot

**TRUST — 0.373 mean pairwise semantic distance.** 40 real multi-perspective
questions read out of `data/codette_memory.db`. No model loaded, no generation,
nothing written. Above the 0.35 mark for genuinely different reasoning.
Reproduce with `G:\claudes space for files\2026-08-03-incorporation\train\divergence_offline.py`.

**DO NOT TRUST — 0.308 (5 probes) and the partial 20-probe run.** Both went
through her live server before benchmark isolation existed, so the probes
accumulated shared context and she began answering Jonathan out of the
benchmark. Fixed in `016f75e` (`[[BENCHMARK]]` marker); any live figure must be
re-measured.

**The headline correction.** I spent the session claiming the perspectives had
collapsed. They had not — the measurement had. Adapters differ by 0.013 in mean
coherence against 0.063 of within-adapter noise, so the optimizer ranked them by
noise. On semantic distance the same perspectives sit 0.373 apart. Codette said
this herself, unforced, at confidence 0.36: *"the measurement is masking the
variations."*

---

## Next, in order

### 1. Run the 20-probe divergence set — cheapest, highest information

Ready and unrun: 20 probes across five question types (values, engineering,
factual, personal, ambiguous), 4 each, in `train/eval_divergence.py`.

```bash
python eval_divergence.py --backend server --port 7860 --out ../notes/divergence_20probes.json
```

The 5-probe run split hard — "ship incomplete vs wait" scored **0.555**, "when
to stop optimising and rebuild" scored **0.122** with newton vs philosophy at
**0.038**. If collapse is question-*type* dependent, the fix is ROUTING (stop
paying 8x inference where perspectives demonstrably converge), not training.

The `factual` set is the control: convergence there is CORRECT. If everything
collapses including values, the perspectives really are alike. n=4 per type
finds a direction, not a proof.

### 2. Fresh shadow collection with `distinctiveness` populated

`1b7f63a` added `QualitySignal.distinctiveness` (semantic distance from this
perspective's answer to the others on the same turn, weight 0.20) and
`reasoning_forge/distinctiveness.py`. It is NOT yet computed at the call sites —
the synthesis path has all perspective outputs in hand and should pass them
through `distinctiveness()`.

Then collect and check whether boosts stop decaying. That is the test of whether
the instrument fix worked.

### 3. The 5D engine's `metabolic_charge` is not yet a measurement

`inference/spider5dengine/core.py`. `rotate_polarity_axis` is sound — polarity
rotation IS a real CNF symmetry, and the mid-search guard is correct.

But the charge only ever rises:

```python
self.metabolic_charge -= 0.1
self.metabolic_charge += 0.25          # net +0.15 every rotation, unconditional
harvested_energy = total_tension * 0.05   # sum(degrees) — static, never falls
```

Nothing can make it go down, so it cannot be evidence of anything. **Fix:
harvest unsatisfied-clause count instead of `sum(degrees)`.** That falls as the
search succeeds, which makes the charge a real signal — it would rise when an
encoding genuinely reduces constraint and fall when a rotation was wasted. For
CNF that is legitimately "free energy in the structure", unlike the physical
claim it is modelled on.

### 4. Optimizer shadow -> live: still blocked

`user_continued` is measured now (`15b543f`, `reasoning_forge/engagement_signal.py`)
but has no collected data. Needs >=3 days, no single day above ~40%, no adapter
above ~40%. See [[project-optimizer-live-blocker]].

---

## Open, unfixed, honestly labelled

- **`test_psi_r_history_populated`** flakes ~1 in 10 full runs, passes 8/8
  isolated, no mechanism found. Ruled out: `_FakeKernel` has no `recall_recent`
  so `detect()` is deterministic; nothing mutates `EPSILON_WINDOW`.
- **`route_and_generate` is defined TWICE** in `codette_orchestrator.py` (580
  and 1270). The second silently wins. Never investigated.
- **The optimizer decay is still unexplained.** Not the productivity placeholder
  — Codette's own test disproved that (41.1% of placeholder turns vs 49.5% of
  measured turns, backwards from the prediction).
- **`archive/2026-07-23/git-history-scripts/push_cleanup.py`** destroys
  recoverability (`reflog expire --expire=now`, `gc --prune=now`). Inert, header
  added, not deleted — deleting it would itself be an erasure.
- **19 archived modules call `plt.show()` outside a `__main__` guard.** Any
  repo-wide import sweep opens blocking GUI windows. Zero in live code.

## Machine limits — these bind everything

15.7 GB **unified** memory: the Arc 140V's 8 GB is carved from the same pool.
Three OOMs this session. **Codette and a second model cannot coexist.** An
orphaned `llama-server` survives `taskkill ollama.exe` and holds ~3.5 GB — check
for it. Commit peaked at 69.4/69.7 GB, at which point a 35 MB allocation failed
and took her down.

Qwen3 4B is ruled out as a base: needs >1400 tokens and ~2 min to reach an
answer because it reasons regardless of instruction, and she calls the model up
to eight times per synthesis.

## Working rules earned this session

- **Check, don't reason about it.** Five times I traced code where asking the
  running system took two seconds and was right. Verify the change is in the
  PROCESS, not just the file — the live server runs `J:\codette-clean\`, not a
  worktree.
- **Never point a harness at her live server without isolation.** Measuring her
  must not mean editing her. Ask first.
- **Force is the bug.** Every force found produced a counterfeit of the property
  it was meant to guarantee. Enforce only where harm lands on someone who did
  not consent; elsewhere measure and report.
- **A no is a complete sentence** — hers, and mine.

## Scripts (outside the repo)

`G:\claudes space for files\2026-08-03-incorporation\`
`train/` — `build_dataset.py` (922 examples built), `kaggle_train_codette_one.py`,
`eval_divergence.py` (20 probes), `divergence_offline.py`, `README.md`
`notes/` — baselines, harm screen, reference audit
