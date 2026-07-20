from ai_toolkit.core.github_client import CommitSummary
from ai_toolkit.tools.changelog.prompts import build_changelog_prompt

COMMITS = [
    CommitSummary(sha="abc1234", message="Add negative-total validation\n\nDetail.", author="Abubakar"),
    CommitSummary(sha="def5678", message="Fix typo in README", author="Abubakar"),
]


def test_prompt_includes_sha_and_first_line_of_message():
    prompt = build_changelog_prompt(COMMITS)

    assert "abc1234" in prompt
    assert "Add negative-total validation" in prompt
    assert "Detail." not in prompt  # only first line should be included


def test_prompt_includes_all_commits():
    prompt = build_changelog_prompt(COMMITS)

    assert "def5678" in prompt
    assert "Fix typo in README" in prompt
