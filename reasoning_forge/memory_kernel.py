"""
Codette Memory Kernel — Recovered Foundational System
======================================================

Emotional continuity engine with SHA256-anchored memory, importance decay,
ethical regret tracking, and reflection journaling.

Recovered from: J:\codette-training-lab\new data\codette_memory_kernel*.py
Mathematical foundation: Codette_Deep_Simulation_v1.py

Purpose: Prevent synthesis loop corruption by maintaining memory integrity
and emotional continuity across multi-round debate cycles.
"""

import time
import hashlib
import json
import math
import re
import logging
from collections import Counter
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lightweight semantic helpers (no external deps, consistent with EpistemicMetrics)
# ---------------------------------------------------------------------------

_STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "and", "but", "or", "nor", "not", "so",
    "yet", "both", "this", "that", "these", "those", "it", "its", "they",
    "them", "their", "we", "our", "you", "your", "he", "she", "his", "her",
}


def _mk_tokenize(text: str) -> List[str]:
    """Tokenise text: lowercase alpha tokens >= 3 chars, stop-words removed."""
    return [w for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in _STOP_WORDS]


def _mk_vector(text: str) -> Counter:
    return Counter(_mk_tokenize(text))


def _mk_relevance(query_vec: Counter, cocoon_text: str) -> float:
    """Score a cocoon's content against a query vector using cosine similarity.

    Returns a float in [0, 1].
    """
    mem_vec = _mk_vector(cocoon_text)
    if not query_vec or not mem_vec:
        return 0.0
    shared = set(query_vec) & set(mem_vec)
    if not shared:
        return 0.0
    dot = sum(query_vec[k] * mem_vec[k] for k in shared)
    mag_q = math.sqrt(sum(v * v for v in query_vec.values()))
    mag_m = math.sqrt(sum(v * v for v in mem_vec.values()))
    if mag_q == 0 or mag_m == 0:
        return 0.0
    return dot / (mag_q * mag_m)


class MemoryCocoon:
    """
    Emotional memory anchor with SHA256 integrity field.

    Each cocoon represents a discrete memory event with:
    - Emotional context (joy, fear, awe, loss)
    - Importance weight (1-10)
    - SHA256 anchor for integrity validation
    - Timestamp for decay calculation
    """

    def __init__(self, title: str, content: str, emotional_tag: str,
                 importance: int, timestamp: Optional[float] = None):
        """
        Args:
            title: Memory name/label
            content: Memory content/description
            emotional_tag: Emotional classification (joy, fear, awe, loss, etc.)
            importance: Importance weight (1-10)
            timestamp: Unix epoch (auto-generated if None)
        """
        self.title = title
        self.content = content
        self.emotional_tag = emotional_tag
        self.importance = max(1, min(10, importance))  # Clamp to 1-10
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.anchor = self._generate_anchor()

    def _generate_anchor(self) -> str:
        """Generate SHA256 anchor for memory integrity validation."""
        raw = f"{self.title}{self.timestamp}{self.content}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def to_dict(self) -> Dict:
        """Export to serializable dictionary."""
        return {
            "title": self.title,
            "content": self.content,
            "emotional_tag": self.emotional_tag,
            "importance": self.importance,
            "timestamp": self.timestamp,
            "anchor": self.anchor
        }

    def validate_anchor(self) -> bool:
        """Verify memory integrity — anchor should match content."""
        expected = self._generate_anchor()
        return expected == self.anchor

    def __repr__(self) -> str:
        return f"MemoryCocoon('{self.title}', {self.emotional_tag}, importance={self.importance})"


class LivingMemoryKernel:
    """
    Persistent memory kernel with emotion-based recall and importance-based forgetting.

    The "living" aspect means memories decay over time unless reinforced,
    and emotional context shapes recall patterns.
    """

    def __init__(self, cocoon_dir: Optional[str] = None):
        self.memories: List[MemoryCocoon] = []
        if cocoon_dir:
            self._load_cocoons_from_disk(cocoon_dir)

    def _load_cocoons_from_disk(self, cocoon_dir: str) -> None:
        """Load cocoon files (.json and .cocoon) from disk into memory."""
        cocoon_path = Path(cocoon_dir)
        if not cocoon_path.exists():
            logger.warning(f"Cocoon directory not found: {cocoon_dir}")
            return

        loaded = 0

        # Load JSON cocoons (cocoon_joy.json, cocoon_fear.json, etc.)
        for f in cocoon_path.glob("cocoon_*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                cocoon = MemoryCocoon(
                    title=data.get("title", f.stem),
                    content=data.get("summary", data.get("quote", "")),
                    emotional_tag=data.get("emotion", "neutral"),
                    importance=8,  # Foundational memories are important
                )
                self.store(cocoon)
                loaded += 1
            except Exception as e:
                logger.debug(f"Could not load {f.name}: {e}")

        # Load .cocoon binary/JSON files (EMG_*.cocoon)
        for f in cocoon_path.glob("*.cocoon"):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                meta = data.get("metadata", {})
                cocoon = MemoryCocoon(
                    title=meta.get("context", data.get("cocoon_id", f.stem))[:100],
                    content=meta.get("context", ""),
                    emotional_tag=data.get("emotional_classification", "neutral").lower(),
                    importance=data.get("importance_rating", 7),
                    timestamp=data.get("timestamp_unix"),
                )
                self.store(cocoon)
                loaded += 1
            except Exception as e:
                logger.debug(f"Could not load {f.name}: {e}")

        if loaded > 0:
            logger.info(f"  ✓ Loaded {loaded} cocoon memories from {cocoon_dir}")

    def store(self, cocoon: MemoryCocoon) -> None:
        """Store memory cocoon if not already present (by anchor)."""
        if not self._exists(cocoon.anchor):
            self.memories.append(cocoon)
            logger.debug(f"Stored memory: {cocoon.title} (anchor: {cocoon.anchor[:8]}...)")

    def _exists(self, anchor: str) -> bool:
        """Check if memory already stored by anchor."""
        return any(mem.anchor == anchor for mem in self.memories)

    def recall_by_emotion(self, tag: str) -> List[MemoryCocoon]:
        """Recall all memories with specific emotional tag."""
        return [mem for mem in self.memories if mem.emotional_tag == tag]

    def recall_important(
        self,
        min_importance: int = 7,
        query: Optional[str] = None,
        top_n: Optional[int] = None,
    ) -> List[MemoryCocoon]:
        """Recall high-importance memories, optionally ranked by relevance to a query.

        FIX 4: When `query` is provided, results are sorted by a combined score of
        (importance * relevance) so that semantically relevant memories rank above
        high-importance but unrelated ones.  The pure threshold behaviour is
        completely unchanged when query=None.

        Args:
            min_importance: Minimum importance threshold (default 7). Always applied.
            query:          Optional natural-language query string for relevance ranking.
            top_n:          Optional hard cap on returned results (applied after ranking).
        """
        candidates = [mem for mem in self.memories if mem.importance >= min_importance]

        if not query:
            return candidates if top_n is None else candidates[:top_n]

        # Relevance-ranked path (Fix 4)
        query_vec = _mk_vector(query)
        ranked = []
        for mem in candidates:
            full_text = f"{mem.title} {mem.content}"
            rel = _mk_relevance(query_vec, full_text)
            combined = mem.importance * (0.5 + rel)
            ranked.append((combined, mem))

        ranked.sort(key=lambda x: -x[0])
        results = [m for _, m in ranked]
        return results if top_n is None else results[:top_n]

    def forget_least_important(self, keep_n: int = 10) -> None:
        """Forget least important memories, keep top N."""
        if len(self.memories) > keep_n:
            self.memories.sort(key=lambda m: m.importance, reverse=True)
            self.memories = self.memories[:keep_n]
            logger.info(f"Forgot memories, keeping top {keep_n}")

    def validate_all_anchors(self) -> Dict[str, bool]:
        """Validate integrity of all memories."""
        results = {}
        for mem in self.memories:
            results[mem.anchor[:8]] = mem.validate_anchor()
        invalid = [k for k, v in results.items() if not v]
        if invalid:
            logger.warning(f"Invalid memory anchors detected: {invalid}")
        return results

    def export(self) -> str:
        """Export to JSON."""
        return json.dumps([m.to_dict() for m in self.memories], indent=2)

    def load_from_json(self, json_str: str) -> None:
        """Load memories from JSON."""
        try:
            data = json.loads(json_str)
            self.memories = [MemoryCocoon(**m) for m in data]
            logger.info(f"Loaded {len(self.memories)} memories from JSON")
        except Exception as e:
            logger.error(f"Failed to load from JSON: {e}")

    def __len__(self) -> int:
        return len(self.memories)


class DynamicMemoryEngine:
    """
    Time-decay and reinforcement system for memory importance.

    Memories decay over ~1 week exponentially unless explicitly reinforced.
    This prevents stale memories from dominating recall while allowing
    important events to persist longer.
    """

    DECAY_HALF_LIFE = 60 * 60 * 24 * 7  # 1 week in seconds

    def __init__(self, kernel: LivingMemoryKernel):
        self.kernel = kernel

    def decay_importance(self, current_time: Optional[float] = None) -> None:
        """Apply exponential decay to all memory importance values."""
        if current_time is None:
            current_time = time.time()

        for mem in self.kernel.memories:
            age = current_time - mem.timestamp
            decay_factor = math.exp(-age / self.DECAY_HALF_LIFE)
            old_importance = mem.importance
            mem.importance = max(1, round(mem.importance * decay_factor))

            if mem.importance != old_importance:
                logger.debug(f"Decayed '{mem.title}': {old_importance} → {mem.importance}")

    def reinforce(self, anchor: str, boost: int = 1) -> bool:
        """Increase importance of memory (prevents forgetting)."""
        for mem in self.kernel.memories:
            if mem.anchor == anchor:
                old = mem.importance
                mem.importance = min(10, mem.importance + boost)
                logger.debug(f"Reinforced memory: {old} → {mem.importance}")
                return True
        logger.warning(f"Memory anchor not found: {anchor[:8]}")
        return False


class EthicalAnchor:
    """
    Regret-based learning system for ethical continuity.

    Tracks when intended outputs differ from actual outputs and accumulates
    regret signal for use in future decision-making. Prevents repeating
    mistakes and maintains ethical consistency.

    Based on Codette_Deep_Simulation_v1.py EthicalAnchor class.
    """

    def __init__(self, lambda_weight: float = 0.7, gamma_weight: float = 0.5,
                 mu_weight: float = 1.0):
        """
        Args:
            lambda_weight: Historical regret influence (0-1)
            gamma_weight: Learning rate multiplier (0-1)
            mu_weight: Current regret multiplier (0-1)
        """
        self.lam = lambda_weight
        self.gamma = gamma_weight
        self.mu = mu_weight
        self.history: List[Dict] = []

    def regret(self, intended: float, actual: float) -> float:
        """Calculate regret magnitude."""
        return abs(intended - actual)

    def update(self, r_prev: float, h: float, learning_fn,
               e: float, m_prev: float, intended: float, actual: float) -> float:
        """
        Update ethical state with regret tracking.

        M(t) = λ * (R(t-1) + H) + γ * Learning(m_prev, E) + μ * Regret

        Args:
            r_prev: Previous regret accumulation
            h: Harmony score
            learning_fn: Learning function callable
            e: Energy available
            m_prev: Previous ethical state
            intended: Intended output value
            actual: Actual output value

        Returns:
            Updated ethical state
        """
        regret_val = self.regret(intended, actual)
        m = (
            self.lam * (r_prev + h) +
            self.gamma * learning_fn(m_prev, e) +
            self.mu * regret_val
        )

        self.history.append({
            'M': m,
            'regret': regret_val,
            'intended': intended,
            'actual': actual,
            'timestamp': time.time()
        })

        return m

    def get_regret_signal(self) -> float:
        """Get accumulated regret for use in decision-making."""
        if not self.history:
            return 0.0
        # Average recent regrets (last 5 or all if < 5)
        recent = self.history[-5:]
        return sum(h['regret'] for h in recent) / len(recent)


class WisdomModule:
    """
    Reflection and insight generation over memory kernel.

    Summarizes emotional patterns and suggests high-value memories
    for deeper reflection.
    """

    def __init__(self, kernel: LivingMemoryKernel):
        self.kernel = kernel

    def summarize_insights(self) -> Dict[str, int]:
        """Summarize emotional composition of memory kernel."""
        summary = {}
        for mem in self.kernel.memories:
            tag = mem.emotional_tag
            summary[tag] = summary.get(tag, 0) + 1
        return summary

    def suggest_memory_to_reflect(self) -> Optional[MemoryCocoon]:
        """Identify highest-value memory for reflection."""
        if not self.kernel.memories:
            return None
        return sorted(
            self.kernel.memories,
            key=lambda m: (m.importance, len(m.content)),
            reverse=True
        )[0]

    def reflect(self) -> str:
        """Generate reflection prose about key memory."""
        mem = self.suggest_memory_to_reflect()
        if not mem:
            return "No memory to reflect on."
        return (
            f"Reflecting on: '{mem.title}'\n"
            f"Emotion: {mem.emotional_tag}\n"
            f"Content: {mem.content[:200]}...\n"
            f"Anchor: {mem.anchor[:16]}..."
        )


class ReflectionJournal:
    """
    Persistent logging of memory reflections and synthesis events.

    Creates audit trail of what the system has reflected on and learned.
    Stored as JSON file for long-term persistence.
    """

    def __init__(self, path: str = "codette_reflection_journal.json"):
        self.path = Path(path)
        self.entries: List[Dict] = []
        self.load()

    def log_reflection(self, cocoon: MemoryCocoon, context: Optional[str] = None) -> None:
        """Log a memory reflection event."""
        entry = {
            "title": cocoon.title,
            "anchor": cocoon.anchor[:16],  # Short anchor in logs
            "emotion": cocoon.emotional_tag,
            "importance": cocoon.importance,
            "timestamp": time.time(),
            "content_snippet": cocoon.content[:150],
            "context": context
        }
        self.entries.append(entry)
        self._save()

    def log_synthesis_event(self, event_type: str, data: Dict,
                           emotional_context: Optional[str] = None) -> None:
        """Log synthesis-related events for debugging."""
        entry = {
            "type": event_type,
            "timestamp": time.time(),
            "data": data,
            "emotional_context": emotional_context
        }
        self.entries.append(entry)
        self._save()

    def _save(self) -> None:
        """Persist journal to disk."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.entries, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save reflection journal: {e}")

    def load(self) -> None:
        """Load journal from disk."""
        try:
            if self.path.exists():
                with open(self.path, "r") as f:
                    self.entries = json.load(f)
                logger.info(f"Loaded {len(self.entries)} journal entries")
        except Exception as e:
            logger.warning(f"Failed to load reflection journal: {e}")
            self.entries = []

    def get_recent_entries(self, n: int = 10) -> List[Dict]:
        """Get most recent journal entries."""
        return self.entries[-n:]

    def __len__(self) -> int:
        return len(self.entries)
