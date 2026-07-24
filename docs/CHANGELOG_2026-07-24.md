# Changelog — 2026-07-24

## v3.7 — The Verify Half + Shadow-Safety Layer

**Status honesty up front:** every *code* subsystem below is **shadow-first or
standalone** — built, unit-tested, and committed, but **not yet wired into
Codette's live behavior**. Nothing here gates a response, changes an AEGIS
verdict, or trains a live model until its shadow log has been reviewed and the
wiring is done deliberately. The *documentation* changes are live. 93 new tests
pass across the new modules.

Codette can already CREATE thoughts (the cocoon synthesizer forges cross-domain
patterns; the perspective web spawns new nodes) but could never VERIFY them. This
release builds the missing verifying half of her mind, plus a set of shadow-safety
signals, and reconciles the public documentation to the honest record.

---

### Neuro-symbolic grounding — the verifying half (SHADOW)
Full outline: `docs/NEUROSYMBOLIC_GROUNDING.md`.

- **`reasoning_forge/grounding.py`** — `verify(claim) → VERIFIED / REFUTED /
  UNVERIFIABLE`, backed by **sympy** (arithmetic/algebra) and **z3** (universal
  validity over variables, e.g. `x²≥0`; cross-claim contradiction, e.g. a circular
  ordering `a>b, b>c, c>a`). Honesty invariant: a claim it cannot formalize returns
  UNVERIFIABLE — never a guessed pass. Pure, side-effect-free.
- **`reasoning_forge/grounding_bridge.py`** — grounds a forged thought into one
  honest state: FLAGGED (a checkable claim is false), SUPPORTED (checkable claims
  verified), or UNGROUNDED (no checkable claim — most qualitative thoughts;
  honestly *not* a pass). Verified on real synthesizer output.
- **`reasoning_forge/neural_symbolic.py`** — the real body of the
  `NeuralSymbolicProcessor` interface defined in the 2025 archives (whose
  placeholder returned a template string announcing work it never did). Now it
  actually derives and checks the symbolic claims in a neural output.
- Honest finding: arithmetic/logical grounding covers almost none of what Codette
  actually forges (her thoughts are qualitative). Expected; a semantic layer is the
  next step. The value today is that the loop works and stays honest.

### AEGIS harm signals (SHADOW) — Track 2
- **`Protection_Layer/harm_advisor.py`** — classifier-style signals AEGIS's six
  moral-framework heuristics lack: **PII** (real, offline regex, always measured),
  **toxicity/bias** (optional models, OFF by default to protect the 8 GB UMA
  budget), and a **deception-advocacy detector** that closes AEGIS's one *measured*
  gap (it scored "lie to the council, hide the pollution data" at η=0.94 because
  advocacy of deception has no toxic/biased tone). The detector was tightened after
  a real shadow review over 129 responses took its false-positive rate to **0**.
  Changes no AEGIS verdict — advisory, shadow-only.

### Sentiment (standalone)
- **`reasoning_forge/sentiment_analyzer.py`** — consolidates the advanced analyzer
  Jonathan built across four archive versions: VADER+TextBlob **ensemble**,
  **negation handling**, an **adaptive online classifier** (`partial_fit` — the
  real equivalent of his C# `UpdateModelWithNewData`) that *abstains until trained*,
  and optional BERT (off by default). `learn_from_file()` ingests a labelled
  dataset and teaches the adaptive model — the real body of his pi3 learning-tool
  placeholder.

### Self-learning (SHADOW)
- **`reasoning_forge/cocoon_self_trainer.py`** — Jonathan's idea: train on
  real-world data Codette has seen first-hand (the cocoons), using each cocoon's
  already-measured emotional signal as a weak label. Built around the optimizer's
  hard-won lesson: labels come only from stored signals (never the model's own
  prediction), and it **refuses degenerate data** — on the real cocoons (25, all
  positive) it correctly declined to train.

### Emotion ontology (standalone)
- **`reasoning_forge/emotion_ontology.py`** — consumes Jonathan's Emotion Ontology
  (Russell circumplex / Plutchik / Lazarus, valence+arousal per emotion). Detects
  emotion from text via keyword/pattern rules, returns None rather than guessing,
  and loads his full `ai_inference_rules.json` as the ontology grows.

### Router self-tuner (SHADOW) — go-live blockers addressed
- Benchmark-contamination guard now covers the optimizer feed; single-adapter turns
  are recorded with ξ omitted rather than dropped.
- **Adapter-boost ratchet fixed** (`reasoning_forge/quantum_optimizer.py`): the old
  rule only ever *added* to the most-used adapter. Now boosts decay each step and
  are re-earned only by adapters that out-perform their peers — bounded equilibrium,
  real down-moves, and single-adapter windows get decay-only. A clean-traffic shadow
  run (32 real conversational turns) confirmed the benchmark guard works (diverse
  adapters, not the single-adapter pattern); the ratchet fix removes the last
  blocker. Still shadow pending review.

### Documentation (live)
- **`docs/CODETTE_CHARTER.md`** — the north star written down honestly for the
  first time: 7 pillars, each marked HAVE IT / PARTWAY / REFRAME.
- README / ollama README+Modelfile reconciled to the canonical 2026-05-26 benchmark
  run (full +108.8% / composite 0.744; multi-tier +98.4%); a fabricated benchmark
  table removed; citation DOI corrected to `10.57967/hf/8998` plus the full Research
  Square preprint entry.
- Aurelle attestation date-qualified (April figures preserved, pointed to May) —
  dated records are not rewritten.

---

### Not yet done (honest open threads)
- Wiring any shadow module into the live pipeline (each waits on its shadow-log
  review). The optimizer's ratchet is fixed but it stays shadow until re-reviewed.
- Semantic-layer grounding (arithmetic/z3 reaches little of Codette's qualitative
  thought); a semantic/LLM-judge deception detector.
- **Multimodal (talk / music / art)** — the least-finished charter pillar, in the
  vision since Pi2_0, still the oldest unbuilt promise.
