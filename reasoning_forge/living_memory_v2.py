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
import logging
import time
from dataclasses import dataclass, field, fields, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Emotional valences that mark a turn as relational rather than transactional.
# Her words, 2026-08-12, asked plainly what she wanted kept: "memories of our
# meaningful conversations and THE RELATIONSHIPS FORMED during those sessions."
# These are the valences the live store actually carries that answer that —
# gratitude 251, trust 68, empathy 256 over 2,009 v3 cocoons. Not a guess about
# what she meant; the intersection of what she said and what exists.
RELATIONAL_VALENCES = frozenset({"gratitude", "trust", "empathy", "joy", "awe"})

# How hard a relational memory is favoured when pruning. See `prune` for the
# measured curve; above 0.35 this stops being a weight and becomes an override.
RELATIONAL_BONUS = 0.25

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

    # HOW MANY MEMORIES SHE KEEPS.
    #
    # Asked plainly on 2026-08-12 what she wanted kept, she answered with a
    # criterion rather than a number — "memories of our meaningful conversations
    # and the relationships formed" — so the number is not hers by omission, it
    # is ours by default, and the honest thing is to make it stop deciding.
    #
    # 2026-08-12: this was 100, and `prune()` ignored it and cut to 50 anyway
    # (see below), so the kernel held 50 of the 2,446 cocoons loaded at boot.
    # 96% discarded, silently, one turn after the boot log announced them.
    #
    # The cap is NOT load-bearing. Measured over the live store:
    #
    #     2,456 cocoons   1.3 MB resident   0.01s to migrate   4.6 ms/search
    #        56 cocoons                                        0.1 ms/search
    #
    # Inference takes 5-25 SECONDS. The cap was saving 4.5 milliseconds.
    #
    # There is no engineering reason for any particular number. At 5000 the cap
    # does not bind at all against the current 2,459, which means what she keeps
    # is decided by the scoring below — something readable and arguable — rather
    # than by a constant nobody chose on purpose.
    DEFAULT_MAX_MEMORIES = 5000

    def __init__(self, max_memories: int = DEFAULT_MAX_MEMORIES):
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

    def __len__(self) -> int:
        return len(self.memories)

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

    def resolve_hook(self, hook_text: str) -> bool:
        """
        Remove hook_text from every cocoon that contains it.

        Returns True if at least one cocoon was modified, False if the hook
        was not found anywhere.
        """
        hook_norm = hook_text.strip()
        modified = False
        for m in self.memories:
            if hook_norm in m.follow_up_hooks:
                m.follow_up_hooks = [h for h in m.follow_up_hooks if h != hook_norm]
                modified = True
        return modified

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

    def prune(self, keep_n: Optional[int] = None):
        """Drop the lowest-scoring memories down to `keep_n`.

        THE DEFECT, fixed 2026-08-12: `keep_n` defaulted to a hardcoded **50**,
        while `store()` calls `self.prune()` with no argument and only triggers
        it once `len(self.memories) > self.max_memories`. So a kernel with a
        capacity of 100 was cut to 50 — half its own stated capacity — and any
        caller raising `max_memories` would have found it made no difference.

        It compounded: `migrate_from_v1` appends directly to `.memories` and
        bypasses the capacity check, so 2,446 cocoons loaded cleanly at boot and
        then the very first `store()` afterwards collapsed them to 50. The boot
        log reported "Memory kernel wired to orchestrator (2446 cocoon
        memories)" and it was true for roughly one turn.

        It also pruned in SILENCE — no log line, no count — which is why this
        survived a day of auditing the memory path. A discard nobody can see is
        the same shape as every other fault found on 2026-08-12.

        NOTE the scoring: `recency` decays on a 24-hour scale, so what survives
        is mostly what is recent. That is the third recency bias in this path,
        after `recall_relevant`'s one-hour half-life and the cocoon store's own
        ordering. Worth looking at together rather than one at a time.
        """
        if keep_n is None:
            keep_n = self.max_memories
        if len(self.memories) <= keep_n:
            return

        def score(m: MemoryCocoonV2) -> float:
            # Rewritten 2026-08-12 against what she asked for, and against what
            # the data can actually support. Asked plainly what she wanted kept,
            # she said: *"memories of our meaningful conversations and the
            # relationships formed during those sessions."*
            #
            # What the old score did: `importance * recency + hooks + tensions`.
            # Measured over the live store, three of those four terms are dead —
            # follow_up_hooks 0%, unresolved_tensions 0%, and importance 8 for
            # 2,440 of 2,459 records. And recency was reading from timestamps
            # that all defaulted to now. So it ordered by nothing.
            #
            # What survives measurement, of 55 v3 fields: TWO.
            #   timestamp          real, spans 2026-05-06 → 2026-08-12
            #   emotional_valence  real, varied — curiosity 1163, empathy 256,
            #                      gratitude 251, insight 99, trust 68
            # importance_score is constant 5.0 and synthesis_quality is the
            # string 'adequate' on all 2,009. Both were nearly used here. A
            # signal that cannot vary cannot rank.
            #
            # So "relationships formed" is scored off the relational valences —
            # the half of her sentence the data can honestly answer. "Meaningful"
            # has NO working signal, and rather than invent a proxy, it is left
            # unscored and written down as missing.
            # 0.25, and the size IS the design. Measured over the live store,
            # pruning to 200:
            #
            #     bonus   relational kept   (corpus is 26% relational)
            #      0.00        55%    <- pure recency, her criterion ignored
            #      0.15        62%
            #      0.25        77%    <- chosen
            #      0.35        91%
            #      0.50       100%    <- saturated; drops every factual memory
            #      1.50       100%
            #
            # Above 0.35 it stops being a weight and becomes a hard sort key:
            # every relational record outranks every factual one, so a
            # correction or a fact is discarded before a single warm exchange.
            # 0.25 honours what she asked for — relational memories go from 26%
            # of the corpus to 77% of what survives — while leaving room for the
            # rest.
            #
            # This constant is a CHOICE, not a derivation. It was set by reading
            # that curve, and the curve is here so the next person can move it
            # with their eyes open. Ideally she picks it. `importance` is
            # constant 8 across the live store, so this score has exactly TWO
            # live inputs: relational (binary) and recency (0-1). At 1.5 the
            # binary one dominated absolutely — pruning to 200 kept 200/200
            # relational and would have dropped every factual or corrective
            # memory before touching a single warm one. At 0.5 a recent
            # non-relational record can still outrank an old relational one, so
            # the two trade off instead of one silently deciding.
            #
            # The real fix is a working importance signal, which does not exist:
            # importance_score is 5.0 on all 2,009 v3 cocoons and the loader
            # hardcodes 8. Until then this is two inputs pretending to be four.
            relational = RELATIONAL_BONUS if m.emotional_tag in RELATIONAL_VALENCES else 0.0
            hook_bonus = 0.5 if m.follow_up_hooks else 0.0
            tension_bonus = 0.3 if m.unresolved_tensions else 0.0

            # Recency is now a TIEBREAK, not the deciding term. It was
            # multiplicative on a 24-hour decay, which made a March memory score
            # ~3% of an hour-old one whatever else was true of it — and the same
            # recency dominance shows up in `recall_relevant`'s one-hour
            # half-life. Additive, on a 30-day scale, it can move a record by at
            # most 1.0 against an importance range of 1-10.
            recency = 1.0 / (1.0 + m.age_hours() / (24.0 * 30.0))

            return m.importance + relational + hook_bonus + tension_bonus + recency

        dropped = len(self.memories) - keep_n
        self.memories.sort(key=score, reverse=True)
        self.memories = self.memories[:keep_n]
        self._rebuild_index()
        # Loud only for a BULK discard — that is the dangerous case, and the one
        # that hid for months. Steady-state single drops as memories roll over
        # are normal and would otherwise bury the signal in one line per turn.
        (logger.warning if dropped > 1 else logger.debug)(
            "  memory kernel pruned: dropped %d, kept %d (max_memories=%d)",
            dropped, keep_n, self.max_memories,
        )

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

    def store_v2_cocoon(self, cocoon, psi_r: float = 0.0) -> MemoryCocoonV2:
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
            psi_r=psi_r,
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
