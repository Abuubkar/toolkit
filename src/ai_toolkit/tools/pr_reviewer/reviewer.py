from __future__ import annotations

from dataclasses import dataclass

from ai_toolkit.core.config import ReviewConfig
from ai_toolkit.core.diff_parser import DiffHunk, parse_diff
from ai_toolkit.core.github_client import GitHubClient
from ai_toolkit.providers.base import LLMProvider
from ai_toolkit.shared.llm_json import StructuredOutputError, complete_structured
from ai_toolkit.shared.telemetry import MetricsCollector
from ai_toolkit.tools.pr_reviewer.prompts import SYSTEM_PROMPT, build_review_prompt
from ai_toolkit.tools.pr_reviewer.schema import ReviewResult, meets_severity_threshold

ReviewParsingError = StructuredOutputError


@dataclass(frozen=True)
class ReviewOutcome:
    result: ReviewResult
    hunks_analyzed: int
    hunks_skipped_ignored: int
    retried: bool


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
    result, retried = await complete_structured(
        provider, ReviewResult, SYSTEM_PROMPT, prompt, collector=collector
    )

    filtered_comments = [
        c for c in result.comments if meets_severity_threshold(c, config.severity_threshold)
    ]
    filtered_comments = filtered_comments[: config.max_comments]
    final_result = ReviewResult(summary=result.summary, comments=filtered_comments)

    if collector is not None:
        collector.record_items_analyzed(len(hunks))

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
