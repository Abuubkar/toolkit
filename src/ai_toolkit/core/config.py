"""Loads and validates the consumer repo's review config
(default path: .github/pr-reviewer.yml). Falls back to sane defaults
if the file doesn't exist, so the tool works with zero config.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

VALID_SEVERITIES = ("low", "medium", "high")


class ReviewConfig(BaseModel):
    focus: list[str] = Field(default_factory=lambda: ["bugs", "security", "performance"])
    ignore_paths: list[str] = Field(default_factory=list)
    max_comments: int = 10
    severity_threshold: str = "medium"

    def model_post_init(self, __context) -> None:  # noqa: ANN001
        if self.severity_threshold not in VALID_SEVERITIES:
            raise ValueError(
                f"severity_threshold must be one of {VALID_SEVERITIES}, "
                f"got {self.severity_threshold!r}"
            )
        if self.max_comments < 1:
            raise ValueError("max_comments must be at least 1")


def load_config(config_path: str | Path = ".github/pr-reviewer.yml") -> ReviewConfig:
    path = Path(config_path)
    if not path.exists():
        return ReviewConfig()

    raw = yaml.safe_load(path.read_text()) or {}
    review_section = raw.get("review", {})
    return ReviewConfig(**review_section)
