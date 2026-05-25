"""Product gateway read-only projection for OperationFlow operation flow routing."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cognition_operation_flows.product_entry_service import (
    route_operation_flow_product_entry_turn,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator

from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayExecutionMode,
    ProductGatewayRequest,
)


INTERNAL_OPERATION_FLOW_ROUTE_SOURCE = "product_gateway._operation_flows.route"


class InternalOperationFlowRouteInput(BaseModel):
    """Product-entry facts used to route a operation flow without executing it."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1)
    sanitized_user_text: str = Field(..., min_length=1)
    chat_session_id: str | None = None
    turn_index: int | None = None
    sanitized_history: tuple[Mapping[str, str], ...] = ()
    sanitized_previous_display_text: str | None = None
    live_model_requested: bool = False
    reference_paths: tuple[str, ...] = ()
    external_readonly_evidence_paths: tuple[str, ...] = ()
    run_workspace_requested: bool = False
    audit_run_workspace_requested: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_product_gateway_operation_flow_route_input(
        self,
    ) -> "InternalOperationFlowRouteInput":
        if any(not item for item in self.reference_paths):
            raise ValueError("reference_paths must not contain empty values.")
        if any(not item for item in self.external_readonly_evidence_paths):
            raise ValueError(
                "external_readonly_evidence_paths must not contain empty values."
            )
        return self


class InternalOperationFlowRouteProjection(BaseModel):
    """Product-level read-only projection for a OperationFlow route decision."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1)
    entry_kind: str = Field(..., min_length=1)
    execution_mode: str = Field(..., min_length=1)
    matched: bool
    workflow_name: str | None = None
    workflow_version: str | None = None
    task_kind: str | None = None
    route_reason: str = Field(..., min_length=1)
    confidence: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    turn_index: int | None = None
    requires_live_model: bool = False
    requires_tools: tuple[str, ...] = ()
    requires_workspace: bool = False
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    registry_version: str = Field(..., min_length=1)
    registry_workflow_count: int = 0
    registry_workflow_names: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


def build_internal_operation_flow_route_request(
    route_input: InternalOperationFlowRouteInput | Mapping[str, Any],
) -> ProductGatewayRequest:
    """Build a product-level request for read-only OperationFlow routing."""

    normalized_input = _coerce_route_input(route_input)
    return ProductGatewayRequest(
        request_id=normalized_input.request_id,
        entry_kind=ProductGatewayEntryKind.TASK_WORKFLOW_ROUTE,
        execution_mode=ProductGatewayExecutionMode.PREFLIGHT_ONLY,
        input_payload={
            "sanitized_user_text": normalized_input.sanitized_user_text,
            "reference_path_count": len(normalized_input.reference_paths),
            "external_readonly_evidence_path_count": len(
                normalized_input.external_readonly_evidence_paths
            ),
            "run_workspace_requested": normalized_input.run_workspace_requested,
            "audit_run_workspace_requested": (
                normalized_input.audit_run_workspace_requested
            ),
        },
        metadata={
            "source": INTERNAL_OPERATION_FLOW_ROUTE_SOURCE,
            "route_only": True,
            "workflow_execution_enabled": False,
            **normalized_input.metadata,
        },
    )


def build_internal_operation_flow_route_projection(
    route_input: InternalOperationFlowRouteInput | Mapping[str, Any],
) -> InternalOperationFlowRouteProjection:
    """Route a product-entry task request without executing a workflow."""

    normalized_input = _coerce_route_input(route_input)
    gateway_request = build_internal_operation_flow_route_request(normalized_input)
    route_result = route_operation_flow_product_entry_turn(
        sanitized_user_text=normalized_input.sanitized_user_text,
        chat_session_id=normalized_input.chat_session_id,
        turn_index=normalized_input.turn_index,
        sanitized_history=normalized_input.sanitized_history,
        sanitized_previous_display_text=(
            normalized_input.sanitized_previous_display_text
        ),
        live_model_requested=normalized_input.live_model_requested,
        reference_paths=normalized_input.reference_paths,
        external_readonly_evidence_paths=(
            normalized_input.external_readonly_evidence_paths
        ),
        run_workspace_requested=normalized_input.run_workspace_requested,
        audit_run_workspace_requested=(
            normalized_input.audit_run_workspace_requested
        ),
        source=INTERNAL_OPERATION_FLOW_ROUTE_SOURCE,
        metadata=normalized_input.metadata,
    )
    route = route_result.route

    return InternalOperationFlowRouteProjection(
        request_id=gateway_request.request_id,
        entry_kind=gateway_request.entry_kind.value,
        execution_mode=gateway_request.execution_mode.value,
        matched=route.matched,
        workflow_name=route.workflow_name,
        workflow_version=route.workflow_version,
        task_kind=route.task_kind,
        route_reason=route.route_reason,
        confidence=route.confidence,
        source=route.source,
        turn_index=route.turn_index,
        requires_live_model=route.requires_live_model,
        requires_tools=tuple(route.requires_tools),
        requires_workspace=route.requires_workspace,
        blocking_reasons=tuple(route.blocking_reasons),
        warnings=tuple(route.warnings),
        registry_version=route_result.registry_version,
        registry_workflow_count=route_result.registry_workflow_count,
        registry_workflow_names=route_result.registry_workflow_names,
        metadata={
            "source": INTERNAL_OPERATION_FLOW_ROUTE_SOURCE,
            "route_status": route_result.route_status,
            "route_metadata": {
                "detector": route.metadata.get("detector"),
                "reference_path_count": route.metadata.get(
                    "reference_path_count",
                    len(normalized_input.reference_paths),
                ),
                "external_readonly_evidence_path_count": route.metadata.get(
                    "external_readonly_evidence_path_count",
                    len(normalized_input.external_readonly_evidence_paths),
                ),
            },
            "route_only": True,
            "workflow_execution_enabled": False,
        },
    )


def _coerce_route_input(
    route_input: InternalOperationFlowRouteInput | Mapping[str, Any],
) -> InternalOperationFlowRouteInput:
    if isinstance(route_input, InternalOperationFlowRouteInput):
        return route_input
    return InternalOperationFlowRouteInput.model_validate(dict(route_input))


__all__ = [
    "INTERNAL_OPERATION_FLOW_ROUTE_SOURCE",
    "InternalOperationFlowRouteInput",
    "InternalOperationFlowRouteProjection",
    "build_internal_operation_flow_route_projection",
    "build_internal_operation_flow_route_request",
]
