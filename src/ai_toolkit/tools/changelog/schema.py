from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

CATEGORIES = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security")


class ChangelogEntry(BaseModel):
    category: str
    description: str

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        if value not in CATEGORIES:
            raise ValueError(f"category must be one of {CATEGORIES}, got {value!r}")
        return value


class Changelog(BaseModel):
    entries: list[ChangelogEntry] = Field(default_factory=list)
