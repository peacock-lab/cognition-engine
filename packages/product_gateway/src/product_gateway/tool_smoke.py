"""tool-smoke product entry normalization for product_gateway."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayExecutionMode,
    ProductGatewayInputRefs,
    ProductGatewayOutputRefs,
    ProductGatewayRef,
    ProductGatewayRequest,
    ProductGatewayResponse,
    ProductGatewayStatus,
)

TOOL_SMOKE_RESPONSE_SOURCE = "product_gateway.tool_smoke"
TOOL_SMOKE_PURPOSE = "tool_smoke"

TOOL_SMOKE_BLOCKED_FAILURE_TYPES = frozenset(
    {
        "tool_call_not_allowed",
        "tool_confirmation_rejected",
        "tool_confirmation_required",
        "tool_not_in_low_risk_allowlist",
        "tool_smoke_disabled",
        "tool_smoke_override_source_missing",
    }
)
TOOL_SMOKE_FAILED_STATUSES = frozenset({"failed", "failure"})
TOOL_SMOKE_SKIPPED_STATUSES = frozenset({"skipped", "not_run"})
TOOL_SMOKE_SUCCESS_STATUSES = frozenset({"success"})

FORBIDDEN_TOOL_SMOKE_INPUT_KEYS = frozenset(
    {
        "ToolConfirmation",
        "ToolConfirmation object",
        "ToolContext",
        "api_key",
        "credential",
        "function_args",
        "function_response",
        "low_risk_tool_allowlist",
        "messages",
        "prompt",
        "provider_payload",
        "provider_response",
        "raw_adk_event",
        "raw_adk_object",
        "raw_tool_input",
        "raw_tool_output",
        "response",
        "response_text",
        "secret",
        "token",
        "tool_confirmation",
        "tool_confirmation_ref",
        "tool_context",
        "tool_input",
        "tool_output",
        "tool_policy_ref",
    }
)
FORBIDDEN_TOOL_SMOKE_STRING_MARKERS = frozenset(
    {
        "ToolConfirmation",
        "ToolConfirmation object",
        "ToolContext",
        "function_args",
        "function_response",
        "provider_payload",
        "provider_response",
        "raw_adk_event",
        "raw_adk_object",
        "raw_tool_input",
        "raw_tool_output",
        "tool_input",
        "tool_output",
    }
)
FORBIDDEN_TOOL_SMOKE_MODULE_PREFIXES = (
    "google" + ".adk",
    "adk" + "_adapter",
)


class ToolSmokeGatewayInput(BaseModel):
    """Sanitized tool-smoke refs and facts accepted by product_gateway."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1)
    tool_evidence_ref: str | None = None
    tool_run_ref: str | None = None
    tool_audit_ref: str | None = None
    governance_summary_ref: str | None = None
    tool_status: str | None = None
    tool_failure_type: str | None = None
    tool_runtime_call_performed: bool = False
    tool_confirmation_required: bool = False
    tool_confirmation_granted: bool = False
    adk_tool_confirmation_requested: bool = False
    tool_confirmation_decision_source: str | None = None
    controlled_live_external_tool_smoke_enabled: bool | None = None
    controlled_live_external_tool_smoke_source: str | None = None
    tool_smoke_ready: bool = False
    low_risk_tool_allowlist_count: int | None = Field(default=None, ge=0)
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_tool_smoke_input(self) -> "ToolSmokeGatewayInput":
        _raise_if_forbidden_tool_smoke_payload_found(
            self.model_dump(mode="python"),
            field_name="tool_smoke_gateway_input",
        )
        if _would_block(self) and not self.blocking_reasons:
            raise ValueError(
                "blocked tool-smoke gateway inputs require blocking_reasons."
            )
        return self


class ToolSmokeCompatibilityProjection(BaseModel):
    """Product-normalized tool-smoke projection without execution objects."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1)
    entry_kind: str = Field(..., min_length=1)
    execution_mode: str = Field(..., min_length=1)
    tool_evidence_ref: str | None = None
    tool_run_ref: str | None = None
    tool_audit_ref: str | None = None
    governance_summary_ref: str | None = None
    tool_status: str | None = None
    tool_failure_type: str | None = None
    tool_runtime_call_performed: bool = False
    tool_confirmation_required: bool = False
    tool_confirmation_granted: bool = False
    adk_tool_confirmation_requested: bool = False
    tool_confirmation_decision_source: str | None = None
    controlled_live_external_tool_smoke_enabled: bool | None = None
    controlled_live_external_tool_smoke_source: str | None = None
    tool_smoke_ready: bool = False
    low_risk_tool_allowlist_count: int | None = None
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def build_tool_smoke_gateway_request(
    gateway_input: ToolSmokeGatewayInput | Mapping[str, Any],
) -> ProductGatewayRequest:
    """Build a product-level tool-smoke request from sanitized refs."""

    normalized_input = _coerce_gateway_input(gateway_input)

    return ProductGatewayRequest(
        request_id=normalized_input.request_id,
        entry_kind=ProductGatewayEntryKind.TOOL_SMOKE,
        execution_mode=ProductGatewayExecutionMode.SMOKE,
        input_refs=ProductGatewayInputRefs(
            governance_summary_ref=normalized_input.governance_summary_ref,
            additional_refs=_input_additional_refs(normalized_input),
        ),
        metadata=_request_metadata(normalized_input),
    )


def build_tool_smoke_compatibility_projection(
    gateway_input: ToolSmokeGatewayInput | Mapping[str, Any],
) -> ToolSmokeCompatibilityProjection:
    """Build a tool-smoke projection without upstream payloads or objects."""

    normalized_input = _coerce_gateway_input(gateway_input)
    gateway_request = build_tool_smoke_gateway_request(normalized_input)

    return ToolSmokeCompatibilityProjection(
        request_id=gateway_request.request_id,
        entry_kind=gateway_request.entry_kind.value,
        execution_mode=gateway_request.execution_mode.value,
        tool_evidence_ref=normalized_input.tool_evidence_ref,
        tool_run_ref=normalized_input.tool_run_ref,
        tool_audit_ref=normalized_input.tool_audit_ref,
        governance_summary_ref=normalized_input.governance_summary_ref,
        tool_status=normalized_input.tool_status,
        tool_failure_type=normalized_input.tool_failure_type,
        tool_runtime_call_performed=normalized_input.tool_runtime_call_performed,
        tool_confirmation_required=normalized_input.tool_confirmation_required,
        tool_confirmation_granted=normalized_input.tool_confirmation_granted,
        adk_tool_confirmation_requested=(
            normalized_input.adk_tool_confirmation_requested
        ),
        tool_confirmation_decision_source=(
            normalized_input.tool_confirmation_decision_source
        ),
        controlled_live_external_tool_smoke_enabled=(
            normalized_input.controlled_live_external_tool_smoke_enabled
        ),
        controlled_live_external_tool_smoke_source=(
            normalized_input.controlled_live_external_tool_smoke_source
        ),
        tool_smoke_ready=normalized_input.tool_smoke_ready,
        low_risk_tool_allowlist_count=(
            normalized_input.low_risk_tool_allowlist_count
        ),
        blocking_reasons=list(normalized_input.blocking_reasons),
        warnings=list(normalized_input.warnings),
        metadata=dict(gateway_request.metadata),
    )


def run_tool_smoke_gateway_request(
    gateway_input: ToolSmokeGatewayInput | Mapping[str, Any],
) -> ProductGatewayResponse:
    """Normalize tool-smoke refs and facts into ProductGatewayResponse."""

    gateway_request = build_tool_smoke_gateway_request(gateway_input)
    projection = build_tool_smoke_compatibility_projection(gateway_input)
    return _product_gateway_response_from_projection(
        gateway_request=gateway_request,
        projection=projection,
    )


def _coerce_gateway_input(
    gateway_input: ToolSmokeGatewayInput | Mapping[str, Any],
) -> ToolSmokeGatewayInput:
    if isinstance(gateway_input, ToolSmokeGatewayInput):
        return gateway_input
    return ToolSmokeGatewayInput.model_validate(dict(gateway_input))


def _input_additional_refs(
    gateway_input: ToolSmokeGatewayInput,
) -> list[ProductGatewayRef]:
    return [
        *_refs_from_input(
            gateway_input,
            ("tool_evidence_ref",),
            kind="tool_evidence",
        ),
        *_refs_from_input(
            gateway_input,
            ("tool_run_ref",),
            kind="tool_run",
        ),
        *_refs_from_input(
            gateway_input,
            ("tool_audit_ref",),
            kind="tool_audit",
        ),
    ]


def _request_metadata(gateway_input: ToolSmokeGatewayInput) -> dict[str, Any]:
    metadata = dict(gateway_input.metadata)
    metadata.update(_status_metadata(gateway_input))
    metadata["source"] = TOOL_SMOKE_RESPONSE_SOURCE
    return _without_none(metadata)


def _product_gateway_response_from_projection(
    *,
    gateway_request: ProductGatewayRequest,
    projection: ToolSmokeCompatibilityProjection,
) -> ProductGatewayResponse:
    status = _response_status(projection)
    tool_audit_refs = [
        *_refs_from_projection(
            projection,
            ("tool_evidence_ref",),
            kind="tool_evidence",
        ),
        *_refs_from_projection(
            projection,
            ("tool_run_ref",),
            kind="tool_run",
        ),
        *_refs_from_projection(
            projection,
            ("tool_audit_ref",),
            kind="tool_audit",
        ),
    ]

    return ProductGatewayResponse(
        request_id=gateway_request.request_id,
        entry_kind=gateway_request.entry_kind,
        status=status,
        exit_code=_exit_code_for_status(status),
        blocking_reasons=list(projection.blocking_reasons),
        warnings=list(projection.warnings),
        output_refs=ProductGatewayOutputRefs(
            governance_summary_ref=projection.governance_summary_ref,
            tool_audit_refs=tool_audit_refs,
        ),
        governance_summary_ref=projection.governance_summary_ref,
        tool_audit_refs=tool_audit_refs,
        metadata=_response_metadata(projection),
    )


def _response_status(
    projection: ToolSmokeCompatibilityProjection,
) -> ProductGatewayStatus:
    failure_type = _status_text(projection.tool_failure_type)
    tool_status = _status_text(projection.tool_status)

    if _is_blocking_failure(failure_type) or _is_confirmation_blocked(projection):
        return ProductGatewayStatus.BLOCKED
    if tool_status in TOOL_SMOKE_SUCCESS_STATUSES:
        return ProductGatewayStatus.SUCCESS
    if tool_status in TOOL_SMOKE_FAILED_STATUSES:
        return ProductGatewayStatus.FAILED
    if failure_type:
        return ProductGatewayStatus.FAILED
    if tool_status in TOOL_SMOKE_SKIPPED_STATUSES:
        return ProductGatewayStatus.SKIPPED
    if projection.tool_smoke_ready:
        return ProductGatewayStatus.SUCCESS
    return ProductGatewayStatus.SKIPPED


def _exit_code_for_status(status: ProductGatewayStatus) -> int:
    if status is ProductGatewayStatus.BLOCKED:
        return 2
    if status is ProductGatewayStatus.FAILED:
        return 1
    return 0


def _response_metadata(
    projection: ToolSmokeCompatibilityProjection,
) -> dict[str, Any]:
    metadata = dict(projection.metadata)
    metadata.update(_status_metadata(projection))
    metadata["source"] = TOOL_SMOKE_RESPONSE_SOURCE
    if projection.tool_status is None and projection.tool_failure_type is None:
        metadata.setdefault(
            "status_warning",
            "tool_status_missing_without_failure_type",
        )
    return _without_none(metadata)


def _status_metadata(
    value: ToolSmokeGatewayInput | ToolSmokeCompatibilityProjection,
) -> dict[str, Any]:
    return {
        "tool_status": value.tool_status,
        "tool_failure_type": value.tool_failure_type,
        "tool_runtime_call_performed": value.tool_runtime_call_performed,
        "tool_confirmation_required": value.tool_confirmation_required,
        "tool_confirmation_granted": value.tool_confirmation_granted,
        "adk_tool_confirmation_requested": value.adk_tool_confirmation_requested,
        "tool_confirmation_decision_source": (
            value.tool_confirmation_decision_source
        ),
        "controlled_live_external_tool_smoke_enabled": (
            value.controlled_live_external_tool_smoke_enabled
        ),
        "controlled_live_external_tool_smoke_source": (
            value.controlled_live_external_tool_smoke_source
        ),
        "tool_smoke_ready": value.tool_smoke_ready,
        "low_risk_tool_allowlist_count": value.low_risk_tool_allowlist_count,
    }


def _refs_from_input(
    gateway_input: ToolSmokeGatewayInput,
    keys: tuple[str, ...],
    *,
    kind: str,
) -> list[ProductGatewayRef]:
    return [
        ProductGatewayRef(
            ref=ref,
            kind=kind,
            purpose=TOOL_SMOKE_PURPOSE,
            metadata={"source_key": key},
        )
        for key in keys
        if (ref := _optional_text(getattr(gateway_input, key)))
    ]


def _refs_from_projection(
    projection: ToolSmokeCompatibilityProjection,
    keys: tuple[str, ...],
    *,
    kind: str,
) -> list[ProductGatewayRef]:
    return [
        ProductGatewayRef(
            ref=ref,
            kind=kind,
            purpose=TOOL_SMOKE_PURPOSE,
            metadata={"source_key": key},
        )
        for key in keys
        if (ref := _optional_text(getattr(projection, key)))
    ]


def _would_block(gateway_input: ToolSmokeGatewayInput) -> bool:
    failure_type = _status_text(gateway_input.tool_failure_type)
    return _is_blocking_failure(failure_type) or _is_confirmation_blocked(
        gateway_input
    )


def _is_blocking_failure(failure_type: str | None) -> bool:
    return failure_type in TOOL_SMOKE_BLOCKED_FAILURE_TYPES


def _is_confirmation_blocked(
    value: ToolSmokeGatewayInput | ToolSmokeCompatibilityProjection,
) -> bool:
    return (
        not value.tool_runtime_call_performed
        and value.tool_confirmation_required
        and not value.tool_confirmation_granted
    )


def _status_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip().lower()
    return text or None


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _without_none(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}


def _raise_if_forbidden_tool_smoke_payload_found(
    value: Any,
    *,
    field_name: str,
) -> None:
    violations = [
        f"{field_name} contains forbidden tool-smoke payload at {path}."
        for path, item in _walk(value)
        if _is_forbidden_tool_smoke_payload(path, item)
    ]
    if violations:
        raise ValueError("; ".join(violations))


def _is_forbidden_tool_smoke_payload(path: str, value: Any) -> bool:
    key = path.rsplit(".", maxsplit=1)[-1].strip("[]'")
    if key in FORBIDDEN_TOOL_SMOKE_INPUT_KEYS:
        return True
    if isinstance(value, dict):
        module_name = value.get("object_module")
        return isinstance(module_name, str) and module_name.startswith(
            FORBIDDEN_TOOL_SMOKE_MODULE_PREFIXES
        )
    if isinstance(value, str):
        return any(token in value for token in FORBIDDEN_TOOL_SMOKE_STRING_MARKERS)
    return False


def _walk(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    items = [(path, value)]
    if isinstance(value, dict):
        for key, item in value.items():
            items.extend(_walk(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            items.extend(_walk(item, f"{path}[{index}]"))
    return items


__all__ = [
    "TOOL_SMOKE_PURPOSE",
    "TOOL_SMOKE_RESPONSE_SOURCE",
    "ToolSmokeCompatibilityProjection",
    "ToolSmokeGatewayInput",
    "build_tool_smoke_compatibility_projection",
    "build_tool_smoke_gateway_request",
    "run_tool_smoke_gateway_request",
]
