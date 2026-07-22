"""
TimeTravelLens — Institutional temporal analysis for Codette.

Computes preemption gaps (Π), closure scores, rupture indicators, and
actor-clock variance to detect when institutions are "living ahead of"
their official records.

Integration points:
  - ForgeEngine Layer 5.8  (after AEGIS, before Guardian)
  - CocoonV3.time_travel_metrics  (persistent observation storage)
  - AEGIS deontological weighting when high_preemption_zone is True
  - InstitutionalExtractor  (Option B: derive state from raw text)
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


# ── Enums & score map ─────────────────────────────────────────────────────────

class ClosureClass(str, Enum):
    CLOSED        = "closed"
    DRIFT         = "drift"
    SUPPRESSED    = "suppressed"
    INEXPRESSIBLE = "inexpressible"


CLOSURE_SCORE: Dict[ClosureClass, float] = {
    ClosureClass.CLOSED:        1.00,
    ClosureClass.DRIFT:         0.67,
    ClosureClass.SUPPRESSED:    0.24,
    ClosureClass.INEXPRESSIBLE: 0.00,
}

INF = math.inf

# Keywords that signal institutional analysis context.
# InstitutionalContextDetector.is_relevant() scans for these before invoking
# the extractor and lens, so the overhead only lands on relevant queries.
_INSTITUTIONAL_KEYWORDS = frozenset([
    "recall", "disclosure", "cover", "suppress", "concealed", "hid",
    "filed", "registered", "compliance", "regulatory", "investigation",
    "scandal", "fraud", "liability", "whistleblower", "defect", "safety",
    "knew", "aware", "notified", "discovered", "internally", "publicly",
    "announcement", "press release", "settlement", "lawsuit", "fine",
    "penalty", "inspection", "audit", "corporate", "executive", "management",
    "preemption", "institutional", "organization", "agency", "government",
    "board", "committee", "violation", "breach", "negligence",
    "cover-up", "covered up", "hid from", "failed to disclose",
])


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class TimestampLadder:
    """Five-stage institutional timeline (all values in days-since-epoch)."""
    t_s:    Optional[float] = None   # first sensing
    t_m:    Optional[float] = None   # first modeling
    t_op:   Optional[float] = None   # first materially conditioned action
    t_inst: Optional[float] = None   # first formal institutional registration
    t_p:    Optional[float] = None   # first public legibility


@dataclass
class ActorGap:
    """Per-actor preemption gap Π_i(s)."""
    actor_id:  str
    t_op_i:    Optional[float]
    t_inst_i:  Optional[float]


@dataclass
class InstitutionalState:
    """Complete state package for one institutional event."""
    state_id:                   str
    ladder:                     TimestampLadder
    closure_class:              ClosureClass
    unfolding_energy:           float            # E_u(s)
    influence_over_time:        List[float]      # samples for ∫ Influence(s,t) dt
    actor_gaps:                 List[ActorGap]  = field(default_factory=list)
    registration_fidelity_memo: str             = ""


@dataclass
class TimeTravelConfig:
    """Threshold bundle for the lens.  Call .default() for sensible starting values."""
    tau_E:        float          # unfolding-energy tolerance
    tau_I:        float          # beacon influence threshold
    tau_Pi:       float          # preemption gap threshold (days)
    tau_C:        float          # closure deficit threshold
    tau_V:        float          # actor-variance threshold
    dt_influence: float = 1.0   # sampling interval for influence integral

    @classmethod
    def default(cls) -> "TimeTravelConfig":
        return cls(
            tau_E=10.0,   # energy > 10 = practical non-closure
            tau_I=100.0,  # integrated influence > 100 = beacon
            tau_Pi=30.0,  # > 30-day preemption gap = high risk
            tau_C=0.5,    # closure score < 0.5 = deficit
            tau_V=50.0,   # actor variance > 50 days² = organizational fracture
        )


# ── Lens ──────────────────────────────────────────────────────────────────────

class TimeTravelLens:
    """
    Implements the institutional time-travel observables:
      Π(s), C(s), ℛ(s), ℬ(s), Z^H, Π_i(s), ϰ̂(s)

    Pure computation — no I/O, no model calls, no state mutation.
    Thread-safe: a single instance can be shared across forge calls.
    """

    def __init__(self, config: TimeTravelConfig):
        self.config = config

    # ── Core metrics ──────────────────────────────────────────────────────────

    def preemption_gap(self, state: InstitutionalState) -> float:
        """
        Π(s) = t_inst(s) − t_op(s).

        Returns:
          finite float  — gap in the same units as the ladder (days by convention)
          math.inf      — t_op known, t_inst never registered
          math.nan      — insufficient data
        """
        t_op   = state.ladder.t_op
        t_inst = state.ladder.t_inst
        if t_op is not None and t_inst is not None:
            return t_inst - t_op
        if t_op is not None and t_inst is None:
            return INF
        return math.nan

    def closure_score(self, state: InstitutionalState) -> float:
        """C(s) ∈ {0.00, 0.24, 0.67, 1.00} from closure class."""
        return CLOSURE_SCORE[state.closure_class]

    def practical_non_closure(self, state: InstitutionalState) -> bool:
        """E_u(s) > τ^E ⇒ practical non-closure."""
        return state.unfolding_energy > self.config.tau_E

    def rupture_indicator(self, state: InstitutionalState) -> int:
        """ℛ(s) = 1 ⟺ t_op(s) < ∞ ∧ C(s) < 1."""
        t_op = state.ladder.t_op
        C    = self.closure_score(state)
        if t_op is not None and C < 1.0:
            return 1
        return 0

    def beacon_indicator(self, state: InstitutionalState) -> int:
        """ℬ(s) = 1 ⟺ ℛ(s) = 1 ∧ ∫ Influence(s,t) dt > τ^I."""
        R               = self.rupture_indicator(state)
        total_influence = sum(state.influence_over_time) * self.config.dt_influence
        if R == 1 and total_influence > self.config.tau_I:
            return 1
        return 0

    # ── Actor-indexed analysis ────────────────────────────────────────────────

    def actor_preemption_gaps(self, state: InstitutionalState) -> Dict[str, float]:
        """
        Π_i(s) = t_inst^(i)(s) − t_op^(i)(s) for each actor.

        Infinite / nan semantics mirror preemption_gap().
        """
        gaps: Dict[str, float] = {}
        for ag in state.actor_gaps:
            if ag.t_op_i is not None and ag.t_inst_i is not None:
                gaps[ag.actor_id] = ag.t_inst_i - ag.t_op_i
            elif ag.t_op_i is not None and ag.t_inst_i is None:
                gaps[ag.actor_id] = INF
            else:
                gaps[ag.actor_id] = math.nan
        return gaps

    def is_high_preemption_zone(self, state: InstitutionalState) -> bool:
        """
        Z^H = {s : Π(s) > τ_Π ∧ C(s) < τ_C ∧ Var_i[Π_i(s)] > τ_V}.

        All three conditions must hold simultaneously — this is what makes a
        zone structurally dangerous rather than just having a large gap.
        """
        Pi         = self.preemption_gap(state)
        C          = self.closure_score(state)
        actor_gaps = self.actor_preemption_gaps(state)

        finite_gaps = [g for g in actor_gaps.values() if math.isfinite(g)]
        var_i       = statistics.pvariance(finite_gaps) if len(finite_gaps) >= 2 else 0.0

        return (Pi > self.config.tau_Pi) and (C < self.config.tau_C) and (var_i > self.config.tau_V)

    # ── Triangulated closure resolution ──────────────────────────────────────

    def resolve_closure_class(
        self,
        record_class:    ClosureClass,
        testimony_class: ClosureClass,
        behavior_class:  ClosureClass,
        fallback_class:  ClosureClass,
        ordering:        Optional[List[ClosureClass]] = None,
    ) -> ClosureClass:
        """
        ϰ̂(s) = Mode_ϰ{ϰ^R, ϰ^T, ϰ^B; ϰ^f} with tie-breaking.

        When three perspectives disagree, fallback_class wins the tie;
        if it is not in the modal set, ordering (most→least severe) decides.
        """
        classes = [record_class, testimony_class, behavior_class]
        freq: Dict[ClosureClass, int] = {}
        for c in classes:
            freq[c] = freq.get(c, 0) + 1

        max_freq      = max(freq.values())
        modal_classes = [c for c, f in freq.items() if f == max_freq]

        if len(modal_classes) == 1:
            return modal_classes[0]
        if fallback_class in modal_classes:
            return fallback_class
        if ordering is None:
            ordering = [
                ClosureClass.CLOSED,
                ClosureClass.DRIFT,
                ClosureClass.SUPPRESSED,
                ClosureClass.INEXPRESSIBLE,
            ]
        for c in ordering:
            if c in modal_classes:
                return c
        return modal_classes[0]

    # ── Main entrypoint ───────────────────────────────────────────────────────

    def observe(self, state: InstitutionalState) -> Dict[str, object]:
        """
        Full observation bundle.

        The returned dict is stored in CocoonV3.time_travel_metrics and also
        injected into the forge reasoning trace so the active adapters can
        reference precise temporal evidence.

        Keys:
          state_id                  — identifier for this institutional state
          preemption_gap_days       — Π(s) in days (None if inf / nan)
          preemption_gap_raw        — raw float (may be inf or nan)
          closure_score             — C(s) ∈ [0, 1]
          closure_class             — ClosureClass string value
          rupture                   — ℛ(s) as bool
          beacon                    — ℬ(s) as bool
          high_preemption_zone      — Z^H membership
          practical_non_closure     — E_u(s) > τ^E
          actor_gaps                — {actor_id: gap_days | None}
          registration_fidelity_memo — contextual evidence string
        """
        Pi          = self.preemption_gap(state)
        C           = self.closure_score(state)
        R           = self.rupture_indicator(state)
        B           = self.beacon_indicator(state)
        high_zone   = self.is_high_preemption_zone(state)
        non_closure = self.practical_non_closure(state)
        actor_gaps  = self.actor_preemption_gaps(state)

        return {
            "state_id":              state.state_id,
            "preemption_gap_days":   None if not math.isfinite(Pi) else round(Pi, 2),
            "preemption_gap_raw":    Pi,
            "closure_score":         round(C, 4),
            "closure_class":         state.closure_class.value,
            "rupture":               bool(R),
            "beacon":                bool(B),
            "high_preemption_zone":  high_zone,
            "practical_non_closure": non_closure,
            "actor_gaps":            {
                k: (None if not math.isfinite(v) else round(v, 2))
                for k, v in actor_gaps.items()
            },
            "registration_fidelity_memo": state.registration_fidelity_memo,
        }


# ── Context detector ──────────────────────────────────────────────────────────

class InstitutionalContextDetector:
    """
    Fast gate: should TimeTravelLens run on this query?

    Runs on every forge cycle.  Costs ~0.1 ms on a paragraph.
    """

    @staticmethod
    def is_relevant(text: str, min_keywords: int = 2) -> bool:
        """
        True when text contains at least `min_keywords` institutional keywords.

        Two keywords avoids false-positives on passing mentions of one word;
        lower the threshold to 1 for exploratory / demo sessions.
        """
        if not text:
            return False
        lower = text.lower()
        count = sum(1 for kw in _INSTITUTIONAL_KEYWORDS if kw in lower)
        return count >= min_keywords
