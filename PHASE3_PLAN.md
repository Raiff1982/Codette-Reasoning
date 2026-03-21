# Phase 3 Plan: Multi-Round Conflict Resolution Tracking

## Overview

**Goal**: Track how conflicts evolve across multiple debate rounds, measure resolution effectiveness, and build data for conflict-resolution strategies.

**Why Phase 3?**: Phase 1 detected conflicts (single round), Phase 2 learned which adapters performed best. Phase 3 closes the loop: measure if conflicts are *actually resolved* and which agents/strategies work best.

**Scope**: Medium (3-4 hours implementation + testing)

---

## Architecture: Multi-Round Conflict Tracking

### Current State (Phase 1-2)
- **Round 0**: Detect conflicts (70 detected)
- **Round 1**: Debate → Store conflicts in memory
- **End of cycle**: No tracking of conflict *evolution*

### Phase 3: Conflict Evolution Tracking
```
Round 0: Detect conflicts
    ├─ conflictA: Newton vs Quantum (emphasis, strength=0.15)
    ├─ conflictB: Philosophy vs DaVinci (framework, strength=0.12)
    └─ ...
    ↓
Round 1: Debate responses
    ├─ Did agents address conflictA? (addressing yes/no)
    ├─ Did positions soften? (softening yes/no)
    └─ Did conflict persist/worsen? (new_strength=0.10)
    ↓
Round 2: Follow-up analysis
    ├─ conflictA: NEW strength=0.08 (RESOLVED: 46% improvement)
    ├─ conflictB: NEW strength=0.14 (WORSENED: +17%)
    └─ ...
    ↓
Metrics per conflict:
    - resolution_path: [R0: 0.15, R1: 0.10, R2: 0.08] (improving)
    - resolution_rate: (0.15 - 0.08) / 0.15 = 46%
    - resolution_type: "soft_consensus" vs "hard_victory" vs "unresolved"
    - agent_contribution: Which agents moved positions?
```

---

## Implementation Components

### 1. ConflictEvolution Dataclass (NEW)

**Path**: `reasoning_forge/conflict_engine.py`

```python
@dataclass
class ConflictEvolution:
    """Track how a conflict changes across debate rounds."""

    original_conflict: Conflict        # From Round 0
    round_trajectories: Dict[int, Dict]  # {round: {strength, agents, addressing_score, softening_score}}
    resolution_rate: float             # (initial - final) / initial
    resolution_type: str               # "hard_victory" | "soft_consensus" | "stalled" | "worsened"
    resolved_in_round: int             # Which round did it resolve? (-1 if not resolved)
    adaptive_suggestions: List[str]    # "Try adapter X", "Reframe as Y", etc.

    def __post_init__(self):
        if not self.round_trajectories:
            self.round_trajectories = {}
        if self.resolution_rate == 0.0:
            self.resolution_rate = self._compute_resolution_rate()

    def _compute_resolution_rate(self) -> float:
        """Calculate (initial - final) / initial."""
        if not self.round_trajectories or 0 not in self.round_trajectories:
            return 0.0

        initial_strength = self.round_trajectories[0].get("strength", 0)
        final_strength = min(self.round_trajectories.values(),
                           key=lambda x: x.get("strength", float('inf'))).get("strength", 0)

        if initial_strength == 0:
            return 0.0

        return (initial_strength - final_strength) / initial_strength
```

### 2. ConflictTracker Class (NEW)

**Path**: `reasoning_forge/conflict_engine.py` (add to existing file)

```python
class ConflictTracker:
    """Track conflicts across multiple debate rounds."""

    def __init__(self, conflict_engine):
        self.conflict_engine = conflict_engine
        self.evolution_data: Dict[str, ConflictEvolution] = {}  # key: conflict anchor

    def track_round(self, round_num: int, agent_analyses: Dict[str, str],
                   previous_round_conflicts: List[Conflict]) -> List[ConflictEvolution]:
        """
        Track how previous round's conflicts evolved in this round.

        Returns:
            List of ConflictEvolution objects with updated metrics
        """
        # Detect conflicts in current round
        current_round_conflicts = self.conflict_engine.detect_conflicts(agent_analyses)

        evolutions = []
        for prev_conflict in previous_round_conflicts:
            # Find matching conflict in current round (by agents and claim overlap)
            matches = self._find_matching_conflicts(prev_conflict, current_round_conflicts)

            if matches:
                # Conflict still exists (may have changed strength)
                current_conflict = matches[0]
                evolution = self._compute_evolution(
                    prev_conflict, current_conflict, round_num, agent_analyses
                )
            else:
                # Conflict resolved (no longer detected)
                evolution = self._mark_resolved(prev_conflict, round_num)

            evolutions.append(evolution)

        # Track any new conflicts introduced this round
        new_conflicts = self._find_new_conflicts(previous_round_conflicts, current_round_conflicts)
        for new_conflict in new_conflicts:
            evolution = ConflictEvolution(
                original_conflict=new_conflict,
                round_trajectories={round_num: {
                    "strength": new_conflict.conflict_strength,
                    "addressing_score": 0.0,
                    "softening_score": 0.0,
                }},
                resolution_rate=0.0,
                resolution_type="new",
                resolved_in_round=-1,
            )
            evolutions.append(evolution)

        return evolutions

    def _find_matching_conflicts(self, conflict: Conflict,
                                candidates: List[Conflict]) -> List[Conflict]:
        """Find conflicts from previous round that likely match current round conflicts."""
        matches = []
        for candidate in candidates:
            # Match if same agent pair + similar claims
            if ((conflict.agent_a == candidate.agent_a and conflict.agent_b == candidate.agent_b) or
                (conflict.agent_a == candidate.agent_b and conflict.agent_b == candidate.agent_a)):

                # Compute claim similarity
                overlap = self.conflict_engine._compute_semantic_overlap(
                    conflict.claim_a, candidate.claim_a
                )
                if overlap > 0.5:  # Threshold for "same conflict"
                    matches.append(candidate)

        return matches

    def _compute_evolution(self, prev_conflict: Conflict, current_conflict: Conflict,
                          round_num: int, agent_analyses: Dict[str, str]) -> ConflictEvolution:
        """Compute how conflict evolved."""
        # Check if agents addressed each other's claims
        addressing_a = self.conflict_engine._is_claim_addressed(
            prev_conflict.claim_b, agent_analyses.get(current_conflict.agent_a, "")
        )
        addressing_b = self.conflict_engine._is_claim_addressed(
            prev_conflict.claim_a, agent_analyses.get(current_conflict.agent_b, "")
        )
        addressing_score = (addressing_a + addressing_b) / 2.0

        # Check if agents softened positions
        softening_a = self.conflict_engine._is_claim_softened(
            prev_conflict.claim_a, agent_analyses.get(current_conflict.agent_a, "")
        )
        softening_b = self.conflict_engine._is_claim_softened(
            prev_conflict.claim_b, agent_analyses.get(current_conflict.agent_b, "")
        )
        softening_score = (softening_a + softening_b) / 2.0

        # Determine resolution type
        strength_delta = prev_conflict.conflict_strength - current_conflict.conflict_strength
        if strength_delta > prev_conflict.conflict_strength * 0.5:
            resolution_type = "hard_victory"  # Strength dropped >50%
        elif strength_delta > 0.1:
            resolution_type = "soft_consensus"  # Strength decreased
        elif abs(strength_delta) < 0.05:
            resolution_type = "stalled"  # No change
        else:
            resolution_type = "worsened"  # Strength increased

        # Accumulate trajectory
        key = prev_conflict.agent_a + "_vs_" + prev_conflict.agent_b
        if key not in self.evolution_data:
            self.evolution_data[key] = ConflictEvolution(
                original_conflict=prev_conflict,
                round_trajectories={0: {
                    "strength": prev_conflict.conflict_strength,
                    "addressing_score": 0.0,
                    "softening_score": 0.0,
                }},
                resolution_rate=0.0,
                resolution_type="new",
                resolved_in_round=-1,
            )

        self.evolution_data[key].round_trajectories[round_num] = {
            "strength": current_conflict.conflict_strength,
            "addressing_score": addressing_score,
            "softening_score": softening_score,
            "agents": [current_conflict.agent_a, current_conflict.agent_b],
        }

        self.evolution_data[key].resolution_rate = self.evolution_data[key]._compute_resolution_rate()
        self.evolution_data[key].resolution_type = resolution_type

        return self.evolution_data[key]

    def _mark_resolved(self, conflict: Conflict, round_num: int) -> ConflictEvolution:
        """Mark a conflict as resolved (no longer appears in current round)."""
        key = conflict.agent_a + "_vs_" + conflict.agent_b
        if key not in self.evolution_data:
            self.evolution_data[key] = ConflictEvolution(
                original_conflict=conflict,
                round_trajectories={0: {
                    "strength": conflict.conflict_strength,
                    "addressing_score": 0.0,
                    "softening_score": 0.0,
                }},
                resolution_rate=1.0,
                resolution_type="resolved",
                resolved_in_round=round_num,
            )
            # Add final round with 0 strength
            self.evolution_data[key].round_trajectories[round_num] = {
                "strength": 0.0,
                "addressing_score": 1.0,
                "softening_score": 1.0,
            }

        return self.evolution_data[key]

    def _find_new_conflicts(self, previous: List[Conflict],
                           current: List[Conflict]) -> List[Conflict]:
        """Find conflicts that are new (not in previous round)."""
        prev_pairs = {(c.agent_a, c.agent_b) for c in previous}
        new = []
        for conflict in current:
            pair = (conflict.agent_a, conflict.agent_b)
            if pair not in prev_pairs:
                new.append(conflict)
        return new

    def get_summary(self) -> Dict:
        """Get summary of all conflict evolutions."""
        resolved = [e for e in self.evolution_data.values() if e.resolution_type == "resolved"]
        improving = [e for e in self.evolution_data.values() if e.resolution_type in ["hard_victory", "soft_consensus"]]
        worsened = [e for e in self.evolution_data.values() if e.resolution_type == "worsened"]

        avg_resolution = sum(e.resolution_rate for e in self.evolution_data.values()) / max(len(self.evolution_data), 1)

        return {
            "total_conflicts_tracked": len(self.evolution_data),
            "resolved": len(resolved),
            "improving": len(improving),
            "worsened": len(worsened),
            "avg_resolution_rate": avg_resolution,
            "resolution_types": {
                "resolved": len(resolved),
                "hard_victory": len([e for e in self.evolution_data.values() if e.resolution_type == "hard_victory"]),
                "soft_consensus": len([e for e in self.evolution_data.values() if e.resolution_type == "soft_consensus"]),
                "stalled": len([e for e in self.evolution_data.values() if e.resolution_type == "stalled"]),
                "worsened": len(worsened),
            },
        }
```

### 3. Integration into ForgeEngine (MODIFY)

**Path**: `reasoning_forge/forge_engine.py`

Modify `forge_with_debate()` to support multi-round tracking:

```python
def forge_with_debate(self, concept: str, debate_rounds: int = 2) -> dict:
    """Run forge with multi-turn agent debate and conflict tracking."""

    # ... existing code ...

    # NEW Phase 3: Initialize conflict tracker
    tracker = ConflictTracker(self.conflict_engine)

    # Round 0: Initial analyses + conflict detection
    conflicts_round_0 = self.conflict_engine.detect_conflicts(analyses)
    tracker.track_round(0, analyses, [])  # Track R0 conflicts

    # ... existing code ...

    # Multi-round debate loop (now can handle 2+ rounds)
    round_conflicts = conflicts_round_0

    for round_num in range(1, min(debate_rounds + 1, 4)):  # Cap at 3 rounds for now
        # ... agent debate code ...

        # NEW: Track conflicts for this round
        round_evolutions = tracker.track_round(round_num, analyses, round_conflicts)

        # Store evolution data
        debate_log.append({
            "round": round_num,
            "type": "debate",
            "conflict_evolutions": [
                {
                    "agents": f"{e.original_conflict.agent_a}_vs_{e.original_conflict.agent_b}",
                    "initial_strength": e.original_conflict.conflict_strength,
                    "current_strength": e.round_trajectories[round_num]["strength"],
                    "resolution_type": e.resolution_type,
                    "resolution_rate": e.resolution_rate,
                }
                for e in round_evolutions
            ],
        })

        # Update for next round
        round_conflicts = self.conflict_engine.detect_conflicts(analyses)

    # Return with Phase 3 metrics
    return {
        "messages": [...],
        "metadata": {
            ... # existing metadata ...
            "phase_3_metrics": tracker.get_summary(),
            "evolution_data": [
                {
                    "agents": key,
                    "resolved_in_round": e.resolved_in_round,
                    "resolution_rate": e.resolution_rate,
                    "trajectory": e.round_trajectories,
                }
                for key, e in tracker.evolution_data.items()
            ],
        }
    }
```

---

## Testing Plan

### Unit Tests
1. ConflictEvolution dataclass creation
2. ConflictTracker.track_round() with mock conflicts
3. Resolution rate computation
4. Evolution type classification (hard_victory vs soft_consensus, etc.)

### E2E Test
1. Run forge_with_debate() with 3 rounds
2. Verify conflicts tracked across all rounds
3. Check resolution_rate computed correctly
4. Validate evolved conflicts stored in memory

---

## Expected Outputs

**Per-Conflict Evolution**:
```
Conflict: Newton vs Quantum (emphasis)
  Round 0: strength = 0.15
  Round 1: strength = 0.12 (addressing=0.8, softening=0.6)  → soft_consensus
  Round 2: strength = 0.08 (addressing=0.9, softening=0.9)  → hard_victory

  Resolution: 46% (0.15→0.08)
  Type: hard_victory (>50% strength reduction)
  Resolved: ✓ Round 2
```

**Summary Metrics**:
```
Total conflicts tracked: 70
  Resolved: 18 (26%)
  Hard victory: 15 (21%)
  Soft consensus: 22 (31%)
  Stalled: 10 (14%)
  Worsened: 5 (7%)

Average resolution rate: 0.32 (32% improvement)
```

---

## Success Criteria

- [x] ConflictEvolution dataclass stores trajectory
- [x] ConflictTracker tracks conflicts across rounds
- [x] Resolution types classified correctly
- [x] Multi-round debate runs without errors
- [x] Evolution data stored in memory with performance metrics
- [x] Metrics returned in metadata
- [x] E2E test passes with 3-round debate

---

## Timeline

- **Part 1** (30 min): Implement ConflictEvolution + ConflictTracker
- **Part 2** (20 min): Integrate into ForgeEngine
- **Part 3** (20 min): Write unit + E2E tests
- **Part 4** (10 min): Update PHASE3_SUMMARY.md

**Total**: ~80 minutes

---

## What This Enables for Phase 4+

1. **Adaptive Conflict Resolution**: Choose debate strategy based on conflict type (hard contradictions need X, soft emphases need Y)
2. **Agent Specialization**: Identify which agents resolve which conflict types best
3. **Conflict Weighting**: Prioritize resolving high-impact conflicts first
4. **Predictive Resolution**: Train classifier to predict which conflicts will resolve in how many rounds
5. **Recursive Convergence Boost**: Feed evolution data back into RC+xi coherence/tension metrics
