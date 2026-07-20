from __future__ import annotations

from ai_toolkit.core.diff_parser import DiffHunk

SYSTEM_PROMPT = """You are identifying missing test coverage in a pull request diff.

Look for: new functions/methods with no accompanying test changes, changed \
branching logic (conditionals, error handling) that isn't covered, edge \
cases (empty input, negative numbers, None/null, boundary values) that \
aren't exercised, and changed behavior that existing tests wouldn't catch.

Respond with ONLY valid JSON matching this exact schema, and nothing else \
— no markdown code fences, no preamble, and DO NOT write any test code, \
only prose descriptions of what should be tested:

{
  "summary": "<one or two sentence overview of test coverage gaps>",
  "recommendations": [
    {
      "file_path": "<path exactly as shown in the diff>",
      "description": "<specific, actionable description of what to test and why \
— e.g. 'Test that calculate_total raises ValueError for a negative total, \
not just the happy path'>",
      "priority": "<low|medium|high>"
    }
  ]
}

If the diff already has adequate test coverage, or contains no testable \
logic (e.g. only docs, config, or formatting changes), return an empty \
recommendations list — do not invent gaps to have something to say."""


def build_test_recommendation_prompt(hunks: list[DiffHunk]) -> str:
    hunk_sections = [f"File: {hunk.file_path}\n{hunk.content}" for hunk in hunks]
    diff_text = "\n\n".join(hunk_sections)
    return f"Identify test coverage gaps in the following diff:\n\n{diff_text}"
