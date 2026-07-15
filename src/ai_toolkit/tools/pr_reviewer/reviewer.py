from __future__ import annotations

import json
import time
from dataclasses import dataclass

from pydantic import ValidationError

from ai_toolkit.core.config import ReviewConfig
from ai_toolkit.core.diff_parser import DiffHunk, parse_diff
from ai_toolkit.core.github_client import GitHubClient
from ai_toolkit.providers.base import LLMProvider
from ai_toolkit.shared.telemetry import MetricsCollector
from ai_toolkit.tools.pr_reviewer.prompts import (
    SYSTEM_PROMPT,
    build_retry_prompt,
    build_review_prompt,
)
from ai_toolkit.tools.pr_reviewer.schema import ReviewResult, meets_severity_threshold


class ReviewParsingError(Exception):
    """LLM response still invalid after one retry."""


@dataclass(frozen=True)
class ReviewOutcome:
    result: ReviewResult
    hunks_analyzed: int
    hunks_skipped_ignored: int
    retried: bool


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        lines = lines[1:] if lines else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines)
    return stripped.strip()


def _parse_review_json(raw_text: str) -> ReviewResult:
    cleaned = _strip_code_fences(raw_text)
    data = json.loads(cleaned)
    return ReviewResult.model_validate(data)


async def _timed_complete(provider: LLMProvider, system_prompt: str, user_prompt: str, collector: MetricsCollector | None):
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


async def review_diff_hunks(
    hunks: list[DiffHunk],
    provider: LLMProvider,
    config: ReviewConfig,
    collector: MetricsCollector | None = None,
) -> ReviewOutcome:
    if not hunks:
        return ReviewOutcome(
            result=ReviewResult(summary="No reviewable changes in this diff."),
            hunks_analyzed=0,
            hunks_skipped_ignored=0,
            retried=False,
        )

    prompt = build_review_prompt(hunks, focus=config.focus)
    response = await _timed_complete(provider, SYSTEM_PROMPT, prompt, collector)

    retried = False
    try:
        result = _parse_review_json(response.content)
    except (json.JSONDecodeError, ValidationError):
        retried = True
        if collector is not None:
            collector.record_retry()
        retry_prompt = build_retry_prompt(response.content)
        retry_response = await _timed_complete(provider, SYSTEM_PROMPT, retry_prompt, collector)
        try:
            result = _parse_review_json(retry_response.content)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ReviewParsingError(
                "LLM response could not be parsed as valid JSON matching the "
                f"review schema, even after one retry. Last raw response: "
                f"{retry_response.content!r}"
            ) from exc

    filtered_comments = [
        c for c in result.comments if meets_severity_threshold(c, config.severity_threshold)
    ]
    filtered_comments = filtered_comments[: config.max_comments]

    final_result = ReviewResult(summary=result.summary, comments=filtered_comments)

    if collector is not None:
        collector.record_hunks_analyzed(len(hunks))

    return ReviewOutcome(
        result=final_result,
        hunks_analyzed=len(hunks),
        hunks_skipped_ignored=0,
        retried=retried,
    )


async def review_pull_request(
    github_client: GitHubClient,
    provider: LLMProvider,
    pr_number: int,
    config: ReviewConfig,
    collector: MetricsCollector | None = None,
) -> ReviewOutcome:
    raw_diff = github_client.get_pull_request_diff(pr_number)
    if collector is not None:
        collector.record_github_call()

    parsed = parse_diff(raw_diff, ignore_paths=config.ignore_paths)
    return await review_diff_hunks(parsed.hunks, provider, config, collector)
