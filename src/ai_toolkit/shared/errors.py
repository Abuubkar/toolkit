"""Shared exception types used across providers and core modules."""

from __future__ import annotations


class GitHubAPIError(Exception):
    """Raised when the GitHub API returns an error response."""

    def __init__(self, status_code: int, message: str, *, url: str | None = None):
        self.status_code = status_code
        self.message = message
        self.url = url
        super().__init__(f"GitHub API error {status_code}: {message}" + (f" ({url})" if url else ""))


class LLMProviderError(Exception):
    """Raised when an LLM provider's API returns an error response, or
    when its response can't be parsed into the expected shape.
    """

    def __init__(self, status_code: int | None, message: str, *, provider: str | None = None):
        self.status_code = status_code
        self.message = message
        self.provider = provider
        prefix = f"{provider} error" if provider else "LLM provider error"
        status = f" {status_code}" if status_code is not None else ""
        super().__init__(f"{prefix}{status}: {message}")
