from __future__ import annotations

import json
import time
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from ai_toolkit.providers.base import LLMProvider
from ai_toolkit.shared.telemetry import MetricsCollector

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(Exception):
    """LLM response still invalid after one retry."""


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        lines = lines[1:] if lines else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines)
    return stripped.strip()


def default_retry_prompt(original_response: str) -> str:
    return (
        "Your previous response could not be parsed as valid JSON matching "
        "the required schema. Here is what you returned:\n\n"
        f"{original_response}\n\n"
        "Respond again with ONLY the corrected JSON object, matching the "
        "schema exactly. No markdown code fences, no text outside the JSON."
    )


async def _timed_complete(
    provider: LLMProvider, system_prompt: str, user_prompt: str, collector: MetricsCollector | None
):
    start = time.monotonic()
    response = await provider.complete(system_prompt, user_prompt)
    duration = time.monotonic() - start

    if collector is not None:
        collector.record_llm_call(
            duration_seconds=duration,
            input_tokens=response.input_tokens or 0,
            output_tokens=response.output_tokens or 0,
            model=response.model,
        )
    return response


async def complete_structured(
    provider: LLMProvider,
    schema: type[T],
    system_prompt: str,
    user_prompt: str,
    *,
    collector: MetricsCollector | None = None,
) -> tuple[T, bool]:
    """Calls provider.complete, parses+validates the response against
    `schema`, retrying once with a stricter reminder on failure. Returns
    (parsed_result, retried). Raises StructuredOutputError if still
    invalid after the retry — callers must treat this as a failed run,
    not silently produce an empty result.
    """
    response = await _timed_complete(provider, system_prompt, user_prompt, collector)

    retried = False
    try:
        return schema.model_validate(json.loads(_strip_code_fences(response.content))), retried
    except (json.JSONDecodeError, ValidationError):
        retried = True
        if collector is not None:
            collector.record_retry()
        retry_response = await _timed_complete(
            provider, system_prompt, default_retry_prompt(response.content), collector
        )
        try:
            return (
                schema.model_validate(json.loads(_strip_code_fences(retry_response.content))),
                retried,
            )
        except (json.JSONDecodeError, ValidationError) as exc:
            raise StructuredOutputError(
                "LLM response could not be parsed as valid JSON matching the "
                f"expected schema, even after one retry. Last raw response: "
                f"{retry_response.content!r}"
            ) from exc
