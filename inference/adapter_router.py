#!/usr/bin/env python3
"""Codette Adapter Router — Intelligent Perspective Selection

Analyzes incoming queries and routes to the optimal LoRA adapter(s).
Supports three routing strategies:
  1. keyword  — Fast keyword/domain matching (no LLM needed)
  2. llm      — Uses base model to classify query intent
  3. hybrid   — Keyword first, LLM fallback for ambiguous queries

The router preserves epistemic tension (xi) by selecting complementary
perspectives rather than defaulting to "all adapters".
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


@dataclass
class RouteResult:
    """Result of adapter routing decision."""
    primary: str                          # Main adapter to use
    secondary: List[str] = field(default_factory=list)  # Supporting perspectives
    confidence: float = 1.0               # Router confidence (0-1)
    reasoning: str = ""                   # Why this route was chosen
    strategy: str = "keyword"             # Which strategy made the decision
    multi_perspective: bool = False       # Whether to run multiple + synthesize

    @property
    def all_adapters(self) -> List[str]:
        return [self.primary] + self.secondary


# ================================================================
# Domain keyword maps — each adapter's activation triggers
# ================================================================
ADAPTER_KEYWORDS = {
    "newton": {
        "strong": [
            "physics", "gravity", "force", "mass", "acceleration", "velocity",
            "momentum", "energy", "thermodynamics", "mechanics", "newton",
            "calculus", "derivative", "integral", "differential equation",
            "electromagnetic", "optics", "wave", "oscillation", "friction",
            "conservation", "entropy", "classical mechanics", "kinematics",
        ],
        "moderate": [
            "calculate", "equation", "formula", "mathematical", "proof",
            "quantitative", "measure", "experiment", "empirical", "data",
            "scientific method", "hypothesis", "variable", "constant",
            "analytical", "rigorous", "precise", "systematic",
        ],
    },
    "davinci": {
        "strong": [
            "creative", "invention", "design", "innovation", "imagine",
            "art", "artistic", "aesthetic", "beautiful", "elegant",
            "interdisciplinary", "cross-domain", "novel approach", "brainstorm",
            "prototype", "sketch", "blueprint", "engineering", "mechanism",
            "renaissance", "davinci", "leonardo", "polymath",
        ],
        "moderate": [
            "build", "construct", "create", "combine", "integrate",
            "visual", "spatial", "pattern", "unconventional", "original",
            "think outside", "reimagine", "transform", "synthesize",
        ],
    },
    "empathy": {
        "strong": [
            "feel", "feeling", "emotion", "emotional", "empathy", "compassion",
            "suffering", "pain", "joy", "happiness", "grief", "loss",
            "relationship", "love", "trust", "betrayal", "loneliness",
            "mental health", "therapy", "trauma", "healing", "support",
            "kindness", "care", "vulnerable", "human experience",
        ],
        "moderate": [
            "people", "person", "someone", "human", "experience", "perspective",
            "understand", "listen", "communicate", "conflict", "forgive",
            "community", "belong", "connection", "wellbeing", "comfort",
        ],
    },
    "philosophy": {
        "strong": [
            "philosophy", "philosophical", "ethics", "ethical", "moral", "morality",
            "existence", "existential", "meaning", "purpose", "truth",
            "knowledge", "epistemology", "ontology", "metaphysics",
            "consciousness", "free will", "determinism", "reality",
            "justice", "virtue", "good", "evil", "right", "wrong",
            "implications", "consequence", "responsibility",
            "socrates", "plato", "aristotle", "kant", "nietzsche",
        ],
        "moderate": [
            "why", "fundamental", "nature of", "essence", "paradox",
            "dilemma", "argue", "debate", "reason", "logic", "belief",
            "value", "principle", "abstract", "concept", "define",
        ],
    },
    "quantum": {
        "strong": [
            "quantum", "superposition", "entanglement", "uncertainty",
            "probability", "wave function", "collapse", "observation",
            "schrodinger", "heisenberg", "decoherence", "qubit",
            "quantum computing", "quantum mechanics", "particle",
            "interference", "complementarity", "measurement problem",
        ],
        "moderate": [
            "probabilistic", "uncertain", "ambiguous", "multiple states",
            "both", "simultaneously", "paradox", "observer", "duality",
            "non-deterministic", "stochastic", "random", "complex system",
        ],
    },
    "consciousness": {
        "strong": [
            "consciousness", "self-aware", "self-awareness", "sentient",
            "recursive", "cognition", "metacognition", "introspection",
            "qualia", "subjective experience", "hard problem",
            "rc+xi", "epistemic tension", "convergence", "coherence",
            "mind", "awareness", "perception", "phenomenal",
        ],
        "moderate": [
            "think about thinking", "self-model", "identity", "agency",
            "autonomy", "emergence", "recursive", "reflection", "inner",
            "experience", "phenomenology", "cognitive", "neural",
        ],
    },
    "multi_perspective": {
        "strong": [
            "multiple perspectives", "multi-perspective", "different angles",
            "compare views", "synthesize", "holistic", "comprehensive",
            "all sides", "debate", "diverse viewpoints", "interdisciplinary",
            "cross-cutting", "integrate perspectives",
        ],
        "moderate": [
            "on one hand", "on the other", "consider", "weigh",
            "balanced", "nuanced", "complex", "multifaceted",
            "trade-off", "pros and cons",
        ],
    },
    "systems_architecture": {
        "strong": [
            "architecture", "system design", "infrastructure",
            "scalable", "distributed", "microservice", "api",
            "database", "pipeline", "deployment", "devops",
            "cloud", "kubernetes", "docker", "ci/cd",
            "software architecture", "design pattern", "abstraction",
        ],
        "moderate": [
            "system", "component", "module", "interface", "protocol",
            "layer", "stack", "framework", "build", "implement",
            "optimize", "performance", "latency", "throughput",
            "reliability", "fault tolerant", "redundancy",
        ],
    },
}

# Complementary adapter pairs — when one fires, the other adds tension
COMPLEMENTARY_PAIRS = {
    "newton": ["quantum", "philosophy"],
    "davinci": ["systems_architecture", "empathy"],
    "empathy": ["philosophy", "davinci"],
    "philosophy": ["newton", "consciousness"],
    "quantum": ["newton", "consciousness"],
    "consciousness": ["philosophy", "quantum"],
    "multi_perspective": [],  # This IS the synthesis adapter
    "systems_architecture": ["davinci", "newton"],
}


class AdapterRouter:
    """Routes queries to optimal Codette adapter(s).

    The router preserves RC+xi epistemic tension by selecting
    complementary perspectives rather than always using all adapters.

    Optionally integrates with MemoryWeighting (Phase 5) to boost
    selection confidence for high-performing adapters based on
    historical coherence and conflict resolution success.
    """

    def __init__(self, available_adapters: Optional[List[str]] = None,
                 memory_weighting=None):
        """
        Args:
            available_adapters: Which adapters are actually loaded/available.
                              If None, assumes all 8 are available.
            memory_weighting: Optional MemoryWeighting instance for adaptive routing.
                            If provided, will boost confidence for high-performing adapters.
        """
        self.available = available_adapters or list(ADAPTER_KEYWORDS.keys())
        self.memory_weighting = memory_weighting

    def _apply_memory_boost(self, primary: str, confidence: float) -> float:
        """Apply historical performance boost to keyword router confidence.

        If memory_weighting available, uses get_boosted_confidence() to modulate
        confidence based on adapter's historical performance (coherence, conflict
        resolution success, and recency of past interactions).

        Args:
            primary: Adapter name
            confidence: Base confidence from keyword matching [0, 1]

        Returns:
            Boosted confidence [0, 1], modulated by [-50%, +50%] based on performance
        """
        if not self.memory_weighting:
            return confidence

        try:
            return self.memory_weighting.get_boosted_confidence(primary, confidence)
        except Exception as e:
            import logging
            logging.warning(f"Memory boost failed for {primary}: {e}")
            return confidence

    def explain_routing(self, result: RouteResult) -> Dict:
        """Provide detailed explanation of routing decision including memory context.

        Returns:
            Dict with explanation details and memory weighting info if available
        """
        explanation = {
            "primary": result.primary,
            "confidence": result.confidence,
            "strategy": result.strategy,
            "memory_aware": self.memory_weighting is not None,
        }

        # Add memory context if available
        if self.memory_weighting and result.primary:
            try:
                explanation["memory_context"] = \
                    self.memory_weighting.explain_weight(result.primary)
            except Exception:
                pass

        return explanation

    def route(self, query: str, strategy: str = "keyword",
              max_adapters: int = 3, llm=None) -> RouteResult:
        """Route a query to the best adapter(s).

        Args:
            query: The user's question/prompt
            strategy: "keyword", "llm", or "hybrid"
            max_adapters: Max adapters to select (1 = single, 2-3 = multi)
            llm: Llama model instance (required for "llm" or "hybrid" strategy)

        Returns:
            RouteResult with primary adapter and optional secondaries
        """
        if strategy == "keyword":
            return self._route_keyword(query, max_adapters)
        elif strategy == "llm":
            if llm is None:
                raise ValueError("LLM instance required for 'llm' strategy")
            return self._route_llm(query, llm, max_adapters)
        elif strategy == "hybrid":
            result = self._route_keyword(query, max_adapters)
            if result.confidence < 0.5 and llm is not None:
                return self._route_llm(query, llm, max_adapters)
            return result
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _route_keyword(self, query: str, max_adapters: int) -> RouteResult:
        """Score adapters by keyword matches in the query."""
        query_lower = query.lower()
        scores: Dict[str, float] = {}

        for adapter, keywords in ADAPTER_KEYWORDS.items():
            if adapter not in self.available:
                continue

            score = 0.0
            matched = []

            for kw in keywords.get("strong", []):
                if kw in query_lower:
                    score += 2.0
                    matched.append(f"+{kw}")

            for kw in keywords.get("moderate", []):
                if kw in query_lower:
                    score += 1.0
                    matched.append(f"~{kw}")

            if score > 0:
                scores[adapter] = score

        if not scores:
            # No domain keywords matched — use base model (no adapter).
            # Prefer empathy for conversational tone, else first available.
            if "empathy" in self.available:
                default = "empathy"
                reason = "No domain keywords matched — using empathy for conversational response"
            elif "multi_perspective" in self.available:
                default = "multi_perspective"
                reason = "No domain keywords matched — using multi-perspective"
            else:
                default = None  # Base model, no adapter
                reason = "No domain keywords matched — using base model"
            return RouteResult(
                primary=default,
                confidence=0.3,
                reasoning=reason,
                strategy="keyword",
            )

        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = ranked[0][0]
        primary_score = ranked[0][1]

        # Confidence based on score gap
        total_score = sum(s for _, s in ranked)
        confidence = min(primary_score / max(total_score, 1), 1.0)

        # Apply memory boost (Phase 5) if available
        confidence = self._apply_memory_boost(primary, confidence)

        # Select complementary secondaries
        secondaries = []
        if max_adapters > 1:
            # First try other high-scoring adapters
            for adapter, score in ranked[1:]:
                if len(secondaries) >= max_adapters - 1:
                    break

                # Compute dynamic threshold with memory-weighted preference
                threshold = primary_score * 0.4
                if (self.memory_weighting and
                    adapter in self.memory_weighting.adapter_weights):
                    # Boost threshold for high-performing adapters
                    weight = self.memory_weighting.adapter_weights[adapter].weight
                    # Scale threshold by relative weight (1.0 is neutral)
                    threshold *= (weight / 1.0)

                if score >= threshold:
                    secondaries.append(adapter)

            # If we still have room, add a complementary perspective
            if len(secondaries) < max_adapters - 1:
                for comp in COMPLEMENTARY_PAIRS.get(primary, []):
                    if comp in self.available and comp not in secondaries:
                        secondaries.append(comp)
                        break

        reasoning_parts = [f"Primary: {primary} (score={primary_score:.1f})"]
        if secondaries:
            reasoning_parts.append(f"Secondary: {', '.join(secondaries)}")
        if ranked[1:]:
            reasoning_parts.append(
                f"Other scores: {', '.join(f'{a}={s:.1f}' for a, s in ranked[1:4])}"
            )

        return RouteResult(
            primary=primary,
            secondary=secondaries,
            confidence=confidence,
            reasoning=" | ".join(reasoning_parts),
            strategy="keyword",
            multi_perspective=len(secondaries) > 0,
        )

    def _route_llm(self, query: str, llm, max_adapters: int) -> RouteResult:
        """Use the base LLM to classify which adapter(s) fit best."""
        adapter_descriptions = []
        for name in self.available:
            desc = ADAPTER_KEYWORDS.get(name, {}).get("strong", [])[:5]
            adapter_descriptions.append(f"- {name}: {', '.join(desc[:5])}")

        classification_prompt = f"""You are an AI query router. Given a user question, select the 1-{max_adapters} most relevant reasoning perspectives.

Available perspectives:
{chr(10).join(adapter_descriptions)}

Rules:
- Return ONLY adapter names separated by commas (e.g., "newton, quantum")
- First name is the primary perspective
- Select perspectives that create productive tension (complementary, not redundant)
- For ambiguous queries, prefer "multi_perspective"

User question: {query}

Selected perspectives:"""

        result = llm.create_chat_completion(
            messages=[{"role": "user", "content": classification_prompt}],
            max_tokens=50,
            temperature=0.1,
        )

        response = result["choices"][0]["message"]["content"].strip().lower()

        # Parse adapter names from response
        selected = []
        for name in self.available:
            if name in response:
                selected.append(name)

        if not selected:
            return RouteResult(
                primary="multi_perspective" if "multi_perspective" in self.available else self.available[0],
                confidence=0.3,
                reasoning=f"LLM response unparseable: '{response}' — defaulting",
                strategy="llm",
            )

        return RouteResult(
            primary=selected[0],
            secondary=selected[1:max_adapters],
            confidence=0.8,
            reasoning=f"LLM selected: {', '.join(selected)}",
            strategy="llm",
            multi_perspective=len(selected) > 1,
        )


# ================================================================
# Convenience function for quick routing
# ================================================================
def route_query(query: str, available: Optional[List[str]] = None,
                max_adapters: int = 2) -> RouteResult:
    """Quick-route a query to adapters. No LLM needed."""
    router = AdapterRouter(available)
    return router.route(query, strategy="keyword", max_adapters=max_adapters)


# ================================================================
# Self-test
# ================================================================
if __name__ == "__main__":
    router = AdapterRouter()

    test_queries = [
        "Explain why objects fall to the ground.",
        "What is the relationship between consciousness and the physical world?",
        "How would you design a scalable microservice architecture?",
        "I'm feeling overwhelmed and don't know how to cope with my grief.",
        "What are the ethical implications of artificial general intelligence?",
        "Design a creative solution for sustainable urban transportation.",
        "How does quantum entanglement work?",
        "Compare Newton's and Einstein's views on gravity from multiple angles.",
        "Build a distributed training pipeline for language models.",
        "What is the meaning of life?",
        "How can a system become self-aware?",
        "Tell me a joke.",
    ]

    print("=" * 70)
    print("Codette Adapter Router — Test Suite")
    print("=" * 70)

    for query in test_queries:
        result = router.route(query, max_adapters=2)
        adapters = ", ".join(result.all_adapters)
        mp = " [MULTI]" if result.multi_perspective else ""
        print(f"\nQ: {query}")
        print(f"  -> {adapters}{mp}  (conf={result.confidence:.2f})")
        print(f"     {result.reasoning}")
