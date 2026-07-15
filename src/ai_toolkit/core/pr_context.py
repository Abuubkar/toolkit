from __future__ import annotations

import json
import os
from pathlib import Path


def resolve_pr_number(explicit: int | None = None) -> int:
    if explicit is not None:
        return explicit

    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        raise RuntimeError(
            "No PR number given and GITHUB_EVENT_PATH is not set. "
            "Pass --pr-number explicitly when running outside a pull_request workflow."
        )

    payload = json.loads(Path(event_path).read_text())
    pr_number = payload.get("pull_request", {}).get("number") or payload.get("number")
    if pr_number is None:
        raise RuntimeError(f"Could not find a PR number in event payload at {event_path}")

    return pr_number
