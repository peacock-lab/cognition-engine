"""Product gateway execution entry for Twf task workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from config_contexts.runtime import (
    RuntimeConfigSelectionContext,
    RuntimeLiveLlmInvocationOptionsContext,
)
from contract_core.external_readonly_evidence import (
    build_external_readonly_evidence_readonly_public_refs_from_read_context,
)
from contract_core.llm_invocation import (
    GovernedLlmInvocationServiceFactory,
    GovernedLlmInvocationServiceResolution,
)
from cognition_operation_flows.product_entry_service import (
    build_operation_flow_product_entry_request,
    extract_operation_flow_product_entry_external_readonly_evidence_context,
    get_operation_flow_product_entry_default_model_name,
    get_operation_flow_product_entry_result_display_text,
    run_operation_flow_product_entry,
    operation_flow_product_entry_result_updates_latest_plan,
)

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
from product_gateway._operation_flows.route import (
    InternalTwfRouteProjection,
)
from product_gateway.external_readonly_refs import (
    run_external_readonly_refs_gateway_request,
)


INTERNAL_TWF_EXECUTION_SOURCE = "product_gateway._operation_flows.execution"
INTERNAL_TWF_EXTERNAL_READONLY_REFS_SOURCE = (
    "twf_execution_external_readonly_refs"
)
TWF_LIVE_LLM_PROVIDER_NOT_INJECTED = "twf_live_llm_provider_not_injected"
TWF_LIVE_LLM_PROVIDER_REQUIRED = "twf_live_llm_provider_required"
TWF_LIVE_LLM_PROVIDER_RESOLUTION_FAILED = (
    "twf_live_llm_provider_resolution_failed"
)
TWF_LIVE_LLM_PROVIDER_RESOLUTION_EXCEPTION = (
    "twf_live_llm_provider_resolution_exception"
)


@dataclass(frozen=True)
class InternalTwfExecutionContext:
    """Backend context needed to turn a Twf draft into an executable request."""

    llm_invocation_service: Any | None = None
    llm_invocation_service_factory: (
        GovernedLlmInvocationServiceFactory | None
    ) = None
    config_context: Any | None = None
    config_root: str | None = None
    environment: str = "local"
    profile: str | None = None
    ollama_api_base: str | None = None
    reference_profile_config: Mapping[str, Any] | None = None
    reference_session_args: Mapping[str, Any] = field(default_factory=dict)
    reference_entrypoint_explicit_args: Mapping[str, Any] = field(
        default_factory=dict
    )
    model_name: str = field(
        default_factory=get_operation_flow_product_entry_default_model_name
    )


@dataclass(frozen=True)
class InternalTwfExecutionInput:
    """Product gateway input for executing a channel-neutral Twf request draft."""

    request_id: str
    route_projection: InternalTwfRouteProjection
    request_draft: Any
    execution_context: InternalTwfExecutionContext = field(
        default_factory=InternalTwfExecutionContext
    )

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must not be empty.")
        if self.route_projection.request_id != self.request_id:
            raise ValueError("route_projection request_id must match request_id.")
        if (
            self.route_projection.workflow_name
            and self.route_projection.workflow_name != self.request_draft.workflow_name
        ):
            raise ValueError("route projection and request draft workflow mismatch.")


@dataclass(frozen=True)
class InternalTwfExecutionResult:
    """Product gateway result for one task workflow execution."""

    handled: bool
    product_request: ProductGatewayRequest
    product_response: ProductGatewayResponse
    terminal_display_text: str | None = None
    workflow_result: Any | None = None
    updates_latest_plan: bool = False
    latest_plan_display_text: str | None = None
    latest_plan_result: Any | None = None


def build_internal_twf_execution_request(
    execution_input: InternalTwfExecutionInput,
) -> ProductGatewayRequest:
    """Build the product request envelope for a Twf workflow execution."""

    draft = execution_input.request_draft
    governance_refs = draft.governance_refs
    return ProductGatewayRequest(
        request_id=execution_input.request_id,
        entry_kind=ProductGatewayEntryKind.TASK_WORKFLOW_EXECUTION,
        execution_mode=(
            ProductGatewayExecutionMode.CONTROLLED_LIVE
            if draft.live_model_allowed
            else ProductGatewayExecutionMode.NO_LIVE
        ),
        input_payload={
            "workflow_name": draft.workflow_name,
            "task_kind": draft.task_kind,
            "chat_session_id": draft.turn_input.chat_session_id,
            "turn_index": draft.turn_input.turn_index,
            "route_matched": execution_input.route_projection.matched,
            "live_model_allowed": draft.live_model_allowed,
            "reference_path_count": len(draft.controls.reference_paths),
            "external_readonly_evidence_path_count": len(
                draft.controls.external_readonly_evidence_paths
            ),
            "run_workspace_requested": draft.controls.run_workspace_enabled,
            "audit_run_workspace_requested": bool(
                draft.controls.audit_run_workspace_path
                or draft.controls.audit_run_workspace_ref
            ),
        },
        input_refs=ProductGatewayInputRefs(
            operator_approval_ref=governance_refs.approval_ref,
            audit_ref=governance_refs.audit_ref,
            sanitized_evidence_ref=governance_refs.sanitized_evidence_ref,
            governance_summary_ref=governance_refs.governance_summary_output_ref,
        ),
        operator_approval=ProductGatewayOperatorApprovalRef(
            approved=draft.operator_approved,
            approval_ref=governance_refs.approval_ref,
            audit_ref=governance_refs.audit_ref,
            decision_source=INTERNAL_TWF_EXECUTION_SOURCE,
        ),
        live_options=ProductGatewayLiveOptions(
            request_live_llm=draft.request_live_llm,
            request_ollama=draft.request_ollama,
            allow_live_llm=draft.allow_live_llm,
            allow_ollama=draft.allow_ollama,
            live_llm_approval_ref=governance_refs.live_llm_approval_ref,
            override_source=(
                INTERNAL_TWF_EXECUTION_SOURCE
                if draft.request_live_llm or draft.request_ollama
                else None
            ),
        ),
        metadata={
            "source": INTERNAL_TWF_EXECUTION_SOURCE,
            "route_source": execution_input.route_projection.source,
            "request_draft_schema_version": draft.schema_version,
            "product_gateway_entry_required": draft.product_gateway_entry_required,
            "workflow_execution_enabled": True,
            "public_schema_enabled": draft.public_schema_enabled,
        },
    )


def execute_internal_twf_workflow(
    execution_input: InternalTwfExecutionInput,
) -> InternalTwfExecutionResult:
    """Execute a Twf workflow through the product gateway boundary."""

    product_request = build_internal_twf_execution_request(execution_input)
    if not execution_input.route_projection.matched:
        return InternalTwfExecutionResult(
            handled=False,
            product_request=product_request,
            product_response=ProductGatewayResponse(
                request_id=product_request.request_id,
                entry_kind=product_request.entry_kind,
                status=ProductGatewayStatus.SKIPPED,
                warnings=["task_workflow_route_not_matched"],
                metadata={
                    "source": INTERNAL_TWF_EXECUTION_SOURCE,
                    "workflow_name": execution_input.request_draft.workflow_name,
                    "execution_skipped": True,
                },
            ),
        )

    llm_invocation_resolution = _resolve_twf_llm_invocation_service(
        execution_input
    )
    if llm_invocation_resolution.blocking_reasons:
        return _blocked_twf_live_provider_result(
            execution_input,
            product_request=product_request,
            resolution=llm_invocation_resolution,
        )

    workflow_request = _build_workflow_request(
        execution_input,
        llm_invocation_service=llm_invocation_resolution.service,
    )
    workflow_result = run_operation_flow_product_entry(
        execution_input.request_draft.workflow_name,
        workflow_request,
    )
    external_readonly_refs_response = (
        _workflow_result_external_readonly_refs_response(
            workflow_result,
            request_id=product_request.request_id,
        )
    )
    blocking_reasons = _workflow_result_blocking_reasons(workflow_result)
    warnings = _ordered_unique(
        (
            *tuple(llm_invocation_resolution.warnings),
            *_workflow_result_warnings(workflow_result),
        )
    )
    status = _workflow_result_status(
        workflow_result,
        blocking_reasons=blocking_reasons,
    )
    updates_latest_plan = operation_flow_product_entry_result_updates_latest_plan(
        workflow_result
    )
    terminal_display_text = get_operation_flow_product_entry_result_display_text(
        workflow_result
    )
    return InternalTwfExecutionResult(
        handled=True,
        product_request=product_request,
        product_response=ProductGatewayResponse(
            request_id=product_request.request_id,
            entry_kind=product_request.entry_kind,
            status=status,
            blocking_reasons=list(blocking_reasons),
            warnings=list(warnings),
            output_refs=_workflow_result_output_refs(
                workflow_result,
                external_readonly_refs_response=external_readonly_refs_response,
            ),
            governance_summary_ref=(
                execution_input.request_draft.governance_refs.governance_summary_output_ref
            ),
            metadata={
                "source": INTERNAL_TWF_EXECUTION_SOURCE,
                "workflow_name": execution_input.request_draft.workflow_name,
                "task_kind": execution_input.request_draft.task_kind,
                "triggered": bool(getattr(workflow_result, "triggered", False)),
                "no_live": bool(getattr(workflow_result, "no_live", False)),
                "fail_safe": bool(getattr(workflow_result, "fail_safe", False)),
                "model_call_count": int(
                    getattr(workflow_result, "model_call_count", 0) or 0
                ),
                "route_reason": execution_input.route_projection.route_reason,
                "route_confidence": execution_input.route_projection.confidence,
                **_external_readonly_refs_response_metadata(
                    external_readonly_refs_response
                ),
            },
        ),
        terminal_display_text=terminal_display_text,
        workflow_result=workflow_result,
        updates_latest_plan=updates_latest_plan,
        latest_plan_display_text=(
            terminal_display_text if updates_latest_plan else None
        ),
        latest_plan_result=workflow_result if updates_latest_plan else None,
    )


def _build_workflow_request(
    execution_input: InternalTwfExecutionInput,
    *,
    llm_invocation_service: Any | None = None,
) -> Any:
    context = execution_input.execution_context
    resolved_config_context = context.config_context
    return build_operation_flow_product_entry_request(
        execution_input.request_draft,
        llm_invocation_service=llm_invocation_service,
        config_context=resolved_config_context,
        config_root=context.config_root,
        environment=context.environment,
        profile=context.profile,
        ollama_api_base=context.ollama_api_base,
        reference_profile_config=context.reference_profile_config,
        reference_session_args=context.reference_session_args,
        reference_entrypoint_explicit_args=context.reference_entrypoint_explicit_args,
        model_name=context.model_name,
    )


def _resolve_twf_llm_invocation_service(
    execution_input: InternalTwfExecutionInput,
) -> GovernedLlmInvocationServiceResolution:
    context = execution_input.execution_context
    if context.llm_invocation_service is not None:
        return GovernedLlmInvocationServiceResolution(
            service=context.llm_invocation_service,
            metadata={"resolution_source": "injected_service"},
        )
    if not execution_input.request_draft.live_model_allowed:
        return GovernedLlmInvocationServiceResolution()
    if context.llm_invocation_service_factory is None:
        return GovernedLlmInvocationServiceResolution(
            blocking_reasons=(TWF_LIVE_LLM_PROVIDER_NOT_INJECTED,),
            warnings=(TWF_LIVE_LLM_PROVIDER_REQUIRED,),
            metadata={"resolution_source": "missing_factory"},
        )

    try:
        resolution = context.llm_invocation_service_factory.resolve(
            config_context=context.config_context,
            config_selection=_build_twf_runtime_config_selection(execution_input),
            live_llm_options=_build_twf_live_llm_options(execution_input),
        )
    except Exception:
        return GovernedLlmInvocationServiceResolution(
            blocking_reasons=(TWF_LIVE_LLM_PROVIDER_RESOLUTION_FAILED,),
            warnings=(TWF_LIVE_LLM_PROVIDER_RESOLUTION_EXCEPTION,),
            metadata={"failure_type": TWF_LIVE_LLM_PROVIDER_RESOLUTION_EXCEPTION},
        )

    if resolution.service is not None and not resolution.blocking_reasons:
        return resolution
    return GovernedLlmInvocationServiceResolution(
        service=None,
        blocking_reasons=(
            tuple(resolution.blocking_reasons)
            or (TWF_LIVE_LLM_PROVIDER_RESOLUTION_FAILED,)
        ),
        warnings=tuple(resolution.warnings),
        metadata=dict(resolution.metadata),
    )


def _build_twf_runtime_config_selection(
    execution_input: InternalTwfExecutionInput,
) -> RuntimeConfigSelectionContext:
    context = execution_input.execution_context
    return RuntimeConfigSelectionContext(
        config_root=context.config_root,
        environment=context.environment,
        profile=context.profile,
        selection_source=INTERNAL_TWF_EXECUTION_SOURCE,
        metadata={
            "request_id": execution_input.request_id,
            "workflow_name": execution_input.request_draft.workflow_name,
            "task_kind": execution_input.request_draft.task_kind,
        },
    )


def _build_twf_live_llm_options(
    execution_input: InternalTwfExecutionInput,
) -> RuntimeLiveLlmInvocationOptionsContext:
    context = execution_input.execution_context
    return RuntimeLiveLlmInvocationOptionsContext(
        ollama_api_base=context.ollama_api_base,
        timeout_seconds=execution_input.request_draft.live_llm_timeout_seconds,
        selection_source=INTERNAL_TWF_EXECUTION_SOURCE,
        metadata={
            "request_id": execution_input.request_id,
            "workflow_name": execution_input.request_draft.workflow_name,
            "task_kind": execution_input.request_draft.task_kind,
        },
    )


def _blocked_twf_live_provider_result(
    execution_input: InternalTwfExecutionInput,
    *,
    product_request: ProductGatewayRequest,
    resolution: GovernedLlmInvocationServiceResolution,
) -> InternalTwfExecutionResult:
    return InternalTwfExecutionResult(
        handled=True,
        product_request=product_request,
        product_response=ProductGatewayResponse(
            request_id=product_request.request_id,
            entry_kind=product_request.entry_kind,
            status=ProductGatewayStatus.BLOCKED,
            blocking_reasons=list(resolution.blocking_reasons),
            warnings=list(resolution.warnings),
            governance_summary_ref=(
                execution_input.request_draft.governance_refs.governance_summary_output_ref
            ),
            metadata={
                "source": INTERNAL_TWF_EXECUTION_SOURCE,
                "workflow_name": execution_input.request_draft.workflow_name,
                "task_kind": execution_input.request_draft.task_kind,
                "triggered": False,
                "no_live": False,
                "fail_safe": True,
                "model_call_count": 0,
                "route_reason": execution_input.route_projection.route_reason,
                "route_confidence": execution_input.route_projection.confidence,
                "provider_resolution_blocked": True,
            },
        ),
        workflow_result=None,
    )


def _workflow_result_status(
    workflow_result: Any,
    *,
    blocking_reasons: Sequence[str],
) -> ProductGatewayStatus:
    if blocking_reasons:
        return ProductGatewayStatus.BLOCKED
    if bool(getattr(workflow_result, "fail_safe", False)):
        return ProductGatewayStatus.FAILED
    return ProductGatewayStatus.SUCCESS


def _workflow_result_blocking_reasons(workflow_result: Any) -> tuple[str, ...]:
    reasons: list[str] = []
    task_context = getattr(workflow_result, "task_run_context", None)
    preflight = getattr(task_context, "preflight", None)
    reasons.extend(str(item) for item in getattr(preflight, "blocking_reasons", ()))
    for attr_name in ("reference_context", "explain_context", "audit_context"):
        context = getattr(workflow_result, attr_name, None)
        reasons.extend(str(item) for item in getattr(context, "blocking_reasons", ()))
    audit_context = getattr(workflow_result, "audit_context", None)
    target = getattr(audit_context, "target", None)
    reasons.extend(str(item) for item in getattr(target, "blocking_reasons", ()))
    return tuple(_ordered_unique(reasons))


def _workflow_result_warnings(workflow_result: Any) -> tuple[str, ...]:
    warnings: list[str] = []
    task_context = getattr(workflow_result, "task_run_context", None)
    preflight = getattr(task_context, "preflight", None)
    warnings.extend(str(item) for item in getattr(preflight, "warnings", ()))
    for attr_name in ("reference_context", "explain_context", "audit_context"):
        context = getattr(workflow_result, attr_name, None)
        warnings.extend(str(item) for item in getattr(context, "warnings", ()))
    return tuple(_ordered_unique(warnings))


def _workflow_result_external_readonly_refs_response(
    workflow_result: Any,
    *,
    request_id: str,
) -> ProductGatewayResponse | None:
    context = extract_operation_flow_product_entry_external_readonly_evidence_context(
        workflow_result
    )
    if context is None:
        return None
    readonly_public_refs = (
        build_external_readonly_evidence_readonly_public_refs_from_read_context(
            context,
            metadata={"source": INTERNAL_TWF_EXTERNAL_READONLY_REFS_SOURCE},
        )
    )
    return run_external_readonly_refs_gateway_request(
        {
            "request_id": f"{request_id}/external-readonly-refs",
            "readonly_public_refs": readonly_public_refs,
            "metadata": {"source": INTERNAL_TWF_EXECUTION_SOURCE},
        }
    )


def _workflow_result_output_refs(
    workflow_result: Any,
    *,
    external_readonly_refs_response: ProductGatewayResponse | None = None,
) -> ProductGatewayOutputRefs:
    evidence_refs = [
        ProductGatewayRef(ref=ref, kind="evidence", purpose="task_workflow")
        for ref in _workflow_result_evidence_refs(workflow_result)
    ]
    if external_readonly_refs_response is None:
        return ProductGatewayOutputRefs(evidence_refs=evidence_refs)
    return ProductGatewayOutputRefs(
        evidence_refs=_merge_product_gateway_refs(
            evidence_refs,
            external_readonly_refs_response.output_refs.evidence_refs,
        ),
        additional_refs=_merge_product_gateway_refs(
            external_readonly_refs_response.output_refs.additional_refs,
        ),
    )


def _workflow_result_evidence_refs(workflow_result: Any) -> tuple[str, ...]:
    refs: list[str] = []
    for attr_name in ("reference_context", "task_run_context"):
        context = getattr(workflow_result, attr_name, None)
        refs.extend(str(item) for item in getattr(context, "evidence_refs", ()))
    run_workspace = getattr(workflow_result, "run_workspace", None)
    refs.extend(str(item) for item in getattr(run_workspace, "evidence_refs", ()))
    return tuple(_ordered_unique(refs))


def _external_readonly_refs_response_metadata(
    response: ProductGatewayResponse | None,
) -> dict[str, Any]:
    if response is None:
        return {}
    return {
        "external_readonly_refs_consumed": True,
        "external_readonly_refs_response_status": response.status.value,
        "external_readonly_refs_status": response.metadata.get(
            "readonly_refs_status"
        ),
        "external_readonly_refs_evidence_ref_count": len(
            response.output_refs.evidence_refs
        ),
        "external_readonly_refs_additional_ref_count": len(
            response.output_refs.additional_refs
        ),
    }


def _merge_product_gateway_refs(
    *ref_groups: Sequence[ProductGatewayRef],
) -> list[ProductGatewayRef]:
    refs: list[ProductGatewayRef] = []
    seen: set[tuple[str, str, str | None]] = set()
    for ref_group in ref_groups:
        for ref in ref_group:
            key = (ref.ref, ref.kind, ref.purpose)
            if key in seen:
                continue
            seen.add(key)
            refs.append(ref)
    return refs


def _ordered_unique(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


__all__ = [
    "INTERNAL_TWF_EXECUTION_SOURCE",
    "InternalTwfExecutionContext",
    "InternalTwfExecutionInput",
    "InternalTwfExecutionResult",
    "build_internal_twf_execution_request",
    "execute_internal_twf_workflow",
]
