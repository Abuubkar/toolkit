"""Orchestration for the PR reviewer: diff hunks -> LLM call -> validated,
filtered ReviewResult. Two entry points:

- review_diff_hunks: pure LLM-calling logic, takes hunks directly. This is
  the piece with the real failure modes (malformed JSON, retry logic), so
  it's kept testable against a fake LLMProvider with no GitHub involved.
- review_pull_request: the thin wrapper that adds the GitHub fetch/parse
  step on top, for actual CLI use.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import ValidationError

from ai_toolkit.core.config import ReviewConfig
from ai_toolkit.core.diff_parser import DiffHunk, parse_diff
from ai_toolkit.core.github_client import GitHubClient
from ai_toolkit.providers.base import LLMProvider
from ai_toolkit.tools.pr_reviewer.prompts import (
    SYSTEM_PROMPT,
    build_retry_prompt,
    build_review_prompt,
)
from ai_toolkit.tools.pr_reviewer.schema import ReviewResult, meets_severity_threshold


class ReviewParsingError(Exception):
    """Raised when the LLM's response still doesn't parse as valid JSON
    matching ReviewResult after one retry. Callers should treat this as a
    failed run, not silently produce zero comments.
    """


@dataclass(frozen=True)
class ReviewOutcome:
    result: ReviewResult
    hunks_analyzed: int
    hunks_skipped_ignored: int
    retried: bool


def _strip_code_fences(text: str) -> str:
    """Models frequently wrap JSON in ```json ... ``` despite instructions
    not to. Defensive stripping here is cheaper than relying on prompt
    compliance alone.
    """
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
    data = json.loads(cleaned)  # raises json.JSONDecodeError on bad JSON
    return ReviewResult.model_validate(data)  # raises ValidationError on bad shape


async def review_diff_hunks(
    hunks: list[DiffHunk],
    provider: LLMProvider,
    config: ReviewConfig,
) -> ReviewOutcome:
    if not hunks:
        return ReviewOutcome(
            result=ReviewResult(summary="No reviewable changes in this diff."),
            hunks_analyzed=0,
            hunks_skipped_ignored=0,
            retried=False,
        )

    prompt = build_review_prompt(hunks, focus=config.focus)
    response = await provider.complete(SYSTEM_PROMPT, prompt)

    retried = False
    try:
        result = _parse_review_json(response.content)
    except (json.JSONDecodeError, ValidationError):
        retried = True
        retry_prompt = build_retry_prompt(response.content)
        retry_response = await provider.complete(SYSTEM_PROMPT, retry_prompt)
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
) -> ReviewOutcome:
    raw_diff = github_client.get_pull_request_diff(pr_number)
    parsed = parse_diff(raw_diff, ignore_paths=config.ignore_paths)

    outcome = await review_diff_hunks(parsed.hunks, provider, config)
    return outcome
