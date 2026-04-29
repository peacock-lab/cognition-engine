#!/usr/bin/env python3
"""GitHub 连接器测试。"""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from connectors.import_github_repository import build_connection_record, parse_repo_ref


def sample_repo_payload() -> dict:
    return {
        "full_name": "google/adk-python",
        "name": "adk-python",
        "html_url": "https://github.com/google/adk-python",
        "description": "Agent Development Kit for building multi-agent systems.",
        "language": "Python",
        "topics": ["agents", "multi-agent"],
        "stargazers_count": 4200,
        "forks_count": 320,
        "subscribers_count": 65,
        "open_issues_count": 18,
        "default_branch": "main",
        "homepage": "https://example.com/adk",
        "private": False,
        "archived": False,
        "disabled": False,
        "updated_at": "2026-04-16T00:00:00Z",
        "pushed_at": "2026-04-16T01:00:00Z",
        "created_at": "2025-01-01T00:00:00Z",
        "owner": {"login": "google"},
        "license": {"spdx_id": "Apache-2.0"},
    }


def test_parse_repo_ref_accepts_short_name() -> None:
    owner, repo, url = parse_repo_ref("google/adk-python")
    assert owner == "google"
    assert repo == "adk-python"
    assert url == "https://github.com/google/adk-python"


def test_parse_repo_ref_accepts_full_url() -> None:
    owner, repo, url = parse_repo_ref("https://github.com/google/adk-python/")
    assert owner == "google"
    assert repo == "adk-python"
    assert url == "https://github.com/google/adk-python"


def test_build_connection_record_contains_expected_snapshot() -> None:
    record = build_connection_record(
        repo_payload=sample_repo_payload(),
        issues=[
            {
                "number": 12,
                "title": "How does session state survive resume?",
                "state": "open",
                "html_url": "https://github.com/google/adk-python/issues/12",
                "created_at": "2026-04-15T00:00:00Z",
                "updated_at": "2026-04-16T00:00:00Z",
                "user": {"login": "alice"},
                "labels": [{"name": "question"}],
                "comments": 3,
                "body": "Trying to understand session persistence.",
            }
        ],
        pull_requests=[
            {
                "number": 34,
                "title": "Refine event stream handling",
                "state": "open",
                "html_url": "https://github.com/google/adk-python/pull/34",
                "created_at": "2026-04-15T00:00:00Z",
                "updated_at": "2026-04-16T00:00:00Z",
                "user": {"login": "bob"},
                "labels": [{"name": "enhancement"}],
                "comments": 1,
                "draft": False,
                "body": "Improves event stream consistency.",
            }
        ],
        releases=[
            {
                "name": "v2.0.0",
                "tag_name": "v2.0.0",
                "html_url": "https://github.com/google/adk-python/releases/tag/v2.0.0",
                "published_at": "2026-04-10T00:00:00Z",
                "draft": False,
                "prerelease": False,
                "body": "Stable release.",
            }
        ],
        framework_id="adk-2.0.0a3",
        channel="github_repository_snapshot",
        tags=["adk", "daily-fuel"],
    )

    assert record["id"] == "connection-github-repo-google-adk-python"
    assert record["framework_id"] == "adk-2.0.0a3"
    assert record["type"] == "github_repository"
    assert record["source"] == "https://github.com/google/adk-python"
    assert record["metadata"]["repository"]["topics"] == ["adk", "agents", "daily-fuel", "multi-agent", "python"]
    assert record["metadata"]["stats"]["issues_collected"] == 1
    assert record["metadata"]["stats"]["pull_requests_collected"] == 1
    assert record["metadata"]["stats"]["releases_collected"] == 1
    assert len(record["repository_snapshot"]["open_issues"]) == 1
    assert len(record["repository_snapshot"]["recent_pull_requests"]) == 1
    assert len(record["repository_snapshot"]["recent_releases"]) == 1
    assert "Stars 4200" in record["content_summary"]
