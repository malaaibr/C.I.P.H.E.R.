"""Unit tests for Memgraph, Qdrant, and MinIO adapters (T-006, T-007, T-008)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cipher.core.adapters.memgraph_client import MemgraphClient, get_memgraph_uri
from cipher.core.adapters.minio_client import MinioStore, get_minio_endpoint
from cipher.core.adapters.qdrant_client_wrapper import QdrantHealthClient, get_qdrant_url


class TestMemgraphClient:
    def test_default_uri(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MEMGRAPH_URI", raising=False)
        assert get_memgraph_uri() == "bolt://localhost:7687"

    def test_not_connected_raises(self) -> None:
        client = MemgraphClient()
        with pytest.raises(RuntimeError, match="not connected"):
            _ = client.driver

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        client = MemgraphClient()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"cnt": 0})
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_driver.session = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        client._driver = mock_driver

        count = await client.health_check()
        assert count == 0


class TestQdrantHealthClient:
    def test_default_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("QDRANT_URL", raising=False)
        assert get_qdrant_url() == "http://localhost:6333"

    @pytest.mark.asyncio
    async def test_health_check_success(self) -> None:
        client = QdrantHealthClient("http://localhost:6333")
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_resp)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            result = await client.health_check()
            assert result is True


class TestMinioStore:
    def test_default_endpoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MINIO_ENDPOINT", raising=False)
        assert get_minio_endpoint() == "localhost:9000"

    def test_ensure_bucket_creates(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        store = MinioStore(client=mock_client)
        store.ensure_bucket()
        mock_client.make_bucket.assert_called_once_with("cipher-artifacts")

    def test_ensure_bucket_exists_noop(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        store = MinioStore(client=mock_client)
        store.ensure_bucket()
        mock_client.make_bucket.assert_not_called()

    def test_put_object(self) -> None:
        mock_client = MagicMock()
        store = MinioStore(client=mock_client)
        store.put_object("test.csv", b"a,b,c\n1,2,3", "text/csv")
        mock_client.put_object.assert_called_once()
        args = mock_client.put_object.call_args
        assert args[0][0] == "cipher-artifacts"
        assert args[0][1] == "test.csv"
