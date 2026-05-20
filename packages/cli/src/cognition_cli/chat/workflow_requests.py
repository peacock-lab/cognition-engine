"""Chat workflow request assembly for the Cognition System CLI."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from typing import Any

from cognition_cli.chat.controls import (
    _chat_plan_control_kwargs,
)
from cognition_cli.chat.status_payload import (
    _chat_task_route_metadata,
)
from cognition_cli.services.runtime import (
    _full_controlled_live_args,
)
from contract_core.product_gateway_cli import (
    PRODUCT_GATEWAY_CLI_TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
    PRODUCT_GATEWAY_CLI_TWF_PLAN_WORKFLOW_NAME,
    PRODUCT_GATEWAY_CLI_TWF_REFERENCE_REVIEW_WORKFLOW_NAME,
    PRODUCT_GATEWAY_CLI_TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
    ProductGatewayCliTwfGovernanceRefsSchema,
    ProductGatewayCliTwfReferenceWorkspaceControlsSchema,
    ProductGatewayCliTwfRequestDraftInputSchema,
)


def _chat_plan_workflow_request_draft_input(
    *,
    args: argparse.Namespace,
    user_text: str,
    chat_session_id: str,
    turn_index: int,
    history: Sequence[Mapping[str, str]],
    previous_plan_text: str | None,
    route: Any | None = None,
) -> ProductGatewayCliTwfRequestDraftInputSchema:
    live_model_allowed = _full_controlled_live_args(args)
    plan_controls = _chat_plan_control_kwargs(args)
    return ProductGatewayCliTwfRequestDraftInputSchema(
        workflow_name=PRODUCT_GATEWAY_CLI_TWF_PLAN_WORKFLOW_NAME,
        sanitized_user_text=user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        sanitized_history=tuple(history),
        sanitized_previous_display_text=previous_plan_text,
        governance_refs=_chat_twf_governance_refs(args),
        controls=_chat_twf_reference_workspace_controls(plan_controls),
        route_summary=_chat_task_route_metadata(route),
        user_passthrough_parameters={},
        operator_approved=args.operator_approved,
        request_live_llm=args.request_live_llm,
        request_ollama=args.request_ollama,
        allow_live_llm=args.allow_live_llm,
        allow_ollama=args.allow_ollama,
        live_llm_timeout_seconds=args.live_llm_timeout_seconds,
        live_model_allowed=live_model_allowed,
        metadata=_chat_twf_request_draft_metadata(plan_controls),
    )


def _chat_reference_review_workflow_request_draft_input(
    *,
    args: argparse.Namespace,
    user_text: str,
    chat_session_id: str,
    turn_index: int,
    history: Sequence[Mapping[str, str]],
    route: Any | None = None,
) -> ProductGatewayCliTwfRequestDraftInputSchema:
    live_model_allowed = _full_controlled_live_args(args)
    review_controls = _chat_plan_control_kwargs(args)
    return ProductGatewayCliTwfRequestDraftInputSchema(
        workflow_name=PRODUCT_GATEWAY_CLI_TWF_REFERENCE_REVIEW_WORKFLOW_NAME,
        sanitized_user_text=user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        sanitized_history=tuple(history),
        governance_refs=_chat_twf_governance_refs(args),
        controls=_chat_twf_reference_workspace_controls(review_controls),
        route_summary=_chat_task_route_metadata(route),
        user_passthrough_parameters={},
        operator_approved=args.operator_approved,
        request_live_llm=args.request_live_llm,
        request_ollama=args.request_ollama,
        allow_live_llm=args.allow_live_llm,
        allow_ollama=args.allow_ollama,
        live_llm_timeout_seconds=args.live_llm_timeout_seconds,
        live_model_allowed=live_model_allowed,
        metadata=_chat_twf_request_draft_metadata(review_controls),
    )


def _chat_config_profile_explain_workflow_request_draft_input(
    *,
    args: argparse.Namespace,
    user_text: str,
    chat_session_id: str,
    turn_index: int,
    history: Sequence[Mapping[str, str]],
    route: Any | None = None,
) -> ProductGatewayCliTwfRequestDraftInputSchema:
    plan_controls = _chat_plan_control_kwargs(args)
    return ProductGatewayCliTwfRequestDraftInputSchema(
        workflow_name=PRODUCT_GATEWAY_CLI_TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
        sanitized_user_text=user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        sanitized_history=tuple(history),
        governance_refs=_chat_twf_governance_refs(args),
        controls=_chat_twf_reference_workspace_controls(
            plan_controls,
            tool_exposure_profile=args.tool_exposure_profile,
        ),
        route_summary=_chat_task_route_metadata(route),
        entrypoint_explicit_args=_chat_config_profile_entrypoint_explicit_args(args),
        session_args={},
        user_passthrough_parameters={},
        operator_approved=args.operator_approved,
        request_live_llm=args.request_live_llm,
        request_ollama=args.request_ollama,
        allow_live_llm=args.allow_live_llm,
        allow_ollama=args.allow_ollama,
        live_llm_timeout_seconds=args.live_llm_timeout_seconds,
        live_model_allowed=False,
        metadata=_chat_twf_request_draft_metadata(plan_controls),
    )


def _chat_run_workspace_evidence_audit_workflow_request_draft_input(
    *,
    args: argparse.Namespace,
    user_text: str,
    chat_session_id: str,
    turn_index: int,
    history: Sequence[Mapping[str, str]],
    route: Any | None = None,
) -> ProductGatewayCliTwfRequestDraftInputSchema:
    plan_controls = _chat_plan_control_kwargs(args)
    return ProductGatewayCliTwfRequestDraftInputSchema(
        workflow_name=(
            PRODUCT_GATEWAY_CLI_TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME
        ),
        sanitized_user_text=user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        sanitized_history=tuple(history),
        governance_refs=_chat_twf_governance_refs(args),
        controls=_chat_twf_reference_workspace_controls(
            plan_controls,
            audit_run_workspace_path=(
                str(args.audit_run_workspace_path)
                if args.audit_run_workspace_path is not None
                else None
            ),
            audit_run_workspace_ref=args.audit_run_workspace_ref,
            audit_run_workspace_root=(
                str(args.audit_run_workspace_root)
                if args.audit_run_workspace_root is not None
                else None
            ),
            audit_focus=tuple(args.audit_focus),
        ),
        route_summary=_chat_task_route_metadata(route),
        user_passthrough_parameters={},
        operator_approved=args.operator_approved,
        request_live_llm=args.request_live_llm,
        request_ollama=args.request_ollama,
        allow_live_llm=args.allow_live_llm,
        allow_ollama=args.allow_ollama,
        live_llm_timeout_seconds=args.live_llm_timeout_seconds,
        live_model_allowed=False,
        metadata={
            **_chat_twf_request_draft_metadata(plan_controls),
            "governance_summary_output_ref_present": bool(
                args.governance_summary_output_ref
            ),
        },
    )


def _chat_twf_governance_refs(
    args: argparse.Namespace,
) -> ProductGatewayCliTwfGovernanceRefsSchema:
    return ProductGatewayCliTwfGovernanceRefsSchema(
        approval_ref=args.approval_ref,
        audit_ref=args.audit_ref,
        sanitized_evidence_ref=args.sanitized_evidence_ref,
        governance_summary_output_ref=args.governance_summary_output_ref,
        live_llm_approval_ref=args.live_llm_approval_ref,
    )


def _chat_twf_reference_workspace_controls(
    plan_controls: Mapping[str, Any],
    *,
    tool_exposure_profile: str | None = None,
    audit_run_workspace_path: str | None = None,
    audit_run_workspace_ref: str | None = None,
    audit_run_workspace_root: str | None = None,
    audit_focus: Sequence[str] = (),
) -> ProductGatewayCliTwfReferenceWorkspaceControlsSchema:
    return ProductGatewayCliTwfReferenceWorkspaceControlsSchema(
        reference_paths=tuple(plan_controls["reference_paths"]),
        reference_repo_root=plan_controls["reference_repo_root"],
        external_readonly_evidence_paths=tuple(
            plan_controls["external_readonly_evidence_paths"]
        ),
        external_readonly_evidence_repo_root=plan_controls[
            "external_readonly_evidence_repo_root"
        ],
        reference_profile_name=plan_controls["reference_profile_name"],
        tool_exposure_profile=tool_exposure_profile,
        run_workspace_root=plan_controls["run_workspace_root"],
        run_workspace_enabled=bool(plan_controls["run_workspace_enabled"]),
        run_workspace_retention_policy=plan_controls[
            "run_workspace_retention_policy"
        ],
        run_workspace_cleanup_policy=plan_controls["run_workspace_cleanup_policy"],
        run_workspace_max_write_bytes=plan_controls["run_workspace_max_write_bytes"],
        audit_run_workspace_path=audit_run_workspace_path,
        audit_run_workspace_ref=audit_run_workspace_ref,
        audit_run_workspace_root=audit_run_workspace_root,
        audit_focus=tuple(audit_focus),
    )


def _chat_twf_request_draft_metadata(
    plan_controls: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "source": "cognition_cli.chat.workflow_requests",
        "chat_entry_is_trigger_only": True,
        **dict(plan_controls.get("metadata") or {}),
    }


def _chat_config_profile_entrypoint_explicit_args(
    args: argparse.Namespace,
) -> dict[str, Any]:
    entrypoint_explicit_args: dict[str, Any] = {}
    if args.tool_exposure_profile:
        entrypoint_explicit_args["tool_exposure_profile"] = args.tool_exposure_profile
    if args.enable_run_workspace:
        entrypoint_explicit_args["enable_run_workspace"] = True
    if args.run_workspace_root is not None:
        entrypoint_explicit_args["run_workspace_root"] = str(args.run_workspace_root)
    if args.run_workspace_retention_policy is not None:
        entrypoint_explicit_args["run_workspace_retention_policy"] = (
            args.run_workspace_retention_policy
        )
    if args.run_workspace_cleanup_policy is not None:
        entrypoint_explicit_args["run_workspace_cleanup_policy"] = (
            args.run_workspace_cleanup_policy
        )
    if args.run_workspace_max_write_bytes is not None:
        entrypoint_explicit_args["run_workspace_max_write_bytes"] = (
            args.run_workspace_max_write_bytes
        )
    if args.request_live_llm:
        entrypoint_explicit_args["request_live_llm"] = True
    if args.request_ollama:
        entrypoint_explicit_args["request_ollama"] = True
    if args.allow_live_llm:
        entrypoint_explicit_args["allow_live_llm"] = True
    if args.allow_ollama:
        entrypoint_explicit_args["allow_ollama"] = True
    if args.ollama_api_base:
        entrypoint_explicit_args["ollama_api_base"] = args.ollama_api_base
    if args.live_llm_timeout_seconds is not None:
        entrypoint_explicit_args["live_llm_timeout_seconds"] = (
            args.live_llm_timeout_seconds
        )
    return entrypoint_explicit_args
