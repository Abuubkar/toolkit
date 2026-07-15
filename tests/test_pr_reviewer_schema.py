import pytest
from pydantic import ValidationError

from ai_toolkit.tools.pr_reviewer.schema import (
    ReviewComment,
    ReviewResult,
    meets_severity_threshold,
)


def test_valid_comment_parses():
    comment = ReviewComment(file_path="src/utils.py", line=15, severity="high", comment="Bug")
    assert comment.severity == "high"


def test_invalid_severity_rejected():
    with pytest.raises(ValidationError, match="severity must be one of"):
        ReviewComment(file_path="a.py", line=1, severity="critical", comment="x")


def test_invalid_line_rejected():
    with pytest.raises(ValidationError, match="line must be >= 1"):
        ReviewComment(file_path="a.py", line=0, severity="low", comment="x")


def test_review_result_defaults_to_empty_comments():
    result = ReviewResult(summary="All good")
    assert result.comments == []


def test_full_llm_style_json_parses():
    raw = {
        "summary": "Found one issue",
        "comments": [
            {"file_path": "src/utils.py", "line": 15, "severity": "medium", "comment": "Check for None"}
        ],
    }
    result = ReviewResult.model_validate(raw)
    assert len(result.comments) == 1
    assert result.comments[0].file_path == "src/utils.py"


@pytest.mark.parametrize(
    "severity,threshold,expected",
    [
        ("low", "medium", False),
        ("medium", "medium", True),
        ("high", "medium", True),
        ("low", "low", True),
        ("high", "high", True),
        ("medium", "high", False),
    ],
)
def test_meets_severity_threshold(severity, threshold, expected):
    comment = ReviewComment(file_path="a.py", line=1, severity=severity, comment="x")
    assert meets_severity_threshold(comment, threshold) is expected
