"""Candidate-only external read-only reference tool design helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import re
from typing import Any


OPERATION_FLOW_EXTERNAL_READONLY_TOOL_DESIGN_STAGES = (
    "tool_origin_review",
    "operation_family_review",
    "network_gate_review",
    "schema_boundary_review",
    "source_boundary_review",
    "output_boundary_review",
    "interaction_boundary_review",
    "runtime_closed_review",
    "sanitized_summary",
)
OPERATION_FLOW_EXTERNAL_READONLY_ALLOWED_ORIGINS = frozenset({"google_search", "url_context"})
OPERATION_FLOW_EXTERNAL_READONLY_ALLOWED_OPERATIONS = frozenset({"fetch", "read", "search"})
OPERATION_FLOW_EXTERNAL_READONLY_ORIGIN_OPERATIONS = {
    "google_search": frozenset({"search"}),
    "url_context": frozenset({"fetch", "read"}),
}
OPERATION_FLOW_EXTERNAL_READONLY_FORBIDDEN_OPERATION_TOKENS = frozenset(
    {
        "call",
        "create",
        "delete",
        "execute",
        "insert",
        "invoke",
        "login",
        "mutate",
        "patch",
        "post",
        "publish",
        "put",
        "remove",
        "run",
        "send",
        "submit",
        "update",
        "write",
    }
)
OPERATION_FLOW_EXTERNAL_READONLY_SECRET_KEY_MARKERS = (
    "access_token",
    "api_key",
    "cookie",
    "credential",
    "password",
    "private_key",
    "secret",
    "service_account_json",
    "session",
    "token",
)


@dataclass(frozen=True)
class OperationFlowExternalReadonlyToolDesignCandidate:
    """Sanitized design facts for one future external read-only reference tool."""

    tool_name: str
    tool_origin: str
    operation_family: str
    source_ref: str | None = None
    input_schema_ref: str | None = None
    output_boundary_ref: str | None = None
    adapter_boundary_ref: str | None = None
    evidence_boundary_ref: str | None = None
    network_access_required: bool = True
    network_enabled_by_default: bool = False
    operator_confirmation_required: bool = True
    source_url_required: bool = True
    timestamp_required: bool = True
    sanitized_excerpt_only: bool = True
    stores_raw_response: bool = False
    stores_full_page_content: bool = False
    stores_cookies: bool = False
    stores_tokens: bool = False
    allows_login: bool = False
    allows_form_submission: bool = False
    executes_javascript_action: bool = False
    follows_unbounded_redirects: bool = False
    writes_files: bool = False
    mutates_external_system: bool = False
    executes_code: bool = False
    executes_shell: bool = False
    calls_llm: bool = False
    external_tool_runtime_enabled: bool = False
    tool_execution_enabled: bool = False
    raw_tool_payload_included: bool = False
    raw_network_response_included: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationFlowExternalReadonlyToolDesignReviewCandidate:
    """Candidate-only design review for one external read-only reference tool."""

    tool_name: str
    tool_origin: str
    operation_family: str
    status: str
    risk_level: str
    allowed_for_design: bool
    network_gate_required: bool
    confirmation_required: bool
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationFlowExternalReadonlyToolDesignSummaryCandidate:
    """Aggregate sanitized summary for external read-only reference tool designs."""

    status: str
    allowed_tool_names: tuple[str, ...]
    blocked_tool_names: tuple[str, ...]
    reviews: tuple[OperationFlowExternalReadonlyToolDesignReviewCandidate, ...]
    allowed_origins: tuple[str, ...] = tuple(
        sorted(OPERATION_FLOW_EXTERNAL_READONLY_ALLOWED_ORIGINS)
    )
    allowed_operations: tuple[str, ...] = tuple(
        sorted(OPERATION_FLOW_EXTERNAL_READONLY_ALLOWED_OPERATIONS)
    )
    network_enabled_by_default: bool = False
    external_tool_runtime_enabled: bool = False
    tool_execution_enabled: bool = False
    external_network_call_performed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


def review_operation_flow_external_readonly_tool_design(
    design: OperationFlowExternalReadonlyToolDesignCandidate,
) -> OperationFlowExternalReadonlyToolDesignReviewCandidate:
    """Review one external read-only tool design without network execution."""

    origin = _normalize_token(design.tool_origin)
    operation = _normalize_operation_family(design.operation_family)
    blocking: list[str] = []
    warnings: list[str] = []

    if not design.tool_name.strip():
        blocking.append("tool_name_missing")
    if not origin:
        blocking.append("tool_origin_missing")
    elif origin not in OPERATION_FLOW_EXTERNAL_READONLY_ALLOWED_ORIGINS:
        blocking.append("tool_origin_not_allowed_for_external_readonly")
    if not operation:
        blocking.append("operation_family_missing")
    elif operation not in OPERATION_FLOW_EXTERNAL_READONLY_ALLOWED_OPERATIONS:
        blocking.append("operation_family_not_in_external_readonly_allowlist")
    elif origin in OPERATION_FLOW_EXTERNAL_READONLY_ORIGIN_OPERATIONS:
        allowed_for_origin = OPERATION_FLOW_EXTERNAL_READONLY_ORIGIN_OPERATIONS[origin]
        if operation not in allowed_for_origin:
            blocking.append("operation_family_not_allowed_for_tool_origin")
    if _operation_contains_forbidden_token(design.operation_family):
        blocking.append("operation_family_contains_side_effect_token")

    if not _present(design.source_ref):
        blocking.append("source_ref_required")
    if not _present(design.input_schema_ref):
        blocking.append("input_schema_ref_required")
    if not _present(design.output_boundary_ref):
        blocking.append("output_boundary_ref_required")
    if not _present(design.adapter_boundary_ref):
        blocking.append("adapter_boundary_ref_required")
    if not _present(design.evidence_boundary_ref):
        blocking.append("evidence_boundary_ref_required")

    if not design.network_access_required:
        warnings.append("external_tool_network_access_not_declared")
    if design.network_enabled_by_default:
        blocking.append("network_enabled_by_default_forbidden")
    if not design.operator_confirmation_required:
        blocking.append("operator_confirmation_required")
    if not design.source_url_required:
        blocking.append("source_url_required")
    if not design.timestamp_required:
        blocking.append("timestamp_required")
    if not design.sanitized_excerpt_only:
        blocking.append("sanitized_excerpt_only_required")
    if design.stores_raw_response:
        blocking.append("raw_response_storage_forbidden")
    if design.stores_full_page_content:
        blocking.append("full_page_content_storage_forbidden")
    if design.stores_cookies:
        blocking.append("cookie_storage_forbidden")
    if design.stores_tokens:
        blocking.append("token_storage_forbidden")
    if design.allows_login:
        blocking.append("login_flow_forbidden")
    if design.allows_form_submission:
        blocking.append("form_submission_forbidden")
    if design.executes_javascript_action:
        blocking.append("javascript_action_forbidden")
    if design.follows_unbounded_redirects:
        blocking.append("unbounded_redirects_forbidden")
    if design.writes_files:
        blocking.append("writes_files_forbidden")
    if design.mutates_external_system:
        blocking.append("mutates_external_system_forbidden")
    if design.executes_code:
        blocking.append("executes_code_forbidden")
    if design.executes_shell:
        blocking.append("executes_shell_forbidden")
    if design.calls_llm:
        blocking.append("calls_llm_forbidden")
    if design.external_tool_runtime_enabled:
        blocking.append("external_tool_runtime_must_remain_closed")
    if design.tool_execution_enabled:
        blocking.append("tool_execution_enabled_forbidden")
    if design.raw_tool_payload_included:
        blocking.append("raw_tool_payload_forbidden")
    if design.raw_network_response_included:
        blocking.append("raw_network_response_forbidden")
    if _raw_secret_keys(design.metadata):
        blocking.append("raw_credential_material_forbidden")

    return OperationFlowExternalReadonlyToolDesignReviewCandidate(
        tool_name=design.tool_name,
        tool_origin=origin,
        operation_family=operation,
        status="allowed" if not blocking else "blocked",
        risk_level="blocked" if blocking else "medium",
        allowed_for_design=not blocking,
        network_gate_required=True,
        confirmation_required=True,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "candidate_only": True,
            "reference_only": True,
            "stages": list(OPERATION_FLOW_EXTERNAL_READONLY_TOOL_DESIGN_STAGES),
            "source_ref": design.source_ref,
            "input_schema_ref": design.input_schema_ref,
            "output_boundary_ref": design.output_boundary_ref,
            "adapter_boundary_ref": design.adapter_boundary_ref,
            "evidence_boundary_ref": design.evidence_boundary_ref,
            "network_access_required": design.network_access_required,
            "network_enabled_by_default": False,
            "operator_confirmation_required": True,
            "sanitized_excerpt_only": design.sanitized_excerpt_only,
            "source_url_required": design.source_url_required,
            "timestamp_required": design.timestamp_required,
            "does_not_execute_tool": True,
            "external_network_call_performed": False,
            "external_tool_runtime_enabled": False,
            "tool_execution_enabled": False,
        },
    )


def build_operation_flow_external_readonly_tool_design_summary(
    designs: Sequence[OperationFlowExternalReadonlyToolDesignCandidate],
) -> OperationFlowExternalReadonlyToolDesignSummaryCandidate:
    """Build an aggregate candidate-only summary for external read-only tools."""

    reviews = tuple(
        review_operation_flow_external_readonly_tool_design(design) for design in designs
    )
    allowed = tuple(
        review.tool_name for review in reviews if review.allowed_for_design
    )
    blocked = tuple(
        review.tool_name for review in reviews if not review.allowed_for_design
    )
    return OperationFlowExternalReadonlyToolDesignSummaryCandidate(
        status="allowed" if not blocked else "blocked",
        allowed_tool_names=tuple(_ordered_unique(allowed)),
        blocked_tool_names=tuple(_ordered_unique(blocked)),
        reviews=reviews,
        metadata={
            "candidate_only": True,
            "reference_only": True,
            "does_not_execute_tools": True,
            "does_not_perform_external_network_calls": True,
            "requires_operator_confirmation_before_future_use": True,
            "allowed_origin_count": len(OPERATION_FLOW_EXTERNAL_READONLY_ALLOWED_ORIGINS),
            "review_count": len(reviews),
        },
    )


def operation_flow_external_readonly_tool_design_review_status_dict(
    review: OperationFlowExternalReadonlyToolDesignReviewCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready sanitized review summary."""

    return {
        "tool_name": review.tool_name,
        "tool_origin": review.tool_origin,
        "operation_family": review.operation_family,
        "status": review.status,
        "risk_level": review.risk_level,
        "allowed_for_design": review.allowed_for_design,
        "network_gate_required": review.network_gate_required,
        "confirmation_required": review.confirmation_required,
        "blocking_reasons": list(review.blocking_reasons),
        "warnings": list(review.warnings),
        "metadata": dict(review.metadata),
    }


def operation_flow_external_readonly_tool_design_summary_status_dict(
    summary: OperationFlowExternalReadonlyToolDesignSummaryCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready sanitized aggregate summary."""

    return {
        "status": summary.status,
        "allowed_tool_names": list(summary.allowed_tool_names),
        "blocked_tool_names": list(summary.blocked_tool_names),
        "allowed_origins": list(summary.allowed_origins),
        "allowed_operations": list(summary.allowed_operations),
        "network_enabled_by_default": summary.network_enabled_by_default,
        "external_tool_runtime_enabled": summary.external_tool_runtime_enabled,
        "tool_execution_enabled": summary.tool_execution_enabled,
        "external_network_call_performed": summary.external_network_call_performed,
        "reviews": [
            operation_flow_external_readonly_tool_design_review_status_dict(review)
            for review in summary.reviews
        ],
        "metadata": dict(summary.metadata),
    }


def _normalize_operation_family(value: str) -> str:
    normalized = _normalize_token(value)
    if normalized in OPERATION_FLOW_EXTERNAL_READONLY_ALLOWED_OPERATIONS:
        return normalized
    tokens = _split_operation_tokens(normalized)
    for token in tokens:
        if token in OPERATION_FLOW_EXTERNAL_READONLY_ALLOWED_OPERATIONS:
            return token
    return normalized


def _operation_contains_forbidden_token(value: str) -> bool:
    tokens = _split_operation_tokens(_normalize_token(value))
    return any(
        token in OPERATION_FLOW_EXTERNAL_READONLY_FORBIDDEN_OPERATION_TOKENS for token in tokens
    )


def _raw_secret_keys(raw_config: Mapping[str, Any]) -> tuple[str, ...]:
    keys: list[str] = []
    for key, value in raw_config.items():
        key_text = str(key).lower()
        if any(
            marker in key_text
            for marker in OPERATION_FLOW_EXTERNAL_READONLY_SECRET_KEY_MARKERS
        ):
            if value:
                keys.append(str(key))
        if isinstance(value, Mapping):
            nested = _raw_secret_keys(value)
            keys.extend(f"{key}.{item}" for item in nested)
    return tuple(_ordered_unique(keys))


def _present(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def _normalize_token(value: str) -> str:
    return (
        _camel_to_snake(value.strip())
        .replace("-", "_")
        .replace(" ", "_")
        .replace("/", "_")
        .lower()
    )


def _camel_to_snake(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value)


def _split_operation_tokens(value: str) -> list[str]:
    return [token for token in value.split("_") if token]


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
