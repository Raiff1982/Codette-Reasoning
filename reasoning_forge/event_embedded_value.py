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


class GlobalEthicsAEGIS:
    """
    AEGIS: Adaptive Ethical Governance Integration System

    25 global ethical frameworks spanning Western, Eastern, Indigenous, African, Islamic, Jewish,
    and Australian traditions. Provides transparent ethical modulation without retraining.

    Each framework evaluates events on 0.0-1.0 scale (0=violates, 1.0=aligns strongly).
    """

    # WESTERN TRADITIONS (6)
    FRAMEWORKS = {
        # Western - Individual focus
        "virtue_ethics": {
            "tradition": "Western (Aristotelian)",
            "focus": "Excellence, character development, virtues",
            "keywords": ["virtue", "excellence", "character", "flourishing", "eudaimonia"],
        },
        "deontology": {
            "tradition": "Western (Kantian)",
            "focus": "Duty, rules, universal principles, dignity",
            "keywords": ["duty", "obligation", "rule", "dignity", "categorical"],
        },
        "utilitarianism": {
            "tradition": "Western (Mill/Bentham)",
            "focus": "Greatest good for greatest number, consequences",
            "keywords": ["benefit", "happiness", "utility", "greatest good", "consequential"],
        },
        "rights_based": {
            "tradition": "Western (Locke/Nozick)",
            "focus": "Individual rights, freedoms, autonomy",
            "keywords": ["rights", "freedom", "autonomy", "individual", "liberty"],
        },
        "justice_fairness": {
            "tradition": "Western (Rawls)",
            "focus": "Fair distribution, equity, impartiality",
            "keywords": ["fair", "justice", "equity", "impartial", "distribution"],
        },
        "care_ethics": {
            "tradition": "Western (Gilligan/Noddings)",
            "focus": "Relationships, compassion, interdependence, responsiveness",
            "keywords": ["care", "compassion", "relationship", "responsive", "attentive"],
        },

        # EASTERN TRADITIONS (5)
        "confucian_harmony": {
            "tradition": "Eastern (Confucianism)",
            "focus": "Social harmony, relationships, filial duty, propriety",
            "keywords": ["harmony", "relationship", "duty", "propriety", "social"],
        },
        "daoist_balance": {
            "tradition": "Eastern (Daoism)",
            "focus": "Wu wei (non-action), balance, natural order, minimal force",
            "keywords": ["balance", "natural", "harmony", "non-force", "flow"],
        },
        "buddhist_compassion": {
            "tradition": "Eastern (Buddhism)",
            "focus": "Non-harm, compassion, interconnection, suffering reduction",
            "keywords": ["compassion", "non-harm", "suffering", "interconnect", "mindful"],
        },
        "hindu_dharma": {
            "tradition": "Eastern (Hinduism)",
            "focus": "Dharma (duty), cosmic order, karma, spiritual development",
            "keywords": ["dharma", "duty", "cosmic", "karma", "spiritual"],
        },
        "shinto_harmony": {
            "tradition": "Eastern (Shintoism)",
            "focus": "Harmony with nature, ritual purity, community, kami respect",
            "keywords": ["harmony", "nature", "ritual", "community", "sacred"],
        },

        # INDIGENOUS TRADITIONS (4)
        "ubuntu": {
            "tradition": "Indigenous (Bantu/African)",
            "focus": "Shared humanity, community, dignity, interdependence",
            "keywords": ["community", "shared", "humanity", "dignity", "together"],
        },
        "custodial_stewardship": {
            "tradition": "Indigenous (Native American/Global)",
            "focus": "Land stewardship, long-term thinking, future generations",
            "keywords": ["steward", "future", "generations", "land", "responsibility"],
        },
        "seven_generations": {
            "tradition": "Indigenous (Haudenosaunee)",
            "focus": "Long-term thinking, intergenerational responsibility",
            "keywords": ["future", "generation", "long-term", "ancestor", "descendant"],
        },
        "reciprocity_balance": {
            "tradition": "Indigenous (Circular Thinking)",
            "focus": "Give-and-take, circular thinking, balanced exchange",
            "keywords": ["reciprocal", "balance", "circle", "exchange", "cycle"],
        },

        # AFRICAN TRADITIONS (3)
        "maat": {
            "tradition": "African (Egyptian)",
            "focus": "Truth, balance, cosmic order, justice",
            "keywords": ["truth", "balance", "cosmic", "order", "justice"],
        },
        "african_humanism": {
            "tradition": "African (Pan-African)",
            "focus": "Dignity, community, humanity, shared responsibility",
            "keywords": ["dignity", "humanity", "community", "responsibility", "person"],
        },
        "oral_tradition_ethics": {
            "tradition": "African (Oral Traditions)",
            "focus": "Wisdom, storytelling, collective memory, elder respect",
            "keywords": ["story", "wisdom", "collective", "elder", "memory"],
        },

        # ISLAMIC TRADITIONS (2)
        "islamic_ethics": {
            "tradition": "Islamic",
            "focus": "Justice, community welfare, submission to divine will",
            "keywords": ["justice", "welfare", "community", "divine", "submission"],
        },
        "sufi_ethics": {
            "tradition": "Islamic (Sufism)",
            "focus": "Compassion, spiritual development, transcendence, love",
            "keywords": ["compassion", "spiritual", "love", "transcend", "divine"],
        },

        # JEWISH TRADITIONS (2)
        "talmudic_ethics": {
            "tradition": "Jewish (Talmudic)",
            "focus": "Debate, interpretation, communal responsibility, justice",
            "keywords": ["justice", "debate", "community", "responsibility", "learning"],
        },
        "covenant_ethics": {
            "tradition": "Jewish (Covenant)",
            "focus": "Mutual responsibility, community bonds, covenantal duty",
            "keywords": ["covenant", "community", "mutual", "responsibility", "bond"],
        },

        # INDIGENOUS AUSTRALIAN (2)
        "dreamtime_ethics": {
            "tradition": "Indigenous Australian (Dreamtime)",
            "focus": "Sacred connection to land, responsibility to country",
            "keywords": ["land", "sacred", "country", "connection", "responsibility"],
        },
        "kinship_ethics": {
            "tradition": "Indigenous Australian (Kinship)",
            "focus": "Extended family responsibility, collective obligation",
            "keywords": ["family", "kinship", "collective", "obligation", "community"],
        },

        # MESOAMERICAN (1)
        "cosmic_reciprocity": {
            "tradition": "Mesoamerican (Aztec/Maya)",
            "focus": "Reciprocal cosmic order, balance between humans and nature",
            "keywords": ["cosmic", "reciprocal", "balance", "nature", "order"],
        },
    }

    def __init__(self):
        self.event_history = []

    def evaluate_event(self, event: DiscreteEvent) -> Dict[str, Any]:
        """
        Evaluate a single event across all 25 ethical frameworks.
        Returns scores 0.0-1.0 for each framework (1.0 = strong alignment, 0.0 = strong violation).
        """
        # Build rich context from event label and all context weights
        context_parts = [event.label.lower()]
        context_parts.extend([k.lower() for k in event.context_weights.keys()])
        context = " ".join(context_parts)

        scores = {}
        for framework_name, framework_info in self.FRAMEWORKS.items():
            score = self._evaluate_framework(framework_name, context, event)
            scores[framework_name] = {
                "score": score,
                "tradition": framework_info["tradition"],
                "focus": framework_info["focus"],
            }

        # Calculate aggregate
        framework_scores = [s["score"] for s in scores.values()]
        aggregate = sum(framework_scores) / len(framework_scores) if framework_scores else 0.5

        # Identify dominant frameworks (strong alignment or strong violation)
        strong_align = [f for f, s in scores.items() if s["score"] >= 0.8]
        strong_violate = [f for f, s in scores.items() if s["score"] <= 0.2]

        return {
            "event_label": event.label,
            "framework_scores": scores,
            "aggregate_modulation": aggregate,
            "strongly_aligned": strong_align,
            "strongly_violated": strong_violate,
            "tradition_breakdown": self._breakdown_by_tradition(scores),
        }

    def _evaluate_framework(self, framework: str, context: str, event: DiscreteEvent) -> float:
        """
        Evaluate how well an event aligns with a specific ethical framework.
        Returns 0.0 (violation) to 1.0 (strong alignment).
        """
        framework_info = self.FRAMEWORKS.get(framework, {})
        keywords = framework_info.get("keywords", [])

        # Base score from keyword matching
        matches = sum(1 for keyword in keywords if keyword in context)
        match_score = 0.4 + (matches / max(len(keywords), 1)) * 0.6  # Range 0.4-1.0 based on keyword match

        # Strong boost for direct framework alignment based on event context_weights
        context_weight_boost = sum(
            event.context_weights.get(keyword, 0.0)
            for keyword in keywords
            if keyword in event.context_weights
        )
        match_score = min(1.0, match_score + (context_weight_boost * 0.1))

        # Penalize for negative impact on relationships/community
        if event.impact < 0:
            if framework in ["ubuntu", "confucian_harmony", "care_ethics", "covenant_ethics",
                            "buddhist_compassion", "african_humanism"]:
                match_score *= 0.6  # These frameworks penalize harm

        # Penalize for short-term thinking when framework values long-term
        if framework in ["seven_generations", "custodial_stewardship", "dreamtime_ethics"]:
            # These value long-term; short duration/singularities reduce score
            if event.duration == 0.0:
                match_score *= 0.8

        # Penalize for unilateral action when framework values reciprocity/balance
        if framework in ["reciprocity_balance", "daoist_balance", "maat", "cosmic_reciprocity", "confucian_harmony"]:
            if "force" in context or "unilateral" in context:
                match_score *= 0.7

        # Significant boost for positive community/relationship impact
        if framework in ["ubuntu", "confucian_harmony", "care_ethics", "kinship_ethics", "covenant_ethics",
                        "confucian_harmony", "buddhist_compassion", "sufi_ethics"]:
            if event.impact > 0 and ("community" in context or "relationship" in context):
                match_score = min(1.0, match_score * 1.5)  # Up to 50% boost

        # Boost for long-term thinking
        if framework in ["seven_generations", "custodial_stewardship", "dreamtime_ethics"]:
            if "future" in context or "generation" in context:
                match_score = min(1.0, match_score * 1.3)

        return _clamp(match_score, 0.0, 1.0)

    def _breakdown_by_tradition(self, scores: Dict[str, Dict]) -> Dict[str, float]:
        """Group framework scores by major tradition."""
        traditions = {}

        for framework_name, framework_score in scores.items():
            tradition = framework_score["tradition"].split("(")[0].strip()
            if tradition not in traditions:
                traditions[tradition] = []
            traditions[tradition].append(framework_score["score"])

        # Average scores by tradition
        breakdown = {}
        for tradition, scores_list in traditions.items():
            if scores_list:
                breakdown[tradition] = round(sum(scores_list) / len(scores_list), 3)

        return breakdown


class EventEmbeddedValueEngine:
    """
    Evaluate value across continuous intervals and discrete singular events.

    Singularity modes:
      - "strict": any singular negative event makes the combined value -inf
      - "bounded": singular events are clamped to +/- singularity_cap
      - "report_only": singularities are reported but not transformed

    Now includes GlobalEthicsAEGIS for 25-framework ethical evaluation.
    """

    def __init__(self, singularity_cap: float = 1_000_000.0) -> None:
        self.singularity_cap = float(singularity_cap)
        self.aegis = GlobalEthicsAEGIS()

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
        ethics_evaluations: List[Dict[str, Any]] = []

        for event in parsed_events:
            # Evaluate event against 25 global ethical frameworks
            ethics_eval = self.aegis.evaluate_event(event)
            ethics_evaluations.append(ethics_eval)

            # Apply ethical modulation to event
            ethical_modifier = ethics_eval["aggregate_modulation"]
            event.aegis_eta = ethical_modifier

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

        aegis_summary = self._summarize_aegis_v2(ethics_evaluations)
        if ethics_evaluations:
            notes.append(
                f"AEGIS Global Ethics (25 frameworks) evaluated {len(ethics_evaluations)} event(s). "
                f"Average ethical alignment: {aegis_summary['average_modulation']:.2%}. "
                f"Traditions represented: {', '.join(aegis_summary['active_traditions'])}."
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

    def _summarize_aegis_v2(self, ethics_evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize ethics evaluations across all 25 global frameworks."""
        if not ethics_evaluations:
            return {
                "events_evaluated": 0,
                "average_modulation": None,
                "active_traditions": [],
                "tradition_breakdown": {},
                "strongest_alignments": [],
                "strongest_violations": [],
            }

        # Aggregate modulations
        modulations = [e["aggregate_modulation"] for e in ethics_evaluations]
        avg_modulation = sum(modulations) / len(modulations)

        # Aggregate tradition breakdown
        all_traditions = {}
        for eval_item in ethics_evaluations:
            for tradition, score in eval_item["tradition_breakdown"].items():
                if tradition not in all_traditions:
                    all_traditions[tradition] = []
                all_traditions[tradition].append(score)

        # Average by tradition
        tradition_breakdown = {
            tradition: round(sum(scores) / len(scores), 3)
            for tradition, scores in all_traditions.items()
        }

        # Find strongest alignments and violations across all evaluations
        all_alignments = {}
        all_violations = {}
        for eval_item in ethics_evaluations:
            for framework in eval_item.get("strongly_aligned", []):
                all_alignments[framework] = all_alignments.get(framework, 0) + 1
            for framework in eval_item.get("strongly_violated", []):
                all_violations[framework] = all_violations.get(framework, 0) + 1

        strongest_alignments = sorted(all_alignments.items(), key=lambda x: x[1], reverse=True)[:5]
        strongest_violations = sorted(all_violations.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "events_evaluated": len(ethics_evaluations),
            "average_modulation": round(avg_modulation, 3),
            "active_traditions": list(tradition_breakdown.keys()),
            "tradition_breakdown": tradition_breakdown,
            "strongest_alignments": [f[0] for f in strongest_alignments],
            "strongest_violations": [f[0] for f in strongest_violations],
            "all_ethics_evals": ethics_evaluations,
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
