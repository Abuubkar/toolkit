import httpx
import pytest

from ai_toolkit.core.github_client import GitHubClient
from ai_toolkit.shared.errors import GitHubAPIError

PR_JSON = {
    "number": 42,
    "title": "Add validation to calculate_total",
    "body": "Fixes negative totals bug.",
    "state": "open",
    "base": {"sha": "base123"},
    "head": {"sha": "head456"},
}

SAMPLE_DIFF = (
    "diff --git a/src/utils.py b/src/utils.py\n"
    "index 111..222 100644\n--- a/src/utils.py\n+++ b/src/utils.py\n"
    "@@ -1 +1 @@\n-old\n+new\n"
)


def _client_with_transport(handler) -> GitHubClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    return GitHubClient(token="fake-token", repo="abubakar/markpoint", client=http_client)


def test_get_pull_request_returns_parsed_info():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/abubakar/markpoint/pulls/42"
        assert request.headers["Authorization"] == "Bearer fake-token"
        return httpx.Response(200, json=PR_JSON)

    client = _client_with_transport(handler)
    pr = client.get_pull_request(42)

    assert pr.number == 42
    assert pr.title == "Add validation to calculate_total"
    assert pr.base_sha == "base123"
    assert pr.head_sha == "head456"
    assert pr.state == "open"


def test_get_pull_request_diff_requests_diff_media_type():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Accept"] == "application/vnd.github.v3.diff"
        return httpx.Response(200, text=SAMPLE_DIFF)

    client = _client_with_transport(handler)
    diff = client.get_pull_request_diff(42)

    assert diff == SAMPLE_DIFF


def test_get_pull_request_raises_on_404():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    client = _client_with_transport(handler)

    with pytest.raises(GitHubAPIError) as exc_info:
        client.get_pull_request(999)

    assert exc_info.value.status_code == 404
    assert "Not Found" in exc_info.value.message


def test_post_review_comment_sends_correct_payload():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.content
        return httpx.Response(201, json={"id": 123, "body": "Looks good"})

    client = _client_with_transport(handler)
    result = client.post_review_comment(
        42, commit_sha="head456", file_path="src/utils.py", line=15, body="Looks good"
    )

    assert result["id"] == 123
    assert "/pulls/42/comments" in captured["url"]
    import json

    payload = json.loads(captured["body"])
    assert payload["commit_id"] == "head456"
    assert payload["path"] == "src/utils.py"
    assert payload["line"] == 15
    assert payload["side"] == "RIGHT"


def test_post_review_comment_raises_on_rate_limit():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "API rate limit exceeded"})

    client = _client_with_transport(handler)

    with pytest.raises(GitHubAPIError) as exc_info:
        client.post_review_comment(
            42, commit_sha="head456", file_path="src/utils.py", line=15, body="x"
        )

    assert exc_info.value.status_code == 403


def test_post_issue_comment_hits_issues_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/issues/42/comments" in str(request.url)
        return httpx.Response(201, json={"id": 999, "body": "Run summary"})

    client = _client_with_transport(handler)
    result = client.post_issue_comment(42, "Run summary")

    assert result["id"] == 999


def test_update_pull_request_body_sends_patch_with_body():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["body"] = request.content
        return httpx.Response(200, json={"number": 42, "body": "new description"})

    client = _client_with_transport(handler)
    result = client.update_pull_request_body(42, "new description")

    assert captured["method"] == "PATCH"
    assert "/pulls/42" in captured["url"]
    import json

    assert json.loads(captured["body"]) == {"body": "new description"}
    assert result["body"] == "new description"
