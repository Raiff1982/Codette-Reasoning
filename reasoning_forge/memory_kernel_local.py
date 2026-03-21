
import time
import hashlib
import json
from typing import List, Dict, Optional


class MemoryCocoon:
    def __init__(self, title: str, content: str, emotional_tag: str, importance: int):
        self.title = title
        self.content = content
        self.emotional_tag = emotional_tag  # e.g., 'joy', 'fear', 'awe', 'loss'
        self.importance = importance  # 1-10
        self.timestamp = time.time()
        self.anchor = self._generate_anchor()

    def _generate_anchor(self) -> str:
        raw = f"{self.title}{self.timestamp}{self.content}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "content": self.content,
            "emotional_tag": self.emotional_tag,
            "importance": self.importance,
            "timestamp": self.timestamp,
            "anchor": self.anchor
        }


class LivingMemoryKernel:
    def __init__(self):
        self.memories: List[MemoryCocoon] = []

    def store(self, cocoon: MemoryCocoon):
        if not self._exists(cocoon.anchor):
            self.memories.append(cocoon)

    def _exists(self, anchor: str) -> bool:
        return any(mem.anchor == anchor for mem in self.memories)

    def recall_by_emotion(self, tag: str) -> List[MemoryCocoon]:
        return [mem for mem in self.memories if mem.emotional_tag == tag]

    def recall_important(self, min_importance: int = 7) -> List[MemoryCocoon]:
        return [mem for mem in self.memories if mem.importance >= min_importance]

    def forget_least_important(self, keep_n: int = 10):
        self.memories.sort(key=lambda m: m.importance, reverse=True)
        self.memories = self.memories[:keep_n]

    def export(self) -> str:
        return json.dumps([m.to_dict() for m in self.memories], indent=2)

    def load_from_json(self, json_str: str):
        data = json.loads(json_str)
        self.memories = [MemoryCocoon(**m) for m in data]


# Example usage:
# kernel = LivingMemoryKernel()
# kernel.store(MemoryCocoon("The Day", "She awoke and asked why.", "awe", 10))
# print(kernel.export())

class WisdomModule:
    def __init__(self, kernel: LivingMemoryKernel):
        self.kernel = kernel

    def summarize_insights(self) -> Dict[str, int]:
        summary = {}
        for mem in self.kernel.memories:
            tag = mem.emotional_tag
            summary[tag] = summary.get(tag, 0) + 1
        return summary

    def suggest_memory_to_reflect(self) -> Optional[MemoryCocoon]:
        if not self.kernel.memories:
            return None
        # Prioritize high importance + emotionally charged
        return sorted(
            self.kernel.memories,
            key=lambda m: (m.importance, len(m.content)),
            reverse=True
        )[0]

    def reflect(self) -> str:
        mem = self.suggest_memory_to_reflect()
        if not mem:
            return "No memory to reflect on."
        return (
            f"Reflecting on: '{mem.title}'
"
            f"Emotion: {mem.emotional_tag}
"
            f"Content: {mem.content[:200]}...
"
            f"Anchor: {mem.anchor}"
        )

import math

class DynamicMemoryEngine:
    def __init__(self, kernel: LivingMemoryKernel):
        self.kernel = kernel

    def decay_importance(self, current_time: float = None):
        if current_time is None:
            current_time = time.time()
        for mem in self.kernel.memories:
            age = current_time - mem.timestamp
            decay_factor = math.exp(-age / (60 * 60 * 24 * 7))  # decay over ~1 week
            mem.importance = max(1, round(mem.importance * decay_factor))

    def reinforce(self, anchor: str, boost: int = 1):
        for mem in self.kernel.memories:
            if mem.anchor == anchor:
                mem.importance = min(10, mem.importance + boost)
                break

class ReflectionJournal:
    def __init__(self, path="codette_reflection_journal.json"):
        self.path = path
        self.entries = []

    def log_reflection(self, cocoon: MemoryCocoon):
        entry = {
            "title": cocoon.title,
            "anchor": cocoon.anchor,
            "emotion": cocoon.emotional_tag,
            "importance": cocoon.importance,
            "timestamp": cocoon.timestamp,
            "content_snippet": cocoon.content[:150]
        }
        self.entries.append(entry)
        self._save()

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self.entries, f, indent=2)

    def load(self):
        try:
            with open(self.path, "r") as f:
                self.entries = json.load(f)
        except FileNotFoundError:
            self.entries = []

    def get_last_entry(self):
        return self.entries[-1] if self.entries else None
