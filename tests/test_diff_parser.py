from pathlib import Path

from ai_toolkit.core.diff_parser import parse_diff

FIXTURE = (Path(__file__).parent / "fixtures" / "sample.diff").read_text()


def test_parses_hunks_from_both_files():
    result = parse_diff(FIXTURE)

    assert result.files_changed == 2
    assert len(result.hunks) == 2
    paths = {hunk.file_path for hunk in result.hunks}
    assert paths == {"src/utils.py", "dist/bundle.generated.ts"}


def test_counts_added_and_removed_lines():
    result = parse_diff(FIXTURE)

    # src/utils.py hunk: +2 added ("if total < 0" line + "raise" line kept,
    # "return total" removed then re-added), dist hunk: +1/-1
    assert result.total_added > 0
    assert result.total_removed > 0


def test_ignore_paths_excludes_matching_files():
    result = parse_diff(FIXTURE, ignore_paths=["*.generated.ts"])

    assert result.files_changed == 1
    assert all(hunk.file_path == "src/utils.py" for hunk in result.hunks)


def test_ignore_paths_glob_on_directory():
    diff_with_vendor = FIXTURE + (
        "\ndiff --git a/vendor/lib.py b/vendor/lib.py\n"
        "index 111..222 100644\n--- a/vendor/lib.py\n+++ b/vendor/lib.py\n"
        "@@ -1 +1 @@\n-old\n+new\n"
    )

    result = parse_diff(diff_with_vendor, ignore_paths=["vendor/**"])

    assert "vendor/lib.py" not in {h.file_path for h in result.hunks}
