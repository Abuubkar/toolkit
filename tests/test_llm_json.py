import json

import pytest
from pydantic import BaseModel

from ai_toolkit.providers.base import LLMProvider, LLMResponse
from ai_toolkit.shared.llm_json import StructuredOutputError, complete_structured


class SampleSchema(BaseModel):
    value: str


class FakeProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = responses
        self.call_count = 0

    async def complete(self, system_prompt, user_prompt, *, max_tokens=2000):
        text = self._responses[self.call_count]
        self.call_count += 1
        return LLMResponse(content=text, model="fake-model")


@pytest.mark.asyncio
async def test_happy_path():
    provider = FakeProvider([json.dumps({"value": "ok"})])
    result, retried = await complete_structured(provider, SampleSchema, "sys", "user")

    assert result.value == "ok"
    assert retried is False
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_strips_code_fences():
    fenced = "```json\n" + json.dumps({"value": "ok"}) + "\n```"
    provider = FakeProvider([fenced])
    result, _ = await complete_structured(provider, SampleSchema, "sys", "user")

    assert result.value == "ok"


@pytest.mark.asyncio
async def test_retries_once_then_succeeds():
    provider = FakeProvider(["not json", json.dumps({"value": "fixed"})])
    result, retried = await complete_structured(provider, SampleSchema, "sys", "user")

    assert result.value == "fixed"
    assert retried is True
    assert provider.call_count == 2


@pytest.mark.asyncio
async def test_raises_after_retry_also_fails():
    provider = FakeProvider(["bad", "still bad"])

    with pytest.raises(StructuredOutputError):
        await complete_structured(provider, SampleSchema, "sys", "user")

    assert provider.call_count == 2
