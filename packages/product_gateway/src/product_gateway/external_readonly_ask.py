"""external-readonly question-answering product entry summary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from schemas.evidence_summary_answer import (
    EVIDENCE_SUMMARY_ANSWER_ARTIFACT_REF_PREFIX,
    EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_REF_PREFIX,
    EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX,
)

from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayExecutionMode,
    ProductGatewayInputRefs,
    ProductGatewayLiveOptions,
    ProductGatewayOutputRefs,
    ProductGatewayRef,
    ProductGatewayRequest,
    ProductGatewayResponse,
    ProductGatewayStatus,
)
from product_gateway.response_summary_projection import (
    project_product_gateway_response_summary,
)


EXTERNAL_READONLY_ASK_RESPONSE_SOURCE = "product_gateway.external_readonly_ask"
EXTERNAL_READONLY_ASK_PURPOSE = "external_readonly_question_answer"
EXTERNAL_READONLY_ASK_BLOCKED_REASON = "external_readonly_ask_blocked"
EXTERNAL_READONLY_ASK_INSUFFICIENT_EVIDENCE_REASON = (
    "external_readonly_ask_insufficient_evidence"
)

_FORBIDDEN_EXTERNAL_READONLY_ASK_KEYS = frozenset(
    {
        "answer",
        "answer_preview",
        "authorization",
        "body",
        "config_context",
        "content",
        "cookie",
        "credential",
        "headers",
        "html",
        "message",
        "messages",
        "password",
        "prompt",
        "provider_payload",
        "provider_response",
        "raw",
        "raw_html",
        "raw_payload",
        "raw_provider_response",
        "raw_response",
        "response",
        "response_headers",
        "response_text",
        "sanitized_excerpt_preview",
        "secret",
        "system_prompt",
        "token",
        "user_question",
    }
)
_FORBIDDEN_EXTERNAL_READONLY_ASK_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "runtime_container",
    "composition",
    "litellm",
)


class ExternalReadonlyAskGatewayInput(BaseModel):
    """Sanitized product summary facts for one external-readonly QA turn."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1)
    answer_status: str = Field(..., min_length=1)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    additional_refs: list[dict[str, Any]] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    readonly_refs_status: str | None = None
    source_url_present: bool = False
    evidence_path_count: int = Field(default=0, ge=0)
    model_name: str | None = None
    llm_call_allowed: bool = False
    llm_call_attempted: bool = False
    llm_runtime_call_performed: bool = False
    external_readonly_fetch_performed: bool = False
    external_readonly_network_call_performed: bool = False
    external_network_call_performed: bool = False
    follow_up: bool = False
    follow_up_turn_index: int | None = Field(default=None, ge=1)
    follow_up_seed_ref: str | None = None
    temporary_follow_up: bool = True
    answer_trace_ref: str | None = None
    answer_trace_status: str | None = None
    answer_trace_summary: dict[str, Any] = Field(default_factory=dict)
    answer_artifact_ref: str | None = None
    answer_artifact_status: str | None = None
    answer_artifact_summary: dict[str, Any] = Field(default_factory=dict)
    durable_session: bool = False
    memory_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_ask_input(self) -> "ExternalReadonlyAskGatewayInput":
        _raise_if_forbidden_ask_payload_found(
            {
                "metadata": self.metadata,
                "evidence_refs": self.evidence_refs,
                "additional_refs": self.additional_refs,
                "answer_trace_summary": self.answer_trace_summary,
                "answer_artifact_summary": self.answer_artifact_summary,
            },
            field_name="external_readonly_ask_gateway_input",
        )
        if self.durable_session:
            raise ValueError("external-readonly ask does not use durable sessions.")
        if self.memory_enabled:
            raise ValueError("external-readonly ask does not use Memory runtime.")
        if self.follow_up:
            if self.temporary_follow_up is not True:
                raise ValueError("external-readonly follow-up is temporary only.")
            if not (
                isinstance(self.follow_up_seed_ref, str)
                and self.follow_up_seed_ref.startswith(
                    EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_REF_PREFIX
                )
            ):
                raise ValueError("follow_up_seed_ref is required for follow-up.")
        if self.answer_trace_ref is not None and not self.answer_trace_ref.startswith(
            EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX
        ):
            raise ValueError("answer_trace_ref must be an evidence summary answer trace ref.")
        if self.answer_artifact_ref is not None and not (
            self.answer_artifact_ref.startswith(
                EVIDENCE_SUMMARY_ANSWER_ARTIFACT_REF_PREFIX
            )
        ):
            raise ValueError(
                "answer_artifact_ref must be an evidence summary answer artifact ref."
            )
        return self


@dataclass(frozen=True)
class ExternalReadonlyAskGatewayExecutionResult:
    """Product entry result that exposes only public response summary facts."""

    product_request: ProductGatewayRequest
    product_response: ProductGatewayResponse
    product_response_summary: dict[str, Any]


def build_external_readonly_ask_gateway_request(
    gateway_input: ExternalReadonlyAskGatewayInput | Mapping[str, Any],
) -> ProductGatewayRequest:
    """Build a product-level external-readonly QA request summary."""

    normalized_input = _coerce_gateway_input(gateway_input)
    return ProductGatewayRequest(
        request_id=normalized_input.request_id,
        entry_kind=ProductGatewayEntryKind.EXTERNAL_READONLY_ASK,
        execution_mode=_execution_mode(normalized_input),
        input_payload={
            "answer_status": normalized_input.answer_status,
            "readonly_refs_status": normalized_input.readonly_refs_status,
            "source_url_present": normalized_input.source_url_present,
            "evidence_path_count": normalized_input.evidence_path_count,
            "evidence_ref_count": len(normalized_input.evidence_refs),
            "additional_ref_count": len(normalized_input.additional_refs),
            "llm_call_allowed": normalized_input.llm_call_allowed,
            "llm_call_attempted": normalized_input.llm_call_attempted,
            "llm_runtime_call_performed": (
                normalized_input.llm_runtime_call_performed
            ),
            "external_readonly_fetch_performed": (
                normalized_input.external_readonly_fetch_performed
            ),
            "external_readonly_network_call_performed": (
                normalized_input.external_readonly_network_call_performed
            ),
            "follow_up": normalized_input.follow_up,
            "follow_up_turn_index": normalized_input.follow_up_turn_index,
            "follow_up_seed_ref": normalized_input.follow_up_seed_ref,
            "temporary_follow_up": normalized_input.temporary_follow_up,
            "answer_trace_ref": normalized_input.answer_trace_ref,
            "answer_trace_status": normalized_input.answer_trace_status,
            "answer_artifact_ref": normalized_input.answer_artifact_ref,
            "answer_artifact_status": normalized_input.answer_artifact_status,
            "durable_session": normalized_input.durable_session,
            "memory_enabled": normalized_input.memory_enabled,
        },
        input_refs=ProductGatewayInputRefs(),
        live_options=ProductGatewayLiveOptions(
            request_live_llm=normalized_input.llm_call_attempted,
            request_ollama=normalized_input.llm_call_attempted,
            override_source=(
                EXTERNAL_READONLY_ASK_RESPONSE_SOURCE
                if normalized_input.llm_call_attempted
                else None
            ),
        ),
        metadata=_request_metadata(normalized_input),
    )


def run_external_readonly_ask_gateway_request(
    gateway_input: ExternalReadonlyAskGatewayInput | Mapping[str, Any],
) -> ProductGatewayResponse:
    """Build the product response summary boundary for external-readonly QA."""

    normalized_input = _coerce_gateway_input(gateway_input)
    gateway_request = build_external_readonly_ask_gateway_request(normalized_input)
    status = _response_status(normalized_input)
    blocking_reasons = _blocking_reasons(normalized_input, status)
    output_refs = ProductGatewayOutputRefs(
        evidence_refs=_refs(normalized_input.evidence_refs),
        additional_refs=_refs(normalized_input.additional_refs),
    )
    return ProductGatewayResponse(
        request_id=gateway_request.request_id,
        entry_kind=gateway_request.entry_kind,
        status=status,
        exit_code=_exit_code_for_status(status),
        blocking_reasons=blocking_reasons,
        warnings=list(normalized_input.warnings),
        output_refs=output_refs,
        evidence_refs=output_refs.evidence_refs,
        metadata=_response_metadata(normalized_input),
    )


def execute_external_readonly_ask_gateway_request(
    gateway_input: ExternalReadonlyAskGatewayInput | Mapping[str, Any],
) -> ExternalReadonlyAskGatewayExecutionResult:
    """Run the product entry and return a public response summary."""

    normalized_input = _coerce_gateway_input(gateway_input)
    product_request = build_external_readonly_ask_gateway_request(normalized_input)
    product_response = run_external_readonly_ask_gateway_request(normalized_input)
    return ExternalReadonlyAskGatewayExecutionResult(
        product_request=product_request,
        product_response=product_response,
        product_response_summary=project_product_gateway_response_summary(
            product_response
        ),
    )


def _coerce_gateway_input(
    gateway_input: ExternalReadonlyAskGatewayInput | Mapping[str, Any],
) -> ExternalReadonlyAskGatewayInput:
    if isinstance(gateway_input, ExternalReadonlyAskGatewayInput):
        return gateway_input
    return ExternalReadonlyAskGatewayInput.model_validate(dict(gateway_input))


def _execution_mode(
    gateway_input: ExternalReadonlyAskGatewayInput,
) -> ProductGatewayExecutionMode:
    if gateway_input.llm_call_attempted:
        return ProductGatewayExecutionMode.CONTROLLED_LIVE
    return ProductGatewayExecutionMode.PREFLIGHT_ONLY


def _response_status(
    gateway_input: ExternalReadonlyAskGatewayInput,
) -> ProductGatewayStatus:
    if gateway_input.answer_status == "success":
        return ProductGatewayStatus.SUCCESS
    if gateway_input.answer_status in {"blocked", "insufficient_evidence"}:
        return ProductGatewayStatus.BLOCKED
    return ProductGatewayStatus.FAILED


def _blocking_reasons(
    gateway_input: ExternalReadonlyAskGatewayInput,
    status: ProductGatewayStatus,
) -> list[str]:
    reasons = list(gateway_input.blocking_reasons)
    if status is not ProductGatewayStatus.BLOCKED:
        return reasons
    if reasons:
        return reasons
    if gateway_input.answer_status == "insufficient_evidence":
        return [EXTERNAL_READONLY_ASK_INSUFFICIENT_EVIDENCE_REASON]
    return [EXTERNAL_READONLY_ASK_BLOCKED_REASON]


def _exit_code_for_status(status: ProductGatewayStatus) -> int:
    if status is ProductGatewayStatus.SUCCESS:
        return 0
    if status is ProductGatewayStatus.BLOCKED:
        return 2
    return 1


def _refs(values: Sequence[Mapping[str, Any]]) -> list[ProductGatewayRef]:
    refs: list[ProductGatewayRef] = []
    for value in values:
        ref = value.get("ref")
        kind = value.get("kind")
        if not isinstance(ref, str) or not ref:
            continue
        if not isinstance(kind, str) or not kind:
            continue
        refs.append(
            ProductGatewayRef(
                ref=ref,
                kind=kind,
                purpose=_optional_string(value.get("purpose")),
                metadata=_safe_metadata(value.get("metadata")),
            )
        )
    return refs


def _request_metadata(gateway_input: ExternalReadonlyAskGatewayInput) -> dict[str, Any]:
    return _response_metadata(gateway_input)


def _response_metadata(gateway_input: ExternalReadonlyAskGatewayInput) -> dict[str, Any]:
    metadata = {
        "source": EXTERNAL_READONLY_ASK_RESPONSE_SOURCE,
        "answer_status": gateway_input.answer_status,
        "readonly_refs_status": gateway_input.readonly_refs_status,
        "source_url_present": gateway_input.source_url_present,
        "evidence_path_count": gateway_input.evidence_path_count,
        "evidence_ref_count": len(gateway_input.evidence_refs),
        "additional_ref_count": len(gateway_input.additional_refs),
        "model_name": gateway_input.model_name,
        "llm_call_allowed": gateway_input.llm_call_allowed,
        "llm_call_attempted": gateway_input.llm_call_attempted,
        "llm_runtime_call_performed": gateway_input.llm_runtime_call_performed,
        "external_readonly_fetch_performed": (
            gateway_input.external_readonly_fetch_performed
        ),
        "external_readonly_network_call_performed": (
            gateway_input.external_readonly_network_call_performed
        ),
        "external_network_call_performed": gateway_input.external_network_call_performed,
        "follow_up": gateway_input.follow_up,
        "follow_up_turn_index": gateway_input.follow_up_turn_index,
        "follow_up_seed_ref": gateway_input.follow_up_seed_ref,
        "temporary_follow_up": gateway_input.temporary_follow_up,
        "answer_trace_ref": gateway_input.answer_trace_ref,
        "answer_trace_status": gateway_input.answer_trace_status,
        "answer_trace_summary": _safe_trace_summary(
            gateway_input.answer_trace_summary
        ),
        "answer_artifact_ref": gateway_input.answer_artifact_ref,
        "answer_artifact_status": gateway_input.answer_artifact_status,
        "answer_artifact_summary": _safe_trace_summary(
            gateway_input.answer_artifact_summary
        ),
        "durable_session": gateway_input.durable_session,
        "memory_enabled": gateway_input.memory_enabled,
        **_safe_metadata(gateway_input.metadata),
    }
    return {key: value for key, value in metadata.items() if value is not None}


def _safe_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    metadata: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            continue
        if _sensitive_text(key):
            continue
        if not isinstance(item, bool | int | float | str):
            continue
        if isinstance(item, str) and _sensitive_text(item):
            continue
        metadata[key] = item
    return metadata


def _safe_trace_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    summary: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str) or _sensitive_text(key):
            continue
        if not isinstance(item, bool | int | float | str):
            continue
        if isinstance(item, str) and _sensitive_text(item):
            continue
        summary[key] = item
    return summary


def _raise_if_forbidden_ask_payload_found(
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
    if key in _FORBIDDEN_EXTERNAL_READONLY_ASK_KEYS:
        return True
    if isinstance(value, Mapping):
        module_name = value.get("object_module")
        return isinstance(module_name, str) and module_name.startswith(
            _FORBIDDEN_EXTERNAL_READONLY_ASK_MODULE_PREFIXES
        )
    return False


def _optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _sensitive_text(value: str) -> bool:
    normalized = value.lower()
    return any(
        marker in normalized
        for marker in (
            "authorization",
            "config_context",
            "cookie",
            "header",
            "html",
            "message",
            "payload",
            "prompt",
            "raw",
            "response_text",
            "secret",
            "token",
        )
    )


__all__ = [
    "EXTERNAL_READONLY_ASK_BLOCKED_REASON",
    "EXTERNAL_READONLY_ASK_INSUFFICIENT_EVIDENCE_REASON",
    "EXTERNAL_READONLY_ASK_PURPOSE",
    "EXTERNAL_READONLY_ASK_RESPONSE_SOURCE",
    "ExternalReadonlyAskGatewayExecutionResult",
    "ExternalReadonlyAskGatewayInput",
    "build_external_readonly_ask_gateway_request",
    "execute_external_readonly_ask_gateway_request",
    "run_external_readonly_ask_gateway_request",
]
