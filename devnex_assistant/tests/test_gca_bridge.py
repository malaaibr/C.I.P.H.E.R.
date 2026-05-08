# tests/test_gca_bridge.py
import pytest
from unittest.mock import patch, MagicMock

from gca.bridge import DevNexBridge


def test_is_available_returns_true_on_200() -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("gca.bridge.requests.get", return_value=mock_resp):
        assert DevNexBridge.is_available() is True


def test_is_available_returns_false_on_connection_error() -> None:
    import requests as req_lib
    with patch("gca.bridge.requests.get", side_effect=req_lib.ConnectionError):
        assert DevNexBridge.is_available() is False


def test_is_available_returns_false_on_non_200() -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    with patch("gca.bridge.requests.get", return_value=mock_resp):
        assert DevNexBridge.is_available() is False


def test_send_prompt_returns_response_text() -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "LLD output here"}
    with patch("gca.bridge.requests.post", return_value=mock_resp):
        result = DevNexBridge.send_prompt("Generate LLD", [])
    assert result == "LLD output here"


def test_send_prompt_raises_on_bridge_error() -> None:
    from core.errors import GCABridgeError
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    # post() returns 500 — bridge raises GCABridgeError before raise_for_status
    with patch("gca.bridge.requests.post", return_value=mock_resp):
        with pytest.raises(GCABridgeError):
            DevNexBridge.send_prompt("Generate LLD", [])


def test_send_prompt_raises_on_connection_error() -> None:
    import requests as req_lib
    from core.errors import GCANotAvailableError
    with patch("gca.bridge.requests.post", side_effect=req_lib.ConnectionError):
        with pytest.raises(GCANotAvailableError):
            DevNexBridge.send_prompt("Generate LLD", [])
