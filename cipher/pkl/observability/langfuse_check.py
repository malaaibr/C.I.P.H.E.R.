"""Langfuse health verification (T-028)."""

from __future__ import annotations

import os

import httpx


def get_langfuse_host() -> str:
    return os.environ.get("LANGFUSE_HOST", "http://localhost:3000")


async def langfuse_health_check(host: str | None = None) -> bool:
    """Verify Langfuse is reachable at the configured host."""
    url = host or get_langfuse_host()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{url}/api/public/health")
            return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


async def otel_collector_health_check(endpoint: str | None = None) -> bool:
    """Verify OTel Collector is accepting spans."""
    url = endpoint or os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
    )
    # OTel Collector gRPC doesn't have a simple HTTP health endpoint,
    # but the HTTP receiver at :4318 does
    http_url = url.replace(":4317", ":4318")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{http_url}/v1/health")
            return resp.status_code in (200, 405)  # 405 = endpoint exists but wrong method
    except (httpx.ConnectError, httpx.TimeoutException):
        return False
