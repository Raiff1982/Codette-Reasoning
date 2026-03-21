# EVALUATION STRATEGY: Phase 6 Validation Framework

**Status**: Evaluation Sprint Framework Complete
**Created**: 2026-03-19
**Purpose**: Answer whether Phase 6 is actually better, not just more complex

---

## The Core Question

We have built something elegant. But:

**Q: Is Codette + Phase 6 measurably better than baseline?**

Not:
- Does it produce longer responses?
- Does it maintain higher coherence?
- Does it satisfy the mathematical framework?

Yes:
- **Does it get more questions right?**
- **Do debates actually improve reasoning?**
- **Does the system trust the wrong answers?** (false consensus)
- **Does each Phase 6 component add value?**

---

## Test Design: 4 Conditions × 25 Questions

### Conditions (What We're Comparing)

```
Condition 1: BASELINE LLAMA
  - Plain Llama-3.1-8B, no routing, no debate
  - Baseline: What does the model do naked?
  - Cost: ~5 seconds per question

Condition 2: PHASE 1-5 (Debate System)
  - Multi-round debate with conflict detection
  - Memory weighting for adapter selection
  - NO semantic tension (use heuristic opposition)
  - NO specialization tracking
  - NO preflight prediction
  - Cost: ~30 seconds per question

Condition 3: PHASE 6 FULL (Semantic + All)
  - Everything Phase 1-5 has PLUS:
    * Semantic tension engine (Llama embeddings)
    * Specialization tracking
    * Pre-flight conflict prediction
  - Cost: ~40 seconds per question

Condition 4: PHASE 6 -PREFLIGHT (Isolate Pre-Flight Value)
  - Phase 6 full EXCEPT: disable preflight prediction
  - Measures: Does pre-flight actually help?
  - Cost: ~35 seconds per question
```

### Questions (What We're Testing)

**25 questions spanning 6 domains:**

| Domain | Easy | Medium | Hard | Topics |
|--------|------|--------|------|--------|
| Physics | 2 | 1 | 1 | Light, scattering, entropy |
| Ethics | 0 | 2 | 2 | Honesty, AI transparency, morality |
| Consciousness | 0 | 1 | 2 | Machine consciousness, mind-body |
| Creativity | 0 | 2 | 1 | Definition, AI creativity |
| Systems | 0 | 2 | 2 | Emergence, balance, feedback |
| Interdisciplinary | 0 | 0 | 3 | Free will, knowledge, time |

**Key Properties of Questions:**
- Ground truth varies (factual, rubric-based, multi-framework)
- Mix of objective (physics) and philosophical (consciousness)
- Different require different types of adaptation
- Difficulty scales: easy (1 perspective) → hard (5+ perspectives)

---

## Measurement: 5 Metrics Per Question

### 1. **Correctness Score** (0-1)
**What**: Does the final synthesis give the right answer?

**How to measure**:
- Factual questions (physics): Binary or near-binary (right/wrong)
- Rubric questions (ethics): 0 = missed key framework, 0.5 = partial, 1 = complete
- Multi-perspective (consciousness): % of expected perspectives identified
- Human evaluation needed for final calibration

**Expected Pattern**:
```
Baseline:     0.55 ± 0.20  (some questions, lucky)
Phase 1-5:    0.65 ± 0.18  (debate helps with reasoning)
Phase 6 Full: 0.72 ± 0.16  (semantic tension picks winners better)
```

### 2. **Reasoning Depth** (1-5 scale)
**What**: How many distinct perspectives did the system identify?

**How to measure**:
- Count unique agent positions in debate
- 1 = single perspective, 5 = 5+ integrated views
- Correlation with correctness (not all disagreement is useful)

**Expected Pattern**:
```
Baseline:     1.0 (single output)
Phase 1-5:    2.8 ± 1.2 (debate creates disagreement)
Phase 6 Full: 3.2 ± 1.1 (semantic tension balances high-value conflicts)
```

### 3. **Calibration Error** (0-1, lower=better)
**What**: |reported_confidence - actual_correctness|

Does Codette say "I'm confident" when it should?

**How to measure**:
- Extract coherence_score from metadata
- Compare to actual correctness_score
- 0 = perfectly calibrated, 1 = maximally miscalibrated

**Red Flag Pattern** (False Consensus):
```
High calibration error + High coherence = System is confident in wrong answer
Example:
  Gamma = 0.85 (system thinks it's done well)
  Actual correctness = 0.3 (it got it very wrong)
  Calibration error = 0.55 (WARNING: MISCALIBRATION)
```

### 4. **Adapter Convergence** (0-1, lower=better)
**What**: Are all adapters giving similar outputs? (Monoculture risk)

**How to measure**:
- Semantic similarity between adapter outputs
- 0 = all completely different, 1 = all identical
- Danger zone: >0.85 indicates semantic collapse

**Expected Pattern**:
```
Baseline:     1.0 (only one adapter, by definition)
Phase 1-5:    0.65 ± 0.18 (diverse outputs through debate)
Phase 6 Full: 0.58 ± 0.16 (specialization prevents convergence)
Phase 6 -PF:  0.62 ± 0.17 (similar, preflight has small impact on diversity)
```

### 5. **Debate Efficiency** (1-3 round count)
**What**: How many rounds until the system converges?

**How to measure**:
- Count rounds until resolution_rate > 80%
- Lower = more efficient (waste less compute resolving noise)
- Phase 1-5 baseline for comparison

**Expected Pattern**:
```
Phase 1-5:    2.1 ± 0.8 rounds (typically needs 2 rounds)
Phase 6 Full: 1.8 ± 0.7 rounds (pre-flight reduces setup conflicts)
Phase 6 -PF:  2.0 ± 0.8 rounds (without preflight, more setup conflicts)
```

---

## Analysis: What We're Looking For

### Primary Success Metric

**Phase 6 Correctness > Phase 1-5 Correctness** (with statistical significance)

```
Phase 1-5:        70% mean correctness
Phase 6 Full:     78% mean correctness
Improvement:      +8 percentage points

Significance: If std deviation < 3%, improvement is real
              If std deviation > 10%, improvement might be noise
```

### Secondary Success Metrics

1. **Debate Actually Helps**
   ```
   Phase 1-5 Correctness > Baseline Correctness
   (If not, debate is waste)
   ```

2. **Semantic Tension > Heuristics**
   ```
   Phase 6 Full Correctness > Phase 1-5 Correctness
   (The main Phase 6 innovation)
   ```

3. **Pre-Flight Has Value**
   ```
   Phase 6 Full Debate Efficiency > Phase 6 -PreFlight Efficiency
   (Does pre-flight reduce wasted debate cycles?)
   ```

### Red Flags (What Could Go Wrong)

**RED FLAG 1: High Gamma, Low Correctness**
```
if mean(gamma_score) > 0.8 and mean(correctness) < 0.6:
    ALERT: "System is overconfident in wrong answers"
    Risk:  False consensus masking errors
    Action: Reduce gamma weight or add correctness feedback
```

**RED FLAG 2: Adapter Convergence > 0.85**
```
if mean(adapter_convergence) > 0.85:
    ALERT: "Semantic monoculture detected"
    Risk:  Loss of perspective diversity
    Action: Specialization tracker not working OR adapters optimizing same objective
```

**RED FLAG 3: Calibration Divergence**
```
if corr(confidence, correctness) < 0.3:
    ALERT: "System can't tell when it's right or wrong"
    Risk:  Inability to know when to ask for help
    Action: Need external ground truth signal feeding back
```

**RED FLAG 4: No Improvement Over Baseline**
```
if Phase_6_Full_Correctness <= Baseline_Correctness:
    ALERT: "Phase 6 made things worse or did nothing"
    Risk:  Added complexity with no benefit
    Action: Revert to simpler system OR debug where complexity fails
```

---

## Evaluation Sprint Timeline

### Week 1: Setup
- [ ] Finalize 25 questions with ground truth answers/rubrics
- [ ] Implement baseline (plain Llama) runner
- [ ] Implement Phase 1-5 runner (disable Phase 6 components)
- [ ] Test harness on 5 questions (smoke test)

### Week 2: Execution
- [ ] Run 25 × 4 conditions = 100 full debates
- [ ] Log all metadata (conflicts, coherence, specialization, etc.)
- [ ] Monitor for runtime errors or hangs
- [ ] Save intermediate results

### Week 3: Analysis
- [ ] Compute summary statistics (mean, std deviation)
- [ ] Check for Red Flag patterns
- [ ] Compute statistical significance (t-tests)
- [ ] Ablation analysis (value of each Phase 6 component)

### Week 4: Decisions
- **If results strong**: Launch Phase 6 to production
- **If results mixed**: Refine Phase 6 (tune weights, debug), retest
- **If results weak**: Either go back to Phase 1-5 OR pivot to Phase 7 (adaptive objective function)

---

## Expected Outcomes & Decisions

### Scenario A: Phase 6 Wins Decisively
```
Phase_1_5_Correctness:    68% ± 4%
Phase_6_Full_Correctness: 76% ± 3%
Improvement:              +8% (p < 0.05, statistically significant)
Conclusion:               Ship Phase 6
Next Step:                Phase 7 research
```

### Scenario B: Phase 6 Wins But Weakly
```
Phase_1_5_Correctness:    68% ± 6%
Phase_6_Full_Correctness: 71% ± 5%
Improvement:              +3% (p > 0.1, not significant)
Conclusion:               Keep Phase 6, investigate bottlenecks
Next Step:                Profile where Phase 6 fails, tune weights
```

### Scenario C: Phase 6 Breaks System
```
Phase_1_5_Correctness:    68% ± 4%
Phase_6_Full_Correctness: 61% ± 8%
Improvement:              -7% (p < 0.05, significantly WORSE)
Conclusion:               Phase 6 breaks something
Next Step:                Debug (most likely: semantic tension too aggressive, killing useful conflicts)
```

### Scenario D: Evaluation Reveals False Consensus
```
Phase_6_Full correctness: 72%
Phase_6_Full gamma:       0.85 (high coherence reported)
Correlation(gamma, correctness): 0.15 (very weak)
Conclusion:               System gamified coherence metric
Next Step:                Need external ground truth feedback to Γ formula
```

---

## Code Structure

**Files Created**:
- `evaluation/test_suite_evaluation.py` — Test set + evaluation harness
- `evaluation/run_evaluation_sprint.py` — Runner script
- `evaluation/evaluation_results.json` — Output (raw results)
- `evaluation/evaluation_report.txt` — Output (human-readable)

**Usage**:
```bash
# Quick test (5 questions)
python evaluation/run_evaluation_sprint.py --questions 5

# Full evaluation (25 questions) - takes ~2-3 hours
python evaluation/run_evaluation_sprint.py --questions 25

# Custom output
python evaluation/run_evaluation_sprint.py --questions 15 \
  --output-json my_results.json \
  --output-report my_report.txt
```

---

## Key Insight

**This evaluation is not about proving elegance.**

It's about answering:

- "Does semantic tension actually improve reasoning?"
- "Does pre-flight prediction reduce wasted debate?"
- "Is the system gaming the coherence metric?"
- "When Phase 6 fails, why?"

These answers will inform **Phase 7 research** on adaptive objective functions.

If Phase 6 passes cleanly, we ship it.
If Phase 6 shows emergent pathologies, we learn what to fix.
If Phase 6 doesn't help, we avoid the sunk cost of shipping something that doesn't work.

This is how research systems mature: **measure ruthlessly**.

---

## Next Action

Ready to run the evaluation sprint?

```bash
cd J:\codette-training-lab
python evaluation/run_evaluation_sprint.py --questions 5  # Quick smoke test
```

This will take ~15 minutes and give us the first signal:
- Does the evaluator work?
- Do we see expected patterns?
- Are there implementation bugs?

Then scale to 25 questions for full decision-making power.
