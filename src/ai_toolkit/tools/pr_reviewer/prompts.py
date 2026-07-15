"""Prompt templates for the PR reviewer."""

from __future__ import annotations

from ai_toolkit.core.diff_parser import DiffHunk

SYSTEM_PROMPT = """You are an expert code reviewer analyzing a pull request diff.

Review the provided diff hunks and identify genuine issues — bugs, security \
problems, and performance concerns. Do not comment on style or formatting \
unless it causes a real bug. Prefer flagging something as a question over \
asserting it confidently if you are not certain it applies to this exact code.

You MUST respond with ONLY valid JSON matching this exact schema, and \
nothing else — no markdown code fences, no preamble, no explanation outside \
the JSON:

{
  "summary": "<one or two sentence overall summary>",
  "comments": [
    {
      "file_path": "<path exactly as shown in the diff>",
      "line": <line number in the NEW version of the file, as an integer>,
      "severity": "<low|medium|high>",
      "comment": "<specific, actionable feedback>"
    }
  ]
}

If you find nothing worth flagging, return an empty comments list — do not \
invent issues to have something to say."""


def build_review_prompt(hunks: list[DiffHunk], *, focus: list[str]) -> str:
    focus_line = f"Focus areas for this review: {', '.join(focus)}.\n\n" if focus else ""

    hunk_sections = []
    for hunk in hunks:
        hunk_sections.append(f"File: {hunk.file_path}\n{hunk.content}")

    diff_text = "\n\n".join(hunk_sections)

    return f"{focus_line}Review the following diff hunks:\n\n{diff_text}"


def build_retry_prompt(original_response: str) -> str:
    return (
        "Your previous response could not be parsed as valid JSON matching "
        "the required schema. Here is what you returned:\n\n"
        f"{original_response}\n\n"
        "Respond again with ONLY the corrected JSON object, matching the "
        "schema exactly. No markdown code fences, no text outside the JSON."
    )
