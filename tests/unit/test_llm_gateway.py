"""Unit tests for LLM Gateway (T-010, T-011, T-012, T-013)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cipher.core.schemas.task_contract import TaskClass
from cipher.trf.mcp_servers.llm_gateway.gca_http_driver import GCAHttpDriver
from cipher.trf.mcp_servers.llm_gateway.ollama_driver import OllamaDriver
from cipher.trf.mcp_servers.llm_gateway.protocol import (
    LLMBackend,
    LLMResponse,
    LLMUnavailableError,
)
from cipher.trf.mcp_servers.llm_gateway.router import TaskClassRouter


class TestProtocol:
    def test_ollama_satisfies_protocol(self) -> None:
        assert isinstance(OllamaDriver(), LLMBackend)

    def test_gca_satisfies_protocol(self) -> None:
        assert isinstance(GCAHttpDriver(), LLMBackend)

    def test_llm_response_round_trip(self) -> None:
        resp = LLMResponse(
            text="hello",
            backend_id="ollama",
            task_class="TRIAGE",
            duration_ms=123.4,
            prompt_tokens=10,
            completion_tokens=5,
        )
        restored = LLMResponse.model_validate_json(resp.model_dump_json())
        assert restored.text == "hello"

    def test_unavailable_error(self) -> None:
        err = LLMUnavailableError("ollama", "connection refused")
        assert "ollama" in str(err)
        assert err.backend == "ollama"


class TestOllamaDriver:
    @pytest.mark.asyncio
    async def test_is_available_success(self) -> None:
        driver = OllamaDriver()
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            assert await driver.is_available() is True

    @pytest.mark.asyncio
    async def test_complete_returns_response(self) -> None:
        driver = OllamaDriver()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "response": "classified as: requirement",
            "prompt_eval_count": 15,
            "eval_count": 8,
        }

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await driver.complete("classify this", {})
            assert result.text == "classified as: requirement"
            assert result.backend_id == "ollama"
            assert result.prompt_tokens == 15


class TestGCAHttpDriver:
    @pytest.mark.asyncio
    async def test_complete_returns_response(self) -> None:
        driver = GCAHttpDriver()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "text": "generated code here",
            "instance_id": "abc-123",
        }

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await driver.complete("generate LLD", {"workspace_hint": "/ws"})
            assert result.text == "generated code here"
            assert result.backend_id == "gca_http"
            assert result.instance_id == "abc-123"


class TestTaskClassRouter:
    @pytest.mark.asyncio
    async def test_routes_triage_to_ollama(self) -> None:
        router = TaskClassRouter()
        mock_driver = AsyncMock()
        mock_driver.is_available = AsyncMock(return_value=True)
        mock_driver.complete = AsyncMock(
            return_value=LLMResponse(
                text="ok", backend_id="ollama", task_class="TRIAGE", duration_ms=10.0
            )
        )
        mock_driver.backend_id = "ollama"
        router._drivers["TRIAGE"] = mock_driver

        result = await router.route("test", TaskClass.TRIAGE, {})
        assert result.backend_id == "ollama"

    @pytest.mark.asyncio
    async def test_raises_when_unavailable(self) -> None:
        router = TaskClassRouter()
        mock_driver = AsyncMock()
        mock_driver.is_available = AsyncMock(return_value=False)
        mock_driver.backend_id = "ollama"
        router._drivers["TRIAGE"] = mock_driver

        with pytest.raises(LLMUnavailableError):
            await router.route("test", TaskClass.TRIAGE, {})

    @pytest.mark.asyncio
    async def test_routes_code_gen_to_gca(self) -> None:
        router = TaskClassRouter()
        mock_driver = AsyncMock()
        mock_driver.is_available = AsyncMock(return_value=True)
        mock_driver.complete = AsyncMock(
            return_value=LLMResponse(
                text="code", backend_id="gca_http", task_class="CODE_GEN", duration_ms=50.0
            )
        )
        mock_driver.backend_id = "gca_http"
        router._drivers["CODE_GEN"] = mock_driver

        result = await router.route("gen", TaskClass.CODE_GEN, {})
        assert result.backend_id == "gca_http"
