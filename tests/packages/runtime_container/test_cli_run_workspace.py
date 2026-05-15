from __future__ import annotations

import json
from pathlib import Path

from config_assembly.runtime import assemble_runtime_config_payload
from config_contexts.runtime_builder import build_runtime_config_contexts
from runtime_container.cli_run_workspace import (
    build_cli_run_workspace_policy,
    cleanup_cli_run_workspace,
    cli_run_workspace_status_dict,
    create_cli_run_workspace,
    finalize_cli_run_workspace,
    write_cli_run_workspace_json,
    write_cli_run_workspace_text,
)


def test_run_workspace_creates_standard_directories_and_manifest(tmp_path) -> None:
    policy = build_cli_run_workspace_policy(workspace_root=tmp_path)
    workspace = create_cli_run_workspace(
        policy=policy,
        workflow_name="cli_plan_workflow",
        run_id="run-001",
    )

    assert workspace.workspace_created is True
    workspace_path = Path(workspace.workspace_path)
    assert workspace_path.exists()
    for subdir in ("inputs", "references", "evidence", "artifacts", "results"):
        assert (workspace_path / subdir).is_dir()
    manifest = json.loads(Path(workspace.manifest_path).read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "cli-run-workspace.v1"
    assert manifest["status"] == "created"


def test_run_workspace_writes_refs_and_final_manifest(tmp_path) -> None:
    workspace = create_cli_run_workspace(
        policy=build_cli_run_workspace_policy(workspace_root=tmp_path),
        workflow_name="cli_plan_workflow",
        run_id="run-002",
    )

    workspace, evidence_write = write_cli_run_workspace_json(
        workspace,
        relative_path="evidence/reference_context.json",
        payload={"status": "succeeded"},
        kind="evidence",
    )
    workspace, artifact_write = write_cli_run_workspace_text(
        workspace,
        relative_path="artifacts/terminal_display.txt",
        text="鱼塘建设方案\n",
        kind="artifact",
    )
    workspace, result_write = write_cli_run_workspace_json(
        workspace,
        relative_path="results/workflow_result.json",
        payload={"status": "succeeded"},
        kind="result",
    )
    workspace = finalize_cli_run_workspace(workspace, status="succeeded")
    status = cli_run_workspace_status_dict(workspace)

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
    workspace = create_cli_run_workspace(
        policy=build_cli_run_workspace_policy(workspace_root=tmp_path),
        workflow_name="cli_plan_workflow",
        run_id="run-003",
    )

    _, traversal = write_cli_run_workspace_text(
        workspace,
        relative_path="../escape.txt",
        text="bad",
        kind="artifact",
    )
    _, sensitive = write_cli_run_workspace_text(
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
    workspace = create_cli_run_workspace(
        policy=build_cli_run_workspace_policy(
            workspace_root=tmp_path,
            retention_policy="delete_on_success",
            cleanup_policy="delete_on_success",
        ),
        workflow_name="cli_plan_workflow",
        run_id="run-004",
    )
    workspace_path = Path(workspace.workspace_path)

    workspace, cleanup = cleanup_cli_run_workspace(workspace, status="succeeded")

    assert cleanup.status == "succeeded"
    assert cleanup.cleanup_performed is True
    assert workspace.cleanup_performed is True
    assert not workspace_path.exists()


def test_runtime_config_run_workspace_policy_feeds_workspace_creation(tmp_path) -> None:
    bundle = build_runtime_config_contexts(
        assemble_runtime_config_payload(Path("config"), environment="local")
    )
    policy_kwargs = bundle.run_workspace.to_policy_kwargs()
    policy_kwargs["workspace_root"] = tmp_path / policy_kwargs["workspace_root"]

    workspace = create_cli_run_workspace(
        policy=build_cli_run_workspace_policy(**policy_kwargs),
        workflow_name="cli_plan_workflow",
        run_id="run-config-bridge",
    )

    assert workspace.workspace_created is True
    assert workspace.retention_policy == "keep"
    assert workspace.cleanup_policy == "manual"
    assert Path(workspace.manifest_path).is_file()
