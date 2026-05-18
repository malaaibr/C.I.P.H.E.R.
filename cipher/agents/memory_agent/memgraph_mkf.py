"""
MemgraphMkf — production MkfClient backed by Memgraph.

Implements the same sync `MkfClient` Protocol as `InMemoryMkf` so MemoryAgent
swaps adapters with no orchestrator changes.

Each call opens a short-lived event loop and session — fine for the MVP
volume (a handful of evidence checks per node run). For higher throughput
swap to a persistent driver via `asyncio.run_coroutine_threadsafe`.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
from typing import Any

log = logging.getLogger(__name__)

MEMGRAPH_DEFAULT_URI = "bolt://localhost:7687"
ARTIFACT_LABEL = "Artifact"


def _parse_host_port(uri: str) -> tuple[str, int]:
    """Strip the bolt:// prefix and return (host, port) for TCP probe."""
    s = uri
    if "://" in s:
        s = s.split("://", 1)[1]
    if "/" in s:
        s = s.split("/", 1)[0]
    if ":" in s:
        h, p = s.rsplit(":", 1)
        try:
            return h, int(p)
        except ValueError:
            return h, 7687
    return s, 7687


def memgraph_reachable(uri: str | None = None, timeout: float = 0.3) -> bool:
    """Cheap TCP probe before paying for the neo4j driver cold-start."""
    uri = uri or os.environ.get("MEMGRAPH_URI", MEMGRAPH_DEFAULT_URI)
    host, port = _parse_host_port(uri)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


class MemgraphMkf:
    """
    Sync facade over the async MemgraphClient.

    Schema convention (per HLD §4 MKF layer):
      (:Artifact { uri: STRING, node_id: STRING, asil: STRING })
    """

    def __init__(self, uri: str | None = None) -> None:
        self._uri = uri or os.environ.get("MEMGRAPH_URI", MEMGRAPH_DEFAULT_URI)

    # ── MkfClient protocol ────────────────────────────────────────────────

    def has(self, uri: str) -> bool:
        cypher = "MATCH (a:Artifact {uri:$uri}) RETURN count(a) AS c"
        rec = self._run(cypher, {"uri": uri})
        return bool(rec and rec.get("c", 0) > 0)

    def list_for_node(self, node_id: str) -> list[str]:
        cypher = "MATCH (a:Artifact {node_id:$nid}) RETURN a.uri AS uri"
        rows = self._run_all(cypher, {"nid": node_id})
        return [r["uri"] for r in rows if r.get("uri")]

    # ── Optional write side (used by Research → Memory ingest pipelines) ──

    def upsert(self, uri: str, *, node_id: str | None = None, asil: str | None = None) -> None:
        cypher = (
            "MERGE (a:Artifact {uri:$uri}) "
            "SET a.node_id = coalesce($nid, a.node_id), "
            "    a.asil = coalesce($asil, a.asil)"
        )
        self._run(cypher, {"uri": uri, "nid": node_id, "asil": asil})

    # ── Internal: bridge sync→async without leaking loops ─────────────────

    def _run(self, cypher: str, params: dict[str, Any]) -> dict[str, Any] | None:
        rows = self._run_all(cypher, params)
        return rows[0] if rows else None

    def _run_all(self, cypher: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        async def _go() -> list[dict[str, Any]]:
            from cipher.core.adapters.memgraph_client import MemgraphClient
            client = MemgraphClient(self._uri)
            await client.connect()
            try:
                async with client.driver.session() as session:
                    result = await session.run(cypher, params)
                    rows = [dict(rec) async for rec in result]
                    return rows
            finally:
                await client.close()

        try:
            return asyncio.run(_go())
        except Exception as e:
            log.warning("Memgraph query failed (%s); returning empty result. Cypher: %s",
                        e, cypher[:80])
            return []
