"""Covers Gemini, Groq, OpenRouter, and self-hosted Ollama/vLLM — any
OpenAI-compatible chat-completions endpoint, driven by base_url + model.
"""

from __future__ import annotations

import httpx

from ai_toolkit.providers.base import LLMProvider, LLMResponse
from ai_toolkit.shared.errors import LLMProviderError


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        client: httpx.AsyncClient | None = None,
        provider_label: str = "openai-compatible",
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._provider_label = provider_label
        self._client = client or httpx.AsyncClient(timeout=60.0)
        self._client.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        url = f"{self._base_url}/chat/completions"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
        }

        try:
            response = await self._client.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise LLMProviderError(None, str(exc), provider=self._provider_label) from exc

        if response.status_code >= 400:
            message = self._extract_error_message(response)
            raise LLMProviderError(response.status_code, message, provider=self._provider_label)

        data = response.json()
        return self._parse_response(data)

    def _parse_response(self, data: dict) -> LLMResponse:
        try:
            choice = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMProviderError(
                None,
                f"Unexpected response shape, missing choices[0].message.content: {data!r}",
                provider=self._provider_label,
            ) from exc

        usage = data.get("usage", {})
        return LLMResponse(
            content=choice,
            model=data.get("model", self._model),
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        try:
            body = response.json()
            return body.get("error", {}).get("message") or body.get("message") or response.text
        except Exception:
            return response.text

    async def aclose(self) -> None:
        await self._client.aclose()
