"""Structured output schema for the PR reviewer. The LLM is instructed
(see prompts.py) to return JSON matching this shape exactly. Validating
against this schema is what turns "the LLM said something" into "we
either have a usable review or a clear error" — see reviewer.py for how
a validation failure triggers one retry before failing loudly.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

SEVERITIES = ("low", "medium", "high")
_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}


class ReviewComment(BaseModel):
    file_path: str
    line: int
    severity: str
    comment: str

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        if value not in SEVERITIES:
            raise ValueError(f"severity must be one of {SEVERITIES}, got {value!r}")
        return value

    @field_validator("line")
    @classmethod
    def validate_line(cls, value: int) -> int:
        if value < 1:
            raise ValueError(f"line must be >= 1, got {value}")
        return value


class ReviewResult(BaseModel):
    summary: str
    comments: list[ReviewComment] = Field(default_factory=list)


def meets_severity_threshold(comment: ReviewComment, threshold: str) -> bool:
    """True if comment's severity is at or above the configured threshold.
    e.g. threshold='medium' keeps medium and high, drops low.
    """
    return _SEVERITY_RANK[comment.severity] >= _SEVERITY_RANK[threshold]
