"""Thin GitHub REST API client for PR metadata, diffs, and comments."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from ai_toolkit.shared.errors import GitHubAPIError

DEFAULT_API_BASE = "https://api.github.com"


@dataclass(frozen=True)
class PullRequestInfo:
    number: int
    title: str
    body: str
    base_sha: str
    head_sha: str
    state: str


@dataclass(frozen=True)
class CommitSummary:
    sha: str
    message: str
    author: str


class GitHubClient:
    def __init__(
        self,
        token: str,
        repo: str,
        *,
        base_url: str = DEFAULT_API_BASE,
        client: httpx.Client | None = None,
    ):
        """repo is 'owner/name', e.g. 'abubakar/markpoint'."""
        self.repo = repo
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=30.0)
        self._client.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def get_pull_request(self, pr_number: int) -> PullRequestInfo:
        url = f"{self._base_url}/repos/{self.repo}/pulls/{pr_number}"
        response = self._client.get(url)
        self._raise_for_status(response, url)
        data = response.json()
        return PullRequestInfo(
            number=data["number"],
            title=data["title"],
            body=data.get("body") or "",
            base_sha=data["base"]["sha"],
            head_sha=data["head"]["sha"],
            state=data["state"],
        )

    def get_pull_request_diff(self, pr_number: int) -> str:
        url = f"{self._base_url}/repos/{self.repo}/pulls/{pr_number}"
        response = self._client.get(url, headers={"Accept": "application/vnd.github.v3.diff"})
        self._raise_for_status(response, url)
        return response.text

    def post_review_comment(
        self,
        pr_number: int,
        *,
        commit_sha: str,
        file_path: str,
        line: int,
        body: str,
    ) -> dict:
        """`line` must already be part of the diff — GitHub rejects
        comments on lines outside the diff context.
        """
        url = f"{self._base_url}/repos/{self.repo}/pulls/{pr_number}/comments"
        payload = {
            "body": body,
            "commit_id": commit_sha,
            "path": file_path,
            "line": line,
            "side": "RIGHT",
        }
        response = self._client.post(url, json=payload)
        self._raise_for_status(response, url)
        return response.json()

    def post_issue_comment(self, pr_number: int, body: str) -> dict:
        """Non-line-anchored comment; used as fallback and for run summaries."""
        url = f"{self._base_url}/repos/{self.repo}/issues/{pr_number}/comments"
        response = self._client.post(url, json={"body": body})
        self._raise_for_status(response, url)
        return response.json()

    def update_pull_request_body(self, pr_number: int, body: str) -> dict:
        url = f"{self._base_url}/repos/{self.repo}/pulls/{pr_number}"
        response = self._client.patch(url, json={"body": body})
        self._raise_for_status(response, url)
        return response.json()

    def compare_commits(self, base: str, head: str) -> list[CommitSummary]:
        url = f"{self._base_url}/repos/{self.repo}/compare/{base}...{head}"
        response = self._client.get(url)
        self._raise_for_status(response, url)
        data = response.json()
        return [
            CommitSummary(
                sha=c["sha"][:7],
                message=c["commit"]["message"],
                author=c["commit"]["author"]["name"],
            )
            for c in data.get("commits", [])
        ]

    @staticmethod
    def _raise_for_status(response: httpx.Response, url: str) -> None:
        if response.status_code >= 400:
            try:
                message = response.json().get("message", response.text)
            except Exception:
                message = response.text
            raise GitHubAPIError(response.status_code, message, url=url)

    def close(self) -> None:
        self._client.close()
