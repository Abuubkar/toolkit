from ai_toolkit.tools.pr_description.schema import PRDescription


def test_defaults_to_empty_changes_and_null_testing_notes():
    description = PRDescription(summary="Fixes a bug")

    assert description.changes == []
    assert description.testing_notes is None


def test_full_json_parses():
    raw = {
        "summary": "Adds validation",
        "changes": ["Added null check", "Added test"],
        "testing_notes": "Ran pytest locally",
    }
    description = PRDescription.model_validate(raw)

    assert len(description.changes) == 2
    assert description.testing_notes == "Ran pytest locally"
