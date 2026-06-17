# Changelog — 2026-06-10

Session focus: cross-turn coherence layer, GPQA benchmark integrity, memory
telemetry, template contamination, and a cocoon data-quality incident
(detected, fixed, and cleaned same day).

---

## Added

### Factual Coherence Tracker (`reasoning_forge/factual_coherence_tracker.py`)
- New pre-generation consistency layer: stores Q→A anchors per session and
  injects relevant prior answers as `[COHERENCE ANCHORS]` context before
  generation, so the model maintains consistency naturally instead of being
  patched post-hoc.
- Content-word fingerprints (4-char minimum, expanded stop-word list,
  2+ words required) matched by Jaccard similarity, threshold 0.35
  (0.30 false-positived on "proton mass" vs "electron mass").
- `check_contradiction()` post-generation numeric drift detection with
  float-normalised comparison ("300" == "300.0"); logs `COHERENCE_DRIFT`.
- Rolling 30-anchor cap; max 3 anchors injected per turn, ordered by
  relevance; in-place update when the same question is re-asked.
- Wired into `codette_session.py` (`get_coherence_block`,
  `record_coherence_turn`) and `codette_server.py` (inject before
  generation, record after; responses under 60 chars not recorded).
- Tests: `tests/test_coherence_tracker.py` — 18 tests including documented
  known limitations (paraphrase miss, unit-level equivalence).

### Memory telemetry (`utilities/memory_telemetry.py`)
- `MemoryTracker` context manager with background peak sampler — returns
  baseline / peak / retained-delta / duration as data (`to_dict()`).
- `--watch` mode attaches to running codette_server processes and samples
  real RSS over a window.
- Per-request tracking wired into `codette_server.py`: every generation
  logs a `[MEMORY]` line and attaches `result["memory_telemetry"]`.
- **Measured findings:** idle steady-state 5.2 GB fully resident; peak under
  load ~5.8 GB; all 10 LoRA adapters total just 280 MB. On a 93%-utilised
  machine, 2.4 GB of weights were churning through the pagefile per request
  (min 3,420 MB → peak 5,795 MB); after stabilisation the swing was 2 MB.

### `CODETTE_MLOCK` flag (`inference/codette_orchestrator.py`)
- Opt-in `CODETTE_MLOCK=1` pins model weights in physical RAM
  (`use_mlock=True`) so the OS cannot page them out between requests.
  Only enable with ~6 GB actually free.

### GPQA self-consistency mode (`benchmarks/gpqa_codette.py`)
- New `--mode sc3`: 3 votes per question with independently shuffled answer
  orderings (seeds 0/1/2), majority decided by **answer text** (cancels
  position bias). Reports unanimous-vs-split consensus breakdown and saves
  `sc3_stats` in results JSON.

### Cocoon cleanup script (`scripts/clean_cocoon_queries.py`)
- One-shot repair for the cocoon query contamination (see Fixed below).
  Dry-run by default; `--apply` rewrites with originals backed up to
  `cocoons/_backup_query_cleanup/`.

## Changed

### Informal anchor phrasing (`reasoning_forge/constraint_tracker.py`)
- `ANCHOR_PHRASE_PATTERNS` now recognises "don't forget X", "keep in mind X",
  "call it X", "refer to it as X" (with or without the word "phrase").
- Fast-path keyword signals extended with `forget`, `note`, `call`, `refer`.
- Tests: 12 passing in `tests/test_constraint_tracker.py`.

### GPQA routing fix (`inference/adapter_router.py`)
- `newton` strong keywords expanded with chemistry (stoichiometry, enthalpy,
  titration, …), biology (dna, enzyme, photosynthesis, …), and exam-format
  signals (`(a)`–`(d)`, "which of the following").
- New quantitative-science veto: ≥2 GPQA-style signals removes
  empathy / philosophy / consciousness from primary contention
  (fixes empathy adapter dominating at 61.2% on physics questions).
- `_classify_domain()` in `codette_forge_bridge.py` gains "chemistry" and
  "biology" domains.

### GPQA 0-shot prompt hardening (`benchmarks/gpqa_codette.py`)
- `prompt_0s` no longer invites extended reasoning after the answer —
  reduces format drift and parse failures in long generations.

### Template-density scrubber (`inference/codette_forge_bridge.py`)
- New `_strip_template_sentences()` layer after the exact-phrase regex scrub:
  any sentence containing ≥2 template markers is dropped. Catches rephrased
  boilerplate the regex list cannot.
- Markers upgraded same-day from exact substrings to **37 regex families**
  after a post-restart specimen mutated past the substring version
  ("revealing *new* insights", "deeper layers of *understanding*",
  "multi-layered approaches", "Your careful approach … is noteworthy").
  Families match phrasing variations: `reveal(ing|s|ed)? (\w+ )?insights?`,
  `(deeper|several|new) layers? of \w+`, etc.
- Markers that fire on the user's own query are exempt, so genuine answers
  about Codette's machinery survive. Verified zero false positives on
  technical, emotional-support, and query-exempted meta content.
- Fully-contaminated responses (every sentence template-dense) are replaced
  with an honest fallback instead of reaching the user; logged as
  `[SCRUB] FULL template contamination`.

## Fixed

### Cocoon query contamination (data-quality incident)
- **Bug:** all three cocoon storage points (`build_cocoon_v3`,
  `wrap_reasoning`, Supabase mirror) stored the ENRICHED query — including
  appended `# ACTIVE CONTINUITY SUMMARY` sections and (since the coherence
  tracker shipped) prepended `[COHERENCE ANCHORS]` / `[SESSION CONSTRAINTS]`
  blocks — instead of the user's actual words. 1,141 of 1,357 cocoon JSON
  files (84%) were affected, polluting FTS5 recall and pattern mining.
- **Fix:** storage points now use `user_query`;
  `_extract_primary_user_query()` strips prepended bracketed blocks as well
  as appended sections (previously it only handled appended).
- **Cleanup:** `scripts/clean_cocoon_queries.py --apply` repaired all 1,141
  files; verified 0 remaining; originals in `cocoons/_backup_query_cleanup/`.
  SQLite stores (`codette_memory.db`, `codette_core.db`) checked: clean.

### Coherence anchors cross-contaminating GPQA benchmark
- **Bug:** benchmark questions share vocabulary, so the coherence tracker
  injected one GPQA question's answer into the next similar question's
  prompt (cocoon listings showed `FAIL` integrity + `[COLLAPSE]`).
- **Fix:** `codette_server.py` detects benchmark/exam-style queries
  ("What is the correct answer to this question" or ≥3 choice lines) and
  skips BOTH anchor injection and anchor recording for them.
- **Note:** any GPQA results produced between the coherence tracker landing
  and this fix are suspect. The 2026-06-06 run (30.81% 0-shot) predates the
  tracker and is clean.

## Benchmark status (GPQA Diamond, 198 questions)
| Run | Mode | Accuracy | Parse fails |
|-----|------|----------|-------------|
| 06-04/05 | cot | 25.25% | 4 |
| 06-05 | 0shot | 28.79% | 1 |
| 06-06 | 0shot (50q) | 30.00% | 0 |
| 06-06 | 0shot | **30.81%** | 0 |

CoT underperforms 0-shot on this stack; the 0-shot trend is positive.
Next steps: re-run 0-shot post-fixes, then `--mode sc3`; longer-term,
newton adapter fine-tune on the public GPQA training split.
