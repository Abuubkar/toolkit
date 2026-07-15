import json

import pytest

from ai_toolkit.core.config import ReviewConfig
from ai_toolkit.core.diff_parser import DiffHunk
from ai_toolkit.providers.base import LLMProvider, LLMResponse
from ai_toolkit.tools.pr_reviewer.reviewer import ReviewParsingError, review_diff_hunks

SAMPLE_HUNK = DiffHunk(
    file_path="src/utils.py",
    hunk_header="@@ -2,4 +2,6 @@",
    added_lines=2,
    removed_lines=0,
    content="@@ -2,4 +2,6 @@\n     total = 0\n+    if total < 0:\n+        raise ValueError()\n",
)


class FakeProvider(LLMProvider):
    """Scriptable fake: returns each item in `responses` in order, one per
    call to complete(). Records call count for retry-path assertions.
    """

    def __init__(self, responses: list[str]):
        self._responses = responses
        self.call_count = 0

    async def complete(self, system_prompt, user_prompt, *, max_tokens=2000):
        response_text = self._responses[self.call_count]
        self.call_count += 1
        return LLMResponse(content=response_text, model="fake-model")


def _default_config(**overrides) -> ReviewConfig:
    return ReviewConfig(**overrides)


@pytest.mark.asyncio
async def test_empty_hunks_short_circuits_without_calling_provider():
    provider = FakeProvider(responses=[])
    outcome = await review_diff_hunks([], provider, _default_config())

    assert outcome.result.comments == []
    assert outcome.hunks_analyzed == 0
    assert provider.call_count == 0


@pytest.mark.asyncio
async def test_happy_path_parses_valid_response():
    valid_json = json.dumps(
        {
            "summary": "One issue found",
            "comments": [
                {
                    "file_path": "src/utils.py",
                    "line": 5,
                    "severity": "high",
                    "comment": "Missing null check",
                }
            ],
        }
    )
    provider = FakeProvider(responses=[valid_json])
    outcome = await review_diff_hunks([SAMPLE_HUNK], provider, _default_config())

    assert outcome.retried is False
    assert len(outcome.result.comments) == 1
    assert outcome.result.comments[0].severity == "high"
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_strips_markdown_code_fences():
    fenced = "```json\n" + json.dumps({"summary": "ok", "comments": []}) + "\n```"
    provider = FakeProvider(responses=[fenced])
    outcome = await review_diff_hunks([SAMPLE_HUNK], provider, _default_config())

    assert outcome.result.summary == "ok"


@pytest.mark.asyncio
async def test_retries_once_on_malformed_json_then_succeeds():
    bad_response = "not json at all {{{"
    good_response = json.dumps({"summary": "fixed", "comments": []})
    provider = FakeProvider(responses=[bad_response, good_response])

    outcome = await review_diff_hunks([SAMPLE_HUNK], provider, _default_config())

    assert outcome.retried is True
    assert outcome.result.summary == "fixed"
    assert provider.call_count == 2


@pytest.mark.asyncio
async def test_raises_review_parsing_error_after_retry_also_fails():
    provider = FakeProvider(responses=["bad {{{", "still bad {{{"])

    with pytest.raises(ReviewParsingError):
        await review_diff_hunks([SAMPLE_HUNK], provider, _default_config())

    assert provider.call_count == 2


@pytest.mark.asyncio
async def test_filters_comments_below_severity_threshold():
    raw = json.dumps(
        {
            "summary": "Mixed severities",
            "comments": [
                {"file_path": "a.py", "line": 1, "severity": "low", "comment": "nit"},
                {"file_path": "a.py", "line": 2, "severity": "medium", "comment": "check this"},
                {"file_path": "a.py", "line": 3, "severity": "high", "comment": "bug"},
            ],
        }
    )
    provider = FakeProvider(responses=[raw])
    config = _default_config(severity_threshold="medium")

    outcome = await review_diff_hunks([SAMPLE_HUNK], provider, config)

    severities = {c.severity for c in outcome.result.comments}
    assert severities == {"medium", "high"}
    assert "low" not in severities


@pytest.mark.asyncio
async def test_truncates_to_max_comments():
    comments = [
        {"file_path": "a.py", "line": i, "severity": "high", "comment": f"issue {i}"}
        for i in range(1, 6)
    ]
    raw = json.dumps({"summary": "many issues", "comments": comments})
    provider = FakeProvider(responses=[raw])
    config = _default_config(max_comments=2)

    outcome = await review_diff_hunks([SAMPLE_HUNK], provider, config)

    assert len(outcome.result.comments) == 2
