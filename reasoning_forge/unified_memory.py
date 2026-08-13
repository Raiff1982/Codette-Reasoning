"""
Codette Unified Memory — SQLite + FTS5 Backed Cocoon Store
===========================================================

Consolidates three previously separate memory systems:
1. CognitionCocooner (JSON files on disk)
2. LivingMemoryKernel (in-memory MemoryCocoons)
3. CodetteSession (SQLite conversation state)

Into ONE system with:
- SQLite backing for persistence + ACID guarantees
- FTS5 full-text search for fast relevance matching (replaces O(n) file scan)
- In-memory LRU cache for hot cocoons
- Unified API for store/recall/search
- Migration from legacy JSON cocoons on first load

Schema:
    cocoons(id, query, response, adapter, domain, complexity, emotion,
            importance, timestamp, metadata_json)
    cocoons_fts(query, response)  -- FTS5 virtual table

Author: Jonathan Harrison (Raiff's Bits LLC)
"""

import json
import math
import sqlite3
import threading

# Shared cocoon-quality signal (demotion-only; see cocoon_authority.py). Guarded
# import so recall degrades to unfiltered behaviour if the module is unavailable.
try:
    from reasoning_forge.cocoon_authority import authority as _cocoon_authority
except Exception:  # pragma: no cover
    try:
        from cocoon_authority import authority as _cocoon_authority
    except Exception:
        _cocoon_authority = None
import time
import hashlib
import os
import logging
import datetime as _dt

# ── When the stored `success` flag started meaning what it says ───────────────
#
# Until 2026-08-13, `codette_server` set a cocoon's `success` field to False on
# ANY warning from `behavior_governor.post_validate`. The dominant contributor
# was `_did_answer_question`, a keyword-overlap check its own docstring measures
# as inverted — it passed parroted responses at 100% and real answers at 47.5%,
# and fired on roughly half of all turns.
#
# So for every cocoon written before that fix, `success` is not a quality
# reading. Measured over the 3,841 cocoons in the live store, responses that
# echo their own query carry a mean success_score of 0.928 against 0.633 for
# everything else — a 47% advantage, to exactly the responses the flag existed
# to catch. Recall ranked on it, so her echoes were retrieved first and injected
# into the following turn.
#
# Cocoons older than this are not rewritten and not deleted. The flag is simply
# not consulted for the period in which it cannot mean what it says, and the
# ranking renormalises over the signals that were actually measured. If nothing
# in the store is newer than this, the success term drops out entirely — which
# is the honest state until real readings accumulate.
SUCCESS_FLAG_TRUSTED_FROM = _dt.datetime(2026, 8, 13, 8, 0, 0).timestamp()
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import OrderedDict

logger = logging.getLogger(__name__)

DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "codette_memory.db"
LEGACY_COCOON_DIR = Path(__file__).parent.parent / "cocoons"

# In-memory cache size
CACHE_MAX = 200


class UnifiedMemory:
    """
    Single source of truth for all Codette memory.

    Replaces CognitionCocooner + LivingMemoryKernel + session memory
    with one SQLite-backed store using FTS5 for fast relevance search.
    """

    def __init__(self, db_path: Optional[Path] = None,
                 legacy_dir: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.legacy_dir = legacy_dir or LEGACY_COCOON_DIR

        # In-memory LRU cache (id -> cocoon dict)
        self._cache: OrderedDict = OrderedDict()

        # Serialize all writes — SQLite's shared connection isn't write-safe across threads.
        # Reads are safe because WAL mode (set below) allows concurrent readers.
        self._write_lock = threading.Lock()

        # Initialize database
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # WAL mode: readers don't block writers and writers don't block readers.
        # This is the single biggest concurrency win for a multi-threaded server.
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

        # Stats
        self._total_stored = self._count()
        self._cache_hits = 0
        self._cache_misses = 0

        # Migrate legacy cocoons on first use
        if self._total_stored == 0 and self.legacy_dir.exists():
            self._migrate_legacy()

        logger.info(f"UnifiedMemory: {self._total_stored} cocoons in {self.db_path}")

    def _init_schema(self):
        """Create tables and FTS5 index if they don't exist."""
        cur = self._conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS cocoons (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                adapter TEXT DEFAULT 'unknown',
                domain TEXT DEFAULT 'general',
                complexity TEXT DEFAULT 'MEDIUM',
                emotion TEXT DEFAULT 'neutral',
                importance INTEGER DEFAULT 7,
                timestamp REAL NOT NULL,
                metadata_json TEXT DEFAULT '{}'
            )
        """)

        # FTS5 virtual table for fast full-text search
        cur.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS cocoons_fts
            USING fts5(query, response, content='cocoons', content_rowid='rowid')
        """)

        # Triggers to keep FTS in sync
        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS cocoons_ai AFTER INSERT ON cocoons BEGIN
                INSERT INTO cocoons_fts(rowid, query, response)
                VALUES (new.rowid, new.query, new.response);
            END
        """)
        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS cocoons_ad AFTER DELETE ON cocoons BEGIN
                INSERT INTO cocoons_fts(cocoons_fts, rowid, query, response)
                VALUES ('delete', old.rowid, old.query, old.response);
            END
        """)
        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS cocoons_au AFTER UPDATE ON cocoons BEGIN
                INSERT INTO cocoons_fts(cocoons_fts, rowid, query, response)
                VALUES ('delete', old.rowid, old.query, old.response);
                INSERT INTO cocoons_fts(rowid, query, response)
                VALUES (new.rowid, new.query, new.response);
            END
        """)

        # Index on timestamp for recency queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_cocoons_timestamp
            ON cocoons(timestamp DESC)
        """)

        # Index on adapter for dominance analysis
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_cocoons_adapter
            ON cocoons(adapter)
        """)

        self._conn.commit()

    def _count(self) -> int:
        """Count total cocoons in database."""
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM cocoons")
        return cur.fetchone()[0]

    # ─────────────────────────────────────────────────────────
    # STORE
    # ─────────────────────────────────────────────────────────
    def store(self, query: str, response: str, adapter: str = "unknown",
              domain: str = "general", complexity: str = "MEDIUM",
              emotion: str = "neutral", importance: int = 7,
              metadata: Optional[Dict] = None) -> str:
        """
        Store a reasoning exchange as a cocoon.

        This is the unified replacement for:
        - CognitionCocooner.wrap_reasoning()
        - LivingMemoryKernel.store()
        - CodetteSession.add_message()

        Returns cocoon ID.
        """
        cocoon_id = f"cocoon_{int(time.time())}_{hashlib.md5(query.encode()).hexdigest()[:6]}"
        timestamp = time.time()
        meta_json = json.dumps(metadata or {})

        try:
            with self._write_lock:
                cur = self._conn.cursor()
                cur.execute("""
                    INSERT OR REPLACE INTO cocoons
                    (id, query, response, adapter, domain, complexity, emotion,
                     importance, timestamp, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cocoon_id,
                    query[:500],      # Cap query length
                    response[:2000],  # Cap response length
                    adapter,
                    domain,
                    complexity,
                    emotion,
                    importance,
                    timestamp,
                    meta_json,
                ))
                self._conn.commit()
                self._total_stored += 1

            # Cache it (lock-free — OrderedDict ops are GIL-protected)
            cocoon = {
                "id": cocoon_id, "query": query[:500], "response": response[:2000],
                "adapter": adapter, "domain": domain, "complexity": complexity,
                "emotion": emotion, "importance": importance,
                "timestamp": timestamp, "metadata": metadata or {},
            }
            self._cache_put(cocoon_id, cocoon)

            return cocoon_id
        except Exception as e:
            logger.error(f"Failed to store cocoon: {e}")
            return ""

    # ─────────────────────────────────────────────────────────
    # RECALL — FTS5 powered relevance search
    # ─────────────────────────────────────────────────────────
    def recall_relevant(self, query: str, max_results: int = 3,
                        min_importance: int = 0,
                        identity_id: str = "",
                        recency_weight: float = 0.3,
                        success_weight: float = 0.2,
                        identity_weight: float = 0.2) -> List[Dict]:
        """
        Find cocoons relevant to a query using FTS5 + multi-signal ranking.

        Ranking combines four signals:
        1. FTS5 relevance (text match quality) — base signal
        2. Recency — newer cocoons rank higher (exponential decay)
        3. Success — cocoons marked as successful rank higher
        4. Identity — cocoons linked to the current user rank higher

        Weight params control the balance (0.0 = disabled, 1.0 = dominant).
        """
        if not query.strip():
            return self.recall_recent(max_results)

        # Build FTS5 query: extract significant words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "can", "to", "of", "in", "for", "on",
            "with", "at", "by", "from", "as", "and", "but", "or", "if",
            "it", "its", "this", "that", "i", "me", "my", "we", "you",
            "what", "how", "why", "when", "where", "who", "about", "just",
            "not", "no", "so", "very", "really", "also", "too", "up",
        }
        words = [
            w.strip(".,!?;:\"'()[]{}").lower()
            for w in query.split()
            if len(w) > 2 and w.lower().strip(".,!?;:\"'()[]{}") not in stop_words
        ]

        if not words:
            return self.recall_recent(max_results)

        # FTS5 query: OR-join significant words
        fts_query = " OR ".join(f'"{w}"' for w in words[:8])  # Cap at 8 terms

        # Fetch more candidates than needed for re-ranking
        fetch_limit = max(max_results * 4, 12)

        try:
            cur = self._conn.cursor()
            sql = """
                SELECT c.id, c.query, c.response, c.adapter, c.domain,
                       c.complexity, c.emotion, c.importance, c.timestamp,
                       c.metadata_json,
                       rank
                FROM cocoons_fts
                JOIN cocoons c ON cocoons_fts.rowid = c.rowid
                WHERE cocoons_fts MATCH ?
                  AND c.importance >= ?
                ORDER BY rank
                LIMIT ?
            """
            cur.execute(sql, (fts_query, min_importance, fetch_limit))
            rows = cur.fetchall()

            if not rows:
                return self.recall_recent(max_results)

            # Multi-signal re-ranking
            now = time.time()
            scored = []
            for row in rows:
                cocoon = dict(row)
                cocoon["metadata"] = json.loads(cocoon.pop("metadata_json", "{}"))

                # Base: FTS5 rank (negative = better match, normalize to 0-1)
                fts_score = 1.0 / (1.0 + abs(cocoon.get("rank", 0)))

                # Recency: exponential decay (half-life = 1 hour)
                age_seconds = now - cocoon.get("timestamp", now)
                recency_score = math.exp(-age_seconds / 3600.0)

                # Success: check metadata for success marker
                #
                # 2026-08-13. This read `meta.get("success", True)` — absence
                # scored the MAXIMUM — and the flag it trusted was written by
                # `behavior_governor._did_answer_question`, a keyword-overlap
                # check measured as inverted: it passed parroted responses at
                # 100% and real answers at 47.5%, and `codette_server` turned any
                # warning from it into `success: False` on the stored cocoon.
                #
                # So the ranking signal was backwards where it mattered most.
                # Measured over her live store, 3,841 cocoons:
                #
                #     responses echoing the query   mean success_score 0.928 (n=1344)
                #     everything else                                  0.633 (n=2497)
                #
                # Her echoes outranked her answers by 47% on this term, were
                # recalled first, and were injected back into the next turn —
                # which is a machine for making her repeat herself, and it is
                # upstream of every echo detector built to catch the result.
                #
                # Two fixes, both the pattern already used throughout: absence is
                # not a value, and a reading from an instrument known to be
                # inverted is not evidence. Unmeasured or untrusted, the term is
                # OMITTED and the remaining weights renormalised — the same
                # treatment `QualitySignal.tension` gets — rather than
                # substituted with a number nobody measured.
                #
                # Nothing is rewritten. The stored flags stay exactly as written;
                # they are simply not consulted for the period in which they
                # cannot mean what they say.
                meta = cocoon.get("metadata", {})
                _raw_success = meta.get("success", None)
                _trustworthy = (
                    _raw_success is not None
                    and cocoon.get("timestamp", 0) >= SUCCESS_FLAG_TRUSTED_FROM
                )
                success_score = None
                if _trustworthy:
                    success_score = 1.0 if _raw_success else 0.3

                # Identity: boost if cocoon is linked to current user
                identity_score = 0.5  # neutral
                if identity_id:
                    cocoon_identity = meta.get("identity_id", "")
                    if cocoon_identity == identity_id:
                        identity_score = 1.0
                    elif cocoon_identity:
                        identity_score = 0.2  # different user's cocoon

                # Combined score (weighted).
                #
                # Omitted terms are renormalised across the ones that were
                # actually measured, so a cocoon is never penalised or rewarded
                # for a reading nobody took. Before this, relevance carried
                # 1.0 - 0.3 - 0.2 - 0.2 = 0.30 — exactly the same weight as
                # recency on its own, with 0.70 of the score going to signals
                # that say nothing about whether the memory answers the question.
                relevance_weight = 1.0 - recency_weight - success_weight - identity_weight
                terms = [
                    (relevance_weight, fts_score),
                    (recency_weight, recency_score),
                    (success_weight, success_score),
                    (identity_weight, identity_score),
                ]
                measured = [(w, v) for w, v in terms if v is not None and w > 0]
                total_w = sum(w for w, _ in measured)
                combined = (
                    sum(w * v for w, v in measured) / total_w if total_w > 0 else 0.0
                )

                # Authority demotion (2026-07-26): down-weight known-polluted
                # cocoons (parroter / meta-recall / boilerplate) so real sources
                # out-rank the parroter's later echoes. DEMOTION-ONLY (weight ≤ 1.0)
                # so a clean cocoon's score is unchanged — this cannot over-boost.
                if _cocoon_authority is not None:
                    auth = _cocoon_authority(cocoon)
                    combined *= auth.weight
                    if auth.flags:
                        cocoon["_authority"] = round(auth.weight, 3)
                        cocoon["_authority_flags"] = auth.flags

                cocoon["_rank_score"] = round(combined, 4)
                cocoon.pop("rank", None)
                scored.append(cocoon)

            # Sort by combined score (descending)
            scored.sort(key=lambda c: c["_rank_score"], reverse=True)

            results = scored[:max_results]
            self._cache_hits += len(results)
            return results

        except Exception as e:
            logger.debug(f"FTS5 ranked search failed: {e}")
            return self.recall_recent(max_results)

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Literal full-text search over the cocoon store.

        This is the method `/api/search` (and therefore the `cocoon_search` MCP
        tool) has always called. It did not exist, and the call site guarded it
        with `hasattr`, so the endpoint returned an empty list unconditionally
        from the day it was written — see the 2026-08-12 note in
        `docs/HANDOFF_2026-08-12.md`, which recorded the symptom as "two stores,
        the search covers one". There is one store; nothing was searching it.

        Deliberately NOT `recall_relevant`:

        * no recency/identity/authority re-ranking — this answers "is it in
          there", not "what should she remember now";
        * **no fallback to `recall_recent`**. `recall_relevant` substitutes the
          most recent cocoons when FTS matches nothing, which is right for
          recall and wrong for a search box: it turns "no match" into a page of
          unrelated results. An empty list here means an empty result.

        Returns dicts, not objects. Callers must use `row["field"]`.
        """
        if not query or not query.strip():
            return []

        # FTS5 needs its own escaping: a bare apostrophe or hyphen in user text
        # is syntax, not literal. Quote every term and double internal quotes.
        terms = [
            w.strip(".,!?;:\"'()[]{}").replace('"', '""')
            for w in query.split()
        ]
        terms = [t for t in terms if t]
        if not terms:
            return []
        fts_query = " OR ".join(f'"{t}"' for t in terms[:16])

        try:
            cur = self._conn.cursor()
            cur.execute("""
                SELECT c.id, c.query, c.response, c.adapter, c.domain,
                       c.complexity, c.emotion, c.importance, c.timestamp,
                       c.metadata_json, rank
                FROM cocoons_fts
                JOIN cocoons c ON cocoons_fts.rowid = c.rowid
                WHERE cocoons_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (fts_query, limit))
            results = []
            for row in cur.fetchall():
                cocoon = dict(row)
                cocoon["metadata"] = json.loads(cocoon.pop("metadata_json", None) or "{}")
                cocoon.pop("rank", None)
                results.append(cocoon)
            return results
        except Exception as e:
            logger.warning("UnifiedMemory.search failed for %r: %s", query, e)
            raise

    def recall_recent(self, limit: int = 5) -> List[Dict]:
        """Get N most recent cocoons."""
        try:
            cur = self._conn.cursor()
            cur.execute("""
                SELECT id, query, response, adapter, domain, complexity,
                       emotion, importance, timestamp, metadata_json
                FROM cocoons
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            rows = cur.fetchall()
            results = []
            for row in rows:
                cocoon = dict(row)
                cocoon["metadata"] = json.loads(cocoon.pop("metadata_json", "{}"))
                results.append(cocoon)
            return results
        except Exception as e:
            logger.debug(f"Recent recall failed: {e}")
            return []

    def recall_by_emotion(self, emotion: str, limit: int = 5) -> List[Dict]:
        """Recall cocoons with specific emotional tag."""
        try:
            cur = self._conn.cursor()
            cur.execute("""
                SELECT id, query, response, adapter, domain, complexity,
                       emotion, importance, timestamp, metadata_json
                FROM cocoons
                WHERE emotion = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (emotion, limit))
            return [dict(r) for r in cur.fetchall()]
        except Exception:
            return []

    def recall_by_domain(self, domain: str, limit: int = 5) -> List[Dict]:
        """Recall cocoons from a specific domain."""
        try:
            cur = self._conn.cursor()
            cur.execute("""
                SELECT id, query, response, adapter, domain, complexity,
                       emotion, importance, timestamp, metadata_json
                FROM cocoons
                WHERE domain = ?
                ORDER BY importance DESC, timestamp DESC
                LIMIT ?
            """, (domain, limit))
            results = []
            for row in cur.fetchall():
                cocoon = dict(row)
                cocoon["metadata"] = json.loads(cocoon.pop("metadata_json", "{}"))
                results.append(cocoon)
            return results
        except Exception:
            return []

    def recall_multi_domain(self, domains: List[str], limit_per: int = 3) -> List[Dict]:
        """Recall cocoons across multiple domains, limit_per each."""
        results = []
        for domain in domains:
            results.extend(self.recall_by_domain(domain, limit_per))
        # Also search by FTS for domain keywords not captured by exact match
        for domain in domains:
            fts_results = self.recall_relevant(domain, max_results=limit_per)
            for r in fts_results:
                if r.get("id") not in {c.get("id") for c in results}:
                    results.append(r)
        return results

    def recall_by_adapter(self, adapter: str, limit: int = 5) -> List[Dict]:
        """Recall cocoons generated by specific adapter."""
        try:
            cur = self._conn.cursor()
            cur.execute("""
                SELECT id, query, response, adapter, domain, complexity,
                       emotion, importance, timestamp, metadata_json
                FROM cocoons
                WHERE adapter = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (adapter, limit))
            return [dict(r) for r in cur.fetchall()]
        except Exception:
            return []

    def fetch_adapter_learning_signals(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Return recent cocoon records shaped for adapter performance learning."""
        try:
            cur = self._conn.cursor()
            cur.execute("""
                SELECT id, query, response, adapter, domain, complexity,
                       emotion, importance, timestamp, metadata_json
                FROM cocoons
                WHERE adapter IS NOT NULL
                  AND TRIM(adapter) != ''
                  AND adapter != 'unknown'
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            results = []
            for row in cur.fetchall():
                cocoon = dict(row)
                cocoon["metadata"] = json.loads(cocoon.pop("metadata_json", "{}"))
                results.append(cocoon)
            return results
        except Exception as e:
            logger.debug(f"Adapter learning fetch failed: {e}")
            return []

    def recall_important(self, min_importance: int = 7, limit: int = 10) -> List[Dict]:
        """Recall high-importance cocoons (replaces LivingMemoryKernel.recall_important)."""
        try:
            cur = self._conn.cursor()
            cur.execute("""
                SELECT id, query, response, adapter, domain, complexity,
                       emotion, importance, timestamp, metadata_json
                FROM cocoons
                WHERE importance >= ?
                ORDER BY importance DESC, timestamp DESC
                LIMIT ?
            """, (min_importance, limit))
            return [dict(r) for r in cur.fetchall()]
        except Exception:
            return []

    # ─────────────────────────────────────────────────────────
    # SUCCESS MARKING — for ranked recall feedback loop
    # ─────────────────────────────────────────────────────────
    def mark_success(self, cocoon_id: str, success: bool = True,
                      identity_id: str = ""):
        """
        Mark a cocoon as successful or unsuccessful.

        This feeds back into ranked recall — successful cocoons
        get boosted in future searches, unsuccessful ones get demoted.
        """
        try:
            with self._write_lock:
                cur = self._conn.cursor()
                cur.execute(
                    "SELECT metadata_json FROM cocoons WHERE id = ?",
                    (cocoon_id,)
                )
                row = cur.fetchone()
                if row:
                    meta = json.loads(row["metadata_json"] or "{}")
                    meta["success"] = success
                    if identity_id:
                        meta["identity_id"] = identity_id
                    cur.execute(
                        "UPDATE cocoons SET metadata_json = ? WHERE id = ?",
                        (json.dumps(meta), cocoon_id)
                    )
                    self._conn.commit()
        except Exception as e:
            logger.debug(f"mark_success failed: {e}")

    def store_value_analysis(
        self,
        title: str,
        analysis: Dict[str, Any],
        payload: Optional[Dict[str, Any]] = None,
        frontier: bool = False,
        importance: int = 8,
    ) -> str:
        """Persist a valuation or frontier analysis as a searchable cocoon."""
        mode = "risk_frontier" if frontier else "event_embedded_value"
        query = title[:500] or ("Risk frontier analysis" if frontier else "Singularity-aware value analysis")

        if frontier:
            best = (analysis or {}).get("best_scenario") or {}
            worst = (analysis or {}).get("worst_scenario") or {}
            response = (
                f"Risk frontier comparison completed. "
                f"Best scenario: {best.get('name', 'unknown')}. "
                f"Worst scenario: {worst.get('name', 'unknown')}. "
                f"Compared {len((analysis or {}).get('scenarios', []))} scenarios."
            )
        else:
            combined = (analysis or {}).get("combined_total")
            singularity = (analysis or {}).get("singularity_detected", False)
            response = (
                f"Singularity-aware valuation completed. Combined total={combined}. "
                f"Singularity detected={singularity}. "
                f"Mode={(analysis or {}).get('singularity_mode', 'strict')}."
            )

        metadata = {
            "analysis_type": mode,
            "payload": payload or {},
            "analysis": analysis or {},
            "success": True,
        }
        return self.store(
            query=query,
            response=response,
            adapter="event_embedded_value",
            domain="risk_frontier" if frontier else "singularity_analysis",
            complexity="COMPLEX",
            emotion="concerned" if not frontier else "analytical",
            importance=importance,
            metadata=metadata,
        )

    def recall_value_analyses(self, query: str = "", max_results: int = 5) -> List[Dict]:
        """Recall recent or relevant value-analysis cocoons."""
        if query.strip():
            results = self.recall_relevant(query, max_results=max_results)
            return [
                cocoon for cocoon in results
                if cocoon.get("metadata", {}).get("analysis_type") in {"event_embedded_value", "risk_frontier"}
            ]

        combined = self.recall_by_domain("singularity_analysis", max_results)
        combined.extend(self.recall_by_domain("risk_frontier", max_results))
        deduped = []
        seen = set()
        for cocoon in sorted(combined, key=lambda c: c.get("timestamp", 0), reverse=True):
            cid = cocoon.get("id")
            if cid in seen:
                continue
            seen.add(cid)
            deduped.append(cocoon)
        return deduped[:max_results]

    def store_web_research(
        self,
        query: str,
        summary: str,
        sources: List[Dict[str, Any]],
        importance: int = 8,
    ) -> str:
        """Persist cited web research as a searchable cocoon."""
        metadata = {
            "memory_type": "web_research",
            "sources": sources,
            "success": True,
        }
        return self.store(
            query=query,
            response=summary,
            adapter="web_research",
            domain="web_research",
            complexity="CURRENT",
            emotion="analytical",
            importance=importance,
            metadata=metadata,
        )

    def recall_web_research(self, query: str = "", max_results: int = 3) -> List[Dict]:
        """Recall relevant prior web research cocoons."""
        if query.strip():
            results = self.recall_relevant(query, max_results=max_results)
            return [
                cocoon for cocoon in results
                if cocoon.get("metadata", {}).get("memory_type") == "web_research"
            ]
        return self.recall_by_domain("web_research", max_results)

    # ─────────────────────────────────────────────────────────
    # INTROSPECTION — adapter dominance, domain clusters, trends
    # ─────────────────────────────────────────────────────────
    def adapter_dominance(self) -> Dict:
        """Analyze adapter usage distribution."""
        try:
            cur = self._conn.cursor()
            cur.execute("""
                SELECT adapter, COUNT(*) as cnt
                FROM cocoons
                GROUP BY adapter
                ORDER BY cnt DESC
            """)
            rows = cur.fetchall()
            total = sum(r["cnt"] for r in rows)
            if not total:
                return {"total_responses": 0, "dominant": None, "ratio": 0, "balanced": True}

            distribution = {r["adapter"]: r["cnt"] for r in rows}
            dominant = rows[0]["adapter"]
            ratio = rows[0]["cnt"] / total

            return {
                "total_responses": total,
                "dominant": dominant,
                "ratio": round(ratio, 3),
                "balanced": ratio <= 0.4,
                "distribution": distribution,
            }
        except Exception:
            return {"total_responses": 0, "dominant": None, "ratio": 0, "balanced": True}

    def domain_distribution(self) -> Dict:
        """Analyze domain distribution."""
        try:
            cur = self._conn.cursor()
            cur.execute("""
                SELECT domain, COUNT(*) as cnt
                FROM cocoons
                GROUP BY domain
                ORDER BY cnt DESC
            """)
            return {r["domain"]: r["cnt"] for r in cur.fetchall()}
        except Exception:
            return {}

    def complexity_distribution(self) -> Dict:
        """Analyze query complexity distribution."""
        try:
            cur = self._conn.cursor()
            cur.execute("""
                SELECT complexity, COUNT(*) as cnt
                FROM cocoons
                GROUP BY complexity
                ORDER BY cnt DESC
            """)
            return {r["complexity"]: r["cnt"] for r in cur.fetchall()}
        except Exception:
            return {}

    def response_length_trend(self, window: int = 20) -> List[int]:
        """Get response length trend (last N cocoons)."""
        try:
            cur = self._conn.cursor()
            cur.execute("""
                SELECT LENGTH(response) as len
                FROM cocoons
                ORDER BY timestamp DESC
                LIMIT ?
            """, (window,))
            return [r["len"] for r in cur.fetchall()][::-1]  # Chronological order
        except Exception:
            return []

    def full_introspection(self) -> Dict:
        """Full statistical self-analysis (replaces CocoonIntrospectionEngine)."""
        adapter = self.adapter_dominance()
        domains = self.domain_distribution()
        complexities = self.complexity_distribution()
        lengths = self.response_length_trend(20)
        avg_len = sum(lengths) / len(lengths) if lengths else 0

        observations = []
        total = adapter.get("total_responses", 0)
        observations.append(f"I've processed {total} reasoning exchanges.")

        if adapter.get("dominant"):
            ratio = adapter.get("ratio", 0)
            if ratio > 0.4:
                observations.append(
                    f"My {adapter['dominant']} adapter handles {ratio:.0%} of queries "
                    f"— that's dominant. I should diversify."
                )
            else:
                observations.append(
                    f"My adapter usage is balanced (most-used: {adapter['dominant']} at {ratio:.0%})."
                )

        if domains:
            top_domain = max(domains, key=domains.get)
            observations.append(f"Most common domain: {top_domain} ({domains[top_domain]} queries).")

        observations.append(f"Average response length: {avg_len:.0f} characters.")

        return {
            "total_cocoons": total,
            "adapter_dominance": adapter,
            "domain_distribution": domains,
            "complexity_distribution": complexities,
            "avg_response_length": round(avg_len),
            "response_length_trend": lengths,
            "observations": observations,
        }

    # ─────────────────────────────────────────────────────────
    # LEGACY MIGRATION
    # ─────────────────────────────────────────────────────────
    def _migrate_legacy(self):
        """Migrate legacy JSON cocoons and .cocoon files into SQLite.

        Only runs on a cold start (`_total_stored == 0`); live writes go
        straight to SQLite via `store()`. That one-shot behaviour is deliberate
        and is NOT changed here — re-running it against a populated database
        would duplicate every cocoon, and `store()` does not deduplicate.
        """
        migrated = 0
        skipped_types: Dict[str, int] = {}

        # Migrate JSON reasoning cocoons.
        #
        # This matched `type == "reasoning"` exactly until 2026-08-12. The
        # schema moved to `reasoning_v3` (cocoon_schema_v3.py) and the check was
        # never updated, so on a cold start 1,992 of 2,452 files on disk — 81% —
        # fell through to the `summary`/`quote` branch, failed that too, and
        # were dropped without a log line. Match the family, not one spelling.
        for f in sorted(self.legacy_dir.glob("cocoon_*.json")):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)

                _type = str(data.get("type") or "")
                if _type.startswith("reasoning"):
                    # v3 keeps the same `wrapped` block; fall back to the `v3`
                    # block for any record that carries only the newer shape.
                    wrapped = data.get("wrapped") or {}
                    _v3 = data.get("v3") or {}
                    _meta = wrapped.get("metadata") or {}
                    self.store(
                        query=wrapped.get("query") or _v3.get("query", ""),
                        response=(wrapped.get("response")
                                  or _v3.get("user_response_text")
                                  or _v3.get("response_summary", "")),
                        adapter=(wrapped.get("adapter")
                                 or _v3.get("dominant_perspective") or "unknown"),
                        domain=_meta.get("domain", "general"),
                        complexity=_meta.get("complexity", "MEDIUM"),
                        importance=7,
                        metadata=_meta or None,
                    )
                    migrated += 1
                elif "summary" in data or "quote" in data:
                    # Foundational memory cocoons
                    self.store(
                        query=data.get("title", f.stem),
                        response=data.get("summary", data.get("quote", "")),
                        adapter="memory_kernel",
                        emotion=data.get("emotion", "neutral"),
                        importance=8,
                    )
                    migrated += 1
                else:
                    # Count what we decline to import instead of dropping it in
                    # silence. This is how the v3 gap stayed invisible.
                    key = _type or "<no type>"
                    skipped_types[key] = skipped_types.get(key, 0) + 1
            except Exception as e:
                logger.debug(f"Migration skip {f.name}: {e}")
                skipped_types["<error>"] = skipped_types.get("<error>", 0) + 1

        # Migrate .cocoon files (EMG format)
        for f in sorted(self.legacy_dir.glob("*.cocoon")):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                meta = data.get("metadata", {})
                self.store(
                    query=meta.get("context", data.get("cocoon_id", f.stem))[:200],
                    response=meta.get("context", ""),
                    adapter="consciousness_stack",
                    emotion=data.get("emotional_classification", "neutral").lower(),
                    importance=data.get("importance_rating", 7),
                )
                migrated += 1
            except Exception:
                continue

        if migrated > 0:
            logger.info(f"Migrated {migrated} legacy cocoons to SQLite")
            self._total_stored = self._count()
        if skipped_types:
            logger.warning(
                "Migration left %d cocoon file(s) unimported: %s",
                sum(skipped_types.values()),
                ", ".join(f"{k}={v}" for k, v in sorted(skipped_types.items())),
            )

    # ─────────────────────────────────────────────────────────
    # CACHE
    # ─────────────────────────────────────────────────────────
    def _cache_put(self, key: str, value: Dict):
        """Add to LRU cache."""
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        while len(self._cache) > CACHE_MAX:
            self._cache.popitem(last=False)

    def _cache_get(self, key: str) -> Optional[Dict]:
        """Get from LRU cache."""
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache_hits += 1
            return self._cache[key]
        self._cache_misses += 1
        return None

    # ─────────────────────────────────────────────────────────
    # DIAGNOSTICS
    # ─────────────────────────────────────────────────────────
    def get_stats(self) -> Dict:
        """Memory system stats for health checks."""
        return {
            "total_cocoons": self._total_stored,
            "cache_size": len(self._cache),
            "cache_max": CACHE_MAX,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": (
                self._cache_hits / max(1, self._cache_hits + self._cache_misses)
            ),
            "db_path": str(self.db_path),
            "db_size_kb": round(self.db_path.stat().st_size / 1024, 1) if self.db_path.exists() else 0,
        }

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
