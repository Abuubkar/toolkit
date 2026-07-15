"""The provider abstraction every LLM-backed tool depends on. Adding a new
provider means one new class implementing this interface plus, once there
are 2+, a line in registry.py — nothing else in the codebase changes.
"""

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
    ) -> LLMResponse:
        """Single completion call. Structured-output enforcement (for the
        review-comment schema) is layered on top of this by the calling
        tool via prompt instructions + response parsing/validation, kept
        out of the provider interface so providers stay swappable even
        if their native structured-output support differs.
        """
        ...

    async def aclose(self) -> None:
        """Providers that own an HTTP client should override this to
        release it. Default is a no-op for providers that don't need it.
        """
        return None
