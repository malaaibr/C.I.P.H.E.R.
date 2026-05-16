"""Audit Journal — append-only SQLite audit log (T-026)."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from cipher.core.otel import traced


class AuditJournal:
    """Append-only audit log backed by audit.db."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    @traced(name="audit.record", attributes={"layer": "gcl"})
    async def record(
        self,
        agent_id: str,
        action: str,
        detail: dict[str, Any] | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
    ) -> int:
        cursor = self._conn.execute(
            "INSERT INTO audit_log (agent_id, action, detail_json, trace_id, span_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (agent_id, action, json.dumps(detail or {}), trace_id, span_id),
        )
        self._conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def query(
        self, agent_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        if agent_id:
            rows = self._conn.execute(
                "SELECT * FROM audit_log WHERE agent_id = ? ORDER BY id DESC LIMIT ?",
                (agent_id, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        cols = ["id", "timestamp", "agent_id", "action", "detail_json", "trace_id", "span_id"]
        return [dict(zip(cols, row)) for row in rows]
