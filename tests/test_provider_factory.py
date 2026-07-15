import pytest

from ai_toolkit.providers.factory import DEFAULT_BASE_URL, DEFAULT_MODEL, build_provider_from_env
from ai_toolkit.providers.openai_compatible import OpenAICompatibleProvider


def test_raises_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="AI_API_KEY"):
        build_provider_from_env()


def test_uses_defaults_when_only_api_key_set(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "fake-key")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("MODEL_ID", raising=False)

    provider = build_provider_from_env()

    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider._base_url == DEFAULT_BASE_URL
    assert provider._model == DEFAULT_MODEL


def test_uses_overrides_when_set(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "fake-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("MODEL_ID", "llama-3.3-70b-versatile")

    provider = build_provider_from_env()

    assert provider._base_url == "https://api.groq.com/openai/v1"
    assert provider._model == "llama-3.3-70b-versatile"
