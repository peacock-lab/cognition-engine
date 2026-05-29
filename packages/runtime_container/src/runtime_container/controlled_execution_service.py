"""Product-gateway-facing controlled execution runtime service."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config_contexts.runtime import (
    RuntimeConfigSelectionContext,
    RuntimeLiveLlmInvocationOptionsContext,
)
from contract_core.controlled_execution import (
    ControlledExecutionRequestSchema,
    ControlledExecutionRuntimeSummarySchema,
    validate_controlled_execution_request,
)
from runtime_container._controlled_run_facade import (
    ControlledRunEntryRunner,
    ControlledRunFacadeInput,
    ControlledRunFacadeResult,
    ControlledRunSupportProviders,
    DEFAULT_CONTROLLED_RUN_WORKFLOW_ID,
    DEFAULT_CONTROLLED_RUN_WORKFLOW_NAME,
    run_controlled_run_facade,
)

ControlledExecutionEntryRunner = ControlledRunEntryRunner


@dataclass(frozen=True)
class ControlledExecutionServiceInput:
    """Internal runtime service input derived from public request contracts."""

    runtime_id: str
    config_root: str | Path | None = None
    environment: str = "local"
    profile: str | None = None
    invocation_id: str | None = None
    workflow_id: str = DEFAULT_CONTROLLED_RUN_WORKFLOW_ID
    workflow_name: str = DEFAULT_CONTROLLED_RUN_WORKFLOW_NAME
    input_payload: Mapping[str, Any] | None = None
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
    allow_tool_confirmation: bool | None = None
    tool_confirmation_approval_ref: str | None = None
    tool_confirmation_decision_source: str | None = None
    metadata: Mapping[str, Any] | None = None


def run_controlled_execution_service(
    request: (
        ControlledExecutionRequestSchema
        | ControlledExecutionServiceInput
        | Mapping[str, Any]
    ),
    *,
    config_selection: RuntimeConfigSelectionContext | Mapping[str, Any] | None = None,
    live_llm_options: (
        RuntimeLiveLlmInvocationOptionsContext | Mapping[str, Any] | None
    ) = None,
    workflow_registry: Any | None = None,
    llm_invocation_service: Any | None = None,
    agent_shell_live_client: Any | None = None,
    support_providers: ControlledRunSupportProviders | None = None,
    entry_runner: ControlledExecutionEntryRunner | None = None,
) -> ControlledExecutionRuntimeSummarySchema:
    """Run controlled execution and return a product-facing runtime summary."""

    normalized_input = _coerce_service_input(
        request,
        config_selection=config_selection,
    )
    resolved_llm_invocation_service = (
        llm_invocation_service
        if llm_invocation_service is not None
        else _default_live_llm_invocation_service(
            normalized_input,
            live_llm_options=live_llm_options,
        )
    )
    facade_kwargs = {
        "workflow_registry": workflow_registry,
        "llm_invocation_service": resolved_llm_invocation_service,
        "agent_shell_live_client": agent_shell_live_client,
        "support_providers": support_providers,
    }
    if entry_runner is not None:
        facade_kwargs["entry_runner"] = entry_runner
    facade_result = run_controlled_run_facade(
        _facade_input_from_service_input(normalized_input),
        **facade_kwargs,
    )
    return _runtime_summary_from_facade_result(facade_result)


def _runtime_summary_from_facade_result(
    facade_result: ControlledRunFacadeResult,
) -> ControlledExecutionRuntimeSummarySchema:
    return ControlledExecutionRuntimeSummarySchema(
        runtime_id=facade_result.runtime_id,
        invocation_id=facade_result.invocation_id,
        workflow_id=facade_result.workflow_id,
        execution_mode=facade_result.execution_mode,
        status=facade_result.status,
        controlled_run=facade_result.controlled_run,
        productized_controlled_run=facade_result.productized_controlled_run,
        sanitized=facade_result.sanitized,
        adk_run_allowed=facade_result.adk_run_allowed,
        adk_run_performed=facade_result.adk_run_performed,
        execution_performed=facade_result.execution_performed,
        live_llm_allowed=facade_result.live_llm_allowed,
        live_llm_call_performed=facade_result.live_llm_call_performed,
        ollama_allowed=facade_result.ollama_allowed,
        ollama_call_performed=facade_result.ollama_call_performed,
        llm_invocation_call_allowed=facade_result.llm_invocation_call_allowed,
        llm_invocation_call_attempted=facade_result.llm_invocation_call_attempted,
        llm_invocation_runtime_call_performed=(
            facade_result.llm_invocation_runtime_call_performed
        ),
        llm_invocation_failure_type=facade_result.llm_invocation_failure_type,
        tool_runtime_call_performed=facade_result.tool_runtime_call_performed,
        tool_status=facade_result.tool_status,
        tool_failure_type=facade_result.tool_failure_type,
        observability_source=facade_result.observability_source,
        sanitized_evidence_ref=facade_result.sanitized_evidence_ref,
        audit_ref=facade_result.audit_ref,
        governance_summary_payload_ref=facade_result.governance_summary_payload_ref,
        governance_summary_output_ref=facade_result.governance_summary_output_ref,
        tool_evidence_ref=facade_result.tool_evidence_ref,
        tool_run_ref=facade_result.tool_run_ref,
        llm_invocation_result_ref=facade_result.llm_invocation_result_ref,
        llm_invocation_observation_ref=(
            facade_result.llm_invocation_observation_ref
        ),
        llm_invocation_summary_ref=facade_result.llm_invocation_summary_ref,
        sanitized_response_display=facade_result.sanitized_response_display,
        sanitized_response_preview=facade_result.sanitized_response_preview,
        final_preflight=_mapping_copy(facade_result.final_preflight),
        controlled_live_llm_preflight=_mapping_copy(
            facade_result.controlled_live_llm_preflight
        ),
        lifecycle_facts=_mapping_copy(facade_result.lifecycle_facts),
        run_config_service_bundle_facts=_mapping_copy(
            facade_result.run_config_service_bundle_facts
        ),
        blocking_reasons=tuple(facade_result.blocking_reasons),
        warnings=tuple(facade_result.warnings),
    )


def _facade_input_from_service_input(
    request: (
        ControlledExecutionRequestSchema
        | ControlledExecutionServiceInput
        | Mapping[str, Any]
    ),
    *,
    config_selection: RuntimeConfigSelectionContext | Mapping[str, Any] | None = None,
) -> ControlledRunFacadeInput:
    normalized_input = _coerce_service_input(
        request,
        config_selection=config_selection,
    )
    return ControlledRunFacadeInput(
        runtime_id=normalized_input.runtime_id,
        config_root=Path(normalized_input.config_root or "config"),
        environment=normalized_input.environment,
        profile=normalized_input.profile,
        invocation_id=normalized_input.invocation_id,
        workflow_id=normalized_input.workflow_id,
        workflow_name=normalized_input.workflow_name,
        input_payload=normalized_input.input_payload,
        operator_approved=normalized_input.operator_approved,
        approval_ref=normalized_input.approval_ref,
        audit_ref=normalized_input.audit_ref,
        sanitized_evidence_ref=normalized_input.sanitized_evidence_ref,
        governance_summary_output_ref=(
            normalized_input.governance_summary_output_ref
        ),
        request_live_llm=normalized_input.request_live_llm,
        request_ollama=normalized_input.request_ollama,
        allow_live_llm=normalized_input.allow_live_llm,
        allow_ollama=normalized_input.allow_ollama,
        live_llm_approval_ref=normalized_input.live_llm_approval_ref,
        allow_tool_confirmation=normalized_input.allow_tool_confirmation,
        tool_confirmation_approval_ref=(
            normalized_input.tool_confirmation_approval_ref
        ),
        tool_confirmation_decision_source=(
            normalized_input.tool_confirmation_decision_source
        ),
        metadata=normalized_input.metadata,
    )


def _coerce_service_input(
    request: (
        ControlledExecutionRequestSchema
        | ControlledExecutionServiceInput
        | Mapping[str, Any]
    ),
    *,
    config_selection: RuntimeConfigSelectionContext | Mapping[str, Any] | None = None,
) -> ControlledExecutionServiceInput:
    if isinstance(request, ControlledExecutionServiceInput):
        if config_selection is not None:
            raise ValueError(
                "config_selection must be omitted when passing "
                "ControlledExecutionServiceInput."
            )
        return request

    normalized_request = validate_controlled_execution_request(request)
    normalized_config = _coerce_config_selection(config_selection)
    return ControlledExecutionServiceInput(
        runtime_id=normalized_request.runtime_id,
        config_root=normalized_config.config_root,
        environment=normalized_config.environment,
        profile=normalized_config.profile,
        invocation_id=normalized_request.invocation_id,
        workflow_id=(
            normalized_request.workflow_id or DEFAULT_CONTROLLED_RUN_WORKFLOW_ID
        ),
        workflow_name=(
            normalized_request.workflow_name or DEFAULT_CONTROLLED_RUN_WORKFLOW_NAME
        ),
        input_payload=dict(normalized_request.input_payload),
        operator_approved=normalized_request.operator_approved,
        approval_ref=normalized_request.approval_ref,
        audit_ref=normalized_request.audit_ref,
        sanitized_evidence_ref=normalized_request.sanitized_evidence_ref,
        governance_summary_output_ref=(
            normalized_request.governance_summary_output_ref
        ),
        request_live_llm=normalized_request.request_live_llm,
        request_ollama=normalized_request.request_ollama,
        allow_live_llm=normalized_request.allow_live_llm,
        allow_ollama=normalized_request.allow_ollama,
        live_llm_approval_ref=normalized_request.live_llm_approval_ref,
        allow_tool_confirmation=normalized_request.allow_tool_confirmation,
        tool_confirmation_approval_ref=(
            normalized_request.tool_confirmation_approval_ref
        ),
        tool_confirmation_decision_source=(
            normalized_request.tool_confirmation_decision_source
        ),
        metadata=dict(normalized_request.metadata),
    )


def _coerce_config_selection(
    config_selection: RuntimeConfigSelectionContext | Mapping[str, Any] | None,
) -> RuntimeConfigSelectionContext:
    if config_selection is None:
        return RuntimeConfigSelectionContext()
    if isinstance(config_selection, RuntimeConfigSelectionContext):
        return config_selection
    return RuntimeConfigSelectionContext.model_validate(dict(config_selection))


def _default_live_llm_invocation_service(
    service_input: ControlledExecutionServiceInput,
    *,
    live_llm_options: (
        RuntimeLiveLlmInvocationOptionsContext | Mapping[str, Any] | None
    ) = None,
) -> Any | None:
    if not _controlled_live_args_satisfied(service_input):
        return None
    options = _coerce_live_llm_options(live_llm_options)
    from runtime_container.controlled_live_llm_service import (
        build_runtime_container_controlled_live_llm_invocation_service,
    )

    return build_runtime_container_controlled_live_llm_invocation_service(
        config_root=service_input.config_root,
        environment=service_input.environment,
        ollama_api_base=options.ollama_api_base,
        timeout_seconds=options.timeout_seconds,
        max_tokens=options.max_tokens,
        response_preview_limit=options.response_preview_limit,
        metadata={
            "source": options.selection_source
            or "runtime_container.controlled_execution_service",
            **dict(options.metadata),
        },
    )


def _controlled_live_args_satisfied(
    service_input: ControlledExecutionServiceInput,
) -> bool:
    return (
        service_input.request_live_llm is True
        and service_input.request_ollama is True
        and service_input.allow_live_llm is True
        and service_input.allow_ollama is True
        and bool(service_input.live_llm_approval_ref)
    )


def _coerce_live_llm_options(
    live_llm_options: (
        RuntimeLiveLlmInvocationOptionsContext | Mapping[str, Any] | None
    ),
) -> RuntimeLiveLlmInvocationOptionsContext:
    if live_llm_options is None:
        return RuntimeLiveLlmInvocationOptionsContext()
    if isinstance(live_llm_options, RuntimeLiveLlmInvocationOptionsContext):
        return live_llm_options
    return RuntimeLiveLlmInvocationOptionsContext.model_validate(
        dict(live_llm_options)
    )


def _mapping_copy(value: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if value is None:
        return None
    return dict(value)


__all__ = [
    "ControlledExecutionEntryRunner",
    "run_controlled_execution_service",
]
