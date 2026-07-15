from ai_toolkit.shared.telemetry import MetricsCollector, MetricsSnapshot


def test_collector_accumulates_llm_calls():
    collector = MetricsCollector()
    collector.record_llm_call(
        duration_seconds=1.5, input_tokens=100, output_tokens=20, model="gemini-3-flash-preview"
    )
    collector.record_llm_call(
        duration_seconds=0.5, input_tokens=50, output_tokens=10, model="gemini-3-flash-preview"
    )

    snapshot = collector.finalize()

    assert snapshot.llm_call_count == 2
    assert snapshot.llm_tokens_input == 150
    assert snapshot.llm_tokens_output == 30
    assert snapshot.llm_duration_seconds == 2.0


def test_collector_records_retry_and_github_calls():
    collector = MetricsCollector()
    collector.record_retry()
    collector.record_github_call()
    collector.record_github_call()

    snapshot = collector.finalize()

    assert snapshot.llm_retry_count == 1
    assert snapshot.github_api_call_count == 2


def test_collector_records_outcome_and_error():
    collector = MetricsCollector()
    collector.record_outcome("failed", error_message="boom")

    snapshot = collector.finalize()

    assert snapshot.outcome == "failed"
    assert snapshot.error_message == "boom"


def test_estimated_cost_uses_known_model_pricing():
    snapshot = MetricsSnapshot(
        llm_tokens_input=1_000_000, llm_tokens_output=1_000_000, model="gemini-3-flash-preview"
    )

    assert snapshot.estimated_cost_usd() == 0.10 + 0.40


def test_estimated_cost_falls_back_to_default_for_unknown_model():
    snapshot = MetricsSnapshot(
        llm_tokens_input=1_000_000, llm_tokens_output=0, model="some-unknown-model"
    )

    assert snapshot.estimated_cost_usd() == 0.20
