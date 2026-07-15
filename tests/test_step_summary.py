from ai_toolkit.shared.sinks.step_summary import format_summary_markdown, write_step_summary
from ai_toolkit.shared.telemetry import MetricsSnapshot


def test_format_includes_key_metrics():
    snapshot = MetricsSnapshot(
        review_comments_posted=3,
        hunks_analyzed=10,
        llm_tokens_input=500,
        llm_tokens_output=100,
        total_duration_seconds=12.3,
        model="gemini-3-flash-preview",
    )

    markdown = format_summary_markdown(snapshot)

    assert "3 comment(s) posted" in markdown
    assert "10 hunk(s) analyzed" in markdown
    assert "500 in / 100 out tokens" in markdown
    assert "12.3s total" in markdown
    assert "estimate" in markdown


def test_format_shows_retry_warning_when_present():
    snapshot = MetricsSnapshot(llm_retry_count=1)

    markdown = format_summary_markdown(snapshot)

    assert "retry" in markdown.lower()


def test_format_omits_retry_line_when_zero():
    snapshot = MetricsSnapshot(llm_retry_count=0)

    markdown = format_summary_markdown(snapshot)

    assert "retry" not in markdown.lower()


def test_format_shows_error_on_failure():
    snapshot = MetricsSnapshot(outcome="failed", error_message="LLM response could not be parsed")

    markdown = format_summary_markdown(snapshot)

    assert "❌" in markdown
    assert "LLM response could not be parsed" in markdown


def test_write_step_summary_returns_false_when_env_unset(monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    result = write_step_summary(MetricsSnapshot())

    assert result is False


def test_write_step_summary_writes_to_file_when_env_set(tmp_path, monkeypatch):
    summary_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    result = write_step_summary(MetricsSnapshot(review_comments_posted=2))

    assert result is True
    content = summary_file.read_text()
    assert "2 comment(s) posted" in content


def test_write_step_summary_appends_not_overwrites(tmp_path, monkeypatch):
    summary_file = tmp_path / "summary.md"
    summary_file.write_text("# Existing content\n")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    write_step_summary(MetricsSnapshot())

    content = summary_file.read_text()
    assert content.startswith("# Existing content")
    assert "AI PR Reviewer" in content
