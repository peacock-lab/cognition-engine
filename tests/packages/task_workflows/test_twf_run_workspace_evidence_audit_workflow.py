from __future__ import annotations

import json
from pathlib import Path

from cognition_task_workflows._core.run_workspace import (
    build_twf_run_workspace_policy,
    create_twf_run_workspace,
    finalize_twf_run_workspace,
    write_twf_run_workspace_json,
    write_twf_run_workspace_text,
)
from cognition_task_workflows._workflows.run_workspace_evidence_audit import (
    TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
    TwfRunWorkspaceEvidenceAuditWorkflowRequestCandidate,
    detect_twf_run_workspace_evidence_audit_request,
    run_twf_run_workspace_evidence_audit_workflow,
)


def test_detector_requires_audit_target_signal() -> None:
    assert (
        detect_twf_run_workspace_evidence_audit_request(
            "请审计 run workspace，检查证据完整吗",
            audit_target_requested=False,
        )
        is False
    )
    assert (
        detect_twf_run_workspace_evidence_audit_request(
            "请审计 run workspace，检查证据完整吗",
            audit_target_requested=True,
        )
        is True
    )


def test_audit_existing_workspace_path_without_model_or_tool_call(
    tmp_path: Path,
) -> None:
    audited_workspace = _create_passed_workspace(tmp_path / "audited")

    result = run_twf_run_workspace_evidence_audit_workflow(
        TwfRunWorkspaceEvidenceAuditWorkflowRequestCandidate(
            user_text="请审计 run workspace，检查证据完整吗",
            chat_session_id="cli-audit-test",
            turn_index=1,
            audit_run_workspace_path=audited_workspace,
            approval_ref="approval://audit-test",
            audit_ref="audit://audit-test",
            sanitized_evidence_ref="evidence://audit-test",
        )
    )

    assert result.fail_safe is False
    assert result.no_live is True
    assert result.model_call_count == 0
    assert result.audit_context.audit_result == "passed"
    assert result.audit_context.target.status == "resolved"
    assert result.task_run_context is not None
    assert result.task_run_context.status == "succeeded"
    assert "运行工作区证据审计结果" in result.terminal_display_text
    assert "结构完整性" in result.terminal_display_text
    assert "未发现结构或边界问题" in result.terminal_display_text
    assert "raw_response" not in result.terminal_display_text


def test_audit_existing_workspace_ref_resolves_under_root(tmp_path: Path) -> None:
    workspace_root = tmp_path / "audited"
    audited_workspace = _create_passed_workspace(workspace_root)
    manifest = json.loads(
        (audited_workspace / "manifest.json").read_text(encoding="utf-8")
    )

    result = run_twf_run_workspace_evidence_audit_workflow(
        TwfRunWorkspaceEvidenceAuditWorkflowRequestCandidate(
            user_text="请审计 run workspace，检查证据完整吗",
            chat_session_id="cli-audit-ref-test",
            turn_index=1,
            audit_run_workspace_ref=manifest["workspace_ref"],
            audit_run_workspace_root=workspace_root,
        )
    )

    assert result.audit_context.audit_result == "passed"
    assert result.audit_context.target.workspace_ref == manifest["workspace_ref"]


def test_audit_detects_forbidden_json_key_without_printing_value(
    tmp_path: Path,
) -> None:
    audited_workspace = _create_passed_workspace(tmp_path / "audited")
    (audited_workspace / "evidence" / "unsafe.json").write_text(
        json.dumps(
            {
                "status": "captured",
                "raw_response": "sensitive provider payload should not appear",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = run_twf_run_workspace_evidence_audit_workflow(
        TwfRunWorkspaceEvidenceAuditWorkflowRequestCandidate(
            user_text="请审计 run workspace，检查证据完整吗",
            audit_run_workspace_path=audited_workspace,
        )
    )

    assert result.audit_context.audit_result == "attention_required"
    assert any(
        finding.code == "boundary_sensitive_marker_detected"
        for finding in result.audit_context.findings
    )
    assert "sensitive provider payload" not in result.terminal_display_text


def test_audit_output_workspace_writes_summary_layers(tmp_path: Path) -> None:
    audited_workspace = _create_passed_workspace(tmp_path / "audited")
    output_root = tmp_path / "audit-output"

    result = run_twf_run_workspace_evidence_audit_workflow(
        TwfRunWorkspaceEvidenceAuditWorkflowRequestCandidate(
            user_text="请审计 run workspace，检查证据完整吗",
            chat_session_id="cli-audit-output-test",
            turn_index=1,
            audit_run_workspace_path=audited_workspace,
            run_workspace_root=str(output_root),
            run_workspace_enabled=True,
            run_workspace_retention_policy="keep",
            run_workspace_cleanup_policy="manual",
        )
    )

    assert result.run_workspace is not None
    assert result.run_workspace.workspace_created is True
    output_workspace = Path(result.run_workspace.workspace_path)
    context_payload = json.loads(
        (output_workspace / "evidence" / "workspace_audit_context.json").read_text(
            encoding="utf-8"
        )
    )
    result_payload = json.loads(
        (output_workspace / "results" / "workflow_result.json").read_text(
            encoding="utf-8"
        )
    )
    terminal_display = (
        output_workspace / "artifacts" / "terminal_display.txt"
    ).read_text(encoding="utf-8")

    assert context_payload["audit_result"] == "passed"
    assert context_payload["does_not_modify_audited_workspace"] is True
    assert result_payload["workflow"] == TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME
    assert result_payload["model_call_count"] == 0
    assert "运行工作区证据审计结果" in terminal_display


def _create_passed_workspace(workspace_root: Path) -> Path:
    policy = build_twf_run_workspace_policy(
        workspace_root=workspace_root,
        retention_policy="keep",
        cleanup_policy="manual",
        max_write_bytes=65536,
    )
    workspace = create_twf_run_workspace(
        policy=policy,
        workflow_name="twf_config_profile_explain_workflow",
        run_id="cli-config-profile-explain-workflow-audit-source-turn-001",
    )
    workspace, _ = write_twf_run_workspace_json(
        workspace,
        relative_path="evidence/config_explain_context.json",
        payload={
            "status": "succeeded",
            "does_not_read_raw_config_directly": True,
            "does_not_execute_tools": True,
            "does_not_call_model": True,
            "run_workspace_summary": {"source": "entrypoint_explicit_args"},
        },
        kind="evidence",
    )
    workspace, _ = write_twf_run_workspace_text(
        workspace,
        relative_path="artifacts/terminal_display.txt",
        text="配置解释结果\n边界：不读取 raw config，不调用模型。\n",
        kind="artifact",
    )
    workspace, _ = write_twf_run_workspace_json(
        workspace,
        relative_path="results/workflow_result.json",
        payload={
            "workflow": "twf_config_profile_explain_workflow",
            "status": "succeeded",
            "model_call_count": 0,
            "no_live": True,
        },
        kind="result",
    )
    workspace = finalize_twf_run_workspace(
        workspace,
        status="succeeded",
        metadata={"workflow": "twf_config_profile_explain_workflow"},
    )
    return Path(workspace.workspace_path)
