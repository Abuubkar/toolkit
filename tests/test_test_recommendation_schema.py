import pytest
from pydantic import ValidationError

from ai_toolkit.tools.test_recommendation.schema import CoverageGap, CoverageReport


def test_valid_priority_parses():
    rec = CoverageGap(file_path="a.py", description="Test the edge case", priority="high")
    assert rec.priority == "high"


def test_invalid_priority_rejected():
    with pytest.raises(ValidationError, match="priority must be one of"):
        CoverageGap(file_path="a.py", description="x", priority="urgent")


def test_result_defaults_to_empty_recommendations():
    result = CoverageReport(summary="All good")
    assert result.recommendations == []


def test_full_json_parses():
    raw = {
        "summary": "One gap found",
        "recommendations": [
            {
                "file_path": "src/utils.py",
                "description": "Test negative input raises ValueError",
                "priority": "high",
            }
        ],
    }
    result = CoverageReport.model_validate(raw)
    assert len(result.recommendations) == 1
