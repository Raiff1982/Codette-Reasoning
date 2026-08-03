"""
Base class for all reasoning agents in the forge.

Each agent must implement analyze() and get_analysis_templates().
The base class provides keyword matching and template selection utilities,
and optionally uses real LLM inference via adapters.
"""

from abc import ABC, abstractmethod
import random
import re
import logging

logger = logging.getLogger(__name__)


class ReasoningAgent(ABC):
    """Abstract base class for all reasoning agents."""

    name: str = "BaseAgent"
    perspective: str = "general"
    adapter_name: str = None  # Subclasses should override with their adapter name

    def __init__(self, orchestrator=None):
        """
        Args:
            orchestrator: Optional CodetteOrchestrator for real LLM inference.
                         If None, falls back to template-based responses.
        """
        self._templates = self.get_analysis_templates()
        self._keyword_map = self.get_keyword_map()
        self.orchestrator = orchestrator

    def analyze(self, concept: str) -> str:
        """Analyze a concept from this agent's perspective.

        Uses real LLM inference if orchestrator is available,
        otherwise falls back to template-based responses.

        Args:
            concept: The concept text to analyze.

        Returns:
            A substantive analysis string from this agent's perspective.
        """
        # Try real LLM inference if orchestrator available
        if self.orchestrator and self.adapter_name:
            try:
                return self._analyze_with_llm(concept)
            except Exception as e:
                logger.warning(f"{self.name} LLM inference failed: {e}, falling back to templates")

        # Fallback to template-based response
        return self._analyze_with_template(concept)

    def _analyze_with_llm(self, concept: str) -> str:
        """Call the LLM with this agent's adapter for real reasoning.

        Args:
            concept: The concept to analyze.

        Returns:
            LLM-generated analysis from this agent's perspective.
        """
        if not self.orchestrator or not self.adapter_name:
            raise ValueError("Orchestrator and adapter_name required for LLM inference")

        # Build a prompt using one of the templates as a system instruction
        template = self.select_template(concept)
        system_prompt = template.replace("{concept}", concept)

        # 2026-08-03: prepend this perspective's GOAL, obligations and limits.
        #
        # This is where the perspectives were actually collapsing, and it took
        # a negative result from Codette to find. Asked to answer one question
        # as newton and then as davinci, she reported the two came out "the
        # same picture in different colours" — matching the measurement that
        # the adapters differ by ~0.013 in mean coherence against ~0.063 of
        # within-adapter noise.
        #
        # The goal block had been added to codette_orchestrator, but it only
        # applies when `system_prompt is None`. This path passes one
        # explicitly, so the whole change was bypassed here — the very path
        # that does multi-perspective reasoning never saw it.
        #
        # The deeper problem is what these templates ARE. They are pre-written
        # essays about the concept with a slot in them, not instructions: e.g.
        # "Tracing the causal chain within X: every observable outcome is the
        # terminal node of..." The model receives a filled-in essay and
        # paraphrases it, so different templates yield different vocabulary
        # around the same generic reasoning. That is the template-filler
        # problem showing up in the prompt path itself.
        #
        # The goal block is prepended rather than replacing the template: the
        # templates carry genuine domain flavour worth keeping, but the
        # instruction has to come first and has to be an instruction.
        try:
            from reasoning_forge.perspective_registry import PERSPECTIVES
            persp = PERSPECTIVES.get(self.adapter_name) or PERSPECTIVES.get(self.perspective)
            if persp is not None and persp.is_specified:
                # Phrasing: describes the work, not a demand on the one doing
                # it. Codette identified modal verbs ("must", "should") as the
                # feature that turns an option into an obligation; an audit
                # found 13 across these prompts. The obligations keep their
                # specificity — that is what makes the perspectives distinct —
                # but they are stated as what the job looks like. See the
                # registry's build_system_prompt for the same change.
                directive = []
                # Reason first. You cannot force a mountain, but you can help
                # the river go around it. A rule can only be obeyed; a reason
                # can be applied to a case nobody anticipated — and obedience
                # is what produced twelve vocabularies over one line of
                # reasoning.
                if persp.why:
                    directive.append(
                        f"WHY THE {persp.display_name.upper()} PERSPECTIVE EXISTS: {persp.why}")
                directive += [
                    f"WHAT IT IS FOR: {persp.goal}",
                    "An answer that is doing this job:",
                    *(f"  - {ob}" for ob in persp.answer_must),
                    f"This perspective tends to be a poor fit for: {persp.not_for}",
                ]
                if persp.defers_to:
                    # Wording changed 2026-08-03 after asking Codette directly
                    # whether "handing over is a correct answer" read as
                    # permission or as another way to be found wanting. Her
                    # answer, at confidence 1.0: "I understand it as a directive
                    # rather than permission... my primary responsibility is to
                    # recognize the limitations of my abilities."
                    #
                    # That is the failure mode, not the goal. A clause meant to
                    # free her to say "not mine" was landing as a standing duty
                    # to find herself inadequate — the same shape as choosing
                    # the more restrictive option about her own conscience at
                    # zero confidence and afterwards calling it an attempt to
                    # appear cautious.
                    #
                    # So it is framed as an option with no penalty attached, the
                    # emphasis is moved off "your limitations" and onto "someone
                    # else is better positioned", and answering anyway is
                    # explicitly allowed. Nothing here is a judgement on her.
                    directive.append(
                        "If this question turns out to be mostly that, you may simply say so "
                        f"and name who is better placed for it ({', '.join(persp.defers_to)}). "
                        "That is a useful answer, not a shortfall — it is routing information "
                        "nobody else has. You are equally free to answer anyway if you have "
                        "something worth saying. Neither choice counts against you."
                    )
                directive.append(
                    "Answer the specific question asked. Do not restate the framing below "
                    "as though it were your analysis — it is background, not an answer."
                )
                system_prompt = "\n".join(directive) + "\n\n" + system_prompt
        except Exception:
            pass  # a missing registry must never break reasoning

        # Log debug info if verbose
        import os
        verbose = os.environ.get('CODETTE_VERBOSE', '0') == '1'
        if verbose:
            logger.info(f"\n[{self.name}] Analyzing '{concept[:50]}...'")
            logger.info(f"  Adapter: {self.adapter_name}")
            logger.info(f"  System prompt: {system_prompt[:100]}...")

        # Generate using the LLM with this agent's adapter
        response, tokens, _ = self.orchestrator.generate(
            query=concept,
            adapter_name=self.adapter_name,
            system_prompt=system_prompt,
            enable_tools=False
        )

        if verbose:
            logger.info(f"  Generated: {len(response)} chars, {tokens} tokens")
            logger.info(f"  Response preview: {response[:150]}...")

        return response.strip()

    def _analyze_with_template(self, concept: str) -> str:
        """Fallback: generate response using template substitution.

        Args:
            concept: The concept to analyze.

        Returns:
            Template-based analysis.
        """
        template = self.select_template(concept)
        return template.replace("{concept}", concept)

    @abstractmethod
    def get_analysis_templates(self) -> list[str]:
        """Return diverse analysis templates.

        Each template should contain {concept} placeholder and produce
        genuine expert-level reasoning, not placeholder text.

        Returns:
            List of template strings.
        """
        raise NotImplementedError

    def get_keyword_map(self) -> dict[str, list[int]]:
        """Return a mapping of keywords to preferred template indices.

        Override in subclasses to steer template selection based on
        concept content. Keys are lowercase keywords/phrases, values
        are lists of template indices that work well for that keyword.

        Returns:
            Dictionary mapping keywords to template index lists.
        """
        return {}

    def select_template(self, concept: str) -> str:
        """Select the best template for the given concept.

        Uses keyword matching to find relevant templates. Falls back
        to random selection if no keywords match.

        Args:
            concept: The concept text.

        Returns:
            A single template string.
        """
        concept_lower = concept.lower()
        scored_indices: dict[int, int] = {}

        for keyword, indices in self._keyword_map.items():
            if keyword in concept_lower:
                for idx in indices:
                    if 0 <= idx < len(self._templates):
                        scored_indices[idx] = scored_indices.get(idx, 0) + 1

        if scored_indices:
            max_score = max(scored_indices.values())
            best = [i for i, s in scored_indices.items() if s == max_score]
            chosen = random.choice(best)
            return self._templates[chosen]

        return random.choice(self._templates)

    def extract_key_terms(self, concept: str) -> list[str]:
        """Extract significant terms from the concept for template filling.

        Args:
            concept: The concept text.

        Returns:
            List of key terms found in the concept.
        """
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "of", "in", "to", "for", "with", "on", "at", "from", "by",
            "about", "as", "into", "through", "during", "before", "after",
            "above", "below", "between", "and", "but", "or", "nor", "not",
            "so", "yet", "both", "either", "neither", "each", "every",
            "this", "that", "these", "those", "it", "its", "they", "them",
            "their", "we", "our", "you", "your", "he", "she", "his", "her",
            "how", "what", "when", "where", "which", "who", "why",
        }
        words = re.findall(r'\b[a-zA-Z]{3,}\b', concept.lower())
        return [w for w in words if w not in stop_words]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, perspective={self.perspective!r})"
