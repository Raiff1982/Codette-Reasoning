---
title: "Phase 0: Runtime Layer Ablation on GPQA — and a Corrected Conclusion"
authors: "Jonathan Harrison"
orcid: "0009-0003-7005-8187"
affiliations: "Raiff's Bits LLC (independent)"
date: 2026-07-22
tags: [ablation, gpqa, negative-results, reproducibility, self-correction, llama-3.1, openvino]
---

*Jonathan Harrison — ORCID [0009-0003-7005-8187](https://orcid.org/0009-0003-7005-8187) — Raiff's Bits LLC (independent)*

# Phase 0: Runtime Layer Ablation

## Purpose

The STaR study (Harrison, 2026a) isolated a single *training-time* intervention. Phase 0 asks the complementary *runtime* question: of the post-generation layers that shape every Codette response — permanent output LOCKs, adapter-aware post-processing (AAP), the response-complexity register matcher, and manifold steering — which, if any, is measurably responsible for the system's GPQA reasoning score? The layers were built for conversational quality, not benchmark accuracy; Phase 0 tests whether they help, hurt, or are simply invisible to a graduate-level multiple-choice test.

Each layer is gated by a default-on kill-switch (commit `54f77c5`): `CODETTE_LOCKS`, `CODETTE_AAP`, `CODETTE_COMPLEXITY_MATCHER`, `CODETTE_MANIFOLD_STEER`. Six arms were run on GPQA-main (reason-then-answer, n=50 per arm), holding the model, quantization, decoding parameters, and prompt fixed: a full-stack control, four single-layer removals, and a "lobotomy" arm with every layer off.

## Results as first scored

| Arm | Layers | Accuracy (n=50) | Δ vs control |
|---|---|---|---|
| `layers_all_on` | full stack (control) | 30.0% | — |
| `no_aap` | AAP off | 28.0% | −2 pp |
| `no_complexity` | register matcher off | 32.0% | +2 pp |
| `no_manifold` | manifold steering off | 30.0% | 0 pp |
| `no_locks` | permanent LOCKs off | 16.0% | −14 pp |
| `lobotomy` | all off | 10.0% | −20 pp |

The immediate temptation was a clean story: removing LOCKs costs 14 points, removing everything costs 20, and the other three layers are noise. A closer look at *how* the score was lost complicated that story — and then, on a second pass, overturned the mechanism we first proposed for it. Both the wrong turn and the correction are reported here, because the correction is the contribution.

## First (incorrect) mechanism: "it's all parse failures"

Decomposing each arm into three buckets — **correct**, **reasoned-wrong** (a definite answer was parsed, and it was wrong), and **parse-fail** (no answer letter was emitted at all) — produced a striking pattern:

| Arm | correct / reasoned-wrong / parse-fail |
|---|---|
| `layers_all_on` | 15 / 28 / 7 |
| `no_aap` | 14 / 28 / 8 |
| `no_complexity` | 16 / 27 / 7 |
| `no_manifold` | 15 / 28 / 7 |
| `no_locks` | 8 / 29 / 13 |
| `lobotomy` | 5 / 30 / 15 |

The reasoned-wrong count sits at 27–30 across **all six arms, including the full lobotomy**, while parse-fails climb from 7 to 15 as layers are stripped. The apparent reading: the model reasons identically regardless of the layer stack, and the layers — LOCK-1 in particular, which enforces the terminal answer line — only govern whether that reasoning gets *emitted* in parseable form. Under this account the −14 and −20 point drops are an **output-format artifact**, not a reasoning effect, and no layer touches reasoning quality at all.

This was recorded as the Phase 0 conclusion. It was wrong.

## The correction: a raw count over a shrinking denominator

The flaw is that "reasoned-wrong holds at ~29" is a **raw count, not a rate**, and its denominator is not fixed. As layers are removed, the number of questions that receive *any* parsed answer falls — answered drops 43 → 37 → 35 from control to `no_locks` to `lobotomy` — so a reasoned-wrong count that stays near 29 is not evidence of preserved reasoning. It is evidence that the **correct** bucket is collapsing (15 → 8 → 5) while the wrong bucket absorbs the fixed denominator's slack. A constant numerator over a shrinking denominator is a rising error *rate*, not a stable one.

The test that settles it is a lenient re-score: re-parse every stored response offline with a maximally permissive extractor (explicit answer line → any parenthesized letter → last bare A–D token anywhere), forcing a letter out of responses that the strict parser recorded as parse-fails. If the format-artifact story were true, those recovered answers should be correct at roughly the base rate, and conditional accuracy (correct / answered) should be flat across arms.

| Arm | raw acc | lenient acc | acc \| answered | recovered / of which correct |
|---|---|---|---|---|
| `layers_all_on` | 30% | 30% | 34.9% | 2 / 0 |
| `no_aap` | 28% | 28% | 33.3% | 2 / 0 |
| `no_complexity` | 32% | 32% | 37.2% | 2 / 0 |
| `no_manifold` | 30% | 30% | 34.9% | 3 / 0 |
| `no_locks` | 16% | 18% | 21.6% | 5 / 1 |
| `lobotomy` | 10% | 12% | 14.3% | 4 / 1 |

Two facts kill the format-artifact story:

1. **The recovered answers are not hidden-correct.** Across all arms, lenient parsing forced out 18 answers; **2 were correct (11%)** — *below* the 25% chance rate. Parse-fails are overwhelmingly responses that never reached a conclusion, not correct answers lost to a strict parser. Forcing a letter from them is worse than guessing.
2. **Conditional accuracy is not flat.** Correct-given-answered falls 34.9% (control) → 21.6% (`no_locks`) → 14.3% (`lobotomy`). Removing layers degrades the answers the model *does* commit to — not merely whether it commits. The reasoning is worse, not just less parseable.

## What actually survives significance testing

With the mechanism corrected, the honest question is which contrasts are real at n=50 (Fisher exact vs. control, raw and conditional):

| Contrast | raw p | conditional p | verdict |
|---|---|---|---|
| `no_aap` | 1.000 | — | inert on GPQA |
| `no_complexity` | 1.000 | — | inert on GPQA |
| `no_manifold` | 1.000 | — | inert on GPQA |
| `no_locks` | 0.153 | 0.223 | not significant |
| `lobotomy` | 0.023 | 0.066 | raw significant; conditional marginal |

Only removing the **entire stack** produces a demonstrable effect at this sample size. The 14-point LOCK drop that anchored the original clean story **trends negative but does not reach significance at n=50** — it is underpowered, not established. The AAP, complexity-matcher, and manifold layers are genuinely inert *on this benchmark* (p = 1.000): GPQA cannot see them, which is consistent with their design purpose being conversational quality rather than multiple-choice accuracy. And the lobotomy arm's 14.3% conditional accuracy sits **below the 25% chance rate**, meaning the fully stripped stack is actively anti-correlated with the correct answer, not merely uninformative.

## Conclusion

Phase 0's defensible claims are narrow, and narrower than the first pass suggested:

- **The full runtime stack matters; individual layers are not individually established at n=50.** Only the all-off lobotomy contrast is significant (raw p = 0.023). Every single-layer removal, LOCKs included, is underpowered here.
- **The layer effect is a reasoning effect, not merely a formatting one.** Conditional accuracy degrades as layers are stripped; the original "it's all parse failures" mechanism is disproven.
- **GPQA is blind to three of the four layers.** AAP, the register matcher, and manifold steering are inert on this test (p = 1.000) — expected, given they target conversational register rather than answer correctness, and a caution against reading GPQA as a whole-system verdict.

To make the locks claim stand on its own would require n ≥ 150 per arm. Absent that, the only contrast this study is powered to report is the lobotomy one.

The methodological point generalizes beyond this system. The statistic that misled the first analysis — "reasoned-wrong is flat across all arms" — was true as stated and false as interpreted: a raw count is not a rate, and a stable numerator over a shrinking denominator is a degradation in disguise. The error survived one review and was caught only by a pre-registered second test whose falsification criterion had been written down in advance. We report the wrong turn in full because a corrected conclusion with its correction visible is more trustworthy than a clean one whose revisions are hidden.

## Reproducibility

The six per-arm response sets are preserved as timestamped `data/results/gpqa_codette_reason_*.json`. Both scorings are deterministic functions of those stored outputs: the strict parser is `parse_final_answer` in `benchmarks/gpqa_codette.py`; the lenient re-score and Fisher tests operate offline on the stored responses and are fully specified by the bucket counts and the conditional-accuracy table above. No arm was re-run to produce the correction — the reversal came entirely from re-reading data already on disk.
