import io
import json
from unittest import mock

import pytest

from translate.llm import client

BASE = "http://127.0.0.1:8080/v1"


def _response(content):
    body = io.BytesIO(json.dumps({"choices": [{"message": {"content": content}}]}).encode())
    return mock.Mock(
        getcode=lambda: 200, read=body.read, __enter__=lambda s: s, __exit__=mock.Mock()
    )


@pytest.fixture
def llm_env(monkeypatch):
    """Point the client at a fake local server."""
    _set_env(monkeypatch)


def _set_env(monkeypatch):
    monkeypatch.setenv("HTLB_LLM_BASE_URL", BASE)
    monkeypatch.setenv("HTLB_LLM_MODEL", "test-model")
    monkeypatch.setenv("HTLB_LLM_API_KEY", "local")


@pytest.mark.usefixtures("llm_env")
def test_chat_ok():
    def fake_urlopen(req, timeout=0):
        assert timeout
        assert "/chat/completions" in req.full_url
        assert req.get_header("Authorization") == "Bearer local"
        return _response(" translated unit ")

    with mock.patch("urllib.request.urlopen", fake_urlopen):
        assert client.chat([{"role": "user", "content": "hi"}]) == "translated unit"


@pytest.mark.usefixtures("llm_env")
def test_chat_empty_content_raises():
    with (
        mock.patch("urllib.request.urlopen", return_value=_response("   ")),
        pytest.raises(client.LLMError, match="empty"),
    ):
        client.chat([{"role": "user", "content": "x"}])


@pytest.mark.usefixtures("llm_env")
def test_missing_env_raises(monkeypatch):
    monkeypatch.delenv("HTLB_LLM_BASE_URL")
    with mock.patch.object(client, "load_dotenv"), pytest.raises(client.LLMError):
        client.chat([{"role": "user", "content": "x"}])


def test_chat_explicit_overrides_omit_bearer(monkeypatch):
    for key in ("HTLB_LLM_BASE_URL", "HTLB_LLM_MODEL", "HTLB_LLM_API_KEY"):
        monkeypatch.delenv(key, raising=False)

    def fake_urlopen(req, timeout=0):
        assert timeout == 120
        assert req.full_url == "http://127.0.0.1:11434/v1/chat/completions"
        assert req.get_header("Authorization") is None
        return _response("hi")

    with mock.patch("urllib.request.urlopen", fake_urlopen):
        out = client.chat(
            [{"role": "user", "content": "x"}],
            base_url="http://127.0.0.1:11434/v1",
            model="llama",
            api_key=None,
            temperature=0.0,
            timeout=120,
        )
    assert out == "hi"
