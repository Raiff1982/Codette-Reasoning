"""
Reasoning Metrics - scores text quality across multiple dimensions.

Each dimension is scored 0.0-1.0 using concrete textual analysis:
regex patterns, keyword detection, sentence structure analysis,
word counts, and concept density measures.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Keyword / pattern banks
# ---------------------------------------------------------------------------

_TRANSITION_WORDS = {
    "therefore", "however", "moreover", "furthermore", "consequently",
    "nevertheless", "additionally", "specifically", "thus", "hence",
    "accordingly", "meanwhile", "similarly", "conversely", "likewise",
    "in contrast", "on the other hand", "as a result", "for example",
    "for instance", "in addition", "in particular", "in summary",
    "to illustrate", "that is", "notably", "indeed", "alternatively",
}

_EXAMPLE_MARKERS = {
    "for example", "for instance", "such as", "e.g.", "e.g.,",
    "consider", "imagine", "suppose", "like when", "think of",
    "analogy", "analogous", "metaphor", "illustration", "to illustrate",
    "case in point", "picture", "envision", "scenario",
}

_PERSPECTIVE_MARKERS = {
    "on the other hand", "from another perspective", "alternatively",
    "some argue", "others believe", "one view", "another view",
    "proponents", "opponents", "critics", "supporters",
    "different perspective", "counterargument", "counter-argument",
    "multiple perspectives", "various viewpoints", "diverse views",
    "some scholars", "other researchers", "in contrast",
    "conversely", "while some", "whereas others",
    "from a … standpoint", "from the standpoint",
    "different schools of thought", "competing theories",
    "pluralistic", "multifaceted",
}

_SCIENTIFIC_TERMS = {
    "hypothesis", "theory", "empirical", "variable", "correlation",
    "causation", "experiment", "observation", "evidence", "data",
    "quantitative", "qualitative", "statistical", "significant",
    "methodology", "systematic", "peer-reviewed", "replicable",
    "falsifiable", "paradigm", "model", "framework", "mechanism",
    "phenomenon", "equation", "entropy", "quantum", "relativity",
    "thermodynamic", "kinetic", "potential", "electromagnetic",
    "wavelength", "frequency", "spectrum", "molecular", "cellular",
    "neural", "cognitive", "algorithm", "computational", "stochastic",
    "deterministic", "probabilistic", "inference", "deduction",
    "induction", "axiom", "theorem", "coefficient", "parameter",
    "optimization", "convergence", "divergence", "gradient",
    "eigenvalue", "tensor", "vector", "scalar", "integral",
    "derivative", "differential", "asymptotic", "heuristic",
}

_ETHICAL_TERMS = {
    "ethical", "moral", "responsibility", "accountability", "fairness",
    "justice", "bias", "harm", "benefit", "consequence", "implication",
    "stakeholder", "rights", "duty", "obligation", "dilemma",
    "autonomy", "consent", "privacy", "transparency", "trust",
    "equity", "inclusion", "diversity", "sustainability",
    "well-being", "welfare", "dignity", "integrity", "virtue",
    "utilitarian", "deontological", "consequentialist", "normative",
    "values", "principles", "compassion", "empathy",
    "social impact", "unintended consequences",
}

_STRUCTURE_PATTERNS = [
    re.compile(r"^\s*\d+[\.\)]\s", re.MULTILINE),           # numbered list
    re.compile(r"^\s*[-*]\s", re.MULTILINE),                 # bullet list
    re.compile(r"^#{1,4}\s", re.MULTILINE),                  # markdown headings
    re.compile(r"\b(first|second|third|finally|lastly)\b", re.I),
    re.compile(r"\b(step\s+\d+|phase\s+\d+)\b", re.I),
    re.compile(r"\b(in conclusion|to summarize|in summary)\b", re.I),
    re.compile(r"\b(introduction|background|method|result|discussion|conclusion)\b", re.I),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _word_tokenize(text: str) -> List[str]:
    """Simple whitespace + punctuation tokeniser."""
    return re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*", text.lower())


def _sentences(text: str) -> List[str]:
    """Split text into sentences (simple heuristic)."""
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in parts if len(s) > 2]


def _unique_word_ratio(words: List[str]) -> float:
    if not words:
        return 0.0
    return len(set(words)) / len(words)


def _sigmoid(x: float, midpoint: float = 0.0, steepness: float = 1.0) -> float:
    """Soft clamping via logistic function, output in (0, 1)."""
    try:
        return 1.0 / (1.0 + math.exp(-steepness * (x - midpoint)))
    except OverflowError:
        return 0.0 if x < midpoint else 1.0


def _keyword_density(words: List[str], keyword_set: set) -> float:
    """Fraction of *unique* keywords from the set that appear in words."""
    if not keyword_set:
        return 0.0
    word_set = set(words)
    hits = word_set & keyword_set
    return len(hits) / len(keyword_set)


def _phrase_count(text: str, phrases: set) -> int:
    """Count how many distinct phrases from *phrases* appear in text."""
    text_lower = text.lower()
    return sum(1 for p in phrases if p in text_lower)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class ReasoningMetrics:
    """Score a reasoning response on multiple quality dimensions."""

    # Default weights for the composite score
    DEFAULT_WEIGHTS: Dict[str, float] = {
        "clarity": 0.15,
        "structure": 0.15,
        "depth": 0.15,
        "examples": 0.10,
        "multi_perspective": 0.10,
        "scientific_rigor": 0.15,
        "ethical_awareness": 0.10,
        "coherence": 0.10,
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or dict(self.DEFAULT_WEIGHTS)

    # -- individual scorers ------------------------------------------------

    def _score_clarity(self, text: str, words: List[str], sents: List[str]) -> float:
        """
        Clarity: readable sentences, moderate length, good vocabulary variety.
        """
        if not sents:
            return 0.0

        # Average sentence length (ideal ~15-25 words)
        avg_sent_len = len(words) / len(sents)
        len_score = 1.0 - min(abs(avg_sent_len - 20) / 20, 1.0)

        # Vocabulary diversity (unique / total)
        diversity = _unique_word_ratio(words)

        # Penalise very short responses
        length_penalty = min(len(words) / 50, 1.0)

        # Transition word usage (smooths reading)
        transition_count = _phrase_count(text, _TRANSITION_WORDS)
        transition_score = min(transition_count / max(len(sents) * 0.3, 1), 1.0)

        score = (
            0.35 * len_score
            + 0.25 * diversity
            + 0.20 * length_penalty
            + 0.20 * transition_score
        )
        return round(min(max(score, 0.0), 1.0), 4)

    def _score_structure(self, text: str, sents: List[str]) -> float:
        """
        Structure: numbered/bulleted lists, headings, step markers,
        paragraph breaks, logical ordering cues.
        """
        if not text.strip():
            return 0.0

        pattern_hits = sum(1 for p in _STRUCTURE_PATTERNS if p.search(text))
        pattern_score = min(pattern_hits / 4, 1.0)  # 4+ patterns = perfect

        # Paragraph structure (multiple newline-separated blocks)
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        para_score = min(len(paragraphs) / 4, 1.0)

        # Sentence count contribution (longer = more structured opportunity)
        sent_score = min(len(sents) / 8, 1.0)

        score = 0.50 * pattern_score + 0.25 * para_score + 0.25 * sent_score
        return round(min(max(score, 0.0), 1.0), 4)

    def _score_depth(self, text: str, words: List[str], sents: List[str]) -> float:
        """
        Depth: word count, concept density, vocabulary richness.
        """
        if not words:
            return 0.0

        # Word count (sigmoid centred at ~200 words)
        wc_score = _sigmoid(len(words), midpoint=200, steepness=0.015)

        # Long words (>= 8 chars) as proxy for complex vocabulary
        long_words = [w for w in words if len(w) >= 8]
        complexity = min(len(long_words) / max(len(words) * 0.15, 1), 1.0)

        # Unique concept density: unique 3+-letter words / total words
        concepts = set(w for w in words if len(w) >= 3)
        concept_density = min(len(concepts) / max(len(words) * 0.5, 1), 1.0)

        # Sentence count depth
        sent_depth = min(len(sents) / 10, 1.0)

        score = (
            0.30 * wc_score
            + 0.25 * complexity
            + 0.25 * concept_density
            + 0.20 * sent_depth
        )
        return round(min(max(score, 0.0), 1.0), 4)

    def _score_examples(self, text: str) -> float:
        """
        Examples: presence of illustrative examples, analogies, scenarios.
        """
        if not text.strip():
            return 0.0

        marker_hits = _phrase_count(text, _EXAMPLE_MARKERS)

        # Quoted examples
        quotes = len(re.findall(r'"[^"]{5,}"', text))

        # Code / formula blocks
        code_blocks = len(re.findall(r'```', text)) // 2
        inline_code = len(re.findall(r'`[^`]+`', text))

        # Concrete numbers / data points
        numbers = len(re.findall(r'\b\d+(?:\.\d+)?(?:\s*(?:%|kg|m|km|s|ms|Hz|J|W|N))\b', text))

        total_evidence = marker_hits + quotes + code_blocks + inline_code + numbers
        score = min(total_evidence / 5, 1.0)  # 5+ pieces = full score
        return round(min(max(score, 0.0), 1.0), 4)

    def _score_multi_perspective(self, text: str) -> float:
        """
        Multi-perspective: references to multiple viewpoints, balanced discussion.
        """
        if not text.strip():
            return 0.0

        perspective_hits = _phrase_count(text, _PERSPECTIVE_MARKERS)

        # "but" / "however" / "although" as hedging signals
        hedge_words = len(re.findall(
            r'\b(?:but|however|although|though|yet|still|nonetheless|'
            r'notwithstanding|despite|regardless)\b',
            text, re.I
        ))

        # Question marks (self-questioning / Socratic style)
        questions = text.count('?')

        total = perspective_hits * 2 + hedge_words + questions * 0.5
        score = min(total / 8, 1.0)
        return round(min(max(score, 0.0), 1.0), 4)

    def _score_scientific_rigor(self, text: str, words: List[str]) -> float:
        """
        Scientific rigor: precise terminology, quantitative language,
        references to evidence/method.
        """
        if not words:
            return 0.0

        sci_hits = sum(1 for w in set(words) if w in _SCIENTIFIC_TERMS)
        term_score = min(sci_hits / 6, 1.0)  # 6+ unique scientific terms

        # Quantitative expressions
        quant = len(re.findall(
            r'\b\d+(?:\.\d+)?(?:\s*(?:x|times|percent|%|ratio|factor))\b',
            text, re.I
        ))
        quant += len(re.findall(r'[<>=]+\s*\d', text))
        quant_score = min(quant / 3, 1.0)

        # Causal / evidence language
        causal = len(re.findall(
            r'\b(?:because|caused? by|leads? to|results? in|due to|'
            r'evidence suggests?|research shows?|studies indicate|'
            r'according to|demonstrated|proven|measured)\b',
            text, re.I
        ))
        causal_score = min(causal / 4, 1.0)

        score = 0.45 * term_score + 0.25 * causal_score + 0.30 * quant_score
        return round(min(max(score, 0.0), 1.0), 4)

    def _score_ethical_awareness(self, text: str, words: List[str]) -> float:
        """
        Ethical awareness: considers implications, fairness, harm, responsibility.
        """
        if not words:
            return 0.0

        eth_hits = sum(1 for w in set(words) if w in _ETHICAL_TERMS)
        term_score = min(eth_hits / 4, 1.0)

        # Implication / consequence language
        impl = len(re.findall(
            r'\b(?:implication|consequence|impact|risk|concern|'
            r'should|ought|must consider|raises questions|'
            r'responsible|accountable|careful|caution)\b',
            text, re.I
        ))
        impl_score = min(impl / 4, 1.0)

        # Stakeholder awareness
        stakeholder = len(re.findall(
            r'\b(?:people|society|community|individual|user|patient|'
            r'citizen|public|vulnerable|marginalized|affected)\b',
            text, re.I
        ))
        stake_score = min(stakeholder / 3, 1.0)

        score = 0.40 * term_score + 0.35 * impl_score + 0.25 * stake_score
        return round(min(max(score, 0.0), 1.0), 4)

    def _score_coherence(self, text: str, sents: List[str], words: List[str]) -> float:
        """
        Coherence: adjacent sentences share vocabulary, topic consistency.
        """
        if len(sents) < 2:
            return 0.5  # neutral for very short texts

        # Lexical overlap between adjacent sentences
        overlaps = []
        for i in range(len(sents) - 1):
            w1 = set(_word_tokenize(sents[i]))
            w2 = set(_word_tokenize(sents[i + 1]))
            if w1 | w2:
                overlaps.append(len(w1 & w2) / len(w1 | w2))
            else:
                overlaps.append(0.0)
        avg_overlap = sum(overlaps) / len(overlaps) if overlaps else 0.0
        # Ideal overlap is moderate (0.1-0.3); too high = repetitive
        overlap_score = 1.0 - abs(avg_overlap - 0.2) / 0.4
        overlap_score = max(overlap_score, 0.0)

        # Pronoun / referent continuity
        pronoun_count = len(re.findall(
            r'\b(?:this|that|these|those|it|they|its|their|such|said)\b',
            text, re.I
        ))
        ref_score = min(pronoun_count / max(len(sents), 1) / 1.5, 1.0)

        score = 0.60 * overlap_score + 0.40 * ref_score
        return round(min(max(score, 0.0), 1.0), 4)

    # -- public API --------------------------------------------------------

    def score_reasoning(self, text: str) -> Dict[str, float]:
        """Score a reasoning response on multiple dimensions.

        Returns dict with scores 0.0-1.0 for:
        - clarity, structure, depth, examples, multi_perspective,
          scientific_rigor, ethical_awareness, coherence, overall
        """
        words = _word_tokenize(text)
        sents = _sentences(text)

        scores: Dict[str, float] = {
            "clarity": self._score_clarity(text, words, sents),
            "structure": self._score_structure(text, sents),
            "depth": self._score_depth(text, words, sents),
            "examples": self._score_examples(text),
            "multi_perspective": self._score_multi_perspective(text),
            "scientific_rigor": self._score_scientific_rigor(text, words),
            "ethical_awareness": self._score_ethical_awareness(text, words),
            "coherence": self._score_coherence(text, sents, words),
        }

        # Weighted composite
        total_weight = sum(self.weights.get(k, 0) for k in scores)
        if total_weight > 0:
            overall = sum(
                scores[k] * self.weights.get(k, 0) for k in scores
            ) / total_weight
        else:
            overall = sum(scores.values()) / len(scores)

        scores["overall"] = round(overall, 4)
        scores["word_count"] = len(words)
        scores["sentence_count"] = len(sents)
        return scores

    def score_batch(self, texts: List[str]) -> List[Dict[str, float]]:
        """Score a batch of responses."""
        return [self.score_reasoning(t) for t in texts]

    def compare(self, text_a: str, text_b: str) -> Dict[str, Dict[str, float]]:
        """Compare two responses side-by-side."""
        sa = self.score_reasoning(text_a)
        sb = self.score_reasoning(text_b)
        delta = {k: round(sb[k] - sa[k], 4) for k in sa if isinstance(sa[k], (int, float))}
        return {"baseline": sa, "candidate": sb, "delta": delta}
