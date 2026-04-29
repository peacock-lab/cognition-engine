#!/usr/bin/env python3
"""GitHub 线程到 validation 候选生成测试。"""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.map_github_threads_to_validations import (  # noqa: E402
    build_candidate_payload,
    collect_signal_matches,
    collect_thread_context,
    qualifies_as_validation_candidate,
    upsert_validation_link,
)


def sample_bug_thread() -> dict:
    return {
        "id": "connection-github-issue-google-adk-python-4901",
        "framework_id": "adk-2.0.0a3",
        "type": "github_issue_thread",
        "source": "https://github.com/google/adk-python/issues/4901",
        "title": "GitHub Issue #4901: ADK agent hangs for ~5 minutes when MCP server returns non-2xx HTTP response",
        "content_summary": "MCP server returns 403 Forbidden, caller hangs, callback never fires and request times out.",
        "connections": [],
        "metadata": {
            "repository": {
                "full_name": "google/adk-python",
                "owner": "google",
                "name": "adk-python",
            },
            "thread": {
                "kind": "issue",
                "number": 4901,
                "labels": ["tools", "mcp"],
            },
        },
        "thread_snapshot": {
            "body_excerpt": (
                "When an MCP server returns 403 Forbidden, the background TaskGroup crashes but "
                "send_request never raises, the caller remains blocked and after 5 minutes a timeout appears."
            ),
            "comments": [
                {
                    "body_excerpt": (
                        "This is not just a transport bug, callback never fires and retries hide the real HTTP 403."
                    )
                }
            ],
            "reviews": [],
        },
    }


def sample_question_thread() -> dict:
    return {
        "id": "connection-github-issue-google-adk-python-4940",
        "framework_id": "adk-2.0.0a3",
        "type": "github_issue_thread",
        "source": "https://github.com/google/adk-python/issues/4940",
        "title": "GitHub Issue #4940: Switch models with same session context",
        "content_summary": "Question about using live audio and text with the same session context.",
        "connections": [],
        "metadata": {
            "repository": {
                "full_name": "google/adk-python",
                "owner": "google",
                "name": "adk-python",
            },
            "thread": {
                "kind": "issue",
                "number": 4940,
                "labels": ["question", "live"],
            },
        },
        "thread_snapshot": {
            "body_excerpt": "How can I reuse the same session context when switching from text to audio?",
            "comments": [],
            "reviews": [],
        },
    }


def test_bug_thread_qualifies_as_validation_candidate() -> None:
    context = collect_thread_context(sample_bug_thread())
    signal_matches = collect_signal_matches(context)

    assert qualifies_as_validation_candidate(signal_matches, min_score=0.52) is True
    assert "mcp" in signal_matches["component_hits"]
    assert "403" in signal_matches["status_hits"]
    assert any(item.startswith("hang") for item in signal_matches["problem_hits"])


def test_question_thread_does_not_qualify() -> None:
    context = collect_thread_context(sample_question_thread())
    signal_matches = collect_signal_matches(context)

    assert qualifies_as_validation_candidate(signal_matches, min_score=0.52) is False


def test_build_candidate_payload_produces_pending_validation() -> None:
    record = sample_bug_thread()
    record["connections"] = [
        {
            "type": "insight_candidate",
            "insight_id": "insight-adk-entrypoint-layering",
            "connection_strength": 0.66,
            "notes": "自动推荐",
        }
    ]
    signal_matches = collect_signal_matches(collect_thread_context(record))
    payload = build_candidate_payload(
        connection_record=record,
        source_path=project_root / "data" / "connections" / "github" / "connection-github-issue-google-adk-python-4901.json",
        signal_matches=signal_matches,
    )

    assert payload["id"] == "validation-candidate-github-issue-google-adk-python-4901"
    assert payload["result"] == "pending"
    assert payload["method"] == "community_signal_analysis"
    assert payload["source_connection_id"] == "connection-github-issue-google-adk-python-4901"
    assert payload["insight_id"] == "insight-adk-entrypoint-layering"


def test_upsert_validation_link_is_idempotent() -> None:
    record = sample_bug_thread()

    first = upsert_validation_link(record, "validation-candidate-github-issue-google-adk-python-4901", 0.82)
    second = upsert_validation_link(record, "validation-candidate-github-issue-google-adk-python-4901", 0.82)

    assert first == 1
    assert second == 1
    assert len(record["connections"]) == 1
    assert record["connections"][0]["type"] == "validation_candidate"
