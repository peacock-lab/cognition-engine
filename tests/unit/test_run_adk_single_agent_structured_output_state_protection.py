from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.run_adk_single_agent_structured_output_state_protection import (  # noqa: E402
    CAPABILITY_ID,
    ENTRY_ID,
    FAILURE_RECOGNITION_REFERENCE,
    OUTPUTS_DIR,
    OUTPUT_KEY,
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


def test_build_success_payload_marks_state_channels_as_protected() -> None:
    output_path = project_root / "outputs" / "structured_output" / "formal-state-protection.json"

    payload = build_success_payload(
        started_at="2026-04-17T03:00:00Z",
        completed_at="2026-04-17T03:00:01Z",
        duration_seconds=1.23456,
        input_text="Write a tiny story as structured output.",
        output_path=output_path,
        adk_module_path="/tmp/google-adk/src/google/adk/__init__.py",
        error_type="ValidationError",
        error_message="1 validation error for StoryOutput",
        event_records=[
            {
                "author": "single_agent_structured_output_state_protection_run",
                "node_path": "single_agent_structured_output_state_protection_run@1",
                "node_name": "single_agent_structured_output_state_protection_run",
                "output": None,
                "role": None,
                "text_parts": ['{"title": "Broken Story"}'],
                "has_state_delta": False,
                "state_delta": {},
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
        session_state={},
    )

    assert payload["result"] == "success"
    assert payload["entry_type"] == "formal_structured_output_state_protection_run"
    assert payload["capability_id"] == CAPABILITY_ID
    assert payload["probe_reference"] == PROBE_REFERENCE
    assert payload["failure_recognition_reference"] == FAILURE_RECOGNITION_REFERENCE
    assert payload["selected_runtime_path"] == SELECTED_RUNTIME_PATH
    assert payload["response_schema_request_count"] == 1
    assert payload["formal_state_protection_established"] is True
    assert payload["state_delta_write_observed"] is False
    assert payload["session_state_write_observed"] is False
    assert payload["protected_state_channels"] == {
        "state_delta": True,
        "session_state": True,
    }
    assert payload["internal_observation"] == {
        "observed_node_names": ["single_agent_structured_output_state_protection_run"],
        "semantic_observation": {
            "entered_semantics": [
                "structured_output_constraint",
                "schema_validation_failure",
            ],
            "observed_results": [],
        },
        "event_records": [
            {
                "author": "single_agent_structured_output_state_protection_run",
                "role": None,
                "output": None,
                "node_name": "single_agent_structured_output_state_protection_run",
                "has_state_delta": False,
                "state_delta": {},
            }
        ],
    }
    assert payload["context_access"] == {
        "state_delta": {},
        "session_state": {},
    }
    assert payload["runner_execution"] == {
        "Runner": "Runner",
        "request_acceptance": True,
        "event_consumption": True,
        "append_progression": True,
        "response_return": True,
    }
    assert payload["state_delta"] == {}
    assert payload["session_state"] == {}
    assert payload["output_file"] == "outputs/structured_output/formal-state-protection.json"
    assert payload["duration_seconds"] == 1.2346
    assert "CA-03" in payload["boundary_judgement"]


def test_build_success_payload_detects_dirty_state_write() -> None:
    output_path = project_root / "outputs" / "structured_output" / "dirty-state.json"

    payload = build_success_payload(
        started_at="2026-04-17T03:00:00Z",
        completed_at="2026-04-17T03:00:01Z",
        duration_seconds=0.5,
        input_text="Write a tiny story as structured output.",
        output_path=output_path,
        adk_module_path="/tmp/google-adk/src/google/adk/__init__.py",
        error_type="ValidationError",
        error_message="1 validation error for StoryOutput",
        event_records=[
            {
                "author": "single_agent_structured_output_state_protection_run",
                "node_path": "single_agent_structured_output_state_protection_run@1",
                "node_name": "single_agent_structured_output_state_protection_run",
                "output": None,
                "role": None,
                "text_parts": ['{"title": "Broken Story"}'],
                "has_state_delta": True,
                "state_delta": {OUTPUT_KEY: {"title": "Broken Story"}},
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
        session_state={OUTPUT_KEY: {"title": "Broken Story"}},
    )

    assert payload["state_delta_write_observed"] is True
    assert payload["session_state_write_observed"] is True
    assert payload["protected_state_channels"] == {
        "state_delta": False,
        "session_state": False,
    }
    assert payload["context_access"] == {
        "state_delta": {OUTPUT_KEY: {"title": "Broken Story"}},
        "session_state": {OUTPUT_KEY: {"title": "Broken Story"}},
    }
    assert payload["runner_execution"] == {
        "Runner": "Runner",
        "request_acceptance": True,
        "event_consumption": True,
        "append_progression": True,
        "response_return": True,
    }
    assert payload["state_delta"] == {OUTPUT_KEY: {"title": "Broken Story"}}
    assert payload["session_state"] == {OUTPUT_KEY: {"title": "Broken Story"}}
    assert payload["internal_observation"]["event_records"] == [
        {
            "author": "single_agent_structured_output_state_protection_run",
            "role": None,
            "output": None,
            "node_name": "single_agent_structured_output_state_protection_run",
            "has_state_delta": True,
            "state_delta": {OUTPUT_KEY: {"title": "Broken Story"}},
        }
    ]


def test_build_failure_payload_keeps_formal_entry_warning() -> None:
    output_path = project_root / "outputs" / "structured_output" / "failed-state-protection.json"

    payload = build_failure_payload(
        started_at="2026-04-17T03:00:00Z",
        completed_at="2026-04-17T03:00:01Z",
        duration_seconds=0.25,
        input_text="Write a tiny story as structured output.",
        output_path=output_path,
        exc=RuntimeError("formal state protection was not established"),
    )

    assert payload["result"] == "failed"
    assert payload["capability_id"] == CAPABILITY_ID
    assert payload["output_key"] == OUTPUT_KEY
    assert payload["selected_runtime_path"] == SELECTED_RUNTIME_PATH
    assert payload["error_type"] == "RuntimeError"
    assert payload["output_file"] == "outputs/structured_output/failed-state-protection.json"
    assert "正式状态保护能力已接入" in payload["boundary_judgement"]
