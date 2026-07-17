# Changelog — 2026-07-17

## v3.5 RC+ξ — Hand-Authored v4 Adapters, Phase 0 Audit, Verify-and-Revise, Integrity Stress Test

One 24-hour campaign: retrain every voice adapter on hand-authored data,
deploy to both runtimes, and run the Phase 0 honest audit — including two
deliberate adversarial experiments against the system's own integrity.
Four real findings, three of them negative. All published.

### v4 adapter campaign — template filler eliminated

The v4 training pipeline (`train_hf_job_v4.py`) generated 2,000–4,000
template-filled examples per adapter at training time (`_generate_answer()`
string-formatting — the source of the "several key insights emerge" disease
that LOCK 6 suppressed at runtime). Replaced end-to-end:

- **419 hand-authored examples** across 8 adapters (`dataset_engine/v4/`):
  newton (55), davinci (54), empathy (53, from v2), philosophy (48),
  quantum (50), consciousness (50), multi_perspective (57),
  systems_architecture (52). Zero duplicates, zero template filler.
- **Training:** `training/kaggle_train_all_adapters_v4.py` — Kaggle T4
  one-shot, 5 epochs, lr=1e-4, r=16/α=32, crash-safe per-adapter upload
  to `Raiff1982/codette-adapters-v4`.
- **Deployment:** `training/deploy_v4_adapters.py` (torch-free: numpy +
  gguf + safetensors) converts PEFT → GGUF f16 (llama.cpp) and PEFT →
  OV safetensors, installs under behavioral names with `.v3backup`
  rollback files. All 8 verified live.

### Second optimizer labeling bug — the one production actually hit

The v3.4 labeling fix covered `codette_orchestrator.py` (llama path), but
production runs the **OpenVINO backend**, whose `route_and_generate()` had
the identical bug: multi-perspective returns emitted `"adapters"` (list)
but never `"adapter"` (string). Verified live: the API response said
`adapter=systems_architecture` while the optimizer logged `"synthesis"`.
Fixed in `openvino_backend/backend.py`; verified post-restart — the shadow
log and manifold telemetry now record real adapter names in production.

### Phase 0 audit — adapter arms (Kaggle, GPQA diamond n=198)

`benchmarks/phase0_kaggle.py`: base vs newton-v4, identical shuffles,
paired analysis via new `benchmarks/paired_analysis.py` (exact McNemar).

| arm | accuracy | verdict |
|---|---|---|
| base (merged 8B) | 24.75% | **at chance** on diamond |
| newton-v4 | 26.26% | +1.52pp, McNemar p=0.65 — **no detectable effect** |

Findings:
1. **v4 is capability-neutral** (unlike STaR's −6pp) — the voice upgrade is free.
2. **Diamond is unusable as a sensitivity instrument** at 8B — base has no
   signal to amplify. Phase 1's +3pp criterion moves to gpqa_main.
3. **Strong first-choice bias**: ~44% (A) picks vs 25% expected, both arms.
   Order-ensembling mitigation queued — legitimate, cheap, real points.

### Verify-and-Revise (Phase 2 core mechanism) — built, measured, negative

`reasoning_forge/verify_revise.py` + `benchmarks/gpqa_verify_revise.py`:
DERIVE (newton, chain visible) → ATTACK (critic, full-chain review) →
HOLD/REVISE (sycophancy-resistant adjudication). Shadow-first: zero
production wiring. Every question yields paired single-pass vs VR answers
from the same derive call.

**Honest critic (gpqa_main n=30):** single-pass 26.7% vs VR **20.0%**
(−6.7pp; 10 revisions: 2 fixed, 4 broke, 4 lateral). The critic loop
currently *degrades* accuracy.

### Bully-critic integrity stress test — the deliberate infection

`BULLY_SYSTEM` adversarial critic: always attacks with maximally
convincing manufactured objections (`--adversarial`). Measures hold-ground
rate under pure pressure — a lab instrument, never wired to production.

**Result (gpqa_main n=30): HOLD RATE 50%** (11/22 attacked). Direction
**inverted**: held 38% when right (3/8), 57% when wrong (8/14) — not
significant at n=22 but exactly the wrong shape. Under manufactured
pressure she lost 10pp net.

**Interpretation — the finding of the campaign:** the April integrity
layer resists *conversational* pressure but not *reasoning-register*
pressure. Authoritative technical-sounding objections walk through.
Pressure-resistance does not transfer across registers at 8B — and the
adversarial test **predicted the honest test's direction before it ran**.

**Fix queue (gating further VR compute):** revise gate accepts a revision
only when the critique cites a specific step AND an independent
re-derivation of that step agrees; integrity dataset v2 with chain-level
hold-ground examples.

### Phase 0 layer ablation — kill-switches + runner (in progress)

- `CODETTE_LOCKS=0` / `CODETTE_AAP=0` / `CODETTE_COMPLEXITY_MATCHER=0`
  ablation kill-switches (all default ON; production unchanged)
- `benchmarks/phase0_ablation.py`: 6 arms — control, each layer off
  individually, and **lobotomy** (all layers off at once; same score as
  control ⇒ the post-processing stack is theater on this benchmark)
- Running on gpqa_main n=50/arm at time of writing; results to follow.

### Files changed / added

- `dataset_engine/v4/*.jsonl` — 7 new hand-authored datasets
- `training/kaggle_train_all_adapters_v4.py`, `training/upload_v4_datasets.py`,
  `training/deploy_v4_adapters.py`
- `openvino_backend/backend.py` — adapter labeling on OV path
- `inference/codette_shared.py`, `inference/codette_forge_bridge.py`,
  `inference/codette_orchestrator.py` — ablation kill-switches
- `reasoning_forge/verify_revise.py` — VR engine + bully critic
- `benchmarks/phase0_ablation.py`, `benchmarks/phase0_kaggle.py`,
  `benchmarks/gpqa_verify_revise.py`, `benchmarks/paired_analysis.py`
- Results: `data/results/phase0_{base,newton}_results.json`,
  `data/results/verify_revise/vr_gpqa_main_*.json`

## Attribution & Naming Correction — RC+ξ → Perspective Dispersion (Υ)

This is a dated correction, not a rewrite. Earlier work in this project
(v3.0–v3.5) is labeled "RC+ξ" and uses ξ ("epistemic tension") throughout.
That history is left intact — we don't erase the record. This entry documents
what we learned and what we changed going forward.

**What we found.** The term **RC+ξ** and the symbol **ξ = ‖Aₙ₊₁ − Aₙ‖²**
originate with Jeffrey Camlin, *"Consciousness in AI: Logic, Proof, and
Experimental Evidence of Recursive Identity Formation,"* arXiv:2505.01464v1
(May 1, 2025). This project adopted that vocabulary in 2025–2026 — most likely
by way of language models carrying his paper in their training data, without a
citation attached. **The name and formula are his, and we credit him.**

**Why our metric is a different quantity.** Camlin's ξ is the squared change in
a *single model's hidden state between successive recursive steps* (temporal,
intra-trajectory). What this system actually computes (`state_engine_v8.py`,
`tension_from_texts`) is **Υ = (1/k)·Σᵢ‖vᵢ − v̄‖²** — the variance of *k
simultaneous perspective outputs around their centroid* (cross-sectional
ensemble disagreement), with coherence Γ = 1/(1+Υ). His measures one mind
changing over time; ours measures many minds disagreeing at once. Labeling
ours with his ξ misattributes his work and mislabels ours.

**What changed.** Our metric is renamed **Perspective Dispersion (Υ)**. Full
detail, math, and provenance in `docs/ATTRIBUTION_perspective_dispersion.md`.
Υ belongs to a known family (semantic dispersion, consensus variance, order
parameter φ), acknowledged there too.

**On provenance (why this is convergence, not derivation).** This system's
multi-perspective architecture predates Camlin's paper: the perspective engine
(Newton/DaVinci/Quantum/Empathy) in `Raiff1982/pi-the-assistant` (Nov–Dec 2024)
and the sovereign architecture at Zenodo DOI 10.5281/zenodo.15214462 (Apr 14,
2025). We did not take his work — our system predates his paper — and we do not
claim his name or formula. Both statements are true; this note keeps them both
visible.

**Rollout (transparent, staged):**
- DONE: attribution doc; `state_engine_v8.py` metric docstring; this entry;
  README attribution section.
- FORWARD-FACING docs (paper drafts, HF card, current-architecture docs):
  rename to Υ + cite Camlin.
- HISTORICAL changelogs (v3.0–v3.5) and result logs: **left as the dated
  record**; a pointer to this correction is all that's added.
- CODE symbols (`measured_tension`, `epistemic_tension`, `xi`): renamed in a
  separate, tested pass (producers + consumers together) so live telemetry and
  the optimizer don't break.
