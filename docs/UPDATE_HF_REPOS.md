# How to Update the 3 HF Model Repos (April 2, 2026)

Since the repos contain large model files, direct git operations are limited. **Update via HuggingFace Web UI:**

## For each of these repos:
1. `Raiff1982/codette-llama-3.1-8b-merged`
2. `Raiff1982/codette-llama-3.1-8b-gguf`
3. `Raiff1982/codette-lora-adapters`

## Steps:

1. **Go to the repo page** (e.g., https://huggingface.co/Raiff1982/codette-llama-3.1-8b-merged)

2. **Click "Files and versions"** tab

3. **Look for "README.md"** in the file list
   - If it exists, click the pencil icon to edit
   - If not, click "Add file" → "Create a new file" and name it `README.md`

4. **Add this section to the README:**
   - Copy the content from `docs/HF_README_APRIL2_UPDATE.md`
   - Paste it into the README editor
   - You can add it as a new section at the top or bottom

5. **Commit the changes:**
   - Add a commit message: "Update README: April 2, 2026 enhancements"
   - Click "Commit changes to main"

6. **Repeat for all 3 repos**

---

## Quick Copy-Paste Content

### April 2, 2026 Enhancement Wave

This model now includes all April 2, 2026 improvements from the Codette research release:

**Event-Embedded Value (EEV) Analysis Framework** — Singularity-aware valuation with AEGIS ethical modulation for complex decision scenarios.

**Tightened Triggers** — Eliminated false positives in diagnostic and auto-tool modes through explicit keyword requirements.

**Safe Web Research** — Opt-in, cited web search with safe fetch rules and stored research findings.

**Memory Continuity** — Active continuity summaries and decision landmarks for coherent long-form conversations.

**Confidence Hardening** — 3-layer hallucination prevention with explicit uncertainty reporting and trust tags.

**Full Changelog**: [codette_paper_v5](https://github.com/Raiff1982/Codette-Reasoning/blob/main/docs/CHANGELOG_2026-04-02.md)

---

**Note**: The Ollama version `raiff1982/codette:latest` includes the full April 2 system prompt with all these enhancements active.
