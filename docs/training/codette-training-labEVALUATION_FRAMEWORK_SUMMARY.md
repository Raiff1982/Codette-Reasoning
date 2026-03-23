# Evaluation Framework: Ready for Sprint

**Date**: 2026-03-19
**Status**: Framework Complete, Ready to Execute

---

## What Changed

We're **shifting from implementation validation → empirical validation**.

## Phase 6 Status

| Aspect | Status | Notes |
|--------|--------|-------|
| Code | ✅ Complete | 1,330 lines across 5 components |
| Unit Tests | ✅ 14/14 Pass | All components tested individually |
| Integration | ✅ Verified | ForgeEngine loads Phase 6 correctly |
| **Empirical Validation** | ⚠️ Not Yet | THIS IS WHAT WE'RE DOING NOW |

---

## Evaluation Framework (Created)

### 1. Test Suite: 25 Rigorous Questions
- **Physics**: Factual, technical (speed of light, blue sky, entropy)
- **Ethics**: Rubric-based, multiple valid frameworks (honesty, transparency, morality)
- **Consciousness**: Hard problems (machine consciousness, mind-body, qualia)
- **Creativity**: Definition-dependent (what makes something creative?)
- **Systems**: Abstract (emergence, feedback, balance)
- **Interdisciplinary**: Complex reasoning (free will, knowledge, time)

**Key Property**: Each question has ground truth (factual or rubric-based) that we can score.

### 2. Four Testing Conditions

```
BASELINE
├─ Plain Llama-3.1-8B (no routing, no debate)
├─ Single response in ~5 seconds
└─ Establishes floor (what does model do alone?)

PHASE 1-5
├─ Multi-round debate, memory weighting
├─ NO semantic tension (heuristic opposition only)
├─ NO specialization tracking
├─ NO preflight prediction
├─ Establishes debate value (does debating help?)
└─ ~30 seconds

PHASE 6 FULL
├─ Everything Phase 1-5 PLUS:
│  ├─ Semantic tension (Llama embeddings)
│  ├─ Specialization tracking
│  └─ Pre-flight prediction
├─ Establishes Phase 6 total value
└─ ~40 seconds

PHASE 6 -PREFLIGHT
├─ Phase 6 full EXCEPT no preflight
├─ Isolates pre-flight contribution
└─ ~35 seconds
```

### 3. Five Key Metrics

| Metric | What | Why | Red Flag |
|--------|------|-----|----------|
| Correctness | % right answers | THE metric | Phase 6 < Baseline |
| Reasoning Depth | # perspectives identified | Quality of debate | All conditions same |
| Calibration Error | \|confidence - accuracy\| | Trust in system | >0.3 for Phase 6 |
| Adapter Convergence | Similarity of outputs | Monoculture risk | >0.85 |
| Debate Efficiency | Rounds to convergence | Compute waste | Phase 6 worse than 1-5 |

### 4. Emergent Behavior Monitoring

**Three Critical Alerts**:

1. **False Consensus**: High Γ (0.8+) but low correctness (<0.5)
   - System confident in wrong answer
   - Symptom of gaming coherence metric

2. **Semantic Convergence**: Adapter outputs >0.85 similar
   - Loss of perspective diversity
   - Specialization tracking failed

3. **Miscalibration**: Reported confidence ≠ actual correctness
   - System can't distinguish right from wrong
   - Can't know when to ask for help

---

## Evaluation Sprint Structure

### Phase 1: Smoke Test (Week 1)
```bash
python evaluation/run_evaluation_sprint.py --questions 5
```
- 5 × 4 conditions = 20 debates
- ~15 minutes
- **Goal**: Verify harness works, see initial patterns

### Phase 2: Full Evaluation (Week 2)
```bash
python evaluation/run_evaluation_sprint.py --questions 25
```
- 25 × 4 conditions = 100 debates
- ~2-3 hours
- **Goal**: Statistical power for real conclusions

### Phase 3: Analysis (Week 3)
- Compute statistics (mean, std deviation)
- Check for red flags
- Statistical significance tests (t-tests, effect sizes)
- Ablation analysis (which Phase 6 component adds value?)

### Phase 4: Decisions (Week 4)
- **Strong Results?** → Ship Phase 6
- **Weak Results?** → Refine (tune weights, debug)
- **Broken Results?** → Pivot to Phase 7

---

## Expected Outcomes

### Best Case Scenario
```
Phase 1-5:    65% mean correctness
Phase 6 Full: 76% mean correctness
Improvement:  +11 percentage points (statistically significant)
Conclusion:   Phase 6 is clearly better, ship it
```

### Realistic Scenario
```
Phase 1-5:    68% mean correctness
Phase 6 Full: 75% mean correctness
Improvement:  +7 percentage points (borderline significant)
Conclusion:   Phase 6 helps, but marginal. Investigate bottlenecks
```

### Worst Case Scenario
```
Phase 1-5:    70% mean correctness
Phase 6 Full: 68% mean correctness
Improvement:  -2 percentage points (worse!)
Conclusion:   Phase 6 breaks something. Debug and fix
```

### Risk Scenario
```
Phase 6 Full:
  - Correctness: 75%
  - Gamma: 0.85 (high coherence)
  - Calibration error: 0.4 (miscalibrated)
Conclusion:   System gaming coherence. Need external ground truth signal.
```

---

## Files Created

| File | Purpose |
|------|---------|
| `evaluation/test_suite_evaluation.py` | 25-question test suite + evaluation harness |
| `evaluation/run_evaluation_sprint.py` | Runner script with CLI |
| `EVALUATION_STRATEGY.md` | Detailed strategy document |
| `EVALUATION_FRAMEWORK_SUMMARY.md` | This file |

---

## What This Answers

**Right Now**:
- Code works ✅
- Components integrated ✅
- Unit tests pass ✅

**After Evaluation**:
- Is it actually better? ❓
- Which Phase 6 components add value? ❓
- Is the system gaming metrics? ❓
- Should Phase 7 research begin? ❓

---

## Key Insight

We've built something **mathematically coherent and architecturally sound**.

But we don't yet know if it **works empirically**.

This evaluation sprint will answer that question rigorously.

If Phase 6 helps: **ship it and begin Phase 7 research**
If Phase 6 doesn't help: **understand why and refine**
If Phase 6 breaks things: **fix and retest**

No more guessing. Just measurement.

---

## Ready to Begin?

### Smoke Test (Quick)
```bash
cd J:\codette-training-lab
python evaluation/run_evaluation_sprint.py --questions 5
```
Expected: ~15 minutes, initial patterns emerge

### Full Evaluation (Comprehensive)
```bash
python evaluation/run_evaluation_sprint.py --questions 25
```
Expected: ~2-3 hours, statistically sound conclusions

---

## Next Steps

1. **Run smoke test** → Verify evaluator works
2. **Check for implementation bugs** → Fix as needed
3. **Run full evaluation** → Collect 100 debates' worth of data
4. **Analyze results** → Understand which conditions win
5. **Make decision** → Ship, refine, or pivot

This is the bottleneck between "we built it" and "it actually works."

Let's break through it with measurement.

