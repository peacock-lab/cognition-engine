from __future__ import annotations

from pathlib import Path

from cognition_operation_flows._requests.drafts import (
    OperationFlowGovernanceRefsCandidate,
    OperationFlowReferenceWorkspaceControlsCandidate,
    build_operation_flow_config_profile_explain_request_draft,
    build_operation_flow_plan_request_draft,
    build_operation_flow_reference_review_request_draft,
    build_operation_flow_run_workspace_evidence_audit_request_draft,
)
from cognition_operation_flows._workflows.config_profile_explain import (
    OperationFlowConfigProfileExplainWorkflowRequestCandidate,
)
from cognition_operation_flows._workflows.plan import OperationFlowPlanWorkflowRequestCandidate
from cognition_operation_flows._workflows.reference_review import (
    OperationFlowReferenceReviewWorkflowRequestCandidate,
)
from cognition_operation_flows._workflows.run_workspace_evidence_audit import (
    OperationFlowRunWorkspaceEvidenceAuditWorkflowRequestCandidate,
)
from cognition_operation_flows._requests.builder import (
    build_operation_flow_config_profile_explain_workflow_request_from_operation_flow_draft,
    build_operation_flow_plan_workflow_request_from_operation_flow_draft,
    build_operation_flow_reference_review_workflow_request_from_operation_flow_draft,
    build_operation_flow_run_workspace_evidence_audit_workflow_request_from_operation_flow_draft,
    build_operation_flow_workflow_request_from_operation_flow_draft,
)


def test_plan_request_builder_builds_current_operation_flow_request() -> None:
    live_service = object()
    draft = build_operation_flow_plan_request_draft(
        sanitized_user_text="我要建一个鱼塘，请给建设方案",
        chat_session_id="session-plan",
        turn_index=1,
        sanitized_history=({"user": "上一轮", "assistant": "已收到"},),
        sanitized_previous_display_text="上一轮计划",
        governance_refs=_refs(),
        controls=OperationFlowReferenceWorkspaceControlsCandidate(
            reference_paths=("docs/a.md",),
            reference_repo_root="/repo",
            reference_profile_name="readonly_reference",
            run_workspace_root="/tmp/runs",
            run_workspace_enabled=True,
            run_workspace_retention_policy="keep",
            run_workspace_cleanup_policy="manual",
            run_workspace_max_write_bytes=4096,
        ),
        route_summary={"matched": True, "workflow_name": "operation_flow_plan_workflow"},
        user_passthrough_parameters={"audience": "farmer"},
        live_model_allowed=True,
    )

    request = build_operation_flow_plan_workflow_request_from_operation_flow_draft(
        draft,
        llm_invocation_service=live_service,
        reference_profile_config={"profiles": {}},
        reference_session_args={"profile": "readonly_reference"},
        reference_entrypoint_explicit_args={"reference_paths": ["docs/a.md"]},
    )

    assert isinstance(request, OperationFlowPlanWorkflowRequestCandidate)
    assert request.user_text == "我要建一个鱼塘，请给建设方案"
    assert request.chat_session_id == "session-plan"
    assert request.turn_index == 1
    assert request.history == ({"user": "上一轮", "assistant": "已收到"},)
    assert request.previous_plan_text == "上一轮计划"
    assert request.llm_invocation_service is live_service
    assert request.live_gate == "controlled_live"
    assert request.approval_ref == "approval://test"
    assert request.audit_ref == "audit://test"
    assert request.sanitized_evidence_ref == "evidence://test"
    assert request.reference_paths == ("docs/a.md",)
    assert request.reference_profile_config == {"profiles": {}}
    assert request.reference_session_args == {"profile": "readonly_reference"}
    assert request.run_workspace_enabled is True
    assert request.run_workspace_max_write_bytes == 4096
    assert request.user_passthrough_parameters == {"audience": "farmer"}
    assert request.metadata["source"] == "cognition_operation_flows._requests.builder"
    assert request.metadata["operation_flow_request_builder"] is True
    assert request.metadata["request_draft_status"]["workflow_execution_enabled"] is False
    assert "sanitized_user_text" not in request.metadata["request_draft_status"]


def test_reference_review_request_builder_builds_current_operation_flow_request() -> None:
    draft = build_operation_flow_reference_review_request_draft(
        sanitized_user_text="请审查这些资料是否符合当前主线",
        chat_session_id="session-review",
        turn_index=2,
        governance_refs=_refs(),
        controls=OperationFlowReferenceWorkspaceControlsCandidate(
            reference_paths=("tasks/b1/example.md",),
            reference_repo_root="/repo",
            external_readonly_evidence_paths=(
                "outputs/external-readonly/cli-fetch/example.json",
            ),
            external_readonly_evidence_repo_root="/repo",
        ),
    )

    request = build_operation_flow_workflow_request_from_operation_flow_draft(draft)

    assert isinstance(request, OperationFlowReferenceReviewWorkflowRequestCandidate)
    assert request.user_text == "请审查这些资料是否符合当前主线"
    assert request.reference_paths == ("tasks/b1/example.md",)
    assert request.external_readonly_evidence_paths == (
        "outputs/external-readonly/cli-fetch/example.json",
    )
    assert request.external_readonly_evidence_repo_root == "/repo"
    assert request.reference_profile_name == "readonly_reference"
    assert request.live_model_allowed is False
    assert request.llm_invocation_service is None
    assert request.live_gate == "no_live"
    assert request.metadata["builder_target"] == "operation_flow_reference_review_workflow"


def test_config_profile_explain_request_builder_maps_operation_flow_context_fields() -> None:
    config_context = {"status": "fake-context"}
    draft = build_operation_flow_config_profile_explain_request_draft(
        sanitized_user_text="请解释当前配置为什么这样生效",
        chat_session_id="session-config",
        turn_index=3,
        governance_refs=_refs(),
        controls=OperationFlowReferenceWorkspaceControlsCandidate(
            reference_paths=("config/base/runtime.yaml",),
            tool_exposure_profile="readonly_reference",
            run_workspace_root="/tmp/runs",
            run_workspace_enabled=True,
        ),
        entrypoint_explicit_args={"tool_exposure_profile": "readonly_reference"},
        session_args={"profile": "local"},
        operator_approved=True,
        request_live_llm=True,
        request_ollama=True,
        allow_live_llm=False,
        allow_ollama=True,
        live_llm_timeout_seconds=180,
    )

    request = build_operation_flow_config_profile_explain_workflow_request_from_operation_flow_draft(
        draft,
        config_context=config_context,
        config_root="config",
        environment="local",
        profile="dev",
        ollama_api_base="http://127.0.0.1:11434",
    )

    assert isinstance(request, OperationFlowConfigProfileExplainWorkflowRequestCandidate)
    assert request.config_context == config_context
    assert request.config_root == "config"
    assert request.environment == "local"
    assert request.profile == "dev"
    assert request.ollama_api_base == "http://127.0.0.1:11434"
    assert request.operator_approved is True
    assert request.request_live_llm is True
    assert request.allow_live_llm is False
    assert request.governance_summary_output_ref == "artifact://test"
    assert request.reference_paths == ("config/base/runtime.yaml",)
    assert request.tool_exposure_profile == "readonly_reference"
    assert request.entrypoint_explicit_args == {
        "tool_exposure_profile": "readonly_reference"
    }
    assert request.session_args == {"profile": "local"}
    assert request.run_workspace_enabled is True
    assert request.metadata["builder_target"] == "operation_flow_config_profile_explain_workflow"


def test_evidence_audit_request_builder_maps_audit_controls() -> None:
    draft = build_operation_flow_run_workspace_evidence_audit_request_draft(
        sanitized_user_text="请审计 run workspace，检查证据完整吗",
        chat_session_id="session-audit",
        turn_index=4,
        governance_refs=_refs(),
        controls=OperationFlowReferenceWorkspaceControlsCandidate(
            audit_run_workspace_path="/tmp/audited",
            audit_run_workspace_ref="run-workspace://operation_flow-plan/session-turn",
            audit_run_workspace_root="/tmp",
            audit_focus=("manifest", "results"),
            run_workspace_root="/tmp/audit-output",
            run_workspace_enabled=True,
        ),
    )

    request = build_operation_flow_workflow_request_from_operation_flow_draft(draft)

    assert isinstance(request, OperationFlowRunWorkspaceEvidenceAuditWorkflowRequestCandidate)
    assert request.audit_run_workspace_path == "/tmp/audited"
    assert request.audit_run_workspace_ref == "run-workspace://operation_flow-plan/session-turn"
    assert request.audit_run_workspace_root == "/tmp"
    assert request.audit_focus == ("manifest", "results")
    assert request.run_workspace_root == "/tmp/audit-output"
    assert request.run_workspace_enabled is True
    assert request.metadata["builder_target"] == (
        "operation_flow_run_workspace_evidence_audit_workflow"
    )


def test_request_builder_rejects_wrong_workflow_builder() -> None:
    draft = build_operation_flow_reference_review_request_draft(
        sanitized_user_text="请审查资料",
        controls=OperationFlowReferenceWorkspaceControlsCandidate(
            reference_paths=("tasks/example.md",)
        ),
    )

    try:
        build_operation_flow_plan_workflow_request_from_operation_flow_draft(draft)
    except ValueError as exc:
        assert "expected operation_flow_plan_workflow draft" in str(exc)
    else:
        raise AssertionError("expected workflow mismatch to be rejected")


def test_request_builder_source_keeps_cli_and_gateway_out() -> None:
    source = (
        Path(__file__).resolve().parents[3]
        / "packages"
        / "operation_flows"
        / "src"
        / "cognition_operation_flows"
        / "_requests"
        / "builder.py"
    ).read_text(encoding="utf-8")

    assert "from cognition_cli" not in source
    assert "import cognition_cli" not in source
    assert "from product_gateway" not in source
    assert "import product_gateway" not in source
    assert "import argparse" not in source


def _refs() -> OperationFlowGovernanceRefsCandidate:
    return OperationFlowGovernanceRefsCandidate(
        approval_ref="approval://test",
        audit_ref="audit://test",
        sanitized_evidence_ref="evidence://test",
        governance_summary_output_ref="artifact://test",
    )
