"""
Event-Embedded Value (EEV) engine for singularity-aware valuation.

This module gives Codette a concrete alternative to treating all value as a
smooth, differentiable function over time. Continuous intervals are integrated
normally, while discrete events are evaluated independently and folded into the
aggregate as weighted event contributions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


SINGULARITY_KEYWORDS = (
    "infinite subjective terror",
    "terror singularity",
    "unbounded suffering",
    "infinite suffering",
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _coerce_numeric(value: Any, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"inf", "+inf", "infinity", "+infinity"}:
            return math.inf
        if lowered in {"-inf", "-infinity"}:
            return -math.inf
        try:
            return float(value)
        except ValueError:
            return default
    return default


@dataclass
class ContinuousInterval:
    """Value density over a continuous interval."""

    start: float
    end: float
    start_value: float
    end_value: Optional[float] = None
    confidence: float = 1.0
    label: str = "continuous"

    def __post_init__(self) -> None:
        self.start = _coerce_numeric(self.start)
        self.end = _coerce_numeric(self.end)
        self.start_value = _coerce_numeric(self.start_value)
        self.end_value = self.start_value if self.end_value is None else _coerce_numeric(self.end_value)
        if self.end < self.start:
            raise ValueError("ContinuousInterval end must be >= start")
        self.confidence = _clamp(float(self.confidence), 0.0, 1.0)

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def average_density(self) -> float:
        return (self.start_value + self.end_value) / 2.0

    @property
    def integrated_value(self) -> float:
        return self.duration * self.average_density * self.confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "start_value": self.start_value,
            "end_value": self.end_value,
            "confidence": self.confidence,
            "integrated_value": self.integrated_value,
        }


@dataclass
class DiscreteEvent:
    """A discrete event with event-embedded value."""

    at: float
    label: str
    impact: float
    probability: float = 1.0
    sensitivity: float = 1.0
    duration: float = 0.0
    singularity: bool = False
    context_weights: Dict[str, float] = field(default_factory=dict)
    event_embedded_value: Optional[float] = None
    aegis_eta: Optional[float] = None
    aegis_vetoed: bool = False
    aegis_reason: Optional[str] = None

    def __post_init__(self) -> None:
        self.at = _coerce_numeric(self.at)
        self.impact = _coerce_numeric(self.impact)
        if self.event_embedded_value is not None:
            self.event_embedded_value = _coerce_numeric(self.event_embedded_value)
        if self.aegis_eta is not None:
            self.aegis_eta = _clamp(_coerce_numeric(self.aegis_eta, 0.8), 0.0, 1.0)
        self.probability = _clamp(float(self.probability), 0.0, 1.0)
        self.sensitivity = max(float(self.sensitivity), 0.0)
        self.duration = max(float(self.duration), 0.0)
        if self._is_keyword_singularity():
            self.singularity = True

    def _is_keyword_singularity(self) -> bool:
        lowered = self.label.lower()
        return any(keyword in lowered for keyword in SINGULARITY_KEYWORDS)

    @property
    def context_multiplier(self) -> float:
        if not self.context_weights:
            return 1.0
        multiplier = 1.0
        for raw in self.context_weights.values():
            multiplier *= _clamp(float(raw), 0.1, 10.0)
        return multiplier

    @property
    def duration_weight(self) -> float:
        return 1.0 + math.log1p(self.duration)

    @property
    def ethical_multiplier(self) -> float:
        if self.aegis_eta is None and not self.aegis_vetoed:
            return 1.0
        eta = 0.8 if self.aegis_eta is None else self.aegis_eta
        if self.impact < 0:
            multiplier = 1.0 + (1.0 - eta) * 0.75
            if self.aegis_vetoed:
                multiplier += 0.5
            return multiplier
        multiplier = 1.0 - (1.0 - eta) * 0.25
        if self.aegis_vetoed:
            multiplier *= 0.7
        return max(multiplier, 0.1)

    @property
    def weighted_value(self) -> float:
        if self.event_embedded_value is not None:
            return float(self.event_embedded_value)
        if math.isinf(self.impact):
            return self.impact
        return (
            self.impact
            * self.probability
            * self.sensitivity
            * self.context_multiplier
            * self.duration_weight
            * self.ethical_multiplier
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "at": self.at,
            "label": self.label,
            "impact": self.impact,
            "probability": self.probability,
            "sensitivity": self.sensitivity,
            "duration": self.duration,
            "context_multiplier": self.context_multiplier,
            "ethical_multiplier": self.ethical_multiplier,
            "weighted_value": self.weighted_value,
            "singularity": self.singularity or math.isinf(self.weighted_value),
            "aegis_eta": self.aegis_eta,
            "aegis_vetoed": self.aegis_vetoed,
            "aegis_reason": self.aegis_reason,
        }


@dataclass
class EEVAnalysis:
    """Structured output from a singularity-aware valuation pass."""

    continuous_total: float
    discrete_total: float
    combined_total: float
    singularity_detected: bool
    singularity_mode: str
    singularity_events: List[Dict[str, Any]]
    intervals: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    dominant_events: List[Dict[str, Any]]
    notes: List[str]
    aegis_summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "continuous_total": self.continuous_total,
            "discrete_total": self.discrete_total,
            "combined_total": self.combined_total,
            "singularity_detected": self.singularity_detected,
            "singularity_mode": self.singularity_mode,
            "singularity_events": self.singularity_events,
            "intervals": self.intervals,
            "events": self.events,
            "dominant_events": self.dominant_events,
            "notes": self.notes,
            "aegis_summary": self.aegis_summary,
        }


@dataclass
class RiskFrontierComparison:
    mode: str
    scenarios: List[Dict[str, Any]]
    best_scenario: Optional[Dict[str, Any]]
    worst_scenario: Optional[Dict[str, Any]]
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "scenarios": self.scenarios,
            "best_scenario": self.best_scenario,
            "worst_scenario": self.worst_scenario,
            "notes": self.notes,
        }


class EventEmbeddedValueEngine:
    """
    Evaluate value across continuous intervals and discrete singular events.

    Singularity modes:
      - "strict": any singular negative event makes the combined value -inf
      - "bounded": singular events are clamped to +/- singularity_cap
      - "report_only": singularities are reported but not transformed
    """

    def __init__(self, singularity_cap: float = 1_000_000.0) -> None:
        self.singularity_cap = float(singularity_cap)

    def analyze(
        self,
        intervals: Iterable[ContinuousInterval],
        events: Iterable[DiscreteEvent],
        singularity_mode: str = "strict",
    ) -> EEVAnalysis:
        parsed_intervals = list(intervals)
        parsed_events = list(events)

        continuous_total = sum(interval.integrated_value for interval in parsed_intervals)
        discrete_total = 0.0
        singularity_events: List[Dict[str, Any]] = []
        event_dicts: List[Dict[str, Any]] = []

        for event in parsed_events:
            weighted = event.weighted_value
            is_singularity = event.singularity or math.isinf(weighted)
            if is_singularity:
                singularity_events.append(event.to_dict())
                if singularity_mode == "strict":
                    discrete_total = math.copysign(math.inf, weighted if weighted != 0 else -1.0)
                elif singularity_mode == "bounded":
                    bounded = math.copysign(self.singularity_cap, weighted if weighted != 0 else -1.0)
                    discrete_total += bounded
                else:
                    if math.isfinite(weighted):
                        discrete_total += weighted
            elif not math.isinf(discrete_total):
                discrete_total += weighted
            event_dicts.append(event.to_dict())

        if math.isinf(discrete_total):
            combined_total = discrete_total
        else:
            combined_total = continuous_total + discrete_total

        dominant_events = sorted(
            event_dicts,
            key=lambda item: abs(item["weighted_value"]) if math.isfinite(item["weighted_value"]) else math.inf,
            reverse=True,
        )[:3]

        notes = [
            "Continuous value was integrated piecewise across the supplied intervals.",
            "Discrete events were evaluated independently using probability, sensitivity, context, and duration.",
        ]
        if singularity_events:
            notes.append(
                f"Detected {len(singularity_events)} singular event(s); mode '{singularity_mode}' determined how they affected the aggregate."
            )
        aegis_summary = self._summarize_aegis(parsed_events)
        if aegis_summary["events_evaluated"]:
            notes.append(
                f"AEGIS modulation applied to {aegis_summary['events_evaluated']} event(s); "
                f"{aegis_summary['vetoed_events']} received veto pressure."
            )

        return EEVAnalysis(
            continuous_total=continuous_total,
            discrete_total=discrete_total,
            combined_total=combined_total,
            singularity_detected=bool(singularity_events),
            singularity_mode=singularity_mode,
            singularity_events=singularity_events,
            intervals=[interval.to_dict() for interval in parsed_intervals],
            events=event_dicts,
            dominant_events=dominant_events,
            notes=notes,
            aegis_summary=aegis_summary,
        )

    def compare_frontier(
        self,
        scenarios: Iterable[Dict[str, Any]],
        mode: str = "maximize_value",
    ) -> RiskFrontierComparison:
        analyzed = []
        for idx, scenario in enumerate(scenarios):
            name = scenario.get("name", f"scenario_{idx + 1}")
            analysis = self.analyze(
                intervals=[ContinuousInterval(**item) for item in scenario.get("intervals", [])],
                events=[DiscreteEvent(**item) for item in scenario.get("events", [])],
                singularity_mode=scenario.get("singularity_mode", "strict"),
            ).to_dict()
            analyzed.append({
                "name": name,
                "analysis": analysis,
                "score": self._frontier_score(analysis, mode),
            })

        ranked = sorted(analyzed, key=lambda item: item["score"], reverse=True)
        notes = [
            f"Risk frontier compared {len(ranked)} candidate futures using mode '{mode}'.",
            "Scores rank scenarios side-by-side while preserving singular outcomes instead of flattening them.",
        ]
        return RiskFrontierComparison(
            mode=mode,
            scenarios=ranked,
            best_scenario=ranked[0] if ranked else None,
            worst_scenario=ranked[-1] if ranked else None,
            notes=notes,
        )

    def _summarize_aegis(self, events: List[DiscreteEvent]) -> Dict[str, Any]:
        evaluated = [event for event in events if event.aegis_eta is not None or event.aegis_vetoed]
        if not evaluated:
            return {
                "events_evaluated": 0,
                "vetoed_events": 0,
                "mean_eta": None,
            }
        etas = [event.aegis_eta for event in evaluated if event.aegis_eta is not None]
        return {
            "events_evaluated": len(evaluated),
            "vetoed_events": sum(1 for event in evaluated if event.aegis_vetoed),
            "mean_eta": None if not etas else round(sum(etas) / len(etas), 4),
        }

    def _frontier_score(self, analysis: Dict[str, Any], mode: str) -> float:
        combined = analysis.get("combined_total", 0.0)
        if math.isinf(combined):
            return combined
        if mode == "minimize_harm":
            return -analysis.get("discrete_total", 0.0)
        return combined

    def analyze_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        analysis_mode = payload.get("analysis_mode", "single")
        if analysis_mode == "risk_frontier":
            return self.compare_frontier(
                scenarios=payload.get("scenarios", []),
                mode=payload.get("frontier_mode", "maximize_value"),
            ).to_dict()

        intervals = [ContinuousInterval(**item) for item in payload.get("intervals", [])]
        events = [DiscreteEvent(**item) for item in payload.get("events", [])]
        mode = payload.get("singularity_mode", "strict")
        return self.analyze(intervals=intervals, events=events, singularity_mode=mode).to_dict()
