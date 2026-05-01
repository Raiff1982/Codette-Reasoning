"""
Codette Living Memory Kernel — v2 (Schema Upgrade)
====================================================
Extends the v1 MemoryCocoon schema with fields that enable real conversational
continuity: unresolved tensions, follow-up hooks, user facts, active project
context, contradiction detection, and synthesis quality tracking.

Backward compatible: from_dict() handles missing v2 fields gracefully via
defaults, so existing cocoon files on disk load without errors.

Key additions over v1:
  MemoryCocoon:
    + unresolved_tensions   list[str]   Tensions not resolved in this turn
    + follow_up_hooks       list[str]   Open questions raised but not answered
    + user_facts            dict        Identity/preference facts inferred
    + active_project        str         Project context at creation time
    + contradicts_anchor    str         Anchor of a prior cocoon this disagrees with
    + synthesis_quality     float       Critic score for this turn's synthesis
    + perspectives_active   list[str]   Perspectives that contributed
    + epsilon_band          str         "low" | "medium" | "high" | "max"
    + forge_mode            str         Which forge path created this cocoon
    + psi_r                 float       Resonance state at creation time
    + trace_id              str         ReasoningTrace query_hash (links to trace)

  LivingMemoryKernelV2:
    + recall_by_project()   Retrieve memories sharing an active project
    + recall_contradictions() Find cocoons that contradict a given anchor
    + recall_with_hooks()   Find cocoons that have unresolved follow-up hooks
    + search_by_tension()   Find cocoons where a specific tension was unresolved
    + continuity_profile()  Aggregated view of unresolved hooks and open tensions
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field, fields, asdict
from typing import Any, Dict, List, Optional

# ── V2 MemoryCocoon ───────────────────────────────────────────────────────────

@dataclass
class MemoryCocoonV2:
    """
    Memory unit with full conversational continuity fields.

    V1 fields preserved verbatim for disk backward-compatibility.
    V2 fields have defaults so from_dict() handles old cocoon files.
    """

    # ── V1 fields (unchanged) ──────────────────────────────────────────────
    title:          str
    content:        str
    emotional_tag:  str   = "neutral"
    importance:     int   = 5
    timestamp:      float = 0.0
    anchor:         str   = ""
    adapter_used:   str   = ""
    query:          str   = ""
    coherence:      float = 0.0
    tension:        float = 0.0

    # ── V2 fields ──────────────────────────────────────────────────────────

    # Tensions that were NOT resolved in this turn.
    # Format: "perspective_a_vs_perspective_b" or free-text description.
    unresolved_tensions: List[str] = field(default_factory=list)

    # Questions or threads raised during reasoning but left open.
    # These become search seeds for future memory recall.
    follow_up_hooks: List[str] = field(default_factory=list)

    # User identity/preference facts extracted from query + response.
    # e.g. {"preferred_depth": "technical", "project": "Codette", "name": "Jonathan"}
    user_facts: Dict[str, Any] = field(default_factory=dict)

    # The active project or task context at creation time.
    active_project: str = ""

    # Anchor of a prior cocoon that this turn disagrees with.
    contradicts_anchor: str = ""

    # Critic quality score for the synthesis that created this cocoon (0–1).
    synthesis_quality: float = 0.0

    # Which perspectives contributed (by name).
    perspectives_active: List[str] = field(default_factory=list)

    # Epsilon band at time of creation.
    epsilon_band: str = "medium"  # "low" | "medium" | "high" | "max"

    # Which forge path created this cocoon.
    forge_mode: str = "unknown"

    # Resonance state (psi_r) at creation time.
    psi_r: float = 0.0

    # Links this cocoon to a ReasoningTrace (query_hash).
    trace_id: str = ""

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if not self.anchor:
            self.anchor = self._generate_anchor()

    def _generate_anchor(self) -> str:
        raw = f"{self.title}{self.timestamp}{self.content}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    def age_hours(self) -> float:
        return (time.time() - self.timestamp) / 3600.0

    # ── Serialization ─────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title":                self.title,
            "content":              self.content[:500],
            "emotional_tag":        self.emotional_tag,
            "importance":           self.importance,
            "timestamp":            self.timestamp,
            "anchor":               self.anchor,
            "adapter_used":         self.adapter_used,
            "query":                self.query[:200],
            "coherence":            self.coherence,
            "tension":              self.tension,
            # V2
            "unresolved_tensions":  self.unresolved_tensions,
            "follow_up_hooks":      self.follow_up_hooks,
            "user_facts":           self.user_facts,
            "active_project":       self.active_project,
            "contradicts_anchor":   self.contradicts_anchor,
            "synthesis_quality":    self.synthesis_quality,
            "perspectives_active":  self.perspectives_active,
            "epsilon_band":         self.epsilon_band,
            "forge_mode":           self.forge_mode,
            "psi_r":                self.psi_r,
            "trace_id":             self.trace_id,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MemoryCocoonV2":
        """Load from dict; missing V2 fields fall back to defaults."""
        valid = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})

    @classmethod
    def from_v1(cls, v1_dict: Dict[str, Any]) -> "MemoryCocoonV2":
        """Upgrade a V1 cocoon dict to V2 with empty V2 fields."""
        return cls.from_dict(v1_dict)

    def summary_line(self) -> str:
        """One-line human-readable summary."""
        hooks = len(self.follow_up_hooks)
        tensions = len(self.unresolved_tensions)
        return (
            f"[{self.anchor}] {self.title[:40]} "
            f"imp={self.importance} ε={self.epsilon_band} "
            f"hooks={hooks} tensions={tensions} "
            f"q={self.synthesis_quality:.2f}"
        )


# ── V2 LivingMemoryKernel ─────────────────────────────────────────────────────

class LivingMemoryKernelV2:
    """
    Emotionally-aware memory store with full V2 schema support.

    Drop-in upgrade from LivingMemoryKernel (V1). All V1 method signatures
    preserved; V2 adds project-based retrieval, contradiction detection,
    hook search, and continuity profiling.
    """

    def __init__(self, max_memories: int = 100):
        self.max_memories = max_memories
        self.memories: List[MemoryCocoonV2] = []
        self._anchor_index: Dict[str, MemoryCocoonV2] = {}

    # ── Storage ──────────────────────────────────────────────────────────

    def store(self, cocoon: MemoryCocoonV2):
        """Store a cocoon, pruning if at capacity."""
        if cocoon.anchor in self._anchor_index:
            return  # Dedup by anchor
        self.memories.append(cocoon)
        self._anchor_index[cocoon.anchor] = cocoon
        if len(self.memories) > self.max_memories:
            self.prune()

    def store_from_turn(
        self,
        query: str,
        response: str,
        emotional_tag: str = "neutral",
        importance: Optional[int] = None,
        adapter_used: str = "",
        coherence: float = 0.0,
        tension: float = 0.0,
        # V2 extras
        unresolved_tensions: Optional[List[str]] = None,
        follow_up_hooks: Optional[List[str]] = None,
        user_facts: Optional[Dict[str, Any]] = None,
        active_project: str = "",
        contradicts_anchor: str = "",
        synthesis_quality: float = 0.0,
        perspectives_active: Optional[List[str]] = None,
        epsilon_band: str = "medium",
        forge_mode: str = "unknown",
        psi_r: float = 0.0,
        trace_id: str = "",
    ) -> MemoryCocoonV2:
        """Create and store a V2 memory from a conversation turn."""
        if importance is None:
            importance = self._estimate_importance(query, response, emotional_tag)
        cocoon = MemoryCocoonV2(
            title=query[:50],
            content=response[:500],
            emotional_tag=emotional_tag,
            importance=importance,
            adapter_used=adapter_used,
            query=query[:200],
            coherence=coherence,
            tension=tension,
            unresolved_tensions=unresolved_tensions or [],
            follow_up_hooks=follow_up_hooks or [],
            user_facts=user_facts or {},
            active_project=active_project,
            contradicts_anchor=contradicts_anchor,
            synthesis_quality=synthesis_quality,
            perspectives_active=perspectives_active or [],
            epsilon_band=epsilon_band,
            forge_mode=forge_mode,
            psi_r=psi_r,
            trace_id=trace_id,
        )
        self.store(cocoon)
        return cocoon

    # ── V1 Retrieval (preserved) ──────────────────────────────────────────

    def recall_by_emotion(self, tag: str, limit: int = 10) -> List[MemoryCocoonV2]:
        return [m for m in self.memories if m.emotional_tag == tag][:limit]

    def recall_important(self, min_importance: int = 7, limit: int = 10) -> List[MemoryCocoonV2]:
        ranked = sorted(
            [m for m in self.memories if m.importance >= min_importance],
            key=lambda m: m.importance, reverse=True,
        )
        return ranked[:limit]

    def recall_recent(self, limit: int = 10) -> List[MemoryCocoonV2]:
        return sorted(self.memories, key=lambda m: m.timestamp, reverse=True)[:limit]

    def recall_by_adapter(self, adapter: str, limit: int = 10) -> List[MemoryCocoonV2]:
        return [m for m in self.memories if m.adapter_used == adapter][:limit]

    def search(self, terms: str, limit: int = 5) -> List[MemoryCocoonV2]:
        words = terms.lower().split()
        results = []
        for m in self.memories:
            searchable = f"{m.title} {m.query} {m.content}".lower()
            score = sum(searchable.count(w) for w in words)
            if score > 0:
                results.append((score, m))
        results.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in results[:limit]]

    # ── V2 Retrieval (new) ────────────────────────────────────────────────

    def recall_by_project(self, project: str, limit: int = 10) -> List[MemoryCocoonV2]:
        """Retrieve cocoons sharing a project context."""
        return [m for m in self.memories if m.active_project == project][:limit]

    def recall_contradictions(self, anchor: str) -> List[MemoryCocoonV2]:
        """Find cocoons that contradict the cocoon at the given anchor."""
        return [m for m in self.memories if m.contradicts_anchor == anchor]

    def recall_with_hooks(self, limit: int = 20) -> List[MemoryCocoonV2]:
        """Find cocoons that have unresolved follow-up hooks."""
        ranked = sorted(
            [m for m in self.memories if m.follow_up_hooks],
            key=lambda m: m.importance, reverse=True,
        )
        return ranked[:limit]

    def search_by_tension(self, tension_label: str, limit: int = 10) -> List[MemoryCocoonV2]:
        """Find cocoons where a specific tension label remained unresolved."""
        label = tension_label.lower()
        return [
            m for m in self.memories
            if any(label in t.lower() for t in m.unresolved_tensions)
        ][:limit]

    # ── Continuity Profile (V2 signature feature) ─────────────────────────

    def continuity_profile(self) -> Dict[str, Any]:
        """
        Aggregated view of the memory store for continuity reasoning.

        Returns a dict that Codette can use at the start of a session to
        recall: what's unfinished, what the user cares about, and what
        the system still doesn't know.
        """
        all_hooks: List[str] = []
        all_tensions: List[str] = []
        all_facts: Dict[str, Any] = {}
        projects: Dict[str, int] = {}
        perspective_usage: Dict[str, int] = {}
        epsilon_bands: Dict[str, int] = {"low": 0, "medium": 0, "high": 0, "max": 0}

        for m in self.memories:
            all_hooks.extend(m.follow_up_hooks)
            all_tensions.extend(m.unresolved_tensions)
            all_facts.update(m.user_facts)
            if m.active_project:
                projects[m.active_project] = projects.get(m.active_project, 0) + 1
            for p in m.perspectives_active:
                perspective_usage[p] = perspective_usage.get(p, 0) + 1
            if m.epsilon_band in epsilon_bands:
                epsilon_bands[m.epsilon_band] += 1

        # Deduplicate hooks/tensions while preserving order
        seen: set = set()
        unique_hooks = [h for h in all_hooks if h not in seen and not seen.add(h)]  # type: ignore
        seen = set()
        unique_tensions = [t for t in all_tensions if t not in seen and not seen.add(t)]  # type: ignore

        dominant_project = max(projects, key=projects.get) if projects else ""
        dominant_perspective = max(perspective_usage, key=perspective_usage.get) if perspective_usage else ""

        return {
            "total_cocoons":        len(self.memories),
            "open_hooks":           unique_hooks[:20],
            "open_tensions":        unique_tensions[:20],
            "user_facts":           all_facts,
            "dominant_project":     dominant_project,
            "dominant_perspective": dominant_perspective,
            "perspective_usage":    perspective_usage,
            "epsilon_distribution": epsilon_bands,
            "emotional_profile":    self.emotional_profile(),
        }

    def emotional_profile(self) -> Dict[str, int]:
        profile: Dict[str, int] = {}
        for m in self.memories:
            profile[m.emotional_tag] = profile.get(m.emotional_tag, 0) + 1
        return profile

    # ── Pruning ──────────────────────────────────────────────────────────

    def prune(self, keep_n: int = 50):
        def score(m: MemoryCocoonV2) -> float:
            recency = 1.0 / (1.0 + m.age_hours() / 24.0)
            hook_bonus = 0.5 if m.follow_up_hooks else 0.0
            tension_bonus = 0.3 if m.unresolved_tensions else 0.0
            return m.importance * recency + hook_bonus + tension_bonus

        self.memories.sort(key=score, reverse=True)
        self.memories = self.memories[:keep_n]
        self._rebuild_index()

    def _rebuild_index(self):
        self._anchor_index = {m.anchor: m for m in self.memories}

    # ── Persistence ──────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": "v2",
            "memories": [m.to_dict() for m in self.memories],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LivingMemoryKernelV2":
        kernel = cls()
        for md in d.get("memories", []):
            kernel.memories.append(MemoryCocoonV2.from_dict(md))
        kernel._rebuild_index()
        return kernel

    @classmethod
    def migrate_from_v1(cls, v1_kernel_dict: Dict[str, Any]) -> "LivingMemoryKernelV2":
        """Upgrade a serialized V1 kernel to V2. All V2 fields default to empty."""
        kernel = cls()
        for md in v1_kernel_dict.get("memories", []):
            kernel.memories.append(MemoryCocoonV2.from_v1(md))
        kernel._rebuild_index()
        return kernel

    # ── Bridge: accept cocoon_schema_v2.Cocoon ───────────────────────────

    def store_v2_cocoon(self, cocoon) -> MemoryCocoonV2:
        """Accept a cocoon_schema_v2.Cocoon and store it as MemoryCocoonV2.

        Field mapping:
          Cocoon.query[:50]              → title
          Cocoon.response_summary[:500]  → content
          Cocoon.emotional_valence       → emotional_tag
          Cocoon.importance_score        → importance (int, clamped 1-10)
          Cocoon.dominant_perspective    → adapter_used
          Cocoon.query[:200]             → query
          Cocoon.gamma_coherence         → coherence
          Cocoon.epsilon_value           → tension
          Cocoon.unresolved_tensions     → unresolved_tensions
          Cocoon.open_threads            → follow_up_hooks
          Cocoon.project_context         → active_project
          Cocoon.synthesis_quality       → synthesis_quality (str→float)
          Cocoon.active_perspectives     → perspectives_active
          Cocoon.cocoon_id[:16]          → anchor (override for cross-schema link)
        """
        _sq_map = {"strong": 0.9, "adequate": 0.6, "partial": 0.3}
        _eps = cocoon.epsilon_value
        _band = "max" if _eps > 0.7 else "high" if _eps > 0.5 else "medium" if _eps > 0.3 else "low"
        mc = MemoryCocoonV2(
            title=cocoon.query[:50],
            content=cocoon.response_summary[:500],
            emotional_tag=cocoon.emotional_valence,
            importance=max(1, min(10, int(round(cocoon.importance_score)))),
            adapter_used=cocoon.dominant_perspective or "",
            query=cocoon.query[:200],
            coherence=cocoon.gamma_coherence,
            tension=cocoon.epsilon_value,
            unresolved_tensions=list(cocoon.unresolved_tensions),
            follow_up_hooks=list(cocoon.open_threads),
            active_project=cocoon.project_context or "",
            synthesis_quality=_sq_map.get(cocoon.synthesis_quality, 0.6),
            perspectives_active=list(cocoon.active_perspectives),
            epsilon_band=_band,
        )
        mc.anchor = cocoon.cocoon_id[:16]
        self.store(mc)
        return mc

    # ── Importance estimation (unchanged from V1) ─────────────────────────

    def _estimate_importance(self, query: str, response: str, emotional_tag: str) -> int:
        score = 5
        depth_markers = ["why", "how", "explain", "analyze", "understand", "compare"]
        if any(m in query.lower() for m in depth_markers):
            score += 1
        if len(query.split()) > 20:
            score += 1
        if len(response.split()) > 200:
            score += 1
        high_emotion = {"awe", "insight", "determination", "trust"}
        if emotional_tag in high_emotion:
            score += 1
        return min(score, 10)
