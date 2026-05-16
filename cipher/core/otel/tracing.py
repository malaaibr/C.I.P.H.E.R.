"""OTel tracing setup and @traced decorator (T-004)."""

from __future__ import annotations

import functools
import os
from typing import Any, Callable, TypeVar

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

F = TypeVar("F", bound=Callable[..., Any])

_TRACER_NAME = "cipher"
_initialized = False


def init_tracing(
    service_name: str = "cipher",
    otlp_endpoint: str | None = None,
) -> TracerProvider:
    """Initialize the OTel TracerProvider with OTLP gRPC export."""
    global _initialized
    endpoint = otlp_endpoint or os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
    )
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _initialized = True
    return provider


def get_tracer(name: str | None = None) -> trace.Tracer:
    return trace.get_tracer(name or _TRACER_NAME)


def traced(
    name: str | None = None,
    attributes: dict[str, str] | None = None,
) -> Callable[[F], F]:
    """Decorator that wraps a function in an OTel span."""

    def decorator(func: F) -> F:
        span_name = name or f"{func.__module__}.{func.__qualname__}"

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for k, v in attributes.items():
                        span.set_attribute(k, v)
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(trace.StatusCode.OK)
                    return result
                except Exception as exc:
                    span.set_status(trace.StatusCode.ERROR, str(exc))
                    span.record_exception(exc)
                    raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for k, v in attributes.items():
                        span.set_attribute(k, v)
                try:
                    result = func(*args, **kwargs)
                    span.set_status(trace.StatusCode.OK)
                    return result
                except Exception as exc:
                    span.set_status(trace.StatusCode.ERROR, str(exc))
                    span.record_exception(exc)
                    raise

        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator
