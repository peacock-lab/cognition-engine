"""cognition-run product entry normalization for product_gateway."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayExecutionMode,
    ProductGatewayInputRefs,
    ProductGatewayLiveOptions,
    ProductGatewayOperatorApprovalRef,
    ProductGatewayOutputRefs,
    ProductGatewayRef,
    ProductGatewayRequest,
    ProductGatewayResponse,
    ProductGatewayStatus,
)
from runtime_container.controlled_run_facade import (
    ControlledRunFacadeInput,
    ControlledRunFacadeResult,
    run_controlled_run_facade,
)

DEFAULT_COGNITION_RUN_WORKFLOW_ID = "workflow-controlled-adk-run"
DEFAULT_COGNITION_RUN_WORKFLOW_NAME = "controlled-adk-run"
PRODUCT_ENTRY_DECISION_SOURCE = "explicit_product_entry"


class CognitionRunGatewayInput(BaseModel):
    """Already parsed cognition-run product entry input."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1)
    runtime_id: str = Field(..., min_length=1)
    workflow_id: str = DEFAULT_COGNITION_RUN_WORKFLOW_ID
    workflow_name: str = DEFAULT_COGNITION_RUN_WORKFLOW_NAME
    environment: str = "local"
    profile: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    operator_approved: bool = False
    approval_ref: str | None = None
    audit_ref: str | None = None
    sanitized_evidence_ref: str | None = None
    governance_summary_output_ref: str | None = None
    request_live_llm: bool = False
    request_ollama: bool = False
    allow_live_llm: bool = False
    allow_ollama: bool = False
    live_llm_approval_ref: str | None = None
    preflight_only: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class CognitionRunCompatibilityProjection(BaseModel):
    """Product-normalized field projection for a later controlled service boundary."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1)
    entry_kind: str = Field(..., min_length=1)
    execution_mode: str = Field(..., min_length=1)
    runtime_id: str = Field(..., min_length=1)
    workflow_id: str = Field(..., min_length=1)
    workflow_name: str = Field(..., min_length=1)
    environment: str = Field(..., min_length=1)
    profile: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    operator_approved: bool = False
    approval_ref: str | None = None
    audit_ref: str | None = None
    sanitized_evidence_ref: str | None = None
    governance_summary_output_ref: str | None = None
    request_live_llm: bool = False
    request_ollama: bool = False
    allow_live_llm: bool = False
    allow_ollama: bool = False
    live_llm_approval_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def build_cognition_run_gateway_request(
    gateway_input: CognitionRunGatewayInput | Mapping[str, Any],
) -> ProductGatewayRequest:
    """Build a product-level request for cognition-run without executing runtime."""

    normalized_input = _coerce_gateway_input(gateway_input)
    execution_mode = _execution_mode(normalized_input)
    live_requested = _live_fields_present(normalized_input)

    return ProductGatewayRequest(
        request_id=normalized_input.request_id,
        entry_kind=ProductGatewayEntryKind.COGNITION_RUN,
        execution_mode=execution_mode,
        input_payload=dict(normalized_input.input_payload),
        input_refs=ProductGatewayInputRefs(
            operator_approval_ref=normalized_input.approval_ref,
            audit_ref=normalized_input.audit_ref,
            sanitized_evidence_ref=normalized_input.sanitized_evidence_ref,
            governance_summary_ref=normalized_input.governance_summary_output_ref,
        ),
        operator_approval=ProductGatewayOperatorApprovalRef(
            approved=normalized_input.operator_approved,
            approval_ref=normalized_input.approval_ref,
            audit_ref=normalized_input.audit_ref,
            decision_source=PRODUCT_ENTRY_DECISION_SOURCE,
        ),
        live_options=ProductGatewayLiveOptions(
            request_live_llm=normalized_input.request_live_llm,
            request_ollama=normalized_input.request_ollama,
            allow_live_llm=normalized_input.allow_live_llm,
            allow_ollama=normalized_input.allow_ollama,
            live_llm_approval_ref=normalized_input.live_llm_approval_ref,
            override_source=PRODUCT_ENTRY_DECISION_SOURCE if live_requested else None,
        ),
        metadata=_request_metadata(normalized_input),
    )


def build_cognition_run_compatibility_projection(
    gateway_input: CognitionRunGatewayInput | Mapping[str, Any],
) -> CognitionRunCompatibilityProjection:
    """Build a compatibility projection without constructing runtime internals."""

    normalized_input = _coerce_gateway_input(gateway_input)
    gateway_request = build_cognition_run_gateway_request(normalized_input)

    return CognitionRunCompatibilityProjection(
        request_id=gateway_request.request_id,
        entry_kind=gateway_request.entry_kind.value,
        execution_mode=gateway_request.execution_mode.value,
        runtime_id=normalized_input.runtime_id,
        workflow_id=normalized_input.workflow_id,
        workflow_name=normalized_input.workflow_name,
        environment=normalized_input.environment,
        profile=normalized_input.profile,
        input_payload=dict(gateway_request.input_payload),
        operator_approved=gateway_request.operator_approval.approved,
        approval_ref=gateway_request.operator_approval.approval_ref,
        audit_ref=gateway_request.operator_approval.audit_ref,
        sanitized_evidence_ref=(
            gateway_request.input_refs.sanitized_evidence_ref
        ),
        governance_summary_output_ref=(
            gateway_request.input_refs.governance_summary_ref
        ),
        request_live_llm=gateway_request.live_options.request_live_llm,
        request_ollama=gateway_request.live_options.request_ollama,
        allow_live_llm=gateway_request.live_options.allow_live_llm,
        allow_ollama=gateway_request.live_options.allow_ollama,
        live_llm_approval_ref=(
            gateway_request.live_options.live_llm_approval_ref
        ),
        metadata=dict(gateway_request.metadata),
    )


def run_cognition_run_gateway_request(
    gateway_input: CognitionRunGatewayInput | Mapping[str, Any],
) -> ProductGatewayResponse:
    """Run cognition-run through the runtime-container public controlled facade."""

    gateway_request = build_cognition_run_gateway_request(gateway_input)
    projection = build_cognition_run_compatibility_projection(gateway_input)
    facade_input = _controlled_run_facade_input_from_projection(projection)
    facade_result = run_controlled_run_facade(facade_input)
    return _product_gateway_response_from_facade_result(
        gateway_request=gateway_request,
        facade_result=facade_result,
    )


def _coerce_gateway_input(
    gateway_input: CognitionRunGatewayInput | Mapping[str, Any],
) -> CognitionRunGatewayInput:
    if isinstance(gateway_input, CognitionRunGatewayInput):
        return gateway_input
    return CognitionRunGatewayInput.model_validate(dict(gateway_input))


def _execution_mode(
    gateway_input: CognitionRunGatewayInput,
) -> ProductGatewayExecutionMode:
    if gateway_input.preflight_only:
        return ProductGatewayExecutionMode.PREFLIGHT_ONLY
    if _live_fields_present(gateway_input):
        return ProductGatewayExecutionMode.CONTROLLED_LIVE
    return ProductGatewayExecutionMode.NO_LIVE


def _live_fields_present(gateway_input: CognitionRunGatewayInput) -> bool:
    return any(
        (
            gateway_input.request_live_llm,
            gateway_input.request_ollama,
            gateway_input.allow_live_llm,
            gateway_input.allow_ollama,
            bool(gateway_input.live_llm_approval_ref),
        )
    )


def _request_metadata(gateway_input: CognitionRunGatewayInput) -> dict[str, Any]:
    metadata = dict(gateway_input.metadata)
    metadata.update(
        {
            "source": "product_gateway.cognition_run",
            "runtime_id": gateway_input.runtime_id,
            "workflow_id": gateway_input.workflow_id,
            "workflow_name": gateway_input.workflow_name,
            "environment": gateway_input.environment,
            "profile": gateway_input.profile,
        }
    )
    return metadata


def _controlled_run_facade_input_from_projection(
    projection: CognitionRunCompatibilityProjection,
) -> ControlledRunFacadeInput:
    return ControlledRunFacadeInput(
        runtime_id=projection.runtime_id,
        environment=projection.environment,
        profile=projection.profile,
        invocation_id=projection.request_id,
        workflow_id=projection.workflow_id,
        workflow_name=projection.workflow_name,
        input_payload=dict(projection.input_payload),
        operator_approved=projection.operator_approved,
        approval_ref=projection.approval_ref,
        audit_ref=projection.audit_ref,
        sanitized_evidence_ref=projection.sanitized_evidence_ref,
        governance_summary_output_ref=projection.governance_summary_output_ref,
        request_live_llm=projection.request_live_llm,
        request_ollama=projection.request_ollama,
        allow_live_llm=projection.allow_live_llm,
        allow_ollama=projection.allow_ollama,
        live_llm_approval_ref=projection.live_llm_approval_ref,
        metadata=dict(projection.metadata),
    )


def _product_gateway_response_from_facade_result(
    *,
    gateway_request: ProductGatewayRequest,
    facade_result: ControlledRunFacadeResult,
) -> ProductGatewayResponse:
    status = _response_status(facade_result)
    evidence_refs = _refs_from_result(
        facade_result,
        ("sanitized_evidence_ref",),
        kind="sanitized_evidence",
        purpose="cognition_run",
    )
    audit_refs = _refs_from_result(
        facade_result,
        ("audit_ref",),
        kind="audit",
        purpose="cognition_run",
    )
    tool_audit_refs = _refs_from_result(
        facade_result,
        ("tool_evidence_ref", "tool_run_ref"),
        kind="tool_audit",
        purpose="cognition_run",
    )
    governance_summary_ref = (
        facade_result.governance_summary_payload_ref
        or facade_result.governance_summary_output_ref
    )

    return ProductGatewayResponse(
        request_id=gateway_request.request_id,
        entry_kind=gateway_request.entry_kind,
        status=status,
        exit_code=_exit_code_for_status(status),
        blocking_reasons=list(facade_result.blocking_reasons),
        warnings=list(facade_result.warnings),
        output_refs=ProductGatewayOutputRefs(
            governance_summary_ref=governance_summary_ref,
            evidence_refs=evidence_refs,
            audit_refs=audit_refs,
            tool_audit_refs=tool_audit_refs,
        ),
        governance_summary_ref=governance_summary_ref,
        evidence_refs=evidence_refs,
        audit_refs=audit_refs,
        tool_audit_refs=tool_audit_refs,
        metadata=_response_metadata(facade_result),
    )


def _response_status(facade_result: ControlledRunFacadeResult) -> ProductGatewayStatus:
    if facade_result.status == "blocked":
        return ProductGatewayStatus.BLOCKED
    if facade_result.status == "success":
        return ProductGatewayStatus.SUCCESS
    return ProductGatewayStatus.FAILED


def _exit_code_for_status(status: ProductGatewayStatus) -> int:
    if status is ProductGatewayStatus.SUCCESS:
        return 0
    if status is ProductGatewayStatus.BLOCKED:
        return 2
    return 1


def _refs_from_result(
    facade_result: ControlledRunFacadeResult,
    keys: tuple[str, ...],
    *,
    kind: str,
    purpose: str,
) -> list[ProductGatewayRef]:
    refs: list[ProductGatewayRef] = []
    for key in keys:
        ref = _optional_text(getattr(facade_result, key))
        if ref:
            refs.append(
                ProductGatewayRef(
                    ref=ref,
                    kind=kind,
                    purpose=purpose,
                    metadata={"source_key": key},
                )
            )
    return refs


def _response_metadata(facade_result: ControlledRunFacadeResult) -> dict[str, Any]:
    metadata = {
        "source": "product_gateway.cognition_run",
        "runtime_facade": "runtime_container.controlled_run_facade",
        "runtime_id": facade_result.runtime_id,
        "invocation_id": facade_result.invocation_id,
        "workflow_id": facade_result.workflow_id,
        "execution_mode": facade_result.execution_mode,
        "controlled_run": facade_result.controlled_run,
        "productized_controlled_run": facade_result.productized_controlled_run,
        "sanitized": facade_result.sanitized,
        "adk_run_allowed": facade_result.adk_run_allowed,
        "adk_run_performed": facade_result.adk_run_performed,
        "execution_performed": facade_result.execution_performed,
        "live_llm_allowed": facade_result.live_llm_allowed,
        "live_llm_call_performed": facade_result.live_llm_call_performed,
        "ollama_allowed": facade_result.ollama_allowed,
        "ollama_call_performed": facade_result.ollama_call_performed,
        "tool_status": facade_result.tool_status,
        "tool_failure_type": facade_result.tool_failure_type,
        "tool_runtime_call_performed": facade_result.tool_runtime_call_performed,
        "observability_source": facade_result.observability_source,
    }
    return {key: value for key, value in metadata.items() if value is not None}


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return [str(value)]


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


__all__ = [
    "CognitionRunCompatibilityProjection",
    "CognitionRunGatewayInput",
    "DEFAULT_COGNITION_RUN_WORKFLOW_ID",
    "DEFAULT_COGNITION_RUN_WORKFLOW_NAME",
    "PRODUCT_ENTRY_DECISION_SOURCE",
    "build_cognition_run_compatibility_projection",
    "build_cognition_run_gateway_request",
    "run_cognition_run_gateway_request",
]
