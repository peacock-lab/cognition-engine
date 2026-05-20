"""external-readonly readonly refs product entry for product_gateway."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from contract_core.external_readonly_evidence import (
    ExternalReadonlyEvidenceReadonlyPublicRefs,
    external_readonly_evidence_readonly_public_refs_status_dict,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator

from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayExecutionMode,
    ProductGatewayInputRefs,
    ProductGatewayOutputRefs,
    ProductGatewayRequest,
    ProductGatewayResponse,
    ProductGatewayStatus,
)
from product_gateway.external_readonly_refs_projection import (
    EXTERNAL_READONLY_READONLY_PUBLIC_REFS_PURPOSE,
    project_external_readonly_readonly_public_refs_to_product_gateway_output_refs,
)
from product_gateway.response_summary_projection import (
    project_product_gateway_response_summary,
)


EXTERNAL_READONLY_REFS_RESPONSE_SOURCE = "product_gateway.external_readonly_refs"
EXTERNAL_READONLY_REFS_PURPOSE = EXTERNAL_READONLY_READONLY_PUBLIC_REFS_PURPOSE
EXTERNAL_READONLY_REFS_EMPTY_WARNING = (
    "external_readonly_readonly_public_refs_empty"
)
EXTERNAL_READONLY_REFS_BLOCKED_REASON = (
    "external_readonly_readonly_public_refs_blocked"
)

_FORBIDDEN_EXTERNAL_READONLY_REFS_METADATA_KEYS = frozenset(
    {
        "authorization",
        "body",
        "config" + "_assembly",
        "config" + "_context",
        "config" + "_contexts",
        "content_hash",
        "cookie",
        "headers",
        "html",
        "object_module",
        "password",
        "raw_html",
        "raw_payload",
        "raw_response",
        "response_headers",
        "sanitized_excerpt_preview",
        "secret",
        "set_cookie",
        "source_urls",
        "token",
    }
)


class ExternalReadonlyRefsGatewayInput(BaseModel):
    """Sanitized readonly refs accepted by product_gateway."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    request_id: str = Field(..., min_length=1)
    readonly_public_refs: ExternalReadonlyEvidenceReadonlyPublicRefs | Mapping[str, Any]
    governance_summary_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_external_readonly_refs_input(
        self,
    ) -> "ExternalReadonlyRefsGatewayInput":
        _raise_if_forbidden_external_readonly_refs_metadata(
            self.metadata,
            field_name="external_readonly_refs_gateway_input.metadata",
        )
        _output_refs_and_status(self.readonly_public_refs)
        return self


class ExternalReadonlyRefsGatewayProjection(BaseModel):
    """Product-normalized readonly refs projection without source payloads."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1)
    entry_kind: str = Field(..., min_length=1)
    execution_mode: str = Field(..., min_length=1)
    governance_summary_ref: str | None = None
    payload_type: str = Field(..., min_length=1)
    payload_version: str = Field(..., min_length=1)
    readonly_refs_status: str = Field(..., min_length=1)
    reference_review_ready: bool = False
    allowed_for_model_context: bool = False
    candidate_count: int = Field(default=0, ge=0)
    evidence_ref_count: int = Field(default=0, ge=0)
    observation_ref_count: int = Field(default=0, ge=0)
    blocking_reason_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class ExternalReadonlyRefsGatewayExecutionResult:
    """Summary-only execution result for cross-package product application use."""

    product_response_summary: dict[str, Any]


def build_external_readonly_refs_gateway_request(
    gateway_input: ExternalReadonlyRefsGatewayInput | Mapping[str, Any],
) -> ProductGatewayRequest:
    """Build a product-level readonly refs request."""

    normalized_input = _coerce_gateway_input(gateway_input)
    _, status = _output_refs_and_status(normalized_input.readonly_public_refs)
    return ProductGatewayRequest(
        request_id=normalized_input.request_id,
        entry_kind=ProductGatewayEntryKind.EXTERNAL_READONLY_REFS,
        execution_mode=ProductGatewayExecutionMode.NO_LIVE,
        input_payload=_compact_request_payload(status),
        input_refs=ProductGatewayInputRefs(
            governance_summary_ref=normalized_input.governance_summary_ref,
        ),
        metadata=_request_metadata(normalized_input, status),
    )


def build_external_readonly_refs_gateway_projection(
    gateway_input: ExternalReadonlyRefsGatewayInput | Mapping[str, Any],
) -> ExternalReadonlyRefsGatewayProjection:
    """Build a compact readonly refs projection without source payloads."""

    normalized_input = _coerce_gateway_input(gateway_input)
    gateway_request = build_external_readonly_refs_gateway_request(normalized_input)
    _, status = _output_refs_and_status(normalized_input.readonly_public_refs)
    facts = _facts(status)
    return ExternalReadonlyRefsGatewayProjection(
        request_id=gateway_request.request_id,
        entry_kind=gateway_request.entry_kind.value,
        execution_mode=gateway_request.execution_mode.value,
        governance_summary_ref=normalized_input.governance_summary_ref,
        payload_type=str(status["payload_type"]),
        payload_version=str(status["payload_version"]),
        readonly_refs_status=str(facts["status"]),
        reference_review_ready=facts.get("reference_review_ready") is True,
        allowed_for_model_context=(
            facts.get("allowed_for_model_context") is True
        ),
        candidate_count=_int_value(facts.get("candidate_count")),
        evidence_ref_count=len(
            _list_value(status.get("external_readonly_evidence_refs"))
        ),
        observation_ref_count=len(
            _list_value(status.get("external_readonly_evidence_observation_refs"))
        ),
        blocking_reason_count=len(_list_value(facts.get("blocking_reasons"))),
        warning_count=len(_list_value(facts.get("warnings"))),
        metadata=dict(gateway_request.metadata),
    )


def run_external_readonly_refs_gateway_request(
    gateway_input: ExternalReadonlyRefsGatewayInput | Mapping[str, Any],
) -> ProductGatewayResponse:
    """Normalize readonly external evidence refs into ProductGatewayResponse."""

    normalized_input = _coerce_gateway_input(gateway_input)
    gateway_request = build_external_readonly_refs_gateway_request(normalized_input)
    output_refs, status = _output_refs_and_status(normalized_input.readonly_public_refs)
    facts = _facts(status)
    response_status = _response_status(facts)
    return ProductGatewayResponse(
        request_id=gateway_request.request_id,
        entry_kind=gateway_request.entry_kind,
        status=response_status,
        exit_code=_exit_code_for_status(response_status),
        blocking_reasons=_response_blocking_reasons(facts, response_status),
        warnings=_response_warnings(facts),
        output_refs=ProductGatewayOutputRefs(
            governance_summary_ref=normalized_input.governance_summary_ref,
            evidence_refs=output_refs.evidence_refs,
            additional_refs=output_refs.additional_refs,
        ),
        governance_summary_ref=normalized_input.governance_summary_ref,
        evidence_refs=output_refs.evidence_refs,
        metadata=_response_metadata(normalized_input, status),
    )


def execute_external_readonly_refs_gateway_request(
    gateway_input: ExternalReadonlyRefsGatewayInput | Mapping[str, Any],
) -> ExternalReadonlyRefsGatewayExecutionResult:
    """Run readonly refs and return only the public response summary."""

    product_response = run_external_readonly_refs_gateway_request(gateway_input)
    return ExternalReadonlyRefsGatewayExecutionResult(
        product_response_summary=project_product_gateway_response_summary(
            product_response
        )
    )


def _coerce_gateway_input(
    gateway_input: ExternalReadonlyRefsGatewayInput | Mapping[str, Any],
) -> ExternalReadonlyRefsGatewayInput:
    if isinstance(gateway_input, ExternalReadonlyRefsGatewayInput):
        return gateway_input
    return ExternalReadonlyRefsGatewayInput.model_validate(dict(gateway_input))


def _output_refs_and_status(
    readonly_public_refs: ExternalReadonlyEvidenceReadonlyPublicRefs
    | Mapping[str, Any],
) -> tuple[ProductGatewayOutputRefs, dict[str, Any]]:
    output_refs = (
        project_external_readonly_readonly_public_refs_to_product_gateway_output_refs(
            readonly_public_refs
        )
    )
    status = external_readonly_evidence_readonly_public_refs_status_dict(
        readonly_public_refs
    )
    return output_refs, status


def _compact_request_payload(status: Mapping[str, Any]) -> dict[str, Any]:
    facts = _facts(status)
    return {
        "payload_type": str(status["payload_type"]),
        "payload_version": str(status["payload_version"]),
        "readonly_refs_status": str(facts["status"]),
        "reference_review_ready": facts.get("reference_review_ready") is True,
        "allowed_for_model_context": (
            facts.get("allowed_for_model_context") is True
        ),
        "candidate_count": _int_value(facts.get("candidate_count")),
        "external_readonly_evidence_ref_count": len(
            _list_value(status.get("external_readonly_evidence_refs"))
        ),
        "external_readonly_evidence_observation_ref_count": len(
            _list_value(status.get("external_readonly_evidence_observation_refs"))
        ),
        "blocking_reason_count": len(_list_value(facts.get("blocking_reasons"))),
        "warning_count": len(_list_value(facts.get("warnings"))),
        "readonly": True,
        "refs_only": True,
        "candidate_only": True,
    }


def _request_metadata(
    gateway_input: ExternalReadonlyRefsGatewayInput,
    status: Mapping[str, Any],
) -> dict[str, Any]:
    metadata = dict(gateway_input.metadata)
    metadata.update(_status_metadata(status))
    metadata["source"] = EXTERNAL_READONLY_REFS_RESPONSE_SOURCE
    return _without_none(metadata)


def _response_metadata(
    gateway_input: ExternalReadonlyRefsGatewayInput,
    status: Mapping[str, Any],
) -> dict[str, Any]:
    metadata = dict(gateway_input.metadata)
    metadata.update(_status_metadata(status))
    metadata["source"] = EXTERNAL_READONLY_REFS_RESPONSE_SOURCE
    return _without_none(metadata)


def _status_metadata(status: Mapping[str, Any]) -> dict[str, Any]:
    facts = _facts(status)
    raw_boundary_flags = _mapping(facts.get("raw_boundary_flags"))
    return {
        "payload_type": str(status["payload_type"]),
        "payload_version": str(status["payload_version"]),
        "readonly_refs_status": str(facts["status"]),
        "candidate_count": _int_value(facts.get("candidate_count")),
        "reference_review_ready": facts.get("reference_review_ready") is True,
        "allowed_for_model_context": (
            facts.get("allowed_for_model_context") is True
        ),
        "evidence_ref_count": len(
            _list_value(status.get("external_readonly_evidence_refs"))
        ),
        "observation_ref_count": len(
            _list_value(status.get("external_readonly_evidence_observation_refs"))
        ),
        "blocking_reason_count": len(_list_value(facts.get("blocking_reasons"))),
        "warning_count": len(_list_value(facts.get("warnings"))),
        "readonly": True,
        "refs_only": True,
        "candidate_only": True,
        "raw_response_included": (
            raw_boundary_flags.get("raw_response_included") is True
        ),
        "raw_html_included": raw_boundary_flags.get("raw_html_included") is True,
        "response_headers_included": (
            raw_boundary_flags.get("response_headers_included") is True
        ),
    }


def _response_status(facts: Mapping[str, Any]) -> ProductGatewayStatus:
    status = str(facts["status"])
    if status == "blocked":
        return ProductGatewayStatus.BLOCKED
    if status == "empty":
        return ProductGatewayStatus.SKIPPED
    return ProductGatewayStatus.SUCCESS


def _exit_code_for_status(status: ProductGatewayStatus) -> int:
    if status is ProductGatewayStatus.BLOCKED:
        return 2
    if status is ProductGatewayStatus.FAILED:
        return 1
    return 0


def _response_blocking_reasons(
    facts: Mapping[str, Any],
    status: ProductGatewayStatus,
) -> list[str]:
    if status is not ProductGatewayStatus.BLOCKED:
        return []
    blocking_reasons = [
        str(value) for value in _list_value(facts.get("blocking_reasons"))
    ]
    return blocking_reasons or [EXTERNAL_READONLY_REFS_BLOCKED_REASON]


def _response_warnings(facts: Mapping[str, Any]) -> list[str]:
    warnings = [str(value) for value in _list_value(facts.get("warnings"))]
    if (
        facts.get("status") == "empty"
        and EXTERNAL_READONLY_REFS_EMPTY_WARNING not in warnings
    ):
        warnings.append(EXTERNAL_READONLY_REFS_EMPTY_WARNING)
    return warnings


def _raise_if_forbidden_external_readonly_refs_metadata(
    value: Mapping[str, Any],
    *,
    field_name: str,
) -> None:
    violations: list[str] = []

    def visit(item: Any, item_path: str) -> None:
        if isinstance(item, Mapping):
            for raw_key, raw_value in item.items():
                key = _normalize_key(raw_key)
                next_path = f"{item_path}.{raw_key}"
                if _forbidden_metadata_key(key):
                    violations.append(next_path)
                visit(raw_value, next_path)
        elif isinstance(item, list | tuple):
            for index, raw_value in enumerate(item):
                visit(raw_value, f"{item_path}[{index}]")

    visit(value, "$")
    if violations:
        joined = ", ".join(violations)
        raise ValueError(f"{field_name} contains forbidden keys: {joined}")


def _forbidden_metadata_key(key: str) -> bool:
    return (
        key in _FORBIDDEN_EXTERNAL_READONLY_REFS_METADATA_KEYS
        or key.endswith("_token")
        or key.endswith("_secret")
        or key.endswith("_credential")
    )


def _facts(status: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(status.get("external_readonly_evidence_readonly_facts"))


def _list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int_value(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _normalize_key(value: Any) -> str:
    return str(value).strip().replace("-", "_").replace(" ", "_").lower()


def _without_none(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}


__all__ = [
    "EXTERNAL_READONLY_REFS_BLOCKED_REASON",
    "EXTERNAL_READONLY_REFS_EMPTY_WARNING",
    "EXTERNAL_READONLY_REFS_PURPOSE",
    "EXTERNAL_READONLY_REFS_RESPONSE_SOURCE",
    "ExternalReadonlyRefsGatewayExecutionResult",
    "ExternalReadonlyRefsGatewayInput",
    "ExternalReadonlyRefsGatewayProjection",
    "build_external_readonly_refs_gateway_projection",
    "build_external_readonly_refs_gateway_request",
    "execute_external_readonly_refs_gateway_request",
    "run_external_readonly_refs_gateway_request",
]
