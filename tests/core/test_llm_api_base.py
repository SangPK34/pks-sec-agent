"""Tests for the OpenAI endpoint resolver."""

from pks.util import llm_api_base as m


def test_default_openai_base_url(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    assert m.resolve_openai_base_url() == "https://api.openai.com/v1"
    assert m.custom_openai_base_url_configured() is False


def test_custom_openai_base_url_is_normalized(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_BASE_URL", " https://gateway.example/v1/ ")
    assert m.resolve_openai_base_url() == "https://gateway.example/v1"
    assert m.custom_openai_base_url_configured() is True


def test_only_openai_api_key_is_used(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert m.resolve_openai_api_key() == ""

    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    assert m.resolve_openai_api_key() == "openai-key"
