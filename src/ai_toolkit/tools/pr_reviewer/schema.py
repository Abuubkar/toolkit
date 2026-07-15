"""Structured output schema the LLM's JSON response is validated against."""

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
    return _SEVERITY_RANK[comment.severity] >= _SEVERITY_RANK[threshold]
