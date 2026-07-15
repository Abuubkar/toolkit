import json

import pytest

from ai_toolkit.core.pr_context import resolve_pr_number


def test_explicit_number_takes_priority(monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_PATH", "/does/not/matter")

    assert resolve_pr_number(explicit=99) == 99


def test_reads_pull_request_number_from_event_payload(tmp_path, monkeypatch):
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps({"pull_request": {"number": 42}}))
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file))

    assert resolve_pr_number() == 42


def test_raises_when_no_explicit_and_no_event_path(monkeypatch):
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)

    with pytest.raises(RuntimeError, match="GITHUB_EVENT_PATH"):
        resolve_pr_number()


def test_raises_when_event_payload_has_no_pr_number(tmp_path, monkeypatch):
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps({"some_other_event": True}))
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file))

    with pytest.raises(RuntimeError, match="Could not find a PR number"):
        resolve_pr_number()
