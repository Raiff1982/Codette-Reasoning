"""
authored_state.py — Codette Cognitive Substrate Output
=======================================================

AuthoredState is the cognitive artifact produced entirely upstream of the
render layer.  The LLM never owns semantic authority — it can only express
an AuthoredState, not create one.

Design mirrors Aura's TCF/render separation:
  CognitionSubstrate → AuthoredState → RenderLayer → natural language

The LLM renderer receives a fully-authored payload and is constrained to
verbalization only.  It cannot mutate conclusions, add new claims, or
alter confidence values.

Original: Jonathan Harrison (Raiff1982/Codette-Reasoning)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PerspectiveEntry:
    """A single agent perspective on the query."""
    agent_name: str
    text: str                       # Raw analysis text
    confidence: float = 0.5         # Agent-level confidence
    domain: str = ""                # e.g. "scientific", "ethical", "creative"


@dataclass
class AuthoredState:
    """
    The complete cognitive output of the reasoning substrate.

    This object is the source of truth.  The render layer may only express
    what is encoded here — it adds no new semantic content.

    Fields
    ------
    query           : Original user query (verbatim)
    conclusion      : The substrate's best answer / synthesis
    evidence        : Ordered list of supporting evidence strings
    perspectives    : Agent name → PerspectiveEntry
    strategy        : Name of the reasoning strategy selected
    strategy_def    : Brief definition of the strategy
    confidence      : Overall authored confidence [0, 1]
    dominant_emotion: Emotional framing (maps to Codette adapter palette)
    cocoon_refs     : Cocoon IDs that contributed to this state
    constraints     : Render constraints e.g. ["max_words:150", "tone:calm"]
    metadata        : Arbitrary extras (adapter, epsilon, gamma, etc.)
    timestamp       : Unix time at substrate completion
    render_tier     : Which render surface should be used ("llm", "template", "fallback")
    """

    query: str
    conclusion: str
    evidence: List[str] = field(default_factory=list)
    perspectives: Dict[str, PerspectiveEntry] = field(default_factory=dict)
    strategy: str = "default"
    strategy_def: str = ""
    confidence: float = 0.5
    dominant_emotion: str = "curious"
    cocoon_refs: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    render_tier: str = "llm"          # "llm" | "template" | "fallback"

    # ── Derived helpers ────────────────────────────────────────────────────

    def perspective_summary(self) -> str:
        """Return a compact multi-perspective block for verbalization prompts."""
        if not self.perspectives:
            return ""
        parts = []
        for name, entry in self.perspectives.items():
            parts.append(f"{name}: {entry.text.strip()}")
        return "\n\n".join(parts)

    def evidence_block(self, max_items: int = 3) -> str:
        """Return evidence as a numbered block."""
        items = self.evidence[:max_items]
        if not items:
            return ""
        return "\n".join(f"{i+1}. {e}" for i, e in enumerate(items))

    def constraint_string(self) -> str:
        """Return constraints as a readable instruction string."""
        if not self.constraints:
            return ""
        return "; ".join(self.constraints)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dict (for cocoon storage / Supabase sync)."""
        return {
            "query":           self.query,
            "conclusion":      self.conclusion,
            "evidence":        self.evidence,
            "perspectives":    {k: {"agent": v.agent_name, "text": v.text,
                                    "confidence": v.confidence, "domain": v.domain}
                                for k, v in self.perspectives.items()},
            "strategy":        self.strategy,
            "strategy_def":    self.strategy_def,
            "confidence":      self.confidence,
            "dominant_emotion": self.dominant_emotion,
            "cocoon_refs":     self.cocoon_refs,
            "constraints":     self.constraints,
            "metadata":        self.metadata,
            "timestamp":       self.timestamp,
            "render_tier":     self.render_tier,
        }

    @classmethod
    def fallback(cls, query: str, reason: str = "") -> "AuthoredState":
        """Minimal fallback state when substrate processing fails."""
        return cls(
            query=query,
            conclusion="",
            confidence=0.0,
            render_tier="fallback",
            metadata={"fallback_reason": reason},
        )
