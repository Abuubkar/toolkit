"""CLI entrypoint for ai-github-toolkit."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from ai_toolkit import __version__
from ai_toolkit.core.config import load_config
from ai_toolkit.core.github_client import GitHubClient
from ai_toolkit.core.pr_context import resolve_pr_number
from ai_toolkit.providers.factory import build_provider_from_env
from ai_toolkit.shared.errors import GitHubAPIError, LLMProviderError
from ai_toolkit.shared.sinks.step_summary import write_step_summary
from ai_toolkit.shared.telemetry import MetricsCollector
from ai_toolkit.tools.pr_reviewer.reviewer import ReviewParsingError, review_pull_request


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-toolkit",
        description="AI-powered GitHub automation tools",
    )
    parser.add_argument("--version", action="version", version=f"ai-toolkit {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    hello = subparsers.add_parser("hello", help="Sanity-check: confirms the CLI runs.")
    hello.set_defaults(func=_cmd_hello)

    review_pr = subparsers.add_parser("review-pr", help="Run the AI PR reviewer on a pull request.")
    review_pr.add_argument("--config-path", default=".github/pr-reviewer.yml")
    review_pr.add_argument(
        "--pr-number",
        type=int,
        default=None,
        help="PR number to review. Defaults to reading GITHUB_EVENT_PATH.",
    )
    review_pr.set_defaults(func=_cmd_review_pr)

    return parser


def _cmd_hello(_args: argparse.Namespace) -> int:
    print("ai-toolkit is installed and working.")
    return 0


def _cmd_review_pr(args: argparse.Namespace) -> int:
    collector = MetricsCollector()
    try:
        token = os.environ.get("GITHUB_TOKEN")
        repo = os.environ.get("GITHUB_REPOSITORY")
        if not token or not repo:
            print("GITHUB_TOKEN and GITHUB_REPOSITORY must both be set.", file=sys.stderr)
            return 1

        pr_number = resolve_pr_number(explicit=args.pr_number)
        config = load_config(args.config_path)
        github_client = GitHubClient(token=token, repo=repo)
        provider = build_provider_from_env()

        outcome = asyncio.run(
            review_pull_request(github_client, provider, pr_number, config, collector)
        )

        pr_info = github_client.get_pull_request(pr_number)
        collector.record_github_call()
        for comment in outcome.result.comments:
            github_client.post_review_comment(
                pr_number,
                commit_sha=pr_info.head_sha,
                file_path=comment.file_path,
                line=comment.line,
                body=f"**[{comment.severity}]** {comment.comment}",
            )
            collector.record_github_call()

        collector.record_comments_posted(len(outcome.result.comments))
        collector.record_outcome("success")
        write_step_summary(collector.finalize())

        print(
            f"Review complete: {len(outcome.result.comments)} comment(s) posted, "
            f"{outcome.hunks_analyzed} hunk(s) analyzed"
            + (" (retried once on malformed response)" if outcome.retried else "")
        )
        return 0

    except (GitHubAPIError, LLMProviderError, ReviewParsingError, RuntimeError) as exc:
        collector.record_outcome("failed", error_message=str(exc))
        write_step_summary(collector.finalize())
        print(f"review-pr failed: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

