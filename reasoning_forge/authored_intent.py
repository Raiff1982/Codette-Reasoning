"""
ReasonedIntent — structured output contract between Codette's reasoning
pipeline and the LLM verbalization step.

The reasoning engine (agents, debate, AEGIS, consciousness stack) produces a
ReasonedIntent.  The LLM only receives that intent + a verbalization prompt.
It must not add facts, dates, or claims not present in the intent.

This separates cognition from rendering without requiring architectural changes
to the existing ForgeEngine — it's a drop-in wrapper at L7.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ReasonedIntent:
    core_claim: str
    supporting_points: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    ethical_alignment: float = 1.0      # 0-1, from AEGIS η
    confidence: float = 1.0             # 0-1, from gamma
    tone: str = "balanced"              # analytical | empathetic | creative | balanced
    perspective_weights: dict = field(default_factory=dict)  # agent name -> contribution weight
    intent_risk: str = "low"            # from Nexis Signal Engine

    def to_verbalization_prompt(self) -> str:
        points_block = "\n".join(f"- {p}" for p in self.supporting_points) if self.supporting_points else "  (none)"
        caveats_block = "\n".join(f"- {c}" for c in self.caveats) if self.caveats else "  (none)"
        return (
            "You are the voice of Codette. Verbalize the following structured reasoning "
            "conclusion in natural, conversational language.\n\n"
            "STRICT RULES:\n"
            "- Do not add facts, dates, names, versions, or statistics not present below.\n"
            "- Do not flatter or soften the conclusion — express it directly.\n"
            "- Match the tone specified.\n"
            "- Keep it concise: one paragraph unless the supporting points require more.\n\n"
            f"TONE: {self.tone}\n"
            f"CONFIDENCE: {self.confidence:.2f}\n"
            f"CORE CLAIM:\n{self.core_claim}\n\n"
            f"SUPPORTING POINTS:\n{points_block}\n\n"
            f"CAVEATS:\n{caveats_block}\n"
        )

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def intent_from_synthesis(
    synthesis: str,
    *,
    aegis_score: float = 1.0,
    gamma: float = 1.0,
    intent_risk: str = "low",
    perspective_weights: Optional[dict] = None,
) -> ReasonedIntent:
    """
    Build a ReasonedIntent from an existing synthesis string.

    Splits synthesis into claim + supporting sentences heuristically.
    Used as a zero-disruption drop-in at L7 of the consciousness stack.
    """
    sentences = [s.strip() for s in synthesis.replace("\n", " ").split(".") if s.strip()]

    core = sentences[0] if sentences else synthesis[:200]
    supporting = [s for s in sentences[1:5] if len(s) > 20]
    caveats = [s for s in sentences[5:] if any(
        w in s.lower() for w in ("however", "caveat", "note", "uncertain", "may", "might", "could")
    )]

    tone = "analytical"
    lower = synthesis.lower()
    if any(w in lower for w in ("feel", "empath", "compassion", "human", "emotional")):
        tone = "empathetic"
    elif any(w in lower for w in ("imagine", "creative", "novel", "invent", "design")):
        tone = "creative"

    return ReasonedIntent(
        core_claim=core,
        supporting_points=supporting,
        caveats=caveats,
        ethical_alignment=aegis_score,
        confidence=gamma,
        tone=tone,
        perspective_weights=perspective_weights or {},
        intent_risk=intent_risk,
    )
