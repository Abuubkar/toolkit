import json

import pytest

from ai_toolkit.core.github_client import CommitSummary
from ai_toolkit.providers.base import LLMProvider, LLMResponse
from ai_toolkit.shared.llm_json import StructuredOutputError
from ai_toolkit.tools.changelog.generator import (
    Changelog,
    format_changelog_markdown,
    generate_changelog_from_commits,
)

COMMITS = [
    CommitSummary(sha="abc1234", message="Add negative-total validation", author="Abubakar"),
]


class FakeProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = responses
        self.call_count = 0

    async def complete(self, system_prompt, user_prompt, *, max_tokens=2000):
        text = self._responses[self.call_count]
        self.call_count += 1
        return LLMResponse(content=text, model="fake-model")


@pytest.mark.asyncio
async def test_empty_commits_short_circuits():
    provider = FakeProvider(responses=[])
    outcome = await generate_changelog_from_commits([], provider)

    assert outcome.changelog.entries == []
    assert provider.call_count == 0


@pytest.mark.asyncio
async def test_happy_path():
    raw = json.dumps(
        {"entries": [{"category": "Added", "description": "Negative-total validation"}]}
    )
    provider = FakeProvider(responses=[raw])
    outcome = await generate_changelog_from_commits(COMMITS, provider)

    assert len(outcome.changelog.entries) == 1
    assert outcome.changelog.entries[0].category == "Added"
    assert outcome.commits_analyzed == 1


@pytest.mark.asyncio
async def test_raises_on_malformed_response_after_retry():
    provider = FakeProvider(responses=["bad {{{", "still bad {{{"])

    with pytest.raises(StructuredOutputError):
        await generate_changelog_from_commits(COMMITS, provider)


def test_format_groups_entries_by_category_in_keep_a_changelog_order():
    changelog = Changelog.model_validate(
        {
            "entries": [
                {"category": "Fixed", "description": "Fixed bug A"},
                {"category": "Added", "description": "New feature B"},
                {"category": "Fixed", "description": "Fixed bug C"},
            ]
        }
    )

    markdown = format_changelog_markdown(changelog)

    added_index = markdown.index("### Added")
    fixed_index = markdown.index("### Fixed")
    assert added_index < fixed_index  # Added comes before Fixed in Keep a Changelog order
    assert "- New feature B" in markdown
    assert "- Fixed bug A" in markdown
    assert "- Fixed bug C" in markdown


def test_format_omits_empty_categories():
    changelog = Changelog.model_validate({"entries": [{"category": "Security", "description": "x"}]})

    markdown = format_changelog_markdown(changelog)

    assert "### Added" not in markdown
    assert "### Security" in markdown


def test_format_handles_no_entries():
    markdown = format_changelog_markdown(Changelog())

    assert "No user-facing changes" in markdown
