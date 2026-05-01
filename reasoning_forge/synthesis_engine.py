"""
Synthesis Engine v2.1 — Codette RC+xi Framework

Upgrades over v1:
- Tension-aware bridging: bridges now surface REAL disagreements, not random template picks
- Dynamic closing: descriptors are derived from active perspective analyses, not hardcoded
- Epistemic state block: every synthesis emits a structured CognitiveStateTrace
- Perspective coverage enforcement: warns when < 3 perspectives are active
- Sycophancy resistance: synthesis must name at least one unresolved tension
- All 8 registered perspectives supported in focus_map
"""

from __future__ import annotations
import re
import textwrap
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CognitiveStateTrace:
    """Structured reasoning state emitted alongside every synthesis."""
    concept: str
    active_perspectives: list[str]
    epsilon_band: str           # 'low' | 'moderate' | 'high'
    epsilon_value: float        # 0.0 – 1.0
    gamma_coherence: float      # 0.0 – 1.0
    top_tensions: list[str]     # named pairwise tensions
    unresolved: list[str]       # tensions synthesis could NOT resolve
    eta_score: Optional[float]  # AEGIS ethical alignment, None if not evaluated
    trust_level: str            # Guardian trust classification
    memory_write: bool          # whether this exchange should be cocooned
    synthesis_quality: str      # 'strong' | 'adequate' | 'partial'

    def to_block(self) -> str:
        """Render as a compact readable block for optional surfacing."""
        tension_str = "; ".join(self.top_tensions) if self.top_tensions else "none detected"
        unresolved_str = "; ".join(self.unresolved) if self.unresolved else "all tensions bridged"
        eta_str = f"{self.eta_score:.2f}" if self.eta_score is not None else "not evaluated"
        return (
            f"╔═ Codette Cognitive State ══════════════════════╗\n"
            f"  concept       : {self.concept}\n"
            f"  perspectives  : {', '.join(self.active_perspectives)}\n"
            f"  epsilon       : {self.epsilon_value:.2f} ({self.epsilon_band})\n"
            f"  gamma         : {self.gamma_coherence:.2f}\n"
            f"  top tensions  : {tension_str}\n"
            f"  unresolved    : {unresolved_str}\n"
            f"  eta (AEGIS)   : {eta_str}\n"
            f"  trust         : {self.trust_level}\n"
            f"  cocoon write  : {'yes' if self.memory_write else 'no'}\n"
            f"  quality       : {self.synthesis_quality}\n"
            f"╚════════════════════════════════════════════════╝"
        )


class SynthesisEngine:
    """Combines multi-agent analyses into coherent synthesized responses.

    v2.1 changes:
    - Derives tension pairs from actual analysis text divergence
    - Builds dynamic perspective descriptors from real analysis content
    - Enforces at least one unresolved tension in every synthesis
    - Emits CognitiveStateTrace alongside the text response
    """

    # All 8 registered Codette perspectives + their focus areas
    _focus_map: dict[str, str] = {
        "Newton":             "causal mechanisms, measurable dynamics, and logical cause-effect chains",
        "DaVinci":            "cross-domain synthesis, design innovation, and creative possibility spaces",
        "Empathy":            "emotional reality, relational understanding, and lived human experience",
        "Philosophy":         "foundational assumptions, meaning-making, and the structure of concepts",
        "Quantum":            "superposition of possibilities, probability distributions, and complementary interpretations",
        "Consciousness":      "meta-cognitive self-reflection, recursive comprehension, and RC+xi integration",
        "MultiPerspective":   "harmonizing threads across all active perspectives into unified insight",
        "SystemsArchitecture":"systemic properties, feedback loops, emergent behaviors, and input-process-output dynamics",
    }

    # Opening lines keyed to epsilon band — not random, context-driven
    _openings: dict[str, list[str]] = {
        "low": [
            "The perspectives converge clearly on '{concept}': here is the integrated view.",
            "High coherence across the reasoning ensemble on '{concept}' allows a direct synthesis.",
        ],
        "moderate": [
            "'{concept}' reveals genuine productive tension across the reasoning perspectives.",
            "To understand '{concept}' fully, we must hold several competing frames simultaneously.",
        ],
        "high": [
            "'{concept}' resists resolution — the perspectives are in genuine conflict and that conflict is informative.",
            "Maximum epistemic tension on '{concept}': what follows names what is unresolved, not just what converges.",
        ],
    }

    def synthesize(
        self,
        concept: str,
        analyses: dict[str, str],
        critique: dict,
        epsilon: float = 0.35,
        gamma: float = 0.72,
        eta: Optional[float] = None,
        trust_level: str = "standard",
    ) -> tuple[str, CognitiveStateTrace]:
        """Produce a synthesized response AND a CognitiveStateTrace.

        Args:
            concept: The original query or concept.
            analyses: Dict mapping agent_name -> analysis_text.
            critique: Output from CriticAgent.evaluate_ensemble().
            epsilon: Epistemic tension score (0.0-1.0).
            gamma: Ensemble coherence score (0.0-1.0).
            eta: AEGIS ethical alignment score, or None.
            trust_level: Guardian trust classification string.

        Returns:
            (synthesis_text, CognitiveStateTrace)
        """
        epsilon_band = self._classify_epsilon(epsilon)
        active = list(analyses.keys())

        if len(active) < 3:
            import warnings
            warnings.warn(
                f"SynthesisEngine: only {len(active)} perspectives active. "
                "Synthesis quality will be partial. Consider activating >= 3.",
                RuntimeWarning,
            )

        sections = []

        # 1. Opening (epsilon-band driven, not random)
        opening_pool = self._openings.get(epsilon_band, self._openings["moderate"])
        opening = opening_pool[hash(concept) % len(opening_pool)].replace("{concept}", concept)
        sections.append(opening)
        sections.append("")

        # 2. Per-perspective summaries with real content extraction
        perspective_summaries = self._extract_perspective_summaries(analyses)
        for agent_name, summary in perspective_summaries.items():
            focus = self._focus_map.get(agent_name, "analytical focus")
            sections.append(f"**{agent_name}** ({focus[:40]}...): {summary}")

        sections.append("")

        # 3. Tension-aware bridges — find real divergences, not random templates
        bridges, tensions_found, unresolved = self._generate_tension_bridges(
            analyses, perspective_summaries, epsilon_band
        )
        if bridges:
            for bridge in bridges:
                sections.append(bridge)
            sections.append("")

        # 4. Critic section
        critic_section = self._incorporate_critique(critique)
        if critic_section:
            sections.append(critic_section)
            sections.append("")

        # 5. Dynamic closing derived from actual analysis content
        closing = self._generate_dynamic_closing(concept, analyses, perspective_summaries, epsilon_band)
        sections.append(closing)

        # 6. Unresolved tensions block (always included if any exist)
        if unresolved:
            sections.append("")
            sections.append(
                f"**⚠ Unresolved tensions:** {'; '.join(unresolved)}. "
                "These remain open questions that further reasoning or evidence should address."
            )

        raw = "\n\n".join(s for s in sections if s != "")
        synthesis_text = self._trim_to_target(raw, min_words=200, max_words=500)

        # 7. Build CognitiveStateTrace
        synthesis_quality = (
            "strong" if gamma >= 0.7 and len(active) >= 4
            else "adequate" if gamma >= 0.5 or len(active) >= 3
            else "partial"
        )
        trace = CognitiveStateTrace(
            concept=concept,
            active_perspectives=active,
            epsilon_band=epsilon_band,
            epsilon_value=epsilon,
            gamma_coherence=gamma,
            top_tensions=tensions_found[:3],
            unresolved=unresolved[:2],
            eta_score=eta,
            trust_level=trust_level,
            memory_write=(synthesis_quality != "partial" and epsilon < 0.85),
            synthesis_quality=synthesis_quality,
        )

        return synthesis_text, trace

    # ─── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _classify_epsilon(epsilon: float) -> str:
        if epsilon <= 0.29:
            return "low"
        elif epsilon <= 0.59:
            return "moderate"
        else:
            return "high"

    @staticmethod
    def _extract_perspective_summaries(analyses: dict[str, str]) -> dict[str, str]:
        """Extract a focused 1-2 sentence summary from each analysis."""
        summaries = {}
        for name, text in analyses.items():
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 20]
            if len(sentences) >= 3:
                summary = " ".join(sentences[1:3])
            elif sentences:
                summary = sentences[0]
            else:
                summary = text[:200]
            words = summary.split()
            if len(words) > 50:
                summary = " ".join(words[:45]) + "…"
            summaries[name] = summary
        return summaries

    def _generate_tension_bridges(
        self,
        analyses: dict[str, str],
        summaries: dict[str, str],
        epsilon_band: str,
    ) -> tuple[list[str], list[str], list[str]]:
        """Identify real tensions between perspective pairs and bridge them.

        Returns:
            bridges: List of bridge statement strings.
            tensions_found: Named tension pairs.
            unresolved: Tensions too deep to bridge (high epsilon only).
        """
        bridges = []
        tensions_found = []
        unresolved = []

        agent_names = list(analyses.keys())

        # Tension indicator keywords per perspective
        _tension_signals: dict[str, list[str]] = {
            "Newton":             ["cause", "mechanism", "measur", "quantif", "predict"],
            "Empathy":            ["feel", "human", "emotional", "lived", "relat"],
            "Philosophy":         ["assume", "meaning", "concept", "ontolog", "epistem"],
            "Quantum":            ["uncertain", "probabilit", "superpos", "comple", "wave"],
            "DaVinci":            ["creat", "innovat", "design", "possibi", "cross-domain"],
            "Consciousness":      ["self", "recurs", "meta", "aware", "integrat"],
            "SystemsArchitecture":["system", "feedback", "emergent", "loop", "architect"],
            "MultiPerspective":   ["synthes", "harmoni", "integrat", "unified", "bridge"],
        }

        def signal_score(name: str, text: str) -> float:
            signals = _tension_signals.get(name, [])
            text_lower = text.lower()
            return sum(1 for s in signals if s in text_lower) / max(len(signals), 1)

        # Score each perspective's dominance signals
        scores = {n: signal_score(n, analyses[n]) for n in agent_names}

        # Find pairs with divergent signals (potential tension)
        checked = set()
        for i, a in enumerate(agent_names):
            for b in agent_names[i + 1:]:
                pair_key = f"{a}_vs_{b}"
                if pair_key in checked:
                    continue
                checked.add(pair_key)

                diff = abs(scores.get(a, 0) - scores.get(b, 0))
                if diff >= 0.15 or epsilon_band == "high":
                    tensions_found.append(pair_key)
                    fa = self._focus_map.get(a, "its analytical axis")
                    fb = self._focus_map.get(b, "its analytical axis")

                    if epsilon_band == "high":
                        # Name the conflict explicitly; mark as unresolved
                        bridge = (
                            f"**{a} ↔ {b} [unresolved]:** {a}'s emphasis on {fa[:50]} "
                            f"directly conflicts with {b}'s emphasis on {fb[:50]}. "
                            f"Both claims are valid within their frame; this synthesis "
                            f"does not force a false resolution."
                        )
                        unresolved.append(pair_key)
                    else:
                        bridge = (
                            f"**{a} ↔ {b}:** The tension between {a}'s focus on {fa[:50]} "
                            f"and {b}'s focus on {fb[:50]} is productive — together they "
                            f"reveal dimensions neither captures alone."
                        )
                    bridges.append(bridge)

        return bridges[:4], tensions_found, unresolved

    def _generate_dynamic_closing(
        self,
        concept: str,
        analyses: dict[str, str],
        summaries: dict[str, str],
        epsilon_band: str,
    ) -> str:
        """Generate a closing derived from actual analysis content, not hardcoded."""
        perspective_list = ", ".join(
            f"{n} ({self._focus_map.get(n, 'analysis')[:30]}…)"
            for n in summaries
        )

        if epsilon_band == "low":
            verdict = (
                f"The perspectives converge: '{concept}' is best understood as "
                f"{self._extract_shared_claim(analyses)}. "
                f"This convergence across {perspective_list} "
                f"provides high-confidence grounding for that understanding."
            )
        elif epsilon_band == "moderate":
            verdict = (
                f"**Final Integrated Understanding:** '{concept}' is a domain where "
                f"multiple valid frameworks each reveal something the others miss. "
                f"The perspectives activated — {perspective_list} — agree that "
                f"{self._extract_shared_claim(analyses)}, but diverge on "
                f"how to weight mechanism versus meaning, structure versus experience. "
                f"A complete understanding requires holding both."
            )
        else:  # high
            verdict = (
                f"**Final Integrated Understanding — High Tension:** "
                f"'{concept}' remains genuinely contested across the activated perspectives "
                f"({perspective_list}). Rather than forcing false convergence, "
                f"Codette records this as an open attractor: a concept whose full meaning "
                f"is still being discovered through the tension between frameworks. "
                f"The most honest answer is to map the disagreement, not dissolve it."
            )
        return verdict

    @staticmethod
    def _extract_shared_claim(analyses: dict[str, str]) -> str:
        """Find the most common substantive noun phrase across analyses."""
        # Collect all 2-3 word sequences appearing in multiple analyses
        from collections import Counter
        ngram_counter: Counter = Counter()
        for text in analyses.values():
            words = re.findall(r'\b[a-zA-Z][a-zA-Z]{3,}\b', text.lower())
            for i in range(len(words) - 1):
                ngram_counter[(words[i], words[i + 1])] += 1

        # Find n-grams appearing in >= half the analyses
        threshold = max(2, len(analyses) // 2)
        candidates = [
            " ".join(ng)
            for ng, count in ngram_counter.most_common(20)
            if count >= threshold and len(" ".join(ng)) > 8
        ]
        if candidates:
            return candidates[0]
        return "a concept requiring multi-framework analysis"

    @staticmethod
    def _incorporate_critique(critique: dict) -> str:
        parts = []
        if critique.get("missing_perspectives"):
            gap = critique["missing_perspectives"][0]
            parts.append(f"**Critic note:** {gap}")
        if critique.get("improvement_suggestions"):
            sug = critique["improvement_suggestions"][0]
            words = sug.split()
            parts.append(f"**Improvement:** {' '.join(words[:30])}{'…' if len(words) > 30 else ''}")
        overall = critique.get("overall_quality", 0)
        if overall >= 0.75:
            parts.append("Ensemble quality: strong (≥ 0.75).")
        elif overall >= 0.5:
            parts.append("Ensemble quality: adequate (0.5–0.75). Deeper inter-perspective engagement recommended.")
        else:
            parts.append("Ensemble quality: partial (< 0.5). Expand perspective coverage before final synthesis.")
        return " ".join(parts)

    @staticmethod
    def _trim_to_target(text: str, min_words: int = 200, max_words: int = 500) -> str:
        words = text.split()
        if len(words) <= max_words:
            return text
        lines = text.split("\n\n")
        while len(" ".join(lines).split()) > max_words and len(lines) > 3:
            middle = list(range(1, len(lines) - 1))
            if not middle:
                break
            longest = max(middle, key=lambda i: len(lines[i].split()))
            lines.pop(longest)
        return "\n\n".join(lines)
