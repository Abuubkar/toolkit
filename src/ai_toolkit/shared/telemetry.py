from __future__ import annotations

import time
from dataclasses import dataclass

_MODEL_PRICING_PER_MILLION_TOKENS: dict[str, tuple[float, float]] = {
    # (input, output) USD per 1M tokens. Estimates only — see step_summary.py.
    "gemini-3-flash-preview": (0.10, 0.40),
    "gemini-2.5-flash": (0.30, 2.50),
}
_DEFAULT_PRICING = (0.20, 1.00)


@dataclass
class MetricsSnapshot:
    llm_call_count: int = 0
    llm_retry_count: int = 0
    llm_tokens_input: int = 0
    llm_tokens_output: int = 0
    llm_duration_seconds: float = 0.0
    github_api_call_count: int = 0
    review_comments_posted: int = 0
    items_analyzed: int = 0
    outcome: str = "success"
    error_message: str | None = None
    model: str | None = None
    total_duration_seconds: float = 0.0

    def estimated_cost_usd(self) -> float:
        input_price, output_price = _MODEL_PRICING_PER_MILLION_TOKENS.get(
            self.model or "", _DEFAULT_PRICING
        )
        return (self.llm_tokens_input / 1_000_000 * input_price) + (
            self.llm_tokens_output / 1_000_000 * output_price
        )


class MetricsCollector:
    def __init__(self):
        self._snapshot = MetricsSnapshot()
        self._start_time = time.monotonic()

    def record_llm_call(self, *, duration_seconds: float, input_tokens: int, output_tokens: int, model: str):
        self._snapshot.llm_call_count += 1
        self._snapshot.llm_duration_seconds += duration_seconds
        self._snapshot.llm_tokens_input += input_tokens or 0
        self._snapshot.llm_tokens_output += output_tokens or 0
        self._snapshot.model = model

    def record_retry(self):
        self._snapshot.llm_retry_count += 1

    def record_github_call(self):
        self._snapshot.github_api_call_count += 1

    def record_comments_posted(self, count: int):
        self._snapshot.review_comments_posted = count

    def record_items_analyzed(self, count: int):
        self._snapshot.items_analyzed = count

    def record_outcome(self, outcome: str, *, error_message: str | None = None):
        self._snapshot.outcome = outcome
        self._snapshot.error_message = error_message

    def finalize(self) -> MetricsSnapshot:
        self._snapshot.total_duration_seconds = time.monotonic() - self._start_time
        return self._snapshot
