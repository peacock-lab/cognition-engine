"""Chat status terminal and JSON presenters for the Cognition System CLI."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from typing import Any

from cognition_cli.chat.status_payload import _chat_status_payload


def _chat_status_command(line: str) -> bool:
    return line in {"/status", "/status --json", "/status json", "/status-json"}


def _chat_status_json_command(line: str) -> bool:
    return line in {"/status --json", "/status json", "/status-json"}


def _chat_status_text(
    args: argparse.Namespace,
    chat_session_id: str,
    turn_count: int,
    *,
    latest_plan_snapshot: Any | None = None,
    status_summary_artifact_ref: str | None = None,
) -> str:
    payload = _chat_status_payload(
        args,
        chat_session_id,
        turn_count,
        latest_plan_snapshot=latest_plan_snapshot,
        status_summary_artifact_ref=status_summary_artifact_ref,
    )
    tools = payload["tools"]
    workspace = payload["workspace"]
    skills = payload["skills"]
    skill_projection = skills.get("capability_projection") or {}
    latest = payload["latest_plan"]
    return "\n".join(
        [
            f"session: {payload['chat_session_id']}",
            f"turn_count: {payload['turn_count']}",
            f"history_limit: {payload['history_limit']}",
            f"live_llm_requested: {str(payload['live_llm_requested']).lower()}",
            f"ollama_requested: {str(payload['ollama_requested']).lower()}",
            f"reference_path_count: {payload['reference_path_count']}",
            "external_readonly_evidence_path_count: "
            f"{payload['external_readonly_evidence_path_count']}",
            "run_workspace_requested: "
            f"{str(payload['run_workspace_requested']).lower()}",
            f"tool_profile: {tools['profile_name']}",
            f"tool_exposure_status: {tools['status']}",
            "exposed_tools: "
            + _chat_status_csv(tools.get("exposed_tool_names") or []),
            "blocked_tools: "
            + _chat_status_csv(tools.get("blocked_tool_names") or []),
            f"reference_reader_status: {tools['reference_reader_status']}",
            "tool_config_precedence: "
            + _chat_status_csv(tools.get("config_precedence") or []),
            f"run_workspace_enabled: {str(workspace['enabled']).lower()}",
            f"run_workspace_root: {workspace['root'] or 'none'}",
            f"run_workspace_retention_policy: {workspace['retention_policy']}",
            f"run_workspace_cleanup_policy: {workspace['cleanup_policy']}",
            f"run_workspace_max_write_bytes: {workspace['max_write_bytes']}",
            f"skills_status: {skills['status']}",
            "skills_metadata_view_available: "
            f"{str(skills['metadata_view_available']).lower()}",
            "skills_runtime_integrated: "
            f"{str(skills['runtime_integrated']).lower()}",
            "skill_toolset_runtime_enabled: "
            f"{str(skills['skill_toolset_runtime_enabled']).lower()}",
            "skill_registry_runtime_enabled: "
            f"{str(skills['skill_registry_runtime_enabled']).lower()}",
            "skills_capability_projection_status: "
            + str(skill_projection.get("status") or "not_configured"),
            "skills_capability_projection_count: "
            + str(skill_projection.get("projection_count") or 0),
            "skills_workflow_slot_reference_count: "
            + str(skill_projection.get("workflow_slot_reference_count") or 0),
            "skills_active_slot_reference_count: "
            + str(skill_projection.get("active_slot_reference_count") or 0),
            "skills_projection_runtime_enabled: "
            + str(skill_projection.get("runtime_enabled", False)).lower(),
            "skills_projection_public_schema_enabled: "
            + str(skill_projection.get("public_schema_enabled", False)).lower(),
            "latest_plan_status: " + str(latest["status"]),
            "latest_product_gateway_route_status: "
            + str(latest["product_gateway_route_projection"]["status"]),
            "latest_product_gateway_route_source: "
            + str(latest["product_gateway_route_projection"]["source"] or "none"),
            "latest_product_gateway_route_workflow_name: "
            + str(
                latest["product_gateway_route_projection"]["workflow_name"] or "none"
            ),
            "latest_product_gateway_route_execution_enabled: "
            + str(
                latest["product_gateway_route_projection"][
                    "workflow_execution_enabled"
                ]
            ).lower(),
            "latest_reference_context_status: "
            + str(latest["reference_context_status"]),
            "latest_reference_evidence_ref_count: "
            + str(latest["reference_evidence_ref_count"]),
            "latest_workspace_created: "
            + str(latest["workspace_created"]).lower(),
            "latest_workspace_ref: " + str(latest["workspace_ref"] or "none"),
            "latest_workspace_artifact_ref_count: "
            + str(latest["workspace_artifact_ref_count"]),
            "latest_workspace_result_ref_count: "
            + str(latest["workspace_result_ref_count"]),
            "status_summary_artifact_ref: "
            + str(payload["status_summary_artifact_ref"] or "none"),
        ]
    )


def _chat_status_json_text(
    args: argparse.Namespace,
    chat_session_id: str,
    turn_count: int,
    *,
    latest_plan_snapshot: Any | None = None,
    status_summary_artifact_ref: str | None = None,
) -> str:
    payload = _chat_status_payload(
        args,
        chat_session_id,
        turn_count,
        latest_plan_snapshot=latest_plan_snapshot,
        status_summary_artifact_ref=status_summary_artifact_ref,
    )
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _chat_status_csv(values: Sequence[Any]) -> str:
    normalized = [str(value) for value in values if str(value)]
    return ", ".join(normalized) if normalized else "none"
