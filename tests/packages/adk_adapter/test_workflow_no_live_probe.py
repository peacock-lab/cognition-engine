from __future__ import annotations

import re
from pathlib import Path

from adk_adapter import (
    AdkWorkflowNoLiveProbeOptions,
    run_workflow_no_live_probe,
)


def test_workflow_no_live_probe_outputs_safe_projection() -> None:
    projection = run_workflow_no_live_probe(
        AdkWorkflowNoLiveProbeOptions(
            probe_ref="adk-workflow-no-live-probe://unit-test",
            workflow_id="workflow-no-live-unit-test",
            invocation_id="workflow-no-live-invocation-test",
            artifact_ref="workflow-summary.txt",
        )
    )
    payload = projection.to_evaluation_projection()

    assert projection.probe_ref == "adk-workflow-no-live-probe://unit-test"
    assert projection.workflow_ref == "adk-workflow://workflow-no-live-unit-test"
    assert projection.workflow_status == "success"
    assert projection.event_count >= 1
    assert projection.node_paths
    assert projection.event_review_refs
    assert projection.artifact_binding_summary_refs
    assert projection.evaluation_summary_ref.startswith(
        "evaluation://adk-workflow-no-live/"
    )
    assert projection.service_summary["in_memory_services"] is True
    assert projection.raw_object_included is False
    assert projection.raw_event_payload_included is False
    assert projection.artifact_body_included is False
    assert projection.adk_eval_raw_data_included is False
    assert projection.user_product_path_enabled is False
    assert projection.default_local_state_dir_enabled is False
    assert projection.auto_resume_enabled is False
    assert projection.skills_loaded is False
    assert projection.memory_enabled is False
    assert projection.tools_mcp_enabled is False
    assert projection.callbacks_enabled is False
    assert projection.plugins_enabled is False
    assert "output" not in str(payload["event_review_refs"])
    assert "raw_event" not in str(payload["event_review_refs"])
    assert "raw_payload" not in str(payload)


def test_adk_adapter_does_not_depend_on_cognition_evaluation() -> None:
    package_root = Path("packages/adk_adapter/src/adk_adapter")
    forbidden = re.compile(
        r"^\s*(from\s+cognition_evaluation|import\s+cognition_evaluation)\b",
        re.MULTILINE,
    )

    for source_file in package_root.rglob("*.py"):
        source = source_file.read_text(encoding="utf-8")
        assert forbidden.search(source) is None, source_file
