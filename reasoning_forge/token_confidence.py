"""
Token-Level Confidence Scoring Engine

Synthesizes four confidence signals to rate individual claims:
1. Semantic Confidence — Confidence markers in text ("I'm confident that...", "arguably...")
2. Attentional Confidence — Semantic overlap with other agents' responses
3. Probabilistic Confidence — Token-level probabilities from LLM logits
4. Integrated Learning Signal — Historical coherence from past similar responses

Author: Claude Code
"""

import re
import time
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Confidence markers (grouped by confidence level)
CONFIDENCE_MARKERS = {
    "high": [
        r"\bi['\"]?m confident\b",
        r"\bdefinitively\b",
        r"\bclearly\b",
        r"\bunambiguously\b",
        r"\bcertainly\b",
        r"\bwithout doubt\b",
        r"\bno question\b",
        r"\bproven\b",
        r"\bestablished fact\b",
    ],
    "medium": [
        r"\bi argue\b",
        r"\b(it appears|it seems)\b",
        r"\breasonably\b",
        r"\barguably\b",
        r"\blikely\b",
        r"\bprobably\b",
        r"\bin my view\b",
        r"\bi think\b",
        r"\bi believe\b",
        r"\bfrom my perspective\b",
    ],
    "low": [
        r"\b(it['\"]?s possible|it could be)\b",
        r"\bone could say\b",
        r"\bperhaps\b",
        r"\bmaybe\b",
        r"\buncertain\b",
        r"\bi['\"]?m not sure\b",
        r"\ballegedly\b",
        r"\bseemingly\b",
        r"\bapparently\b",
        r"\bwhoa\b",
    ],
}

# Compile regex patterns for performance
_MARKER_PATTERNS = {}
for level, markers in CONFIDENCE_MARKERS.items():
    _MARKER_PATTERNS[level] = [re.compile(m, re.IGNORECASE) for m in markers]


@dataclass
class ClaimSegment:
    """A single claim extracted from an agent's response."""

    text: str  # The claim text
    start_idx: int  # Position in original response
    end_idx: int  # End position
    confidence: float  # Aggregate confidence [0, 1]
    semantic_conf: float  # From markers
    attentional_conf: float  # From semantic overlap with peers
    probabilistic_conf: float  # From logits (if available)
    learning_signal: float  # From historical coherence
    agent_name: str = ""  # Which agent produced this
    debate_round: int = 0


@dataclass
class TokenConfidenceScore:
    """Per-token confidence analysis for a full response."""

    agent_name: str
    response_text: str
    token_scores: List[float]  # [0, 1] per token (or sentence)
    claims: List[ClaimSegment]
    semantic_confidence_dict: Dict[int, float]  # Token idx -> semantic confidence
    attentional_confidence_dict: Dict[int, float]  # Token idx -> attentional confidence
    probabilistic_confidence_dict: Dict[int, float]  # Token idx -> logit probability
    learning_signal_dict: Dict[int, float]  # Token idx -> learning signal
    composite_scores: Dict[int, float]  # Token idx -> composite [α, β, γ, δ]
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> Dict:
        """Serialize for storage."""
        return {
            "agent_name": self.agent_name,
            "response_text": self.response_text[:500],
            "mean_token_confidence": sum(self.token_scores) / max(len(self.token_scores), 1),
            "claims_count": len(self.claims),
            "claims": [
                {
                    "text": c.text,
                    "confidence": c.confidence,
                    "semantic_conf": c.semantic_conf,
                    "attentional_conf": c.attentional_conf,
                    "probabilistic_conf": c.probabilistic_conf,
                    "learning_signal": c.learning_signal,
                }
                for c in self.claims
            ],
        }


class TokenConfidenceEngine:
    """Four-signal token confidence scorer."""

    def __init__(
        self,
        embedding_model: Optional[Any] = None,
        living_memory: Optional[Any] = None,
        alpha: float = 0.25,
        beta: float = 0.25,
        gamma: float = 0.25,
        delta: float = 0.25,
    ):
        """
        Initialize token confidence engine.

        Args:
            embedding_model: Model for generating embeddings (optional, uses sklearn if None)
            living_memory: LivingMemoryKernel instance for historical coherence lookup
            alpha: Weight for semantic confidence
            beta: Weight for attentional confidence
            gamma: Weight for probabilistic confidence
            delta: Weight for learning signal
        """
        self.embedding_model = embedding_model
        self.living_memory = living_memory
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.delta = delta

        # Lazy-loaded embedder (sklearn TfidfVectorizer for lightweight usage)
        self._embedder = None
        self._embedder_cache = {}

    def score_tokens(
        self,
        agent_response: str,
        agent_name: str,
        peer_responses: Optional[Dict[str, str]] = None,
        logits: Optional[List[float]] = None,
    ) -> TokenConfidenceScore:
        """
        Score all tokens/claims in an agent's response using 4 signals.

        Args:
            agent_response: The full response text from the agent
            agent_name: Name of the agent (for memory lookup)
            peer_responses: Dict {peer_agent_name: response_text} for attentional scoring
            logits: Optional list of per-token probabilities from generation

        Returns:
            TokenConfidenceScore with all components
        """
        if peer_responses is None:
            peer_responses = {}

        # Step 1: Parse semantic confidence markers
        semantic_conf_dict = self._parse_semantic_markers(agent_response)

        # Step 2: Compute attentional confidence (semantic overlap with peers)
        attentional_conf_dict = self._compute_attentional_confidence(
            agent_response, peer_responses
        )

        # Step 3: Probabilistic confidence from logits (if provided)
        probabilistic_conf_dict = self._extract_probabilistic_confidence(
            agent_response, logits
        )

        # Step 4: Learning signal from memory (historical coherence)
        learning_signal_dict = self._compute_learning_signal(
            agent_response, agent_name
        )

        # Step 5: Extract claims and compute aggregate confidence per claim
        claims = self._extract_claims(
            agent_response,
            semantic_conf_dict,
            attentional_conf_dict,
            probabilistic_conf_dict,
            learning_signal_dict,
            agent_name,
        )

        # Step 6: Synthesize composite confidence scores
        token_scores = []
        composite_scores = {}

        for i, token_text in enumerate(agent_response.split()):
            semantic = semantic_conf_dict.get(i, 0.5)
            attentional = attentional_conf_dict.get(i, 0.5)
            probabilistic = probabilistic_conf_dict.get(i, 0.5)
            learning = learning_signal_dict.get(i, 0.5)

            # Weighted synthesis
            composite = (
                self.alpha * semantic
                + self.beta * attentional
                + self.gamma * probabilistic
                + self.delta * learning
            )
            composite = max(0.0, min(1.0, composite))  # Clamp to [0, 1]

            token_scores.append(composite)
            composite_scores[i] = composite

        return TokenConfidenceScore(
            agent_name=agent_name,
            response_text=agent_response,
            token_scores=token_scores,
            claims=claims,
            semantic_confidence_dict=semantic_conf_dict,
            attentional_confidence_dict=attentional_conf_dict,
            probabilistic_confidence_dict=probabilistic_conf_dict,
            learning_signal_dict=learning_signal_dict,
            composite_scores=composite_scores,
        )

    def _parse_semantic_markers(self, response: str) -> Dict[int, float]:
        """
        Parse confidence markers from text.

        Returns:
            Dict mapping token_idx to confidence [0, 1]
        """
        conf_dict = {}
        tokens = response.split()

        # Find spans of confidence markers and propagate confidence to nearby tokens
        for level, confidence_level in [("high", 0.9), ("medium", 0.6), ("low", 0.3)]:
            for pattern in _MARKER_PATTERNS[level]:
                for match in pattern.finditer(response):
                    # Map character position to token index
                    char_pos = match.start()
                    char_count = 0
                    for token_idx, token in enumerate(tokens):
                        if char_count <= char_pos < char_count + len(token):
                            # Mark this token and nearby tokens
                            for nearby_idx in range(
                                max(0, token_idx - 1), min(len(tokens), token_idx + 4)
                            ):
                                if nearby_idx not in conf_dict:
                                    conf_dict[nearby_idx] = confidence_level
                                else:
                                    # Take max confidence found
                                    conf_dict[nearby_idx] = max(
                                        conf_dict[nearby_idx], confidence_level
                                    )
                            break
                        char_count += len(token) + 1  # +1 for space

        # Default to neutral for unscored tokens
        for i in range(len(tokens)):
            if i not in conf_dict:
                conf_dict[i] = 0.5

        return conf_dict

    def _compute_attentional_confidence(
        self, agent_response: str, peer_responses: Dict[str, str]
    ) -> Dict[int, float]:
        """
        Compute attentional confidence via semantic overlap with peers.

        High overlap = higher confidence (claim addresses peer perspectives)

        Returns:
            Dict mapping token_idx to confidence [0.3, 1.0]
        """
        conf_dict = {}
        tokens = agent_response.split()

        if not peer_responses:
            # No peers → neutral attentional score
            for i in range(len(tokens)):
                conf_dict[i] = 0.5
            return conf_dict

        # Compute token-level overlap with each peer
        token_overlaps = defaultdict(list)

        for peer_name, peer_response in peer_responses.items():
            peer_tokens_set = set(peer_response.lower().split())

            for token_idx, token in enumerate(tokens):
                # Check if this token or semantically similar tokens appear in peer
                if token.lower() in peer_tokens_set:
                    token_overlaps[token_idx].append(1.0)
                elif any(
                    token.lower().startswith(p[:3]) or p.startswith(token.lower()[:3])
                    for p in peer_tokens_set
                ):
                    # Partial match (first 3 chars)
                    token_overlaps[token_idx].append(0.6)

        # Aggregate overlap: mean overlap with peers, map to [0.3, 1.0]
        for i in range(len(tokens)):
            if token_overlaps[i]:
                overlap_score = sum(token_overlaps[i]) / len(token_overlaps[i])
            else:
                overlap_score = 0.0

            # Scale to [0.3, 1.0]: low overlap agents get 0.3, high get 1.0
            attentional_conf = 0.3 + 0.7 * overlap_score
            conf_dict[i] = attentional_conf

        return conf_dict

    def _extract_probabilistic_confidence(
        self, response: str, logits: Optional[List[float]] = None
    ) -> Dict[int, float]:
        """
        Extract per-token probabilities from logits.

        If logits not provided, use fallback heuristic (all 0.5).

        Returns:
            Dict mapping token_idx to probability [0, 1]
        """
        conf_dict = {}
        tokens = response.split()

        if logits and len(logits) == len(tokens):
            # Direct logit probabilities
            for i, prob in enumerate(logits):
                conf_dict[i] = max(0.0, min(1.0, prob))
        else:
            # Fallback: common words get higher confidence
            common_words = {
                "the",
                "a",
                "is",
                "and",
                "or",
                "of",
                "to",
                "in",
                "that",
                "it",
            }
            for i, token in enumerate(tokens):
                if token.lower() in common_words:
                    conf_dict[i] = 0.9  # Very common
                elif len(token) > 3:
                    conf_dict[i] = 0.6  # More specific words
                else:
                    conf_dict[i] = 0.5  # Neutral

        return conf_dict

    def _compute_learning_signal(
        self, response: str, agent_name: str
    ) -> Dict[int, float]:
        """
        Compute learning signal from historical coherence (Phase 2 enhancement).

        Query memory for similar past responses and boost confidence if
        they led to high coherence. Recent memories are weighted higher.

        Returns:
            Dict mapping token_idx to learning signal [0.5, 1.0]

        Phase 2: Now includes recency weighting with ~7 day half-life
        """
        import math

        conf_dict = {}
        tokens = response.split()

        # If no memory, return neutral signal
        if not self.living_memory:
            for i in range(len(tokens)):
                conf_dict[i] = 0.5
            return conf_dict

        # Retrieve past responses by this agent
        try:
            similar_cocoons = self.living_memory.recall_by_adapter(agent_name, limit=10)
            if not similar_cocoons:
                avg_coherence = 0.5
            else:
                # Phase 2: Weight recent memories higher
                # Using exponential decay with ~7 day half-life
                recency_weights = []
                weighted_coherences = []

                for cocoon in similar_cocoons:
                    if isinstance(cocoon, dict):
                        timestamp = float(cocoon.get("timestamp", time.time()) or time.time())
                        age_hours = max(0.0, (time.time() - timestamp) / 3600.0)
                        meta = cocoon.get("metadata", {}) or {}
                        coherence = float(
                            meta.get("coherence")
                            or meta.get("epistemic", {}).get("ensemble_coherence")
                            or 0.5
                        )
                    else:
                        age_hours = cocoon.age_hours()
                        coherence = float(getattr(cocoon, "coherence", 0.5) or 0.5)
                    # exp(-age_hours / 168) = 0.5 after 168 hours (~7 days)
                    recency_weight = math.exp(-age_hours / 168.0)
                    recency_weights.append(recency_weight)
                    weighted_coherences.append(coherence * recency_weight)

                # Compute weighted average
                total_weight = sum(recency_weights)
                if total_weight > 0:
                    avg_coherence = sum(weighted_coherences) / total_weight
                else:
                    avg_coherence = 0.5

        except Exception as e:
            logger.warning(f"Error retrieving memory for {agent_name}: {e}")
            avg_coherence = 0.5

        # Boost confidence proportional to historical coherence
        # learning_signal = 0.5 + 0.5 * avg_coherence → [0.5, 1.0]
        learning_signal = 0.5 + 0.5 * avg_coherence

        for i in range(len(tokens)):
            conf_dict[i] = learning_signal

        return conf_dict

    def _extract_claims(
        self,
        response: str,
        semantic_conf_dict: Dict[int, float],
        attentional_conf_dict: Dict[int, float],
        probabilistic_conf_dict: Dict[int, float],
        learning_signal_dict: Dict[int, float],
        agent_name: str,
    ) -> List[ClaimSegment]:
        """
        Extract individual claims (sentences/clauses) from response.

        Returns:
            List of ClaimSegment with aggregate confidence from component signals
        """
        claims = []

        # Simple segmentation: split on sentence boundaries
        sentence_pattern = re.compile(r"[.!?]+")
        sentences = sentence_pattern.split(response)

        token_idx = 0
        start_char_idx = 0

        for sentence in sentences:
            if not sentence.strip():
                continue

            sentence_tokens = sentence.split()
            sentence_token_indices = list(range(token_idx, token_idx + len(sentence_tokens)))
            token_idx += len(sentence_tokens)

            # Aggregate confidence across sentence tokens
            if sentence_token_indices:
                semantic = sum(
                    semantic_conf_dict.get(i, 0.5) for i in sentence_token_indices
                ) / len(sentence_token_indices)
                attentional = sum(
                    attentional_conf_dict.get(i, 0.5) for i in sentence_token_indices
                ) / len(sentence_token_indices)
                probabilistic = sum(
                    probabilistic_conf_dict.get(i, 0.5) for i in sentence_token_indices
                ) / len(sentence_token_indices)
                learning = sum(
                    learning_signal_dict.get(i, 0.5) for i in sentence_token_indices
                ) / len(sentence_token_indices)

                composite_confidence = (
                    self.alpha * semantic
                    + self.beta * attentional
                    + self.gamma * probabilistic
                    + self.delta * learning
                )
                composite_confidence = max(0.0, min(1.0, composite_confidence))

                claim = ClaimSegment(
                    text=sentence.strip(),
                    start_idx=start_char_idx,
                    end_idx=start_char_idx + len(sentence),
                    confidence=composite_confidence,
                    semantic_conf=semantic,
                    attentional_conf=attentional,
                    probabilistic_conf=probabilistic,
                    learning_signal=learning,
                    agent_name=agent_name,
                )
                claims.append(claim)

                start_char_idx += len(sentence) + 1  # +1 for sentence separator

        return claims
