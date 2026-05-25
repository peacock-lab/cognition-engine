"""Product gateway read-only controls for operation flow tools and Skills slots."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cognition_operation_flows.product_entry_service import (
    OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_READER_FORBIDDEN_PATH_MARKERS,
    OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_READER_FORBIDDEN_SEGMENTS,
    OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_READER_TOOL_NAME,
    build_operation_flow_product_entry_skill_capability_projection_status,
    build_operation_flow_product_entry_tools_status,
    resolve_operation_flow_product_entry_tool_exposure_profile,
)


INTERNAL_REFERENCE_READER_TOOL_NAME = OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_READER_TOOL_NAME
INTERNAL_REFERENCE_READER_FORBIDDEN_SEGMENTS = (
    OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_READER_FORBIDDEN_SEGMENTS
)
INTERNAL_REFERENCE_READER_FORBIDDEN_PATH_MARKERS = (
    OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_READER_FORBIDDEN_PATH_MARKERS
)


@dataclass(frozen=True)
class InternalReferenceReaderPolicy:
    """Sanitized reference-reader policy exposed through product gateway."""

    allowed_roots: tuple[str, ...]
    allowed_files: tuple[str, ...] = ()
    allowed_suffixes: tuple[str, ...] = ()
    max_bytes: int = 32768
    max_chars: int = 6000
    max_excerpt_lines: int = 80
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InternalOperationFlowToolExposureResolution:
    """Sanitized tool exposure resolution for channel adapters."""

    status: str
    exposed_tool_names: tuple[str, ...]
    blocked_tool_names: tuple[str, ...]
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    reference_reader_policy: InternalReferenceReaderPolicy | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def resolve_internal_operation_flow_tool_exposure_profile(
    *,
    profile_name: str,
    profile_config: Mapping[str, Any] | None = None,
    repo_root: str | Path | None = None,
    entrypoint_explicit_args: Mapping[str, Any] | None = None,
) -> InternalOperationFlowToolExposureResolution:
    """Resolve read-only operation flow tool exposure behind product gateway."""

    resolution = resolve_operation_flow_product_entry_tool_exposure_profile(
        profile_name=profile_name,
        profile_config=profile_config,
        repo_root=repo_root,
        entrypoint_explicit_args=entrypoint_explicit_args,
    )
    policy = resolution.reference_reader_policy
    return InternalOperationFlowToolExposureResolution(
        status=resolution.status,
        exposed_tool_names=tuple(resolution.exposed_tool_names),
        blocked_tool_names=tuple(resolution.blocked_tool_names),
        blocking_reasons=tuple(resolution.blocking_reasons),
        warnings=tuple(resolution.warnings),
        reference_reader_policy=(
            InternalReferenceReaderPolicy(
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


def build_internal_operation_flow_tools_status(
    *,
    profile_name: str,
    profile_config: Mapping[str, Any] | None,
    repo_root: str,
    entrypoint_explicit_args: Mapping[str, Any],
    operator_approved: bool,
    approval_ref: str | None,
) -> dict[str, Any]:
    """Return sanitized tool exposure and loading status for CLI status views."""

    return build_operation_flow_product_entry_tools_status(
        profile_name=profile_name,
        profile_config=profile_config,
        repo_root=repo_root,
        entrypoint_explicit_args=entrypoint_explicit_args,
        operator_approved=operator_approved,
        approval_ref=approval_ref,
    )


def build_internal_operation_flow_skill_capability_projection_status() -> dict[str, Any]:
    """Return the candidate-only Skills projection status summary."""

    return build_operation_flow_product_entry_skill_capability_projection_status()


__all__ = [
    "INTERNAL_REFERENCE_READER_FORBIDDEN_PATH_MARKERS",
    "INTERNAL_REFERENCE_READER_FORBIDDEN_SEGMENTS",
    "INTERNAL_REFERENCE_READER_TOOL_NAME",
    "InternalReferenceReaderPolicy",
    "InternalOperationFlowToolExposureResolution",
    "build_internal_operation_flow_skill_capability_projection_status",
    "build_internal_operation_flow_tools_status",
    "resolve_internal_operation_flow_tool_exposure_profile",
]
