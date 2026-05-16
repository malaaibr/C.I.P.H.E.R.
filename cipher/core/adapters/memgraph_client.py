"""Memgraph async client (T-006)."""

from __future__ import annotations

import os

from neo4j import AsyncGraphDatabase, AsyncDriver


def get_memgraph_uri() -> str:
    return os.environ.get("MEMGRAPH_URI", "bolt://localhost:7687")


class MemgraphClient:
    """Thin async wrapper around neo4j driver for Memgraph."""

    def __init__(self, uri: str | None = None) -> None:
        self._uri = uri or get_memgraph_uri()
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        self._driver = AsyncGraphDatabase.driver(self._uri)

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None

    @property
    def driver(self) -> AsyncDriver:
        if self._driver is None:
            raise RuntimeError("MemgraphClient not connected.")
        return self._driver

    async def health_check(self) -> int:
        async with self.driver.session() as session:
            result = await session.run("MATCH (n) RETURN count(n) AS cnt")
            record = await result.single()
            return record["cnt"] if record else 0
