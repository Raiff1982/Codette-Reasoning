"""
cognition_substrate.py — Codette Pure-Python Reasoning Engine
=============================================================

CognitionSubstrate runs the full Codette reasoning pipeline with zero LLM
calls.  It owns semantic authority: it decides what is concluded, what
evidence supports it, and which strategy was applied.

Pipeline
--------
1. Cocoon retrieval   — relevant prior reasoning from UnifiedMemory
2. Multi-perspective  — ForgeEngine template agents (no LLM)
3. Strategy synthesis — SynthesisEngineV3 / CocoonSynthesizer (no LLM)
4. Confidence scoring — weighted by cocoon integrity + adapter confidence
5. AuthoredState      — fully-authored cognitive artifact

The output AuthoredState is passed to RenderLayer, which uses an LLM
purely for verbalization — not for reasoning or truth determination.

This separation means:
  - Codette's cognition survives model swaps
  - Hallucination surface is bounded by authored state
  - Render integrity can be validated against authored content

Original: Jonathan Harrison (Raiff1982/Codette-Reasoning)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from inference.authored_state import AuthoredState, PerspectiveEntry

logger = logging.getLogger(__name__)


class CognitionSubstrate:
    """
    Pure-Python multi-perspective reasoning engine.

    All reasoning happens here before the LLM is invoked.
    """

    def __init__(
        self,
        forge=None,             # ForgeEngine instance (template mode, no LLM)
        memory=None,            # UnifiedMemory instance
        synthesizer=None,       # CocoonSynthesizer instance
        synthesis_v3=None,      # SynthesisEngineV3 instance
    ):
        self.forge = forge
        self.memory = memory
        self.synthesizer = synthesizer
        self.synthesis_v3 = synthesis_v3
        self._init_engines()

    def _init_engines(self) -> None:
        """Lazy-init any engines not provided at construction."""
        if self.forge is None:
            try:
                from reasoning_forge.forge_engine import ForgeEngine
                self.forge = ForgeEngine(orchestrator=None)   # template mode
                logger.info("[substrate] ForgeEngine loaded (template mode)")
            except Exception as e:
                logger.warning(f"[substrate] ForgeEngine unavailable: {e}")

        if self.memory is None or self.synthesizer is None:
            try:
                from reasoning_forge.unified_memory import UnifiedMemory
                from reasoning_forge.cocoon_synthesizer import CocoonSynthesizer
                self.memory = self.memory or UnifiedMemory()
                self.synthesizer = self.synthesizer or CocoonSynthesizer(memory=self.memory)
                logger.info(f"[substrate] Memory loaded ({self.memory._total_stored} cocoons)")
            except Exception as e:
                logger.warning(f"[substrate] Memory/Synthesizer unavailable: {e}")

        if self.synthesis_v3 is None:
            try:
                from reasoning_forge.synthesis_engine_v3 import SynthesisEngineV3
                self.synthesis_v3 = SynthesisEngineV3()
                logger.info("[substrate] SynthesisEngineV3 loaded")
            except Exception as e:
                logger.warning(f"[substrate] SynthesisEngineV3 unavailable: {e}")

    # ── Public API ─────────────────────────────────────────────────────────

    def process(
        self,
        query: str,
        constraints: Optional[List[str]] = None,
        prior_context: Optional[List[Dict[str, Any]]] = None,
    ) -> AuthoredState:
        """
        Run the full substrate pipeline and return an AuthoredState.

        Parameters
        ----------
        query          : The user's query
        constraints    : Render constraints e.g. ["max_words:150", "tone:calm"]
        prior_context  : Prior turn summaries for continuity

        Returns
        -------
        AuthoredState with all fields populated from substrate reasoning.
        Falls back to AuthoredState.fallback() on hard failure.
        """
        t0 = time.time()
        try:
            perspectives = self._gather_perspectives(query)
            cocoon_context = self._retrieve_cocoons(query)
            strategy, strategy_def, evidence = self._synthesize(query, perspectives, cocoon_context)
            conclusion = self._derive_conclusion(query, perspectives, strategy, cocoon_context)
            confidence = self._score_confidence(perspectives, cocoon_context)
            emotion = self._select_emotion(perspectives, query)
            cocoon_refs = [c.get("cocoon_id", "") for c in cocoon_context if c.get("cocoon_id")]

            state = AuthoredState(
                query=query,
                conclusion=conclusion,
                evidence=evidence,
                perspectives=perspectives,
                strategy=strategy,
                strategy_def=strategy_def,
                confidence=confidence,
                dominant_emotion=emotion,
                cocoon_refs=cocoon_refs,
                constraints=constraints or [],
                metadata={
                    "substrate_ms": round((time.time() - t0) * 1000, 1),
                    "perspective_count": len(perspectives),
                    "cocoon_hits": len(cocoon_context),
                },
                render_tier="llm" if confidence > 0.1 else "fallback",
            )
            logger.debug(
                f"[substrate] processed '{query[:60]}' in {state.metadata['substrate_ms']}ms "
                f"— {len(perspectives)} perspectives, confidence={confidence:.2f}"
            )
            return state

        except Exception as e:
            logger.warning(f"[substrate] process failed: {e}")
            return AuthoredState.fallback(query, reason=str(e))

    # ── Internal pipeline steps (all LLM-free) ────────────────────────────

    def _gather_perspectives(self, query: str) -> Dict[str, PerspectiveEntry]:
        """Run template analysis agents — no LLM calls."""
        perspectives: Dict[str, PerspectiveEntry] = {}
        if not self.forge:
            return perspectives
        for agent in getattr(self.forge, "analysis_agents", []):
            try:
                text = agent.analyze(query)
                if text:
                    perspectives[agent.name] = PerspectiveEntry(
                        agent_name=agent.name,
                        text=text.strip(),
                        confidence=0.7,
                        domain=getattr(agent, "domain", ""),
                    )
            except Exception as e:
                logger.debug(f"[substrate] agent {agent.name} failed: {e}")
        return perspectives

    def _retrieve_cocoons(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant prior cocoons from memory."""
        if not self.memory:
            return []
        try:
            return self.memory.recall_relevant(query, max_results=max_results) or []
        except Exception as e:
            logger.debug(f"[substrate] cocoon retrieval failed: {e}")
            return []

    def _synthesize(
        self,
        query: str,
        perspectives: Dict[str, PerspectiveEntry],
        cocoons: List[Dict[str, Any]],
    ) -> tuple[str, str, List[str]]:
        """
        Derive strategy name, definition, and evidence list.

        Returns (strategy, strategy_def, evidence).
        """
        strategy = "MultiPerspective"
        strategy_def = "Synthesise competing analytical frames into a coherent conclusion."
        evidence: List[str] = []

        # Evidence from cocoon memory
        for c in cocoons[:3]:
            q = c.get("query", "")[:60]
            r = c.get("response", "")[:100]
            if q:
                evidence.append(f"Prior analysis of '{q}': {r}")

        # Evidence from synthesizer
        if self.synthesizer:
            try:
                comparison = self.synthesizer.run_full_synthesis(query)
                strategy = comparison.new_strategy.name or strategy
                strategy_def = (comparison.new_strategy.definition or strategy_def)[:300]
                for e_str in (comparison.evidence_chain or [])[:3]:
                    evidence.append(e_str)
            except Exception as e:
                logger.debug(f"[substrate] synthesizer failed: {e}")

        return strategy, strategy_def, evidence

    def _derive_conclusion(
        self,
        query: str,
        perspectives: Dict[str, PerspectiveEntry],
        strategy: str,
        cocoons: List[Dict[str, Any]],
    ) -> str:
        """
        Build a concise conclusion from the available authored material.

        Priority: synthesizer conclusion → cocoon summary → perspective summary.
        """
        # Try synthesizer conclusion first
        if self.synthesizer:
            try:
                comparison = self.synthesizer.run_full_synthesis(query)
                if comparison.new_path.conclusion:
                    return comparison.new_path.conclusion[:300]
            except Exception:
                pass

        # Fall back to most-relevant cocoon response
        if cocoons:
            top = cocoons[0]
            response = top.get("response", "")[:200]
            if response:
                return f"Based on accumulated reasoning: {response}"

        # Fall back to dominant perspective
        if perspectives:
            first = next(iter(perspectives.values()))
            return first.text[:200]

        return ""

    def _score_confidence(
        self,
        perspectives: Dict[str, PerspectiveEntry],
        cocoons: List[Dict[str, Any]],
    ) -> float:
        """Weighted confidence from perspective count and cocoon integrity."""
        base = 0.3

        # More perspectives → higher confidence
        p_count = len(perspectives)
        perspective_bonus = min(p_count * 0.1, 0.3)

        # Cocoon integrity scores
        integrity_scores = [
            float(c.get("cocoon_integrity_score") or c.get("intensity") or 0.5)
            for c in cocoons
        ]
        cocoon_bonus = (sum(integrity_scores) / len(integrity_scores) * 0.2) if integrity_scores else 0.0

        # Individual agent confidence
        agent_conf = (
            sum(e.confidence for e in perspectives.values()) / max(len(perspectives), 1)
            if perspectives else 0.5
        )
        agent_bonus = agent_conf * 0.2

        return min(base + perspective_bonus + cocoon_bonus + agent_bonus, 1.0)

    def _select_emotion(self, perspectives: Dict[str, PerspectiveEntry], query: str) -> str:
        """Select dominant emotional framing based on query and agent mix."""
        query_lower = query.lower()
        if any(w in query_lower for w in ("feel", "sad", "hurt", "afraid", "worried", "love")):
            return "empathetic"
        if any(w in query_lower for w in ("wrong", "unfair", "should", "must", "rights")):
            return "ethical"
        if any(w in query_lower for w in ("how", "why", "explain", "what is", "calculate")):
            return "analytical"
        if any(w in query_lower for w in ("create", "imagine", "story", "design", "write")):
            return "creative"
        return "curious"
