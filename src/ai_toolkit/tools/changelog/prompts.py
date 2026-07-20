from __future__ import annotations

from ai_toolkit.core.github_client import CommitSummary

SYSTEM_PROMPT = """You are writing a changelog from a list of git commits, \
following the Keep a Changelog convention.

Categorize each meaningful change into one of exactly these categories: \
Added, Changed, Deprecated, Removed, Fixed, Security.

Respond with ONLY valid JSON matching this exact schema, and nothing else \
— no markdown code fences, no preamble:

{
  "entries": [
    {"category": "<one of the six categories above>", "description": "<user-facing, one sentence>"}
  ]
}

Skip commits that aren't user-facing (e.g. "fix typo", "update CI config", \
formatting-only changes, merge commits) — the changelog is for people using \
this software, not repo internals. Merge multiple commits describing the \
same change into a single entry rather than repeating it. If nothing is \
user-facing, return an empty entries list."""


def build_changelog_prompt(commits: list[CommitSummary]) -> str:
    commit_lines = [f"- {c.sha}: {c.message.splitlines()[0]}" for c in commits]
    commit_text = "\n".join(commit_lines)
    return f"Generate a changelog from these commits:\n\n{commit_text}"
