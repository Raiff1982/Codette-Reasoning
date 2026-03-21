# AdapterRouter Integration Guide: Memory-Weighted Routing

## Overview

This guide shows how to integrate Phase 2's MemoryWeighting into the actual AdapterRouter to enable adaptive adapter selection based on historical performance.

**Current State**: MemoryWeighting is built and wired into ForgeEngine, but not yet connected to AdapterRouter. This document bridges that gap.

---

## Architecture: Where MemoryWeighting Fits

```
Query
  ↓
AdapterRouter.route()
  ├─ [Current] Keyword matching → base_result = RouteResult(primary, secondary, confidence)
  └─ [Phase 2] Memory-weighted boost → boosted_confidence = base_confidence * (1 + weight_modifier)
  ↓
ForgeEngine.forge_with_debate(primary=primary_adapter, secondary=secondary_adapters)
  ↓
Agents generate analyses → Conflicts detected → Stored in memory
  ↓
Next Query: Adapters with high historical coherence get +50% confidence boost
```

---

## Integration Steps

### Step 1: Wire MemoryWeighting into AdapterRouter.__init__()

**File**: `inference/adapter_router.py` (lines ~50-80)

**Current Code**:
```python
class AdapterRouter:
    def __init__(self, adapter_registry):
        self.adapter_registry = adapter_registry
        self.keyword_index = {}
        # ... initialize other components ...
```

**Phase 2 Enhancement**:
```python
from reasoning_forge.memory_weighting import MemoryWeighting

class AdapterRouter:
    def __init__(self, adapter_registry, memory_weighting=None):
        self.adapter_registry = adapter_registry
        self.keyword_index = {}
        self.memory_weighting = memory_weighting  # NEW: optional memory weighting
        # ... initialize other components ...
```

**Usage**:
```python
# In codette_session.py or app initialization:
from reasoning_forge.living_memory import LivingMemoryKernel
from reasoning_forge.memory_weighting import MemoryWeighting
from inference.adapter_router import AdapterRouter

memory = LivingMemoryKernel(max_memories=100)
weighting = MemoryWeighting(memory)
router = AdapterRouter(adapter_registry, memory_weighting=weighting)
```

---

### Step 2: Modify AdapterRouter.route() for Memory-Weighted Boost

**File**: `inference/adapter_router.py` (lines ~200-250)

**Current Code**:
```python
def route(self, query: str) -> RouteResult:
    """Route query to appropriate adapters."""
    # Keyword matching
    scores = self._route_keyword(query)

    return RouteResult(
        primary=best_adapter,
        secondary=top_secondary,
        confidence=max_score
    )
```

**Phase 2 Enhancement - SOFT BOOST**:
```python
def route(self, query: str, use_memory_boost: bool = True) -> RouteResult:
    """Route query to appropriate adapters with optional memory weighting.

    Args:
        query: User query text
        use_memory_boost: If True, boost confidence based on historical performance

    Returns:
        RouteResult with primary, secondary adapters and confidence
    """
    # Step 1: Keyword-based routing (existing logic)
    base_result = self._route_keyword(query)

    # Step 2: Apply memory-weighted boost (Phase 2)
    if use_memory_boost and self.memory_weighting:
        boosted_conf = self.memory_weighting.get_boosted_confidence(
            base_result.primary,
            base_result.confidence
        )
        base_result.confidence = boosted_conf

        # Optional: Explain the boost for debugging
        if os.environ.get("DEBUG_ADAPTER_ROUTING"):
            explanation = self.memory_weighting.explain_weight(base_result.primary)
            print(f"[ROUTING] {base_result.primary}: "
                  f"base={base_result.confidence:.2f}, "
                  f"boosted={boosted_conf:.2f}, "
                  f"weight={explanation['final_weight']:.2f}")

    return base_result
```

**Advanced Option - STRICT MEMORY-ONLY** (optional, higher risk):
```python
def route(self, query: str, strategy: str = "keyword") -> RouteResult:
    """Route query with pluggable strategy.

    Args:
        query: User query text
        strategy: "keyword" (default), "memory_weighted", or "memory_only"

    Returns:
        RouteResult with primary, secondary adapters and confidence
    """
    if strategy == "memory_only" and self.memory_weighting:
        # Pure learning approach: ignore keywords
        weights = self.memory_weighting.compute_weights()
        if weights:
            primary = max(weights.keys(), key=lambda a: weights[a])
            return RouteResult(
                primary=primary,
                secondary=[],  # No secondary adapters in memory-only mode
                confidence=weights[primary] / 2.0  # Normalize [0, 1]
            )
        else:
            # Fallback to keyword if no memory yet
            return self._route_keyword(query)

    elif strategy == "memory_weighted":
        # Soft boost approach: keyword routing + memory confidence boost
        base_result = self._route_keyword(query)
        if self.memory_weighting:
            boosted_conf = self.memory_weighting.get_boosted_confidence(
                base_result.primary,
                base_result.confidence
            )
            base_result.confidence = boosted_conf
        return base_result

    else:  # strategy == "keyword"
        # Pure keyword routing (existing behavior)
        return self._route_keyword(query)
```

---

### Step 3: Pass MemoryWeighting Through Session/App

**File**: `inference/codette_session.py` (lines ~50-100)

**Current Code**:
```python
class CodetteSession:
    def __init__(self):
        self.memory_kernel = LivingMemoryKernel(max_memories=100)
        self.router = AdapterRouter(adapter_registry)
        self.forge = ForgeEngine()
```

**Phase 2 Enhancement**:
```python
from reasoning_forge.memory_weighting import MemoryWeighting

class CodetteSession:
    def __init__(self):
        self.memory_kernel = LivingMemoryKernel(max_memories=100)

        # NEW: Initialize memory weighting
        self.memory_weighting = MemoryWeighting(self.memory_kernel)

        # Wire into router
        self.router = AdapterRouter(
            adapter_registry,
            memory_weighting=self.memory_weighting
        )

        # Wire into forge (Phase 2)
        self.forge = ForgeEngine(
            living_memory=self.memory_kernel,
            enable_memory_weighting=True
        )

    def on_submit(self, query: str):
        """Process user query with memory-weighted routing."""
        # Route using memory weights
        route_result = self.router.route(query, use_memory_boost=True)

        # Run forge with memory enabled
        result = self.forge.forge_with_debate(query)

        # Conflicts automatically stored in memory
        response = result["metadata"]["synthesized"]

        return response
```

---

## Testing the Integration

### Unit Test: Memory Weighting + Router

```python
def test_memory_weighted_routing():
    """Test that memory weights modulate router confidence."""
    from reasoning_forge.living_memory import LivingMemoryKernel, MemoryCocoon
    from reasoning_forge.memory_weighting import MemoryWeighting
    from inference.adapter_router import AdapterRouter

    # Setup
    memory = LivingMemoryKernel()

    # Seed memory with Newton performance (high coherence)
    newton_cocoon = MemoryCocoon(
        title="Newton analysis",
        content="Analytical approach",
        adapter_used="newton",
        coherence=0.9,
        emotional_tag="neutral",
    )
    memory.store(newton_cocoon)

    # Create weighting + router
    weighting = MemoryWeighting(memory)
    router = AdapterRouter(adapter_registry, memory_weighting=weighting)

    # Test
    query = "Analyze this algorithm"
    result = router.route(query, use_memory_boost=True)

    # If Newton scored high before, its confidence should be boosted
    assert result.confidence > 0.5  # Baseline
    print(f"✓ Routing test passed: {result.primary} @ {result.confidence:.2f}")
```

### E2E Test: Full Loop

```python
def test_memory_learning_loop():
    """Test that conflicts → memory → weights → better future routing."""
    from reasoning_forge.forge_engine import ForgeEngine
    from reasoning_forge.living_memory import LivingMemoryKernel
    from reasoning_forge.memory_weighting import MemoryWeighting
    from inference.adapter_router import AdapterRouter

    # Run 1: Initial debate (no memory history)
    memory = LivingMemoryKernel()
    forge = ForgeEngine(living_memory=memory, enable_memory_weighting=True)

    result1 = forge.forge_with_debate("Compare speed vs clarity", debate_rounds=1)
    conflicts1 = result1["metadata"]["conflicts_round_0_count"]
    print(f"Run 1: {conflicts1} conflicts detected, stored in memory")

    # Run 2: Same query with memory history
    # Adapters that resolved conflicts should get boosted
    weighting = MemoryWeighting(memory)  # Now has history
    weights = weighting.get_all_weights()

    print(f"\nAdapter weights after learning:")
    for adapter, w_dict in weights.items():
        print(f"  {adapter}: weight={w_dict['weight']:.3f}, coherence={w_dict['coherence']:.3f}")

    # Router should now boost high-performing adapters
    router = AdapterRouter(adapter_registry, memory_weighting=weighting)
    route_result = router.route("Compare speed vs clarity", use_memory_boost=True)
    print(f"\nRouting decision: {route_result.primary} @ {route_result.confidence:.2f}")

    # Run debate again (should use boosted adapters)
    result2 = forge.forge_with_debate("Compare speed vs clarity", debate_rounds=1)
    conflicts2 = result2["metadata"]["conflicts_round_0_count"]

    # Measure improvement
    improvement = (conflicts1 - conflicts2) / max(conflicts1, 1)
    print(f"Run 2: {conflicts2} conflicts (improvement: {improvement:.1%})")
```

---

## Configuration: Tuning Parameters

**Memory Weighting Parameters** (in `MemoryWeighting`):

```python
# Update frequency (hours)
update_interval_hours = 1.0  # Recompute weights every hour

# Weight formula contributions
base_coherence_weight = 0.5    # Contribution from mean coherence
conflict_success_weight = 0.3  # Contribution from conflict resolution
recency_weight = 0.2           # Contribution from recency decay

# Recency decay half-life (hours)
recency_half_life_hours = 168  # 7 days

# Boost modulation
max_boost = 0.5                # ±50% confidence modification
```

**Router Integration Options**:

```python
# Memory boost enabled/disabled
router.route(query, use_memory_boost=True)   # Default: enabled
router.route(query, use_memory_boost=False)  # Keyword-only

# Strategy selection (advanced)
router.route(query, strategy="keyword")          # Pure keyword
router.route(query, strategy="memory_weighted")  # Soft boost (recommended)
router.route(query, strategy="memory_only")      # Pure learning (risky)
```

---

## Production Deployment Checklist

- [ ] Wire MemoryWeighting into AdapterRouter.__init__()
- [ ] Modify route() method with use_memory_boost parameter
- [ ] Update CodetteSession to initialize memory_weighting
- [ ] Pass memory_weighting through all routing calls
- [ ] Update app.py/Gradio interface to pass memory context
- [ ] Add unit test for memory-weighted routing
- [ ] Add E2E test for full learning loop
- [ ] Monitor: Log adapter weights after each debate cycle
- [ ] Tune: Adjust weight formula coefficients based on results
- [ ] Document: User-facing explanation of why adapters were selected

---

## Monitoring & Debugging

### Enable Debug Logging

```python
import os
import logging

# In app initialization:
if os.environ.get("DEBUG_ADAPTER_ROUTING"):
    logging.basicConfig(level=logging.DEBUG)

    # This will print weight explanations on each route call
```

### Query Adapter Weight History

```python
from reasoning_forge.memory_weighting import MemoryWeighting

# Get snapshot of adapter weights
weights = memory_weighting.get_all_weights()
for adapter, w_dict in weights.items():
    print(f"{adapter}: weight={w_dict['weight']:.3f}")

# Explain a specific adapter's weight
explanation = memory_weighting.explain_weight("newton")
print(explanation["explanation"])
# Output: "Adapter 'newton' has used 15 times with 0.8 avg coherence,
#          73% conflict resolution rate, and 0.95 recency score.
#          Final weight: 1.45 (range [0, 2.0])"
```

### Memory State

```python
# Check memory cocoon counts per adapter
for cocoon in memory.memories:
    if cocoon.emotional_tag == "tension":
        print(f"Conflict: {cocoon.adapter_used}, coherence={cocoon.coherence}")

# Get emotional profile
profile = memory.emotional_profile()
print(f"Memory profile: {profile}")  # {'tension': 25, 'neutral': 10, ...}
```

---

## Known Limitations & Future Work

1. **Adapter Naming**: Currently stores agent pairs (e.g., "Newton,Quantum"). For pure adapter routing, need to map to actual adapter names.

2. **Cold Start**: New adapters have neutral weights (1.0) until they accumulate history (~10-15 uses).

3. **Strict Mode Risk**: Memory-only routing (no keywords) can ignore important query context. Test thoroughly before production.

4. **Memory Pruning**: Automatic pruning at 100 memories may lose old patterns. Consider keeping high-importance conflicts longer.

5. **Next Phase**: Multi-round conflict resolution tracking would enable learning across multiple debate cycles, not just single-round.

---

## Summary

**To Enable Memory-Weighted Routing**:

1. Add `memory_weighting` parameter to AdapterRouter.__init__()
2. Modify route() to apply `get_boosted_confidence()` soft boost
3. Wire through CodetteSession / app initialization
4. Test with unit + E2E test suite
5. Monitor weights and tune formula if needed

**Recommended Approach**: Soft boost (preserve keyword intelligence) → can migrate to memory-only if results justify it.

**Expected Outcome**: Better adapter selection over time, converging to adapters that historically resolved more conflicts.
