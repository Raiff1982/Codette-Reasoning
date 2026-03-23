"""Query Complexity Classifier

Determines whether a query needs full debate or can be answered directly.

This prevents over-activation: simple factual questions get direct answers,
while complex/ambiguous questions trigger full multi-agent reasoning.
"""

import re
from enum import Enum


class QueryComplexity(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"          # Direct factual answer, no debate needed
    MEDIUM = "medium"          # Limited debate (2-3 agents)
    COMPLEX = "complex"        # Full debate with all relevant agents


class QueryClassifier:
    """Classify query complexity to determine reasoning depth."""

    # Factual keywords (SIMPLE queries)
    FACTUAL_PATTERNS = [
        r"what is the (speed|velocity|mass|temperature|distance|height|width|size|weight|color|pressure|density|definition|meaning|name)",
        r"define ",                 # "Define entropy"
        r"what (year|date|time) ",  # "What year did..."
        r"how fast (is|can)",       # "How fast is..." / "How fast can..."
        r"how high is",
        r"how long is",
        r"what (color|size|shape)",
        r"who (is|wrote|created|invented|discovered|founded)",  # "Who is Einstein? Who wrote Romeo?"
        r"where (is|are)",          # "Where is the capital?"
        r"what is the (capital|president|king|queen|currency|language|population)",  # Geographic facts
        r"list of ",                # "List of elements"
        r"formula for",             # "Formula for..."
        r"calculate ",              # "Calculate..."
    ]

    # Ambiguous keywords (COMPLEX queries)
    AMBIGUOUS_PATTERNS = [
        r"could .* really",           # "Could machines really be conscious?"
        r"might .* ever",             # "Might we ever understand consciousness?"
        r"can .* (truly|really)",     # More specific: "Can machines truly be conscious?"
        r"what does .* (really )?mean",  # Interpretation of meaning
        r"why (do|does) (we|they|people)",  # Why questions (explanation seeking)
        r"is .* the (future|destiny|past|foundation|basis|purpose)",  # "Is AI the future?"
        r"can .* (be|become|achieve)",  # "Can machines achieve consciousness?" (also caught by subjective)
    ]

    # Ethics/Philosophy keywords (COMPLEX queries)
    ETHICS_PATTERNS = [
        r"should (we |i |ai|society|companies)",
        r"is it (right|wrong|ethical|moral)",
        r"is it (good|bad|fair)",
        r"ought",
        r"morally?",
        r"ethics?",
        r"value of",
        r"meaning of",
        r"purpose of",
        r"how should (we |ai|companies|society)",  # "How should we govern"
        r"balance .* (freedom|individual|collective|good|rights)",  # Balancing values
    ]

    # Multi-domain keywords (COMPLEX queries)
    # Note: Pure factual relationships (e.g., "energy and mass") are NOT complex
    # Only philosophical/semantic relationships are complex
    MULTIDOMAIN_PATTERNS = [
        r"relationship .*(consciousness|meaning|identity|knowledge|reality)",  # Philosophical relationships
        r"interaction .*(human|society|culture|mind|consciousness)",
        r"(challenge|question) .* (understanding|reality|belief|knowledge)",  # Foundational questions
    ]

    # Subjective/opinion keywords (COMPLEX queries)
    SUBJECTIVE_PATTERNS = [
        r"is .*consciousness",         # Defining consciousness
        r"do you (think|believe)",     # Asking for opinion
        r"perspective",
        r"what is (the )?nature of",   # "What is the nature of free will?"
        r"can .* (be|become) (measured|quantified|understood)",  # Epistemology: "Can experience be measured?"
    ]

    # Semantic complexity signals — short queries that are actually complex
    # despite low word count. These override the word-count heuristic.
    SEMANTIC_COMPLEX_PATTERNS = [
        r"fix\s+\w+\s*(leak|bug|crash|error|issue|problem|race|deadlock|overflow)",
        r"debug\s+\w+",
        r"(refactor|redesign|rearchitect)\s+",
        r"(optimize|performance)\s+\w+",
        r"(migrate|upgrade)\s+\w+",
        r"why\s+(is|does|did|doesn't|won't|can't)\s+",
        r"how\s+to\s+(prevent|avoid|handle|recover)\s+",
        r"trade.?offs?\s+(between|of|in)",
        r"(compare|contrast|difference)\s+",
        r"what\s+causes?\s+",
        r"(root\s+cause|underlying|fundamental)\s+",
        r"(security|vulnerability|exploit)\s+",
        r"(scale|scaling|scalability)\s+",
        r"(concurrent|parallel|async|thread)\s+",
        r"(architect|design\s+pattern|anti.?pattern)\s+",
    ]

    def classify(self, query: str) -> QueryComplexity:
        """Classify query complexity.

        Args:
            query: The user query

        Returns:
            QueryComplexity level (SIMPLE, MEDIUM, or COMPLEX)

        Includes semantic complexity override: short queries with complex
        intent (e.g., "fix memory leak?") are promoted to MEDIUM or COMPLEX
        despite low word count.
        """
        query_lower = query.lower().strip()

        # SIMPLE: Pure factual queries
        if self._is_factual(query_lower):
            # But check if it has complexity markers too
            if self._has_ambiguity(query_lower) or self._has_ethics(query_lower):
                return QueryComplexity.COMPLEX
            return QueryComplexity.SIMPLE

        # COMPLEX: Ethics, philosophy, interpretation, multi-domain
        if self._has_ethics(query_lower):
            return QueryComplexity.COMPLEX
        if self._has_ambiguity(query_lower):
            return QueryComplexity.COMPLEX
        if self._has_multidomain(query_lower):
            return QueryComplexity.COMPLEX
        if self._has_subjective(query_lower):
            return QueryComplexity.COMPLEX

        # Semantic complexity override: short queries with complex signals
        # A 3-word query like "fix memory leak" needs MEDIUM, not SIMPLE
        if self._has_semantic_complexity(query_lower):
            word_count = len(query_lower.split())
            if word_count <= 5:
                return QueryComplexity.MEDIUM
            return QueryComplexity.COMPLEX

        # MEDIUM: Everything else
        return QueryComplexity.MEDIUM

    def _has_semantic_complexity(self, query: str) -> bool:
        """Check if a short query carries complex semantic intent."""
        return any(re.search(p, query) for p in self.SEMANTIC_COMPLEX_PATTERNS)

    def _is_factual(self, query: str) -> bool:
        """Check if query is direct factual question."""
        return any(re.search(pattern, query) for pattern in self.FACTUAL_PATTERNS)

    def _has_ambiguity(self, query: str) -> bool:
        """Check if query has ambiguity markers."""
        return any(re.search(pattern, query) for pattern in self.AMBIGUOUS_PATTERNS)

    def _has_ethics(self, query: str) -> bool:
        """Check if query involves ethics/philosophy."""
        return any(re.search(pattern, query) for pattern in self.ETHICS_PATTERNS)

    def _has_multidomain(self, query: str) -> bool:
        """Check if query spans multiple domains."""
        return any(re.search(pattern, query) for pattern in self.MULTIDOMAIN_PATTERNS)

    def _has_subjective(self, query: str) -> bool:
        """Check if query invites subjective reasoning."""
        return any(re.search(pattern, query) for pattern in self.SUBJECTIVE_PATTERNS)

    def select_agents(
        self, complexity: QueryComplexity, domain: str
    ) -> dict[str, float]:
        """Select agents and their weights based on complexity and domain.

        Args:
            complexity: Query complexity level
            domain: Detected query domain

        Returns:
            Dict mapping agent names to activation weights (0-1)
        """
        # All available agents with their domains
        all_agents = {
            "Newton": ["physics", "mathematics", "systems"],
            "Quantum": ["physics", "uncertainty", "systems"],
            "Philosophy": ["philosophy", "meaning", "consciousness"],
            "DaVinci": ["creativity", "systems", "innovation"],
            "Empathy": ["ethics", "consciousness", "meaning"],
            "Ethics": ["ethics", "consciousness", "meaning"],
        }

        domain_agents = all_agents

        if complexity == QueryComplexity.SIMPLE:
            # Simple queries: just the primary agent for the domain
            # Activate only 1 agent at full strength
            primary = self._get_primary_agent(domain)
            return {primary: 1.0}

        elif complexity == QueryComplexity.MEDIUM:
            # Medium queries: primary + 1-2 secondary agents
            # Soft gating with weighted influence
            primary = self._get_primary_agent(domain)
            secondaries = self._get_secondary_agents(domain, count=1)

            weights = {primary: 1.0}
            for secondary in secondaries:
                weights[secondary] = 0.6

            return weights

        else:  # COMPLEX
            # Complex queries: all relevant agents for domain + cross-domain
            # Full soft gating
            primary = self._get_primary_agent(domain)
            secondaries = self._get_secondary_agents(domain, count=2)
            cross_domain = self._get_cross_domain_agents(domain, count=1)

            weights = {primary: 1.0}
            for secondary in secondaries:
                weights[secondary] = 0.7
            for cross in cross_domain:
                weights[cross] = 0.4

            return weights

    def _get_primary_agent(self, domain: str) -> str:
        """Get the primary agent for a domain."""
        domain_map = {
            "physics": "Newton",
            "mathematics": "Newton",
            "creativity": "DaVinci",
            "ethics": "Ethics",
            "philosophy": "Philosophy",
            "meaning": "Philosophy",
            "consciousness": "Empathy",
            "uncertainty": "Quantum",
            "systems": "Newton",
        }
        return domain_map.get(domain, "Newton")

    def _get_secondary_agents(self, domain: str, count: int = 1) -> list[str]:
        """Get secondary agents for a domain."""
        domain_map = {
            "physics": ["Quantum", "DaVinci"],
            "mathematics": ["Quantum", "Philosophy"],
            "creativity": ["Quantum", "Empathy"],
            "ethics": ["Philosophy", "Empathy"],
            "philosophy": ["Empathy", "Ethics"],
            "meaning": ["Quantum", "DaVinci"],
            "consciousness": ["Philosophy", "Quantum"],
            "uncertainty": ["Philosophy", "DaVinci"],
            "systems": ["DaVinci", "Philosophy"],
        }
        candidates = domain_map.get(domain, ["Philosophy", "DaVinci"])
        return candidates[:count]

    def _get_cross_domain_agents(self, domain: str, count: int = 1) -> list[str]:
        """Get cross-domain agents (useful for all domains)."""
        # Philosophy and Empathy are useful everywhere
        candidates = ["Philosophy", "Empathy", "DaVinci"]
        return candidates[:count]
