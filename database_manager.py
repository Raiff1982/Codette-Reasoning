"""
DatabaseManager — general-purpose SQLite persistence for Codette.

Manages codette_core.db, which holds:
  - messages   : conversation / awareness event log
  - feedback   : REST API feedback signals (CognitiveUnit.receive_feedback)
  - turns      : REST API turn history

Separate from:
  - data/codette_memory.db  (UnifiedMemory — cocoon store + FTS5)
  - data/codette_sessions.db (SessionStore — full session snapshots)

Usage:
    from database_manager import DatabaseManager
    db = DatabaseManager()
    with db.get_connection() as conn:
        conn.execute("INSERT INTO messages ...")
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Resolve data/ directory relative to this file (project root)
_DATA_DIR = Path(__file__).parent / "data"
DB_PATH = _DATA_DIR / "codette_core.db"


class DatabaseManager:
    """Thread-safe SQLite manager for Codette's general-purpose persistence.

    All connections share WAL mode so concurrent readers never block writes.
    A module-level instance is created on first import via get_default().
    """

    _default: Optional["DatabaseManager"] = None
    _default_lock = threading.Lock()

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()
        self._init_schema()
        logger.info(f"[DatabaseManager] Initialized at {self.db_path}")

    # ── Connection management ─────────────────────────────────────────────────

    @contextmanager
    def get_connection(self):
        """Context manager yielding a SQLite connection.

        The connection is created fresh per call (thread-safe) and closed on exit.
        WAL mode allows concurrent readers; writes are serialized via _write_lock
        by the caller or by the DB engine itself.
        """
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
        finally:
            conn.close()

    # ── Schema ────────────────────────────────────────────────────────────────

    def _init_schema(self):
        with self.get_connection() as conn:
            # General-purpose message / event log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts       REAL    NOT NULL DEFAULT (unixepoch('now', 'subsec')),
                    conversation_id TEXT NOT NULL DEFAULT 'SYSTEM',
                    role     TEXT    NOT NULL DEFAULT 'system',
                    content  TEXT    NOT NULL,
                    metadata TEXT    NOT NULL DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id, ts DESC)
            """)

            # REST API feedback signals
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts         REAL    NOT NULL DEFAULT (unixepoch('now', 'subsec')),
                    session_id TEXT    NOT NULL,
                    helpful    INTEGER NOT NULL,   -- 1=helpful, 0=not
                    note       TEXT    NOT NULL DEFAULT ''
                )
            """)

            # REST API turn history (lightweight — no full adapter pipeline data)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS turns (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts         REAL    NOT NULL DEFAULT (unixepoch('now', 'subsec')),
                    session_id TEXT    NOT NULL,
                    query      TEXT    NOT NULL,
                    response   TEXT    NOT NULL,
                    intent_json TEXT   NOT NULL DEFAULT '{}',
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_turns_session
                ON turns(session_id, ts DESC)
            """)

            conn.commit()

    # ── Write helpers ─────────────────────────────────────────────────────────

    def log_message(
        self,
        content: str,
        role: str = "system",
        conversation_id: str = "SYSTEM",
        metadata: Optional[dict] = None,
    ) -> int:
        """Insert a row into messages. Returns the new row id."""
        meta_str = json.dumps(metadata or {})
        with self._write_lock:
            with self.get_connection() as conn:
                cur = conn.execute(
                    "INSERT INTO messages (conversation_id, role, content, metadata) "
                    "VALUES (?, ?, ?, ?)",
                    (conversation_id, role, content, meta_str),
                )
                conn.commit()
                return cur.lastrowid

    def log_feedback(self, session_id: str, helpful: bool, note: str = "") -> int:
        """Record a feedback signal. Returns the new row id."""
        with self._write_lock:
            with self.get_connection() as conn:
                cur = conn.execute(
                    "INSERT INTO feedback (session_id, helpful, note) VALUES (?, ?, ?)",
                    (session_id, int(helpful), note),
                )
                conn.commit()
                return cur.lastrowid

    def log_turn(
        self,
        session_id: str,
        query: str,
        response: str,
        intent: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> int:
        """Record a completed turn. Returns the new row id."""
        with self._write_lock:
            with self.get_connection() as conn:
                cur = conn.execute(
                    "INSERT INTO turns (session_id, query, response, intent_json, metadata_json) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        session_id,
                        query,
                        response,
                        json.dumps(intent or {}),
                        json.dumps(metadata or {}),
                    ),
                )
                conn.commit()
                return cur.lastrowid

    # ── Read helpers ──────────────────────────────────────────────────────────

    def get_messages(
        self,
        conversation_id: str = "SYSTEM",
        limit: int = 50,
    ) -> list[dict]:
        """Return recent messages for a conversation, newest first."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT id, ts, conversation_id, role, content, metadata "
                "FROM messages WHERE conversation_id = ? ORDER BY ts DESC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_turns(self, session_id: str, limit: int = 20) -> list[dict]:
        """Return recent turns for a session, newest first."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT id, ts, session_id, query, response, intent_json, metadata_json "
                "FROM turns WHERE session_id = ? ORDER BY ts DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["intent"]   = json.loads(d.pop("intent_json", "{}"))
            d["metadata"] = json.loads(d.pop("metadata_json", "{}"))
            result.append(d)
        return result

    def stats(self) -> dict:
        """Return row counts for all tables."""
        with self.get_connection() as conn:
            return {
                "messages": conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
                "feedback": conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0],
                "turns":    conn.execute("SELECT COUNT(*) FROM turns").fetchone()[0],
                "db_path":  str(self.db_path),
                "db_size_kb": round(self.db_path.stat().st_size / 1024, 1)
                              if self.db_path.exists() else 0,
            }

    # ── Module-level default instance ────────────────────────────────────────

    @classmethod
    def get_default(cls) -> "DatabaseManager":
        """Return (and lazily create) the module-level singleton."""
        if cls._default is None:
            with cls._default_lock:
                if cls._default is None:
                    cls._default = cls()
        return cls._default


# Convenience alias used by load_codette_awareness.py and any other caller
# that does `from database_manager import DatabaseManager; db = DatabaseManager()`
# — each call creates its own instance but they all share the same db file.
