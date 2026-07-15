"""Parses unified diffs (as returned by the GitHub API) into structured
hunks that downstream tools (PR reviewer, code explanation, etc.) can
turn into LLM prompts without each tool re-implementing diff parsing.
"""

from __future__ import annotations

from dataclasses import dataclass

from unidiff import PatchSet


@dataclass(frozen=True)
class DiffHunk:
    """A single contiguous block of changes within one file."""

    file_path: str
    hunk_header: str
    added_lines: int
    removed_lines: int
    content: str  # the raw hunk text, including +/- markers, for the prompt


@dataclass(frozen=True)
class ParsedDiff:
    hunks: list[DiffHunk]
    files_changed: int
    total_added: int
    total_removed: int


def parse_diff(raw_diff: str, *, ignore_paths: list[str] | None = None) -> ParsedDiff:
    """Parse a unified diff string into structured hunks.

    ignore_paths supports simple glob-style patterns (e.g. "*.generated.ts",
    "vendor/**") matched against each file's path. Matching files are
    excluded entirely, keeping generated/vendored code out of the LLM's
    context and out of review comments.
    """
    ignore_paths = ignore_paths or []
    patch_set = PatchSet(raw_diff)

    hunks: list[DiffHunk] = []
    total_added = 0
    total_removed = 0
    files_changed = 0

    for patched_file in patch_set:
        file_path = patched_file.path
        if _is_ignored(file_path, ignore_paths):
            continue

        files_changed += 1
        for hunk in patched_file:
            added = hunk.added
            removed = hunk.removed
            total_added += added
            total_removed += removed
            hunks.append(
                DiffHunk(
                    file_path=file_path,
                    hunk_header=str(hunk).splitlines()[0] if str(hunk) else "",
                    added_lines=added,
                    removed_lines=removed,
                    content=str(hunk),
                )
            )

    return ParsedDiff(
        hunks=hunks,
        files_changed=files_changed,
        total_added=total_added,
        total_removed=total_removed,
    )


def _is_ignored(file_path: str, patterns: list[str]) -> bool:
    import fnmatch

    return any(fnmatch.fnmatch(file_path, pattern) for pattern in patterns)
