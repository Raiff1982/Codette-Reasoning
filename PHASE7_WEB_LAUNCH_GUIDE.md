# Phase 7 Web Server Launch Guide

**Ready**: Phase 7 MVP is fully integrated into codette_server.py

## What Happens When You Launch

```bash
codette_web.bat
```

### Initialization Sequence (Expected Console Output)

```
============================================================
  Codette v2.0 - Phase 7 Executive Control Architecture
============================================================

  Starting with intelligent component routing...
  - Phase 7: Executive Controller (query routing)
  - Phase 6: ForgeEngine (semantic tension, specialization)
  - Phases 1-5: Core reasoning infrastructure

  Initializing:
    * CodetteOrchestrator with 8 domain LoRA adapters
    * ForgeEngine with Query Classifier
    * Executive Controller for intelligent routing

  Testing locally at: http://localhost:7860

============================================================

  Loading CodetteOrchestrator...
    ... (model loading, ~60-90 seconds first time)
  Orchestrator ready: [newton, davinci, empathy, philosophy, quantum, consciousness, multi_perspective, systems_architecture]

  Phase 6 bridge initialized
  Phase 7 Executive Controller initialized

  ✓ Server ready on http://localhost:7860
```

### What's Working

✅ Phase 7 Executive Controller auto-initialized
✅ Phase 6 ForgeEngine wrapped behind bridge
✅ All 8 domain-specific LoRA adapters loaded
✅ Intelligent routing ready

---

## Testing Phase 7 in the Web UI

Once the server is running, **try these queries** to observe Phase 7 routing:

### Test 1: SIMPLE Query (Should be ~150-200ms)
```
"What is the speed of light?"
```

**Expected in Response**:
- Fast response (150-200ms actual)
- `phase7_routing.components_activated` should show all FALSE
- `phase7_routing.reasoning`: "SIMPLE factual query - orchestrator direct inference"
- No debate, no semantic tension, no conflicts

---

### Test 2: MEDIUM Query (Should be ~900ms-1200ms)
```
"How does quantum mechanics relate to consciousness?"
```

**Expected in Response**:
- Moderate latency (~900ms-1200ms)
- `phase7_routing.components_activated`:
  - `debate`: TRUE (1 round)
  - `semantic_tension`: TRUE
  - `specialization_tracking`: TRUE
  - `preflight_predictor`: FALSE (skipped for MEDIUM)
- Some conflicts detected (10-20 range)

---

### Test 3: COMPLEX Query (Should be ~2000-3000ms)
```
"Can machines be truly conscious? And how should we ethically govern AI?"
```

**Expected in Response**:
- Longer processing (~2000-3000ms)
- `phase7_routing.components_activated`: ALL TRUE
- Full debate (3 rounds)
- Higher conflict count (20-40 range)
- Deep synthesis with multiple perspectives

---

## Interpreting Response Metadata

Every response will include a `phase7_routing` section:

```json
{
  "response": "The answer to your question...",

  "phase7_routing": {
    "query_complexity": "simple",

    "components_activated": {
      "debate": false,
      "semantic_tension": false,
      "specialization_tracking": false,
      "preflight_predictor": false,
      "memory_weighting": false,
      "gamma_monitoring": false,
      "synthesis": false
    },

    "reasoning": "SIMPLE factual query - avoided heavy machinery for speed",

    "latency_analysis": {
      "estimated_ms": 150,
      "actual_ms": 142,
      "savings_ms": 8
    },

    "correctness_estimate": 0.95,

    "compute_cost": {
      "estimated_units": 3,
      "unit_scale": "1=classifier, 50=full_machinery"
    },

    "metrics": {
      "conflicts_detected": 0,
      "gamma_coherence": 0.95
    }
  }
}
```

### Key Fields to Watch

| Field | Meaning |
|-------|---------|
| `query_complexity` | SIMPLE/MEDIUM/COMPLEX classification |
| `components_activated` | Which Phase 1-6 components ran |
| `actual_ms` vs `estimated_ms` | Real latency vs prediction |
| `conflicts_detected` | How many conflicts were found |
| `gamma_coherence` | Coherence score (higher = more consistent) |

---

## Success Criteria for Phase 7 Validation

- [ ] Server launches with "Phase 7 Executive Controller initialized"
- [ ] SIMPLE queries complete in 150-250ms (2-3x faster than MEDIUM)
- [ ] MEDIUM queries complete in 800-1200ms
- [ ] COMPLEX queries complete in 2000-3500ms (uses full machinery)
- [ ] Response metadata shows correct component activation
- [ ] `phase7_routing.reasoning` matches expected routing decision

---

## If Something Goes Wrong

**Problem**: Server doesn't mention Phase 7
- Check: Is "Phase 7 Executive Controller initialized" in console?
- If missing: ForgeEngine failed to load (check model files)

**Problem**: All queries treated as COMPLEX
- Check: QueryClassifier patterns in `reasoning_forge/query_classifier.py`
- Common issue: Regex patterns too broad

**Problem**: Latencies not improving
- Check: Is `phase7_routing.components_activated.debate` FALSE for SIMPLE?
- If debate=TRUE on simple queries: Classifier misclassifying

**Problem**: Response metadata missing phase7_routing
- Check: Is `phase7_used` set to TRUE in response?
- If FALSE: Bridge fallback happened (check console errors)

---

## Next Steps After Testing

### If Validation Successful (Expected Path)
1. ✅ Document actual latencies (compare to estimates)
2. ✅ Verify correctness not degraded on MEDIUM/COMPLEX
3. → Move to **Path B: Benchmarking** to quantify improvements

### If Issues Found
1. Document the specific problem
2. Check console logs for error messages
3. Fix and retest with `python run_phase7_demo.py` first

---

## Browser Tool UI Notes

The web interface will show:
- **Response** - The actual answer
- **Metadata** - Below response, includes phase7_routing
- **Latency** - Actual time taken (compare to estimated_ms)

Scroll down to see full phase7_routing metadata in JSON format.

---

## Ready to Launch?

```bash
codette_web.bat
```

Open browser to: **http://localhost:7860**

Test with one of the queries above and look for:
- ✅ Phase 7 routing metadata in response
- ✅ Latency improvements on SIMPLE queries
- ✅ Component activation matching query complexity

**Questions during testing?** Check the metadata for clues about routing decisions.
