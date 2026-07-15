"""LLM provider abstraction: one interface, swappable implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class LLMResponse(BaseModel):
    content: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 2000,
    ) -> LLMResponse: ...

    async def aclose(self) -> None:
        """Override to release owned resources (e.g. an HTTP client)."""
        return None
