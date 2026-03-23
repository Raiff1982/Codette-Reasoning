# Test 3: Live Evaluation with Agent LLM Inspection

## Run Command
```bash
python evaluation/run_evaluation_sprint.py --questions 5 --output results.json
```

## What to Look For

### Phase 1: Orchestrator Load (should see in first 60 seconds)
```
[1/4] Loading ForgeEngine with Phase 6...
  ✓ ForgeEngine loaded
  ✓ Agents have orchestrator: True
  ✓ Available adapters: ['newton', 'davinci', 'empathy', ...]
```

**CRITICAL:** If you see "False" or "Using template-based agents" → orchestrator failed to load

### Phase 2: Agent Setup Inspection
```
[AGENT SETUP INSPECTION]
  Orchestrator available: True
  Available adapters: [...]

  Agent LLM modes:
    Newton       ✓ LLM        (orch=True, adapter=newton)
    Quantum      ✓ LLM        (orch=True, adapter=quantum)
    DaVinci      ✓ LLM        (orch=True, adapter=davinci)
    Philosophy   ✓ LLM        (orch=True, adapter=philosophy)
    Empathy      ✓ LLM        (orch=True, adapter=empathy)
    Ethics       ✓ LLM        (orch=True, adapter=philosophy)
```

**CRITICAL**: If any show "✗ TEMPLATE" → agent didn't get orchestrator

### Phase 3: First Question Synthesis Sample
```
[1/5] What is the speed of light in vacuum?...
    [Phase 1-5] 2340 chars, correctness=0.50
      Sample: "The speed of light is a fundamental constant...
    [Phase 6 Full] 2150 chars, correctness=0.65
      Sample: "Light propagates through vacuum at precisely...
    [Phase 6 -PreFlight] 2100 chars, correctness=0.62
      Sample: "The speed of light, denoted by the symbol c...
```

**What it means**:
- If Phase 6 Full/No-PreFlight have **longer** synthesis than Phase 1-5 → agents doing more reasoning ✅
- If Phase 1-5 has **longer** synthesis → something's wrong ❌
- If synthesis reads generic ("analyzing through lens") → likely templates ❌
- If synthesis is specific ("speed of light is 299,792,458 m/s") → likely real LLM ✅

### Phase 4: Final Scores
Look for this pattern:
```
🔍 EVALUATION SUMMARY
Condition          | Correctness | Depth | Synthesis Len
───────────────────┼─────────────┼───────┼──────────────
Baseline (Llama):  |    0.50     |   1   |    500
Phase 1-5:         |    0.48     |   5   |   2100
Phase 6 Full:      |    0.60     |   5   |   2200
Phase 6 -PreFlight:|    0.58     |   5   |   2150
```

**Verdict**:
- Phase 6 > Phase 1-5 and Phase 1-5 > Baseline → System improving ✅
- If Phase 6 < Phase 1-5 → Something wrong with Phase 6 patches ❌
- If Phase 6 Full ≈ Phase 1-5 → Semantics/preflight not helping much (acceptable)

## Critical Checkpoints

| Checkpoint | Success | Failure | Action |
|-----------|---------|---------|--------|
| Orchestrator loads | Logs say "ready" | Logs say "error" | Check if base GGUF path exists |
| All agents show ✓LLM | All 6 agents marked ✓ | Any marked ✗ | Investigate which agent failed |
| Synthesis length increases | Phase6 > Phase1-5 | Phase1-5 > Phase6 | Check if agents using LLM |
| Correctness improves | Phase6 > Phase1-5 | Phase1-5 ≥ Phase6 | Adapters may be weak |
| Synthesis is specific | Mentions concrete details | Generic template text | Agents fell back to templates |

## Expected Timeline

- **Orchestrator load**: ~60 seconds (one-time, then fast)
- **First question (debate)**: ~30-45 seconds
- **5 questions total**: ~3-5 minutes
- **Final report**: <1 second

## If Something Goes Wrong

1. **Orchestrator fails to load**
   - Check: `ls J:\codette-training-lab\bartowski\Meta-Llama-3.1-8B-Instruct-GGUF\*.gguf`
   - Check: `ls J:\codette-training-lab\adapters\*.gguf`

2. **Agents show ✗ TEMPLATE**
   - Check logs for "CodetteOrchestrator not available:"
   - Check Python path includes inference directory

3. **Synthesis is still template-like**
   - Check sample text doesn't contain "{concept}"
   - Check if error logs show "falling back to templates"

4. **Correctness doesn't improve**
   - Adapters may be undertrained
   - System prompts may need refinement
   - Debate mechanism itself may be limiting factor

## Success Criteria ✅

All of these should be true:
1. Orchestrator loads successfully
2. All agents show ✓ LLM mode
3. Phase 6 synthesis is longer than Phase 1-5
4. First question synthesis is specific and domain-aware
5. Correctness improves from Phase 1-5 to Phase 6

If all 5 are true → **Mission accomplished!** 🚀
