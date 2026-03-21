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
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


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

    def __init__(self):
        self.memories: List[MemoryCocoon] = []

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

    def recall_important(self, min_importance: int = 7) -> List[MemoryCocoon]:
        """Recall high-importance memories (default: 7+)."""
        return [mem for mem in self.memories if mem.importance >= min_importance]

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
