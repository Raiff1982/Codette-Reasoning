"""
Cocoon Schema v2 — Living Memory Kernel, Codette RC+xi Framework

Upgrades over v1 (plain dict cocoons):
- Typed dataclass with all fields required or defaulted
- Retrieval index fields: problem_type, user_preferences_inferred, project_context
- Contradiction tracking: contradicts_cocoon_ids
- Follow-up hooks: open_threads list for continuity
- Perspective audit: which perspectives were active and which dominated
- Confidence and verifiability flags
- Helper method: relevance_score() for retrieval ranking

Usage:
    from reasoning_forge.cocoon_schema_v2 import Cocoon, build_cocoon
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional

# Valid emotional valences as defined in the Living Memory Kernel spec
VALID_VALENCES = frozenset([
    "curiosity", "awe", "joy", "insight", "confusion",
    "frustration", "fear", "empathy", "determination",
    "surprise", "trust", "gratitude",
])

# Valid problem type categories
VALID_PROBLEM_TYPES = frozenset([
    "architectural",    # system/software design decisions
    "ethical",          # value conflicts, governance
    "technical",        # implementation, debugging
    "creative",         # generative, design, artistic
    "analytical",       # data, logic, causal reasoning
    "relational",       # interpersonal, communication
    "strategic",        # planning, prioritization
    "exploratory",      # open-ended inquiry, research
    "meta",             # reasoning about Codette itself
    "unknown",
])


@dataclass
class Cocoon:
    """A single memory unit stored by the Living Memory Kernel.

    Fields are organized into four concern groups:
    1. Identity — what this cocoon is
    2. Content — the actual exchange
    3. Cognitive state — what the reasoning engine was doing
    4. Retrieval — fields that enable smart memory lookup
    """

    # ─── Identity ───────────────────────────────────────────────────────────
    cocoon_id: str                          # SHA-256 of query + timestamp
    timestamp: float                        # Unix epoch
    session_id: Optional[str] = None       # conversation session identifier

    # ─── Content ────────────────────────────────────────────────────────────
    query: str = ""                         # original user query
    response_summary: str = ""             # compressed synthesis (< 200 words)
    full_response_hash: str = ""           # SHA-256 of full response text

    # ─── Emotional / importance ──────────────────────────────────────────────
    emotional_valence: str = "curiosity"   # must be in VALID_VALENCES
    importance_score: float = 5.0          # 1.0 – 10.0
    confidence: float = 0.75              # 0.0 – 1.0 synthesis confidence

    # ─── Cognitive state at time of storage ─────────────────────────────────
    epsilon_value: float = 0.35            # epistemic tension
    gamma_coherence: float = 0.72          # ensemble coherence
    eta_score: Optional[float] = None      # AEGIS ethical alignment
    active_perspectives: list[str] = field(default_factory=list)
    dominant_perspective: Optional[str] = None  # perspective with highest signal
    unresolved_tensions: list[str] = field(default_factory=list)
    synthesis_quality: str = "adequate"    # 'strong' | 'adequate' | 'partial'

    # ─── Retrieval fields ───────────────────────────────────────────────────
    problem_type: str = "unknown"          # from VALID_PROBLEM_TYPES
    topic_tags: list[str] = field(default_factory=list)   # keyword tags
    project_context: Optional[str] = None  # e.g., 'Codette-Reasoning', 'raiffs-bits'
    user_preferences_inferred: dict[str, str] = field(default_factory=dict)
    # e.g., {"detail_level": "high", "tone": "direct", "domain": "AI architecture"}

    # ─── Continuity ─────────────────────────────────────────────────────────
    open_threads: list[str] = field(default_factory=list)
    # Questions or decisions that were NOT resolved — follow-up hooks
    # e.g., ["Does synthesis_engine v2 handle all 8 perspectives?",
    #        "Need to test cocoon retrieval with semantic search"]

    contradicts_cocoon_ids: list[str] = field(default_factory=list)
    # IDs of prior cocoons this cocoon's conclusion conflicts with

    references_cocoon_ids: list[str] = field(default_factory=list)
    # IDs of prior cocoons this cocoon builds on

    # ─── Quality flags ──────────────────────────────────────────────────────
    is_hallucination_flagged: bool = False
    is_sycophancy_flagged: bool = False
    is_verified: bool = False  # True if response was externally verified

    def validate(self) -> list[str]:
        """Return a list of validation errors (empty list = valid)."""
        errors = []
        if self.emotional_valence not in VALID_VALENCES:
            errors.append(f"Invalid valence: {self.emotional_valence!r}. Must be one of {sorted(VALID_VALENCES)}")
        if not 1.0 <= self.importance_score <= 10.0:
            errors.append(f"importance_score {self.importance_score} out of range [1, 10]")
        if not 0.0 <= self.confidence <= 1.0:
            errors.append(f"confidence {self.confidence} out of range [0, 1]")
        if not 0.0 <= self.epsilon_value <= 1.0:
            errors.append(f"epsilon_value {self.epsilon_value} out of range [0, 1]")
        if not 0.0 <= self.gamma_coherence <= 1.0:
            errors.append(f"gamma_coherence {self.gamma_coherence} out of range [0, 1]")
        if self.problem_type not in VALID_PROBLEM_TYPES:
            errors.append(f"Invalid problem_type: {self.problem_type!r}. Must be one of {sorted(VALID_PROBLEM_TYPES)}")
        if self.synthesis_quality not in ("strong", "adequate", "partial"):
            errors.append(f"Invalid synthesis_quality: {self.synthesis_quality!r}")
        return errors

    def relevance_score(
        self,
        query_keywords: list[str],
        current_project: Optional[str] = None,
        recency_weight: float = 0.2,
    ) -> float:
        """Score this cocoon's retrieval relevance to a new query.

        Higher = more relevant. Used by the memory kernel for ranked recall.

        Args:
            query_keywords: Lowercased keyword list from the incoming query.
            current_project: Active project context, if any.
            recency_weight: How much to weight recency vs. importance (0-1).

        Returns:
            Relevance score (unbounded, higher is better).
        """
        score = 0.0

        # Tag overlap
        tags_lower = [t.lower() for t in self.topic_tags]
        for kw in query_keywords:
            if any(kw in tag for tag in tags_lower):
                score += 1.5
            if kw in self.query.lower():
                score += 1.0

        # Project match bonus
        if current_project and self.project_context == current_project:
            score += 2.0

        # Importance weight
        score += self.importance_score * 0.3

        # Recency weight (decay over ~30 days)
        age_days = (time.time() - self.timestamp) / 86400
        recency = max(0.0, 1.0 - age_days / 30)
        score += recency * recency_weight * 5.0

        # Quality penalty
        if self.synthesis_quality == "partial":
            score *= 0.6
        elif self.synthesis_quality == "strong":
            score *= 1.15

        # Penalize flagged cocoons
        if self.is_hallucination_flagged or self.is_sycophancy_flagged:
            score *= 0.4

        return score

    def to_retrieval_summary(self) -> str:
        """Compact string for memory search display."""
        tags = ", ".join(self.topic_tags[:5]) if self.topic_tags else "(no tags)"
        threads = " | ".join(self.open_threads[:2]) if self.open_threads else "none"
        return (
            f"[{self.cocoon_id[:8]}] {self.query[:60]}… "
            f"| type={self.problem_type} | ε={self.epsilon_value:.2f} "
            f"| importance={self.importance_score:.1f} | valence={self.emotional_valence} "
            f"| tags=[{tags}] | open_threads=[{threads}]"
        )


def build_cocoon(
    query: str,
    response_text: str,
    response_summary: str,
    emotional_valence: str = "curiosity",
    importance_score: float = 5.0,
    epsilon_value: float = 0.35,
    gamma_coherence: float = 0.72,
    active_perspectives: Optional[list[str]] = None,
    dominant_perspective: Optional[str] = None,
    unresolved_tensions: Optional[list[str]] = None,
    synthesis_quality: str = "adequate",
    problem_type: str = "unknown",
    topic_tags: Optional[list[str]] = None,
    project_context: Optional[str] = None,
    user_preferences_inferred: Optional[dict[str, str]] = None,
    open_threads: Optional[list[str]] = None,
    contradicts_cocoon_ids: Optional[list[str]] = None,
    references_cocoon_ids: Optional[list[str]] = None,
    eta_score: Optional[float] = None,
    confidence: float = 0.75,
    session_id: Optional[str] = None,
) -> Cocoon:
    """Factory function that builds and validates a Cocoon.

    Raises ValueError if validation fails.
    """
    ts = time.time()
    cocoon_id = hashlib.sha256(f"{query}{ts}".encode()).hexdigest()
    full_hash = hashlib.sha256(response_text.encode()).hexdigest()

    # Auto-tag from query words if no tags provided
    if topic_tags is None:
        import re
        words = re.findall(r'\b[a-zA-Z][a-zA-Z]{3,}\b', query.lower())
        stop = {"this", "that", "with", "from", "have", "what", "when", "where", "which", "will", "been"}
        topic_tags = [w for w in dict.fromkeys(words) if w not in stop][:8]

    cocoon = Cocoon(
        cocoon_id=cocoon_id,
        timestamp=ts,
        session_id=session_id,
        query=query,
        response_summary=response_summary,
        full_response_hash=full_hash,
        emotional_valence=emotional_valence,
        importance_score=float(importance_score),
        confidence=confidence,
        epsilon_value=epsilon_value,
        gamma_coherence=gamma_coherence,
        eta_score=eta_score,
        active_perspectives=active_perspectives or [],
        dominant_perspective=dominant_perspective,
        unresolved_tensions=unresolved_tensions or [],
        synthesis_quality=synthesis_quality,
        problem_type=problem_type,
        topic_tags=topic_tags,
        project_context=project_context,
        user_preferences_inferred=user_preferences_inferred or {},
        open_threads=open_threads or [],
        contradicts_cocoon_ids=contradicts_cocoon_ids or [],
        references_cocoon_ids=references_cocoon_ids or [],
    )

    errors = cocoon.validate()
    if errors:
        raise ValueError(f"Cocoon validation failed: {errors}")

    return cocoon
