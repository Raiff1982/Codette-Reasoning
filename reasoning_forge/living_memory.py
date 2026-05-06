"""Codette Living Memory Kernel — Emotionally-Tagged Memory Cocoons

Memories are tagged with emotional context, importance scoring, and
SHA-256 anchors for integrity. The kernel supports recall by emotion,
importance-based pruning, and automatic cocoon formation from
conversation turns.

Origin: codette_memory_kernel.py + dreamcore_wakestate_engine.py, rebuilt
"""

import time
import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Emotional tags recognized by the memory system
EMOTIONAL_TAGS = [
    "neutral", "curiosity", "awe", "joy", "insight",
    "confusion", "frustration", "fear", "empathy",
    "determination", "surprise", "trust", "gratitude",
]

# Keywords that suggest emotional context in text
_EMOTION_SIGNALS = {
    "curiosity": ["why", "how", "what if", "wonder", "curious", "explore"],
    "awe": ["amazing", "incredible", "beautiful", "profound", "mind-blowing"],
    "joy": ["happy", "glad", "love", "wonderful", "great", "excellent"],
    "insight": ["realize", "understand", "aha", "discover", "breakthrough"],
    "confusion": ["confused", "unclear", "don't understand", "lost", "huh"],
    "frustration": ["frustrated", "annoyed", "broken", "doesn't work", "bug"],
    "fear": ["worried", "concerned", "dangerous", "risk", "threat"],
    "empathy": ["feel", "compassion", "care", "support", "kind"],
    "determination": ["must", "need to", "will", "going to", "commit"],
    "surprise": ["unexpected", "surprised", "didn't expect", "wow", "whoa"],
    "trust": ["trust", "reliable", "depend", "confident", "safe"],
    "gratitude": ["thank", "grateful", "appreciate", "helpful"],
}


@dataclass
class MemoryCocoon:
    """A single memory unit with emotional tagging and integrity anchor."""
    title: str
    content: str
    emotional_tag: str = "neutral"
    importance: int = 5          # 1-10 scale
    timestamp: float = 0.0
    anchor: str = ""             # SHA-256 integrity hash
    adapter_used: str = ""       # Which perspective generated this
    query: str = ""              # Original user query
    coherence: float = 0.0       # Epistemic coherence at time of creation
    tension: float = 0.0         # Epistemic tension at time of creation

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if not self.anchor:
            self.anchor = self._generate_anchor()

    def _generate_anchor(self) -> str:
        raw = f"{self.title}{self.timestamp}{self.content}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "content": self.content[:500],  # Cap stored content
            "emotional_tag": self.emotional_tag,
            "importance": self.importance,
            "timestamp": self.timestamp,
            "anchor": self.anchor,
            "adapter_used": self.adapter_used,
            "query": self.query[:200],
            "coherence": self.coherence,
            "tension": self.tension,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "MemoryCocoon":
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})

    def age_hours(self) -> float:
        return (time.time() - self.timestamp) / 3600.0


class LivingMemoryKernel:
    """Emotionally-aware memory store with importance-based pruning.

    Memories form naturally from conversation — each significant exchange
    becomes a cocoon. The kernel can recall by emotion, importance, or
    recency, and automatically prunes low-importance memories when full.
    """

    def __init__(self, max_memories: int = 100):
        self.memories: List[MemoryCocoon] = []
        self.max_memories = max_memories
        self._emotion_index: Dict[str, List[int]] = {}

    def store(self, cocoon: MemoryCocoon):
        """Store a memory cocoon, pruning if at capacity."""
        # Don't store duplicates (same anchor)
        if any(m.anchor == cocoon.anchor for m in self.memories):
            return

        self.memories.append(cocoon)
        self._rebuild_index()

        # Auto-prune if over capacity
        if len(self.memories) > self.max_memories:
            self.prune(keep_n=self.max_memories)

    def store_from_turn(self, query: str, response: str,
                        adapter: str = "", coherence: float = 0.0,
                        tension: float = 0.0):
        """Create and store a memory from a conversation turn."""
        emotion = detect_emotion(query + " " + response)
        importance = self._estimate_importance(query, response, coherence)

        cocoon = MemoryCocoon(
            title=query[:80],
            content=response[:500],
            emotional_tag=emotion,
            importance=importance,
            adapter_used=adapter,
            query=query,
            coherence=coherence,
            tension=tension,
        )
        self.store(cocoon)
        return cocoon

    def recall_by_emotion(self, tag: str, limit: int = 10) -> List[MemoryCocoon]:
        """Recall memories with a specific emotional tag."""
        indices = self._emotion_index.get(tag, [])
        results = [self.memories[i] for i in indices]
        return sorted(results, key=lambda m: m.importance, reverse=True)[:limit]

    def recall_important(self, min_importance: int = 7,
                         limit: int = 10) -> List[MemoryCocoon]:
        """Recall high-importance memories."""
        results = [m for m in self.memories if m.importance >= min_importance]
        return sorted(results, key=lambda m: m.importance, reverse=True)[:limit]

    def recall_recent(self, limit: int = 10) -> List[MemoryCocoon]:
        """Recall most recent memories."""
        return sorted(self.memories, key=lambda m: m.timestamp, reverse=True)[:limit]

    def recall_by_adapter(self, adapter: str,
                          limit: int = 10) -> List[MemoryCocoon]:
        """Recall memories generated by a specific perspective."""
        results = [m for m in self.memories if m.adapter_used == adapter]
        return sorted(results, key=lambda m: m.timestamp, reverse=True)[:limit]

    def recall_by_tension(
        self,
        current_epsilon: float,
        tolerance: float = 0.20,
        limit: int = 5,
        min_importance: int = 4,
    ) -> List[MemoryCocoon]:
        """Zeta-Equilibrium Retrieval — surface past cocoons with similar epistemic tension.

        When the current query has high uncertainty (epsilon > 0.5), this surfaces
        memories from similar-difficulty past reasoning moments.  Cross-referencing
        these 'Aha!' moments gives the current reasoning cycle a head-start toward
        convergence without forcing it to a conclusion.

        Args:
            current_epsilon:  Current epistemic tension (0-1) from the active query.
            tolerance:        Match window (default ±0.20 around current_epsilon).
            limit:            Maximum memories to return.
            min_importance:   Skip low-importance memories (default >= 4/10).

        Returns:
            Memories sorted by composite score: tension_proximity * importance * recency.
        """
        low  = max(0.0, current_epsilon - tolerance)
        high = min(1.0, current_epsilon + tolerance)

        candidates = [
            m for m in self.memories
            if low <= m.tension <= high and m.importance >= min_importance
        ]
        if not candidates:
            return []

        import time as _time
        now = _time.time()

        def _zeta_score(m: MemoryCocoon) -> float:
            # Proximity: 1.0 at exact match, 0.0 at tolerance boundary
            proximity = 1.0 - abs(m.tension - current_epsilon) / max(tolerance, 1e-6)
            # Recency: exponential decay with 14-day half-life
            age_days = (now - m.timestamp) / 86400.0
            recency  = math.exp(-age_days / 14.0)
            return proximity * m.importance * (0.4 + 0.6 * recency)

        candidates.sort(key=_zeta_score, reverse=True)
        return candidates[:limit]

    def tension_summary(self) -> dict:
        """Return distribution of stored tension values for health monitoring."""
        if not self.memories:
            return {"count": 0, "avg_tension": 0.0, "high_tension_count": 0}
        tensions = [m.tension for m in self.memories]
        return {
            "count": len(tensions),
            "avg_tension": round(sum(tensions) / len(tensions), 3),
            "high_tension_count": sum(1 for t in tensions if t > 0.5),
        }

    def search(self, terms: str, limit: int = 5) -> List[MemoryCocoon]:
        """Simple keyword search across memory content."""
        words = terms.lower().split()
        scored = []
        for m in self.memories:
            text = (m.title + " " + m.content + " " + m.query).lower()
            score = sum(1 for w in words if w in text)
            if score > 0:
                scored.append((score, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:limit]]

    def prune(self, keep_n: int = 50):
        """Keep only the most important memories."""
        # Sort by composite score: importance * recency_bonus
        now = time.time()
        def score(m):
            age_days = (now - m.timestamp) / 86400.0
            recency = math.exp(-age_days / 7.0)  # Half-life ~7 days
            return m.importance * (0.5 + 0.5 * recency)

        self.memories.sort(key=score, reverse=True)
        self.memories = self.memories[:keep_n]
        self._rebuild_index()

    def emotional_profile(self) -> Dict[str, int]:
        """Get a count of memories by emotional tag."""
        profile = {}
        for m in self.memories:
            profile[m.emotional_tag] = profile.get(m.emotional_tag, 0) + 1
        return profile

    def get_state(self) -> Dict:
        """Export kernel state for session/API."""
        return {
            "total_memories": len(self.memories),
            "emotional_profile": self.emotional_profile(),
            "recent": [m.to_dict() for m in self.recall_recent(3)],
            "important": [m.to_dict() for m in self.recall_important(limit=3)],
        }

    def _estimate_importance(self, query: str, response: str,
                             coherence: float) -> int:
        """Estimate importance on 1-10 scale from content signals."""
        score = 5  # Base

        # Longer, more substantive exchanges
        if len(response) > 500:
            score += 1
        if len(response) > 1500:
            score += 1

        # High coherence suggests meaningful synthesis
        if coherence > 0.8:
            score += 1

        # Question complexity
        q = query.lower()
        if any(w in q for w in ["why", "how", "explain", "analyze"]):
            score += 1
        if "?" in query and len(query.split()) > 8:
            score += 1

        return min(10, max(1, score))

    def _rebuild_index(self):
        """Rebuild the emotion-to-index lookup."""
        self._emotion_index.clear()
        for i, m in enumerate(self.memories):
            self._emotion_index.setdefault(m.emotional_tag, []).append(i)

    def to_dict(self) -> Dict:
        return {"memories": [m.to_dict() for m in self.memories]}

    def store_v2_cocoon(self, cocoon) -> MemoryCocoon:
        """Accept a cocoon_schema_v2.Cocoon and store it as a MemoryCocoon.

        Bridges the v2 rich schema to the v1 storage layer so ForgeEngine can
        call build_cocoon() and hand the result directly to this kernel.

        Field mapping:
          Cocoon.query[:80]          → MemoryCocoon.title
          Cocoon.response_summary    → MemoryCocoon.content
          Cocoon.emotional_valence   → MemoryCocoon.emotional_tag
          Cocoon.importance_score    → MemoryCocoon.importance (int, clamped)
          Cocoon.cocoon_id[:16]      → MemoryCocoon.anchor (override)
          Cocoon.dominant_perspective → MemoryCocoon.adapter_used
          Cocoon.query               → MemoryCocoon.query
          Cocoon.gamma_coherence     → MemoryCocoon.coherence
          Cocoon.epsilon_value       → MemoryCocoon.tension
        """
        mc = MemoryCocoon(
            title=cocoon.query[:80],
            content=cocoon.response_summary[:500],
            emotional_tag=cocoon.emotional_valence,
            importance=max(1, min(10, int(round(cocoon.importance_score)))),
            adapter_used=cocoon.dominant_perspective or "",
            query=cocoon.query[:200],
            coherence=cocoon.gamma_coherence,
            tension=cocoon.epsilon_value,
        )
        # Override auto-generated anchor with the v2 cocoon_id for cross-schema linkability
        mc.anchor = cocoon.cocoon_id[:16]
        self.store(mc)
        return mc

    def store_conflict(self, conflict: Dict, resolution_outcome: Optional[Dict] = None):
        """
        Store conflict metadata as a memory cocoon.

        Args:
            conflict: Dict with agent_a, agent_b, claim_a, claim_b, conflict_type, conflict_strength, etc.
            resolution_outcome: Optional dict with coherence_after, resolution_score, etc.
        """
        if resolution_outcome is None:
            resolution_outcome = {}

        # Create a conflict cocoon
        cocoon = MemoryCocoon(
            title=f"Conflict: {conflict.get('agent_a', '?')} vs {conflict.get('agent_b', '?')} ({conflict.get('conflict_type', 'unknown')})",
            content=json.dumps(conflict),
            emotional_tag="tension",
            importance=int(conflict.get("conflict_strength", 0.5) * 10),  # 1-10 scale
            adapter_used=f"{conflict.get('agent_a', '?')},{conflict.get('agent_b', '?')}",
            query="",
            coherence=resolution_outcome.get("coherence_after", 0.5),
            tension=conflict.get("conflict_strength", 0.5),
        )
        self.store(cocoon)

    @classmethod
    def from_dict(cls, d: Dict) -> "LivingMemoryKernel":
        kernel = cls()
        for md in d.get("memories", []):
            kernel.memories.append(MemoryCocoon.from_dict(md))
        kernel._rebuild_index()
        return kernel


def detect_emotion(text: str) -> str:
    """Detect the dominant emotional tag from text content."""
    text_lower = text.lower()
    scores = {}
    for emotion, keywords in _EMOTION_SIGNALS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[emotion] = score

    if not scores:
        return "neutral"
    return max(scores, key=scores.get)
