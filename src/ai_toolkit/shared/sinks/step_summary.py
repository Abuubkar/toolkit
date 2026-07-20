from __future__ import annotations

import os
from pathlib import Path

from ai_toolkit.shared.telemetry import MetricsSnapshot


def format_summary_markdown(snapshot: MetricsSnapshot) -> str:
    status_icon = "✅" if snapshot.outcome == "success" else "⚠️" if snapshot.outcome == "partial" else "❌"

    lines = [
        "## AI PR Reviewer — Run Summary",
        f"{status_icon} {snapshot.review_comments_posted} comment(s) posted · "
        f"{snapshot.items_analyzed} item(s) analyzed",
        f"⏱ {snapshot.total_duration_seconds:.1f}s total · "
        f"🔤 {snapshot.llm_tokens_input} in / {snapshot.llm_tokens_output} out tokens · "
        f"💰 ~${snapshot.estimated_cost_usd():.4f} (estimate)",
    ]

    if snapshot.llm_retry_count:
        lines.append(f"⚠ {snapshot.llm_retry_count} malformed-response retry(ies)")

    if snapshot.outcome != "success" and snapshot.error_message:
        lines.append(f"\n**Error:** {snapshot.error_message}")

    lines.append(
        "\n*Cost is an estimate based on a static pricing table and may not "
        "reflect your provider's current billing.*"
    )

    return "\n".join(lines) + "\n"


def write_step_summary(snapshot: MetricsSnapshot) -> bool:
    """Returns False (no-op) when GITHUB_STEP_SUMMARY isn't set."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return False

    markdown = format_summary_markdown(snapshot)
    with Path(summary_path).open("a", encoding="utf-8") as f:
        f.write(markdown)
    return True
