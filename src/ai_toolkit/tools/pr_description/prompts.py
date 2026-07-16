from __future__ import annotations

from ai_toolkit.core.diff_parser import DiffHunk

SYSTEM_PROMPT = """You are writing a pull request description from its diff.

Respond with ONLY valid JSON matching this exact schema, and nothing else \
— no markdown code fences, no preamble:

{
  "summary": "<1-3 sentence overview of what this PR does and why>",
  "changes": ["<bullet point of a specific change>", "..."],
  "testing_notes": "<how this was or should be tested, or null if unclear>"
}

Be specific and concrete — reference actual function/file names from the \
diff rather than generic descriptions. Do not invent testing steps that \
aren't evidenced by the diff; use null for testing_notes if you can't tell."""


def build_description_prompt(hunks: list[DiffHunk]) -> str:
    hunk_sections = [f"File: {hunk.file_path}\n{hunk.content}" for hunk in hunks]
    diff_text = "\n\n".join(hunk_sections)
    return f"Write a PR description for the following diff:\n\n{diff_text}"
