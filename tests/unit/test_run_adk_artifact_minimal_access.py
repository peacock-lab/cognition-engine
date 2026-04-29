#!/usr/bin/env python3
"""ADK artifact 最小正式入口测试。"""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.run_adk_artifact_minimal_access import (  # noqa: E402
    ARTIFACT_NAME,
    ARTIFACT_SERVICE_CLASS,
    ENTRY_ID,
    ENTRY_TYPE,
    OUTPUTS_DIR,
    PROBE_REFERENCE,
    SELECTED_RUNTIME_PATH,
    build_failure_payload,
    build_success_payload,
    resolve_output_path,
)


def test_resolve_output_path_defaults_to_artifact_directory() -> None:
    output_path = resolve_output_path(None)

    assert output_path.parent == OUTPUTS_DIR
    assert output_path.name.startswith(f"{ENTRY_ID}-")
    assert output_path.suffix == ".json"


def test_resolve_output_path_accepts_project_relative_path() -> None:
    output_path = resolve_output_path("outputs/artifact/manual-run.json")

    assert output_path == project_root / "outputs" / "artifact" / "manual-run.json"


def test_build_success_payload_marks_formal_entry_boundary() -> None:
    output_path = project_root / "outputs" / "artifact" / "formal-entry.json"

    payload = build_success_payload(
        started_at="2026-04-17T03:00:00Z",
        completed_at="2026-04-17T03:00:01Z",
        duration_seconds=1.23456,
        input_text="hello-adk-artifact",
        output_path=output_path,
        event_records=[
            {
                "author": "artifact_minimal_access_run",
                "node_path": "artifact_minimal_access_run@1",
                "node_name": "artifact_minimal_access_run",
                "text_parts": ["artifact:hello-artifact"],
                "artifact_delta": {ARTIFACT_NAME: 0},
            }
        ],
        artifact_keys=[ARTIFACT_NAME],
        loaded_artifact_text="hello-artifact",
    )

    assert payload["result"] == "success"
    assert payload["entry_type"] == ENTRY_TYPE
    assert payload["probe_reference"] == PROBE_REFERENCE
    assert payload["selected_runtime_path"] == SELECTED_RUNTIME_PATH
    assert payload["artifact_name"] == ARTIFACT_NAME
    assert payload["artifact_service_class"] == ARTIFACT_SERVICE_CLASS
    assert payload["artifact_version"] == 0
    assert payload["loaded_artifact_text"] == "hello-artifact"
    assert payload["artifact_saved"] is True
    assert payload["artifact_loaded"] is True
    assert payload["artifact_listed"] is True
    assert payload["output_file"] == "outputs/artifact/formal-entry.json"
    assert payload["duration_seconds"] == 1.2346
    assert "正式结果文件" in payload["boundary_judgement"]


def test_build_failure_payload_keeps_formal_entry_warning() -> None:
    output_path = project_root / "outputs" / "artifact" / "failed-entry.json"

    payload = build_failure_payload(
        started_at="2026-04-17T03:00:00Z",
        completed_at="2026-04-17T03:00:01Z",
        duration_seconds=0.25,
        input_text="hello-adk-artifact",
        output_path=output_path,
        exc=RuntimeError("artifact save failed"),
    )

    assert payload["result"] == "failed"
    assert payload["entry_type"] == ENTRY_TYPE
    assert payload["probe_reference"] == PROBE_REFERENCE
    assert payload["selected_runtime_path"] == SELECTED_RUNTIME_PATH
    assert payload["artifact_name"] == ARTIFACT_NAME
    assert payload["artifact_service_class"] == ARTIFACT_SERVICE_CLASS
    assert payload["output_file"] == "outputs/artifact/failed-entry.json"
    assert payload["error_type"] == "RuntimeError"
    assert "probe 级验证结论" in payload["boundary_judgement"]
