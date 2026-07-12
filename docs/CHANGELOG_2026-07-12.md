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
