"""Manual, real-network smoke test for OpenAICompatibleProvider against
the actual Gemini API. NOT part of the pytest suite (see test_provider
guidelines in the risk analysis: never hit real LLM APIs in CI — costs
money and is non-deterministic). Run this yourself, locally, when you
want to confirm the provider actually talks to Gemini correctly.

Usage:
    # Option 1: export directly
    export AI_API_KEY="your-ai-studio-key"
    uv run python scripts/smoke_test_provider.py

    # Option 2: use a .env file (copy .env.example to .env and fill it in)
    uv run --env-file .env python scripts/smoke_test_provider.py

MODEL_ID defaults to gemini-3-flash-preview if unset — override via .env
or the environment since free-tier/preview model availability shifts
often (gemini-2.5-flash, for example, stopped being available to new
accounts).
"""

from __future__ import annotations

import asyncio
import os
import sys

from ai_toolkit.providers.openai_compatible import OpenAICompatibleProvider
from ai_toolkit.shared.errors import LLMProviderError

DEFAULT_MODEL = "gemini-3-flash-preview"


async def main() -> int:
    api_key = os.environ.get("AI_API_KEY")
    if not api_key:
        print("Set AI_API_KEY in your environment first.", file=sys.stderr)
        return 1

    model = os.environ.get("MODEL_ID", DEFAULT_MODEL)

    provider = OpenAICompatibleProvider(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        api_key=api_key,
        model=model,
        provider_label="gemini",
    )

    print(f"Sending a real request to Gemini (model: {model})...")
    try:
        result = await provider.complete(
            system_prompt="You are a terse code reviewer. Reply in one sentence.",
            user_prompt=(
                "Review this diff:\n"
                "-    return total\n"
                "+    if total < 0:\n"
                "+        raise ValueError('Total cannot be negative')\n"
                "+    return total\n"
            ),
            max_tokens=200,
        )
    except LLMProviderError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        await provider.aclose()

    print("\n--- Response ---")
    print(f"Model: {result.model}")
    print(f"Tokens: {result.input_tokens} in / {result.output_tokens} out")
    print(f"Content: {result.content}")
    print("\nSmoke test passed — provider can reach Gemini and parse its response.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
