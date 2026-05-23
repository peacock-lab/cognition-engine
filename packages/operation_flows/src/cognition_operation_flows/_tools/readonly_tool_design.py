"""Candidate-only ADK/MCP read-only tool design review helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import re
from typing import Any


TWF_READONLY_TOOL_DESIGN_STAGES = (
    "tool_origin_review",
    "operation_family_review",
    "schema_boundary_review",
    "side_effect_boundary_review",
    "runtime_closed_review",
    "sanitized_summary",
)
TWF_READONLY_TOOL_ALLOWED_ORIGINS = frozenset(
    {"adk_function_tool", "adk_toolset", "mcp_toolset"}
)
TWF_READONLY_TOOL_ALLOWED_OPERATIONS = frozenset({"grep", "list", "read", "search"})
TWF_READONLY_TOOL_FORBIDDEN_OPERATION_TOKENS = frozenset(
    {
        "call",
        "create",
        "delete",
        "execute",
        "insert",
        "invoke",
        "mutate",
        "patch",
        "post",
        "publish",
        "put",
        "remove",
        "run",
        "send",
        "update",
        "write",
    }
)
TWF_READONLY_TOOL_DEFERRED_EXTERNAL_ORIGINS = frozenset(
    {"google_search", "url_context"}
)
TWF_READONLY_TOOL_SECRET_KEY_MARKERS = (
    "access_token",
    "api_key",
    "credential",
    "password",
    "private_key",
    "secret",
    "service_account_json",
    "token",
)


@dataclass(frozen=True)
class TwfReadonlyToolDesignCandidate:
    """Sanitized design facts for one future ADK/MCP read-only tool."""

    tool_name: str
    tool_origin: str
    operation_family: str
    toolset_name: str | None = None
    source_ref: str | None = None
    input_schema_ref: str | None = None
    output_boundary_ref: str | None = None
    adapter_boundary_ref: str | None = None
    requires_auth: bool = False
    touches_external_system: bool = False
    reads_local_files: bool = False
    reads_project_context: bool = False
    writes_files: bool = False
    mutates_external_system: bool = False
    executes_code: bool = False
    executes_shell: bool = False
    calls_llm: bool = False
    opens_agent_runtime: bool = False
    opens_skills_runtime: bool = False
    opens_mcp_runtime: bool = False
    loads_runtime_objects: bool = False
    raw_runtime_object_included: bool = False
    raw_tool_payload_included: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfReadonlyToolDesignReviewCandidate:
    """Candidate-only design review for one ADK/MCP read-only tool."""

    tool_name: str
    tool_origin: str
    operation_family: str
    status: str
    risk_level: str
    allowed_for_design: bool
    confirmation_required: bool
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfReadonlyToolDesignSummaryCandidate:
    """Aggregate sanitized summary for ADK/MCP read-only tool designs."""

    status: str
    allowed_tool_names: tuple[str, ...]
    blocked_tool_names: tuple[str, ...]
    reviews: tuple[TwfReadonlyToolDesignReviewCandidate, ...]
    allowed_origins: tuple[str, ...] = tuple(sorted(TWF_READONLY_TOOL_ALLOWED_ORIGINS))
    allowed_operations: tuple[str, ...] = tuple(
        sorted(TWF_READONLY_TOOL_ALLOWED_OPERATIONS)
    )
    runtime_enabled: bool = False
    tool_execution_enabled: bool = False
    mcp_runtime_enabled: bool = False
    agent_runtime_enabled: bool = False
    skills_runtime_enabled: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


def review_twf_readonly_tool_design(
    design: TwfReadonlyToolDesignCandidate,
) -> TwfReadonlyToolDesignReviewCandidate:
    """Review one future ADK/MCP tool design without loading or executing it."""

    origin = _normalize_token(design.tool_origin)
    operation = _normalize_operation_family(design.operation_family)
    blocking: list[str] = []
    warnings: list[str] = []

    if not design.tool_name.strip():
        blocking.append("tool_name_missing")
    if not origin:
        blocking.append("tool_origin_missing")
    elif origin not in TWF_READONLY_TOOL_ALLOWED_ORIGINS:
        blocking.append("tool_origin_not_allowed_for_adk_mcp_readonly")
        if origin in TWF_READONLY_TOOL_DEFERRED_EXTERNAL_ORIGINS:
            warnings.append("external_readonly_tool_origin_deferred")
    if not operation:
        blocking.append("operation_family_missing")
    elif operation not in TWF_READONLY_TOOL_ALLOWED_OPERATIONS:
        blocking.append("operation_family_not_in_readonly_allowlist")
    if _operation_contains_forbidden_token(design.operation_family):
        blocking.append("operation_family_contains_side_effect_token")

    if origin in {"adk_toolset", "mcp_toolset"} and not _present(design.source_ref):
        blocking.append("toolset_source_ref_required")
    if not _present(design.input_schema_ref):
        blocking.append("input_schema_ref_required")
    if not _present(design.output_boundary_ref):
        blocking.append("output_boundary_ref_required")
    if not _present(design.adapter_boundary_ref):
        blocking.append("adapter_boundary_ref_required")

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
    if design.opens_agent_runtime:
        blocking.append("agent_runtime_must_remain_closed")
    if design.opens_skills_runtime:
        blocking.append("skills_runtime_must_remain_closed")
    if design.opens_mcp_runtime:
        blocking.append("mcp_runtime_must_remain_closed")
    if design.loads_runtime_objects:
        blocking.append("runtime_object_loading_forbidden")
    if design.raw_runtime_object_included:
        blocking.append("raw_runtime_object_forbidden")
    if design.raw_tool_payload_included:
        blocking.append("raw_tool_payload_forbidden")
    if _raw_secret_keys(design.metadata):
        blocking.append("raw_credential_material_forbidden")

    confirmation_required = (
        design.requires_auth
        or design.touches_external_system
        or design.reads_local_files
        or design.reads_project_context
    )
    if blocking:
        risk_level = "blocked"
    elif confirmation_required:
        risk_level = "medium"
    else:
        risk_level = "low"

    return TwfReadonlyToolDesignReviewCandidate(
        tool_name=design.tool_name,
        tool_origin=origin,
        operation_family=operation,
        status="allowed" if not blocking else "blocked",
        risk_level=risk_level,
        allowed_for_design=not blocking,
        confirmation_required=confirmation_required,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "candidate_only": True,
            "reference_only": True,
            "stages": list(TWF_READONLY_TOOL_DESIGN_STAGES),
            "input_schema_ref": design.input_schema_ref,
            "output_boundary_ref": design.output_boundary_ref,
            "adapter_boundary_ref": design.adapter_boundary_ref,
            "does_not_load_tool": True,
            "does_not_execute_tool": True,
            "runtime_enabled": False,
            "tool_execution_enabled": False,
            "mcp_runtime_enabled": False,
            "agent_runtime_enabled": False,
            "skills_runtime_enabled": False,
        },
    )


def build_twf_readonly_tool_design_summary(
    designs: Sequence[TwfReadonlyToolDesignCandidate],
) -> TwfReadonlyToolDesignSummaryCandidate:
    """Build an aggregate candidate-only summary for future read-only tools."""

    reviews = tuple(review_twf_readonly_tool_design(design) for design in designs)
    allowed = tuple(
        review.tool_name for review in reviews if review.allowed_for_design
    )
    blocked = tuple(
        review.tool_name for review in reviews if not review.allowed_for_design
    )
    return TwfReadonlyToolDesignSummaryCandidate(
        status="allowed" if not blocked else "blocked",
        allowed_tool_names=tuple(_ordered_unique(allowed)),
        blocked_tool_names=tuple(_ordered_unique(blocked)),
        reviews=reviews,
        metadata={
            "candidate_only": True,
            "reference_only": True,
            "does_not_open_adk_runtime": True,
            "does_not_open_mcp_runtime": True,
            "does_not_execute_tools": True,
            "allowed_operation_count": len(TWF_READONLY_TOOL_ALLOWED_OPERATIONS),
            "review_count": len(reviews),
        },
    )


def twf_readonly_tool_design_review_status_dict(
    review: TwfReadonlyToolDesignReviewCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready sanitized review summary."""

    return {
        "tool_name": review.tool_name,
        "tool_origin": review.tool_origin,
        "operation_family": review.operation_family,
        "status": review.status,
        "risk_level": review.risk_level,
        "allowed_for_design": review.allowed_for_design,
        "confirmation_required": review.confirmation_required,
        "blocking_reasons": list(review.blocking_reasons),
        "warnings": list(review.warnings),
        "metadata": dict(review.metadata),
    }


def twf_readonly_tool_design_summary_status_dict(
    summary: TwfReadonlyToolDesignSummaryCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready sanitized aggregate summary."""

    return {
        "status": summary.status,
        "allowed_tool_names": list(summary.allowed_tool_names),
        "blocked_tool_names": list(summary.blocked_tool_names),
        "allowed_origins": list(summary.allowed_origins),
        "allowed_operations": list(summary.allowed_operations),
        "runtime_enabled": summary.runtime_enabled,
        "tool_execution_enabled": summary.tool_execution_enabled,
        "mcp_runtime_enabled": summary.mcp_runtime_enabled,
        "agent_runtime_enabled": summary.agent_runtime_enabled,
        "skills_runtime_enabled": summary.skills_runtime_enabled,
        "reviews": [
            twf_readonly_tool_design_review_status_dict(review)
            for review in summary.reviews
        ],
        "metadata": dict(summary.metadata),
    }


def _normalize_operation_family(value: str) -> str:
    normalized = _normalize_token(value)
    if normalized in TWF_READONLY_TOOL_ALLOWED_OPERATIONS:
        return normalized
    tokens = _split_operation_tokens(normalized)
    for token in tokens:
        if token in TWF_READONLY_TOOL_ALLOWED_OPERATIONS:
            return token
    return normalized


def _operation_contains_forbidden_token(value: str) -> bool:
    tokens = _split_operation_tokens(_normalize_token(value))
    return any(token in TWF_READONLY_TOOL_FORBIDDEN_OPERATION_TOKENS for token in tokens)


def _raw_secret_keys(raw_config: Mapping[str, Any]) -> tuple[str, ...]:
    keys: list[str] = []
    for key, value in raw_config.items():
        key_text = str(key).lower()
        if any(marker in key_text for marker in TWF_READONLY_TOOL_SECRET_KEY_MARKERS):
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
