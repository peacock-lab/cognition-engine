"""Private product-entry routing implementation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from cognition_operation_flows._product_entry.types import (
    OperationFlowProductEntryRouteResultCandidate,
)
from cognition_operation_flows._requests.registry import (
    OperationFlowTurnRequestCandidate,
    build_default_operation_flow_registry,
    route_operation_flow_turn,
    operation_flow_registry_status_dict,
    operation_flow_route_status_dict,
)


def route_operation_flow_product_entry_turn(
    *,
    sanitized_user_text: str,
    chat_session_id: str | None = None,
    turn_index: int | None = None,
    sanitized_history: Sequence[Mapping[str, str]] = (),
    sanitized_previous_display_text: str | None = None,
    live_model_requested: bool = False,
    reference_paths: Sequence[str] = (),
    external_readonly_evidence_paths: Sequence[str] = (),
    run_workspace_requested: bool = False,
    audit_run_workspace_requested: bool = False,
    source: str,
    metadata: Mapping[str, Any] | None = None,
) -> OperationFlowProductEntryRouteResultCandidate:
    """Route a product-entry turn through the operation flow registry."""

    registry = build_default_operation_flow_registry()
    route = route_operation_flow_turn(
        registry,
        OperationFlowTurnRequestCandidate(
            user_text=sanitized_user_text,
            chat_session_id=chat_session_id,
            turn_index=turn_index,
            history=tuple(sanitized_history),
            previous_terminal_display_text=sanitized_previous_display_text,
            live_model_requested=live_model_requested,
            reference_paths=tuple(reference_paths),
            external_readonly_evidence_paths=tuple(
                external_readonly_evidence_paths
            ),
            run_workspace_requested=run_workspace_requested,
            audit_run_workspace_requested=audit_run_workspace_requested,
            metadata={"source": source, **dict(metadata or {})},
        ),
    )
    registry_status = dict(operation_flow_registry_status_dict(registry))
    route_status = dict(operation_flow_route_status_dict(route))
    return OperationFlowProductEntryRouteResultCandidate(
        route=route,
        registry_status=registry_status,
        route_status=route_status,
        registry_version=registry.registry_version,
        registry_workflow_count=int(registry_status["workflow_count"]),
        registry_workflow_names=tuple(registry_status["workflow_names"]),
    )


__all__ = ["route_operation_flow_product_entry_turn"]
