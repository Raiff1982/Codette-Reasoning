
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
