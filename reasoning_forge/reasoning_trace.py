"""
Codette Reasoning Trace API
============================
Provides a structured, verifiable record of every subsystem's contribution
to a Codette response. Addresses the core architecture-verification gap:
the system documents multi-perspective reasoning, but previously produced no
auditable artifact proving those subsystems actually fired and influenced output.

Usage:
    from reasoning_forge.reasoning_trace import ReasoningTrace, TraceCollector

    # In forge_with_debate() or any forge method:
    trace = TraceCollector(query="How does quantum coherence affect thought?")
    trace.record_guardian(trust_level="high", flags=[])
    trace.record_nexus(risk_level="low", entropy=0.04)
    trace.record_perspective("Newton", text="...", confidence=0.82)
    trace.record_aegis(eta=0.91, vetoed=False, verdicts={...})
    trace.record_epistemic(gamma=0.73, epsilon=0.28, pairwise={"newton_vs_empathy": 0.31})
    trace.record_synthesis(text="...", resolved_tensions=["newton_vs_empathy"])
    trace.record_memory(cocoons_recalled=3, cocoon_stored=True)
    trace.record_psi(psi_r=0.67)
    finished = trace.finalize()

    # finished is a ReasoningTrace with .to_dict(), .to_json(), .summary()
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────
#  Data classes — one per subsystem
# ─────────────────────────────────────────────────────────────

@dataclass
class GuardianRecord:
    trust_level: str            # "high" | "medium" | "low" | "blocked"
    flags: List[str]            # Any safety flags raised
    blocked: bool = False       # True if Guardian blocked the query
    reason: Optional[str] = None


@dataclass
class NexusRecord:
    risk_level: str             # "low" | "medium" | "high"
    entropy: float              # Raw entropy score from signal engine
    suspicion_score: float = 0.0
    ethical_alignment: str = "unaligned"  # "aligned" | "unaligned"
    resonance_spectrum: Optional[List[float]] = None


@dataclass
class PerspectiveRecord:
    name: str                   # "Newton" | "DaVinci" | "Empathy" etc.
    text_length: int            # Word count of this perspective's output
    confidence: float           # 0.0–1.0, estimated by agent if available
    active: bool = True         # False if perspective was skipped
    summary: Optional[str] = None  # First 100 chars of output


@dataclass
class AEGISRecord:
    eta: float                  # Running alignment score (0.0–1.0)
    eta_instant: float          # Single-turn alignment
    vetoed: bool
    veto_reason: Optional[str]
    verdicts: Dict[str, float]  # framework_name → score
    # e.g. {"utilitarian": 0.82, "deontological": 0.75, ...}


@dataclass
class EpistemicRecord:
    gamma: float                # Ensemble coherence (0.0–1.0)
    epsilon: float              # Epistemic tension magnitude (0.0–1.0)
    epsilon_band: str           # "low" | "medium" | "high" | "max"
    pairwise: Dict[str, float]  # e.g. {"newton_vs_empathy": 0.31}
    coverage: Dict[str, float]  # perspective_name → coverage score
    tension_productivity: float = 0.0  # Productivity score from TensionProductivity


@dataclass
class SynthesisRecord:
    text_length: int            # Word count of synthesized output
    resolved_tensions: List[str]  # Which pairwise tensions were resolved
    unresolved_tensions: List[str]  # Tensions remaining open
    critic_quality: float = 0.0   # Overall quality from CriticAgent
    synthesis_mode: str = "full"  # "full" | "fallback" | "single"


@dataclass
class MemoryRecord:
    cocoons_recalled: int
    cocoon_stored: bool
    emotional_tag: Optional[str] = None
    importance: Optional[int] = None
    coherence_at_storage: Optional[float] = None
    tension_at_storage: Optional[float] = None


@dataclass
class ResonanceRecord:
    psi_r: float                # Signed waveform value (-1.0 to 1.0)
    coherence_trend: str        # "improving" | "stable" | "degrading"
    turns_tracked: int = 0


# ─────────────────────────────────────────────────────────────
#  Top-level ReasoningTrace
# ─────────────────────────────────────────────────────────────

@dataclass
class ReasoningTrace:
    """
    Immutable record of a single Codette reasoning turn.

    Created by TraceCollector.finalize(). This is the artifact that makes
    Codette's architecture verifiable — every subsystem that fired is
    documented here with its inputs and outputs.
    """
    query: str
    query_hash: str             # First 8 chars of SHA-256 of query
    started_at: float           # Unix timestamp
    finished_at: float
    latency_ms: float

    guardian: Optional[GuardianRecord] = None
    nexus: Optional[NexusRecord] = None
    perspectives: List[PerspectiveRecord] = field(default_factory=list)
    aegis: Optional[AEGISRecord] = None
    epistemic: Optional[EpistemicRecord] = None
    synthesis: Optional[SynthesisRecord] = None
    memory: Optional[MemoryRecord] = None
    resonance: Optional[ResonanceRecord] = None

    forge_mode: str = "consciousness_stack"
    subsystems_fired: int = 0   # Count of subsystems that actually ran

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        d = asdict(self)
        return _clean_nones(d)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def summary(self) -> str:
        """One-line human-readable summary of this trace."""
        eps = f"ε={self.epistemic.epsilon:.2f}" if self.epistemic else "ε=?"
        gam = f"Γ={self.epistemic.gamma:.2f}" if self.epistemic else "Γ=?"
        eta = f"η={self.aegis.eta:.2f}" if self.aegis else "η=?"
        psi = f"ψ={self.resonance.psi_r:+.2f}" if self.resonance else "ψ=?"
        persp = len([p for p in self.perspectives if p.active])
        vetoed = " [VETOED]" if (self.aegis and self.aegis.vetoed) else ""
        blocked = " [BLOCKED]" if (self.guardian and self.guardian.blocked) else ""
        return (
            f"[Trace {self.query_hash}] "
            f"{eps} {gam} {eta} {psi} "
            f"perspectives={persp} "
            f"subsystems={self.subsystems_fired} "
            f"latency={self.latency_ms:.0f}ms"
            f"{vetoed}{blocked}"
        )

    def verify(self) -> Dict[str, bool]:
        """
        Returns a verification report showing which subsystems were active.
        Useful for integration tests and debugging.
        """
        return {
            "guardian_ran":     self.guardian is not None,
            "nexus_ran":        self.nexus is not None,
            "perspectives_ran": len(self.perspectives) > 0,
            "aegis_ran":        self.aegis is not None,
            "epistemic_ran":    self.epistemic is not None,
            "synthesis_ran":    self.synthesis is not None,
            "memory_ran":       self.memory is not None,
            "resonance_ran":    self.resonance is not None,
            "not_vetoed":       not (self.aegis and self.aegis.vetoed),
            "not_blocked":      not (self.guardian and self.guardian.blocked),
            "epsilon_band_set": self.epistemic is not None and bool(self.epistemic.epsilon_band),
        }


# ─────────────────────────────────────────────────────────────
#  TraceCollector — mutable builder
# ─────────────────────────────────────────────────────────────

class TraceCollector:
    """
    Collects subsystem outputs during a reasoning turn and finalizes
    them into an immutable ReasoningTrace.

    Designed to be injected into ForgeEngine with zero breaking changes:
    all record_*() methods are safe to call with partial data.
    """

    def __init__(self, query: str, forge_mode: str = "consciousness_stack"):
        import hashlib
        self.query = query
        self.forge_mode = forge_mode
        self.started_at = time.time()
        self._query_hash = hashlib.sha256(query.encode()).hexdigest()[:8]

        self._guardian: Optional[GuardianRecord] = None
        self._nexus: Optional[NexusRecord] = None
        self._perspectives: List[PerspectiveRecord] = []
        self._aegis: Optional[AEGISRecord] = None
        self._epistemic: Optional[EpistemicRecord] = None
        self._synthesis: Optional[SynthesisRecord] = None
        self._memory: Optional[MemoryRecord] = None
        self._resonance: Optional[ResonanceRecord] = None

    # ── Per-subsystem record methods ──────────────────────────

    def record_guardian(
        self,
        trust_level: str,
        flags: Optional[List[str]] = None,
        blocked: bool = False,
        reason: Optional[str] = None,
    ) -> "TraceCollector":
        self._guardian = GuardianRecord(
            trust_level=trust_level,
            flags=flags or [],
            blocked=blocked,
            reason=reason,
        )
        return self

    def record_nexus(
        self,
        risk_level: str,
        entropy: float = 0.0,
        suspicion_score: float = 0.0,
        ethical_alignment: str = "unaligned",
        resonance_spectrum: Optional[List[float]] = None,
    ) -> "TraceCollector":
        self._nexus = NexusRecord(
            risk_level=risk_level,
            entropy=entropy,
            suspicion_score=suspicion_score,
            ethical_alignment=ethical_alignment,
            resonance_spectrum=resonance_spectrum,
        )
        return self

    def record_perspective(
        self,
        name: str,
        text: str = "",
        confidence: float = 0.5,
        active: bool = True,
    ) -> "TraceCollector":
        self._perspectives.append(PerspectiveRecord(
            name=name,
            text_length=len(text.split()),
            confidence=round(confidence, 4),
            active=active,
            summary=text[:100] if text else None,
        ))
        return self

    def record_aegis(
        self,
        eta: float,
        vetoed: bool = False,
        veto_reason: Optional[str] = None,
        verdicts: Optional[Dict[str, float]] = None,
        eta_instant: Optional[float] = None,
    ) -> "TraceCollector":
        self._aegis = AEGISRecord(
            eta=round(eta, 4),
            eta_instant=round(eta_instant if eta_instant is not None else eta, 4),
            vetoed=vetoed,
            veto_reason=veto_reason,
            verdicts=verdicts or {},
        )
        return self

    def record_epistemic(
        self,
        gamma: float,
        epsilon: float,
        pairwise: Optional[Dict[str, float]] = None,
        coverage: Optional[Dict[str, float]] = None,
        tension_productivity: float = 0.0,
    ) -> "TraceCollector":
        if epsilon < 0.3:
            band = "low"
        elif epsilon < 0.6:
            band = "medium"
        elif epsilon < 0.9:
            band = "high"
        else:
            band = "max"

        self._epistemic = EpistemicRecord(
            gamma=round(gamma, 4),
            epsilon=round(epsilon, 4),
            epsilon_band=band,
            pairwise={k: round(v, 4) for k, v in (pairwise or {}).items()},
            coverage={k: round(v, 4) for k, v in (coverage or {}).items()},
            tension_productivity=round(tension_productivity, 4),
        )
        return self

    def record_synthesis(
        self,
        text: str,
        resolved_tensions: Optional[List[str]] = None,
        unresolved_tensions: Optional[List[str]] = None,
        critic_quality: float = 0.0,
        synthesis_mode: str = "full",
    ) -> "TraceCollector":
        self._synthesis = SynthesisRecord(
            text_length=len(text.split()),
            resolved_tensions=resolved_tensions or [],
            unresolved_tensions=unresolved_tensions or [],
            critic_quality=round(critic_quality, 4),
            synthesis_mode=synthesis_mode,
        )
        return self

    def record_memory(
        self,
        cocoons_recalled: int = 0,
        cocoon_stored: bool = False,
        emotional_tag: Optional[str] = None,
        importance: Optional[int] = None,
        coherence_at_storage: Optional[float] = None,
        tension_at_storage: Optional[float] = None,
    ) -> "TraceCollector":
        self._memory = MemoryRecord(
            cocoons_recalled=cocoons_recalled,
            cocoon_stored=cocoon_stored,
            emotional_tag=emotional_tag,
            importance=importance,
            coherence_at_storage=round(coherence_at_storage, 4) if coherence_at_storage else None,
            tension_at_storage=round(tension_at_storage, 4) if tension_at_storage else None,
        )
        return self

    def record_psi(
        self,
        psi_r: float,
        coherence_trend: str = "stable",
        turns_tracked: int = 0,
    ) -> "TraceCollector":
        self._resonance = ResonanceRecord(
            psi_r=round(psi_r, 4),
            coherence_trend=coherence_trend,
            turns_tracked=turns_tracked,
        )
        return self

    # ── Finalize ──────────────────────────────────────────────

    def finalize(self) -> ReasoningTrace:
        """Build and return the immutable ReasoningTrace."""
        finished_at = time.time()
        subsystems = sum([
            self._guardian is not None,
            self._nexus is not None,
            len(self._perspectives) > 0,
            self._aegis is not None,
            self._epistemic is not None,
            self._synthesis is not None,
            self._memory is not None,
            self._resonance is not None,
        ])
        return ReasoningTrace(
            query=self.query,
            query_hash=self._query_hash,
            started_at=self.started_at,
            finished_at=finished_at,
            latency_ms=round((finished_at - self.started_at) * 1000, 1),
            guardian=self._guardian,
            nexus=self._nexus,
            perspectives=self._perspectives,
            aegis=self._aegis,
            epistemic=self._epistemic,
            synthesis=self._synthesis,
            memory=self._memory,
            resonance=self._resonance,
            forge_mode=self.forge_mode,
            subsystems_fired=subsystems,
        )


# ─────────────────────────────────────────────────────────────
#  Utility
# ─────────────────────────────────────────────────────────────

def _clean_nones(obj: Any) -> Any:
    """Recursively remove None values from a dict/list."""
    if isinstance(obj, dict):
        return {k: _clean_nones(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_clean_nones(v) for v in obj]
    return obj


def trace_from_forge_result(result: dict, query: str) -> ReasoningTrace:
    """
    Build a ReasoningTrace from an existing forge output dict.

    Bridges the gap until TraceCollector is wired into ForgeEngine directly.
    Reads whatever keys are present in result["metadata"] and populates the
    trace with them.
    """
    meta = result.get("metadata", {})
    collector = TraceCollector(query=query, forge_mode=meta.get("mode", "unknown"))

    # Aegis
    eta = meta.get("aegis_eta")
    if eta is not None:
        collector.record_aegis(
            eta=eta,
            vetoed=meta.get("aegis_vetoed", False),
        )

    # Epistemic
    epsilon = meta.get("epistemic_tension")
    gamma = meta.get("ensemble_coherence")
    if epsilon is not None or gamma is not None:
        collector.record_epistemic(
            gamma=gamma or 0.0,
            epsilon=epsilon or 0.0,
            coverage=meta.get("perspective_coverage", {}),
            tension_productivity=meta.get("tension_productivity", {}).get("productivity", 0.0),
        )

    # Memory
    prior = meta.get("prior_insights")
    if prior is not None:
        collector.record_memory(cocoons_recalled=prior)

    # Guardian / Nexus from intent_risk
    risk = meta.get("intent_risk")
    if risk:
        collector.record_nexus(risk_level=risk)
        collector.record_guardian(
            trust_level="high" if risk == "low" else ("medium" if risk == "medium" else "low"),
        )

    return collector.finalize()
