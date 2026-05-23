"""Task workflow request builders for task workflow request drafts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cognition_operation_flows._requests.registry import (
    TWF_PLAN_WORKFLOW_NAME,
)
from cognition_operation_flows._requests.intent_detectors import (
    TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
    TWF_REFERENCE_REVIEW_WORKFLOW_NAME,
    TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
)
from cognition_operation_flows._requests.drafts import (
    TwfWorkflowRequestDraftCandidate,
    twf_workflow_request_draft_status_dict,
)
from cognition_operation_flows._workflows.config_profile_explain import (
    CONFIG_PROFILE_EXPLAIN_DISPLAY_PREVIEW_LIMIT,
    TwfConfigProfileExplainWorkflowRequestCandidate,
)
from cognition_operation_flows._workflows.plan import (
    DEFAULT_PLAN_MODEL_NAME,
    PLAN_DISPLAY_PREVIEW_LIMIT,
    TwfPlanWorkflowRequestCandidate,
)
from cognition_operation_flows._workflows.reference_review import (
    TwfReferenceReviewWorkflowRequestCandidate,
)
from cognition_operation_flows._workflows.run_workspace_evidence_audit import (
    RUN_WORKSPACE_EVIDENCE_AUDIT_DISPLAY_PREVIEW_LIMIT,
    TwfRunWorkspaceEvidenceAuditWorkflowRequestCandidate,
)


TwfWorkflowRequestCandidate = (
    TwfPlanWorkflowRequestCandidate
    | TwfReferenceReviewWorkflowRequestCandidate
    | TwfConfigProfileExplainWorkflowRequestCandidate
    | TwfRunWorkspaceEvidenceAuditWorkflowRequestCandidate
)


def build_twf_workflow_request_from_twf_draft(
    draft: TwfWorkflowRequestDraftCandidate,
    *,
    llm_invocation_service: Any | None = None,
    config_context: Any | None = None,
    config_root: str | None = None,
    environment: str = "local",
    profile: str | None = None,
    ollama_api_base: str | None = None,
    reference_profile_config: Mapping[str, Any] | None = None,
    reference_session_args: Mapping[str, Any] | None = None,
    reference_entrypoint_explicit_args: Mapping[str, Any] | None = None,
    model_name: str = DEFAULT_PLAN_MODEL_NAME,
) -> TwfWorkflowRequestCandidate:
    """Dispatch a Twf request draft to the current task workflow request candidate."""

    if draft.workflow_name == TWF_PLAN_WORKFLOW_NAME:
        return build_twf_plan_workflow_request_from_twf_draft(
            draft,
            llm_invocation_service=llm_invocation_service,
            reference_profile_config=reference_profile_config,
            reference_session_args=reference_session_args,
            reference_entrypoint_explicit_args=reference_entrypoint_explicit_args,
            model_name=model_name,
        )
    if draft.workflow_name == TWF_REFERENCE_REVIEW_WORKFLOW_NAME:
        return build_twf_reference_review_workflow_request_from_twf_draft(
            draft,
            llm_invocation_service=llm_invocation_service,
            reference_profile_config=reference_profile_config,
            reference_session_args=reference_session_args,
            reference_entrypoint_explicit_args=reference_entrypoint_explicit_args,
            model_name=model_name,
        )
    if draft.workflow_name == TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME:
        return build_twf_config_profile_explain_workflow_request_from_twf_draft(
            draft,
            config_context=config_context,
            config_root=config_root,
            environment=environment,
            profile=profile,
            ollama_api_base=ollama_api_base,
        )
    if draft.workflow_name == TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME:
        return build_twf_run_workspace_evidence_audit_workflow_request_from_twf_draft(
            draft
        )
    raise ValueError(f"unsupported Twf workflow draft: {draft.workflow_name}")


def build_twf_plan_workflow_request_from_twf_draft(
    draft: TwfWorkflowRequestDraftCandidate,
    *,
    llm_invocation_service: Any | None = None,
    reference_profile_config: Mapping[str, Any] | None = None,
    reference_session_args: Mapping[str, Any] | None = None,
    reference_entrypoint_explicit_args: Mapping[str, Any] | None = None,
    model_name: str = DEFAULT_PLAN_MODEL_NAME,
) -> TwfPlanWorkflowRequestCandidate:
    """Build the current task workflow plan request from a Twf request draft."""

    _require_workflow(draft, TWF_PLAN_WORKFLOW_NAME)
    return TwfPlanWorkflowRequestCandidate(
        user_text=draft.turn_input.sanitized_user_text,
        chat_session_id=draft.turn_input.chat_session_id,
        turn_index=draft.turn_input.turn_index,
        history=draft.turn_input.sanitized_history,
        previous_plan_text=draft.turn_input.sanitized_previous_display_text,
        live_model_allowed=draft.live_model_allowed,
        llm_invocation_service=(
            llm_invocation_service if draft.live_model_allowed else None
        ),
        approval_ref=draft.governance_refs.approval_ref,
        audit_ref=draft.governance_refs.audit_ref,
        sanitized_evidence_ref=draft.governance_refs.sanitized_evidence_ref,
        risk_level="low",
        output_budget=PLAN_DISPLAY_PREVIEW_LIMIT,
        live_gate=_live_gate(draft),
        user_passthrough_parameters=draft.user_passthrough_parameters,
        reference_paths=draft.controls.reference_paths,
        reference_repo_root=draft.controls.reference_repo_root,
        reference_profile_name=draft.controls.reference_profile_name
        or "readonly_reference",
        reference_profile_config=reference_profile_config,
        reference_session_args=dict(reference_session_args or {}),
        reference_entrypoint_explicit_args=dict(
            reference_entrypoint_explicit_args or {}
        ),
        run_workspace_root=draft.controls.run_workspace_root,
        run_workspace_enabled=draft.controls.run_workspace_enabled,
        run_workspace_retention_policy=(
            draft.controls.run_workspace_retention_policy or "keep"
        ),
        run_workspace_cleanup_policy=(
            draft.controls.run_workspace_cleanup_policy or "manual"
        ),
        run_workspace_max_write_bytes=(
            draft.controls.run_workspace_max_write_bytes or 65536
        ),
        model_name=model_name,
        metadata=_builder_metadata(draft, builder_target="twf_plan_workflow"),
    )


def build_twf_reference_review_workflow_request_from_twf_draft(
    draft: TwfWorkflowRequestDraftCandidate,
    *,
    llm_invocation_service: Any | None = None,
    reference_profile_config: Mapping[str, Any] | None = None,
    reference_session_args: Mapping[str, Any] | None = None,
    reference_entrypoint_explicit_args: Mapping[str, Any] | None = None,
    model_name: str = DEFAULT_PLAN_MODEL_NAME,
) -> TwfReferenceReviewWorkflowRequestCandidate:
    """Build the current task workflow reference review request from a draft."""

    _require_workflow(draft, TWF_REFERENCE_REVIEW_WORKFLOW_NAME)
    return TwfReferenceReviewWorkflowRequestCandidate(
        user_text=draft.turn_input.sanitized_user_text,
        chat_session_id=draft.turn_input.chat_session_id,
        turn_index=draft.turn_input.turn_index,
        history=draft.turn_input.sanitized_history,
        live_model_allowed=draft.live_model_allowed,
        llm_invocation_service=(
            llm_invocation_service if draft.live_model_allowed else None
        ),
        approval_ref=draft.governance_refs.approval_ref,
        audit_ref=draft.governance_refs.audit_ref,
        sanitized_evidence_ref=draft.governance_refs.sanitized_evidence_ref,
        risk_level="low",
        output_budget=PLAN_DISPLAY_PREVIEW_LIMIT,
        live_gate=_live_gate(draft),
        user_passthrough_parameters=draft.user_passthrough_parameters,
        reference_paths=draft.controls.reference_paths,
        reference_repo_root=draft.controls.reference_repo_root,
        external_readonly_evidence_paths=(
            draft.controls.external_readonly_evidence_paths
        ),
        external_readonly_evidence_repo_root=(
            draft.controls.external_readonly_evidence_repo_root
        ),
        reference_profile_name=draft.controls.reference_profile_name
        or "readonly_reference",
        reference_profile_config=reference_profile_config,
        reference_session_args=dict(reference_session_args or {}),
        reference_entrypoint_explicit_args=dict(
            reference_entrypoint_explicit_args or {}
        ),
        run_workspace_root=draft.controls.run_workspace_root,
        run_workspace_enabled=draft.controls.run_workspace_enabled,
        run_workspace_retention_policy=(
            draft.controls.run_workspace_retention_policy or "keep"
        ),
        run_workspace_cleanup_policy=(
            draft.controls.run_workspace_cleanup_policy or "manual"
        ),
        run_workspace_max_write_bytes=(
            draft.controls.run_workspace_max_write_bytes or 65536
        ),
        model_name=model_name,
        metadata=_builder_metadata(
            draft,
            builder_target="twf_reference_review_workflow",
        ),
    )


def build_twf_config_profile_explain_workflow_request_from_twf_draft(
    draft: TwfWorkflowRequestDraftCandidate,
    *,
    config_context: Any | None = None,
    config_root: str | None = None,
    environment: str = "local",
    profile: str | None = None,
    ollama_api_base: str | None = None,
) -> TwfConfigProfileExplainWorkflowRequestCandidate:
    """Build the current task workflow config explain request from a draft."""

    _require_workflow(draft, TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME)
    return TwfConfigProfileExplainWorkflowRequestCandidate(
        user_text=draft.turn_input.sanitized_user_text,
        chat_session_id=draft.turn_input.chat_session_id,
        turn_index=draft.turn_input.turn_index,
        history=draft.turn_input.sanitized_history,
        config_context=config_context,
        config_root=config_root,
        environment=environment,
        profile=profile,
        request_live_llm=draft.request_live_llm,
        request_ollama=draft.request_ollama,
        allow_live_llm=draft.allow_live_llm,
        allow_ollama=draft.allow_ollama,
        ollama_api_base=ollama_api_base,
        live_llm_timeout_seconds=draft.live_llm_timeout_seconds,
        operator_approved=draft.operator_approved,
        approval_ref=draft.governance_refs.approval_ref,
        audit_ref=draft.governance_refs.audit_ref,
        sanitized_evidence_ref=draft.governance_refs.sanitized_evidence_ref,
        governance_summary_output_ref=(
            draft.governance_refs.governance_summary_output_ref
        ),
        risk_level="low",
        output_budget=CONFIG_PROFILE_EXPLAIN_DISPLAY_PREVIEW_LIMIT,
        live_gate=_live_gate(draft),
        user_passthrough_parameters=draft.user_passthrough_parameters,
        reference_paths=draft.controls.reference_paths,
        tool_exposure_profile=draft.controls.tool_exposure_profile,
        entrypoint_explicit_args=draft.entrypoint_explicit_args,
        session_args=draft.session_args,
        run_workspace_root=draft.controls.run_workspace_root,
        run_workspace_enabled=draft.controls.run_workspace_enabled,
        run_workspace_retention_policy=(
            draft.controls.run_workspace_retention_policy or "keep"
        ),
        run_workspace_cleanup_policy=(
            draft.controls.run_workspace_cleanup_policy or "manual"
        ),
        run_workspace_max_write_bytes=(
            draft.controls.run_workspace_max_write_bytes or 65536
        ),
        metadata=_builder_metadata(
            draft,
            builder_target="twf_config_profile_explain_workflow",
        ),
    )


def build_twf_run_workspace_evidence_audit_workflow_request_from_twf_draft(
    draft: TwfWorkflowRequestDraftCandidate,
) -> TwfRunWorkspaceEvidenceAuditWorkflowRequestCandidate:
    """Build the current task workflow run workspace audit request from a draft."""

    _require_workflow(draft, TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME)
    return TwfRunWorkspaceEvidenceAuditWorkflowRequestCandidate(
        user_text=draft.turn_input.sanitized_user_text,
        chat_session_id=draft.turn_input.chat_session_id,
        turn_index=draft.turn_input.turn_index,
        history=draft.turn_input.sanitized_history,
        audit_run_workspace_path=draft.controls.audit_run_workspace_path,
        audit_run_workspace_ref=draft.controls.audit_run_workspace_ref,
        audit_run_workspace_root=draft.controls.audit_run_workspace_root,
        audit_focus=draft.controls.audit_focus,
        approval_ref=draft.governance_refs.approval_ref,
        audit_ref=draft.governance_refs.audit_ref,
        sanitized_evidence_ref=draft.governance_refs.sanitized_evidence_ref,
        risk_level="low",
        output_budget=RUN_WORKSPACE_EVIDENCE_AUDIT_DISPLAY_PREVIEW_LIMIT,
        live_gate=_live_gate(draft),
        user_passthrough_parameters=draft.user_passthrough_parameters,
        run_workspace_root=draft.controls.run_workspace_root,
        run_workspace_enabled=draft.controls.run_workspace_enabled,
        run_workspace_retention_policy=(
            draft.controls.run_workspace_retention_policy or "keep"
        ),
        run_workspace_cleanup_policy=(
            draft.controls.run_workspace_cleanup_policy or "manual"
        ),
        run_workspace_max_write_bytes=(
            draft.controls.run_workspace_max_write_bytes or 65536
        ),
        metadata=_builder_metadata(
            draft,
            builder_target="twf_run_workspace_evidence_audit_workflow",
        ),
    )


def _require_workflow(
    draft: TwfWorkflowRequestDraftCandidate,
    workflow_name: str,
) -> None:
    if draft.workflow_name != workflow_name:
        raise ValueError(
            f"expected {workflow_name} draft, got {draft.workflow_name}."
        )


def _live_gate(draft: TwfWorkflowRequestDraftCandidate) -> str:
    if draft.live_model_allowed:
        return "controlled_live"
    return "no_live"


def _builder_metadata(
    draft: TwfWorkflowRequestDraftCandidate,
    *,
    builder_target: str,
) -> dict[str, Any]:
    return {
        "source": "cognition_operation_flows._requests.builder",
        "builder_target": builder_target,
        "task_workflow_request_builder": True,
        "request_draft_status": twf_workflow_request_draft_status_dict(draft),
        "request_draft_metadata": dict(draft.metadata),
        "route_summary": dict(draft.route_summary),
        **dict(draft.route_summary),
    }
