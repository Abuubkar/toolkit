from ai_toolkit.core.diff_parser import DiffHunk
from ai_toolkit.tools.pr_description.prompts import build_description_prompt

SAMPLE_HUNK = DiffHunk(
    file_path="src/utils.py",
    hunk_header="@@ -2,4 +2,6 @@",
    added_lines=2,
    removed_lines=0,
    content="@@ -2,4 +2,6 @@\n     total = 0\n+    if total < 0:\n+        raise ValueError()\n",
)


def test_prompt_includes_file_path_and_diff_content():
    prompt = build_description_prompt([SAMPLE_HUNK])

    assert "src/utils.py" in prompt
    assert "if total < 0" in prompt


def test_prompt_handles_multiple_hunks():
    hunk2 = DiffHunk(
        file_path="src/other.py",
        hunk_header="@@ -1 +1 @@",
        added_lines=1,
        removed_lines=1,
        content="@@ -1 +1 @@\n-old\n+new\n",
    )
    prompt = build_description_prompt([SAMPLE_HUNK, hunk2])

    assert "src/utils.py" in prompt
    assert "src/other.py" in prompt
