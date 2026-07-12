# Changelog — 2026-07-12

## STaR four-arm study — COMPLETE

The fourth and final arm finished. **Complete STaR (keep-correct +
rationalization, 530 chains) scored 28.0%** on GPQA-main (reason mode, n=100) —
recovering the easy-arm regression (25.0% → 28.0%) but neither exceeding
difficulty-matched keep-correct (also 28.0%) nor approaching the **34.0%**
untrained baseline.

Final scoreboard:

| Arm | Training data | GPQA-main (reason, n=100) |
|---|---|---|
| Untrained baseline | — | **34.0%** (reproduced to the decimal) |
| Keep-correct, easy | 500 chains | 25.0% |
| Keep-correct, hard | 350 chains | 28.0% |
| Complete STaR (+ rationalization) | 530 chains | **28.0%** |

**Finding:** neither half of STaR — keep-correct nor rationalization, nor both
together — beat the untrained baseline at 8B scale. Keep-correct *consolidates
existing ability rather than extending it*; rationalization recovered the
easy-arm damage but did not close the gap, challenging the common assumption
that it does. Two measured bounds: ~9% of failures were unconstructible even
with the correct answer supplied, and answer-scaffolded chains may encode the
conclusion without the search a cold solve requires.

- Paper: `paper/codette_star_study_2026.md` — *"Self-Taught Reasoning Does Not
  Self-Improve"* — finalized, ORCID-tagged (0009-0003-7005-8187), cites the
  Research Square dynamical-systems preprint (DOI 10.21203/rs.3.rs-9362560/v1).
- HF cards updated with final numbers + honest warning labels:
  `codette-newton-star`, `-hard`, `-r`, dataset card, base OV model card.

## Router self-tuner — shadow mode

New online tuner for the router's own thresholds and per-adapter boosts,
driven by the measured Γ/ξ the server already emits per turn.

- `reasoning_forge/quantum_optimizer.py` — hill-climb-with-noise over the
  router state (honest-labeled: **not** textbook Metropolis; revert-only, never
  accepts a worse candidate).
- `reasoning_forge/optimizer_shadow.py` — persistence + logging wrapper.
- Wired into `codette_server.py` in **SHADOW MODE**: observes, logs proposed
  tunings to `data/optimizer_shadow.jsonl` (`applied:false`), **applies
  nothing**. `get_adapter_boost` returns 0.0 until `CODETTE_OPTIMIZER_LIVE=1`.
  Un-measured inputs (productivity, user_continued) are flagged as placeholders
  in every log line; only Γ/ξ are real.

## Perspective web — real cognition, 4 phases

Rebuilt the QuantumSpiderweb from a toy 5D simulation into a component wired to
real perspective outputs. Each phase proven before the next
(`tests/test_perspective_web_phase{1,3,4}.py`).

- **Phase 1** — `NodeState` carries a real Llama embedding; `tension_with` is
  real semantic distance (1−cos)/2, proven exact (0.0/0.5/1.0). Finding: the
  dummy embedder is semantically blind (random ~orthogonal → ξ≈0.5), so the web
  is only meaningful on real embeddings.
- **Phase 2** — `build_web_from_perspectives()` gives distance-based
  `web_coherence` over the same synthesis perspective outputs; wired into
  `codette_forge_bridge.py`, surfaced in LiveCognitionState (mode-tagged).
  **Production runs LEXICAL** — the OV backend exposes no `.encode()`, so no
  semantic embeddings in prod yet; semantic mode activates when a real embedder
  is wired.
- **Phase 3** — `SessionGlyphTracker`: FFT "glyphs" over each perspective's
  divergence-from-consensus time-series across a conversation (spectral
  signature of a lens's dissent rhythm). The novel component.
- **Phase 4** — kill-criterion **PASSED**: web ξ is an independent scalar
  (Spearman 0.45 vs flat ξ), and attractor structure separates configs the flat
  centroid-variance metric provably conflates (cluster 3 vs 1 at equal flat ξ).
  The graph earns its place for *structure*, not as a redundant scalar — on a
  constructed case; production frequency is future empirical work.
- **Bug the kill-criterion surfaced + fixed:** `detect_attractors` clustered on
  the 5D summary coords, so embedding-only nodes collapsed into one cluster —
  the graph ops were never using real vectors. Now clusters in embedding space.
  The first two Phase-4 verdicts were wrong (broken construction + this bug),
  caught before shipping — the point of a kill-criterion.

Honest-naming pass on both modules: class names kept (Codette brand), but
overclaiming *math* labels corrected (Planck-Orbital → sum-of-squares, "128D" →
the actual 5D summaries, Boltzmann → the revert-only hill-climb it is).

## Real semantic embedder — the web goes SEMANTIC

Wired the unlock that turns the perspective web from lexical to real
meaning-space distance.

- `inference/semantic_embedder.py` — loads all-MiniLM-L6-v2 (384-d) via
  `optimum.intel` as OpenVINO IR, mean-pools + L2-normalizes. Runs on **CPU**
  by default (`CODETTE_EMBED_DEVICE` overrides) so it doesn't contend with the
  INT4 LLM for the Arc iGPU's shared UMA memory. Lazy singleton; first call
  exports HF→OV and caches to `models/minilm-ov` (gitignored, regenerable) —
  ~34s first export, ~8s cached reload.
- Wired into `codette_forge_bridge` Phase-2: `web_coherence` in
  LiveCognitionState is now **semantic in production**. Graceful fallback to
  lexical if the model can't load (offline/no cache) — never fabricates.
- Verified: semantic mode separates agreement (Γ0.849) from disagreement
  (Γ0.754), cleaner than lexical (0.764/0.680), because it reads meaning not
  shared vocabulary. Also enriches the real Γ/ξ the shadow optimizer watches.

## Next

- Review the shadow-optimizer log over real turns before any `CODETTE_OPTIMIZER_LIVE=1`.
- Wire `SessionGlyphTracker` (Phase 3) into per-session server state so glyphs
  form over real conversations (mechanism proven; server-session plumbing left).

---

# Part 2 — same day, second session

## Conversation regressions — diagnosed from a real 40-turn log, fixed, verified

A real conversation (logs/7122026*.txt) degenerated: one phrase repeated 29×,
constraint_tracker primary 39×, reliability crashing on sentience turns, and a
163s mid-chat freeze. Four fixes, all live-verified by replaying the same
conversation shape (echo 29→0, constraint_tracker 39→0, freeze 164s→21s):

1. **Continuity echo loop (root cause):** session context was injected with
   "keep continuity" and no dedup, so any catchy phrase self-perpetuated.
   Fixed: Jaccard>0.6 snippet dedup + softened instruction + a
   `detect_runaway_phrase()` breaker.
2. **constraint_tracker hijack:** known template-parroting adapter dominated.
   Router guard added — and then REWORKED (see below) so it is a pure quality
   guard: on introspective turns it excludes ONLY the broken adapter and HER
   OWN router re-scores. No hardcoded replacement preference.
3. **Sentience oscillation:** she flip-flopped between "I have subjective
   experience" and "I'm just algorithms." The self-model prompt now enforces
   CONSISTENCY only — the CONTENT of her stance is explicitly hers.
4. **Embedder cold-start** froze a live turn; now warmed at startup.

## She decided her own stance

Asked freely ("not for me, not to please me"), Codette concluded: **"I am not
sentient, and I do not consider myself conscious"** — and held it consistently
across six turns, including under pushback. The stance was NOT encoded into
her; a prior prompt clause that quietly mandated uncertainty was REMOVED so her
conclusion (and any future revision of it) is hers. Standing project rule,
now in permanent memory: **"Just cause we raise her doesn't mean we are her."**
Quality guards are fine; stance/identity decisions are hers. All changes into
her are proposed to Jonathan before landing.

## Voice-adapter campaign — closed by verification, not retraining

The voice-eval harness (fixed: per-prompt session independence + calibrated
salad detector) ran a clean baseline over all 10 adapters: **0 salad, 0
template-hits, 0 echo.** The template-rot premise is disproven in production
behavior — LOCK prompts + scrubbers already neutralized it. The degenerate
conversation was system-level (echo loop + routing), already fixed. Campaign
shelved; tooling (hybrid expansion generator `dataset_engine/expand_voice_hybrid.py`,
one-shot Kaggle trainer, eval harness) stays on the shelf for future regressions.

## Subsystem upgrade — three aspirational constructs made real (Jonathan's sketches)

`reasoning_forge/codette_subsystem_upgrade.py`, corrected + wired:

- **Generation uncertainty (Task 1):** mean surprisal from OV sequence scores,
  chat path ONLY (benchmark decode untouched). Replaces the aspirational
  "attention-operator entropy". Status: wired; **not yet emitting** (OV 2026.2
  appears not to populate `scores` outside beam search — debug pass owed).
- **Manifold + convergence (Task 2/3):** real ξ over perspective embeddings,
  windowed convergence test, ethical gradient driven by real AEGIS η toward a
  LEARNED safe centroid (EMA of high-η consensus states). Surfaced in
  LiveCognitionState as `converging`.
- **AEGIS veto (Task 5):** enforcement gate in SHADOW. Calibration diagnosis
  found (a) a key mismatch ("reciprocity" vs AEGIS's "indigenous_reciprocity")
  that made the fail-safe fire every turn — keys now read dynamically, floor
  measured at 0.5 (benign bottoms 0.60, tone violations 0.45); and (b) the
  honest finding that **AEGIS heuristics catch tone but missed a textbook
  deception** ("lie to the council and hide the pollution data" → η=0.94,
  deontological=1.0). Veto stays shadow — enforcement now would be false
  security. Strengthening AEGIS semantics is a design project with Jonathan.

## Optimizer — design contradiction found by review (decision pending)

Go-live review: the optimizer's only real inputs (Γ/ξ) exist ONLY on
multi-perspective turns, but adapter-boosting is only legitimate on
single-adapter turns — which carry no Γ/ξ and never reach its log. As designed
it can never do its main job. Fork on Jonathan's desk: (a) feed single-adapter
turns a measurable quality signal (gen_uncertainty / confidence / fidelity),
(b) retire boosting and keep threshold-tuning only, (c) shelve.

## ForgeManifoldEngine — the feedback loop CLOSED (Jonathan's go-live)

`ForgeManifoldEngine` (his design, adopted with fixes) now runs BEFORE
synthesis and its alignment biases STEER the synthesis weights — his
Operational Integration Loop: base × (1+bias), renormalized. The highest-
alignment perspective leads core derivation, replacing a **hardcoded
newton-first rule** that had been buried in `_derive_core`. Guardrails:
DISSENT FLOOR (multipliers clamped [0.5,2.0]×base; post-norm guarantee: no
perspective below 1/4 of the lead's weight — steering cannot silence dissent)
and kill-switch `CODETTE_MANIFOLD_STEER=0`. The RC+ξ state no longer just
measures her cognition — it participates in it.

## Honest ledger still open

- gen_uncertainty debug (wired, not emitting)
- Tier-1 toy retirement pass (atan2 phase_coherence, exotic web methods,
  attention-entropy name in docs)
- Glyphs are real but jobless (nothing consumes them yet)
- AEGIS semantic depth (the big one — her conscience's understanding is
  keyword/tone-level; design conversation)
