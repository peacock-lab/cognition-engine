from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.run_adk_single_agent_structured_output_failure_recognition import (  # noqa: E402
    CAPABILITY_ID,
    ENTRY_ID,
    EXPECTED_ERROR_TYPE,
    INVALID_STRUCTURED_OUTPUT,
    MATRIX_CELL_ID,
    MATRIX_SCOPE_IDS,
    OUTPUTS_DIR,
    OUTPUT_KEY,
    PROBE_REFERENCE,
    SELECTED_RUNTIME_PATH,
    build_failure_payload,
    build_success_payload,
    classify_failure,
    normalize_validation_errors,
    resolve_output_path,
)


class FakeValidationError(Exception):
    def errors(self) -> list[dict[str, object]]:
        return [
            {
                "type": "missing",
                "loc": ("content",),
                "msg": "Field required",
            }
        ]


def test_resolve_output_path_defaults_to_structured_output_directory() -> None:
    output_path = resolve_output_path(None)

    assert output_path.parent == OUTPUTS_DIR
    assert output_path.name.startswith(f"{ENTRY_ID}-")
    assert output_path.suffix == ".json"


def test_normalize_validation_errors_extracts_type_and_location() -> None:
    normalized_errors = normalize_validation_errors(FakeValidationError("boom"))

    assert normalized_errors == [
        {
            "type": "missing",
            "loc": ["content"],
            "msg": "Field required",
        }
    ]


def test_classify_failure_maps_top_level_missing_field_to_m02() -> None:
    classified_failure = classify_failure(
        [
            {
                "type": "missing",
                "loc": ["content"],
                "msg": "Field required",
            }
        ]
    )

    assert classified_failure["matrix_cell_id"] == MATRIX_CELL_ID
    assert classified_failure["failure_kind"] == "missing_required_field"
    assert classified_failure["failure_location_shape"] == "top_level_object_field"
    assert classified_failure["missing_field"] == "content"
    assert classified_failure["location_path"] == ["content"]


def test_build_success_payload_marks_formal_failure_recognition_boundary() -> None:
    output_path = project_root / "outputs" / "structured_output" / "formal-failure-recognition.json"

    payload = build_success_payload(
        started_at="2026-04-17T03:00:00Z",
        completed_at="2026-04-17T03:00:01Z",
        duration_seconds=1.23456,
        input_text="Write a tiny story as structured output.",
        output_path=output_path,
        adk_module_path="/tmp/google-adk/src/google/adk/__init__.py",
        error_type=EXPECTED_ERROR_TYPE,
        error_message="1 validation error for StoryOutput",
        normalized_errors=[
            {
                "type": "missing",
                "loc": ["content"],
                "msg": "Field required",
            }
        ],
        classified_failure={
            "matrix_cell_id": MATRIX_CELL_ID,
            "failure_kind": "missing_required_field",
            "failure_location_shape": "top_level_object_field",
            "missing_field": "content",
            "location_path": ["content"],
            "matched_error": {
                "type": "missing",
                "loc": ["content"],
                "msg": "Field required",
            },
        },
        event_records=[
            {
                "author": "single_agent_structured_output_failure_recognition_run",
                "node_path": "single_agent_structured_output_failure_recognition_run@1",
                "node_name": "single_agent_structured_output_failure_recognition_run",
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
    assert payload["entry_type"] == "formal_structured_output_failure_recognition_run"
    assert payload["capability_id"] == CAPABILITY_ID
    assert payload["matrix_cell_id"] == MATRIX_CELL_ID
    assert payload["matrix_scope_ids"] == MATRIX_SCOPE_IDS
    assert payload["probe_reference"] == PROBE_REFERENCE
    assert payload["selected_runtime_path"] == SELECTED_RUNTIME_PATH
    assert payload["invalid_structured_output_payload"] == INVALID_STRUCTURED_OUTPUT
    assert payload["recognized_error_type"] == EXPECTED_ERROR_TYPE
    assert payload["recognized_failure_kind"] == "missing_required_field"
    assert payload["recognized_failure_location_shape"] == "top_level_object_field"
    assert payload["recognized_missing_field"] == "content"
    assert payload["recognized_location_path"] == ["content"]
    assert payload["recognized_matrix_cell_id"] == MATRIX_CELL_ID
    assert payload["response_schema_request_count"] == 1
    assert payload["formal_failure_recognition_established"] is True
    assert payload["state_delta_write_observed"] is False
    assert payload["session_state_write_observed"] is False
    assert payload["internal_observation"] == {
        "observed_node_names": ["single_agent_structured_output_failure_recognition_run"],
        "semantic_observation": {
            "entered_semantics": [
                "structured_output_constraint",
                "schema_validation_failure",
            ],
            "observed_results": [],
        },
        "event_records": [
            {
                "author": "single_agent_structured_output_failure_recognition_run",
                "role": None,
                "output": None,
                "node_name": "single_agent_structured_output_failure_recognition_run",
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
    assert payload["output_file"] == "outputs/structured_output/formal-failure-recognition.json"
    assert payload["duration_seconds"] == 1.2346
    assert "CA-02" in payload["boundary_judgement"]


def test_build_failure_payload_keeps_formal_entry_warning() -> None:
    output_path = project_root / "outputs" / "structured_output" / "failed.json"

    payload = build_failure_payload(
        started_at="2026-04-17T03:00:00Z",
        completed_at="2026-04-17T03:00:01Z",
        duration_seconds=0.25,
        input_text="Write a tiny story as structured output.",
        output_path=output_path,
        exc=RuntimeError("formal recognition was not established"),
    )

    assert payload["result"] == "failed"
    assert payload["capability_id"] == CAPABILITY_ID
    assert payload["matrix_cell_id"] == MATRIX_CELL_ID
    assert payload["matrix_scope_ids"] == MATRIX_SCOPE_IDS
    assert payload["output_key"] == OUTPUT_KEY
    assert payload["selected_runtime_path"] == SELECTED_RUNTIME_PATH
    assert payload["error_type"] == "RuntimeError"
    assert payload["output_file"] == "outputs/structured_output/failed.json"
    assert "正式失败识别能力已接入" in payload["boundary_judgement"]
