#!/usr/bin/env python3
"""Validation 脚手架生成测试。"""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.generate_validation_skeleton import (  # noqa: E402
    build_context_payload,
    build_repro_script,
    is_pending_candidate,
    planned_scaffold_files,
    update_validation_record,
)


def sample_validation_candidate() -> dict:
    return {
        "id": "validation-candidate-github-issue-google-adk-python-4901",
        "framework_id": "adk-2.0.0a3",
        "type": "external_signal_candidate",
        "method": "community_signal_analysis",
        "description": "验证 MCP transport 在 403 Forbidden 场景下是否会 hang。",
        "expected_output": "原始错误在限定时间内透传给调用方，而不是 hang。",
        "actual_output": "尚未执行。",
        "result": "pending",
        "status": "candidate",
        "source_connection_id": "connection-github-issue-google-adk-python-4901",
        "source_thread_url": "https://github.com/google/adk-python/issues/4901",
        "candidate_score": 0.96,
        "signal_summary": {
            "problem_hits": ["hang", "timeout", "forbidden"],
            "repro_hits": ["when", "callback", "caller"],
            "component_hits": ["mcp", "transport", "http"],
            "http_statuses": ["403"],
            "durations": ["5 minutes"],
        },
        "suggested_checks": [
            "原始异常是否在限定时延内透传到调用方",
            "错误回调是否被触发且没有被后台协程吞掉",
        ],
    }


def test_is_pending_candidate_only_accepts_pending_candidate() -> None:
    record = sample_validation_candidate()

    assert is_pending_candidate(record) is True

    record["status"] = "success"
    assert is_pending_candidate(record) is False


def test_planned_scaffold_files_are_stable() -> None:
    files = planned_scaffold_files(
        sample_validation_candidate(),
        project_root / "validation_samples",
    )

    assert str(files["script"]).endswith(
        "validation_samples/adk-2.0.0a3/validation-candidate-github-issue-google-adk-python-4901/repro_case.py"
    )
    assert files["readme"].name == "README.md"
    assert files["context"].name == "context.json"


def test_build_context_payload_keeps_signal_summary() -> None:
    payload = build_context_payload(sample_validation_candidate())

    assert payload["validation_id"] == "validation-candidate-github-issue-google-adk-python-4901"
    assert payload["signal_summary"]["http_statuses"] == ["403"]
    assert len(payload["suggested_checks"]) == 2


def test_build_repro_script_contains_validation_metadata() -> None:
    script = build_repro_script(
        sample_validation_candidate(),
        "validation_samples/adk-2.0.0a3/foo/context.json",
        "validation_samples/adk-2.0.0a3/foo/README.md",
    )

    assert "Validation Scaffold" in script
    assert "SOURCE_THREAD_URL" in script
    assert "Status: scaffold_ready" in script


def test_update_validation_record_adds_code_sample_without_changing_result() -> None:
    record = sample_validation_candidate()
    base_dir = project_root / "validation_samples" / record["framework_id"] / record["id"]

    update_validation_record(
        record,
        base_dir / "repro_case.py",
        base_dir / "README.md",
        base_dir / "context.json",
    )

    assert record["result"] == "pending"
    assert record["type"] == "minimal_sample_candidate"
    assert record["scaffold_status"] == "ready"
    assert record["code_sample"].endswith("/repro_case.py")
    assert record["execution_command"].startswith("python validation_samples/")
    assert len(record["scaffold_files"]) == 3
