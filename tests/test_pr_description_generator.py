import json

import pytest

from ai_toolkit.core.diff_parser import DiffHunk
from ai_toolkit.providers.base import LLMProvider, LLMResponse
from ai_toolkit.shared.llm_json import StructuredOutputError
from ai_toolkit.tools.pr_description.generator import (
    PRDescription,
    format_description_markdown,
    generate_description_from_hunks,
)

SAMPLE_HUNK = DiffHunk(
    file_path="src/utils.py",
    hunk_header="@@ -2,4 +2,6 @@",
    added_lines=2,
    removed_lines=0,
    content="@@ -2,4 +2,6 @@\n     total = 0\n+    if total < 0:\n+        raise ValueError()\n",
)


class FakeProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = responses
        self.call_count = 0

    async def complete(self, system_prompt, user_prompt, *, max_tokens=2000):
        text = self._responses[self.call_count]
        self.call_count += 1
        return LLMResponse(content=text, model="fake-model")


@pytest.mark.asyncio
async def test_empty_hunks_short_circuits():
    provider = FakeProvider(responses=[])
    outcome = await generate_description_from_hunks([], provider)

    assert outcome.description.summary == "No changes to describe."
    assert provider.call_count == 0


@pytest.mark.asyncio
async def test_happy_path():
    raw = json.dumps(
        {
            "summary": "Adds validation to calculate_total",
            "changes": ["Added negative-total check"],
            "testing_notes": "Ran pytest",
        }
    )
    provider = FakeProvider(responses=[raw])
    outcome = await generate_description_from_hunks([SAMPLE_HUNK], provider)

    assert outcome.description.summary == "Adds validation to calculate_total"
    assert outcome.retried is False
    assert outcome.hunks_analyzed == 1


@pytest.mark.asyncio
async def test_raises_on_malformed_response_after_retry():
    provider = FakeProvider(responses=["bad {{{", "still bad {{{"])

    with pytest.raises(StructuredOutputError):
        await generate_description_from_hunks([SAMPLE_HUNK], provider)


def test_format_includes_summary_changes_and_testing():
    description = PRDescription(
        summary="Adds validation",
        changes=["Added null check", "Added test"],
        testing_notes="Ran pytest locally",
    )

    markdown = format_description_markdown(description)

    assert "## Summary" in markdown
    assert "Adds validation" in markdown
    assert "- Added null check" in markdown
    assert "## Testing" in markdown
    assert "Ran pytest locally" in markdown


def test_format_omits_testing_section_when_none():
    description = PRDescription(summary="Small fix", changes=["Fixed typo"])

    markdown = format_description_markdown(description)

    assert "## Testing" not in markdown


def test_format_omits_changes_section_when_empty():
    description = PRDescription(summary="No specific changes tracked")

    markdown = format_description_markdown(description)

    assert "## Changes" not in markdown
