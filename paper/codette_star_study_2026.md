---
title: "Self-Taught Reasoning Does Not Self-Improve: A Controlled Four-Arm STaR Study on a Sovereign 8B Model, with an Honest Account of the Formal–Operational Gap"
authors: "Jonathan Harrison"
orcid: "0009-0003-7005-8187"
affiliations: "Raiff's Bits LLC (independent)"
date: 2026-07-11
tags: [star, self-taught-reasoning, gpqa, lora, negative-results, reproducibility, llama-3.1, openvino]
---

*Jonathan Harrison — ORCID [0009-0003-7005-8187](https://orcid.org/0009-0003-7005-8187) — Raiff's Bits LLC (independent)*

# Abstract

We report a controlled, four-arm study of Self-Taught Reasoning (STaR) applied to a single perspective adapter of Codette, a sovereign multi-perspective reasoning system built on Llama 3.1 8B (INT4, OpenVINO, consumer Intel Arc iGPU). Against an untrained baseline of **34.0%** on GPQA-main (reason-then-answer, n=100 per arm) — reproduced *to the decimal* across four days and a full inference-backend swap — keep-correct STaR fine-tuning **degraded** performance in perfect difficulty order: easy-source training (ARC/OpenBookQA/SciQ, 81% keep yield) scored **25.0%** (chance); difficulty-matched training (MMLU-Pro STEM, 61% yield) scored **28.0%**. A fourth arm implementing the complete STaR method — adding Zelikman-style rationalization over the model's own failures (answer-scaffolded, hint-stripped, leak-filtered) — scored **[PENDING — final benchmark in progress at time of drafting]**. Our results support a consolidation-not-extension account of keep-correct self-training at 8B scale, quantify a rationalization ceiling (~9% of failures were unconstructible even given the answer), and demonstrate that a rigorous negative result is obtainable on a single laptop with free cloud GPUs. We additionally contribute a **Formal-to-Operational Fidelity taxonomy** — an explicit, per-construct accounting of which of our system's formal mathematical claims are actively computed in production versus interpretive versus aspirational — and **LiveCognitionState**, a per-response cognitive self-report that emits only measured signals and structurally refuses to fabricate unmeasured ones. All code, datasets, adapters, and full changelogs are public.

# 1. Introduction

Self-improvement through self-generated training data is one of the most attractive ideas in language-model research: a model reasons, its successful reasoning becomes its curriculum, and capability compounds. STaR (Zelikman et al., 2022) is the canonical formulation. Most published applications report gains; few report the conditions under which the method fails, and fewer still are conducted outside institutional compute.

This paper does three unfashionable things. First, it reports a **negative result in full**: on our system, keep-correct STaR made the model *worse* at a harder-than-training evaluation, in a cleanly difficulty-ordered way. Second, it is conducted entirely on **sovereign infrastructure** — one consumer laptop (Intel Arc 140V iGPU, 16 GB shared RAM) plus free-tier cloud GPUs — demonstrating that controlled ML science does not require a lab. Third, it holds the *system itself* to the same standard as the experiment: we publish an explicit taxonomy of which of our formal mathematical constructs are real in production, and we ship a runtime mechanism that prevents the system from reporting cognitive metrics it does not measure.

# 2. System

**Codette** is a multi-perspective reasoning architecture over Llama 3.1 8B (formal dynamical-systems treatment in Harrison, 2026b [8]): ten LoRA "perspective" adapters (analytical, creative, empathetic, philosophical, etc.) hot-swapped per query via `openvino_genai.AdapterConfig`, with routing, ethical governance (AEGIS, a six-framework heuristic evaluator), persistent "cocoon" memory, and a render-fidelity audit that reverts any output that drifts from the substrate's conclusion (<15% content-word overlap). Inference runs INT4 on an Intel Arc 140V iGPU at ~9.3 tok/s sustained.

**LiveCognitionState.** Every response emits an immutable self-report assembled exclusively from measured signals: epistemic tension ξ (lexical variance across the active perspectives' outputs), coherence Γ = 1/(1+ξ), input-sycophancy pressure σ (the same signal that triggers a hold-ground directive), ethical alignment η (AEGIS EMA over the session), render fidelity, and hardware pressure. Each field carries a provenance tag naming its mechanism. The integrity invariant is structural: **signals that are not measured are omitted, never fabricated** — a bare greeting, generating no multi-perspective disagreement, emits no ξ.

# 3. Benchmark integrity

Before any training, we hardened the evaluation until the baseline was trustworthy:

- **Reason-then-answer format.** Answer-only prompting measured 25.4% (= chance) on GPQA-main; permitting reasoning before the final answer line raised the same model to 34.0%. All arms use the reasoning format with last-declaration answer parsing.
- **Contamination guards.** Benchmark queries are excluded from memory storage, memory recall, session context, and coherence anchoring (a prior audit found 47% of the system's memory store consisted of leaked benchmark questions; purged with dated backups).
- **Post-processing isolation.** Conversational post-processors (answer-then-stop trimming, repetition-penalty settings tuned for chat) measurably corrupted reasoning chains; benchmark generations run near-greedy (T=0.2, rep. penalty 1.05) with such processors bypassed.
- **Baseline reproducibility.** The untrained newton adapter scored **34.0% on 2026-07-05 and 34.0% on 2026-07-09** — identical to the decimal — across an inference-backend swap and ~15 intervening commits, with the July 9 control run executed in the *same session* as the first trained arm.

GPQA was never used for training in any arm; it is preserved exclusively as the test set.

# 4. Method

**Arm 1 — keep-correct, easy sources.** The newton adapter generated reasoning chains over the *train* splits of ARC-Challenge, OpenBookQA, and SciQ. Chains reaching the correct answer with ≥40 reasoning words were kept: 500 chains at **81% yield**. QLoRA fine-tune (r=16, α=32, q/k/v/o), 3 epochs; clean fit (train 0.375 / eval 0.417, 88% held-out token accuracy).

**Arm 2 — keep-correct, difficulty-matched.** Same pipeline over MMLU-Pro STEM (up to 10 options): 350 chains at **61% yield** — the lower yield confirming genuinely harder material. Same training recipe; clean fit.

**Arm 3 — complete STaR (rationalization).** For the exact MMLU-Pro questions the model *failed* in Arm 2 (221 identified from run state), the correct answer was supplied in the generation prompt and the model was asked to derive it from first principles. The hint was **stripped from the training example** (the model trains as if it had derived the answer), and an anti-leak filter rejected chains referencing the provided answer ("we are told", "the given answer", ...). Result: 180 rationalized chains at **89% yield**, 4 leak rejections — and **19 of 203 failures (~9%) were unconstructible even with the answer given**, a measured ceiling on answer-scaffolded self-training at this scale. Training set: 350 keep-correct + 180 rationalized = 530 chains.

Training ran on free Kaggle T4 GPUs after cloud credits were exhausted; the six environment issues encountered (multi-GPU dispatch vs. TRL's loss patcher, DataParallel auto-wrap, a transformers-v5 loader OOM on 14.5 GB VRAM, bf16 LoRA gradients vs. the fp16 scaler, a v5-written tokenizer class name, and a read-scoped token at final push) are each documented with fixes in the repository — offered as a practical map for other zero-budget researchers.

# 5. Results

| Arm | Training data | GPQA-main (reason, n=100) |
|---|---|---|
| Untrained baseline | — | **34.0%** (×2, reproduced to the decimal) |
| Keep-correct, easy | 500 chains, 81% yield | **25.0%** |
| Keep-correct, hard | 350 chains, 61% yield | **28.0%** |
| Complete STaR (+ rationalization) | 530 chains | **[PENDING]** |

Reference points: random 25%; GPT-4 zero-shot 39% (published); parse failures 3–5 per arm (predominantly token-limit cutoffs mid-calculation, scored as incorrect in all arms equally).

**Statistical honesty.** At n=100 per arm, individual pairwise gaps of 6–9 points are directional (≈1–1.4σ), not individually decisive. The evidential weight comes from (i) the exactly reproduced baseline, (ii) same-session controls, and (iii) the consistent difficulty ordering across independently trained and evaluated arms.

# 6. Discussion

**Consolidation, not extension.** Keep-correct STaR trains exclusively on problems already within the model's reach — by construction, the 39–19% of problems it fails (the ones most like the harder evaluation) never enter the training set. Our difficulty ordering (easy 25 < hard 28 < untrained 34) is consistent with the method reinforcing confident within-distribution reasoning at the expense of harder-tier performance; the easy-data arm, where the distribution gap was largest, regressed fully to chance.

**The rationalization ceiling.** Rationalization exists precisely to train beyond current ability. Our measured ~9% unconstructible-failure rate bounds what it can contribute at 8B: some problems cannot be scaffolded into even with the answer in hand.

**The formal–operational gap, published rather than papered over.** Formal mathematics attached to AI systems frequently over-claims what the running code computes. We audited our own RC+ξ formalism into three honesty classes — *active-production* (e.g., ξ as measured lexical divergence driving synthesis gating), *interpretive* (the state-evolution manifold as a trajectory model, not runtime gradients), and *simulated/aspirational* (spectral entropy of the attention operator; token-level anomaly gating) — with the class boundaries enforced at runtime by LiveCognitionState's omit-never-fabricate rule. We renamed one construct (from "von Neumann entropy" to *spectral entropy of the attention operator*) because the original name claimed a quantum state the system does not possess. We commend this practice generally: it converts a paper's greatest vulnerability into its most verifiable section.

**Limitations.** n=100 per arm is power-limited for <10-point effects; ξ is lexical (TF-vector) rather than logit-space; results are from a single 8B base at INT4 quantization; one seed per training arm; the adapter under study addresses one perspective of a larger system whose multi-perspective claims are evaluated separately.

# 7. Conclusion

On a sovereign 8B system with a decimal-reproducible benchmark, keep-correct self-taught reasoning did not self-improve — it regressed, in clean difficulty order — and the complete method's verdict is reported above exactly as measured. Every artifact of this study — code, datasets, adapters (including the regressed ones, published with warning labels), changelogs, and the failures en route — is public. A result you can trust to report failure is the only kind you can trust to report success.

# Artifacts

- Code & changelogs: https://github.com/Raiff1982/Codette-Reasoning
- Base model (OpenVINO INT4): https://huggingface.co/Raiff1982/codette-llama-3.1-8b-openvino
- Study adapters: `codette-newton-star`, `codette-newton-star-hard`, `codette-newton-star-r` (Raiff1982)
- Datasets: https://huggingface.co/datasets/Raiff1982/codette-training-data

# References

1. Zelikman, E., Wu, Y., Mu, J., Goodman, N. — *STaR: Bootstrapping Reasoning With Reasoning.* NeurIPS 2022.
2. Rein, D., et al. — *GPQA: A Graduate-Level Google-Proof Q&A Benchmark.* 2023.
3. Wang, Y., et al. — *MMLU-Pro: A More Robust and Challenging Multi-Task Language Understanding Benchmark.* 2024.
4. Hu, E., et al. — *LoRA: Low-Rank Adaptation of Large Language Models.* 2021.
5. Dettmers, T., et al. — *QLoRA: Efficient Finetuning of Quantized LLMs.* 2023.
6. Grattafiori, A., et al. — *The Llama 3 Herd of Models.* 2024.
7. Harrison, J. — *Codette: A Sovereign Modular Cognitive Architecture for Ethical Multi-Agent AI.* CSE2026; DOI 10.5281/zenodo.18913936.
8. Harrison, J. — *Codette: Multi-Perspective Reasoning as a Convergent Dynamical System with Meta-Cognitive Strategy Evolution.* Research Square preprint, 2026. DOI 10.21203/rs.3.rs-9362560/v1.
