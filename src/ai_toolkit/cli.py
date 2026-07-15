"""CLI entrypoint for ai-github-toolkit.

This is intentionally minimal at this stage of scaffolding: it exists to
prove the pip-install -> console-script -> invocation path works before
any real logic (diff fetching, LLM calls) is wired in. Real subcommands
(e.g. `review-pr`) get added incrementally on top of this skeleton.
"""

from __future__ import annotations

import argparse
import sys

from ai_toolkit import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-toolkit",
        description="AI-powered GitHub automation tools",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"ai-toolkit {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")

    hello = subparsers.add_parser(
        "hello",
        help="Sanity-check command: confirms the CLI is installed and runnable.",
    )
    hello.set_defaults(func=_cmd_hello)

    return parser


def _cmd_hello(_args: argparse.Namespace) -> int:
    print("ai-toolkit is installed and working.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
