"""Private product-entry request builders."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from cognition_task_workflows._workflows.plan import DEFAULT_PLAN_MODEL_NAME
from cognition_task_workflows._requests.builder import (
    TwfWorkflowRequestCandidate,
    build_twf_workflow_request_from_twf_draft,
)
from cognition_task_workflows._requests.drafts import (
    TwfGovernanceRefsCandidate,
    TwfReferenceWorkspaceControlsCandidate,
    TwfWorkflowRequestDraftCandidate,
    build_twf_config_profile_explain_request_draft,
    build_twf_plan_request_draft,
    build_twf_reference_review_request_draft,
    build_twf_run_workspace_evidence_audit_request_draft,
)


_GOVERNANCE_REF_FIELDS = (
    "approval_ref",
    "audit_ref",
    "sanitized_evidence_ref",
    "governance_summary_output_ref",
    "live_llm_approval_ref",
    "metadata",
)
_REFERENCE_WORKSPACE_CONTROL_FIELDS = (
    "reference_paths",
    "reference_repo_root",
    "external_readonly_evidence_paths",
    "external_readonly_evidence_repo_root",
    "reference_profile_name",
    "tool_exposure_profile",
    "run_workspace_root",
    "run_workspace_enabled",
    "run_workspace_retention_policy",
    "run_workspace_cleanup_policy",
    "run_workspace_max_write_bytes",
    "audit_run_workspace_path",
    "audit_run_workspace_ref",
    "audit_run_workspace_root",
    "audit_focus",
    "metadata",
)


def build_twf_product_entry_plan_request_draft(
    *,
    sanitized_user_text: str,
    chat_session_id: str | None = None,
    turn_index: int | None = None,
    sanitized_history: Sequence[Mapping[str, str]] = (),
    sanitized_previous_display_text: str | None = None,
    governance_refs: Any | Mapping[str, Any] | None = None,
    controls: Any | Mapping[str, Any] | None = None,
    route_summary: Mapping[str, Any] | None = None,
    user_passthrough_parameters: Mapping[str, Any] | None = None,
    operator_approved: bool = False,
    request_live_llm: bool = False,
    request_ollama: bool = False,
    allow_live_llm: bool = False,
    allow_ollama: bool = False,
    live_llm_timeout_seconds: int | None = None,
    live_model_allowed: bool = False,
    metadata: Mapping[str, Any] | None = None,
) -> TwfWorkflowRequestDraftCandidate:
    """Build a plan request draft for product-entry consumers."""

    return build_twf_plan_request_draft(
        sanitized_user_text=sanitized_user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        sanitized_history=sanitized_history,
        sanitized_previous_display_text=sanitized_previous_display_text,
        governance_refs=_twf_product_entry_governance_refs(governance_refs),
        controls=_twf_product_entry_controls(controls),
        route_summary=route_summary,
        user_passthrough_parameters=user_passthrough_parameters,
        operator_approved=operator_approved,
        request_live_llm=request_live_llm,
        request_ollama=request_ollama,
        allow_live_llm=allow_live_llm,
        allow_ollama=allow_ollama,
        live_llm_timeout_seconds=live_llm_timeout_seconds,
        live_model_allowed=live_model_allowed,
        metadata=metadata,
    )


def build_twf_product_entry_reference_review_request_draft(
    *,
    sanitized_user_text: str,
    chat_session_id: str | None = None,
    turn_index: int | None = None,
    sanitized_history: Sequence[Mapping[str, str]] = (),
    governance_refs: Any | Mapping[str, Any] | None = None,
    controls: Any | Mapping[str, Any] | None = None,
    route_summary: Mapping[str, Any] | None = None,
    user_passthrough_parameters: Mapping[str, Any] | None = None,
    operator_approved: bool = False,
    request_live_llm: bool = False,
    request_ollama: bool = False,
    allow_live_llm: bool = False,
    allow_ollama: bool = False,
    live_llm_timeout_seconds: int | None = None,
    live_model_allowed: bool = False,
    metadata: Mapping[str, Any] | None = None,
) -> TwfWorkflowRequestDraftCandidate:
    """Build a reference-review request draft for product-entry consumers."""

    return build_twf_reference_review_request_draft(
        sanitized_user_text=sanitized_user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        sanitized_history=sanitized_history,
        governance_refs=_twf_product_entry_governance_refs(governance_refs),
        controls=_twf_product_entry_controls(controls),
        route_summary=route_summary,
        user_passthrough_parameters=user_passthrough_parameters,
        operator_approved=operator_approved,
        request_live_llm=request_live_llm,
        request_ollama=request_ollama,
        allow_live_llm=allow_live_llm,
        allow_ollama=allow_ollama,
        live_llm_timeout_seconds=live_llm_timeout_seconds,
        live_model_allowed=live_model_allowed,
        metadata=metadata,
    )


def build_twf_product_entry_config_profile_explain_request_draft(
    *,
    sanitized_user_text: str,
    chat_session_id: str | None = None,
    turn_index: int | None = None,
    sanitized_history: Sequence[Mapping[str, str]] = (),
    governance_refs: Any | Mapping[str, Any] | None = None,
    controls: Any | Mapping[str, Any] | None = None,
    route_summary: Mapping[str, Any] | None = None,
    entrypoint_explicit_args: Mapping[str, Any] | None = None,
    session_args: Mapping[str, Any] | None = None,
    user_passthrough_parameters: Mapping[str, Any] | None = None,
    operator_approved: bool = False,
    request_live_llm: bool = False,
    request_ollama: bool = False,
    allow_live_llm: bool = False,
    allow_ollama: bool = False,
    live_llm_timeout_seconds: int | None = None,
    live_model_allowed: bool = False,
    metadata: Mapping[str, Any] | None = None,
) -> TwfWorkflowRequestDraftCandidate:
    """Build a config-profile explanation draft for product-entry consumers."""

    return build_twf_config_profile_explain_request_draft(
        sanitized_user_text=sanitized_user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        sanitized_history=sanitized_history,
        governance_refs=_twf_product_entry_governance_refs(governance_refs),
        controls=_twf_product_entry_controls(controls),
        route_summary=route_summary,
        entrypoint_explicit_args=entrypoint_explicit_args,
        session_args=session_args,
        user_passthrough_parameters=user_passthrough_parameters,
        operator_approved=operator_approved,
        request_live_llm=request_live_llm,
        request_ollama=request_ollama,
        allow_live_llm=allow_live_llm,
        allow_ollama=allow_ollama,
        live_llm_timeout_seconds=live_llm_timeout_seconds,
        live_model_allowed=live_model_allowed,
        metadata=metadata,
    )


def build_twf_product_entry_run_workspace_evidence_audit_request_draft(
    *,
    sanitized_user_text: str,
    chat_session_id: str | None = None,
    turn_index: int | None = None,
    sanitized_history: Sequence[Mapping[str, str]] = (),
    governance_refs: Any | Mapping[str, Any] | None = None,
    controls: Any | Mapping[str, Any] | None = None,
    route_summary: Mapping[str, Any] | None = None,
    user_passthrough_parameters: Mapping[str, Any] | None = None,
    operator_approved: bool = False,
    request_live_llm: bool = False,
    request_ollama: bool = False,
    allow_live_llm: bool = False,
    allow_ollama: bool = False,
    live_llm_timeout_seconds: int | None = None,
    live_model_allowed: bool = False,
    metadata: Mapping[str, Any] | None = None,
) -> TwfWorkflowRequestDraftCandidate:
    """Build a run-workspace evidence-audit draft for product-entry consumers."""

    return build_twf_run_workspace_evidence_audit_request_draft(
        sanitized_user_text=sanitized_user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        sanitized_history=sanitized_history,
        governance_refs=_twf_product_entry_governance_refs(governance_refs),
        controls=_twf_product_entry_controls(controls),
        route_summary=route_summary,
        user_passthrough_parameters=user_passthrough_parameters,
        operator_approved=operator_approved,
        request_live_llm=request_live_llm,
        request_ollama=request_ollama,
        allow_live_llm=allow_live_llm,
        allow_ollama=allow_ollama,
        live_llm_timeout_seconds=live_llm_timeout_seconds,
        live_model_allowed=live_model_allowed,
        metadata=metadata,
    )


def build_twf_product_entry_workflow_request(
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
    """Build an executable TWF request from a product-entry draft."""

    return build_twf_workflow_request_from_twf_draft(
        draft,
        llm_invocation_service=llm_invocation_service,
        config_context=config_context,
        config_root=config_root,
        environment=environment,
        profile=profile,
        ollama_api_base=ollama_api_base,
        reference_profile_config=reference_profile_config,
        reference_session_args=reference_session_args,
        reference_entrypoint_explicit_args=reference_entrypoint_explicit_args,
        model_name=model_name,
    )


def _twf_product_entry_governance_refs(
    value: Any | Mapping[str, Any] | None,
) -> TwfGovernanceRefsCandidate | None:
    if value is None or isinstance(value, TwfGovernanceRefsCandidate):
        return value
    return TwfGovernanceRefsCandidate(
        **_object_values(value, _GOVERNANCE_REF_FIELDS)
    )


def _twf_product_entry_controls(
    value: Any | Mapping[str, Any] | None,
) -> TwfReferenceWorkspaceControlsCandidate | None:
    if value is None or isinstance(value, TwfReferenceWorkspaceControlsCandidate):
        return value
    return TwfReferenceWorkspaceControlsCandidate(
        **_object_values(value, _REFERENCE_WORKSPACE_CONTROL_FIELDS)
    )


def _object_values(value: Any, field_names: Sequence[str]) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    result: dict[str, Any] = {}
    for field_name in field_names:
        if hasattr(value, field_name):
            result[field_name] = getattr(value, field_name)
    return result


__all__ = [
    "build_twf_product_entry_config_profile_explain_request_draft",
    "build_twf_product_entry_plan_request_draft",
    "build_twf_product_entry_reference_review_request_draft",
    "build_twf_product_entry_run_workspace_evidence_audit_request_draft",
    "build_twf_product_entry_workflow_request",
]
