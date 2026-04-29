#!/usr/bin/env python3
"""ADK 单 agent 结构化输出正式入口测试。"""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.run_adk_single_agent_structured_output import (  # noqa: E402
    CAPABILITY_ID,
    ENTRY_ID,
    EXPECTED_OUTPUT_JSON,
    EXPECTED_STRUCTURED_OUTPUT,
    MATRIX_CELL_ID,
    OUTPUT_KEY,
    OUTPUTS_DIR,
    PROBE_REFERENCE,
    SELECTED_RUNTIME_PATH,
    build_failure_payload,
    build_success_payload,
    resolve_output_path,
)


def test_resolve_output_path_defaults_to_structured_output_directory() -> None:
    output_path = resolve_output_path(None)

    assert output_path.parent == OUTPUTS_DIR
    assert output_path.name.startswith(f"{ENTRY_ID}-")
    assert output_path.suffix == ".json"


def test_resolve_output_path_accepts_project_relative_path() -> None:
    output_path = resolve_output_path("outputs/structured_output/custom-run.json")

    assert output_path == project_root / "outputs" / "structured_output" / "custom-run.json"


def test_build_success_payload_marks_formal_entry_boundary() -> None:
    output_path = project_root / "outputs" / "structured_output" / "formal-entry.json"

    payload = build_success_payload(
        started_at="2026-04-17T02:00:00Z",
        completed_at="2026-04-17T02:00:01Z",
        duration_seconds=1.23456,
        input_text="Write a tiny story as structured output.",
        output_path=output_path,
        adk_module_path="/tmp/google-adk/src/google/adk/__init__.py",
        event_records=[
            {
                "author": "single_agent_structured_output_run",
                "node_path": "single_agent_structured_output_run@1",
                "node_name": "single_agent_structured_output_run",
                "output": None,
                "role": "model",
                "text_parts": [EXPECTED_OUTPUT_JSON],
                "has_state_delta": True,
                "state_delta": {OUTPUT_KEY: EXPECTED_STRUCTURED_OUTPUT},
            }
        ],
        request_records=[
            {
                "content_count": 1,
                "has_response_schema": True,
                "response_schema_type": "StoryOutput",
                "response_mime_type": "application/json",
            }
        ],
        session_state={OUTPUT_KEY: EXPECTED_STRUCTURED_OUTPUT},
    )

    assert payload["result"] == "success"
    assert payload["entry_type"] == "formal_structured_output_run"
    assert payload["capability_id"] == CAPABILITY_ID
    assert payload["matrix_cell_id"] == MATRIX_CELL_ID
    assert payload["probe_reference"] == PROBE_REFERENCE
    assert payload["selected_runtime_path"] == SELECTED_RUNTIME_PATH
    assert payload["structured_output_payload"] == EXPECTED_STRUCTURED_OUTPUT
    assert payload["response_schema_request_count"] == 1
    assert payload["state_delta_write_observed"] is True
    assert payload["session_state_write_observed"] is True
    assert payload["internal_observation"] == {
        "observed_node_names": ["single_agent_structured_output_run"],
        "semantic_observation": {
            "entered_semantics": ["structured_output_constraint"],
            "observed_results": [],
        },
        "event_records": [
            {
                "author": "single_agent_structured_output_run",
                "role": "model",
                "output": None,
                "node_name": "single_agent_structured_output_run",
                "has_state_delta": True,
                "state_delta": {OUTPUT_KEY: EXPECTED_STRUCTURED_OUTPUT},
            }
        ],
    }
    assert payload["context_access"] == {
        "state_delta": {OUTPUT_KEY: EXPECTED_STRUCTURED_OUTPUT},
        "session_state": {OUTPUT_KEY: EXPECTED_STRUCTURED_OUTPUT},
    }
    assert payload["runner_execution"] == {
        "Runner": "Runner",
        "request_acceptance": True,
        "event_consumption": True,
        "append_progression": True,
        "response_return": True,
    }
    assert payload["state_delta"] == {OUTPUT_KEY: EXPECTED_STRUCTURED_OUTPUT}
    assert payload["session_state"] == {OUTPUT_KEY: EXPECTED_STRUCTURED_OUTPUT}
    assert payload["output_file"] == "outputs/structured_output/formal-entry.json"
    assert payload["duration_seconds"] == 1.2346
    assert "CA-01 / M-01" in payload["boundary_judgement"]


def test_build_failure_payload_keeps_formal_entry_warning() -> None:
    output_path = project_root / "outputs" / "structured_output" / "failed-entry.json"

    payload = build_failure_payload(
        started_at="2026-04-17T02:00:00Z",
        completed_at="2026-04-17T02:00:01Z",
        duration_seconds=0.25,
        input_text="Write a tiny story as structured output.",
        output_path=output_path,
        exc=RuntimeError("response_schema is missing"),
    )

    assert payload["result"] == "failed"
    assert payload["capability_id"] == CAPABILITY_ID
    assert payload["matrix_cell_id"] == MATRIX_CELL_ID
    assert payload["probe_reference"] == PROBE_REFERENCE
    assert payload["selected_runtime_path"] == SELECTED_RUNTIME_PATH
    assert payload["output_file"] == "outputs/structured_output/failed-entry.json"
    assert payload["error_type"] == "RuntimeError"
    assert "正式结构化输出接入" in payload["boundary_judgement"]
