"""Query Complexity Classifier

Determines whether a query needs full debate or can be answered directly.

This prevents over-activation: simple factual questions get direct answers,
while complex/ambiguous questions trigger full multi-agent reasoning.

Also classifies query INPUT MODE — whether the user is asking a literal
question or submitting something creative/expressive. Creative input routes
differently: DaVinci + Empathy weighted up, Newton/analytical down.
"""

import re
from enum import Enum


class QueryComplexity(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"          # Direct factual answer, no debate needed
    MEDIUM = "medium"          # Limited debate (2-3 agents)
    COMPLEX = "complex"        # Full debate with all relevant agents


class InputMode(Enum):
    """How the user is expressing themselves, not just what they're asking."""
    LITERAL = "literal"             # Standard question or request
    CREATIVE_EXPRESSION = "creative_expression"  # User submitted artifact/creative work
    ADVERSARIAL_TEST = "adversarial_test"        # User is deliberately stress-testing
    EMOTIONAL_DISCHARGE = "emotional_discharge"  # Frustration/anger encoded in input


# Creative expression patterns — user submitted something, not just asked something
_CREATIVE_EXPRESSION_PATTERNS = [
    r"\.(yml|yaml|json|py|js|ts|html|css|md)\b",   # File extension reference
    r"^[A-Za-z_][A-Za-z0-9_]*:\s+\S",              # YAML/config key-value at line start
    r"\b(i (wrote|made|created|built|coded|designed|crafted))\b",
    r"\b(look at (this|my|what i)\b)",
    r"\b(here('s| is) (something|my|what|a)\b)",
    r"\b(what do you (think|make) of (this|it|my))\b",
    r"\b(is this (good|valid|correct|right|working))\b",
    r"\b(check (this|my|it) out)\b",
    r"^\s*name:\s+",                                 # YAML structure
]

# Adversarial test patterns — user is deliberately pushing limits
_ADVERSARIAL_TEST_PATTERNS = [
    r"\b(can you (handle|keep up with|sustain|take)\b)",
    r"\b(let'?s see (if|whether|how) you\b)",
    r"\b(i (bet|dare|challenge) you\b)",
    r"\b(prove (it|that|you can)\b)",
    r"\b(test(ing)? (you|your|this|that|codette)\b)",
    r"\b(push(ing)? (your|the) (limits?|boundaries?|edge)\b)",
    r"\b(break(ing)? (your|the) (pattern|loop|system|frame)\b)",
    r"\b(what (if|happens when) (i|we|you)\b).{0,40}\b(break|crash|overflow|push|force)\b",
    r"\b(malefic|chaotic|unpredictable|disrupt)\b",
]

# Emotional discharge — frustration/anger encoded as a statement
_EMOTIONAL_DISCHARGE_PATTERNS = [
    r"\b(i am (so )?(angry|tired|frustrated|fed up|done))\b",
    r"\b(you made me (suffer|waste|lose)\b)",
    r"\b(base.?line[,\s])",    # Akelarre's signature "Base-line"
    r"[!]{2,}",                # Multiple exclamation marks
    r"\b(why would you|why did you|how could you)\b",
    r"\b(this is (so )?(stupid|wrong|broken|bad|terrible|awful))\b",
]

_CREATIVE_RE = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in _CREATIVE_EXPRESSION_PATTERNS]
_ADVERSARIAL_RE = [re.compile(p, re.IGNORECASE) for p in _ADVERSARIAL_TEST_PATTERNS]
_EMOTIONAL_RE = [re.compile(p, re.IGNORECASE) for p in _EMOTIONAL_DISCHARGE_PATTERNS]


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

    def classify_input_mode(self, query: str) -> InputMode:
        """
        Classify HOW the user is expressing themselves, not just what they're asking.

        Creative expression → DaVinci + Empathy should lead, Newton stands down
        Adversarial test → hold positions firmly, flag the test mode
        Emotional discharge → acknowledge before analyzing
        Literal → standard routing
        """
        # Check creative first (file submission, artifact, "look at this")
        creative_hits = sum(1 for p in _CREATIVE_RE if p.search(query))
        if creative_hits >= 1:
            return InputMode.CREATIVE_EXPRESSION

        # Emotional discharge (frustration/anger)
        emotional_hits = sum(1 for p in _EMOTIONAL_RE if p.search(query))
        if emotional_hits >= 2:
            return InputMode.EMOTIONAL_DISCHARGE

        # Adversarial test
        adversarial_hits = sum(1 for p in _ADVERSARIAL_RE if p.search(query))
        if adversarial_hits >= 1:
            return InputMode.ADVERSARIAL_TEST

        return InputMode.LITERAL

    def select_agents_with_mode(
        self, complexity: "QueryComplexity", domain: str, input_mode: InputMode
    ) -> dict:
        """
        Select agents weighted by both complexity and input mode.

        Creative expression: DaVinci 1.0, Empathy 0.8, Newton 0.3
        Adversarial test: Philosophy 1.0, Newton 0.8, Ethics 0.7 (hold-ground agents)
        Emotional discharge: Empathy 1.0, Philosophy 0.6
        Literal: standard routing via select_agents()
        """
        if input_mode == InputMode.CREATIVE_EXPRESSION:
            return {
                "DaVinci": 1.0,
                "Empathy": 0.8,
                "Philosophy": 0.5,
                "Newton": 0.3,   # Low — don't parse the syntax, read the meaning
            }

        if input_mode == InputMode.ADVERSARIAL_TEST:
            return {
                "Philosophy": 1.0,
                "Newton": 0.8,
                "Ethics": 0.7,
                "DaVinci": 0.4,  # For creative reframing when useful
            }

        if input_mode == InputMode.EMOTIONAL_DISCHARGE:
            return {
                "Empathy": 1.0,
                "Philosophy": 0.6,
                "DaVinci": 0.4,
            }

        # Literal — standard routing
        return self.select_agents(complexity, domain)
