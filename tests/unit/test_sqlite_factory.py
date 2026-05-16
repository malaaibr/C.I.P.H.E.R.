"""Unit tests for SQLite factory (T-009). DoD: All 3 DBs created, WAL mode."""

from __future__ import annotations

from pathlib import Path

import pytest

from cipher.core.adapters.sqlite_factory import (
    create_audit_db,
    create_checkpoints_db,
    create_cipher_db,
)


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    return tmp_path / "sqlite"


class TestCipherDb:
    def test_creates_with_wal(self, tmp_data_dir: Path) -> None:
        conn = create_cipher_db(tmp_data_dir)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
        conn.close()

    def test_tables_exist(self, tmp_data_dir: Path) -> None:
        conn = create_cipher_db(tmp_data_dir)
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "config" in tables
        assert "agent_registry" in tables
        conn.close()


class TestAuditDb:
    def test_creates_with_wal(self, tmp_data_dir: Path) -> None:
        conn = create_audit_db(tmp_data_dir)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
        conn.close()

    def test_append_only_insert(self, tmp_data_dir: Path) -> None:
        conn = create_audit_db(tmp_data_dir)
        conn.execute(
            "INSERT INTO audit_log (agent_id, action, detail_json) VALUES (?, ?, ?)",
            ("devnex", "llm_call", '{"backend": "ollama"}'),
        )
        conn.commit()
        row = conn.execute("SELECT agent_id, action FROM audit_log").fetchone()
        assert row == ("devnex", "llm_call")
        conn.close()


class TestCheckpointsDb:
    def test_creates_with_wal(self, tmp_data_dir: Path) -> None:
        conn = create_checkpoints_db(tmp_data_dir)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
        conn.close()

    def test_tables_exist(self, tmp_data_dir: Path) -> None:
        conn = create_checkpoints_db(tmp_data_dir)
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "checkpoints" in tables
        assert "writes" in tables
        conn.close()

    def test_idempotent(self, tmp_data_dir: Path) -> None:
        conn1 = create_checkpoints_db(tmp_data_dir)
        conn1.close()
        conn2 = create_checkpoints_db(tmp_data_dir)
        conn2.close()
