from __future__ import annotations

from dataclasses import dataclass

from ai_toolkit.core.github_client import CommitSummary, GitHubClient
from ai_toolkit.providers.base import LLMProvider
from ai_toolkit.shared.llm_json import complete_structured
from ai_toolkit.shared.telemetry import MetricsCollector
from ai_toolkit.tools.changelog.prompts import SYSTEM_PROMPT, build_changelog_prompt
from ai_toolkit.tools.changelog.schema import CATEGORIES, Changelog


@dataclass(frozen=True)
class ChangelogOutcome:
    changelog: Changelog
    commits_analyzed: int
    retried: bool


async def generate_changelog_from_commits(
    commits: list[CommitSummary],
    provider: LLMProvider,
    collector: MetricsCollector | None = None,
) -> ChangelogOutcome:
    if not commits:
        return ChangelogOutcome(changelog=Changelog(), commits_analyzed=0, retried=False)

    prompt = build_changelog_prompt(commits)
    result, retried = await complete_structured(
        provider, Changelog, SYSTEM_PROMPT, prompt, collector=collector
    )

    if collector is not None:
        collector.record_items_analyzed(len(commits))

    return ChangelogOutcome(changelog=result, commits_analyzed=len(commits), retried=retried)


async def generate_changelog(
    github_client: GitHubClient,
    provider: LLMProvider,
    base: str,
    head: str,
    collector: MetricsCollector | None = None,
) -> ChangelogOutcome:
    commits = github_client.compare_commits(base, head)
    if collector is not None:
        collector.record_github_call()

    return await generate_changelog_from_commits(commits, provider, collector)


def format_changelog_markdown(changelog: Changelog) -> str:
    if not changelog.entries:
        return "No user-facing changes.\n"

    by_category: dict[str, list[str]] = {c: [] for c in CATEGORIES}
    for entry in changelog.entries:
        by_category[entry.category].append(entry.description)

    lines = []
    for category in CATEGORIES:
        descriptions = by_category[category]
        if not descriptions:
            continue
        lines.append(f"### {category}")
        lines.extend(f"- {d}" for d in descriptions)
        lines.append("")

    return "\n".join(lines).strip() + "\n"
