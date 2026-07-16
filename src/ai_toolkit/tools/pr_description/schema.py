from __future__ import annotations

from pydantic import BaseModel, Field


class PRDescription(BaseModel):
    summary: str
    changes: list[str] = Field(default_factory=list)
    testing_notes: str | None = None
