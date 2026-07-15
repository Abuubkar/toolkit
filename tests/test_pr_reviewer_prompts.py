from ai_toolkit.core.diff_parser import DiffHunk
from ai_toolkit.tools.pr_reviewer.prompts import build_retry_prompt, build_review_prompt

SAMPLE_HUNK = DiffHunk(
    file_path="src/utils.py",
    hunk_header="@@ -2,4 +2,6 @@",
    added_lines=2,
    removed_lines=0,
    content="@@ -2,4 +2,6 @@\n     total = 0\n+    if total < 0:\n+        raise ValueError()\n",
)


def test_prompt_includes_file_path_and_content():
    prompt = build_review_prompt([SAMPLE_HUNK], focus=["bugs"])

    assert "src/utils.py" in prompt
    assert "if total < 0" in prompt


def test_prompt_includes_focus_areas():
    prompt = build_review_prompt([SAMPLE_HUNK], focus=["security", "performance"])

    assert "security" in prompt
    assert "performance" in prompt


def test_prompt_omits_focus_line_when_empty():
    prompt = build_review_prompt([SAMPLE_HUNK], focus=[])

    assert "Focus areas" not in prompt


def test_prompt_handles_multiple_hunks():
    hunk2 = DiffHunk(
        file_path="src/other.py",
        hunk_header="@@ -1 +1 @@",
        added_lines=1,
        removed_lines=1,
        content="@@ -1 +1 @@\n-old\n+new\n",
    )
    prompt = build_review_prompt([SAMPLE_HUNK, hunk2], focus=[])

    assert "src/utils.py" in prompt
    assert "src/other.py" in prompt


def test_retry_prompt_includes_original_response():
    retry = build_retry_prompt("not valid json {{{")

    assert "not valid json {{{" in retry
    assert "JSON" in retry
