"""Shared exception types used across providers and core modules."""

from __future__ import annotations


class GitHubAPIError(Exception):
    """Raised when the GitHub API returns an error response."""

    def __init__(self, status_code: int, message: str, *, url: str | None = None):
        self.status_code = status_code
        self.message = message
        self.url = url
        super().__init__(f"GitHub API error {status_code}: {message}" + (f" ({url})" if url else ""))
