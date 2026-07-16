from unittest.mock import patch

from ai_toolkit.cli import main
from ai_toolkit.core.github_client import PullRequestInfo
from ai_toolkit.shared.errors import GitHubAPIError
from ai_toolkit.tools.pr_description.generator import PRDescriptionOutcome
from ai_toolkit.tools.pr_description.schema import PRDescription
from ai_toolkit.tools.pr_reviewer.reviewer import ReviewOutcome
from ai_toolkit.tools.pr_reviewer.schema import ReviewComment, ReviewResult


def test_hello_command_runs():
    assert main(["hello"]) == 0


def test_review_pr_fails_fast_without_github_env(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    exit_code = main(["review-pr", "--pr-number", "1"])

    assert exit_code == 1
    assert "GITHUB_TOKEN and GITHUB_REPOSITORY" in capsys.readouterr().err


def test_review_pr_posts_comments_and_reports_summary(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "abubakar/markpoint")
    monkeypatch.setenv("AI_API_KEY", "fake-key")

    fake_outcome = ReviewOutcome(
        result=ReviewResult(
            summary="one issue",
            comments=[
                ReviewComment(file_path="a.py", line=5, severity="high", comment="bug here")
            ],
        ),
        hunks_analyzed=1,
        hunks_skipped_ignored=0,
        retried=False,
    )

    with (
        patch("ai_toolkit.cli.GitHubClient") as MockClient,
        patch("ai_toolkit.cli.build_provider_from_env"),
        patch("ai_toolkit.cli.review_pull_request") as mock_review,
    ):
        mock_client_instance = MockClient.return_value
        mock_client_instance.get_pull_request.return_value = PullRequestInfo(
            number=1, title="t", body="", base_sha="base", head_sha="head123", state="open"
        )

        async def fake_review(*_args, **_kwargs):
            return fake_outcome

        mock_review.side_effect = fake_review

        exit_code = main(["review-pr", "--pr-number", "1"])

        assert exit_code == 0
        mock_client_instance.post_review_comment.assert_called_once_with(
            1,
            commit_sha="head123",
            file_path="a.py",
            line=5,
            body="**[high]** bug here",
        )
        out = capsys.readouterr().out
        assert "1 comment(s) posted" in out
        assert "AI PR Reviewer — Run Summary" in out
        assert "tokens" in out


def test_review_pr_handles_github_api_error_gracefully(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "abubakar/markpoint")
    monkeypatch.setenv("AI_API_KEY", "fake-key")

    with (
        patch("ai_toolkit.cli.GitHubClient") as MockClient,
        patch("ai_toolkit.cli.build_provider_from_env"),
    ):
        MockClient.return_value.get_pull_request.side_effect = GitHubAPIError(404, "Not Found")
        # review_pull_request is called before get_pull_request in our flow,
        # so patch it to raise directly for this test's purposes.
        with patch(
            "ai_toolkit.cli.review_pull_request",
            side_effect=GitHubAPIError(404, "Not Found"),
        ):
            exit_code = main(["review-pr", "--pr-number", "1"])

    assert exit_code == 1
    assert "review-pr failed" in capsys.readouterr().err


def test_describe_pr_fills_empty_body(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "abubakar/markpoint")
    monkeypatch.setenv("AI_API_KEY", "fake-key")

    fake_outcome = PRDescriptionOutcome(
        description=PRDescription(summary="Adds validation", changes=["Added check"]),
        hunks_analyzed=2,
        retried=False,
    )

    with (
        patch("ai_toolkit.cli.GitHubClient") as MockClient,
        patch("ai_toolkit.cli.build_provider_from_env"),
        patch("ai_toolkit.cli.generate_pr_description") as mock_generate,
    ):
        mock_client_instance = MockClient.return_value
        mock_client_instance.get_pull_request.return_value = PullRequestInfo(
            number=1, title="t", body="", base_sha="base", head_sha="head123", state="open"
        )

        async def fake_generate(*_args, **_kwargs):
            return fake_outcome

        mock_generate.side_effect = fake_generate

        exit_code = main(["describe-pr", "--pr-number", "1"])

        assert exit_code == 0
        mock_client_instance.update_pull_request_body.assert_called_once()
        mock_client_instance.post_issue_comment.assert_not_called()
        assert "filled in the empty PR description" in capsys.readouterr().out


def test_describe_pr_posts_comment_when_body_exists(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "abubakar/markpoint")
    monkeypatch.setenv("AI_API_KEY", "fake-key")

    fake_outcome = PRDescriptionOutcome(
        description=PRDescription(summary="Adds validation"),
        hunks_analyzed=1,
        retried=False,
    )

    with (
        patch("ai_toolkit.cli.GitHubClient") as MockClient,
        patch("ai_toolkit.cli.build_provider_from_env"),
        patch("ai_toolkit.cli.generate_pr_description") as mock_generate,
    ):
        mock_client_instance = MockClient.return_value
        mock_client_instance.get_pull_request.return_value = PullRequestInfo(
            number=1,
            title="t",
            body="I already wrote a description",
            base_sha="base",
            head_sha="head123",
            state="open",
        )

        async def fake_generate(*_args, **_kwargs):
            return fake_outcome

        mock_generate.side_effect = fake_generate

        exit_code = main(["describe-pr", "--pr-number", "1"])

        assert exit_code == 0
        mock_client_instance.post_issue_comment.assert_called_once()
        mock_client_instance.update_pull_request_body.assert_not_called()
        assert "posted as a comment" in capsys.readouterr().out
