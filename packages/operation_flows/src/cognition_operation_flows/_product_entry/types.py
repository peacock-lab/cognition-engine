"""Private product-entry types for the operation flow public service surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cognition_operation_flows._requests.intent_detectors import (
    OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
    OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
    OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
)
from cognition_operation_flows._tools.reference_reader import (
    DEFAULT_REFERENCE_READER_FORBIDDEN_PATH_MARKERS,
    DEFAULT_REFERENCE_READER_FORBIDDEN_SEGMENTS,
    REFERENCE_READER_TOOL_NAME,
)
from cognition_operation_flows._requests.registry import (
    OPERATION_FLOW_PLAN_WORKFLOW_NAME,
    OperationFlowRouteCandidate,
)


OPERATION_FLOW_PRODUCT_ENTRY_PLAN_WORKFLOW_NAME = OPERATION_FLOW_PLAN_WORKFLOW_NAME
OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_REVIEW_WORKFLOW_NAME = (
    OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME
)
OPERATION_FLOW_PRODUCT_ENTRY_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME = (
    OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME
)
OPERATION_FLOW_PRODUCT_ENTRY_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME = (
    OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME
)
OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_READER_TOOL_NAME = REFERENCE_READER_TOOL_NAME
OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_READER_FORBIDDEN_SEGMENTS = (
    DEFAULT_REFERENCE_READER_FORBIDDEN_SEGMENTS
)
OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_READER_FORBIDDEN_PATH_MARKERS = (
    DEFAULT_REFERENCE_READER_FORBIDDEN_PATH_MARKERS
)


@dataclass(frozen=True)
class OperationFlowProductEntryRouteResultCandidate:
    """Operation flow route result prepared for product-entry consumers."""

    route: OperationFlowRouteCandidate
    registry_status: dict[str, Any]
    route_status: dict[str, Any]
    registry_version: str
    registry_workflow_count: int
    registry_workflow_names: tuple[str, ...]


@dataclass(frozen=True)
class OperationFlowProductEntryReferenceReaderPolicyCandidate:
    """Sanitized reference-reader policy for product-entry consumers."""

    allowed_roots: tuple[str, ...]
    allowed_files: tuple[str, ...] = ()
    allowed_suffixes: tuple[str, ...] = ()
    max_bytes: int = 32768
    max_chars: int = 6000
    max_excerpt_lines: int = 80
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationFlowProductEntryToolExposureResolutionCandidate:
    """Sanitized tool exposure resolution for product-entry consumers."""

    status: str
    exposed_tool_names: tuple[str, ...]
    blocked_tool_names: tuple[str, ...]
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    reference_reader_policy: (
        OperationFlowProductEntryReferenceReaderPolicyCandidate | None
    ) = None
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "OPERATION_FLOW_PRODUCT_ENTRY_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME",
    "OPERATION_FLOW_PRODUCT_ENTRY_PLAN_WORKFLOW_NAME",
    "OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_READER_FORBIDDEN_PATH_MARKERS",
    "OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_READER_FORBIDDEN_SEGMENTS",
    "OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_READER_TOOL_NAME",
    "OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_REVIEW_WORKFLOW_NAME",
    "OPERATION_FLOW_PRODUCT_ENTRY_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME",
    "OperationFlowProductEntryReferenceReaderPolicyCandidate",
    "OperationFlowProductEntryRouteResultCandidate",
    "OperationFlowProductEntryToolExposureResolutionCandidate",
]
