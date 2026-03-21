"""
Problem Generator - Generates diverse reasoning problems from concepts.

Takes a concept text and generates 5-8 different reasoning problems across
types: explain, compare, apply, critique, extend, analogize, decompose, synthesize.
Each problem type has 10+ templates.
"""

import random
import re


class ProblemGenerator:
    """Generates multi-type reasoning problems from concept text."""

    # Each problem type has 10+ templates with {concept} placeholder
    _problem_templates: dict[str, list[str]] = {
        "explain": [
            "Explain the underlying mechanisms of {concept} as if teaching a graduate student who is brilliant but unfamiliar with this domain.",
            "Provide a first-principles explanation of {concept}, starting from the most fundamental assumptions and building up to the full picture.",
            "Explain why {concept} matters, tracing the chain of consequences from the immediate to the long-term.",
            "Explain {concept} by identifying the three most important things someone must understand and why each matters.",
            "Explain the causal structure of {concept}: what drives it, what it drives, and what mediates the relationship.",
            "Give an explanation of {concept} that a thoughtful 15-year-old would find both accessible and intellectually satisfying.",
            "Explain what makes {concept} difficult to understand and how that difficulty can be resolved.",
            "Explain {concept} by contrasting what most people think it means with what it actually means upon closer examination.",
            "Explain the boundary conditions of {concept}: under what circumstances does it hold, and when does it break down?",
            "Explain {concept} using only concrete examples and observable phenomena, avoiding abstract terminology.",
            "Explain how {concept} changes depending on the scale at which you examine it.",
            "Explain the history of how our understanding of {concept} has evolved and what drove each major shift.",
        ],
        "compare": [
            "Compare {concept} with its closest alternative or rival, highlighting where they agree, where they diverge, and why the differences matter.",
            "Compare how {concept} would be understood by an engineer versus a philosopher, and explain what each perspective captures that the other misses.",
            "Compare the short-term and long-term implications of {concept}, noting where they align and where they conflict.",
            "Compare {concept} as it appears in theory versus how it manifests in practice, explaining the gap.",
            "Compare the strongest argument for {concept} with the strongest argument against it, steelmanning both sides.",
            "Compare how {concept} is understood in two different cultural or disciplinary contexts.",
            "Compare the naive understanding of {concept} with the expert understanding, identifying exactly where they diverge.",
            "Compare {concept} with a superficially similar but fundamentally different concept, explaining the crucial distinction.",
            "Compare the risks of overestimating versus underestimating the importance of {concept}.",
            "Compare how {concept} would be analyzed using quantitative methods versus qualitative methods, and what each approach reveals.",
            "Compare the state of {concept} ten years ago with its current state, identifying the key drivers of change.",
        ],
        "apply": [
            "Apply the principles underlying {concept} to solve a concrete real-world problem that you specify.",
            "Describe how you would apply {concept} in a professional context, including specific steps and expected outcomes.",
            "Apply {concept} to a domain where it is not typically used and explain what new insights emerge.",
            "Design an experiment or test that would apply {concept} to generate actionable data.",
            "Apply {concept} to evaluate a current real-world controversy or decision, showing how it clarifies the issues.",
            "Show how {concept} could be applied to improve an existing system or process, specifying the mechanism of improvement.",
            "Apply {concept} to predict what will happen in a specified scenario and explain your reasoning.",
            "Demonstrate how {concept} applies to everyday decision-making by walking through a common choice people face.",
            "Apply {concept} to diagnose why a particular system or approach is failing and propose a remedy.",
            "Show how {concept} could be applied at three different scales (individual, organizational, societal) with different implications at each.",
            "Apply {concept} to a field where it has been underutilized and argue for its relevance.",
        ],
        "critique": [
            "Identify the three most significant weaknesses or limitations of {concept} and assess how seriously they undermine it.",
            "Construct the strongest possible objection to {concept} and then evaluate whether the objection succeeds.",
            "Critique the hidden assumptions underlying {concept}, assessing which are well-founded and which are questionable.",
            "Evaluate whether {concept} confuses correlation with causation, and if so, what the actual causal story might be.",
            "Critique the evidence base for {concept}: is it sufficient, and what kinds of evidence are missing?",
            "Identify who benefits from the current framing of {concept} and whether that framing may be self-serving.",
            "Assess whether {concept} commits any logical fallacies and, if so, whether the core insight survives the correction.",
            "Critique the scalability of {concept}: does it work at small scale but fail at large scale, or vice versa?",
            "Evaluate whether {concept} is genuinely novel or whether it is a repackaging of older ideas under new terminology.",
            "Critique the precision of {concept}: is it defined clearly enough to be testable, or is it vague enough to be unfalsifiable?",
            "Assess whether {concept} adequately accounts for the perspectives and experiences of marginalized groups.",
        ],
        "extend": [
            "Extend {concept} to its logical conclusion: if we take it seriously and follow it consistently, where does it lead?",
            "Propose a novel extension of {concept} that addresses one of its current limitations.",
            "Extend {concept} into the future: how might it evolve over the next decade given current trends?",
            "Identify a domain where {concept} has not yet been applied and develop the extension, including what modifications would be needed.",
            "Extend {concept} by combining it with an insight from a different field, creating something neither field has alone.",
            "Propose how {concept} could be extended to address a problem it was not originally designed for.",
            "Extend {concept} by asking what happens at its extreme: what if it were applied maximally or universally?",
            "Develop an extension of {concept} that makes it more robust against its known failure modes.",
            "Extend {concept} by integrating quantitative measurement where it currently relies on qualitative judgment.",
            "Propose a version of {concept} adapted for a context where resources are extremely limited.",
            "Extend {concept} by identifying the next logical question it raises and sketching how to answer it.",
        ],
        "analogize": [
            "Construct an analogy between {concept} and a biological system, mapping each component to its biological counterpart.",
            "Create an analogy between {concept} and a well-known everyday experience that makes the abstract concrete.",
            "Develop an analogy between {concept} and a historical event or period, drawing specific parallels.",
            "Build an analogy between {concept} and a mechanical or engineering system, identifying the load-bearing correspondences.",
            "Construct an analogy between {concept} and a game or sport, mapping rules, strategies, and winning conditions.",
            "Create an analogy between {concept} and a musical composition, identifying rhythm, harmony, dissonance, and resolution.",
            "Develop an analogy between {concept} and an ecosystem, mapping the roles of producers, consumers, decomposers, and energy flow.",
            "Build an analogy between {concept} and the process of cooking a complex meal, mapping ingredients, techniques, and timing.",
            "Construct an analogy between {concept} and a journey, identifying the starting point, obstacles, milestones, and destination.",
            "Create an analogy between {concept} and a language, mapping grammar, vocabulary, syntax, and meaning.",
            "After constructing your best analogy for {concept}, identify exactly where the analogy breaks down and what the breakdown reveals.",
        ],
        "decompose": [
            "Decompose {concept} into its fundamental components and explain how each contributes to the whole.",
            "Break {concept} into its necessary and sufficient conditions: what must be present for it to hold?",
            "Decompose {concept} into layers of abstraction, from the most concrete to the most abstract.",
            "Identify the independent variables within {concept} and explain how each can be varied independently.",
            "Decompose {concept} into its temporal phases: what happens first, second, third, and how do the phases connect?",
            "Break {concept} into its stakeholder dimensions: how does each affected party experience it differently?",
            "Decompose {concept} into its inputs, processes, and outputs, tracing the transformation at each stage.",
            "Identify the key tensions or trade-offs within {concept} and explain how they create its characteristic behavior.",
            "Decompose {concept} into what is known with confidence, what is suspected but unconfirmed, and what remains entirely unknown.",
            "Break {concept} into its structural elements (what it is) and its dynamic elements (how it changes).",
            "Decompose the causal graph of {concept}: which factors cause which, and which are merely correlated?",
        ],
        "synthesize": [
            "Synthesize a unified understanding of {concept} that integrates scientific, philosophical, and practical perspectives.",
            "Synthesize the arguments for and against {concept} into a balanced position that acknowledges the valid points on both sides.",
            "Create a synthesis that resolves the apparent contradiction between two competing interpretations of {concept}.",
            "Synthesize insights about {concept} from at least three different disciplines into a coherent framework.",
            "Synthesize a practical guide for engaging with {concept} that draws on both theoretical understanding and real-world experience.",
            "Synthesize the historical evolution and current state of {concept} into a narrative that explains both where we are and how we got here.",
            "Create a synthesis of {concept} that a diverse audience (technical and non-technical, young and old) would find valuable.",
            "Synthesize the local and global dimensions of {concept} into an understanding that operates at both scales.",
            "Synthesize the quantitative and qualitative aspects of {concept} into an integrated assessment.",
            "Create a synthesis of {concept} that explicitly addresses and resolves the top three objections to it.",
            "Synthesize a forward-looking vision of {concept} that builds on current understanding to anticipate future development.",
        ],
    }

    def generate_problems(
        self, concept: str, count: int | None = None
    ) -> list[tuple[str, str]]:
        """Generate reasoning problems from a concept.

        Args:
            concept: The concept text to generate problems for.
            count: Number of problems to generate (5-8 if None).

        Returns:
            List of (problem_type, problem_text) tuples.
        """
        if count is None:
            count = random.randint(5, 8)
        count = max(1, min(count, len(self._problem_templates)))

        # Select problem types -- always include explain and synthesize,
        # then fill remaining slots randomly from other types
        all_types = list(self._problem_templates.keys())
        required = ["explain", "synthesize"]
        optional = [t for t in all_types if t not in required]
        random.shuffle(optional)

        selected_types = required + optional[: max(0, count - len(required))]
        random.shuffle(selected_types)

        problems = []
        for ptype in selected_types:
            templates = self._problem_templates[ptype]
            # Score templates by keyword relevance to concept
            template = self._select_relevant_template(concept, templates)
            problem_text = template.replace("{concept}", concept)
            problems.append((ptype, problem_text))

        return problems

    def generate_all_types(self, concept: str) -> list[tuple[str, str]]:
        """Generate one problem of each type for a concept.

        Args:
            concept: The concept text.

        Returns:
            List of (problem_type, problem_text) tuples, one per type.
        """
        problems = []
        for ptype, templates in self._problem_templates.items():
            template = self._select_relevant_template(concept, templates)
            problem_text = template.replace("{concept}", concept)
            problems.append((ptype, problem_text))
        return problems

    def _select_relevant_template(
        self, concept: str, templates: list[str]
    ) -> str:
        """Select the template most relevant to the concept keywords.

        Falls back to random selection if no strong match.
        """
        concept_words = set(re.findall(r'\b[a-z]{4,}\b', concept.lower()))
        if not concept_words:
            return random.choice(templates)

        scored = []
        for template in templates:
            template_lower = template.lower()
            score = sum(1 for w in concept_words if w in template_lower)
            scored.append((score, template))

        max_score = max(s for s, _ in scored)
        if max_score > 0:
            best = [t for s, t in scored if s == max_score]
            return random.choice(best)

        return random.choice(templates)
