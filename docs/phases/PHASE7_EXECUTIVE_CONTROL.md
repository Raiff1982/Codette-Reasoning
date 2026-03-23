# Phase 7: Executive Control Architecture

**Status**: MVP Implementation Complete ✅
**Date**: 2026-03-20
**Author**: Jonathan Harrison (Codette Framework)

## Overview

Phase 7 solves the "powerful brain without executive function" problem by adding intelligent routing of queries to optimal Phase 1-6 component combinations.

**Core Problem**: All queries activated the full machinery (debate, semantic tension, pre-flight prediction, etc.), wasting compute on simple factual questions and slowing down latency unnecessarily.

**Solution**: An Executive Controller that makes per-query routing decisions:
- **SIMPLE** queries (factual): Skip heavy machinery, direct answer (~150ms, 3 compute units)
- **MEDIUM** queries (conceptual): 1-round debate with selective components (~900ms, 25 units)
- **COMPLEX** queries (philosophical/multi-domain): Full 3-round debate with all Phase 1-6 components (~2500ms, 50+ units)

## Architecture

### Executive Controller (`reasoning_forge/executive_controller.py`)

**Core Class**: `ExecutiveController`

```python
decision = controller.route_query(query, complexity)
# Returns ComponentDecision with:
# - component_activation: dict of which Phase 1-6 components to enable
# - component_config: configuration for each component (e.g., debate_rounds: 1)
# - reasoning: explanation of why this routing was chosen
# - estimated_latency_ms, compute_cost: performance expectations
```

**Three Routing Paths**:

1. **SIMPLE Route** (QueryComplexity.SIMPLE)
   ```
   Components activated: None (direct answer)
   Debate: False
   Semantic Tension: False
   Pre-flight Prediction: False
   Expected latency: 150ms
   Expected correctness: 0.95
   Compute cost: 3 units
   ```

2. **MEDIUM Route** (QueryComplexity.MEDIUM)
   ```
   Components activated: Selective
   Debate: True (1 round)
   Semantic Tension: True
   Specialization Tracking: True
   Pre-flight Prediction: False (skipped)
   Memory Weighting: True
   Expected latency: 900ms
   Expected correctness: 0.80
   Compute cost: 25 units
   ```

3. **COMPLEX Route** (QueryComplexity.COMPLEX)
   ```
   Components activated: All Phase 1-6
   Debate: True (3 rounds)
   Semantic Tension: True
   Specialization Tracking: True
   Pre-flight Prediction: True
   Memory Weighting: True
   Gamma Monitoring: True
   Expected latency: 2500ms
   Expected correctness: 0.85
   Compute cost: 50+ units
   ```

### Integration Points

1. **CodetteForgeBridge** (`inference/codette_forge_bridge.py`)
   - Modified to import and initialize ExecutiveController
   - `_generate_with_phase6()` now calls `executive_controller.route_query()` before activation
   - SIMPLE queries now bypass ForgeEngine entirely, use direct orchestrator
   - Response metadata includes Phase 7 routing transparency

2. **Response Transparency**
   ```python
   response['phase7_routing'] = {
       'query_complexity': 'simple',
       'components_activated': {
           'debate': False,
           'semantic_tension': False,
           ...
       },
       'reasoning': "SIMPLE factual query - avoided heavy machinery for speed",
       'latency_analysis': {
           'estimated_ms': 150,
           'actual_ms': 148,
           'savings_ms': 2
       },
       'metrics': {
           'conflicts_detected': 0,
           'gamma_coherence': 0.95
       }
   }
   ```

## Key Features

### 1. Rule-Based Routing (MVP)
- Simple complexity heuristics determine optimal component combination
- No learning required; works immediately after Phase 6
- Predictable and transparent

### 2. Transparency Metadata
- Every response includes Phase 7 routing information
- Users/developers see WHAT ran and WHY
- Estimated vs actual latency comparison
- Compute cost accounting

### 3. Learning-Ready Architecture
- `ExecutiveControllerWithLearning` class for future adaptive routing
- Framework for weekly route optimization from historical data
- ε-greedy exploration vs exploitation strategy (optional)

### 4. Performance Estimates
- SIMPLE: ~2-3x faster than full machinery
- MEDIUM: ~50% of full machinery cost
- COMPLEX: Full capability when needed

## Test Coverage

**File**: `test_phase7_executive_controller.py`

All 10 tests passing:
- [OK] SIMPLE routing correct
- [OK] MEDIUM routing correct
- [OK] COMPLEX routing correct
- [OK] Transparency metadata correct
- [OK] Routing statistics tracked
- [OK] Component activation counts correct
- [OK] Learning router works
- [OK] Compute cost ranking correct
- [OK] Latency ranking correct
- [OK] ComponentDecision serializable

## Expected Impact

### Immediate (MVP Deployment)
- **Latency improvement**: 50-70% reduction on SIMPLE queries
- **Compute savings**: Estimated 40-50% for typical mixed workload
- **Quality preservation**: No degradation on COMPLEX queries
- **User experience**: Fast answers feel snappier; transparent routing builds trust

### Short-term (1-2 weeks)
- Real latency benchmarking against baseline
- Correctness evaluation to confirm no quality loss
- User feedback on response transparency

### Medium-term (Learning Version)
- Historical data analysis to refine routes further
- Per-domain routing optimization
- Meta-learning on component combinations

## Phase 7 vs. Phase 6

| Aspect | Phase 6 | Phase 7 |
|--------|---------|---------|
| **Scope** | Semantic tension, specialization, pre-flight | Component routing, executive control |
| **Problem Solved** | Over-activation on simple queries | System overhead, lack of decision intelligence |
| **Key Innovation** | Continuous conflict strength (ξ) | Intelligent component gating |
| **Complexity** | SIMPLE, MEDIUM, COMPLEX classification | Adaptive routing based on classification |
| **User Impact** | Better reasoning quality | Better latency + transparency |
| **Testing** | Phase 6 architectural validation | Phase 7 routing validation |

## Implementation Notes

### Current Status
- ✅ `executive_controller.py` created (357 lines)
- ✅ `codette_forge_bridge.py` modified for Phase 7 integration
- ✅ 10/10 tests passing
- ✅ Response metadata includes phase7_routing
- ⏳ Not yet tested against actual ForgeEngine (Phase 6 dependency)

### What's Different from Phase 6
Phase 6 enhanced *how we reason* (semantic tension, specialization).
Phase 7 enhances *whether we reason* (selective component activation).

This is governance of capabilities, not new capabilities.

### Design Principle: "Right-sized Reasoning"
- A factual question shouldn't trigger a 3-round philosophical debate
- A philosophical question shouldn't settle for direct lookup
- The system chooses the right tool for the right problem

## Future Directions

### Phase 7B: Learning Router
- Integrate with `living_memory` for historical analysis
- Weekly route optimization from correctness data
- Per-domain routing specialization

### Phase 8: Meta-Learning
- Learn which Phase 1-6 component combinations work best
- Automatic discovery of optimal component sets
- Federated learning across multiple Codette instances

### Phase 9+: Adaptive Governance
- Real-time adjustment of routing based on success/failure
- User preference learning ("I prefer fast over deep")
- Domain-specific routing strategies

## Files Modified/Created

### NEW
- `reasoning_forge/executive_controller.py` (357 lines)
- `test_phase7_executive_controller.py` (268 lines)

### MODIFIED
- `inference/codette_forge_bridge.py` (added Phase 7 integration, routing logic)

### UNCHANGED (but ready for Phase 7)
- All Phase 1-6 components (backward compatible)
- Query Classifier (used in routing decisions)
- ForgeEngine (components conditionally activated)

## Running Phase 7

### Automatic (Production)
Phase 7 auto-initializes in `codette_forge_bridge.py`:
```python
self.executive_controller = ExecutiveController(verbose=verbose)
# Automatically routes all queries through Phase 7
```

### Manual Testing
```bash
python test_phase7_executive_controller.py
# All 10 tests should pass
```

### Integration Validation
Phase 7 will be tested in conjunction with Phase 6:
1. Run existing Phase 6 benchmarks with Phase 7 enabled
2. Measure latency improvement (50-70% on SIMPLE expected)
3. Verify correctness preserved on MEDIUM/COMPLEX
4. Collect transparency metadata for analysis

## Next Steps

**Immediate (Next Session)**:
1. Test Phase 7 integration with actual ForgeEngine
2. Run Phase 6 evaluation suite with Phase 7 enabled
3. Measure real-world latency improvements
4. Deploy MVP to production (codette_web.bat)

**Short-term (1-2 weeks)**:
5. Create comprehensive latency benchmarks
6. Evaluate correctness preservation
7. Gather user feedback on transparency
8. Consider Phase 7B (learning router)

**Decision Point**:
- If MVP shows 50%+ compute savings with no quality loss → green light for learning version
- If users value transparency → expand Phase 7 metadata
- If domain-specific patterns emerge → build specialized routers

---

**Codette Principle**: "Be like water—individuality with responsibility"

Phase 7 brings discipline to Codette's awesome power. Powerful systems need governors.

