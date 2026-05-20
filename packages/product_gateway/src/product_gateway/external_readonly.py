"""External-readonly product entry for gated URL fetch smoke runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayExecutionMode,
    ProductGatewayInputRefs,
    ProductGatewayOperatorApprovalRef,
    ProductGatewayOutputRefs,
    ProductGatewayRef,
    ProductGatewayRequest,
    ProductGatewayResponse,
    ProductGatewayStatus,
)
from external_readonly import (
    ExternalReadonlyHttpTransport,
    ExternalReadonlyUrlFetchRequest,
    ExternalReadonlyUrlFetchResult,
    run_external_readonly_url_fetch,
)


EXTERNAL_READONLY_FETCH_RESPONSE_SOURCE = "product_gateway.external_readonly"
EXTERNAL_READONLY_FETCH_DECISION_SOURCE = "explicit_external_readonly_product_entry"
EXTERNAL_READONLY_FETCH_PURPOSE = "external_readonly_fetch"
EXTERNAL_READONLY_FETCH_BACKEND_API = "external_readonly"

FORBIDDEN_EXTERNAL_READONLY_INPUT_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "body",
        "content",
        "cookie",
        "credential",
        "credentials",
        "full_page_content",
        "full_response",
        "html",
        "message",
        "messages",
        "password",
        "payload",
        "private_key",
        "provider_payload",
        "provider_response",
        "raw",
        "raw_body",
        "raw_html",
        "raw_network_response",
        "raw_payload",
        "raw_provider_payload",
        "raw_provider_response",
        "raw_request_payload",
        "raw_response",
        "response",
        "response_body",
        "response_headers",
        "response_text",
        "secret",
        "service_account_json",
        "session",
        "token",
    }
)
FORBIDDEN_EXTERNAL_READONLY_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "litellm",
    "composition",
)


class ExternalReadonlyFetchGatewayInput(BaseModel):
    """Sanitized product input for one external-readonly URL fetch request."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1)
    source_url: str = Field(..., min_length=1)
    envelope_ref: str = Field(..., min_length=1)
    evidence_ref: str = Field(..., min_length=1)
    network_gate: dict[str, Any] = Field(default_factory=dict)
    citation_index: int = Field(default=1, ge=1)
    source_title: str | None = None
    controlled_output_ref: str | None = None
    operator_approved: bool = False
    approval_ref: str | None = None
    audit_ref: str | None = None
    sanitized_evidence_ref: str | None = None
    governance_summary_ref: str | None = None
    allow_runtime_fetch: bool = False
    runtime_fetch_approval_ref: str | None = None
    use_live_transport: bool = False
    max_bytes: int = Field(default=20_000, ge=1)
    max_excerpt_chars: int = Field(default=2_000, ge=1)
    timeout_seconds: int = Field(default=10, ge=1)
    redirect_limit: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_external_readonly_input(self) -> "ExternalReadonlyFetchGatewayInput":
        _raise_if_forbidden_external_readonly_payload_found(
            {
                "network_gate": self.network_gate,
                "metadata": self.metadata,
            },
            field_name="external_readonly_fetch_gateway_input",
        )
        return self


class ExternalReadonlyFetchGatewayProjection(BaseModel):
    """Product-normalized projection without raw network payloads."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1)
    entry_kind: str = Field(..., min_length=1)
    execution_mode: str = Field(..., min_length=1)
    source_url: str = Field(..., min_length=1)
    envelope_ref: str = Field(..., min_length=1)
    evidence_ref: str = Field(..., min_length=1)
    operator_approved: bool = False
    approval_ref: str | None = None
    audit_ref: str | None = None
    sanitized_evidence_ref: str | None = None
    governance_summary_ref: str | None = None
    allow_runtime_fetch: bool = False
    runtime_fetch_approval_ref: str | None = None
    use_live_transport: bool = False
    network_gate_present: bool = False
    network_gate_open: bool | None = None
    transport_required: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class ExternalReadonlyFetchGatewayExecutionResult:
    """Product result plus the sanitized runtime external-readonly facts."""

    product_request: ProductGatewayRequest
    product_response: ProductGatewayResponse
    runtime_result: ExternalReadonlyUrlFetchResult | None = None


def build_external_readonly_fetch_gateway_request(
    gateway_input: ExternalReadonlyFetchGatewayInput | Mapping[str, Any],
) -> ProductGatewayRequest:
    """Build a product-level external-readonly fetch request."""

    normalized_input = _coerce_gateway_input(gateway_input)
    return ProductGatewayRequest(
        request_id=normalized_input.request_id,
        entry_kind=ProductGatewayEntryKind.EXTERNAL_READONLY_FETCH,
        execution_mode=_execution_mode(normalized_input),
        input_payload={
            "source_url": normalized_input.source_url,
            "envelope_ref": normalized_input.envelope_ref,
            "evidence_ref": normalized_input.evidence_ref,
            "citation_index": normalized_input.citation_index,
            "source_title_present": bool(normalized_input.source_title),
            "controlled_output_ref_present": bool(
                normalized_input.controlled_output_ref
            ),
            "network_gate_present": bool(normalized_input.network_gate),
            "allow_runtime_fetch": normalized_input.allow_runtime_fetch,
            "use_live_transport": normalized_input.use_live_transport,
            "max_bytes": normalized_input.max_bytes,
            "max_excerpt_chars": normalized_input.max_excerpt_chars,
            "timeout_seconds": normalized_input.timeout_seconds,
            "redirect_limit": normalized_input.redirect_limit,
        },
        input_refs=ProductGatewayInputRefs(
            operator_approval_ref=normalized_input.approval_ref,
            audit_ref=normalized_input.audit_ref,
            sanitized_evidence_ref=(
                normalized_input.sanitized_evidence_ref
                or normalized_input.evidence_ref
            ),
            governance_summary_ref=normalized_input.governance_summary_ref,
            additional_refs=[
                ProductGatewayRef(
                    ref=normalized_input.runtime_fetch_approval_ref,
                    kind="approval",
                    purpose=EXTERNAL_READONLY_FETCH_PURPOSE,
                    metadata={"source_key": "runtime_fetch_approval_ref"},
                )
            ]
            if normalized_input.runtime_fetch_approval_ref
            else [],
        ),
        operator_approval=ProductGatewayOperatorApprovalRef(
            approved=normalized_input.operator_approved,
            approval_ref=normalized_input.approval_ref,
            audit_ref=normalized_input.audit_ref,
            decision_source=EXTERNAL_READONLY_FETCH_DECISION_SOURCE,
        ),
        metadata=_request_metadata(normalized_input),
    )


def build_external_readonly_fetch_gateway_projection(
    gateway_input: ExternalReadonlyFetchGatewayInput | Mapping[str, Any],
) -> ExternalReadonlyFetchGatewayProjection:
    """Build a sanitized external-readonly product projection."""

    normalized_input = _coerce_gateway_input(gateway_input)
    gateway_request = build_external_readonly_fetch_gateway_request(normalized_input)
    return ExternalReadonlyFetchGatewayProjection(
        request_id=gateway_request.request_id,
        entry_kind=gateway_request.entry_kind.value,
        execution_mode=gateway_request.execution_mode.value,
        source_url=normalized_input.source_url,
        envelope_ref=normalized_input.envelope_ref,
        evidence_ref=normalized_input.evidence_ref,
        operator_approved=gateway_request.operator_approval.approved,
        approval_ref=gateway_request.operator_approval.approval_ref,
        audit_ref=gateway_request.operator_approval.audit_ref,
        sanitized_evidence_ref=gateway_request.input_refs.sanitized_evidence_ref,
        governance_summary_ref=gateway_request.input_refs.governance_summary_ref,
        allow_runtime_fetch=normalized_input.allow_runtime_fetch,
        runtime_fetch_approval_ref=normalized_input.runtime_fetch_approval_ref,
        use_live_transport=normalized_input.use_live_transport,
        network_gate_present=bool(normalized_input.network_gate),
        network_gate_open=_optional_bool(
            normalized_input.network_gate.get("network_gate_open")
        ),
        transport_required=not normalized_input.use_live_transport,
        metadata=dict(gateway_request.metadata),
    )


def run_external_readonly_fetch_gateway_request(
    gateway_input: ExternalReadonlyFetchGatewayInput | Mapping[str, Any],
    *,
    transport: ExternalReadonlyHttpTransport | None = None,
) -> ProductGatewayResponse:
    """Run the external-readonly fetch product entry and return response only."""

    return execute_external_readonly_fetch_gateway_request(
        gateway_input,
        transport=transport,
    ).product_response


def execute_external_readonly_fetch_gateway_request(
    gateway_input: ExternalReadonlyFetchGatewayInput | Mapping[str, Any],
    *,
    transport: ExternalReadonlyHttpTransport | None = None,
) -> ExternalReadonlyFetchGatewayExecutionResult:
    """Execute a gated URL fetch through the external_readonly backend API."""

    normalized_input = _coerce_gateway_input(gateway_input)
    gateway_request = build_external_readonly_fetch_gateway_request(normalized_input)
    blocking = _preflight_blocking_reasons(
        normalized_input,
        transport_supplied=transport is not None,
    )
    if blocking:
        return ExternalReadonlyFetchGatewayExecutionResult(
            product_request=gateway_request,
            product_response=_blocked_product_response(
                gateway_request=gateway_request,
                gateway_input=normalized_input,
                blocking_reasons=blocking,
            ),
            runtime_result=None,
        )

    runtime_request = ExternalReadonlyUrlFetchRequest(
        request_ref=normalized_input.request_id,
        source_url=normalized_input.source_url,
        envelope_ref=normalized_input.envelope_ref,
        evidence_ref=normalized_input.evidence_ref,
        citation_index=normalized_input.citation_index,
        source_title=normalized_input.source_title,
        controlled_output_ref=normalized_input.controlled_output_ref,
        max_bytes=normalized_input.max_bytes,
        max_excerpt_chars=normalized_input.max_excerpt_chars,
        timeout_seconds=normalized_input.timeout_seconds,
        redirect_limit=normalized_input.redirect_limit,
        metadata={
            "source": EXTERNAL_READONLY_FETCH_RESPONSE_SOURCE,
            "product_request_id": normalized_input.request_id,
        },
    )
    runtime_kwargs: dict[str, Any] = {
        "gate": normalized_input.network_gate,
        "request": runtime_request,
    }
    if transport is not None:
        runtime_kwargs["transport"] = transport
    runtime_result = run_external_readonly_url_fetch(**runtime_kwargs)
    product_response = _product_gateway_response_from_runtime_result(
        gateway_request=gateway_request,
        runtime_result=runtime_result,
    )
    return ExternalReadonlyFetchGatewayExecutionResult(
        product_request=gateway_request,
        product_response=product_response,
        runtime_result=runtime_result,
    )


def _coerce_gateway_input(
    gateway_input: ExternalReadonlyFetchGatewayInput | Mapping[str, Any],
) -> ExternalReadonlyFetchGatewayInput:
    if isinstance(gateway_input, ExternalReadonlyFetchGatewayInput):
        return gateway_input
    return ExternalReadonlyFetchGatewayInput.model_validate(dict(gateway_input))


def _execution_mode(
    gateway_input: ExternalReadonlyFetchGatewayInput,
) -> ProductGatewayExecutionMode:
    if not gateway_input.allow_runtime_fetch:
        return ProductGatewayExecutionMode.PREFLIGHT_ONLY
    return ProductGatewayExecutionMode.SMOKE


def _request_metadata(
    gateway_input: ExternalReadonlyFetchGatewayInput,
) -> dict[str, Any]:
    metadata = dict(gateway_input.metadata)
    metadata.update(
        {
            "source": EXTERNAL_READONLY_FETCH_RESPONSE_SOURCE,
            "backend_api": EXTERNAL_READONLY_FETCH_BACKEND_API,
            "network_gate_present": bool(gateway_input.network_gate),
            "network_gate_open": _optional_bool(
                gateway_input.network_gate.get("network_gate_open")
            ),
            "allow_runtime_fetch": gateway_input.allow_runtime_fetch,
            "use_live_transport": gateway_input.use_live_transport,
            "raw_response_included": False,
            "response_headers_included": False,
            "uploads_content": False,
            "writes_files": False,
        }
    )
    return _without_none(metadata)


def _preflight_blocking_reasons(
    gateway_input: ExternalReadonlyFetchGatewayInput,
    *,
    transport_supplied: bool,
) -> tuple[str, ...]:
    blocking: list[str] = []
    if not gateway_input.allow_runtime_fetch:
        blocking.append("external_readonly_runtime_fetch_not_allowed")
    if not gateway_input.operator_approved:
        blocking.append("operator_approval_not_true")
    if not gateway_input.approval_ref:
        blocking.append("approval_ref_required")
    if not gateway_input.runtime_fetch_approval_ref:
        blocking.append("runtime_fetch_approval_ref_required")
    if not gateway_input.network_gate:
        blocking.append("network_gate_required")
    if gateway_input.use_live_transport and not gateway_input.allow_runtime_fetch:
        blocking.append("live_transport_requires_runtime_fetch_allowance")
    if (
        gateway_input.allow_runtime_fetch
        and not gateway_input.use_live_transport
        and not transport_supplied
    ):
        blocking.append("external_readonly_transport_required")
    return tuple(_ordered_unique(blocking))


def _blocked_product_response(
    *,
    gateway_request: ProductGatewayRequest,
    gateway_input: ExternalReadonlyFetchGatewayInput,
    blocking_reasons: tuple[str, ...],
) -> ProductGatewayResponse:
    return ProductGatewayResponse(
        request_id=gateway_request.request_id,
        entry_kind=gateway_request.entry_kind,
        status=ProductGatewayStatus.BLOCKED,
        exit_code=2,
        blocking_reasons=list(blocking_reasons),
        output_refs=ProductGatewayOutputRefs(
            governance_summary_ref=gateway_input.governance_summary_ref
        ),
        governance_summary_ref=gateway_input.governance_summary_ref,
        metadata={
            **_request_metadata(gateway_input),
            "runtime_fetch_performed": False,
            "transport_called": False,
            "external_network_call_performed": False,
            "allowed_for_model_context": False,
        },
    )


def _product_gateway_response_from_runtime_result(
    *,
    gateway_request: ProductGatewayRequest,
    runtime_result: ExternalReadonlyUrlFetchResult,
) -> ProductGatewayResponse:
    status = _response_status(runtime_result)
    evidence_refs = _evidence_refs_from_runtime_result(runtime_result)
    return ProductGatewayResponse(
        request_id=gateway_request.request_id,
        entry_kind=gateway_request.entry_kind,
        status=status,
        exit_code=_exit_code_for_status(status),
        blocking_reasons=list(runtime_result.blocking_reasons),
        warnings=list(runtime_result.warnings),
        output_refs=ProductGatewayOutputRefs(
            evidence_refs=evidence_refs,
        ),
        evidence_refs=evidence_refs,
        metadata=_response_metadata(runtime_result),
    )


def _response_status(
    runtime_result: ExternalReadonlyUrlFetchResult,
) -> ProductGatewayStatus:
    if runtime_result.status == "completed":
        return ProductGatewayStatus.SUCCESS
    if runtime_result.status == "blocked":
        return ProductGatewayStatus.BLOCKED
    return ProductGatewayStatus.FAILED


def _exit_code_for_status(status: ProductGatewayStatus) -> int:
    if status is ProductGatewayStatus.SUCCESS:
        return 0
    if status is ProductGatewayStatus.BLOCKED:
        return 2
    return 1


def _evidence_refs_from_runtime_result(
    runtime_result: ExternalReadonlyUrlFetchResult,
) -> list[ProductGatewayRef]:
    envelope = runtime_result.envelope
    if envelope is None:
        return []
    return [
        ProductGatewayRef(
            ref=ref,
            kind="external_readonly_evidence",
            purpose=EXTERNAL_READONLY_FETCH_PURPOSE,
            metadata={"source": EXTERNAL_READONLY_FETCH_RESPONSE_SOURCE},
        )
        for ref in envelope.evidence_refs
    ]


def _response_metadata(
    runtime_result: ExternalReadonlyUrlFetchResult,
) -> dict[str, Any]:
    return {
        "source": EXTERNAL_READONLY_FETCH_RESPONSE_SOURCE,
        "backend_api": EXTERNAL_READONLY_FETCH_BACKEND_API,
        "runtime_status": runtime_result.status,
        "runtime_fetch_performed": runtime_result.runtime_fetch_performed,
        "transport_called": runtime_result.transport_called,
        "external_network_call_performed": (
            runtime_result.external_network_call_performed
        ),
        "tool_execution_performed": runtime_result.tool_execution_performed,
        "allowed_for_model_context": runtime_result.allowed_for_model_context,
        "raw_response_included": False,
        "response_headers_included": False,
        "uploads_content": False,
        "writes_files": False,
    }


def _raise_if_forbidden_external_readonly_payload_found(
    value: Any,
    *,
    field_name: str,
) -> None:
    violations = [
        f"{field_name} contains forbidden payload at {path}."
        for path, item in _walk(value)
        if _is_forbidden_payload(path, item)
    ]
    if violations:
        raise ValueError("; ".join(violations))


def _walk(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    items = [(path, value)]
    if isinstance(value, Mapping):
        for key, item in value.items():
            items.extend(_walk(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            items.extend(_walk(item, f"{path}[{index}]"))
    return items


def _is_forbidden_payload(path: str, value: Any) -> bool:
    key = path.rsplit(".", maxsplit=1)[-1].lower()
    if key in FORBIDDEN_EXTERNAL_READONLY_INPUT_KEYS:
        return True
    if isinstance(value, Mapping):
        module_name = value.get("object_module")
        return isinstance(module_name, str) and module_name.startswith(
            FORBIDDEN_EXTERNAL_READONLY_MODULE_PREFIXES
        )
    return False


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _ordered_unique(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def _without_none(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}


__all__ = [
    "EXTERNAL_READONLY_FETCH_DECISION_SOURCE",
    "EXTERNAL_READONLY_FETCH_RESPONSE_SOURCE",
    "ExternalReadonlyFetchGatewayProjection",
    "ExternalReadonlyFetchGatewayExecutionResult",
    "ExternalReadonlyFetchGatewayInput",
    "build_external_readonly_fetch_gateway_projection",
    "build_external_readonly_fetch_gateway_request",
    "execute_external_readonly_fetch_gateway_request",
    "run_external_readonly_fetch_gateway_request",
]
