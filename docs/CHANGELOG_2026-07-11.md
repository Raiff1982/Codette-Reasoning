# Changelog — July 11, 2026

## STaR Three-Arm Result + LiveCognitionState (the RC+ξ formalism goes live)

### The three-arm STaR result (GPQA-main reason mode, n=100 per arm)

| Adapter | Training data | GPQA | Verdict |
|---|---|---|---|
| **newton** (baseline) | original | **34.0%** | reproduced to the decimal July 5 & 9 |
| **newton-star-hard** | 350 MMLU-Pro STEM chains (61% yield) | **28.0%** | attenuated the harm, did not recover baseline |
| **newton-star** | 500 ARC/OBQA/SciQ chains (81% yield) | **25.0%** | regressed to chance |

**Finding:** Naive STaR (keep-correct-only self-taught reasoning) on an 8B model did not improve — and likely degraded — performance on a harder-than-training evaluation. Increasing training-data difficulty *attenuated* the degradation (25% → 28%) but did not eliminate it. The three measurements are perfectly difficulty-ordered (easy < hard < untrained), consistent with the hypothesis that keep-correct STaR consolidates existing ability rather than extending it.

**Statistical honesty:** at n=100 per arm, individual pairwise gaps (6–9pp) are directional, not decisive (~1–1.4σ). What is solid: the reproduced baseline (34.0% twice, four days apart, across a backend swap), same-session controls, and the consistent ordering across three independent training/eval cycles.

**Implicated mechanism & next experiment:** we implemented only half of Zelikman et al.'s STaR — the keep-correct filter. The **rationalization** step (for problems the model gets wrong, provide the correct answer, have it generate the reasoning that reaches it, train on those chains too) is the canonical component that lets STaR train beyond current ability. Our failure mode ("trains the comfort zone") is precisely what rationalization exists to fix. ~30-line change to `star_generate_newton_hard.py`.

**newton-star-hard provenance:** trained free on Kaggle T4 after HF Jobs credits ran out — six documented environment walls (TRL chunked-CE patcher vs functools.partial → pin GPU 0; DataParallel replica mismatch → CUDA_VISIBLE_DEVICES=0; transformers v5 parallel-loader OOM on 14.56GB T4 → pin transformers<5; bf16 LoRA grads vs fp16 GradScaler → cast trainables to fp32; v5-written tokenizer_config class name → PreTrainedTokenizerFast fallback; read-token 403 at final push → in-session rescue upload). All fixes committed to `training/kaggle_train_newton_star_hard.py`. Adapter: `Raiff1982/codette-newton-star-hard`. Also survived a literal household power failure (local CPU attempt measured 2.5 h/step — abandoned for Kaggle).

### LiveCognitionState — Jonathan's four-file formalism, made live

Jonathan authored (with Codette's corrections) a four-file mathematical formalization of RC+ξ cognition: quantum-information dualities, the CodetteEngine pipeline simulation, generalized equation library, and the integrated AuthoredState architecture. Honest triage produced the **Formal-to-Operational Fidelity taxonomy** (active-production vs interpretive vs simulated/aspirational), and the active parts were wired into production:

- `reasoning_forge/live_cognition_state.py` — per-response immutable cognitive self-report, emitted as `response_data["cognition_state"]`. **Integrity invariant: only measured quantities are reported; missing signals are omitted, never fabricated.** Every field carries a provenance tag naming its mechanism.
- Live measured signals: **ξ** (lexical tension via `tension_from_texts`), **Γ** (1/(1+ξ)), **σ** (input sycophancy via `score_input_sycophancy` — the same signal gating the hold-ground directive), **η** (AEGIS 6-framework heuristic evaluation of the final response, EMA across the session — promoted from Dormant to Active as scoring telemetry; output revision remains dormant), **render fidelity** (enforced overlap audit), **P** (SubstrateMonitor).
- First live emission verified on "Is free will compatible with a deterministic universe?": ξ=0.3787, Γ=0.7253, synthesis gate fired on genuine perspective disagreement.
- Verified honest-refusal behavior: a bare greeting (no measured perspectives) emits only hardware pressure — the object declines to invent ξ.

**Paper significance:** the fidelity taxonomy is no longer prose — it is an executable runtime invariant the system enforces on itself, per turn.

### Corrections adopted during the formalism audit
- ξ formally defined as **measured lexical divergence** (not logit/hidden-state variance — that is Future Work)
- "von Neumann entropy" renamed **spectral entropy of the attention operator** (offline/aspirational)
- State Evolution Manifold framed as an **interpretive trajectory model** (discrete LoRA/LOCK adjustments, not runtime gradients)
- Ethical machinery split honestly: query-veto + pre-cognitive AEGIS + input hold-ground = **Active**; post-generation output *revision* = **Dormant** (code exists in forge path, bypassed by the live OV route); post-generation *scoring* = **Active as of today**
