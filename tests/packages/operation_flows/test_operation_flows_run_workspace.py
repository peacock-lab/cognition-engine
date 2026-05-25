from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "packages" / "operation_flows" / "src"

sys.path.insert(0, str(SOURCE_ROOT))

from cognition_operation_flows._core.run_workspace import (  # noqa: E402
    build_operation_flow_run_workspace_policy,
    cleanup_operation_flow_run_workspace,
    operation_flow_run_workspace_status_dict,
    create_operation_flow_run_workspace,
    finalize_operation_flow_run_workspace,
    write_operation_flow_run_workspace_json,
    write_operation_flow_run_workspace_text,
)


def test_run_workspace_creates_standard_directories_and_manifest(tmp_path) -> None:
    policy = build_operation_flow_run_workspace_policy(workspace_root=tmp_path)
    workspace = create_operation_flow_run_workspace(
        policy=policy,
        workflow_name="operation_flow_plan_workflow",
        run_id="run-001",
    )

    assert workspace.workspace_created is True
    workspace_path = Path(workspace.workspace_path)
    assert workspace_path.exists()
    for subdir in ("inputs", "references", "evidence", "artifacts", "results"):
        assert (workspace_path / subdir).is_dir()
    manifest = json.loads(Path(workspace.manifest_path).read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "operation_flow-run-workspace.v1"
    assert manifest["status"] == "created"


def test_run_workspace_writes_refs_and_final_manifest(tmp_path) -> None:
    workspace = create_operation_flow_run_workspace(
        policy=build_operation_flow_run_workspace_policy(workspace_root=tmp_path),
        workflow_name="operation_flow_plan_workflow",
        run_id="run-002",
    )

    workspace, evidence_write = write_operation_flow_run_workspace_json(
        workspace,
        relative_path="evidence/reference_context.json",
        payload={"status": "succeeded"},
        kind="evidence",
    )
    workspace, artifact_write = write_operation_flow_run_workspace_text(
        workspace,
        relative_path="artifacts/terminal_display.txt",
        text="鱼塘建设方案\n",
        kind="artifact",
    )
    workspace, result_write = write_operation_flow_run_workspace_json(
        workspace,
        relative_path="results/workflow_result.json",
        payload={"status": "succeeded"},
        kind="result",
    )
    workspace = finalize_operation_flow_run_workspace(workspace, status="succeeded")
    status = operation_flow_run_workspace_status_dict(workspace)

    assert evidence_write.status == "succeeded"
    assert artifact_write.status == "succeeded"
    assert result_write.status == "succeeded"
    assert evidence_write.ref in workspace.evidence_refs
    assert artifact_write.ref in workspace.artifact_refs
    assert result_write.ref in workspace.result_refs
    assert status is not None
    assert status["workspace_created"] is True
    manifest = json.loads(Path(workspace.manifest_path).read_text(encoding="utf-8"))
    assert manifest["status"] == "succeeded"
    assert manifest["artifact_refs"] == list(workspace.artifact_refs)
    assert manifest["evidence_refs"] == list(workspace.evidence_refs)
    assert manifest["result_refs"] == list(workspace.result_refs)


def test_run_workspace_blocks_path_traversal_and_sensitive_paths(tmp_path) -> None:
    workspace = create_operation_flow_run_workspace(
        policy=build_operation_flow_run_workspace_policy(workspace_root=tmp_path),
        workflow_name="operation_flow_plan_workflow",
        run_id="run-003",
    )

    _, traversal = write_operation_flow_run_workspace_text(
        workspace,
        relative_path="../escape.txt",
        text="bad",
        kind="artifact",
    )
    _, sensitive = write_operation_flow_run_workspace_text(
        workspace,
        relative_path="evidence/api_key.txt",
        text="bad",
        kind="evidence",
    )

    assert traversal.status == "blocked"
    assert "workspace_relative_path_invalid" in traversal.blocking_reasons
    assert sensitive.status == "blocked"
    assert "workspace_relative_path_invalid" in sensitive.blocking_reasons


def test_run_workspace_cleanup_delete_on_success(tmp_path) -> None:
    workspace = create_operation_flow_run_workspace(
        policy=build_operation_flow_run_workspace_policy(
            workspace_root=tmp_path,
            retention_policy="delete_on_success",
            cleanup_policy="delete_on_success",
        ),
        workflow_name="operation_flow_plan_workflow",
        run_id="run-004",
    )
    workspace_path = Path(workspace.workspace_path)

    workspace, cleanup = cleanup_operation_flow_run_workspace(workspace, status="succeeded")

    assert cleanup.status == "succeeded"
    assert cleanup.cleanup_performed is True
    assert workspace.cleanup_performed is True
    assert not workspace_path.exists()
