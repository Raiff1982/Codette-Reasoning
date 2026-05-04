"""
Synthesis Engine v3.0 -- Adaptive Answer Placement + Spectral Trust Gating
==========================================================================

Phase 7.1 upgrade implementing three interlocking mechanisms:

1. Newtonian-First Gating (Directness Fix)
   Low-tension queries (epsilon < 0.35) get the verdict first, metacognitive
   trace last.  Eliminates the 200-token preamble problem on factual queries.
   Benchmark target: Directness 55% → >95%.

2. Dynamic Attractor Routing
   Three cognitive attractors based on epsilon:
     Fact      (eps < 0.35):  "Water" -- answer takes the shape of the question immediately
     Synthesis (0.35–0.7):  Balanced narrative with named perspectives
     Discovery (eps > 0.7):   "Full Ocean" -- productive tension shown, debate foregrounded

3. Spectral Trust Gating (text analogue of TwinFrequencyTrust)
   Monitors whether the generated response resonates with Codette's identity
   anchors (epistemic precision, multi-perspective depth, absence of generic
   assistant drift).  Flags identity erosion before the user sees it.

Integration:
   Called from forge_engine.py after the base synthesis step and after the
   epistemic report is computed (so real epsilon is available).  Falls back
   gracefully to the original synthesis on any exception.

Original design: Jonathan Harrison (Raiff1982/Codette-Reasoning)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Any, Optional


# ── Attractor thresholds ──────────────────────────────────────────────────────

ATTRACTOR_FACT      = 0.35   # eps below this → Fact attractor (Newtonian-First)
ATTRACTOR_DISCOVERY = 0.70   # eps above this → Discovery attractor (full debate)

# ── Identity anchor patterns ─────────────────────────────────────────────────
# Phrases that signal Codette's epistemic voice (positive resonance)
_IDENTITY_POSITIVE = re.compile(
    r"\b(however|suggests|reveals|indicates|implies|tension|perspective|"
    r"synthesis|epistemic|coherence|converge|diverge|uncertainty|framework|"
    r"tradeoff|nuance|analysis|evidence|constraint|principle|reasoning)\b",
    re.IGNORECASE,
)

# Phrases that signal generic assistant drift (negative resonance)
_IDENTITY_NEGATIVE = re.compile(
    r"\b(certainly!|of course!|great question|as an ai|i'm just|i cannot help|"
    r"i apologize for|happy to help|i'd be happy|absolutely!|sure thing|"
    r"no problem|feel free to ask)\b",
    re.IGNORECASE,
)


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class EnhancedCognitiveTrace:
    """Runtime trace emitted by SynthesisEngineV3 for logging and cocoon metadata."""
    epsilon: float
    gamma: float
    direct_mode: bool
    spectral_trust: float
    active_attractor: str  # "Fact" | "Synthesis" | "Discovery"

    def to_dict(self) -> dict:
        return {
            "epsilon":          self.epsilon,
            "gamma":            self.gamma,
            "direct_mode":      self.direct_mode,
            "spectral_trust":   round(self.spectral_trust, 4),
            "active_attractor": self.active_attractor,
        }


# ── Engine ────────────────────────────────────────────────────────────────────

class SynthesisEngineV3:
    """
    Adaptive Answer Placement engine.

    Wraps (or replaces) the output of the base synthesis step with
    attractor-appropriate formatting and a spectral trust check.
    """

    def __init__(self, identity_anchor: str = "Raiff1982/Jonathan Harrison"):
        # "Word and Name" -- the identity reference point for trust scoring
        self.identity_anchor = identity_anchor

    # ── Public API ────────────────────────────────────────────────────────────

    def synthesize_adaptive(
        self,
        concept: str,
        analyses: Dict[str, str],
        epsilon: float,
        gamma: float,
        base_synthesis: str = "",
        trust_engine: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Apply Adaptive Answer Placement to an already-synthesized response.

        Args:
            concept:        The original user query.
            analyses:       Per-perspective outputs {name: text}.
            epsilon:        Epistemic tension magnitude (0–1).
            gamma:          Ensemble coherence (0–1).
            base_synthesis: The existing synthesis text to reformat.
                            If empty, builds from analyses directly.
            trust_engine:   Optional -- any object with score_text_resonance(text)->dict.
                            Defaults to self (text-based resonance check).

        Returns:
            {"response": str, "trace": EnhancedCognitiveTrace}
        """
        attractor = self._classify_attractor(epsilon)
        is_direct = attractor == "Fact"

        # Use base synthesis if provided; otherwise derive from analyses
        core_text = base_synthesis.strip() if base_synthesis.strip() else self._derive_core(analyses)

        if is_direct:
            final_response = self._format_fact(core_text, epsilon)
        elif attractor == "Discovery":
            final_response = self._format_discovery(concept, core_text, analyses, epsilon)
        else:
            final_response = self._format_synthesis(concept, core_text, analyses, epsilon)

        # Spectral trust check
        _trust_engine = trust_engine if trust_engine is not None else self
        trust_score = 1.0
        try:
            trust_result = _trust_engine.score_text_resonance(final_response)
            trust_score = float(trust_result.get("trust", 1.0))
        except Exception:
            pass

        # If trust is low, append a sovereignty note rather than suppressing output
        if trust_score < 0.5:
            final_response += (
                "\n\n*[Sovereignty note: response resonance below threshold -- "
                "verify against identity anchors before accepting.]*"
            )

        return {
            "response": final_response,
            "trace": EnhancedCognitiveTrace(
                epsilon=epsilon,
                gamma=gamma,
                direct_mode=is_direct,
                spectral_trust=trust_score,
                active_attractor=attractor,
            ),
        }

    def score_text_resonance(self, text: str) -> Dict[str, float]:
        """
        Text-domain analogue of TwinFrequencyTrust.score_frame().

        Measures how strongly a response resonates with Codette's identity:
          - Epistemic precision vocabulary (positive signal)
          - Multi-perspective structure (positive signal)
          - Response depth / length (positive signal)
          - Generic assistant phrases (negative signal)

        Returns {"trust": float, "positive_hits": int, "negative_hits": int}
        """
        if not text or len(text) < 20:
            return {"trust": 0.3, "positive_hits": 0, "negative_hits": 0}

        positive_hits = len(_IDENTITY_POSITIVE.findall(text))
        negative_hits = len(_IDENTITY_NEGATIVE.findall(text))

        # Depth bonus: longer substantive responses score higher
        word_count = len(text.split())
        depth_bonus = min(0.2, word_count / 500)  # caps at 0.2 for ~500+ word responses

        # Base score: positive resonance minus negative drift
        raw = (positive_hits * 0.08) - (negative_hits * 0.25) + depth_bonus
        trust = max(0.0, min(1.0, 0.5 + raw))

        return {
            "trust": round(trust, 4),
            "positive_hits": positive_hits,
            "negative_hits": negative_hits,
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _classify_attractor(self, epsilon: float) -> str:
        if epsilon < ATTRACTOR_FACT:
            return "Fact"
        if epsilon > ATTRACTOR_DISCOVERY:
            return "Discovery"
        return "Synthesis"

    def _derive_core(self, analyses: Dict[str, str]) -> str:
        """Extract the Newtonian truth from analyses when no base synthesis exists."""
        newton_out = analyses.get("Newton") or analyses.get("newton") or ""
        if newton_out:
            sentences = re.split(r"(?<=[.!?])\s+", newton_out.strip())
            return sentences[0] if sentences else newton_out[:200]
        # Fallback: longest perspective output
        if analyses:
            best = max(analyses.values(), key=len)
            sentences = re.split(r"(?<=[.!?])\s+", best.strip())
            return sentences[0] if sentences else best[:200]
        return "A convergence of perspectives is required."

    def _format_fact(self, core_text: str, epsilon: float) -> str:
        """Fact attractor: verdict first, metacognitive trace last."""
        verdict = f"**{core_text}**" if not core_text.startswith("**") else core_text
        trace = (
            f"\n\n---\n*Metacognitive Trace: Low epistemic tension "
            f"(eps={epsilon:.2f}) -- Newtonian-First mode active. "
            f"Direct answer surfaced; multi-perspective debate suppressed.*"
        )
        return verdict + trace

    def _format_synthesis(
        self,
        concept: str,
        core_text: str,
        analyses: Dict[str, str],
        epsilon: float,
    ) -> str:
        """Synthesis attractor: narrative with perspectives, verdict at end."""
        lines = [f"Analysis of *'{concept}'* across perspectives:\n"]
        for name, text in analyses.items():
            snippet = text[:120].rstrip()
            if not snippet.endswith((".", "?", "!")):
                snippet += "..."
            lines.append(f"**{name}**: {snippet}")
        lines.append(f"\n**Synthesis:** {core_text}")
        tensions = self._named_tensions(analyses, epsilon)
        if tensions:
            lines.append(f"\n**Unresolved tension:** {tensions}")
        return "\n".join(lines)

    def _format_discovery(
        self,
        concept: str,
        core_text: str,
        analyses: Dict[str, str],
        epsilon: float,
    ) -> str:
        """Discovery attractor: high tension -- full debate foregrounded."""
        lines = [
            f"*'{concept}'* sits in high-tension epistemic space (eps={epsilon:.2f}). "
            f"The productive divergences between perspectives are the answer:\n"
        ]
        for name, text in analyses.items():
            lines.append(f"**{name}**: {text[:200].rstrip()}...")
        lines.append(f"\n**Convergence point:** {core_text}")
        tensions = self._named_tensions(analyses, epsilon)
        if tensions:
            lines.append(f"\n**⚠ Unresolved:** {tensions}")
        return "\n".join(lines)

    def _named_tensions(self, analyses: Dict[str, str], epsilon: float) -> str:
        if epsilon < 0.4:
            return ""
        names = list(analyses.keys())
        if len(names) >= 2:
            return f"{names[0]} vs {names[-1]}: competing analytical frames remain open."
        return ""
