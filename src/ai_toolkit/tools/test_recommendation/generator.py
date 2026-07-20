from __future__ import annotations

from dataclasses import dataclass

from ai_toolkit.core.diff_parser import DiffHunk, parse_diff
from ai_toolkit.core.github_client import GitHubClient
from ai_toolkit.providers.base import LLMProvider
from ai_toolkit.shared.llm_json import complete_structured
from ai_toolkit.shared.telemetry import MetricsCollector
from ai_toolkit.tools.test_recommendation.prompts import (
    SYSTEM_PROMPT,
    build_test_recommendation_prompt,
)
from ai_toolkit.tools.test_recommendation.schema import CoverageReport

MAX_RECOMMENDATIONS = 10


@dataclass(frozen=True)
class CoverageOutcome:
    result: CoverageReport
    hunks_analyzed: int
    retried: bool


async def recommend_tests_from_hunks(
    hunks: list[DiffHunk],
    provider: LLMProvider,
    collector: MetricsCollector | None = None,
) -> CoverageOutcome:
    if not hunks:
        return CoverageOutcome(
            result=CoverageReport(summary="No reviewable changes in this diff."),
            hunks_analyzed=0,
            retried=False,
        )

    prompt = build_test_recommendation_prompt(hunks)
    result, retried = await complete_structured(
        provider, CoverageReport, SYSTEM_PROMPT, prompt, collector=collector
    )

    capped_result = CoverageReport(
        summary=result.summary,
        recommendations=result.recommendations[:MAX_RECOMMENDATIONS],
    )

    if collector is not None:
        collector.record_items_analyzed(len(hunks))

    return CoverageOutcome(
        result=capped_result, hunks_analyzed=len(hunks), retried=retried
    )


async def recommend_tests_for_pr(
    github_client: GitHubClient,
    provider: LLMProvider,
    pr_number: int,
    ignore_paths: list[str],
    collector: MetricsCollector | None = None,
) -> CoverageOutcome:
    raw_diff = github_client.get_pull_request_diff(pr_number)
    if collector is not None:
        collector.record_github_call()

    parsed = parse_diff(raw_diff, ignore_paths=ignore_paths)
    return await recommend_tests_from_hunks(parsed.hunks, provider, collector)


def format_recommendations_markdown(result: CoverageReport) -> str:
    if not result.recommendations:
        return f"**Test coverage check:** {result.summary}\n"

    lines = ["## Suggested test coverage", result.summary, ""]
    for rec in result.recommendations:
        lines.append(f"- **[{rec.priority}]** `{rec.file_path}`: {rec.description}")

    return "\n".join(lines) + "\n"
