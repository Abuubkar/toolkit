import pytest
from pydantic import ValidationError

from ai_toolkit.tools.changelog.schema import Changelog, ChangelogEntry


def test_valid_category_parses():
    entry = ChangelogEntry(category="Added", description="New PR reviewer tool")
    assert entry.category == "Added"


def test_invalid_category_rejected():
    with pytest.raises(ValidationError, match="category must be one of"):
        ChangelogEntry(category="Improved", description="x")


def test_changelog_defaults_to_empty_entries():
    changelog = Changelog()
    assert changelog.entries == []


def test_full_json_parses():
    raw = {
        "entries": [
            {"category": "Fixed", "description": "Fixed negative total bug"},
            {"category": "Added", "description": "New changelog tool"},
        ]
    }
    changelog = Changelog.model_validate(raw)
    assert len(changelog.entries) == 2
