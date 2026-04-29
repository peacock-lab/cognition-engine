#!/usr/bin/env python3
"""Validation 执行结果回写测试。"""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.validate_data import validate_json_file  # noqa: E402
from engine.analyzer.write_validation_result import (  # noqa: E402
    classify_result,
    ensure_json_only_command,
    parse_result_payload,
    update_validation_record,
)
from engine.analyzer.validation_execution import build_validation_execution  # noqa: E402


def sample_validation_candidate() -> dict:
    return {
        "id": "validation-candidate-github-issue-google-adk-python-4901",
        "framework_id": "adk-2.0.0a3",
        "type": "minimal_sample_candidate",
        "method": "community_signal_analysis",
        "description": "验证 MCP transport 在 403 Forbidden 场景下是否会 hang。",
        "execution_command": "python validation_samples/adk-2.0.0a3/foo/repro_case.py",
        "expected_output": "原始错误在限定时间内透传给调用方，而不是 hang。",
        "actual_output": "最小复现脚手架已生成，待补充真实复现逻辑并执行；当前尚无实际运行证据。",
        "result": "pending",
        "status": "candidate",
        "source_connection_id": "connection-github-issue-google-adk-python-4901",
        "source_thread_url": "https://github.com/google/adk-python/issues/4901",
        "scaffold_status": "ready",
        "scaffold_files": [
            "validation_samples/adk-2.0.0a3/foo/repro_case.py",
            "validation_samples/adk-2.0.0a3/foo/README.md",
            "validation_samples/adk-2.0.0a3/foo/context.json",
        ],
    }


def successful_probe_payload() -> dict:
    return {
        "adk_src": "/tmp/google-adk/src",
        "server_url": "http://127.0.0.1:9999/mcp",
        "connect_timeout_seconds": 5.0,
        "configured_read_timeout_seconds": 3.0,
        "default_streamable_http_read_timeout_seconds": 300.0,
        "initialize_elapsed_seconds": 0.0303,
        "call_elapsed_seconds": 3.0057,
        "exception_type": "McpError",
        "exception_message": (
            "Timed out while waiting for response to ClientRequest. Waited 3.0 seconds."
        ),
        "raw_http_status_visible_to_caller": False,
        "progress_callback_invocations": 0,
        "observed_post_methods": [
            "initialize",
            "notifications/initialized",
            "tools/call",
        ],
        "server_tool_status": 403,
        "reproduced_issue": True,
        "notes": ["caller sees timeout instead of raw 403"],
    }


def failed_probe_payload() -> dict:
    return {
        "reproduced_issue": False,
        "fatal_error_type": "RuntimeError",
        "fatal_error_message": "local environment is not ready",
        "fatal_error_chain": [
            {
                "type": "RuntimeError",
                "message": "local environment is not ready",
            }
        ],
    }


def test_ensure_json_only_command_appends_flag_once() -> None:
    assert ensure_json_only_command("python repro_case.py") == [
        sys.executable,
        "repro_case.py",
        "--json-only",
    ]
    assert ensure_json_only_command("python repro_case.py --json-only") == [
        sys.executable,
        "repro_case.py",
        "--json-only",
    ]


def test_parse_result_payload_keeps_structured_json() -> None:
    payload = parse_result_payload('{"reproduced_issue": true}', "", 0)

    assert payload["reproduced_issue"] is True
    assert payload["process_returncode"] == 0


def test_parse_result_payload_reads_trailing_json_from_stderr() -> None:
    payload = parse_result_payload(
        "",
        "warning line\n{\"reproduced_issue\": false, \"fatal_error_type\": \"PermissionError\"}",
        1,
    )

    assert payload["reproduced_issue"] is False
    assert payload["fatal_error_type"] == "PermissionError"
    assert payload["process_returncode"] == 1


def test_classify_result_treats_reproduced_issue_as_success() -> None:
    assert classify_result(successful_probe_payload(), 0) == "success"
    assert classify_result(successful_probe_payload(), 1) == "failed"
    assert classify_result(failed_probe_payload(), 1) == "failed"


def test_build_validation_execution_keeps_only_formal_entry_fields() -> None:
    validation_execution = build_validation_execution(successful_probe_payload())

    assert validation_execution == {
        "reproduced_issue": True,
        "internal_observation": {
            "observed_node_name": None,
            "output_event_count": None,
        },
        "context_access": {
            "state_delta": {},
        },
        "runner_execution": {
            "process_returncode": None,
            "fatal_error_type": None,
            "fatal_error_message": None,
        },
    }


def test_update_validation_record_promotes_candidate_to_executed_success() -> None:
    record = sample_validation_candidate()
    updated = update_validation_record(
        record,
        successful_probe_payload(),
        "python validation_samples/adk-2.0.0a3/foo/repro_case.py --json-only",
        "2026-04-16T01:00:00Z",
        0,
    )

    assert updated["result"] == "success"
    assert updated["type"] == "minimal_sample"
    assert updated["method"] == "code_execution"
    assert updated["run_timestamp"] == "2026-04-16T01:00:00Z"
    assert "正式收口: success" in updated["actual_output"]
    assert "status" not in updated
    assert "scaffold_status" not in updated
    assert updated["environment"]["command_exit_code"] == 0
    assert updated["duration_seconds"] == 3.036
    assert updated["validation_execution"] == {
        "reproduced_issue": True,
        "internal_observation": {
            "observed_node_name": None,
            "output_event_count": None,
        },
        "context_access": {
            "state_delta": {},
        },
        "runner_execution": {
            "process_returncode": None,
            "fatal_error_type": None,
            "fatal_error_message": None,
        },
    }


def test_update_validation_record_marks_failed_when_probe_does_not_reproduce() -> None:
    record = sample_validation_candidate()
    updated = update_validation_record(
        record,
        failed_probe_payload(),
        "python validation_samples/adk-2.0.0a3/foo/repro_case.py --json-only",
        "2026-04-16T01:00:00Z",
        1,
    )

    assert updated["result"] == "failed"
    assert updated["type"] == "minimal_sample"
    assert "正式收口: failed" in updated["actual_output"]
    assert updated["validation_execution"] == {
        "reproduced_issue": False,
        "internal_observation": {
            "observed_node_name": None,
            "output_event_count": None,
        },
        "context_access": {
            "state_delta": {},
        },
        "runner_execution": {
            "process_returncode": None,
            "fatal_error_type": "RuntimeError",
            "fatal_error_message": "local environment is not ready",
        },
    }


def test_update_validation_record_uses_exception_fallback_for_failure_projection() -> None:
    record = sample_validation_candidate()
    payload = {
        "reproduced_issue": False,
        "exception_type": "TimeoutError",
        "exception_message": "timed out while waiting for response",
        "process_returncode": 1,
    }
    updated = update_validation_record(
        record,
        payload,
        "python validation_samples/adk-2.0.0a3/foo/repro_case.py --json-only",
        "2026-04-16T01:00:00Z",
        1,
    )

    assert updated["validation_execution"]["runner_execution"] == {
        "process_returncode": 1,
        "fatal_error_type": "TimeoutError",
        "fatal_error_message": "timed out while waiting for response",
    }


def test_validate_json_file_accepts_executed_validation_sourced_from_connection() -> None:
    validation_file = (
        project_root
        / "data"
        / "validations"
        / "adk-2.0.0a3"
        / "validation-temp-writeback-test.json"
    )
    try:
        validation_file.parent.mkdir(parents=True, exist_ok=True)
        validation_file.write_text(
            """{
  "id": "validation-candidate-github-issue-google-adk-python-4901",
  "framework_id": "adk-2.0.0a3",
  "type": "minimal_sample",
  "method": "code_execution",
  "description": "验证 MCP transport 在 403 Forbidden 场景下是否会 hang。",
  "execution_command": "python validation_samples/adk-2.0.0a3/foo/repro_case.py --json-only",
  "expected_output": "原始错误在限定时间内透传给调用方，而不是 hang。",
  "actual_output": "执行完成并已写回主对象。",
  "result": "success",
  "run_timestamp": "2026-04-16T01:00:00Z",
  "source_connection_id": "connection-github-issue-google-adk-python-4901"
}
""",
            encoding="utf-8",
        )

        result = validate_json_file(validation_file)
    finally:
        if validation_file.exists():
            validation_file.unlink()

    assert result["checks"]["has_validation_target"] is True
