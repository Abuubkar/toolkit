from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

PRIORITIES = ("low", "medium", "high")


class CoverageGap(BaseModel):
    file_path: str
    description: str
    priority: str

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        if value not in PRIORITIES:
            raise ValueError(f"priority must be one of {PRIORITIES}, got {value!r}")
        return value


class CoverageReport(BaseModel):
    summary: str
    recommendations: list[CoverageGap] = Field(default_factory=list)
