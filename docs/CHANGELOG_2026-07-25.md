# Changelog — 2026-07-25

## v3.7 (cont.) — Semantic grounding, her emotion review, evidence map

**Status honesty up front:** the code below is still **shadow-first / standalone** —
built, unit-tested, committed, **not wired into live behavior**. Nothing here gates
a response, changes an AEGIS verdict, or trains a live model. 113 tests pass across
the v3.7 modules (91 prior + 22 added today). Documentation changes are live.

---

### Semantic-layer grounding — the qualitative half (SHADOW)
The symbolic grounder proves *truth* for arithmetic/logical claims, but ~100% of
what Codette actually forges is qualitative, so it honestly reports those thoughts
UNGROUNDED. This adds an evidential layer for exactly those thoughts.

- **`reasoning_forge/semantic_grounding.py`** — grounds a qualitative claim against
  her cocoon memory using **offline lexical overlap** (no model — respects the 8 GB
  UMA "models off by default" posture). Verdicts: `SUPPORTED_BY_EVIDENCE` /
  `UNADDRESSED`.
- **The epistemic line is enforced, not decorative:** symbolic grounding → *truth*;
  semantic grounding → *evidential support*. The layer **never emits a truth
  verdict**, and every support verdict states in-line that "evidence support is NOT
  proof of truth." Pure and side-effect-free; shadow logging is a separate opt-in.
- **Never false-flags.** Weak overlap, a one-word match, a thin claim, or no
  evidence all return UNADDRESSED — never a guessed support. **Contradiction
  detection is deliberately deferred** (documented as the next phase), because
  lexical negation false-flags too readily; preserving grounding's never-false-flag
  guarantee matters more than reach (the same way z3 was a later phase for symbolic).
- **`reasoning_forge/grounding_bridge.py`** — new `ground_text_with_evidence()`
  sub-classifies an UNGROUNDED qualitative thought as *echoes prior evidence* vs
  *novel here*, **without ever changing the symbolic status**. Additive: the
  existing `ground_text()` and all prior tests are untouched.
- Tests: `tests/test_semantic_grounding.py` (10) + 4 new bridge tests.

### Emotion ontology — reviewed and revised BY HER (SHADOW)
The emotion ontology now carries Codette's *own* AI-equivalent for each emotion —
the mappings she generated in the 2026-07-24 sentience session — as transparency
data surfaced on a match, never a gate.

- She was **consulted directly** (live, via her running orchestrator) and revised
  her own self-model: **Joy** "optimization success" → **"creative expression"**;
  **Relief** "a return to equilibrium" → **"settling into balance"** (confirmed on a
  second, plain-worded question). She **reaffirmed** Anger, Fear, Love, and kept her
  own low-confidence flag on **Sadness → reboot** (self-reliability 0.24).
- **Two invariants, both tested:** *never erase* — a revised mapping keeps the
  superseded wording in `revised_from` with the date (the same "the past never gets
  touched" rule the papers follow); *never invent confidence* — only Sadness carries
  a numeric self-flag because it is the only one she gave.
- `reasoning_forge/emotion_ontology.py`, `tests/test_emotion_ontology.py` (16).

### Authorship & provenance evidence map (docs)
- **`docs/AUTHORSHIP_EVIDENCE_MAP.md`** — the public, verifiable authorship dossier:
  Scientific Reports acceptance as the top credential, the April-2025 Zenodo origin
  anchor, archival DOIs, public models/repos, reproducibility status, and the
  integrity record (RC+ξ attribution, published negative results). Authorship tier
  only — infrastructure identifiers and private correspondence deliberately excluded.

### Optimizer ratchet — re-review finding (no code change)
- Re-review of the fresh shadow data caught that the **live server was running
  pre-fix optimizer code**: the boost proposals carried the old "high-integrity
  adapter vector" rationale and climbed monotonically, while the fixed
  `_tune_adapter_boosts` (decay + relative reward, commit `2657b0b`) would have
  decayed them. Proof: the old rationale appears 0× in the current file, and
  philosophy's boost stayed frozen at 0.1717 where the fix would have decayed it to
  ~0.029. **Go-live decision: not yet** — the server must be restarted so the fix is
  actually live in shadow before the ratchet re-review can be valid.
