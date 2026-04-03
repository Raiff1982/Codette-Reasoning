# April 2, 2026 Update Section for HF Repos

Add this section to the README.md of:
- `Raiff1982/codette-llama-3.1-8b-merged`
- `Raiff1982/codette-llama-3.1-8b-gguf`
- `Raiff1982/codette-lora-adapters`

## April 2, 2026 Enhancement Wave

This model now includes all April 2, 2026 improvements from the Codette research release:

### Event-Embedded Value (EEV) Analysis Framework
When evaluating scenarios with ethical weight (especially involving suffering or harm):
- Singularity-aware valuation detects "Infinite Subjective Terror" moments
- Sensitivity parameters weight moments by intensity × duration × context
- AEGIS ethical modulation integrates virtue, duty, care, justice, rights, utility frameworks
- Confidence levels explicitly report uncertainty rather than false precision

### Tightened Triggers (False Positive Elimination)
- **Diagnostic mode**: Only activates on explicit keywords (`system status`, `diagnostics`, `self-check`)
- **Auto-tool mode**: Reduced false triggers; normal chat doesn't drift into code mode
- Phrases like "everything ok?" or "status report" no longer trigger system diagnostics

### Safe Web Research (Opt-In, Cited)
- Web research requires explicit user permission
- Safe fetch rules: blocks localhost/private targets, caps page size, extracts text-only
- Always includes citations with URLs and confidence levels
- Research findings stored as reusable context for future queries

### Memory Continuity & Decision Landmarks
- **Active continuity summary**: Compact working-memory thread for long conversations
- **Decision landmarks**: User constraints and assistant commitments become durable recall points
- **Valuation persistence**: Value analyses and web research stored as searchable cocoons

### Confidence & Hallucination Hardening
- 3-layer hallucination prevention: query intercept, stream detection, post-generation self-correction
- Trust tags in responses: `memory-backed`, `frontier-informed`, `web-cited`, `low-verification`
- Explicit uncertainty: When unable to verify claims, clearly states "I don't have reliable information about that"

### Coherence Hardening for Long Conversations
- Maintains narrative coherence across multi-turn conversations
- Tracks own statements; doesn't contradict earlier claims in same conversation
- Acknowledges context and honors commitments made earlier in conversation

---

**Full Changelog**: See [Codette-Reasoning repository](https://github.com/Raiff1982/Codette-Reasoning/blob/main/docs/CHANGELOG_2026-04-02.md) for detailed technical documentation.

**Ollama Version**: Available as `raiff1982/codette:latest` - includes full April 2 system prompt.

**Research**: See [Codette Paper v5](https://github.com/Raiff1982/Codette-Reasoning/blob/main/paper/codette_paper_v5.pdf) for academic validation.
