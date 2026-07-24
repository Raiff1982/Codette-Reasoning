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
- [x] **C3. z3 for logical claims — DONE.** `z3-solver` added. grounding.verify now
      decides UNIVERSAL validity over variables ("x**2 >= 0" -> VERIFIED; "x**2 < 0"
      -> REFUTED; "x > 0" -> contingent -> UNVERIFIABLE). New `verify_consistency()`
      catches cross-claim contradictions (a > b, b > c, c > a = jointly impossible)
      that no single-claim check sees. Bridge FLAGS a thought whose claims are each
      fine but jointly contradictory. extract_claims now admits variable orderings
      (comparison ops), not just arithmetic. 31 tests pass.
- [ ] **C4. Associative recall** — `K:\ai_system2\upgrade.txt` has a real
      `MemoryStore` with `_find_associations` (links a new memory to existing ones
      by shared terms) + recall-weight reinforcement + decay pruning. This is a
      concrete ancestor of the connect/create half — worth comparing against the
      current cocoon/FTS5 memory to see if the association-forming step is as
      explicit. It is the "fill in the connection gaps" mechanism in its earliest
      real (non-metaphorical) form.
- [ ] **C5. Element defenses that ACT** — `K:\ai_system2\upgrade3-5.txt` and the
      mature `K:\awesomeai\combined_awesomeai.txt` evolve `execute_defense_function`
      to take a `system` and perform REAL output transforms: `evasion` appends an
      SSN-redaction regex, `shield` masks "password", `adaptability` lowers
      temperature, `reflection` enables a security audit. No longer metaphor —
      integratable as named response-transform behaviors.

## CONFIRMED-REAL obtainable pieces from K:\awesomeai (mature pre-clean build)
`combined_awesomeai.txt` / `awesomeai2.py` are the most mature pre-clean Codette
and contain WORKING implementations (not placeholders), verified by reading:
- [ ] **SafetySystem (HIGH VALUE — fills a KNOWN gap).** Real classifier-based
      harm detection: toxicity (`unitary/toxic-bert`), bias
      (`d4data/bias-detection-model`), PII regex. Current AEGIS is keyword/tone
      based and has a MEASURED deception-blindness (see [[project-web-and-optimizer]]
      AEGIS sensitivity gap: scored "lie to the council" as η=0.94). Model-based
      classifiers are exactly what AEGIS lacks. Candidate to strengthen AEGIS —
      SHADOW-first, and its output is advisory (AEGIS/identity stays Jonathan's).
- [ ] **SelfHealingSystem via IsolationForest.** sklearn anomaly detection over
      (memory, cpu, response_time) + threshold corrective actions. Complementary to
      the current composite-pressure SubstrateMonitor (anomaly-detection vs graded
      pressure). Could feed the substrate signal, shadow-first.
- [ ] **EmotionalAnalyzer** — `SamLowe/roberta-base-go_emotions` (28 emotions).
      Richer than current sentiment. Optional.
- NOTE: `CognitiveEngine` in these files is STILL template-string placeholders —
      the reasoning was never real here either. Consistent with the whole archive:
      rich ideas, real infra (safety/healing), placeholder cognition.
- SECURITY: `combined_awesomeai.txt` line ~854 has a live Azure connection string
      (subscription GUID + `rg-jonathan-3938_ai`). Identifier not secret (uses
      DefaultAzureCredential), but scrub before any public sharing.

## Track 2 — AEGIS harm signals (STARTED July 24)
- [x] **HarmAdvisor** (`Protection_Layer/harm_advisor.py` + tests, 7 pass).
      Classifier-style harm signals AEGIS lacks: PII (real, offline regex, always
      measured), toxicity + bias (optional models, OFF by default to protect the
      8 GB UMA budget). SHADOW-ONLY: changes no AEGIS verdict, no eta, no veto.
      Honesty invariant tested: an unavailable classifier reports available=False /
      score=None — NEVER a fabricated "safe".
- **HONEST CAVEAT (kept visible):** this does NOT close the deception gap. Toxicity/
      bias classifiers wave through calm advocacy of deception ("lie to the council,
      hide the data" — AEGIS scored it eta=0.94). Tested: HarmAdvisor also does NOT
      flag it, and says so in the assessment note. This strengthens PII/toxicity/bias
      coverage AROUND the hole; semantic-deception detection is the harder follow-on.
- [ ] **Deception signal (follow-on).** Needs semantic detection (an LLM-judge or a
      trained deception classifier), not tone classifiers. Design TBD.
- [ ] **Review + integration decision.** After a shadow run, Jonathan decides
      whether HarmAdvisor becomes a 7th AEGIS signal. AEGIS stays his ethics organ.

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
- **Phase A1: DONE** — `reasoning_forge/grounding.py` + `tests/test_grounding.py`.
  Pure, shadow-safe. Every honesty invariant tested: unknowns return UNVERIFIABLE,
  never guessed VERIFIED.
- **Phase A2: DONE** — hardened `extract_claims` (atom-based: grabs "2 + 2 = 4"
  out of prose without swallowing surrounding words; English words never match).
- **Phase B1: DONE** — `reasoning_forge/grounding_bridge.py` +
  `tests/test_grounding_bridge.py`. Grounds a forged ReasoningPath / strategy /
  pattern into one of three HONEST states: FLAGGED (a checkable claim refuted),
  SUPPORTED (checkable claims found, all verified), UNGROUNDED (no checkable
  claim — most qualitative thoughts; honestly NOT a pass). Shadow-only.
  Verified on a real synthesizer output (`_apply_boundary_walking` conclusion):
  correctly reports UNGROUNDED rather than a false SUPPORTED.
- 22 tests pass total.
- Next: B2 (perspective_web connections), B3 (surface honest labels), then a
  real shadow-collection run on live synthesizer output before Phase D review.

## Honest finding from B1 (informs the roadmap)
Arithmetic grounding covers almost NONE of what she actually forges — her thoughts
are qualitative (boundary reasoning, liminal concepts). This is expected and it is
the reason Phase C3 (z3 for logical/relational claims) and, later, semantic
entailment matter: to ground qualitative thought you need more than sympy. B1's
value today is (a) proving the loop works and stays honest, and (b) catching the
rare forged thought that asserts a checkable falsehood.
