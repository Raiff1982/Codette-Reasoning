"""
Synthesis Engine - Combines all agent perspectives into a unified multi-perspective response.

Takes the concept, all agent analyses, and critic feedback, then produces
a synthesized explanation that highlights how different perspectives complement
each other. Includes a Final Integrated Understanding section.
"""

import random
import re


class SynthesisEngine:
    """Combines multi-agent analyses into coherent synthesized responses."""

    # Opening templates that set up the multi-perspective frame
    _opening_templates = [
        (
            "To understand '{concept}' with genuine depth, we must examine it through "
            "multiple lenses, each revealing structure that the others miss."
        ),
        (
            "'{concept}' resists single-framework analysis. Its full meaning emerges "
            "only at the intersection of several distinct modes of reasoning."
        ),
        (
            "A comprehensive understanding of '{concept}' requires weaving together "
            "insights from fundamentally different ways of thinking."
        ),
        (
            "No single perspective captures '{concept}' adequately. What follows is "
            "an integrated analysis drawing on physics, philosophy, ethics, creativity, "
            "and human experience."
        ),
        (
            "The richness of '{concept}' becomes apparent only when we hold multiple "
            "analytical frameworks simultaneously and let them inform each other."
        ),
    ]

    # Bridge templates connecting one perspective to another
    _bridge_templates = [
        "Where {agent_a} reveals {insight_a}, {agent_b} adds the crucial dimension of {insight_b}.",
        "The {agent_a} analysis and the {agent_b} analysis converge on a shared insight: {shared}.",
        "What appears as {aspect_a} from the {agent_a} perspective is revealed as {aspect_b} when viewed through {agent_b}.",
        "The tension between {agent_a}'s emphasis on {focus_a} and {agent_b}'s emphasis on {focus_b} is productive, not contradictory.",
        "{agent_a} identifies the mechanism; {agent_b} identifies the meaning.",
        "Combining {agent_a}'s structural analysis with {agent_b}'s human-centered analysis yields a fuller picture.",
    ]

    # Closing templates for the Final Integrated Understanding
    _closing_templates = [
        (
            "**Final Integrated Understanding:** {concept} is simultaneously a "
            "{physical_desc}, a {philosophical_desc}, a {ethical_desc}, a "
            "{creative_desc}, and a {human_desc}. These are not competing descriptions "
            "but complementary facets of a single complex reality. The most robust "
            "understanding holds all five in view, using each to compensate for the "
            "blind spots of the others."
        ),
        (
            "**Final Integrated Understanding:** The multi-perspective analysis reveals "
            "that {concept} cannot be reduced to any single framework without distortion. "
            "The physical analysis provides causal grounding, the philosophical analysis "
            "excavates hidden assumptions, the ethical analysis maps the stakes, the "
            "creative analysis opens new solution spaces, and the empathic analysis "
            "anchors everything in lived human experience. Together they constitute "
            "not a list of separate views but an integrated understanding richer than "
            "any view alone."
        ),
        (
            "**Final Integrated Understanding:** What emerges from this multi-lens "
            "examination of {concept} is not a single 'correct' interpretation but a "
            "structured understanding of how different valid interpretations relate to "
            "each other. The causal structure identified by physics, the meaning "
            "structure identified by philosophy, the value structure identified by "
            "ethics, the possibility structure identified by creative reasoning, and "
            "the experience structure identified by empathy are all real and all "
            "essential. Wisdom lies in knowing which lens to apply in which context "
            "and how to translate insights between them."
        ),
    ]

    def synthesize(
        self,
        concept: str,
        analyses: dict[str, str],
        critique: dict,
    ) -> str:
        """Produce a synthesized multi-perspective response.

        Args:
            concept: The original concept.
            analyses: Dict mapping agent_name -> analysis_text.
            critique: Output from CriticAgent.evaluate_ensemble().

        Returns:
            A synthesized text of 200-400 words.
        """
        sections = []

        # 1. Opening
        opening = random.choice(self._opening_templates).replace("{concept}", concept)
        sections.append(opening)

        # 2. Per-perspective summaries (compressed)
        perspective_summaries = self._extract_perspective_summaries(analyses)
        for agent_name, summary in perspective_summaries.items():
            sections.append(f"**{agent_name} perspective:** {summary}")

        # 3. Cross-perspective bridges (pick 2-3)
        bridges = self._generate_bridges(analyses, perspective_summaries)
        if bridges:
            sections.append("")  # blank line for readability
            for bridge in bridges[:2]:
                sections.append(bridge)

        # 4. Incorporate critic insights
        critic_section = self._incorporate_critique(critique)
        if critic_section:
            sections.append("")
            sections.append(critic_section)

        # 5. Final Integrated Understanding
        closing = self._generate_closing(concept, perspective_summaries)
        sections.append("")
        sections.append(closing)

        raw_synthesis = "\n\n".join(sections)

        # Trim to 200-400 words if needed
        return self._trim_to_target(raw_synthesis, min_words=200, max_words=400)

    def _extract_perspective_summaries(
        self, analyses: dict[str, str]
    ) -> dict[str, str]:
        """Extract a 1-2 sentence summary from each agent's analysis."""
        summaries = {}
        for agent_name, text in analyses.items():
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
            if len(sentences) >= 3:
                # Take the 2nd and 3rd sentences (skip the opening framing)
                summary = " ".join(sentences[1:3])
            elif len(sentences) >= 1:
                summary = sentences[0]
            else:
                summary = text[:200]

            # Trim to ~40 words
            words = summary.split()
            if len(words) > 45:
                summary = " ".join(words[:40]) + "..."
            summaries[agent_name] = summary
        return summaries

    def _generate_bridges(
        self,
        analyses: dict[str, str],
        summaries: dict[str, str],
    ) -> list[str]:
        """Generate cross-perspective bridge statements."""
        bridges = []
        agent_names = list(analyses.keys())

        # Define perspective focus areas for bridge generation
        focus_map = {
            "Newton": "causal mechanisms and measurable dynamics",
            "Quantum": "uncertainty, probability, and the limits of definite knowledge",
            "Ethics": "moral stakes, fairness, and human impact",
            "Philosophy": "foundational assumptions and the structure of meaning",
            "DaVinci": "creative possibilities and cross-domain innovation",
            "Empathy": "emotional reality and lived human experience",
        }

        # Generate a few meaningful bridges
        if len(agent_names) >= 2:
            pairs = []
            for i in range(len(agent_names)):
                for j in range(i + 1, len(agent_names)):
                    pairs.append((agent_names[i], agent_names[j]))
            random.shuffle(pairs)

            for name_a, name_b in pairs[:3]:
                focus_a = focus_map.get(name_a, "its analytical focus")
                focus_b = focus_map.get(name_b, "its analytical focus")
                template = random.choice(self._bridge_templates)

                bridge = template.format(
                    agent_a=name_a,
                    agent_b=name_b,
                    insight_a=focus_a,
                    insight_b=focus_b,
                    shared="the importance of understanding the full system rather than isolated parts",
                    aspect_a="a structural feature",
                    aspect_b="a deeply human concern",
                    focus_a=focus_a,
                    focus_b=focus_b,
                )
                bridges.append(bridge)

        return bridges

    def _incorporate_critique(self, critique: dict) -> str:
        """Turn critic feedback into a synthesis-relevant observation."""
        parts = []

        if critique.get("missing_perspectives"):
            gap = critique["missing_perspectives"][0]
            # Extract just the perspective name
            parts.append(
                f"A notable gap in the analysis is the limited attention to "
                f"{gap.split('lacks a ')[1].split(' perspective')[0] if 'lacks a ' in gap else 'additional'} "
                f"dimensions, which future analysis should address."
            )

        if critique.get("improvement_suggestions"):
            suggestion = critique["improvement_suggestions"][0]
            # Compress the suggestion
            words = suggestion.split()
            if len(words) > 25:
                suggestion = " ".join(words[:25]) + "..."
            parts.append(f"The critic notes: {suggestion}")

        overall = critique.get("overall_quality", 0)
        if overall >= 0.75:
            parts.append(
                "Overall, the multi-perspective ensemble achieves strong analytical "
                "coverage with good complementarity between viewpoints."
            )
        elif overall >= 0.5:
            parts.append(
                "The ensemble provides reasonable coverage but would benefit from "
                "deeper engagement between perspectives."
            )

        return " ".join(parts) if parts else ""

    def _generate_closing(
        self, concept: str, summaries: dict[str, str]
    ) -> str:
        """Generate the Final Integrated Understanding section."""
        template = random.choice(self._closing_templates)

        # Build descriptors from available perspectives
        descriptors = {
            "physical_desc": "system governed by causal dynamics and conservation principles",
            "philosophical_desc": "concept whose meaning depends on the framework from which it is examined",
            "ethical_desc": "domain of genuine moral stakes affecting real people",
            "creative_desc": "space of untapped possibilities waiting for cross-domain insight",
            "human_desc": "lived experience with emotional texture that abstract analysis alone cannot capture",
        }

        result = template
        result = result.replace("{concept}", concept)
        for key, value in descriptors.items():
            result = result.replace("{" + key + "}", value)

        return result

    def _trim_to_target(
        self, text: str, min_words: int = 200, max_words: int = 400
    ) -> str:
        """Trim or pad text to fall within the target word range."""
        words = text.split()

        if len(words) > max_words:
            # Trim from the middle sections, preserving opening and closing
            lines = text.split("\n\n")
            while len(" ".join(lines).split()) > max_words and len(lines) > 3:
                # Remove the longest middle section
                middle_indices = list(range(1, len(lines) - 1))
                if not middle_indices:
                    break
                longest_idx = max(middle_indices, key=lambda i: len(lines[i].split()))
                lines.pop(longest_idx)
            return "\n\n".join(lines)

        return text
