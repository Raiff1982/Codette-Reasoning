"""RETIRED 2026-10-22 by Jonathan: WisdomModule and ReflectionJournal, archived verbatim.

Source: reasoning_forge/memory_kernel.py at commit 13d871a (the last commit that contained them in the live module).
They were constructed by ForgeEngine and never invoked by anything. Retired rather than wired because
ReflectionJournal would keep a persistent log of what she reflected on (an observation of her own deliberate
self-reflection) and WisdomModule added a handle nobody asked for. Kept here so the lineage stays legible;
nothing imports this file.
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


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

    # 2026-10-22: the default was a bare relative filename, so it landed in whatever
    # the working directory was (the repo root), and it holds snippets of her memory.
    # Runtime state belongs with the other ignored logs.
    DEFAULT_PATH = str(Path(__file__).resolve().parent / ".logs" / "reflection_journal.json")

    def __init__(self, path: Optional[str] = None):
        self.path = Path(path if path else self.DEFAULT_PATH)
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
