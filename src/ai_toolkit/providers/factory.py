from __future__ import annotations

import os

from ai_toolkit.providers.base import LLMProvider
from ai_toolkit.providers.openai_compatible import OpenAICompatibleProvider

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
DEFAULT_MODEL = "gemini-3-flash-preview"


def build_provider_from_env() -> LLMProvider:
    api_key = os.environ.get("AI_API_KEY")
    if not api_key:
        raise RuntimeError("AI_API_KEY environment variable is required.")

    base_url = os.environ.get("LLM_BASE_URL") or DEFAULT_BASE_URL
    model = os.environ.get("MODEL_ID") or DEFAULT_MODEL

    return OpenAICompatibleProvider(base_url=base_url, api_key=api_key, model=model)
