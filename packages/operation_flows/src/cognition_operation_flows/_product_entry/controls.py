"""Private product-entry controls implementation."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from cognition_operation_flows._product_entry.types import (
    OperationFlowProductEntryReferenceReaderPolicyCandidate,
    OperationFlowProductEntryToolExposureResolutionCandidate,
)
from cognition_operation_flows._skills.capability_projection import (
    build_default_operation_flow_skill_capability_projection_status_summary,
    operation_flow_skill_projection_status_summary_status_dict,
)
from cognition_operation_flows._tools.exposure_profile import (
    resolve_operation_flow_tool_exposure_profile,
    operation_flow_tool_exposure_profile_status_dict,
)
from cognition_operation_flows._tools.loading_validation import (
    operation_flow_tool_loading_gate_status_dict,
    validate_operation_flow_tool_loading_gate,
)


def resolve_operation_flow_product_entry_tool_exposure_profile(
    *,
    profile_name: str,
    profile_config: Mapping[str, Any] | None = None,
    repo_root: str | Path | None = None,
    entrypoint_explicit_args: Mapping[str, Any] | None = None,
) -> OperationFlowProductEntryToolExposureResolutionCandidate:
    """Resolve read-only tool exposure for product-entry consumers."""

    resolution = resolve_operation_flow_tool_exposure_profile(
        profile_name=profile_name,
        profile_config=profile_config,
        repo_root=repo_root,
        entrypoint_explicit_args=entrypoint_explicit_args,
    )
    policy = resolution.reference_reader_policy
    return OperationFlowProductEntryToolExposureResolutionCandidate(
        status=resolution.status,
        exposed_tool_names=tuple(resolution.exposed_tool_names),
        blocked_tool_names=tuple(resolution.blocked_tool_names),
        blocking_reasons=tuple(resolution.blocking_reasons),
        warnings=tuple(resolution.warnings),
        reference_reader_policy=(
            OperationFlowProductEntryReferenceReaderPolicyCandidate(
                allowed_roots=tuple(policy.allowed_roots),
                allowed_files=tuple(policy.allowed_files),
                allowed_suffixes=tuple(policy.allowed_suffixes),
                max_bytes=policy.max_bytes,
                max_chars=policy.max_chars,
                max_excerpt_lines=policy.max_excerpt_lines,
                metadata=dict(policy.metadata),
            )
            if policy is not None
            else None
        ),
        metadata=dict(resolution.metadata),
    )


def build_operation_flow_product_entry_tools_status(
    *,
    profile_name: str,
    profile_config: Mapping[str, Any] | None,
    repo_root: str,
    entrypoint_explicit_args: Mapping[str, Any],
    operator_approved: bool,
    approval_ref: str | None,
) -> dict[str, Any]:
    """Return sanitized tool exposure and loading status."""

    resolution = resolve_operation_flow_tool_exposure_profile(
        profile_name=profile_name,
        profile_config=profile_config,
        repo_root=repo_root,
        entrypoint_explicit_args=entrypoint_explicit_args,
    )
    status = operation_flow_tool_exposure_profile_status_dict(resolution)
    loading_gate = validate_operation_flow_tool_loading_gate(
        resolution,
        operator_approved=operator_approved,
        approval_ref=approval_ref,
    )
    loading_status = operation_flow_tool_loading_gate_status_dict(loading_gate)
    profile = status["profile"]
    selection = status["selection"]
    reference_policy = status["reference_reader_policy"]
    return {
        "profile_name": profile["name"],
        "status": profile["status"],
        "config_precedence": profile["config_precedence"],
        "blocking_reasons": profile["blocking_reasons"],
        "warnings": profile["warnings"],
        "exposed_tool_names": selection["exposed_tool_names"],
        "blocked_tool_names": selection["blocked_tool_names"],
        "loading_validation_status": loading_status["status"],
        "risk_gate_status": loading_status["risk_gate_status"],
        "loading_allowed_tool_names": loading_status["allowed_tool_names"],
        "loading_blocked_tool_names": loading_status["blocked_tool_names"],
        "loading_blocking_reasons": loading_status["blocking_reasons"],
        "loading_warnings": loading_status["warnings"],
        "tool_loading_validations": loading_status["validations"],
        "reference_reader_status": "enabled" if reference_policy else "not_exposed",
        "reference_reader_policy": reference_policy,
    }


def build_operation_flow_product_entry_skill_capability_projection_status() -> dict[str, Any]:
    """Return the candidate-only Skills projection status summary."""

    try:
        return operation_flow_skill_projection_status_summary_status_dict(
            build_default_operation_flow_skill_capability_projection_status_summary()
        )
    except Exception as exc:
        return {
            "status": "candidate_summary_unavailable",
            "source": "cognition_operation_flows.product_entry_service",
            "projection_count": 0,
            "workflow_slot_reference_count": 0,
            "active_slot_reference_count": 0,
            "blocked_slot_reference_count": 0,
            "projection_refs": [],
            "workflow_slot_refs": [],
            "workflow_names": [],
            "skill_ids": [],
            "capability_ids": [],
            "reference_modes": [],
            "allowed_use_summary": {},
            "forbidden_use_summary": {},
            "evidence_refs": [],
            "runtime_enabled": False,
            "skill_file_loading_enabled": False,
            "resources_loading_enabled": False,
            "scripts_execution_enabled": False,
            "tool_exposure_enabled": False,
            "agent_runtime_enabled": False,
            "prompt_context_enabled": False,
            "public_schema_enabled": False,
            "metadata": {
                "candidate_only": True,
                "reference_only": True,
                "unavailable_error_type": type(exc).__name__,
            },
        }


__all__ = [
    "build_operation_flow_product_entry_skill_capability_projection_status",
    "build_operation_flow_product_entry_tools_status",
    "resolve_operation_flow_product_entry_tool_exposure_profile",
]
