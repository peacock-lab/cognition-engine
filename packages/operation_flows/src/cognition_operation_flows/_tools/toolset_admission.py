"""Candidate-only operation flow toolset admission and tool risk review helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import re
from typing import Any


OPERATION_FLOW_TOOLSET_CONTROL_STAGES = (
    "toolset_admission",
    "tool_inventory",
    "operation_facts",
    "risk_review",
    "selection_policy",
    "exposure_summary",
)
DYNAMIC_TOOLSET_KINDS = frozenset(
    {
        "api_hub",
        "application_integration",
        "connector",
        "openapi",
        "skill_toolset",
        "toolset",
    }
)
READONLY_HTTP_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
SIDE_EFFECT_HTTP_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
READONLY_OPERATION_TOKENS = frozenset(
    {"describe", "find", "get", "list", "lookup", "query", "read", "search"}
)
SIDE_EFFECT_OPERATION_TOKENS = frozenset(
    {
        "action",
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
SECRET_KEY_MARKERS = (
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
class OperationFlowToolsetAdmissionCandidate:
    """Candidate admission review for a dynamic or static operation flow toolset."""

    toolset_name: str
    toolset_kind: str
    source_ref: str | None = None
    dynamic_toolset: bool = True
    admitted: bool = False
    tool_filter_required: bool = True
    selected_tool_names: tuple[str, ...] = ()
    allowlist_tool_names: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    credential_boundary: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationFlowToolOperationFactsCandidate:
    """Sanitized operation facts for one generated or declared tool."""

    tool_name: str
    toolset_name: str
    toolset_kind: str
    operation_id: str | None = None
    http_method: str | None = None
    path: str | None = None
    entity: str | None = None
    action: str | None = None
    operation: str | None = None
    requires_auth: bool = False
    touches_external_system: bool = True
    has_request_body: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationFlowToolRiskReviewCandidate:
    """Risk review for one tool operation before operation flow exposure."""

    tool_name: str
    risk_level: str
    readonly_operation: bool
    allowed_for_readonly: bool
    confirmation_required: bool
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationFlowToolCandidate:
    """Candidate tool exposure after selection and risk review."""

    tool_name: str
    selected: bool
    exposed: bool
    operation_facts: OperationFlowToolOperationFactsCandidate
    risk_review: OperationFlowToolRiskReviewCandidate
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationFlowToolsetInventoryCandidate:
    """Sanitized toolset inventory after admission and per-tool review."""

    admission: OperationFlowToolsetAdmissionCandidate
    tools: tuple[OperationFlowToolCandidate, ...]
    exposed_tool_names: tuple[str, ...]
    blocked_tool_names: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


def evaluate_operation_flow_toolset_admission(
    *,
    toolset_name: str,
    toolset_kind: str,
    source_ref: str | None = None,
    tool_filter: Sequence[str] | None = None,
    allowlist_tool_names: Sequence[str] = (),
    discovery_credential_ref: str | None = None,
    execution_credential_ref: str | None = None,
    dynamic_toolset: bool | None = None,
    raw_config: Mapping[str, Any] | None = None,
) -> OperationFlowToolsetAdmissionCandidate:
    """Evaluate candidate-only toolset admission without loading the toolset."""

    normalized_kind = _normalize_token(toolset_kind)
    selected = tuple(_ordered_unique(tool_filter or ()))
    allowlist = tuple(_ordered_unique(allowlist_tool_names))
    is_dynamic = (
        normalized_kind in DYNAMIC_TOOLSET_KINDS
        if dynamic_toolset is None
        else dynamic_toolset
    )
    blocking: list[str] = []
    warnings: list[str] = []
    if not toolset_name.strip():
        blocking.append("toolset_name_missing")
    if not normalized_kind:
        blocking.append("toolset_kind_missing")
    if is_dynamic and not source_ref:
        blocking.append("toolset_source_ref_missing")
    if is_dynamic and not selected and not allowlist:
        blocking.append("tool_filter_or_allowlist_required")
    raw_secret_keys = _raw_secret_keys(raw_config or {})
    if raw_secret_keys:
        blocking.append("raw_credential_material_forbidden")
    if discovery_credential_ref is None:
        warnings.append("discovery_credential_ref_not_declared")
    if execution_credential_ref is None:
        warnings.append("execution_credential_ref_not_declared")
    return OperationFlowToolsetAdmissionCandidate(
        toolset_name=toolset_name,
        toolset_kind=normalized_kind,
        source_ref=source_ref,
        dynamic_toolset=is_dynamic,
        admitted=not blocking,
        tool_filter_required=is_dynamic,
        selected_tool_names=selected,
        allowlist_tool_names=allowlist,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        credential_boundary={
            "discovery_credential_ref_present": discovery_credential_ref is not None,
            "execution_credential_ref_present": execution_credential_ref is not None,
            "raw_credential_material_included": False,
            "raw_credential_key_count": len(raw_secret_keys),
        },
        metadata={
            "stages": list(OPERATION_FLOW_TOOLSET_CONTROL_STAGES),
            "candidate_only": True,
            "does_not_load_toolset": True,
            "does_not_execute_tools": True,
        },
    )


def review_operation_flow_tool_operation_risk(
    operation_facts: OperationFlowToolOperationFactsCandidate,
) -> OperationFlowToolRiskReviewCandidate:
    """Review one operation for readonly operation flow exposure."""

    identity_tokens = _operation_identity_tokens(operation_facts)
    method = (operation_facts.http_method or "").upper()
    has_identity = bool(method or identity_tokens)
    has_side_effect_method = method in SIDE_EFFECT_HTTP_METHODS
    has_readonly_method = method in READONLY_HTTP_METHODS
    has_side_effect_token = any(
        token in SIDE_EFFECT_OPERATION_TOKENS for token in identity_tokens
    )
    has_readonly_token = any(
        token in READONLY_OPERATION_TOKENS for token in identity_tokens
    )
    readonly_operation = (
        has_identity
        and not has_side_effect_method
        and not has_side_effect_token
        and not operation_facts.has_request_body
        and (has_readonly_method or has_readonly_token)
    )
    blocking: list[str] = []
    warnings: list[str] = []
    if not has_identity:
        blocking.append("tool_operation_identity_missing")
    if readonly_operation:
        if operation_facts.requires_auth or operation_facts.touches_external_system:
            risk_level = "medium"
            warnings.append("readonly_external_or_authenticated_tool_requires_confirmation")
        else:
            risk_level = "low"
    else:
        risk_level = "high" if has_side_effect_method or has_side_effect_token else "medium"
        if has_identity:
            blocking.append("tool_not_readonly")
    return OperationFlowToolRiskReviewCandidate(
        tool_name=operation_facts.tool_name,
        risk_level="blocked" if blocking and not has_identity else risk_level,
        readonly_operation=readonly_operation,
        allowed_for_readonly=readonly_operation and not blocking,
        confirmation_required=(
            operation_facts.requires_auth
            or operation_facts.touches_external_system
            or not readonly_operation
        ),
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "candidate_only": True,
            "operation_identity_tokens": list(identity_tokens),
            "http_method": method or None,
        },
    )


def build_operation_flow_toolset_inventory(
    admission: OperationFlowToolsetAdmissionCandidate,
    operations: Sequence[OperationFlowToolOperationFactsCandidate],
) -> OperationFlowToolsetInventoryCandidate:
    """Build a selected, readonly-safe inventory for a candidate toolset."""

    selected_names = set(admission.selected_tool_names or admission.allowlist_tool_names)
    tools: list[OperationFlowToolCandidate] = []
    warnings: list[str] = list(admission.warnings)
    for operation in operations:
        selected = operation.tool_name in selected_names
        review = review_operation_flow_tool_operation_risk(operation)
        exposed = admission.admitted and selected and review.allowed_for_readonly
        if selected and not review.allowed_for_readonly:
            warnings.append(f"selected_tool_blocked:{operation.tool_name}")
        tools.append(
            OperationFlowToolCandidate(
                tool_name=operation.tool_name,
                selected=selected,
                exposed=exposed,
                operation_facts=operation,
                risk_review=review,
                metadata={
                    "candidate_only": True,
                    "selection_source": (
                        "tool_filter_or_allowlist" if selected else "not_selected"
                    ),
                },
            )
        )
    exposed_tool_names = tuple(tool.tool_name for tool in tools if tool.exposed)
    blocked_tool_names = tuple(
        tool.tool_name
        for tool in tools
        if tool.selected and not tool.exposed
    )
    return OperationFlowToolsetInventoryCandidate(
        admission=admission,
        tools=tuple(tools),
        exposed_tool_names=exposed_tool_names,
        blocked_tool_names=blocked_tool_names,
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "candidate_only": True,
            "tool_count": len(tools),
            "selected_count": sum(1 for tool in tools if tool.selected),
            "exposed_count": len(exposed_tool_names),
        },
    )


def operation_flow_toolset_inventory_status_dict(
    inventory: OperationFlowToolsetInventoryCandidate,
) -> dict[str, Any]:
    """Return a sanitized status dict for task result metadata."""

    return {
        "toolset": {
            "name": inventory.admission.toolset_name,
            "kind": inventory.admission.toolset_kind,
            "source_ref": inventory.admission.source_ref,
            "dynamic_toolset": inventory.admission.dynamic_toolset,
            "admitted": inventory.admission.admitted,
            "blocking_reasons": list(inventory.admission.blocking_reasons),
            "warnings": list(inventory.admission.warnings),
            "credential_boundary": dict(inventory.admission.credential_boundary),
        },
        "selection": {
            "selected_tool_names": list(inventory.admission.selected_tool_names),
            "allowlist_tool_names": list(inventory.admission.allowlist_tool_names),
            "exposed_tool_names": list(inventory.exposed_tool_names),
            "blocked_tool_names": list(inventory.blocked_tool_names),
        },
        "tools": [
            {
                "tool_name": tool.tool_name,
                "selected": tool.selected,
                "exposed": tool.exposed,
                "risk_level": tool.risk_review.risk_level,
                "readonly_operation": tool.risk_review.readonly_operation,
                "allowed_for_readonly": tool.risk_review.allowed_for_readonly,
                "confirmation_required": tool.risk_review.confirmation_required,
                "blocking_reasons": list(tool.risk_review.blocking_reasons),
                "warnings": list(tool.risk_review.warnings),
            }
            for tool in inventory.tools
        ],
        "metadata": dict(inventory.metadata),
    }


def _operation_identity_tokens(
    operation_facts: OperationFlowToolOperationFactsCandidate,
) -> tuple[str, ...]:
    parts = (
        operation_facts.operation_id,
        operation_facts.action,
        operation_facts.operation,
    )
    tokens: list[str] = []
    for part in parts:
        normalized = _normalize_token(part or "")
        if not normalized:
            continue
        tokens.extend(_split_operation_tokens(normalized))
    return tuple(_ordered_unique(tokens))


def _raw_secret_keys(raw_config: Mapping[str, Any]) -> tuple[str, ...]:
    keys: list[str] = []
    for key, value in raw_config.items():
        key_text = str(key).lower()
        if any(marker in key_text for marker in SECRET_KEY_MARKERS):
            if value:
                keys.append(str(key))
        if isinstance(value, Mapping):
            nested = _raw_secret_keys(value)
            keys.extend(f"{key}.{item}" for item in nested)
    return tuple(_ordered_unique(keys))


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
