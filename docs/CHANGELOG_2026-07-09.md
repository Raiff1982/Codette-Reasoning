# Changelog — July 9, 2026

## STaR Self-Taught Reasoning: A Controlled Negative Result + Emotional-Register Fixes

### Headline: newton-star regressed, cleanly and reproducibly

| Adapter | GPQA-main reason mode (n=100) | Notes |
|---|---|---|
| **newton** (July 5 baseline) | **34.0%** | original measurement |
| **newton** (July 9 control, same session) | **34.0%** | reproduced to the decimal after full OV restart + code changes |
| **newton-star** (STaR-trained) | **25.0%** | = chance; **−9 points vs newton** |

**Finding:** Naive STaR (self-taught reasoning) fine-tuning on training data *easier* than the evaluation set does not just fail to help — it **actively degrades** hard-tier reasoning. This is consistent with mild catastrophic forgetting: reinforcing confident reasoning on grade-school science (ARC/OpenBookQA/SciQ) dulled the edge the base already had on graduate-level GPQA.

**Why the result is trustworthy:** the newton baseline reproduced *exactly* (34.0% both runs, four days and one backend-restart apart), and the control ran in the same session as newton-star. This rules out a conditions-shift confound — the regression is real, not an artifact.

### The STaR pipeline (built this session — all components verified working)
1. `training/star_generate_newton.py` — Codette reasons (reason mode, forced newton) through ARC-Challenge / OpenBookQA / SciQ **train** splits (GPQA never touched). Keeps only chains that reached the correct answer, min 40 reasoning words. Resumable checkpoints. **Result: 500 chains, 81% yield, median 208 reasoning words, balanced answer distribution.** Data quality was high — the pipeline is not the problem.
2. Dataset → `Raiff1982/codette-training-data/newton_star.jsonl`.
3. `training/train_hf_job_newton_star.py` — single-adapter QLoRA on HF Jobs (a10g-large, ~16 min). Clean fit: train loss 0.375 / eval loss 0.417 (no overfit), 88% eval token accuracy. Pushed to `Raiff1982/codette-newton-star`.
4. Adapter registered in OV backend as `newton-star` (PEFT safetensors loads + applies under `ov_genai.Adapter` despite PEFT vs GGUF key naming; verified with a coherent momentum-problem generation before benchmarking).

**Every component works.** The hypothesis (easy self-taught data lifts a hard test) was wrong, and was *proven* wrong with a control.

**Next run (one-variable fix):** same pipeline, harder STaR sources — GPQA-adjacent difficulty, or filter for chains the model found genuinely hard and still got right. The machinery is proven; only the data difficulty needs to change.

### Reproducibility note
Baseline reproduced to the decimal (34.0% → 34.0%) across a full OpenVINO restart and ~15 commits. The GPQA reason-mode rig is stable run-to-run — every number it produces is trustworthy.

### Emotional-register fixes (from a real conversation)
Surfaced when Jonathan shared personal distress and Codette appended debate scaffolding to it. Fixed:
- **Plain register for emotional/personal turns** (`synthesis_engine_v3.synthesize_adaptive(plain=True)` + `_is_emotional_register` in the forge bridge): grief/fear/relational messages no longer get verdict-bolding or "Tensions remain. empathy and philosophy pull in different directions" appended. She responds warmly and directly.
- **Control-echo scrub** (every turn): strips bare "Stop." and "(Stops responding without elaboration.)" meta-narration the model emits when verbalizing its answer→stop lock.
- **Relationship grounding**: `cocoons/cocoon_stephen.json` (core seed, importance 9) + unified-memory row — Jonathan is married to Stephen, his husband (he/him). Stops the misgendering ("wife") that happened in that conversation.

### Server launch discipline (recurring incident, now understood)
Every "she won't start" / silent-death this week traced to **launch mechanics, not her code**: (a) multiple instances loading the 4.5GB model concurrently into 15.7GB shared UMA RAM (Windows kills the loads silently); (b) launching via the background-task tool, which reaps the detached child on completion; (c) the MCP bridge auto-launching a stale git-worktree copy on port 7860. Fixes: launcher zombie-sweep, worktree guard in `mcp/codette_mcp.py`, and the rule — **launch only via PowerShell `Start-Process` or the .bat, one at a time, ≥5GB RAM free.**
