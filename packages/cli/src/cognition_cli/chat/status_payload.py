"""Chat status payload assembly for the Cognition System CLI."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from typing import Any

from cognition_cli.chat.controls import (
    _chat_plan_control_kwargs,
    _chat_plan_workspace_args_requested,
)
from cognition_cli.constants import PRODUCT_NAME
from product_gateway.cli_surface import (
    build_cli_operation_flow_latest_plan_status,
    build_cli_operation_flow_skill_capability_projection_status,
    build_cli_operation_flow_tools_status,
)


def _chat_operation_route_metadata(
    route: Any | None,
) -> dict[str, Any]:
    return {
        "operation_flow_route": _chat_operation_route_status(route) if route else None,
        "product_gateway_route_projection": (
            _chat_product_gateway_route_projection_summary(route)
            if route
            else None
        ),
    }


def _chat_operation_route_status(route: Any) -> dict[str, Any]:
    metadata = getattr(route, "metadata", {})
    if isinstance(metadata, Mapping):
        route_status = metadata.get("route_status")
        if isinstance(route_status, Mapping):
            return dict(route_status)
    return {
        "matched": bool(getattr(route, "matched", False)),
        "workflow_name": getattr(route, "workflow_name", None),
        "workflow_version": getattr(route, "workflow_version", None),
        "task_kind": getattr(route, "task_kind", None),
        "route_reason": getattr(route, "route_reason", None),
        "confidence": getattr(route, "confidence", "none"),
        "source": getattr(route, "source", None),
        "turn_index": getattr(route, "turn_index", None),
        "requires_live_model": bool(getattr(route, "requires_live_model", False)),
        "requires_tools": list(getattr(route, "requires_tools", ()) or ()),
        "requires_workspace": bool(getattr(route, "requires_workspace", False)),
        "blocking_reasons": list(getattr(route, "blocking_reasons", ()) or ()),
        "warnings": list(getattr(route, "warnings", ()) or ()),
    }


def _chat_product_gateway_route_projection_summary(
    route: Any | None,
) -> dict[str, Any]:
    if route is None:
        return _chat_product_gateway_route_projection_not_run()
    projection = _chat_route_projection_payload(route)
    if projection is None:
        return {
            **_chat_product_gateway_route_projection_not_run(),
            "status": "not_available",
        }
    projection_metadata = projection.get("metadata")
    if not isinstance(projection_metadata, Mapping):
        projection_metadata = {}
    return {
        "status": "matched" if projection.get("matched") else "not_matched",
        "entry_kind": projection.get("entry_kind"),
        "execution_mode": projection.get("execution_mode"),
        "source": projection_metadata.get("source") or projection.get("source"),
        "workflow_name": projection.get("workflow_name"),
        "workflow_version": projection.get("workflow_version"),
        "task_kind": projection.get("task_kind"),
        "route_reason": projection.get("route_reason"),
        "confidence": projection.get("confidence"),
        "requires_live_model": bool(projection.get("requires_live_model")),
        "requires_workspace": bool(projection.get("requires_workspace")),
        "requires_tools": list(projection.get("requires_tools") or []),
        "registry_workflow_count": projection.get("registry_workflow_count"),
        "route_only": bool(projection_metadata.get("route_only")),
        "workflow_execution_enabled": bool(
            projection_metadata.get("workflow_execution_enabled")
        ),
    }


def _chat_route_projection_payload(route: Any) -> Mapping[str, Any] | None:
    metadata = getattr(route, "metadata", {})
    if isinstance(metadata, Mapping):
        projection = metadata.get("product_gateway_route_projection")
        if isinstance(projection, Mapping):
            return projection
    model_dump = getattr(route, "model_dump", None)
    if callable(model_dump):
        projection = model_dump(mode="json")
        if isinstance(projection, Mapping):
            return projection
    return None


def _chat_product_gateway_route_projection_not_run() -> dict[str, Any]:
    return {
        "status": "not_run",
        "entry_kind": None,
        "execution_mode": None,
        "source": None,
        "workflow_name": None,
        "workflow_version": None,
        "task_kind": None,
        "route_reason": None,
        "confidence": "none",
        "requires_live_model": False,
        "requires_workspace": False,
        "requires_tools": [],
        "registry_workflow_count": 0,
        "route_only": False,
        "workflow_execution_enabled": False,
    }


def _chat_status_payload(
    args: argparse.Namespace,
    chat_session_id: str,
    turn_count: int,
    *,
    latest_plan_snapshot: Any | None = None,
    status_summary_artifact_ref: str | None = None,
) -> dict[str, Any]:
    control_status = _chat_control_status(args, latest_plan_snapshot)
    return {
        "product": PRODUCT_NAME,
        "command": "cognition chat /status",
        "chat_session_id": chat_session_id,
        "turn_count": turn_count,
        "history_limit": args.history_limit,
        "live_llm_requested": args.request_live_llm,
        "ollama_requested": args.request_ollama,
        "reference_path_count": len(args.reference_paths),
        "external_readonly_evidence_path_count": len(
            getattr(args, "external_readonly_evidence_paths", ())
        ),
        "run_workspace_requested": _chat_plan_workspace_args_requested(args),
        "tools": control_status["tools"],
        "workspace": control_status["workspace"],
        "skills": control_status["skills"],
        "latest_plan": control_status["latest_plan"],
        "status_summary_artifact_ref": status_summary_artifact_ref,
    }


def _chat_control_status(
    args: argparse.Namespace,
    latest_plan_snapshot: Any | None,
) -> dict[str, Any]:
    plan_controls = _chat_plan_control_kwargs(args)
    return {
        "tools": _chat_tools_status(
            profile_name=plan_controls["reference_profile_name"],
            profile_config=plan_controls["reference_profile_config"],
            repo_root=plan_controls["reference_repo_root"],
            entrypoint_explicit_args=plan_controls["reference_entrypoint_explicit_args"],
            operator_approved=args.operator_approved,
            approval_ref=args.approval_ref,
        ),
        "workspace": _chat_workspace_status(plan_controls),
        "skills": _chat_skills_status(),
        "latest_plan": _chat_latest_plan_status(latest_plan_snapshot),
    }


def _chat_tools_status(
    *,
    profile_name: str,
    profile_config: Mapping[str, Any] | None,
    repo_root: str,
    entrypoint_explicit_args: Mapping[str, Any],
    operator_approved: bool,
    approval_ref: str | None,
) -> dict[str, Any]:
    return build_cli_operation_flow_tools_status(
        profile_name=profile_name,
        profile_config=profile_config,
        repo_root=repo_root,
        entrypoint_explicit_args=entrypoint_explicit_args,
        operator_approved=operator_approved,
        approval_ref=approval_ref,
    )


def _chat_workspace_status(plan_controls: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "enabled": bool(plan_controls["run_workspace_enabled"]),
        "root": plan_controls["run_workspace_root"],
        "retention_policy": plan_controls["run_workspace_retention_policy"],
        "cleanup_policy": plan_controls["run_workspace_cleanup_policy"],
        "max_write_bytes": plan_controls["run_workspace_max_write_bytes"],
    }


def _chat_skills_status() -> dict[str, Any]:
    try:
        from config_contexts import SkillCandidateFlags, SkillMetadataViewCandidate

        flags = SkillCandidateFlags()
        metadata_view_available = SkillMetadataViewCandidate is not None
    except Exception:
        return {
            "status": "candidate_view_unavailable",
            "metadata_view_available": False,
            "runtime_integrated": False,
            "skill_toolset_runtime_enabled": False,
            "skill_registry_runtime_enabled": False,
            "real_skill_loading_enabled": False,
            "capability_projection": _chat_skill_capability_projection_status(),
        }
    return {
        "status": "candidate_only_frozen",
        "metadata_view_available": metadata_view_available,
        "runtime_integrated": False,
        "skill_toolset_runtime_enabled": flags.skill_toolset_runtime_enabled,
        "skill_registry_runtime_enabled": flags.skill_registry_runtime_enabled,
        "real_skill_loading_enabled": False,
        "capability_projection": _chat_skill_capability_projection_status(),
    }


def _chat_skill_capability_projection_status() -> dict[str, Any]:
    return build_cli_operation_flow_skill_capability_projection_status()


def _chat_latest_plan_status(
    latest_plan_snapshot: Any | None,
) -> dict[str, Any]:
    return build_cli_operation_flow_latest_plan_status(latest_plan_snapshot)
