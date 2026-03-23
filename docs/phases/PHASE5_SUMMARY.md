# Phase 5: AdapterRouter Integration & Gamma Stabilization

**Status**: ✅ COMPLETE (Session 2026-03-19)
**Goal**: Prevent three failure modes (weight drift, false convergence, feedback lock-in) through reinforcement tuning and system health monitoring.

## Implementation Summary

### Part A: Reinforcement Coefficient Tuning (Steps 1-3)

**Created ReinforcementConfig dataclass** (`reasoning_forge/memory_weighting.py`):
```python
@dataclass
class ReinforcementConfig:
    boost_successful: float = 0.08        # Reward for resolution_rate > 40%
    penalize_failed: float = 0.08         # Penalty for "worsened" conflicts
    reward_soft_consensus: float = 0.03   # Partial reward for soft_consensus
```

**Key Features**:
- Tunable via `from_dict()` and `to_dict()` — load from config files
- Integrated into `MemoryWeighting.__init__()` (backward compatible, defaults match Phase 4)
- Updated `update_from_evolution()` to use configurable coefficients

**Wired into AdapterRouter** (`inference/adapter_router.py`):
- Added `memory_weighting` parameter to `__init__()`
- New `_apply_memory_boost()` method: modulates confidence [-50%, +50%] based on adapter weights
- Enhanced secondary adapter selection to prefer high-performing adapters
- New `explain_routing()` method: returns routing decision with memory context

**Updated CodetteOrchestrator** (`inference/codette_orchestrator.py`):
- Accepts `memory_weighting` parameter
- New `route_and_generate()` method: orchestrates routing + generation + logging
- New `log_routing_decision()` method: verbose routing context for observability

### Part B: Gamma Stabilization Field (Step 3.5A — CRITICAL)

**Created CoherenceFieldGamma class** (`reasoning_forge/coherence_field.py`, 380+ lines):

**Health Metrics** (`GammaHealthMetrics` dataclass):
- Tracks: conflict strength, perspective diversity, resolution rate, adapter weight variance, epistemic tension
- Computes **gamma (Γ)** score ∈ [0, 1] via weighted sum:
  ```
  Γ = 0.25×diversity + 0.25×tension_health + 0.25×(1-weight_variance) + 0.25×resolution_rate
  ```

**Health Zones**:
- **Γ < 0.4**: System collapses → inject diverse perspective (diversity_injection)
- **0.4 ≤ Γ ≤ 0.8**: Healthy/stable zone (maintain status quo)
- **Γ > 0.8**: Groupthink risk → force conflict pair (conflict_injection)

**Safety Mechanisms**:
- Runs alongside Phase 4 runaway detection (complementary, not redundant)
- Tracks health history and interventions
- Exports metrics for monitoring
- Graceful fallback if intervention fails

**Integrated into ForgeEngine** (`reasoning_forge/forge_engine.py`):
- Initialized in `__init__()` with `self.coherence_field = CoherenceFieldGamma()`
- Health monitoring added to debate loop after Phase 4 (after conflict evolution + runaway detection)
- Interventions executed when gamma out of bounds
- Gamma metrics exported in metadata:
  - `gamma_metrics`: health history (50-sample rolling window)
  - `gamma_interventions`: list of stabilization actions taken
  - `phase_5a_active`: flag indicating monitoring active

### Part C: Routing Metrics & Observability (Step 4)

**Created RoutingMetrics class** (`reasoning_forge/routing_metrics.py`, 250+ lines):

**Tracks Per-Adapter**:
- Selection count (primary vs secondary)
- Average confidence
- Memory boost hit rate (% of selections with boost applied)
- Average boost magnitude

**System-Level Metrics**:
- Total queries routed
- Strategy distribution (keyword, llm, hybrid, forced)
- Memory boost rate
- Top 5 adapters by selection frequency

**Observability Features**:
- `record_route()`: log individual routing decisions
- `get_adapter_stats()`: per-adapter performance
- `get_summary()`: comprehensive routing statistics
- `get_recent_routes()`: last N routes for debugging
- `create_record()`: factory method with boost magnitude calculation

### Part D: Configuration Management (Step 5)

**Created Phase 5 config file** (`configs/phase5_config.yaml`, 150+ lines):

Sections:
- **reinforcement**: Tuning coefficients for boost/penalize
- **adapter_router**: Memory weighting strategy (soft vs hard)
- **gamma_stabilization**: Health thresholds and intervention strategies
- **monitoring**: Observability settings (logging, metrics export)
- **memory**: Recency decay, weight bounds, update intervals
- **edge_cases**: Cold-start, missing adapters, memory load failures
- **development**: Testing mode, dry-run, replay mode

### Part E: Integration Tests (Step 6)

**Created test_phase5_e2e.py** (300+ lines, ALL PASSING):

**5 Test Functions**:
1. **test_reinforcement_config()**: ReinforcementConfig creation, from_dict, to_dict, partial configs
2. **test_adapter_router_with_memory()**: Router without memory, routing explanations
3. **test_gamma_health_monitoring()**: Health scoring, collapse/groupthink detection, interventions
4. **test_routing_metrics()**: Route recording, adapter stats, summary generation
5. **test_phase5_integration()**: All components working together (health + routing + metrics)

**Test Results**:
```
RESULTS: 5 passed, 0 failed
```

## Files Created/Modified

**NEW FILES**:
- `reasoning_forge/coherence_field.py` (380 lines)
- `reasoning_forge/routing_metrics.py` (250 lines)
- `configs/phase5_config.yaml` (150 lines)
- `test_phase5_e2e.py` (300 lines)
- `PHASE5_SUMMARY.md` (this file)

**MODIFIED FILES**:
- `reasoning_forge/memory_weighting.py` (+40 lines: ReinforcementConfig, config methods)
- `inference/adapter_router.py` (+80 lines: memory_weighting param, _apply_memory_boost, explain_routing)
- `inference/codette_orchestrator.py` (+100 lines: memory_weighting param, log_routing_decision, route_and_generate)
- `reasoning_forge/forge_engine.py` (+80 lines: CoherenceFieldGamma import/init, debate loop gamma monitoring, metadata export)

## Architecture

```
Complete Phase 5 Closed Loop:

Query
  ↓
[P5 AdapterRouter]
  - Routes via keyword/LLM
  - Tests memory_weighting for confidence boost
  - Returns RouteResult with confidence
  ↓
[RoutingMetrics] logs the decision
  ↓
[Agents generate via selected adapters]
  ↓
[P1-P3] Detect + track + evolve conflicts
  ↓
[P4] Self-correcting: update weights, dynamic reroute, runaway detection
  ↓
[P5A Gamma] Monitor health
  ├─ If Γ < 0.4: diversity_injection (inject unused adapter)
  ├─ If Γ > 0.8: conflict_injection (force debate pair)
  └─ Log intervention + metrics
  ↓
Synthesis + export metadata (phase_5a metrics included)
  ↓
[Memory learning] improves next query's routing
```

## Key Metrics Exposed

**Per-Response**:
- `adapter`: Selected primary adapter
- `confidence_before_boost`: Base keyword score
- `confidence_after_boost`: Final confidence (after memory boost)
- `memory_boost_applied`: Boolean flag

**Per-Debate**:
- `gamma_health`: {gamma, status, conflict_strength, perspective_diversity, weight_variance, intervention}
- `adapter_weights`: Current learned weights for all adapters
- `phase_5a_active`: Flag that stabilization is live

**Per-Session** (RoutingMetrics.get_summary()):
- `total_queries`: Total routed
- `avg_confidence`: Mean confidence across routes
- `top_adapters`: Most frequently selected
- `memory_boost_rate`: % routes with memory boost
- `adapter_stats`: Per-adapter breakdown (selections, boosts, coherence)

## Safety Guardrails

**Weight Bounds**: [0, 2.0] prevents unbounded amplification

**Soft Boost Strategy**:
- Confidence modulation [-50%, +50%], not full replacement
- Keyword routing remains primary signal, memory boost refine

**Recency Decay**:
- 7-day half-life prevents old patterns from dominating
- Recent successes count more

**Gamma Intervention Thresholds**:
- Collapse at Γ < 0.4 requires >25% diversity loss or >75% weight concentration
- Groupthink at Γ > 0.8 requires very high diversity but low tension

**Gradual Reinforcement**:
- Boost/penalize caps at ±0.08 per round (prevents oscillation)
- Soft consensus gets partial credit (±0.03) for incremental progress

## What This Prevents

1. **Weight Drift**: Gamma monitoring detects when weight variance spikes (monoculture forming), injects diversity
2. **False Convergence**: Low conflict doesn't guarantee correctness; Gamma checks if diversity also dropping
3. **Feedback Lock-in**: Early bad runs reinforce via memory; Gamma can override by forcing new perspectives

## What This Enables

- **Real-time Health Dashboards**: Monitor Γ, adapter weights, intervention history in real-time
- **Fine-tuning**: Adjust coefficients (boost=0.08 → 0.10) via config without code changes
- **Adaptive Stabilization**: System self-corrects when drifting toward pathological modes
- **Production Observability**: Every routing decision logged with context for debugging
- **A/B Testing**: Can compare different boost amounts or gamma thresholds

## Next Steps (Phase 6+)

Potential enhancements:
- **Emergent Specialization**: Observe which adapters naturally cluster when helping each other
- **Meta-Learning**: Learn which conflicts are "resolvable" vs "epistemic disagreements"
- **Federated Gamma**: Sync gamma health across multiple Codette agents (distributed monitoring)
- **Adversarial Conflict Injection**: Deliberately create productive tension for training robustness
