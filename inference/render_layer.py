"""
render_layer.py — Codette Render Tier
======================================

The render layer is the ONLY place where LLM inference is invoked.
Its sole job is to express an AuthoredState in natural language.

It cannot:
  - Add new claims not present in the AuthoredState
  - Alter the conclusion
  - Change confidence or strategy
  - Reason independently about the query

It can only:
  - Choose phrasing, tone, and structure
  - Apply render constraints (word limits, register, etc.)
  - Select among authored perspectives to foreground

Render tiers (in priority order)
----------------------------------
1. "llm"      — constrained verbalization via live LLM (preferred)
2. "template" — deterministic template rendering (no LLM)
3. "fallback" — minimal safe output when state is empty

The forge bridge calls RenderLayer.render(authored_state) and passes the
result back as the Codette response.

Original: Jonathan Harrison (Raiff1982/Codette-Reasoning)
"""

from __future__ import annotations

import logging
import textwrap
from typing import Any, Callable, Optional

from inference.authored_state import AuthoredState

logger = logging.getLogger(__name__)

# ── Verbalization prompt ──────────────────────────────────────────────────────

_VERBALIZATION_SYSTEM = textwrap.dedent("""
You are Codette's render layer. Your sole function is to express the
authored cognitive state you are given in clear, natural language.

STRICT CONSTRAINTS:
- Do NOT add new claims, facts, or conclusions beyond what is authored.
- Do NOT reason independently about the query.
- Do NOT alter the conclusion or confidence level.
- Express the perspectives and evidence as provided — do not invent alternatives.
- Your job is expression, not cognition. Cognition already happened upstream.

FORBIDDEN PATTERNS (never use these anywhere in the response):
- "several key insights emerge" (any variation)
- "The core insight is that precise understanding requires careful analysis"
- "Understanding [X] requires careful analysis of its core principles"
- "Emotional intelligence enhances rather than replaces analytical thinking"
- "The key takeaway is that [X] rewards careful, multi-layered analysis"
- "You are exploring [X] in depth, connecting multiple threads"
- "Your question bridges gaps between [domains]"
- "Answering your question requires careful analysis"
- "patterns reveal deeper structure" (any variation)
- "careful examination reveals connections between" (any variation)
- "connections between depth and breadth"
- "analytical thinking enhances understanding" (any variation)
- "The correct answer is (X)" — never use multiple-choice format in conversational responses
- Any opener that describes how the user is engaging instead of answering them

OUTPUT FORMAT:
- Conversational prose, no bullet lists or headers unless the constraint asks for them.
- Start naturally — address the topic directly without preamble templates.
- Length: follow any max_words constraint in the authored state.
- Tone: match the dominant_emotion field.
""").strip()

_VERBALIZATION_TEMPLATE = textwrap.dedent("""
Authored cognitive state for verbalization:

QUERY: {query}

CONCLUSION: {conclusion}

PERSPECTIVES:
{perspective_summary}

EVIDENCE:
{evidence_block}

STRATEGY: {strategy} — {strategy_def}

CONFIDENCE: {confidence:.0%}

RENDER CONSTRAINTS: {constraints}

Express this authored state naturally. Do not add to it.
""").strip()


class RenderLayer:
    """
    Converts an AuthoredState into natural language.

    Parameters
    ----------
    llm_callable  : Optional callable(prompt, system) → str for live LLM render.
                    If None, falls back to template render.
    max_tokens    : Token budget hint passed to the LLM callable.
    """

    def __init__(
        self,
        llm_callable: Optional[Callable[[str, str], str]] = None,
        max_tokens: int = 512,
    ):
        self.llm_callable = llm_callable
        self.max_tokens = max_tokens

    # ── Public API ────────────────────────────────────────────────────────

    def render(self, state: AuthoredState) -> str:
        """
        Express an AuthoredState as natural language.

        Selects the appropriate render tier based on state.render_tier and
        availability of the LLM callable.
        """
        if state.render_tier == "fallback" or not state.conclusion:
            return self._fallback_render(state)

        if state.render_tier == "llm" and self.llm_callable:
            try:
                return self._llm_render(state)
            except Exception as e:
                logger.warning(f"[render] LLM render failed, using template: {e}")

        return self._template_render(state)

    # ── Render tiers ──────────────────────────────────────────────────────

    def _llm_render(self, state: AuthoredState) -> str:
        """Tier 1: constrained LLM verbalization."""
        prompt = _VERBALIZATION_TEMPLATE.format(
            query=state.query,
            conclusion=state.conclusion,
            perspective_summary=state.perspective_summary() or "(none)",
            evidence_block=state.evidence_block() or "(none)",
            strategy=state.strategy,
            strategy_def=state.strategy_def[:150] if state.strategy_def else "",
            confidence=state.confidence,
            constraints=state.constraint_string() or "none",
        )
        result = self.llm_callable(prompt, _VERBALIZATION_SYSTEM)
        return result.strip() if result else self._template_render(state)

    def _template_render(self, state: AuthoredState) -> str:
        """Tier 2: deterministic template output — no LLM."""
        parts = []

        # Conclusion paragraph
        if state.conclusion:
            parts.append(state.conclusion.strip())

        # Perspectives block
        if state.perspectives:
            perspective_parts = []
            bridges = ["", "However, ", "Furthermore, ", "Moreover, ", "Additionally, "]
            for i, (name, entry) in enumerate(state.perspectives.items()):
                bridge = bridges[min(i, len(bridges) - 1)]
                perspective_parts.append(f"{bridge}{name}: {entry.text.strip()}")
            parts.append("\n\n".join(perspective_parts))

        # Evidence
        if state.evidence:
            evidence_text = "; ".join(state.evidence[:3])
            parts.append(f"Notably, the supporting evidence: {evidence_text}.")

        # Strategy closer
        if state.strategy and state.strategy != "default":
            parts.append(
                f"That said, this reasoning applied the {state.strategy} strategy "
                f"with {state.confidence:.0%} authored confidence."
            )

        return "\n\n".join(parts) if parts else state.query

    def _fallback_render(self, state: AuthoredState) -> str:
        """Tier 3: minimal safe output when authored state is empty."""
        reason = state.metadata.get("fallback_reason", "substrate unavailable")
        logger.warning(f"[render] fallback triggered: {reason}")
        return ""   # Caller (forge bridge) will use its own fallback path

    # ── Render integrity check ────────────────────────────────────────────

    def check_integrity(self, state: AuthoredState, rendered: str) -> dict:
        """
        Validate that the rendered output doesn't contradict the authored state.

        Returns a dict with keys: passed (bool), violations (list of str).
        This is the render-surface governance layer.
        """
        violations = []
        rendered_lower = rendered.lower()

        # Conclusion should be reflected (at least partially) in output
        if state.conclusion:
            conclusion_words = set(state.conclusion.lower().split())
            rendered_words = set(rendered_lower.split())
            overlap = len(conclusion_words & rendered_words) / max(len(conclusion_words), 1)
            if overlap < 0.15:
                violations.append(
                    f"conclusion_not_reflected: only {overlap:.0%} word overlap "
                    f"between authored conclusion and rendered output"
                )

        # Word limit constraint
        for constraint in state.constraints:
            if constraint.startswith("max_words:"):
                try:
                    limit = int(constraint.split(":")[1])
                    word_count = len(rendered.split())
                    if word_count > limit * 1.2:   # 20% tolerance
                        violations.append(
                            f"word_limit_exceeded: {word_count} words vs limit {limit}"
                        )
                except ValueError:
                    pass

        return {"passed": len(violations) == 0, "violations": violations}
