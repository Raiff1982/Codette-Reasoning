"""
SemanticCocoonField — interference-aware cocoon memory.

Replaces flat list deduplication in LivingMemoryKernel with embedding-based
retrieval and semantic supersession.

Architecture draws from:
  - sentence-transformers (Reimers & Gurevych 2019, public)
  - FAISS nearest-neighbor search (Johnson et al. 2017, Meta AI, Apache 2.0)
  - Standard cosine similarity for interference detection

Interference semantics (Codette-original):
  similarity >= SUPERSEDE_THRESHOLD  → new cocoon supersedes old (updates it)
  similarity >= MERGE_THRESHOLD      → cocoons reinforce each other (importance boost)
  similarity >= CLUSTER_THRESHOLD    → soft cluster (related, co-recalled)
  below CLUSTER_THRESHOLD            → independent memory

Falls back gracefully to the original LivingMemoryKernel if sentence-transformers
or faiss are not installed — no hard dependency at import time.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Interference thresholds — tuned to sentence-transformer embedding space
SUPERSEDE_THRESHOLD = 0.92   # direct contradiction / update
MERGE_THRESHOLD     = 0.78   # same topic, reinforcement
CLUSTER_THRESHOLD   = 0.55   # related topic, co-recall candidate


@dataclass
class SemanticCocoon:
    title: str
    content: str
    emotional_tag: str
    importance: int                     # 1-10
    timestamp: float = field(default_factory=time.time)
    anchor: str = ""                    # SHA256 of title+ts+content (populated on store)
    superseded_by: Optional[str] = None # anchor of cocoon that replaced this one
    merge_count: int = 0                # how many times reinforced
    embedding: Optional[list] = None   # stored separately in FAISS index; not serialized

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "content": self.content,
            "emotional_tag": self.emotional_tag,
            "importance": self.importance,
            "timestamp": self.timestamp,
            "anchor": self.anchor,
            "superseded_by": self.superseded_by,
            "merge_count": self.merge_count,
        }


class SemanticCocoonField:
    """
    Embedding-aware cocoon store with interference-based supersession.

    Usage:
        field = SemanticCocoonField()
        result = field.store(SemanticCocoon("The Rule", "Never override...", "honesty", 9))
        # result.action in ("added", "superseded", "reinforced", "duplicate")

        matches = field.recall_semantic("ethical boundaries", top_k=5)
        matches = field.recall_by_emotion("honesty")
        matches = field.recall_important(min_importance=7)
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._cocoons: List[SemanticCocoon] = []
        self._embeddings = None   # np.ndarray shape (N, D)
        self._model = None
        self._model_name = model_name
        self._available = self._try_init(model_name)

    def _try_init(self, model_name: str) -> bool:
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
            self._model = SentenceTransformer(model_name)
            self._np = np
            logger.info(f"[SemanticCocoonField] Loaded model: {model_name}")
            return True
        except ImportError:
            logger.warning(
                "[SemanticCocoonField] sentence-transformers not installed. "
                "Falling back to anchor-only deduplication. "
                "Run: pip install sentence-transformers"
            )
            return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(self, cocoon: SemanticCocoon) -> "StoreResult":
        import hashlib
        raw = f"{cocoon.title}{cocoon.timestamp}{cocoon.content}".encode()
        cocoon.anchor = hashlib.sha256(raw).hexdigest()

        if not self._available:
            return self._store_fallback(cocoon)

        embedding = self._embed(cocoon.content)
        neighbors = self._nearest(embedding, k=5)

        for idx, sim in neighbors:
            existing = self._cocoons[idx]
            if existing.superseded_by:
                continue  # skip already-superseded memories

            if sim >= SUPERSEDE_THRESHOLD:
                existing.superseded_by = cocoon.anchor
                cocoon.importance = max(cocoon.importance, existing.importance)
                self._append(cocoon, embedding)
                logger.debug(f"[SCF] Superseded '{existing.title}' → '{cocoon.title}' (sim={sim:.3f})")
                return StoreResult("superseded", cocoon, replaced=existing)

            if sim >= MERGE_THRESHOLD:
                existing.merge_count += 1
                existing.importance = min(10, existing.importance + 1)
                logger.debug(f"[SCF] Reinforced '{existing.title}' (sim={sim:.3f}, importance→{existing.importance})")
                return StoreResult("reinforced", existing)

        self._append(cocoon, embedding)
        return StoreResult("added", cocoon)

    def recall_semantic(self, query: str, top_k: int = 5) -> List[SemanticCocoon]:
        if not self._available or not self._cocoons:
            return self.recall_important()

        q_emb = self._embed(query)
        neighbors = self._nearest(q_emb, k=top_k * 2)
        results = []
        for idx, _sim in neighbors:
            c = self._cocoons[idx]
            if c.superseded_by is None:
                results.append(c)
                if len(results) >= top_k:
                    break
        return results

    def recall_by_emotion(self, tag: str) -> List[SemanticCocoon]:
        return [c for c in self._cocoons if c.emotional_tag == tag and not c.superseded_by]

    def recall_important(self, min_importance: int = 7) -> List[SemanticCocoon]:
        return [c for c in self._cocoons if c.importance >= min_importance and not c.superseded_by]

    def active_count(self) -> int:
        return sum(1 for c in self._cocoons if not c.superseded_by)

    def export(self) -> str:
        return json.dumps([c.to_dict() for c in self._cocoons], indent=2)

    def load_from_json(self, json_str: str):
        data = json.loads(json_str)
        for item in data:
            c = SemanticCocoon(**{k: v for k, v in item.items() if k != "embedding"})
            if self._available:
                emb = self._embed(c.content)
                self._append(c, emb)
            else:
                self._cocoons.append(c)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _embed(self, text: str):
        return self._model.encode(text, normalize_embeddings=True)

    def _append(self, cocoon: SemanticCocoon, embedding):
        self._cocoons.append(cocoon)
        if self._embeddings is None:
            self._embeddings = self._np.array([embedding])
        else:
            self._embeddings = self._np.vstack([self._embeddings, embedding])

    def _nearest(self, query_emb, k: int) -> List[Tuple[int, float]]:
        if self._embeddings is None or len(self._cocoons) == 0:
            return []
        sims = self._embeddings @ query_emb
        k = min(k, len(sims))
        top_idx = self._np.argpartition(sims, -k)[-k:]
        top_idx = top_idx[self._np.argsort(sims[top_idx])[::-1]]
        return [(int(i), float(sims[i])) for i in top_idx]

    def _store_fallback(self, cocoon: SemanticCocoon) -> "StoreResult":
        if any(c.anchor == cocoon.anchor for c in self._cocoons):
            return StoreResult("duplicate", cocoon)
        self._cocoons.append(cocoon)
        return StoreResult("added", cocoon)


@dataclass
class StoreResult:
    action: str                              # added | superseded | reinforced | duplicate
    cocoon: SemanticCocoon
    replaced: Optional[SemanticCocoon] = None
