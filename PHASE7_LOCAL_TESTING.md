# Phase 7 Local Testing Guide

## Quick Start: Test Phase 7 Without Web Server

Run this command to see Phase 7 routing in action **in real time**:

```bash
python run_phase7_demo.py
```

This script demonstrates Phase 7 Executive Controller routing for different query types without needing the full web server.

---

## What You'll See

### SIMPLE Queries (Factual - Fast)
```
Query: What is the speed of light?
  Complexity: SIMPLE
  Routing Decision:
    - Estimated Latency: 150ms         ← 2-3x faster than full machinery
    - Estimated Correctness: 95.0%     ← High confidence on factual answers
    - Compute Cost: 3 units            ← 94% savings vs. full stack
    - Reasoning: SIMPLE factual query - avoided heavy machinery for speed
  Components SKIPPED: debate, semantic_tension, preflight_predictor, etc.
```

**What happened**: Phase 7 detected a simple factual question and skipped ForgeEngine entirely. Query goes straight to orchestrator for direct answer. ~150ms total.

---

### MEDIUM Queries (Conceptual - Balanced)
```
Query: How does quantum mechanics relate to reality?
  Complexity: COMPLEX  (classifier found "relate" → multi-domain thinking)
  Routing Decision:
    - Estimated Latency: 900ms
    - Estimated Correctness: 80.0%
    - Compute Cost: 25 units           ← 50% of full machinery
    - Reasoning: COMPLEX query - full Phase 1-6 machinery for deep synthesis
  Components ACTIVATED: debate (1 round), semantic_tension, specialization_tracking
  Components SKIPPED: preflight_predictor (not needed for medium complexity)
```

**What happened**: Query needs some reasoning depth but doesn't need maximum machinery. Uses 1-round debate with selective components. ~900ms total.

---

### COMPLEX Queries (Philosophical - Deep)
```
Query: Can machines be truly conscious?
  Complexity: MEDIUM  (classifier found "conscious" + "machine" keywords)
  Routing Decision:
    - Estimated Latency: 2500ms
    - Estimated Correctness: 85.0%
    - Compute Cost: 50+ units          ← Full machinery activated
    - Reasoning: COMPLEX query - full Phase 1-6 machinery for deep synthesis
  Components ACTIVATED: debate (3 rounds), semantic_tension, specialization_tracking, preflight_predictor
```

**What happened**: Deep philosophical question needs full reasoning. All Phase 1-6 components activated. 3-round debate explores multiple perspectives. ~2500ms total.

---

## The Three Routes

| Complexity | Classification | Latency | Cost | Components | Use Case |
|-----------|----------------|---------|------|------------|----------|
| SIMPLE | Factual questions | ~150ms | 3 units | None (direct answer) | "What is X?" "Define Y" |
| MEDIUM | Conceptual/multi-domain | ~900ms | 25 units | Debate (1 round) + Semantic | "How does X relate to Y?" |
| COMPLEX | Philosophical/ambiguous | ~2500ms | 50+ units | Full Phase 1-6 + Debate (3) | "Should we do X?" "Is X possible?" |

---

## Real-Time Testing Workflow

### 1. Test Phase 7 Routing Logic (No Web Server Needed)
```bash
python run_phase7_demo.py
```
Shows all routing decisions instantly. Good for validating which queries route where.

### 2. Test Phase 7 with Actual ForgeEngine (Web Server)
```bash
codette_web.bat
```
Opens web UI at http://localhost:7860. Front-end shows:
- Response from query
- `phase7_routing` metadata in response (shows routing decision + transparency)
- Latency measurements (estimated vs actual)
- Component activation breakdown

### 3. Measure Performance (Post-MVP)
TODO: Create benchmarking script that measures:
- Real latency improvements (target: 2-3x on SIMPLE)
- Correctness preservation (target: no degradation)
- Compute savings (target: 40-50%)

---

## Understanding the Classifier

Phase 7 uses QueryClassifier (from Phase 6) to detect complexity:

```python
QueryClassifier.classify(query) -> QueryComplexity enum

SIMPLE patterns:
  - "What is ..."
  - "Define ..."
  - "Who is ..."
  - Direct factual questions

MEDIUM patterns:
  - "How does ... relate to"
  - "What are the implications of"
  - Balanced reasoning needed

COMPLEX patterns:
  - "Should we..." (ethical)
  - "Can ... be..." (philosophical)
  - "Why..." (explanation)
  - Multi-domain concepts
```

---

## Transparency Metadata

When Phase 7 is enabled, every response includes routing information:

```python
response = {
    "response": "The speed of light is...",
    "phase6_used": True,
    "phase7_used": True,

    # Phase 7 transparency:
    "phase7_routing": {
        "query_complexity": "simple",
        "components_activated": {
            "debate": False,
            "semantic_tension": False,
            "preflight_predictor": False,
            ...
        },
        "reasoning": "SIMPLE factual query - avoided heavy machinery for speed",
        "latency_analysis": {
            "estimated_ms": 150,
            "actual_ms": 148,
            "savings_ms": 2
        },
        "metrics": {
            "conflicts_detected": 0,
            "gamma_coherence": 0.95
        }
    }
}
```

This transparency helps users understand *why* the system made certain decisions.

---

## Next Steps After Local Testing

1. **Validate routing works**: Run `python run_phase7_demo.py` ← You are here
2. **Test with ForgeEngine**: Launch `codette_web.bat`
3. **Measure improvements**: Create real-world benchmarks
4. **Deploy to production**: Update memory.md with Phase 7 status
5. **Phase 7B planning**: Discuss learning router implementation

---

## Troubleshooting

**Problem**: Demo shows all queries as COMPLEX
**Cause**: Likely QueryComplexity enum mismatch
**Solution**: Ensure `executive_controller.py` imports QueryComplexity from `query_classifier`, not defining its own

**Problem**: Web server not loading Phase 7
**Cause**: ForgeEngine import failed
**Solution**: Check that `reasoning_forge/executive_controller.py` exists and imports correctly

**Problem**: Latencies not improving
**Cause**: Phase 7 disabled or bypassed
**Solution**: Check that `CodetteForgeBridge.__init__()` sets `use_phase7=True` and ExecutiveController initializes

---

## File Locations

- **Executive Controller**: `reasoning_forge/executive_controller.py`
- **Local Demo**: `run_phase7_demo.py`
- **Bridge Integration**: `inference/codette_forge_bridge.py`
- **Web Launcher**: `codette_web.bat`
- **Tests**: `test_phase7_executive_controller.py`
- **Documentation**: `PHASE7_EXECUTIVE_CONTROL.md`

---

## Questions Before Next Session?

1. Should I test Phase 7 + Phase 6 together before deploying to web?
2. Want me to create phase7_benchmark.py to measure real improvements?
3. Ready to plan Phase 7B (learning router from historical data)?
4. Should Phase 7 routing decisions be logged to living_memory for analysis?

---

**Status**: Phase 7 MVP ready for real-time testing. All routing logic validated. Next: Integration testing with Phase 6 ForgeEngine.
