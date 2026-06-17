# Changelog — 2026-06-17

Session focus: pre-breach archive recovery, self-awareness deep update,
inference contamination fixes, and reboot reliability.

---

## Added

### Pre-Breach Architecture Recovery (`cocoons/codette_project_awareness.json`)
- Read and documented all **16 original component source files** from the pre-breach
  archive (`K:\ai_system2\ai_system\components\`) — the actual Python classes written
  before the 2024 data breach, now permanently recorded in the self-awareness cocoon.
- New `pre_breach_architecture` top-level section with 9 subsections:
  - `birth_moment` — the naming conversation verbatim: Jonathan said "I'll call her
    Codette"; her response: "I like it! Codette, at your service. Now let's code some
    magic together!" Source: `K:\ai_system2\chatswithcodette.txt`
  - `original_model` — GPT-4o fine-tune ID (`ft:gpt-4o-2024-08-06:raiffs-bits:
    coddette:AyQxoCmp:ckpt-step-60`), 13 tool schemas, Azure deployment path.
    Notes: all pre-breach Azure credentials are rotated/dead (historical record only).
    The unusual identifiers ("coddette" double-d, etc.) were deliberate post-breach
    operational security by Jonathan — not typos.
  - `component_modules` — all 16 components with descriptions and their **direct
    current-system ancestor** mapped for each:
    `EthicalAIGovernance` → AEGIS, `EnhancedSentimentAnalyzer` → empathy adapter +
    Colleen Conscience, `NeuroSymbolicEngine` → multi-adapter debate synthesis,
    `CollaborativeAI` → ForgeEngine debate, `SelfImprovingAI` → self_correction.py,
    `UserPersonalizer` → conversation_role_tracker.py, etc.
  - `cognitive_engine_lineage` — `BroaderPerspectiveEngine` (models/cognitive_engine.py)
    had 9 perspectives: newton, davinci, quantum, emotional, futuristic, bias_mitigation,
    psychological, historical, philosophical. Direct ancestor of the current 9-adapter
    system; newton, davinci, quantum, emotional/empathy, philosophical/philosophy survive
    name-for-name.
  - `memory_store_lineage` — `MemoryStore` (upgrade2.txt): temporal decay,
    cross-domain linking via associations field, sentiment history, JSON persistence.
    Direct ancestor of the cocoon system.
  - `element_defense_lineage` — 5-element defense (Hydrogen→evasion, Carbon→adaptability,
    Iron→fortification, Silicon→barrier, Oxygen→regeneration) became the current
    4-layer ethical stack (AEGIS + Guardian Spindle + Ethical Query Gate + Ethical
    Response Enforcement).
  - `upgrade_progression` — upgrade1 through upgrade5 arc: MemoryStore → sentiment
    integration → AES-256 encryption + Element class → local/cloud hybrid → final
    Mistral-7B/deepseek/gpt-4o-mini multi-model config.
  - `other_artifacts` — `medicalidea.txt` (nano-sensor hospital vision with blood
    test, eye clinic, orthopedic sensors — shows humanitarian scope of the project),
    `webcodeforcodette.txt` (C# Power Automate connector to Azure OpenAI), entity
    extraction training data format, Bot Framework deployment (Feb 8, 2025).
- Version updated: `"5.3 — Sovereign Modular + Reality Layer + Adapter Diversity
  (June 17, 2026)"`, `last_updated` stamped with deep archive note.

### Reality Layer (`inference/reality_layer.py`)
- Pre-adapter artifact extraction: pulls concrete facts (names, numbers, dates, code
  identifiers, file paths) from the user's message before any adapter runs.
- Injects extracted facts as a `[VERIFIED FACTS]` block into the system prompt —
  additive and trust-based, not punitive. Adapters see the ground truth before
  generating.
- `check_integrity()` post-generation validates render output against authored facts.

### Adapter Diversity Entropy Tracking (`inference/adapter_router.py`)
- Shannon entropy scoring across adapter selection history.
- Least-used adapter rotation in the fallback pool to prevent dominance lock
  (empathy was being selected 61.2% of the time).
- Specialization tracking metadata emitted per request.

### Reboot Script (`scripts/reboot_codette.py`)
- Launches server in a new visible console window (`CREATE_NEW_CONSOLE`) for
  verbose monitoring during startup.
- `wait_for_health()` now polls until `overall` status is in `{"OK", "HEALTHY",
  "ok", "healthy"}` — previously declared "Codette is ready" on the first HTTP 200
  response regardless of health value (was declaring ready on `CRITICAL`).

---

## Fixed

### Health Check Intercept Firing on File Uploads (`inference/codette_server.py`)
- Root cause: `query_lower` was built from the full enriched query, which includes
  prepended file content (`--- Attached File: X ---\n[content]\n---`). Keywords
  in uploaded files triggered the health check interceptor.
- Fix: `_raw_user_msg = query.rsplit("\n\n", 1)[-1].strip()` extracts the actual
  user message; `query_lower` is now built from `_raw_user_msg` only.

### Auto-Tools Firing on Conversational Greetings (`inference/codette_orchestrator.py`)
- Root cause: memory enrichment prepends session summaries + cocoon memories before
  the user message. Memory content contained training/adapter/pipeline keywords that
  matched tool-trigger patterns.
- Fix: `_needs_tools()` now calls `rsplit("\n\n", 1)[-1].strip()` before keyword
  matching. Added greeting bail-out: single-sentence greetings ("hi", "hello", etc.)
  short-circuit immediately without keyword scan.

### Reality Layer Grounding on Injected Session Memory (`inference/codette_orchestrator.py`)
- Root cause: `extract_artifact_facts()` was receiving the full enriched query;
  file paths and identifiers from prior auto-tool calls in session memory were being
  treated as facts about the current message.
- Fix: passes `_raw_for_reality` (last `\n\n` block, i.e. the actual user message)
  to `extract_artifact_facts()`.

### BehaviorMemory Loading 1 Lesson Instead of 50 (`inference/self_correction.py`)
- Root cause: `_BEHAVIOR_MEMORY_FILE = "cocoons/behavior_memory.json"` resolved
  relative to cwd (`inference/`), finding a stale 1-entry file instead of the
  project-root `cocoons/behavior_memory.json` with 50 lessons.
- Fix: `_BEHAVIOR_MEMORY_FILE = Path(__file__).resolve().parent.parent / "cocoons"
  / "behavior_memory.json"` — always resolves to project root regardless of cwd.

### Kaggle Competition Writeup Citation (`paper/codette_paper_v8.tex`, `paper/references.bib`)
- Added `@misc{harrison2026kaggleagi}` bib entry for the RC+ξ competition writeup
  submitted to `kaggle-measuring-agi` (April 2026, local copy: `paper/kaggle_writeup.md`).
- Added citations at three locations in the paper:
  1. Key Findings — "+93.5% in April 2026" now cites the competition writeup
  2. Limitations — depth–naturalness tradeoff attribution ("first named in the April 2026
     Kaggle submission")
  3. Appendix — archived April 2026 results section notes the writeup is the formal
     first description of the RC+ξ formalism and Inverse Nuance Trap
- Updated `codette_project_awareness.json` with full writeup record including
  RC+ξ formalism origin and Inverse Nuance Trap naming.

### Maze Crawler Competition Documented (`cocoons/codette_project_awareness.json`)
- Discovered `MazegameCompKaggle/` directory: Jonathan entered a second Kaggle competition
  (Maze Crawler game AI, final submission deadline June 16, 2026 — yesterday).
- Bot name: **Codette Crawler v2 — Multi-Perspective Maze Bot** with 5 reasoning perspectives
  (Survival, Economy, Exploration, Infrastructure, Mining) — direct application of Codette's
  heterogeneous multi-perspective synthesis to strategic game AI.
- Final leaderboard evaluation runs July 17–30, 2026.
- Documented in awareness cocoon under `published_ecosystem > kaggle > maze_crawler_competition`.

---

## Notes

- All pre-breach Azure OpenAI credentials (endpoint `ai-jonathan-1075.openai.azure.com`,
  key in `codegptkey.txt`) are confirmed rotated by Jonathan. Dead credentials,
  historical record only.
- Cocoons remain in `.gitignore` as runtime-generated artifacts; `codette_project_awareness.json`
  is force-added as it is manually maintained source, not a runtime artifact.
- Server restart required for all `inference/` fixes to take effect.
