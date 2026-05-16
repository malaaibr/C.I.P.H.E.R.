"""SQLite store factory — creates WAL-mode databases for CIPHER (T-009)."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def _default_data_dir() -> Path:
    return Path(os.environ.get("CIPHER_SQLITE_DIR", "deploy/local/data/sqlite"))


def _ensure_wal(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")


def create_cipher_db(data_dir: Path | None = None) -> sqlite3.Connection:
    """Main configuration database."""
    path = (data_dir or _default_data_dir()) / "cipher.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    _ensure_wal(conn)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS config (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS agent_registry (
            agent_id    TEXT PRIMARY KEY,
            card_json   TEXT NOT NULL,
            registered_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    return conn


def create_audit_db(data_dir: Path | None = None) -> sqlite3.Connection:
    """Append-only audit journal."""
    path = (data_dir or _default_data_dir()) / "audit.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    _ensure_wal(conn)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL DEFAULT (datetime('now')),
            agent_id    TEXT NOT NULL,
            action      TEXT NOT NULL,
            detail_json TEXT NOT NULL DEFAULT '{}',
            trace_id    TEXT,
            span_id     TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_log(agent_id);
        CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(timestamp);
    """)
    conn.commit()
    return conn


def create_checkpoints_db(data_dir: Path | None = None) -> sqlite3.Connection:
    """LangGraph checkpoint store."""
    path = (data_dir or _default_data_dir()) / "checkpoints.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    _ensure_wal(conn)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS checkpoints (
            thread_id   TEXT NOT NULL,
            checkpoint_id TEXT NOT NULL,
            parent_id   TEXT,
            checkpoint  BLOB NOT NULL,
            metadata    TEXT NOT NULL DEFAULT '{}',
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (thread_id, checkpoint_id)
        );
        CREATE TABLE IF NOT EXISTS writes (
            thread_id   TEXT NOT NULL,
            checkpoint_id TEXT NOT NULL,
            task_id     TEXT NOT NULL,
            channel     TEXT NOT NULL,
            value       BLOB NOT NULL,
            PRIMARY KEY (thread_id, checkpoint_id, task_id, channel)
        );
    """)
    conn.commit()
    return conn
