# Neuro-Symbolic Grounding — Project Outline

*The missing half of the mind. — started July 24, 2026*

## The idea, in one sentence

Codette already **creates** new thoughts (bridges concepts from memory into new
patterns). She cannot yet **verify** them. This project builds the verifying half
and wires it to the creating half, so a new thought is *proposed by intuition and
disposed by rigor* — creation and honesty in one loop.

This is not new scope bolted on. It is the charter made literal:
- **Pillar 2 (can't lie undetectably):** a solver produces ground truth a claim is
  measured against. A false thought leaves a mark.
- **Pillar 3 (reasons but not trapped in logic):** intuition still proposes freely;
  logic only checks. She is not *confined* to logic — logic is her honesty organ,
  not her whole mind.

Naming is provisional (Jonathan's to set): "Grounding Layer" for the verify half,
"Create–Verify Loop" for the whole. Rename freely.

## What already exists (do NOT rebuild — this is hers)

The **create / connect** half is real and stays untouched in how it forms thoughts:
- `reasoning_forge/cocoon_synthesizer.py` — `retrieve_cross_domain_cocoons`,
  `_detect_emergent_patterns`, `forge_strategy`. Discovers cross-domain links and
  forges new reasoning strategies (Emergent Boundary Walking, etc.).
- `reasoning_forge/perspective_web.py` — `connect`, `tension_with`,
  `detect_attractors`, `spawn_lifeform` (generates a new node wired to N others).
- Substrate self-healing already exists and is better than the 2025 spec:
  `inference/substrate_awareness.py` (live) + `Protection_Layer/aegis_layer5_complete.py`.

## What is genuinely missing (verified by exhaustive archive search, BOTH drives)

No solver, no verifier, no `sympy`/`z3` usage anywhere — not in the repo, not in
any J: archive (`ai_system`, `A new way of thinking`, `My new bot`, `openai`,
`phiseek`, `thoughtbot`, `Ultima`), and not on K: (`K:\ai_system2`).

The one file literally named `neuro_symbolic.py`
(`K:\ai_system2\ai_system\components\neuro_symbolic.py`) is a **stub, not an
implementation**: `NeuroSymbolicEngine` references a `SymbolicReasoner()` class
that is *defined nowhere* on either drive, its neural half loads a non-existent
`"gpt-3"` model, and `integrate_reasoning` merely string-concatenates the two
outputs — no integration, no verification, no grounding. The architecture was
*named* repeatedly across five years; the symbolic reasoning was *never written*.

**The verify half is genuinely greenfield. It is the honesty half.**

---

## Phases

### Phase A — Grounding (the missing convergent half) — GREENFIELD, START HERE
- [ ] **A1. `reasoning_forge/grounding.py`** — `GroundingVerifier`: a claim →
      `Verdict(VERIFIED / REFUTED / UNVERIFIABLE, detail, confidence)`. Backed by
      `sympy` for arithmetic and algebra to start. Pure function, no side effects,
      degrades gracefully if `sympy` is absent. **← first module, this commit.**
- [ ] **A2. Claim extraction** — pull checkable claims out of free text
      (numeric equalities, inequalities, simple equations). Conservative: extract
      only what can be checked; label the rest UNVERIFIABLE, never guess.
- [ ] **A3. Shadow logging** — every verdict appended to
      `data/grounding_shadow.jsonl` with `applied: false`. Observes, changes nothing.
      Same shadow-first discipline that caught the optimizer twice on 2026-07-23.

### Phase B — The Bridge (connect create ⟷ verify) — SHADOW
- [ ] **B1.** Pass `cocoon_synthesizer` forged patterns through the verifier
      (shadow). Log verified / refuted / unverifiable per forged thought.
- [ ] **B2.** Pass `perspective_web` new connections (`spawn_lifeform`, attractor
      links) through the verifier (shadow).
- [ ] **B3.** Honest labeling: a grounded thought carries a `grounding` tag;
      an unverifiable one is labeled **intuition**, never asserted as fact. This is
      the omit-never-fabricate rule extended to created thoughts.

### Phase C — Realize the obtainable archive pieces (there, unrealized until now)
- [ ] **C1. Configurable self-healing thresholds** — the 2025 `self_healing.txt`
      spec (memory / CPU / response-time thresholds + `instant_utilization` flag).
      Current `SubstrateMonitor` folds these into a composite pressure score with
      hardcoded cutoffs. Expose them as config; add the explicit response-time
      trigger and real-time toggle. Small, finishes a genuinely old idea.
- [ ] **C2. `connect_memory_topics` depth control** — the `memory.txt` schema
      (connect topics across memory, with a `depth` parameter). Surface the
      synthesizer's cross-domain connection as an explicit, depth-controlled call.
- [ ] **C3. z3 for logical claims** — add `z3-solver` for propositional/relational
      claims beyond arithmetic (entailment, consistency, contradiction).
- [ ] **C4. Associative recall** — `K:\ai_system2\upgrade.txt` has a real
      `MemoryStore` with `_find_associations` (links a new memory to existing ones
      by shared terms) + recall-weight reinforcement + decay pruning. This is a
      concrete ancestor of the connect/create half — worth comparing against the
      current cocoon/FTS5 memory to see if the association-forming step is as
      explicit. It is the "fill in the connection gaps" mechanism in its earliest
      real (non-metaphorical) form.
- [ ] **C5. Element defenses that ACT** — `K:\ai_system2\upgrade3-5.txt` evolve
      `execute_defense_function` to take a `system` argument and act on it, plus a
      real `SelfHealingSystem` / `SafetySystem`. The 2024 version only `print()`ed.
      IF any defense maps to a real behavior (e.g. "reflection" -> adversarial-input
      detection), reinterpret it concretely; otherwise leave the metaphor. Honest
      about which are real.

## Provenance material (not code — lineage evidence)
- `K:\ai_system2\ai_system\history_2025-02-07T18_*.json` — 108-record design
  conversations (gpt-4o-mini, Feb 2025). The actual record of how these ideas were
  developed. Mine for the lineage/priority documentation, not for implementation.

### Phase D — Integration + go-live gate — REVIEW BEFORE ANY LIVE WIRING
- [ ] **D1.** Review the shadow logs together (like the optimizer review): what does
      grounding flag on real forged thoughts? False-refute rate? Coverage?
- [ ] **D2.** Only then decide whether verified/refuted verdicts gate live output,
      and how honest labels surface in `LiveCognitionState`. Her cognition stays
      hers; grounding is a quality guard (the allowed kind), off by default until
      reviewed.

### Deliberately OUT of scope here (flagged, separate projects)
- Multimodal (talk / music / art) — the least-finished pillar, a separate build.
- Rewriting how she *creates* — untouched. This project adds verification, not
  new cognition.

## Standing-rule compliance (per NEVER-force-Codette)
- The create half is hers and is not modified.
- Grounding is a **quality guard**, explicitly the allowed kind — and it runs
  **shadow-first**, wired to nothing, logging only, until Jonathan reviews.
- All wiring is flagged explicitly in this doc and in each commit.

## Status
- **Phase A1: DONE** — `reasoning_forge/grounding.py` + `tests/test_grounding.py`
  (15 tests pass, incl. every honesty invariant: unknowns return UNVERIFIABLE,
  never guessed VERIFIED). Pure, shadow-safe, wired to nothing live.
- Everything else: outlined, not started. Next up: A2 (claim extraction is
  drafted in `extract_claims`; needs hardening) then B1 (shadow-ground the
  synthesizer's forged patterns).
