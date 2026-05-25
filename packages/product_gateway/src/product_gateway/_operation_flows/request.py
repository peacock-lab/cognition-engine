"""Product gateway request-draft API for OperationFlow operation flows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from cognition_operation_flows.product_entry_service import (
    OPERATION_FLOW_PRODUCT_ENTRY_CONFIG_PROFILE_EXPLAIN_FLOW_NAME,
    OPERATION_FLOW_PRODUCT_ENTRY_PLAN_FLOW_NAME,
    OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_REVIEW_FLOW_NAME,
    OPERATION_FLOW_PRODUCT_ENTRY_RUN_WORKSPACE_EVIDENCE_AUDIT_FLOW_NAME,
    build_operation_flow_product_entry_config_profile_explain_request_draft,
    build_operation_flow_product_entry_plan_request_draft,
    build_operation_flow_product_entry_reference_review_request_draft,
    build_operation_flow_product_entry_run_workspace_evidence_audit_request_draft,
)


INTERNAL_OPERATION_FLOW_PLAN_WORKFLOW_NAME = OPERATION_FLOW_PRODUCT_ENTRY_PLAN_FLOW_NAME
INTERNAL_OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME = (
    OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_REVIEW_FLOW_NAME
)
INTERNAL_OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME = (
    OPERATION_FLOW_PRODUCT_ENTRY_CONFIG_PROFILE_EXPLAIN_FLOW_NAME
)
INTERNAL_OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME = (
    OPERATION_FLOW_PRODUCT_ENTRY_RUN_WORKSPACE_EVIDENCE_AUDIT_FLOW_NAME
)


@dataclass(frozen=True)
class InternalOperationFlowGovernanceRefs:
    """Product-gateway refs carried into a operation flow request draft."""

    approval_ref: str | None = None
    audit_ref: str | None = None
    sanitized_evidence_ref: str | None = None
    governance_summary_output_ref: str | None = None
    live_llm_approval_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InternalOperationFlowReferenceWorkspaceControls:
    """Product-gateway reference and workspace controls for operation flows."""

    reference_paths: tuple[str, ...] = ()
    reference_repo_root: str | None = None
    external_readonly_evidence_paths: tuple[str, ...] = ()
    external_readonly_evidence_repo_root: str | None = None
    reference_profile_name: str | None = None
    tool_exposure_profile: str | None = None
    run_workspace_root: str | None = None
    run_workspace_enabled: bool = False
    run_workspace_retention_policy: str | None = None
    run_workspace_cleanup_policy: str | None = None
    run_workspace_max_write_bytes: int | None = None
    audit_run_workspace_path: str | None = None
    audit_run_workspace_ref: str | None = None
    audit_run_workspace_root: str | None = None
    audit_focus: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


def build_internal_operation_flow_plan_request_draft(
    *,
    sanitized_user_text: str,
    chat_session_id: str | None = None,
    turn_index: int | None = None,
    sanitized_history: Sequence[Mapping[str, str]] = (),
    sanitized_previous_display_text: str | None = None,
    governance_refs: InternalOperationFlowGovernanceRefs | Mapping[str, Any] | None = None,
    controls: InternalOperationFlowReferenceWorkspaceControls
    | Mapping[str, Any]
    | None = None,
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
) -> Any:
    """Build a plan workflow request draft behind the product gateway API."""

    return build_operation_flow_product_entry_plan_request_draft(
        sanitized_user_text=sanitized_user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        sanitized_history=sanitized_history,
        sanitized_previous_display_text=sanitized_previous_display_text,
        governance_refs=governance_refs,
        controls=controls,
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


def build_internal_operation_flow_reference_review_request_draft(
    *,
    sanitized_user_text: str,
    chat_session_id: str | None = None,
    turn_index: int | None = None,
    sanitized_history: Sequence[Mapping[str, str]] = (),
    governance_refs: InternalOperationFlowGovernanceRefs | Mapping[str, Any] | None = None,
    controls: InternalOperationFlowReferenceWorkspaceControls
    | Mapping[str, Any]
    | None = None,
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
) -> Any:
    """Build a reference-review workflow request draft."""

    return build_operation_flow_product_entry_reference_review_request_draft(
        sanitized_user_text=sanitized_user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        sanitized_history=sanitized_history,
        governance_refs=governance_refs,
        controls=controls,
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


def build_internal_operation_flow_config_profile_explain_request_draft(
    *,
    sanitized_user_text: str,
    chat_session_id: str | None = None,
    turn_index: int | None = None,
    sanitized_history: Sequence[Mapping[str, str]] = (),
    governance_refs: InternalOperationFlowGovernanceRefs | Mapping[str, Any] | None = None,
    controls: InternalOperationFlowReferenceWorkspaceControls
    | Mapping[str, Any]
    | None = None,
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
) -> Any:
    """Build a config-profile explanation workflow request draft."""

    return build_operation_flow_product_entry_config_profile_explain_request_draft(
        sanitized_user_text=sanitized_user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        sanitized_history=sanitized_history,
        governance_refs=governance_refs,
        controls=controls,
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


def build_internal_operation_flow_run_workspace_evidence_audit_request_draft(
    *,
    sanitized_user_text: str,
    chat_session_id: str | None = None,
    turn_index: int | None = None,
    sanitized_history: Sequence[Mapping[str, str]] = (),
    governance_refs: InternalOperationFlowGovernanceRefs | Mapping[str, Any] | None = None,
    controls: InternalOperationFlowReferenceWorkspaceControls
    | Mapping[str, Any]
    | None = None,
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
) -> Any:
    """Build a run-workspace evidence-audit workflow request draft."""

    return build_operation_flow_product_entry_run_workspace_evidence_audit_request_draft(
        sanitized_user_text=sanitized_user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        sanitized_history=sanitized_history,
        governance_refs=governance_refs,
        controls=controls,
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


__all__ = [
    "INTERNAL_OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME",
    "INTERNAL_OPERATION_FLOW_PLAN_WORKFLOW_NAME",
    "INTERNAL_OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME",
    "INTERNAL_OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME",
    "InternalOperationFlowGovernanceRefs",
    "InternalOperationFlowReferenceWorkspaceControls",
    "build_internal_operation_flow_config_profile_explain_request_draft",
    "build_internal_operation_flow_plan_request_draft",
    "build_internal_operation_flow_reference_review_request_draft",
    "build_internal_operation_flow_run_workspace_evidence_audit_request_draft",
]
