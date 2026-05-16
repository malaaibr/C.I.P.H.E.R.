"""
DRS Compose Driver — Docker Compose deployment substrate.

WBS Task: T-001
ADR: ADR-0003
Layer: DRS
Module Type: Driver
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ComposeConfig:
    """Configuration for the local Docker Compose deployment."""

    compose_file: Path
    env_file: Path
    data_dir: Path

    @classmethod
    def from_env(cls) -> ComposeConfig:
        base = Path(os.environ.get("CIPHER_DEPLOY_DIR", "deploy/local"))
        return cls(
            compose_file=base / "docker-compose.yml",
            env_file=base / ".env",
            data_dir=base / "data",
        )


class ComposeDriver:
    """
    DRS driver for Docker Compose deployments.

    Provides the four substrate fabrics (compute, network, storage, secret)
    backed by the local Docker Compose stack defined in deploy/local/.
    """

    def __init__(self, config: ComposeConfig | None = None) -> None:
        self._config = config or ComposeConfig.from_env()

    @property
    def redis_url(self) -> str:
        return os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    @property
    def memgraph_uri(self) -> str:
        return os.environ.get("MEMGRAPH_URI", "bolt://localhost:7687")

    @property
    def qdrant_url(self) -> str:
        return os.environ.get("QDRANT_URL", "http://localhost:6333")

    @property
    def minio_endpoint(self) -> str:
        return os.environ.get("MINIO_ENDPOINT", "localhost:9000")

    @property
    def nats_url(self) -> str:
        return os.environ.get("NATS_URL", "nats://localhost:4222")

    @property
    def opa_url(self) -> str:
        return os.environ.get("OPA_URL", "http://localhost:8181")

    @property
    def otel_endpoint(self) -> str:
        return os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    @property
    def langfuse_host(self) -> str:
        return os.environ.get("LANGFUSE_HOST", "http://localhost:3000")

    @property
    def ollama_base_url(self) -> str:
        return os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    @property
    def gca_bridge_url(self) -> str:
        return os.environ.get("GCA_BRIDGE_URL", "http://127.0.0.1:37778")
