"""
Critic Agent - Evaluates all other agents' outputs for quality, accuracy, and completeness.

Checks logical clarity, conceptual accuracy, identifies redundancy between
perspectives, finds missing perspectives, and suggests improvements.
Returns structured critique with scores.
"""

import re
import logging
from reasoning_forge.agents.base_agent import ReasoningAgent

logger = logging.getLogger(__name__)


class CriticAgent(ReasoningAgent):
    name = "Critic"
    perspective = "meta_evaluative"
    adapter_name = "multi_perspective"  # Use multi-perspective adapter for meta-evaluation

    def get_analysis_templates(self) -> list[str]:
        # The critic does not use templates in the same way -- it evaluates
        # other agents' outputs. These templates are used for framing the
        # overall critique report.
        return [
            "Evaluating the ensemble analysis of '{concept}'.",
        ]

    def analyze(self, concept: str) -> str:
        """Analyze using the multi-perspective adapter for meta-evaluation.

        This delegates to the parent class which uses LLM if orchestrator
        is available, or templates otherwise.
        """
        return super().analyze(concept)


    def evaluate_ensemble_with_llm(
        self,
        concept: str,
        analyses: dict[str, str],
    ) -> dict:
        """Use LLM to evaluate ensemble with real reasoning about quality.

        Falls back to heuristic evaluation if orchestrator unavailable.

        Args:
            concept: Original concept
            analyses: Dict of agent_name -> analysis_text

        Returns:
            Structured critique from the LLM
        """
        if not self.orchestrator or not self.adapter_name:
            # Fallback to heuristic evaluation
            return self.evaluate_ensemble(concept, analyses)

        # Build a prompt asking the LLM to evaluate the analyses
        analyses_text = "\n\n".join([
            f"**{agent}**:\n{text[:300]}..."
            for agent, text in analyses.items()
        ])

        eval_prompt = f"""Evaluate this ensemble analysis of "{concept}":

{analyses_text}

Provide a JSON assessment with:
- agent_scores: subjective quality scores per agent (0-1)
- strengths: key insights across perspectives
- weaknesses: gaps and redundancies
- overall_quality: aggregate score (0-1)"""

        try:
            response, tokens, _ = self.orchestrator.generate(
                query=eval_prompt,
                adapter_name=self.adapter_name,
                system_prompt="You are a meta-evaluator of reasoning quality. Reply in valid JSON.",
                enable_tools=False
            )

            # Try to parse JSON response
            import json
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                try:
                    critique_dict = json.loads(response[start:end])
                    critique_dict["concept"] = concept
                    return critique_dict
                except json.JSONDecodeError:
                    logger.debug("Could not parse JSON from LLM evaluation")
        except Exception as e:
            logger.warning(f"LLM evaluation failed: {e}")

        # Fallback to heuristic if LLM fails
        return self.evaluate_ensemble(concept, analyses)

    def evaluate_ensemble(
        self,
        concept: str,
        analyses: dict[str, str],
    ) -> dict:
        """Evaluate all agent analyses and produce a structured critique.

        Args:
            concept: The original concept being analyzed.
            analyses: Dict mapping agent_name -> analysis_text.

        Returns:
            Dictionary with scores, redundancies, gaps, and suggestions.
        """
        critique = {
            "concept": concept,
            "agent_scores": {},
            "redundancies": [],
            "missing_perspectives": [],
            "improvement_suggestions": [],
            "overall_quality": 0.0,
        }

        total_clarity = 0.0
        total_accuracy = 0.0
        agent_count = len(analyses)

        for agent_name, text in analyses.items():
            clarity = self._score_logical_clarity(text)
            accuracy = self._score_conceptual_accuracy(text, concept)
            critique["agent_scores"][agent_name] = {
                "logical_clarity": round(clarity, 2),
                "conceptual_accuracy": round(accuracy, 2),
                "combined": round((clarity + accuracy) / 2, 2),
            }
            total_clarity += clarity
            total_accuracy += accuracy

        # Detect redundancy between perspectives
        critique["redundancies"] = self._detect_redundancy(analyses)

        # Identify missing perspectives
        critique["missing_perspectives"] = self._find_missing_perspectives(
            concept, analyses
        )

        # Generate improvement suggestions
        critique["improvement_suggestions"] = self._suggest_improvements(
            concept, analyses, critique["agent_scores"]
        )

        # Overall quality score
        if agent_count > 0:
            avg_clarity = total_clarity / agent_count
            avg_accuracy = total_accuracy / agent_count
            redundancy_penalty = len(critique["redundancies"]) * 0.03
            gap_penalty = len(critique["missing_perspectives"]) * 0.05
            raw_score = (avg_clarity + avg_accuracy) / 2 - redundancy_penalty - gap_penalty
            critique["overall_quality"] = round(max(0.0, min(1.0, raw_score)), 2)

        return critique

    def _score_logical_clarity(self, text: str) -> float:
        """Score the logical clarity of an analysis on a 0-1 scale.

        Heuristics:
        - Presence of logical connectives (therefore, because, however, thus)
        - Sentence structure variety (not all same length)
        - Specificity (concrete terms vs vague language)
        - Reasonable length (not too terse, not padded)
        """
        score = 0.5  # baseline

        # Logical connectives indicate reasoning structure
        connectives = [
            "because", "therefore", "thus", "however", "although",
            "consequently", "since", "given that", "implies",
            "it follows", "this means", "as a result", "in contrast",
            "specifically", "for example", "in particular",
        ]
        connective_count = sum(1 for c in connectives if c in text.lower())
        score += min(0.2, connective_count * 0.025)

        # Sentence variety (std dev of sentence lengths)
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        if len(sentences) >= 3:
            lengths = [len(s.split()) for s in sentences]
            mean_len = sum(lengths) / len(lengths)
            variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
            std_dev = variance ** 0.5
            if 3 < std_dev < 15:
                score += 0.1
            elif std_dev >= 1:
                score += 0.05

        # Penalize vague language
        vague_terms = [
            "things", "stuff", "a lot", "very", "really",
            "kind of", "sort of", "basically", "obviously",
        ]
        vague_count = sum(1 for v in vague_terms if v in text.lower())
        score -= vague_count * 0.03

        # Length check (reward substantive, penalize extreme)
        word_count = len(text.split())
        if 80 <= word_count <= 300:
            score += 0.1
        elif 50 <= word_count < 80 or 300 < word_count <= 500:
            score += 0.05
        elif word_count < 30:
            score -= 0.15

        return max(0.0, min(1.0, score))

    def _score_conceptual_accuracy(self, text: str, concept: str) -> float:
        """Score how well the analysis engages with the actual concept.

        Heuristics:
        - References to the concept terms
        - Domain-appropriate vocabulary
        - Absence of generic placeholder language
        """
        score = 0.5

        concept_terms = set(re.findall(r'\b[a-zA-Z]{4,}\b', concept.lower()))
        text_lower = text.lower()

        # Check that concept terms appear in the analysis
        if concept_terms:
            found = sum(1 for t in concept_terms if t in text_lower)
            coverage = found / len(concept_terms)
            score += coverage * 0.15

        # Penalize generic placeholder language
        placeholders = [
            "this concept can be approached",
            "from this perspective we see",
            "looking at this through",
            "applying this lens",
            "in conclusion",
            "to summarize",
        ]
        placeholder_count = sum(1 for p in placeholders if p in text_lower)
        score -= placeholder_count * 0.05

        # Reward specific domain vocabulary (indicates substantive analysis)
        domain_terms = [
            "mechanism", "cause", "effect", "evidence", "principle",
            "constraint", "trade-off", "interaction", "dynamic",
            "structure", "function", "process", "system", "pattern",
            "relationship", "variable", "outcome", "hypothesis",
            "implication", "assumption", "framework", "model",
        ]
        domain_count = sum(1 for d in domain_terms if d in text_lower)
        score += min(0.2, domain_count * 0.02)

        # Reward analysis length proportional to concept complexity
        concept_word_count = len(concept.split())
        text_word_count = len(text.split())
        if text_word_count >= concept_word_count * 3:
            score += 0.1

        return max(0.0, min(1.0, score))

    def _detect_redundancy(self, analyses: dict[str, str]) -> list[str]:
        """Detect thematic redundancy between agent analyses."""
        redundancies = []
        agent_names = list(analyses.keys())

        for i in range(len(agent_names)):
            for j in range(i + 1, len(agent_names)):
                name_a = agent_names[i]
                name_b = agent_names[j]
                overlap = self._compute_content_overlap(
                    analyses[name_a], analyses[name_b]
                )
                if overlap > 0.35:
                    redundancies.append(
                        f"{name_a} and {name_b} share significant thematic overlap "
                        f"({overlap:.0%}). Consider diversifying their angles of analysis."
                    )
        return redundancies

    def _compute_content_overlap(self, text_a: str, text_b: str) -> float:
        """Compute Jaccard similarity of significant word sets."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "of", "in", "to", "for", "with", "on", "at", "from", "by",
            "about", "as", "into", "through", "during", "before", "after",
            "and", "but", "or", "nor", "not", "so", "yet", "both",
            "this", "that", "these", "those", "it", "its", "they", "them",
            "their", "we", "our", "you", "your", "he", "she", "his", "her",
        }
        words_a = {
            w for w in re.findall(r'\b[a-z]{4,}\b', text_a.lower())
            if w not in stop_words
        }
        words_b = {
            w for w in re.findall(r'\b[a-z]{4,}\b', text_b.lower())
            if w not in stop_words
        }
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    def _find_missing_perspectives(
        self, concept: str, analyses: dict[str, str]
    ) -> list[str]:
        """Identify perspectives that are absent from the ensemble."""
        missing = []
        all_text = " ".join(analyses.values()).lower()

        perspective_checks = [
            ("temporal/historical", [
                "history", "historical", "evolution", "over time", "timeline",
                "past", "trajectory", "precedent", "legacy",
            ]),
            ("quantitative/statistical", [
                "statistic", "data", "quantif", "measur", "metric",
                "number", "percentage", "rate", "frequency",
            ]),
            ("ecological/environmental", [
                "environment", "ecolog", "sustainab", "ecosystem",
                "resource", "footprint", "biodiversity", "pollution",
            ]),
            ("economic/financial", [
                "economic", "financial", "cost", "benefit", "market",
                "incentive", "investment", "capital", "trade",
            ]),
            ("legal/regulatory", [
                "legal", "law", "regulat", "compliance", "policy",
                "legislation", "governance", "jurisdiction",
            ]),
            ("educational/pedagogical", [
                "learn", "teach", "education", "pedagog", "curriculum",
                "training", "skill", "literacy",
            ]),
        ]

        for perspective_name, indicators in perspective_checks:
            found = sum(1 for ind in indicators if ind in all_text)
            if found < 2:
                missing.append(
                    f"The ensemble lacks a {perspective_name} perspective. "
                    f"Consider how '{concept}' relates to {perspective_name} dimensions."
                )

        return missing[:3]  # Limit to top 3 gaps

    def _suggest_improvements(
        self,
        concept: str,
        analyses: dict[str, str],
        scores: dict[str, dict],
    ) -> list[str]:
        """Generate actionable improvement suggestions."""
        suggestions = []

        # Identify weakest agent
        if scores:
            weakest = min(scores.items(), key=lambda x: x[1]["combined"])
            if weakest[1]["combined"] < 0.6:
                suggestions.append(
                    f"The {weakest[0]} analysis scored lowest ({weakest[1]['combined']:.2f}). "
                    f"It would benefit from more specific engagement with the concept's "
                    f"concrete details rather than abstract framing."
                )

        # Check for concrete examples
        all_text = " ".join(analyses.values()).lower()
        example_indicators = ["for example", "for instance", "such as", "e.g.", "consider"]
        example_count = sum(1 for e in example_indicators if e in all_text)
        if example_count < 2:
            suggestions.append(
                "The ensemble would benefit from more concrete examples and "
                "illustrations. Abstract reasoning without grounding in specifics "
                "is less persuasive and harder to verify."
            )

        # Check for cross-perspective dialogue
        agent_names_lower = [n.lower() for n in analyses.keys()]
        cross_references = sum(
            1 for name in agent_names_lower
            if any(name in text.lower() for text in analyses.values())
        )
        if cross_references < 2:
            suggestions.append(
                "The analyses operate largely in isolation. The synthesis would benefit "
                "from explicit cross-referencing between perspectives -- showing where "
                "they agree, disagree, or complement each other."
            )

        # Check for actionable takeaways
        action_indicators = [
            "should", "must", "recommend", "suggest", "action",
            "implement", "strategy", "step", "practice",
        ]
        action_count = sum(1 for a in action_indicators if a in all_text)
        if action_count < 3:
            suggestions.append(
                "The ensemble is more diagnostic than prescriptive. Adding concrete, "
                "actionable recommendations would increase practical value."
            )

        return suggestions[:4]  # Limit to top 4 suggestions
