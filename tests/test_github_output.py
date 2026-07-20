from ai_toolkit.shared.sinks.github_output import write_github_output


def test_returns_false_when_env_unset(monkeypatch):
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)

    assert write_github_output("changelog", "some text") is False


def test_writes_multiline_value_with_delimiter(tmp_path, monkeypatch):
    output_file = tmp_path / "output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    result = write_github_output("changelog", "line one\nline two")

    assert result is True
    content = output_file.read_text()
    assert "changelog<<ghadelim_" in content
    assert "line one\nline two" in content


def test_appends_not_overwrites(tmp_path, monkeypatch):
    output_file = tmp_path / "output.txt"
    output_file.write_text("existing=value\n")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    write_github_output("changelog", "text")

    content = output_file.read_text()
    assert content.startswith("existing=value")
    assert "changelog<<" in content
