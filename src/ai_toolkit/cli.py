"""CLI entrypoint for ai-github-toolkit."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from ai_toolkit import __version__
from ai_toolkit.core.config import load_config, load_ignore_paths
from ai_toolkit.core.github_client import GitHubClient
from ai_toolkit.core.pr_context import resolve_pr_number
from ai_toolkit.providers.factory import build_provider_from_env
from ai_toolkit.shared.errors import GitHubAPIError, LLMProviderError
from ai_toolkit.shared.llm_json import StructuredOutputError
from ai_toolkit.shared.sinks.step_summary import format_summary_markdown, write_step_summary
from ai_toolkit.shared.telemetry import MetricsCollector
from ai_toolkit.tools.pr_description.generator import (
    format_description_markdown,
    generate_pr_description,
)
from ai_toolkit.tools.pr_reviewer.reviewer import review_pull_request


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

    describe_pr = subparsers.add_parser(
        "describe-pr", help="Generate a PR description from its diff."
    )
    describe_pr.add_argument("--config-path", default=".github/pr-reviewer.yml")
    describe_pr.add_argument(
        "--pr-number",
        type=int,
        default=None,
        help="PR number to describe. Defaults to reading GITHUB_EVENT_PATH.",
    )
    describe_pr.set_defaults(func=_cmd_describe_pr)

    return parser


def _cmd_hello(_args: argparse.Namespace) -> int:
    print("ai-toolkit is installed and working.")
    return 0


def _require_github_env() -> tuple[str, str] | None:
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("GITHUB_TOKEN and GITHUB_REPOSITORY must both be set.", file=sys.stderr)
        return None
    return token, repo


def _finish(collector: MetricsCollector, outcome: str, *, error_message: str | None = None):
    collector.record_outcome(outcome, error_message=error_message)
    snapshot = collector.finalize()
    write_step_summary(snapshot)
    return snapshot


def _cmd_review_pr(args: argparse.Namespace) -> int:
    collector = MetricsCollector()
    try:
        env = _require_github_env()
        if env is None:
            return 1
        token, repo = env

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
        snapshot = _finish(collector, "success")

        print(
            f"Review complete: {len(outcome.result.comments)} comment(s) posted, "
            f"{outcome.hunks_analyzed} hunk(s) analyzed"
            + (" (retried once on malformed response)" if outcome.retried else "")
        )
        print("\n" + format_summary_markdown(snapshot))
        return 0

    except (GitHubAPIError, LLMProviderError, StructuredOutputError, RuntimeError) as exc:
        snapshot = _finish(collector, "failed", error_message=str(exc))
        print(f"review-pr failed: {exc}", file=sys.stderr)
        print("\n" + format_summary_markdown(snapshot), file=sys.stderr)
        return 1


def _cmd_describe_pr(args: argparse.Namespace) -> int:
    collector = MetricsCollector()
    try:
        env = _require_github_env()
        if env is None:
            return 1
        token, repo = env

        pr_number = resolve_pr_number(explicit=args.pr_number)
        ignore_paths = load_ignore_paths(args.config_path)
        github_client = GitHubClient(token=token, repo=repo)
        provider = build_provider_from_env()

        outcome = asyncio.run(
            generate_pr_description(github_client, provider, pr_number, ignore_paths, collector)
        )

        markdown = format_description_markdown(outcome.description)
        pr_info = github_client.get_pull_request(pr_number)
        collector.record_github_call()

        if pr_info.body.strip():
            # Never overwrite an existing human-written description —
            # post the suggestion as a comment instead.
            github_client.post_issue_comment(
                pr_number, f"**Suggested PR description** (existing description was kept):\n\n{markdown}"
            )
            action_taken = "posted as a comment (PR already has a description)"
        else:
            github_client.update_pull_request_body(pr_number, markdown)
            action_taken = "filled in the empty PR description"
        collector.record_github_call()

        collector.record_comments_posted(1)
        snapshot = _finish(collector, "success")

        print(f"Description generated: {action_taken}, {outcome.hunks_analyzed} hunk(s) analyzed")
        print("\n" + format_summary_markdown(snapshot))
        return 0

    except (GitHubAPIError, LLMProviderError, StructuredOutputError, RuntimeError) as exc:
        snapshot = _finish(collector, "failed", error_message=str(exc))
        print(f"describe-pr failed: {exc}", file=sys.stderr)
        print("\n" + format_summary_markdown(snapshot), file=sys.stderr)
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

