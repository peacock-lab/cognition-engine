#!/usr/bin/env python3
"""GitHub 线程连接器测试。"""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from connectors.import_github_thread import build_connection_record, parse_thread_ref


def sample_issue_payload() -> dict:
    return {
        "title": "ADK agent hangs for ~5 minutes when MCP server returns non-2xx HTTP response",
        "body": "The agent hangs when MCP returns 403. Need better timeout and error propagation.",
        "state": "open",
        "html_url": "https://github.com/google/adk-python/issues/4901",
        "created_at": "2026-03-19T18:13:23Z",
        "updated_at": "2026-04-15T16:59:56Z",
        "closed_at": None,
        "comments": 3,
        "labels": [{"name": "tools"}, {"name": "mcp"}],
        "user": {"login": "JamesDuncanNz"},
    }


def sample_pr_payload() -> dict:
    return {
        "title": "fix(auth): handle missing client-credentials scopes safely",
        "body": "Improves error handling for auth scopes.",
        "state": "open",
        "html_url": "https://github.com/google/adk-python/pull/5348",
        "created_at": "2026-04-15T16:24:25Z",
        "updated_at": "2026-04-15T16:41:45Z",
        "closed_at": None,
        "comments": 2,
        "labels": [{"name": "core"}],
        "user": {"login": "sqsge"},
        "pull_request": {"url": "https://api.github.com/repos/google/adk-python/pulls/5348"},
        "pull_request_detail": {
            "draft": False,
            "merged": False,
            "base": {"ref": "main"},
            "head": {"ref": "auth-fix"},
            "mergeable_state": "clean",
            "changed_files": 4,
        },
    }


def test_parse_thread_ref_accepts_issue_url() -> None:
    owner, repo, number, kind = parse_thread_ref(
        "https://github.com/google/adk-python/issues/4901",
        repo_ref=None,
        number=None,
        kind="auto",
    )
    assert owner == "google"
    assert repo == "adk-python"
    assert number == 4901
    assert kind == "issue"


def test_parse_thread_ref_accepts_repo_hash_number() -> None:
    owner, repo, number, kind = parse_thread_ref(
        "google/adk-python#4901",
        repo_ref=None,
        number=None,
        kind="issue",
    )
    assert owner == "google"
    assert repo == "adk-python"
    assert number == 4901
    assert kind == "issue"


def test_build_connection_record_for_issue_links_repository_context() -> None:
    record = build_connection_record(
        owner="google",
        repo="adk-python",
        number=4901,
        thread_payload=sample_issue_payload(),
        comments=[
            {
                "id": 1,
                "user": {"login": "alice"},
                "created_at": "2026-04-15T17:00:00Z",
                "updated_at": "2026-04-15T17:00:00Z",
                "html_url": "https://github.com/google/adk-python/issues/4901#issuecomment-1",
                "body": "I can reproduce this when proxy returns 403.",
            }
        ],
        reviews=[],
        final_kind="issue",
        framework_id="adk-2.0.0a3",
        channel="github_thread_snapshot",
        tags=["github", "issue-thread"],
    )

    assert record["id"] == "connection-github-issue-google-adk-python-4901"
    assert record["type"] == "github_issue_thread"
    assert record["connections"][0]["connection_id"] == "connection-github-repo-google-adk-python"
    assert record["metadata"]["thread"]["kind"] == "issue"
    assert record["metadata"]["thread"]["comment_count"] == 1
    assert len(record["thread_snapshot"]["comments"]) == 1


def test_build_connection_record_for_pr_contains_review_context() -> None:
    record = build_connection_record(
        owner="google",
        repo="adk-python",
        number=5348,
        thread_payload=sample_pr_payload(),
        comments=[],
        reviews=[
            {
                "id": 10,
                "user": {"login": "reviewer"},
                "state": "APPROVED",
                "submitted_at": "2026-04-15T18:00:00Z",
                "commit_id": "abcdef",
                "body": "Looks good to me.",
            }
        ],
        final_kind="pr",
        framework_id="adk-2.0.0a3",
        channel="github_thread_snapshot",
        tags=["github", "pr-thread"],
    )

    assert record["id"] == "connection-github-pull-request-google-adk-python-5348"
    assert record["type"] == "github_pull_request_thread"
    assert record["metadata"]["thread"]["review_count"] == 1
    assert record["thread_snapshot"]["merge_context"]["base_ref"] == "main"
    assert len(record["thread_snapshot"]["reviews"]) == 1
