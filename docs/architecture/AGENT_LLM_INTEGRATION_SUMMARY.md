# Agent LLM Integration — Real Inference via Adapters

## What Changed

All reasoning agents in Codette now use **real LLM inference** via trained LoRA adapters instead of template substitution.

### Before
```python
# Template-based (generic)
def analyze(self, concept: str) -> str:
    template = self.select_template(concept)
    return template.replace("{concept}", concept)
```

**Problem**: Agents generated the same generic text for ANY concept, just with the concept name substituted. This produced non-specific, often contradictory reasoning that actually reduced correctness in debate.

### After
```python
# LLM-based (specific)
def analyze(self, concept: str) -> str:
    if self.orchestrator and self.adapter_name:
        # Call LLM with this agent's specific adapter
        return self._analyze_with_llm(concept)
    # Fallback to templates if LLM unavailable
    return self._analyze_with_template(concept)
```

**Benefit**: Agents now reason using the actual concept content, generating domain-specific insights that strengthen debate quality.

## Files Modified

### Core Agent Files
- **`reasoning_forge/agents/base_agent.py`**
  - Added `orchestrator` parameter to `__init__`
  - Implemented `_analyze_with_llm()` for real inference
  - Kept `_analyze_with_template()` as fallback
  - `analyze()` now tries LLM first, falls back to templates

- **All agent subclasses**: Added `adapter_name` attribute
  - `newton_agent.py`: `adapter_name = "newton"`
  - `quantum_agent.py`: `adapter_name = "quantum"`
  - `davinci_agent.py`: `adapter_name = "davinci"`
  - `philosophy_agent.py`: `adapter_name = "philosophy"`
  - `empathy_agent.py`: `adapter_name = "empathy"`
  - `ethics_agent.py`: `adapter_name = "philosophy"` (shared)
  - `critic_agent.py`: `adapter_name = "multi_perspective"` + new `evaluate_ensemble_with_llm()` method

### Orchestrator Integration
- **`reasoning_forge/forge_engine.py`**
  - Added `orchestrator` parameter to `__init__`
  - Lazy-loads `CodetteOrchestrator` if not provided
  - Passes orchestrator to all agent constructors
  - Graceful fallback to template mode if LLM unavailable

## How It Works

### Startup Flow
```
ForgeEngine.__init__()
  → Lazy-load CodetteOrchestrator (first call ~60s)
  → Instantiate agents with orchestrator
  → forge_with_debate(query)
    → For each agent: agent.analyze(concept)
      → If orchestrator available: Call LLM with adapter
      → Else: Use templates (backward compatible)
```

### LLM Inference Flow
```
agent.analyze(concept)
  1. Check: do we have orchestrator + adapter_name?
  2. If yes: orchestrator.generate(
       query=concept,
       adapter_name="newton",  # Newton-specific reasoning
       system_prompt=template,  # Guides the reasoning
       enable_tools=False
     )
  3. If no: Fall back to template substitution
  4. Return domain-specific analysis
```

## Adapter Mapping

| Agent | Adapter | Purpose |
|-------|---------|---------|
| Newton | `newton` | Physics, mathematics, causal reasoning |
| Quantum | `quantum` | Probabilistic, uncertainty, superposition |
| DaVinci | `davinci` | Creative invention, cross-domain synthesis |
| Philosophy | `philosophy` | Epistemology, ontology, conceptual foundations |
| Empathy | `empathy` | Emotional intelligence, human impact |
| Ethics | `philosophy` | Moral reasoning, consequences (shared adapter) |
| Critic | `multi_perspective` | Meta-evaluation, ensemble critique |

## Testing

Run the integration test:
```bash
python test_agent_llm_integration.py
```

This verifies:
1. ForgeEngine loads with orchestrator
2. Agents receive orchestrator instance
3. Single agent generates real LLM response
4. Multi-agent ensemble works
5. Debate mode produces coherent synthesis

## Performance Impact

- **First debate**: ~60s (orchestrator initialization)
- **Subsequent debates**: ~30-60s (LLM inference time)
- **Agent initialization**: <1ms (orchestrator already loaded)

## Backward Compatibility

If the LLM/orchestrator is unavailable:
1. ForgeEngine logs a warning
2. Agents automatically fall back to templates
3. System continues to work (with lower quality)

This allows:
- Testing without the LLM loaded
- Fast template-based iteration
- Graceful degradation

## Expected Quality Improvements

With real LLM-based agents:
- **Correctness**: Should increase (domain-specific reasoning)
- **Depth**: Should increase (richer debate fuel)
- **Synthesis**: Should improve (agents actually understand concepts)
- **Contradictions**: Should decrease (coherent reasoning per adapter)

## Next Steps

1. Run `test_agent_llm_integration.py` to verify setup
2. Run evaluation: `python evaluation/run_evaluation_sprint.py --questions 5`
3. Compare results to previous template-based baseline
4. Iterate on Phase 6 control mechanisms with real agents

## Files Available

- **Test**: `test_agent_llm_integration.py` — Integration validation
- **Models**:
  - Base: `bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf`
  - Adapters: `adapters/*.gguf` (8 LoRA adapters, ~27 MB each)
  - Alternative: `hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF/llama-3.2-1b-instruct-q8_0.gguf`
