import os

import httpx
import pytest

from ai_toolkit.providers.openai_compatible import OpenAICompatibleProvider
from ai_toolkit.shared.errors import LLMProviderError


model_id = os.environ.get("MODEL_ID")

def _provider_with_transport(handler, **kwargs) -> OpenAICompatibleProvider:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return OpenAICompatibleProvider(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        api_key="fake-gemini-key",
        model=model_id,
        client=http_client,
        **kwargs,
    )


@pytest.mark.asyncio
async def test_complete_returns_parsed_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1beta/openai/chat/completions"
        assert request.headers["Authorization"] == "Bearer fake-gemini-key"
        return httpx.Response(
            200,
            json={
                "model": model_id,
                "choices": [{"message": {"role": "assistant", "content": "Looks fine to me."}}],
                "usage": {"prompt_tokens": 120, "completion_tokens": 8},
            },
        )

    provider = _provider_with_transport(handler)
    result = await provider.complete("You are a reviewer.", "Review this diff: ...")

    assert result.content == "Looks fine to me."
    assert result.model == model_id
    assert result.input_tokens == 120
    assert result.output_tokens == 8


@pytest.mark.asyncio
async def test_complete_sends_system_and_user_messages():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    provider = _provider_with_transport(handler)
    await provider.complete("system instructions", "user diff content", max_tokens=500)

    payload = captured["payload"]
    assert payload["model"] == model_id
    assert payload["max_tokens"] == 500
    assert payload["messages"] == [
        {"role": "system", "content": "system instructions"},
        {"role": "user", "content": "user diff content"},
    ]


@pytest.mark.asyncio
async def test_complete_raises_on_error_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "Rate limit exceeded"}})

    provider = _provider_with_transport(handler, provider_label="gemini")

    with pytest.raises(LLMProviderError) as exc_info:
        await provider.complete("sys", "user")

    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.message
    assert exc_info.value.provider == "gemini"


@pytest.mark.asyncio
async def test_complete_raises_on_malformed_response_instead_of_crashing():
    """This is the 'silently did nothing' failure mode flagged in the risk
    analysis: a response missing choices[0].message.content must raise a
    clear LLMProviderError, not an unhandled KeyError deep in caller code.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    provider = _provider_with_transport(handler)

    with pytest.raises(LLMProviderError) as exc_info:
        await provider.complete("sys", "user")

    assert "Unexpected response shape" in exc_info.value.message


@pytest.mark.asyncio
async def test_complete_raises_on_network_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    provider = _provider_with_transport(handler)

    with pytest.raises(LLMProviderError):
        await provider.complete("sys", "user")
