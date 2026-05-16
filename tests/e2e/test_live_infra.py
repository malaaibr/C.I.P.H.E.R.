"""
Live Infrastructure Integration Tests.

Validates connectivity to all Docker Compose services.
Requires: docker compose up (all services running on localhost).
Mark: pytest -m e2e
"""

from __future__ import annotations

import asyncio

import pytest

pytestmark = pytest.mark.e2e


class TestRedisLive:
    @pytest.mark.asyncio
    async def test_redis_ping(self) -> None:
        import redis.asyncio as aioredis

        r = aioredis.from_url("redis://localhost:6379/0")
        assert await r.ping() is True
        await r.close()

    @pytest.mark.asyncio
    async def test_redis_set_get(self) -> None:
        import redis.asyncio as aioredis

        r = aioredis.from_url("redis://localhost:6379/0")
        await r.set("cipher:test:key", "integration_ok")
        val = await r.get("cipher:test:key")
        assert val == b"integration_ok"
        await r.delete("cipher:test:key")
        await r.close()


class TestMemgraphLive:
    @pytest.mark.asyncio
    async def test_memgraph_bolt_connection(self) -> None:
        from neo4j import AsyncGraphDatabase

        driver = AsyncGraphDatabase.driver("bolt://localhost:7687")
        async with driver.session() as session:
            result = await session.run("RETURN 1 AS n")
            record = await result.single()
            assert record["n"] == 1
        await driver.close()

    @pytest.mark.asyncio
    async def test_memgraph_create_node(self) -> None:
        from neo4j import AsyncGraphDatabase

        driver = AsyncGraphDatabase.driver("bolt://localhost:7687")
        async with driver.session() as session:
            await session.run(
                "CREATE (t:TestNode {name: $name, source: 'integration_test'})",
                name="cipher_e2e",
            )
            result = await session.run(
                "MATCH (t:TestNode {name: 'cipher_e2e'}) RETURN t.name AS name"
            )
            record = await result.single()
            assert record["name"] == "cipher_e2e"
            await session.run("MATCH (t:TestNode {source: 'integration_test'}) DELETE t")
        await driver.close()


class TestQdrantLive:
    @pytest.mark.asyncio
    async def test_qdrant_health(self) -> None:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:6333/healthz")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_qdrant_collections_api(self) -> None:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:6333/collections")
            assert resp.status_code == 200
            data = resp.json()
            assert "result" in data


class TestMinIOLive:
    @pytest.mark.asyncio
    async def test_minio_health(self) -> None:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:9000/minio/health/live")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_minio_bucket_exists(self) -> None:
        from minio import Minio

        client = Minio("localhost:9000", access_key="cipher", secret_key="cipherdev123", secure=False)
        assert client.bucket_exists("cipher-artifacts")
        assert client.bucket_exists("cipher-checkpoints")


class TestNATSLive:
    @pytest.mark.asyncio
    async def test_nats_monitoring_healthz(self) -> None:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8222/healthz")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_nats_jetstream_enabled(self) -> None:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8222/jsz")
            assert resp.status_code == 200
            data = resp.json()
            assert "config" in data


class TestOPALive:
    @pytest.mark.asyncio
    async def test_opa_health(self) -> None:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8181/health")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_opa_policy_evaluation(self) -> None:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://localhost:8181/v1/data/cipher/authz",
                json={"input": {"agent": "devnex", "action": "llm_call"}},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("result", {}).get("allow") is True


class TestOTelCollectorLive:
    @pytest.mark.asyncio
    async def test_otel_grpc_port_open(self) -> None:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:4318/v1/traces")
            # OTel HTTP receiver responds (even if method not allowed)
            assert resp.status_code in (200, 405, 415)
