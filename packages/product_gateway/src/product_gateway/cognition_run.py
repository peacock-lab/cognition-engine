"""cognition-run product entry normalization for product_gateway."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from config_contexts.runtime import (
    RuntimeConfigSelectionContext,
    RuntimeLiveLlmInvocationOptionsContext,
)
from contract_core.controlled_execution import (
    ControlledExecutionRequestSchema,
    ControlledExecutionRuntimeService,
    ControlledExecutionRuntimeSummarySchema,
)
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
from product_gateway.response_summary_projection import (
    project_product_gateway_response_summary,
)

DEFAULT_COGNITION_RUN_WORKFLOW_ID = "workflow-controlled-adk-run"
DEFAULT_COGNITION_RUN_WORKFLOW_NAME = "controlled-adk-run"
PRODUCT_ENTRY_DECISION_SOURCE = "explicit_product_entry"
RUNTIME_SERVICE_NOT_INJECTED_REF = "runtime_service_not_injected"
RUNTIME_SERVICE_NOT_INJECTED_BLOCKING_REASON = (
    "controlled_execution_runtime_service_not_injected"
)
RUNTIME_SERVICE_NOT_INJECTED_EXECUTION_MODE = (
    "product_gateway_runtime_service_missing"
)


class CognitionRunGatewayInput(BaseModel):
    """Already parsed cognition-run product entry input."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1)
    runtime_id: str = Field(..., min_length=1)
    config_root: str | None = None
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
    ollama_api_base: str | None = None
    live_llm_timeout_seconds: int | None = None
    live_llm_max_tokens: int | None = None
    response_preview_limit: int | None = None
    preflight_only: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class CognitionRunGatewayExecutionResult:
    """Product gateway execution result plus the sanitized runtime summary."""

    product_request: ProductGatewayRequest
    product_response: ProductGatewayResponse
    product_response_summary: dict[str, Any]
    runtime_summary: ControlledExecutionRuntimeSummarySchema


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


def build_cognition_run_controlled_execution_request(
    gateway_input: CognitionRunGatewayInput | Mapping[str, Any],
) -> ControlledExecutionRequestSchema:
    """Build the public controlled execution request contract."""

    normalized_input = _coerce_gateway_input(gateway_input)
    gateway_request = build_cognition_run_gateway_request(normalized_input)

    return ControlledExecutionRequestSchema(
        runtime_id=normalized_input.runtime_id,
        invocation_id=gateway_request.request_id,
        workflow_id=normalized_input.workflow_id,
        workflow_name=normalized_input.workflow_name,
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
        metadata=_controlled_execution_request_metadata(gateway_request),
    )


def build_cognition_run_config_selection(
    gateway_input: CognitionRunGatewayInput | Mapping[str, Any],
) -> RuntimeConfigSelectionContext:
    """Build the runtime config selection contract for cognition-run."""

    normalized_input = _coerce_gateway_input(gateway_input)
    return RuntimeConfigSelectionContext(
        config_root=normalized_input.config_root,
        environment=normalized_input.environment,
        profile=normalized_input.profile,
        selection_source=PRODUCT_ENTRY_DECISION_SOURCE,
        metadata={"source": "product_gateway.cognition_run"},
    )


def build_cognition_run_live_llm_options(
    gateway_input: CognitionRunGatewayInput | Mapping[str, Any],
) -> RuntimeLiveLlmInvocationOptionsContext:
    """Build the runtime live LLM invocation options contract."""

    normalized_input = _coerce_gateway_input(gateway_input)
    return RuntimeLiveLlmInvocationOptionsContext(
        ollama_api_base=normalized_input.ollama_api_base,
        timeout_seconds=normalized_input.live_llm_timeout_seconds,
        max_tokens=normalized_input.live_llm_max_tokens,
        response_preview_limit=normalized_input.response_preview_limit,
        selection_source=(
            "cognition_cli.run.gateway"
            if _is_cli_input(normalized_input)
            else "product_gateway.cognition_run"
        ),
        metadata={
            "cli_command": normalized_input.metadata.get("cli_command"),
            "cli_controlled_live": _is_cli_input(normalized_input),
        },
    )


def run_cognition_run_gateway_request(
    gateway_input: CognitionRunGatewayInput | Mapping[str, Any],
    *,
    runtime_service: ControlledExecutionRuntimeService | None = None,
    runtime_service_ref: str | None = None,
) -> ProductGatewayResponse:
    """Run cognition-run through an explicitly injected runtime service."""

    return execute_cognition_run_gateway_request(
        gateway_input,
        runtime_service=runtime_service,
        runtime_service_ref=runtime_service_ref,
    ).product_response


def execute_cognition_run_gateway_request(
    gateway_input: CognitionRunGatewayInput | Mapping[str, Any],
    *,
    runtime_service: ControlledExecutionRuntimeService | None = None,
    runtime_service_ref: str | None = None,
) -> CognitionRunGatewayExecutionResult:
    """Execute cognition-run and retain both product and runtime summaries."""

    normalized_input = _coerce_gateway_input(gateway_input)
    gateway_request = build_cognition_run_gateway_request(gateway_input)
    controlled_request = build_cognition_run_controlled_execution_request(
        normalized_input
    )
    config_selection = build_cognition_run_config_selection(
        normalized_input
    )
    live_llm_options = build_cognition_run_live_llm_options(normalized_input)
    if runtime_service is None:
        runtime_summary = _runtime_service_not_injected_summary(
            controlled_request
        )
    else:
        runtime_summary = runtime_service(
            controlled_request,
            config_selection=config_selection,
            live_llm_options=live_llm_options,
        )
    product_response = _product_gateway_response_from_runtime_summary(
        gateway_request=gateway_request,
        runtime_summary=runtime_summary,
        runtime_service_ref=_runtime_service_ref(
            runtime_service,
            runtime_service_ref=runtime_service_ref,
        ),
    )
    product_response_summary = project_product_gateway_response_summary(
        product_response
    )
    return CognitionRunGatewayExecutionResult(
        product_request=gateway_request,
        product_response=product_response,
        product_response_summary=product_response_summary,
        runtime_summary=runtime_summary,
    )


def _is_cli_input(gateway_input: CognitionRunGatewayInput) -> bool:
    return str(gateway_input.metadata.get("source", "")).startswith("cognition_cli")


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


def _controlled_execution_request_metadata(
    gateway_request: ProductGatewayRequest,
) -> dict[str, Any]:
    return {
        "source": "product_gateway.cognition_run",
        "product_request_id": gateway_request.request_id,
        "entry_kind": gateway_request.entry_kind.value,
        "execution_mode": gateway_request.execution_mode.value,
    }


def _runtime_service_not_injected_summary(
    controlled_request: ControlledExecutionRequestSchema,
) -> ControlledExecutionRuntimeSummarySchema:
    return ControlledExecutionRuntimeSummarySchema(
        runtime_id=controlled_request.runtime_id,
        invocation_id=controlled_request.invocation_id,
        workflow_id=controlled_request.workflow_id,
        execution_mode=RUNTIME_SERVICE_NOT_INJECTED_EXECUTION_MODE,
        status="blocked",
        sanitized=True,
        adk_run_allowed=False,
        adk_run_performed=False,
        execution_performed=False,
        live_llm_allowed=False,
        live_llm_call_performed=False,
        ollama_allowed=False,
        ollama_call_performed=False,
        sanitized_evidence_ref=controlled_request.sanitized_evidence_ref,
        audit_ref=controlled_request.audit_ref,
        governance_summary_output_ref=(
            controlled_request.governance_summary_output_ref
        ),
        blocking_reasons=(RUNTIME_SERVICE_NOT_INJECTED_BLOCKING_REASON,),
        warnings=("runtime_service_required_for_cognition_run",),
    )


def _product_gateway_response_from_runtime_summary(
    *,
    gateway_request: ProductGatewayRequest,
    runtime_summary: ControlledExecutionRuntimeSummarySchema,
    runtime_service_ref: str,
) -> ProductGatewayResponse:
    status = _response_status(runtime_summary)
    evidence_refs = _refs_from_result(
        runtime_summary,
        ("sanitized_evidence_ref",),
        kind="sanitized_evidence",
        purpose="cognition_run",
    )
    audit_refs = _refs_from_result(
        runtime_summary,
        ("audit_ref",),
        kind="audit",
        purpose="cognition_run",
    )
    tool_audit_refs = _refs_from_result(
        runtime_summary,
        ("tool_evidence_ref", "tool_run_ref"),
        kind="tool_audit",
        purpose="cognition_run",
    )
    governance_summary_ref = (
        runtime_summary.governance_summary_payload_ref
        or runtime_summary.governance_summary_output_ref
    )

    return ProductGatewayResponse(
        request_id=gateway_request.request_id,
        entry_kind=gateway_request.entry_kind,
        status=status,
        exit_code=_exit_code_for_status(status),
        blocking_reasons=list(runtime_summary.blocking_reasons),
        warnings=list(runtime_summary.warnings),
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
        metadata=_response_metadata(
            runtime_summary,
            runtime_service_ref=runtime_service_ref,
        ),
    )


def _response_status(
    runtime_summary: ControlledExecutionRuntimeSummarySchema,
) -> ProductGatewayStatus:
    if runtime_summary.status == "blocked":
        return ProductGatewayStatus.BLOCKED
    if runtime_summary.status == "success":
        return ProductGatewayStatus.SUCCESS
    return ProductGatewayStatus.FAILED


def _exit_code_for_status(status: ProductGatewayStatus) -> int:
    if status is ProductGatewayStatus.SUCCESS:
        return 0
    if status is ProductGatewayStatus.BLOCKED:
        return 2
    return 1


def _refs_from_result(
    runtime_summary: ControlledExecutionRuntimeSummarySchema,
    keys: tuple[str, ...],
    *,
    kind: str,
    purpose: str,
) -> list[ProductGatewayRef]:
    refs: list[ProductGatewayRef] = []
    for key in keys:
        ref = _optional_text(getattr(runtime_summary, key))
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


def _response_metadata(
    runtime_summary: ControlledExecutionRuntimeSummarySchema,
    *,
    runtime_service_ref: str,
) -> dict[str, Any]:
    metadata = {
        "source": "product_gateway.cognition_run",
        "runtime_service": runtime_service_ref,
        "runtime_id": runtime_summary.runtime_id,
        "invocation_id": runtime_summary.invocation_id,
        "workflow_id": runtime_summary.workflow_id,
        "execution_mode": runtime_summary.execution_mode,
        "controlled_run": runtime_summary.controlled_run,
        "productized_controlled_run": runtime_summary.productized_controlled_run,
        "sanitized": runtime_summary.sanitized,
        "adk_run_allowed": runtime_summary.adk_run_allowed,
        "adk_run_performed": runtime_summary.adk_run_performed,
        "execution_performed": runtime_summary.execution_performed,
        "live_llm_allowed": runtime_summary.live_llm_allowed,
        "live_llm_call_performed": runtime_summary.live_llm_call_performed,
        "ollama_allowed": runtime_summary.ollama_allowed,
        "ollama_call_performed": runtime_summary.ollama_call_performed,
        "tool_status": runtime_summary.tool_status,
        "tool_failure_type": runtime_summary.tool_failure_type,
        "tool_runtime_call_performed": runtime_summary.tool_runtime_call_performed,
        "observability_source": runtime_summary.observability_source,
    }
    return {key: value for key, value in metadata.items() if value is not None}


def _runtime_service_ref(
    runtime_service: ControlledExecutionRuntimeService | None,
    *,
    runtime_service_ref: str | None,
) -> str:
    if runtime_service_ref:
        return runtime_service_ref
    if runtime_service is None:
        return RUNTIME_SERVICE_NOT_INJECTED_REF
    module = getattr(runtime_service, "__module__", None)
    qualname = getattr(runtime_service, "__qualname__", None)
    if isinstance(module, str) and isinstance(qualname, str):
        return f"{module}.{qualname}"
    return type(runtime_service).__name__


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


__all__ = [
    "CognitionRunGatewayInput",
    "CognitionRunGatewayExecutionResult",
    "DEFAULT_COGNITION_RUN_WORKFLOW_ID",
    "DEFAULT_COGNITION_RUN_WORKFLOW_NAME",
    "PRODUCT_ENTRY_DECISION_SOURCE",
    "RUNTIME_SERVICE_NOT_INJECTED_BLOCKING_REASON",
    "RUNTIME_SERVICE_NOT_INJECTED_REF",
    "build_cognition_run_config_selection",
    "build_cognition_run_controlled_execution_request",
    "build_cognition_run_live_llm_options",
    "build_cognition_run_gateway_request",
    "execute_cognition_run_gateway_request",
    "run_cognition_run_gateway_request",
]
