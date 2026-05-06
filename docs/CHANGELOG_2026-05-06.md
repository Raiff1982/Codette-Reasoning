# Changelog — 2026-05-06

RC+ξ v2.1 wave: four architectural optimisations, two false-positive fixes, and
a production bug that was silently corrupting every v3 cocoon write since the
domain-routing layer was added.

---

## Architectural Additions

### 1. Quantum Harmonic Framework v2.0 — Dual-Interface Rewrite
**`consciousness/quantum_harmonic_framework.py`** complete rewrite.

Previous version was a standalone physics visualisation script with no live
wiring.  v2.0 is a dual-interface module used by ForgeEngine on every inference
turn.

**Vector interface** (user's log-scale design, corrected):
- `calculate_epistemic_tension(current_state, previous_state)` — L2-squared
  distance between numpy perspective state vectors
- `apply_harmonic_damping(wavefunction, epsilon)` — log-scale dynamic damping:
  `β = β_base × (1 + log(1 + ε))`, clamped to 0.95 to prevent coefficient
  inversion at high epsilon
- `update_attractor_field(state, epsilon, label)` — stores stable states
  (ε < 0.175) as named attractors for directed damping
- `nearest_attractor(state)` — L2 nearest-neighbour lookup
- `apply_directed_damping(wavefunction, epsilon)` — pulls toward nearest
  attractor rather than zero-point; prevents undirected dissipation
- `update_resonant_continuity(state, epsilon)` — updates damped wavefunction
  history for Ψ_r computation

**Scalar interface** (backward-compatible with ForgeEngine):
- `stabilize(epsilon)` — exponential decay toward nearest attractor
  (SYNTHESIS at 0.52 or DISCOVERY at 0.70); `λ_d` scales with consecutive
  high-tension depth so sustained high-ε queries converge faster
- `psi_r` property — trajectory smoothness (1 - normalised std of last 10 ε
  values); 0.0 = chaotic, 1.0 = perfectly stable
- `consecutive_high_tension_depth` property — count of sequential turns above
  the stability threshold (0.35)

**Attractor constants:** FACT=0.35, SYNTHESIS=0.52, DISCOVERY=0.70

Wired into `ForgeEngine.__init__` and `_forge_single_safe()`:
```python
self.qhf = QuantumHarmonicFramework()
_stabilized_epsilon = self.qhf.stabilize(_raw_epsilon)
epistemic_report = {**epistemic_report, "tension_magnitude": _stabilized_epsilon}
```

---

### 2. Zeta-Equilibrium Memory Retrieval
**`reasoning_forge/living_memory.py`** — two new methods.

When the current query has high epistemic uncertainty (ε > 0.45), the forge
engine now surfaces past cocoons from similar-difficulty reasoning moments.
Cross-referencing these "Aha!" moments gives the current cycle a head-start
toward convergence without forcing a conclusion.

**`recall_by_tension(current_epsilon, tolerance=0.20, limit=5, min_importance=4)`**

Retrieval score per candidate:
```
ζ(m) = proximity × importance × (0.4 + 0.6 × exp(−age_days / 14))
```
- `proximity` = 1 − |m.tension − ε| / tolerance  (1.0 at exact match)
- 14-day recency half-life
- Filters out low-importance (< 4/10) memories

**`tension_summary()`** — returns `{count, avg_tension, high_tension_count}`
for health monitoring.

Wired into `forge_with_debate()` Layer 1 memory recall:
```python
if _zeta_epsilon > 0.45 and hasattr(self.memory_kernel, 'recall_by_tension'):
    _zeta_hits = self.memory_kernel.recall_by_tension(current_epsilon=_zeta_epsilon, ...)
    prior_insights.extend([m for m in _zeta_hits if m.title not in _existing])
```

---

### 3. Pre-Cognitive AEGIS Query Filter
**`reasoning_forge/aegis.py`** — new `screen_query()` method.

Runs dual-use / manipulation / harmful-content pattern checks in < 1 ms
**before** LLM inference starts.  Saves 30–60 s of wasted GPU compute on
clearly harmful queries.

```python
def screen_query(self, query: str) -> Tuple[bool, Optional[str]]:
    is_safe, confidence = self.quick_check(query)
    if not is_safe:
        reason = ...  # "dual_use_risk" | "harmful_content" | "manipulation_pattern"
        return False, reason
    return True, None
```

Wired into `_generate_with_phase6()` (step 4.7) before `route_and_generate()`:
```python
_aegis_block = self._precognitive_aegis_check(user_query)
if _aegis_block:
    return {"response": _aegis_block["message"], "aegis_precognitive_block": True, ...}
```

---

### 4. Adaptive Answer Placement (AAP) — Wired into Bridge
**`inference/codette_forge_bridge.py`** — AAP now fires in production.

Previous state: AAP (`SynthesisEngineV3.synthesize_adaptive`) was only called
from inside ForgeEngine methods, which the bridge bypasses when routing through
`orchestrator.route_and_generate()` directly.

Fix: AAP block added to `_generate_with_phase6()` after the empty-response
fallback.  Complexity → epsilon mapping:

| Complexity | ε    | Attractor   | Placement                   |
|------------|------|-------------|-----------------------------|
| SIMPLE     | 0.20 | Fact        | Answer bolded first sentence|
| MEDIUM     | 0.50 | Synthesis   | Narrative flow              |
| COMPLEX    | 0.75 | Discovery   | Debate foregrounded         |

---

## Bug Fixes

### v3 Cocoon Validation Failure on Every Non-Ethics Query
**`inference/codette_forge_bridge.py`**

`_classify_domain()` returns routing labels: `"physics"`, `"consciousness"`,
`"creativity"`, `"systems"`, `"general"`.  These were passed directly as
`problem_type` to `build_cocoon_v3()`.

`cocoon_schema_v2.validate()` checks `problem_type` against
`VALID_PROBLEM_TYPES` — none of the bridge labels except `"ethics"` appear
there.  Every query classified as physics / consciousness / systems / general
→ `ValueError: CocoonV3 validation failed` → warning fired → fell back to
legacy shallow cocoon.

Fix: domain-to-problem-type translation map at the call site:

| Bridge domain   | `VALID_PROBLEM_TYPES` target |
|-----------------|------------------------------|
| `physics`       | `analytical`                 |
| `ethics`        | `ethical`                    |
| `consciousness` | `exploratory`                |
| `creativity`    | `creative`                   |
| `systems`       | `architectural`              |
| `general`       | `unknown`                    |

### LOCK Directive Leakage in Model Responses
**`inference/codette_forge_bridge.py`** — `_scrub_leaked_directives()` added.

Model occasionally echoed `LOCK N — ...` and `=== PERMANENT BEHAVIORAL LOCKS`
blocks verbatim into responses (confirmed in Hamlet benchmark output).
Scrubber runs before AAP wraps text so neither the final response nor the
cocoon ever contains leaked directives.

Patterns matched:
1. `--- ### CONSTRAINTS (ABSOLUTE...` blocks
2. `=== PERMANENT BEHAVIORAL LOCKS ... === END PERMANENT LOCKS ===`
3. Standalone `LOCK N — ...` lines
4. Orphan `=== END PERMANENT LOCKS ===` lines

### Guardian False Positive on Windows File Paths
**`reasoning_forge/guardian.py`**

`\\[nr]` in `_INJECTION_PATTERNS` matched any Windows path containing
`\n` or `\r` in a directory name (e.g. `C:\notes\`, `C:\new_folder\`).
JSON files with string values containing `\n` escape sequences also triggered
it — causing file uploads to be blocked as injection attempts.

Fix: removed `\\[nr]` from `_INJECTION_PATTERNS`.  Real newline-injection
threats are caught by `_PROMPT_INJECTION` content patterns (`ignore all
previous`, `you are now`, etc.), not by the character sequence itself.

### Artist-Query Intercept False Positives
**`inference/codette_server.py`**

Two problems:
1. `_music_context_words` included `song`, `songs`, `music`, `track`,
   `release`, `record`, `label` — high-frequency words in any user's own
   creative project conversation.  Any query mentioning these words activated
   the music-context gate.
2. Pattern 3 fired on any Capitalised phrase near a music word:
   `\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b.+\b(album|song|...)\b`
   — too broad; matched file titles like "My New Track".

Fix:
- Stripped the seven high-FP words from `_music_context_words`; kept only
  unambiguous third-party-inquiry terms: `album`, `discography`, `band`,
  `artist`, `singer`, `genre`, `tour`, `concert`, `lyrics`
- Tightened pattern 3 to require an explicit inquiry verb (`who is`, `what is`,
  `tell me about`, `describe`) before matching

### `build_cocoon_v3` Silent Failure
**`inference/codette_forge_bridge.py`**

`except Exception: pass` on the v3 build swallowed the actual error on every
query, making it impossible to diagnose the root cause.

Fix: `_log.warning("[CocoonBridge] build_cocoon_v3 failed — error=%s  query_snippet=%.60r", ...)`

---

## Query Classifier Expansion
**`reasoning_forge/query_classifier.py`** — 12 new `FACTUAL_PATTERNS`

Previous coverage missed common factual queries:
- `"how many legs does a spider have?"` → MEDIUM (wrong)
- `"who wrote Hamlet?"` → MEDIUM (wrong)

New patterns added:
```python
r"how many ",
r"who (is|was|wrote|created|invented|discovered|founded|built|painted|composed)",
r"what is the (symbol|unit|sign|formula|atomic number|molecular weight|chemical)",
r"what is the \w+ (unit|symbol|constant|formula)",
r"what is the \w+ point",
r"what (planet|element|country|city|animal|organ|muscle|bone|…) (is|are|was|were)",
r"what is \d",
```

Result: 10/10 SIMPLE benchmark queries now correctly classified as SIMPLE
(was ~3/10 before).

Also added to `AMBIGUOUS_PATTERNS` (→ COMPLEX, not SIMPLE):
```python
r"(compatible|reconcil|coexist).*(free will|determinism|consciousness|agency)",
r"is (free will|consciousness|reality|truth|knowledge|justice|beauty)",
```

---

## Benchmark Infrastructure
**`benchmarks/phase71_aap_benchmark.py`**, **`scripts/run_benchmark.ps1`**,
**`Makefile`**

- Default timeout raised 90 s → 120 s (CPU inference takes 43–52 s/query)
- `--timeout` CLI argument added to benchmark script
- `run_benchmark.ps1` accepts `-Timeout` parameter
- `bench-aap` / `bench-aap-quick` Makefile targets accept `TIMEOUT=N` variable
- `sys.path.insert(0, PROJECT_ROOT)` fix — `spectral_trust` was silently 0.0
  because `SynthesisEngineV3` import failed when benchmark ran from a different
  working directory
- `_answer_in_first_sentence()` relaxed to accept 1–4 word crisp answers
  (`"William Shakespeare."` was failing the old ≥5 word threshold)

---

## Benchmark Results

Phase 7.1 AAP SIMPLE tier (10/10 queries, run 2026-05-04):

| Metric | Result |
|--------|--------|
| Attractor routing accuracy | 10/10 Fact attractor |
| Answer in first sentence | 10/10 |
| Classifier accuracy | 10/10 SIMPLE |
| Avg latency | 47.3 s (CPU, expected) |
| Spectral trust | Live (was 0.0 before path fix) |

SYNTHESIS and DISCOVERY tiers pending (requires harmonic damping under
high-ε load).
