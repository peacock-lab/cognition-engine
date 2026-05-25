"""Chat operation flow routing adapter for the Cognition System CLI."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from typing import Any

from cognition_cli.chat.controls import (
    _chat_audit_workspace_args_requested,
    _chat_plan_workspace_args_requested,
)
from contract_core.product_gateway_cli import ProductGatewayCliOperationFlowRouteInputSchema
from product_gateway.cli_surface import build_cli_operation_flow_route_projection


def _chat_product_gateway_operation_flow_route_projection(
    *,
    args: argparse.Namespace,
    user_text: str,
    chat_session_id: str,
    turn_index: int,
    history: Sequence[Mapping[str, str]],
    previous_terminal_display_text: str | None,
) -> Any:
    route_input = ProductGatewayCliOperationFlowRouteInputSchema(
        request_id=f"{chat_session_id}/turn-{turn_index:03d}",
        sanitized_user_text=user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        sanitized_history=tuple(history),
        sanitized_previous_display_text=previous_terminal_display_text,
        live_model_requested=args.request_live_llm,
        reference_paths=tuple(args.reference_paths),
        external_readonly_evidence_paths=tuple(
            getattr(args, "external_readonly_evidence_paths", ())
        ),
        run_workspace_requested=_chat_plan_workspace_args_requested(args),
        audit_run_workspace_requested=_chat_audit_workspace_args_requested(args),
        metadata={"source": "cognition_cli.entrypoints.cognition"},
    )
    return _build_product_gateway_operation_flow_route_projection(route_input)


def _chat_operation_flow_route_from_product_gateway_projection(
    projection: Any,
) -> Any:
    return projection


def _build_product_gateway_operation_flow_route_projection(
    route_input: Any,
) -> Any:
    return build_cli_operation_flow_route_projection(route_input)
