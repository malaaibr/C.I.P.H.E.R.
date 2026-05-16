"""CIPHER OTel — tracing helpers and @traced decorator."""

from __future__ import annotations

from cipher.core.otel.tracing import get_tracer, init_tracing, traced

__all__ = ["get_tracer", "init_tracing", "traced"]
