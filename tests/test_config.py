import pytest

from ai_toolkit.core.config import load_config


def test_missing_file_returns_defaults(tmp_path):
    config = load_config(tmp_path / "does-not-exist.yml")

    assert config.focus == ["bugs", "security", "performance"]
    assert config.max_comments == 10
    assert config.severity_threshold == "medium"


def test_loads_custom_values(tmp_path):
    config_file = tmp_path / "pr-reviewer.yml"
    config_file.write_text(
        "review:\n"
        "  focus: [security]\n"
        "  ignore_paths: ['*.generated.ts', 'vendor/**']\n"
        "  max_comments: 5\n"
        "  severity_threshold: high\n"
    )

    config = load_config(config_file)

    assert config.focus == ["security"]
    assert config.ignore_paths == ["*.generated.ts", "vendor/**"]
    assert config.max_comments == 5
    assert config.severity_threshold == "high"


def test_invalid_severity_threshold_raises(tmp_path):
    config_file = tmp_path / "pr-reviewer.yml"
    config_file.write_text("review:\n  severity_threshold: critical\n")

    with pytest.raises(ValueError, match="severity_threshold"):
        load_config(config_file)


def test_empty_file_returns_defaults(tmp_path):
    config_file = tmp_path / "pr-reviewer.yml"
    config_file.write_text("")

    config = load_config(config_file)

    assert config.max_comments == 10
