#!/usr/bin/env python3
"""GitHub 线程到 insight 推荐映射测试。"""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.map_github_threads_to_insights import (  # noqa: E402
    recommend_insights_for_connection,
    upsert_recommendations,
)


def make_insight(insight_id: str, title: str, description: str, tags: list[str]) -> dict:
    return {
        "record": {
            "id": insight_id,
            "title": title,
            "description": description,
            "tags": tags,
            "category": "architectural_pattern",
            "type": "architecture",
            "evidence": [
                {
                    "quote": description,
                }
            ],
        },
        "terms": {
            "title_terms": set(),
            "description_terms": set(),
            "tag_terms": set(),
            "category_terms": set(),
            "evidence_terms": set(),
            "focus_terms": set(),
            "all_terms": set(),
        },
    }


def build_indexed_insight(insight_id: str, title: str, description: str, tags: list[str]) -> dict:
    from engine.analyzer.map_github_threads_to_insights import collect_insight_terms

    insight = make_insight(insight_id, title, description, tags)
    insight["terms"] = collect_insight_terms(insight["record"])
    return insight


def sample_connection_record() -> dict:
    return {
        "id": "connection-github-issue-demo-100",
        "framework_id": "adk-2.0.0a3",
        "type": "github_issue_thread",
        "title": "GitHub Issue #100: Runner fails to append event after InvocationContext creation",
        "content_summary": "Runner, session and Event flow break when append_event is skipped.",
        "metadata": {
            "tags": ["github", "issue-thread"],
            "thread": {
                "labels": ["runner", "event"],
            },
        },
        "thread_snapshot": {
            "body_excerpt": "Runner creates InvocationContext and session, but the Event is never appended back.",
            "comments": [
                {
                    "body_excerpt": "append_event and runner callback look disconnected.",
                }
            ],
            "reviews": [],
        },
        "connections": [],
    }


def unrelated_connection_record() -> dict:
    return {
        "id": "connection-github-issue-demo-4901",
        "framework_id": "adk-2.0.0a3",
        "type": "github_issue_thread",
        "title": "GitHub Issue #4901: MCP transport hangs on 403 for five minutes",
        "content_summary": "MCP HTTP 403 leads to timeout and callback never fires.",
        "metadata": {
            "tags": ["github", "issue-thread"],
            "thread": {
                "labels": ["mcp", "timeout"],
            },
        },
        "thread_snapshot": {
            "body_excerpt": "Transport errors are swallowed in the background TaskGroup and the caller blocks.",
            "comments": [],
            "reviews": [],
        },
        "connections": [],
    }


def test_recommend_insights_prefers_runner_related_match() -> None:
    insights = [
        build_indexed_insight(
            "insight-adk-runner-centrality",
            "Runner is the request coordinator",
            "Runner owns session, InvocationContext, event consumption and append_event flow.",
            ["runner", "session", "event", "invocationcontext"],
        ),
        build_indexed_insight(
            "insight-adk-entrypoint-layering",
            "Entrypoints are layered",
            "run, run_sse and live differ mainly in protocol shape.",
            ["run_sse", "live", "entrypoint"],
        ),
    ]

    recommendations = recommend_insights_for_connection(sample_connection_record(), insights, min_score=0.42, max_results=3)

    assert recommendations
    assert recommendations[0]["insight_id"] == "insight-adk-runner-centrality"
    assert recommendations[0]["score"] >= 0.42
    assert "runner" in recommendations[0]["matched_terms"]


def test_recommend_insights_returns_empty_for_unrelated_thread() -> None:
    insights = [
        build_indexed_insight(
            "insight-adk-state-context-boundary",
            "State boundary across Session and Context",
            "Session.state and Context define a stable boundary.",
            ["session", "context", "boundary"],
        ),
    ]

    recommendations = recommend_insights_for_connection(
        unrelated_connection_record(),
        insights,
        min_score=0.42,
        max_results=3,
    )

    assert recommendations == []


def test_upsert_recommendations_preserves_existing_manual_links() -> None:
    record = sample_connection_record()
    record["connections"] = [
        {
            "insight_id": "insight-adk-runner-centrality",
            "connection_strength": 0.95,
            "notes": "人工确认：核心运行主链直接支撑该 insight。",
        }
    ]

    applied = upsert_recommendations(
        record,
        [
            {
                "insight_id": "insight-adk-runner-centrality",
                "score": 0.81,
                "matched_terms": ["runner", "event"],
                "notes": "自动推荐：命中关键词 runner, event",
            },
            {
                "insight_id": "insight-adk-event-convergence",
                "score": 0.74,
                "matched_terms": ["event", "append_event"],
                "notes": "自动推荐：命中关键词 event, append_event",
            },
        ],
    )

    assert applied == 1
    assert len(record["connections"]) == 2
    assert record["connections"][0]["connection_strength"] == 0.95
    assert record["connections"][1]["type"] == "insight_candidate"
    assert record["connections"][1]["insight_id"] == "insight-adk-event-convergence"
