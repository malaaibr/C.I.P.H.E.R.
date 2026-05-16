"""Unit tests for DRS ComposeDriver (T-001)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from cipher.core.substrate.compose_driver import ComposeConfig, ComposeDriver


class TestComposeConfig:
    def test_from_env_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CIPHER_DEPLOY_DIR", raising=False)
        cfg = ComposeConfig.from_env()
        assert cfg.compose_file == Path("deploy/local/docker-compose.yml")
        assert cfg.env_file == Path("deploy/local/.env")
        assert cfg.data_dir == Path("deploy/local/data")

    def test_from_env_custom(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CIPHER_DEPLOY_DIR", "/opt/cipher")
        cfg = ComposeConfig.from_env()
        assert cfg.compose_file == Path("/opt/cipher/docker-compose.yml")


class TestComposeDriver:
    def test_default_urls(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for var in (
            "REDIS_URL", "MEMGRAPH_URI", "QDRANT_URL", "MINIO_ENDPOINT",
            "NATS_URL", "OPA_URL", "OTEL_EXPORTER_OTLP_ENDPOINT",
            "LANGFUSE_HOST", "OLLAMA_BASE_URL", "GCA_BRIDGE_URL",
        ):
            monkeypatch.delenv(var, raising=False)

        driver = ComposeDriver()
        assert driver.redis_url == "redis://localhost:6379/0"
        assert driver.memgraph_uri == "bolt://localhost:7687"
        assert driver.qdrant_url == "http://localhost:6333"
        assert driver.minio_endpoint == "localhost:9000"
        assert driver.nats_url == "nats://localhost:4222"
        assert driver.opa_url == "http://localhost:8181"
        assert driver.otel_endpoint == "http://localhost:4317"
        assert driver.langfuse_host == "http://localhost:3000"
        assert driver.ollama_base_url == "http://localhost:11434"
        assert driver.gca_bridge_url == "http://127.0.0.1:37778"

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REDIS_URL", "redis://prod:6379/1")
        driver = ComposeDriver()
        assert driver.redis_url == "redis://prod:6379/1"
