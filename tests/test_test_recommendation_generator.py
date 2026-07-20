import json

import pytest

from ai_toolkit.core.diff_parser import DiffHunk
from ai_toolkit.providers.base import LLMProvider, LLMResponse
from ai_toolkit.shared.llm_json import StructuredOutputError
from ai_toolkit.tools.test_recommendation.generator import (
    MAX_RECOMMENDATIONS,
    CoverageReport,
    format_recommendations_markdown,
    recommend_tests_from_hunks,
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
    outcome = await recommend_tests_from_hunks([], provider)

    assert outcome.result.recommendations == []
    assert provider.call_count == 0


@pytest.mark.asyncio
async def test_happy_path():
    raw = json.dumps(
        {
            "summary": "One gap",
            "recommendations": [
                {
                    "file_path": "src/utils.py",
                    "description": "Test negative total raises",
                    "priority": "high",
                }
            ],
        }
    )
    provider = FakeProvider(responses=[raw])
    outcome = await recommend_tests_from_hunks([SAMPLE_HUNK], provider)

    assert len(outcome.result.recommendations) == 1
    assert outcome.retried is False
    assert outcome.hunks_analyzed == 1


@pytest.mark.asyncio
async def test_raises_on_malformed_response_after_retry():
    provider = FakeProvider(responses=["bad {{{", "still bad {{{"])

    with pytest.raises(StructuredOutputError):
        await recommend_tests_from_hunks([SAMPLE_HUNK], provider)


@pytest.mark.asyncio
async def test_caps_recommendations_at_max():
    recs = [
        {"file_path": "a.py", "description": f"gap {i}", "priority": "low"} for i in range(15)
    ]
    raw = json.dumps({"summary": "many gaps", "recommendations": recs})
    provider = FakeProvider(responses=[raw])

    outcome = await recommend_tests_from_hunks([SAMPLE_HUNK], provider)

    assert len(outcome.result.recommendations) == MAX_RECOMMENDATIONS


def test_format_lists_recommendations_with_priority_and_path():
    result = CoverageReport.model_validate(
        {
            "summary": "One gap",
            "recommendations": [
                {"file_path": "a.py", "description": "Test edge case", "priority": "high"}
            ],
        }
    )

    markdown = format_recommendations_markdown(result)

    assert "## Suggested test coverage" in markdown
    assert "[high]" in markdown
    assert "`a.py`" in markdown
    assert "Test edge case" in markdown


def test_format_handles_no_recommendations():
    result = CoverageReport(summary="Coverage looks adequate")

    markdown = format_recommendations_markdown(result)

    assert "Coverage looks adequate" in markdown
    assert "## Suggested test coverage" not in markdown
