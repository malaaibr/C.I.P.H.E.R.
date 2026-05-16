"""Unit tests for @traced decorator (T-004)."""

from __future__ import annotations

from typing import Sequence

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ReadableSpan,
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)

from cipher.core.otel.tracing import get_tracer, traced


class ListSpanExporter(SpanExporter):
    """Test exporter that collects spans in a list."""

    def __init__(self) -> None:
        self.spans: list[ReadableSpan] = []

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def get_finished_spans(self) -> list[ReadableSpan]:
        return list(self.spans)


@pytest.fixture(autouse=True)
def _setup_test_tracing() -> ListSpanExporter:
    exporter = ListSpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    # Reset the global provider for each test
    trace._TRACER_PROVIDER = None  # type: ignore[attr-defined]
    trace._TRACER_PROVIDER_SET_ONCE._done = False  # type: ignore[attr-defined]
    trace.set_tracer_provider(provider)
    return exporter


class TestTracedSync:
    def test_emits_span(self, _setup_test_tracing: ListSpanExporter) -> None:
        exporter = _setup_test_tracing

        @traced(name="test.sync_op")
        def do_work() -> str:
            return "done"

        result = do_work()
        assert result == "done"
        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "test.sync_op"

    def test_records_exception(self, _setup_test_tracing: ListSpanExporter) -> None:
        exporter = _setup_test_tracing

        @traced(name="test.failing")
        def fail() -> None:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            fail()
        spans = exporter.get_finished_spans()
        assert spans[0].status.status_code == trace.StatusCode.ERROR


class TestTracedAsync:
    @pytest.mark.asyncio
    async def test_emits_span(self, _setup_test_tracing: ListSpanExporter) -> None:
        exporter = _setup_test_tracing

        @traced(name="test.async_op", attributes={"layer": "trf"})
        async def do_async() -> int:
            return 42

        result = await do_async()
        assert result == 42
        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "test.async_op"
        assert spans[0].attributes.get("layer") == "trf"

    @pytest.mark.asyncio
    async def test_async_exception(self, _setup_test_tracing: ListSpanExporter) -> None:
        exporter = _setup_test_tracing

        @traced()
        async def explode() -> None:
            raise RuntimeError("async boom")

        with pytest.raises(RuntimeError):
            await explode()
        spans = exporter.get_finished_spans()
        assert spans[0].status.status_code == trace.StatusCode.ERROR
