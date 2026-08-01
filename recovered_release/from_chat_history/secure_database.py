"""
Recovered from a ChatGPT history export (history_2025-*.json) in the archives.
The source existed only inside the conversation transcript, never as a file.
"""

import sqlite3
from threading import Lock
from werkzeug.security import generate_password_hash, check_password_hash

class SecureDatabase:
    """Thread-safe SQLite database manager"""
    def __init__(self, db_path: str = "ai_system.db"):
        self.db_path = db_path
        self.lock = Lock()
        self._init_db()

    def _init_db(self):
        with self.lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE,
                    password_hash TEXT
                )""")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    query TEXT,
                    response TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )""")

    def create_user(self, username: str, password: str):
        with self.lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                        (username, generate_password_hash(password)))
            return conn.execute("SELECT id FROM users WHERE username=?", (username,) ).fetchone()[0]

    def authenticate(self, username: str, password: str) -> int:
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id,password_hash FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            if result and check_password_hash(result[1], password):
                return result[0]
            else:
                return None

    def log_interaction(self, user_id: int, query: str, response: str):
        with self.lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO interactions (user_id, query, response) VALUES (?, ?, ?)
            """, (user_id, query, response))
