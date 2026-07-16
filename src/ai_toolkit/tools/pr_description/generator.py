from __future__ import annotations

from dataclasses import dataclass

from ai_toolkit.core.diff_parser import DiffHunk, parse_diff
from ai_toolkit.core.github_client import GitHubClient
from ai_toolkit.providers.base import LLMProvider
from ai_toolkit.shared.llm_json import complete_structured
from ai_toolkit.shared.telemetry import MetricsCollector
from ai_toolkit.tools.pr_description.prompts import SYSTEM_PROMPT, build_description_prompt
from ai_toolkit.tools.pr_description.schema import PRDescription


@dataclass(frozen=True)
class PRDescriptionOutcome:
    description: PRDescription
    hunks_analyzed: int
    retried: bool


async def generate_description_from_hunks(
    hunks: list[DiffHunk],
    provider: LLMProvider,
    collector: MetricsCollector | None = None,
) -> PRDescriptionOutcome:
    if not hunks:
        return PRDescriptionOutcome(
            description=PRDescription(summary="No changes to describe."),
            hunks_analyzed=0,
            retried=False,
        )

    prompt = build_description_prompt(hunks)
    result, retried = await complete_structured(
        provider, PRDescription, SYSTEM_PROMPT, prompt, collector=collector
    )

    if collector is not None:
        collector.record_hunks_analyzed(len(hunks))

    return PRDescriptionOutcome(description=result, hunks_analyzed=len(hunks), retried=retried)


async def generate_pr_description(
    github_client: GitHubClient,
    provider: LLMProvider,
    pr_number: int,
    ignore_paths: list[str],
    collector: MetricsCollector | None = None,
) -> PRDescriptionOutcome:
    raw_diff = github_client.get_pull_request_diff(pr_number)
    if collector is not None:
        collector.record_github_call()

    parsed = parse_diff(raw_diff, ignore_paths=ignore_paths)
    return await generate_description_from_hunks(parsed.hunks, provider, collector)


def format_description_markdown(description: PRDescription) -> str:
    lines = ["## Summary", description.summary]

    if description.changes:
        lines.append("\n## Changes")
        lines.extend(f"- {change}" for change in description.changes)

    if description.testing_notes:
        lines.append(f"\n## Testing\n{description.testing_notes}")

    return "\n".join(lines) + "\n"
