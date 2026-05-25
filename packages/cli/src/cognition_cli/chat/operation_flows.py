"""Chat operation flow runner adapters for the Cognition System CLI."""

from __future__ import annotations

import argparse
import sys
from collections.abc import MutableSequence
from dataclasses import dataclass
from typing import Any

from cognition_cli.constants import (
    CHAT_NO_LIVE_ASSISTANT_MESSAGE,
    EXIT_BLOCKING,
    EXIT_RUNTIME_FAILURE,
)
from cognition_cli.run.controls import (
    _apply_run_defaults,
    _cli_blocking_reasons,
)
from cognition_cli.run.output import _blocking_output
from cognition_cli.chat.output import _chat_turn_text_output
from cognition_cli.chat.turns import _chat_history_entry, _chat_turn_args
from cognition_cli.chat.workflow_requests import (
    _chat_config_profile_explain_workflow_request_draft_input,
    _chat_plan_workflow_request_draft_input,
    _chat_reference_review_workflow_request_draft_input,
    _chat_run_workspace_evidence_audit_workflow_request_draft_input,
)
from cognition_cli.chat.controls import (
    _chat_plan_control_kwargs,
    _chat_plan_runtime_config_context,
)
from cognition_cli.services.runtime import OperationFlowLlmInvocationServiceFactory
from contract_core.product_gateway_cli import (
    PRODUCT_GATEWAY_CLI_OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
    PRODUCT_GATEWAY_CLI_OPERATION_FLOW_PLAN_WORKFLOW_NAME,
    PRODUCT_GATEWAY_CLI_OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
    PRODUCT_GATEWAY_CLI_OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
    ProductGatewayCliOperationFlowExecutionInputSchema,
    ProductGatewayCliOperationFlowExecutionOptionsSchema,
    ProductGatewayCliOperationFlowRequestDraftInputSchema,
)
from product_gateway.cli_surface import execute_cli_operation_flow_workflow


@dataclass(frozen=True)
class ChatOperationFlowTurnResult:
    handled: bool
    exit_code: int | None
    latest_plan_display_text: str | None
    latest_plan_snapshot: Any | None


def _dispatch_chat_operation_flow_turn(
    *,
    args: argparse.Namespace,
    user_text: str,
    chat_session_id: str,
    turn_index: int,
    history: MutableSequence[dict[str, str]],
    latest_plan_display_text: str | None,
    latest_plan_snapshot: Any | None,
    operation_route_projection: Any,
    operation_route: Any,
    operation_flow_llm_invocation_service_factory: (
        OperationFlowLlmInvocationServiceFactory | None
    ) = None,
) -> ChatOperationFlowTurnResult:
    if not operation_route.matched:
        return _operation_flow_not_handled(
            latest_plan_display_text,
            latest_plan_snapshot,
        )

    if operation_route.workflow_name == PRODUCT_GATEWAY_CLI_OPERATION_FLOW_PLAN_WORKFLOW_NAME:
        return _run_plan_operation_flow_turn(
            args=args,
            user_text=user_text,
            chat_session_id=chat_session_id,
            turn_index=turn_index,
            history=history,
            latest_plan_display_text=latest_plan_display_text,
            latest_plan_snapshot=latest_plan_snapshot,
            operation_route_projection=operation_route_projection,
            operation_route=operation_route,
            operation_flow_llm_invocation_service_factory=(
                operation_flow_llm_invocation_service_factory
            ),
        )

    if (
        operation_route.workflow_name
        == PRODUCT_GATEWAY_CLI_OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME
    ):
        return _run_reference_review_operation_flow_turn(
            args=args,
            user_text=user_text,
            chat_session_id=chat_session_id,
            turn_index=turn_index,
            history=history,
            latest_plan_display_text=latest_plan_display_text,
            latest_plan_snapshot=latest_plan_snapshot,
            operation_route_projection=operation_route_projection,
            operation_route=operation_route,
            operation_flow_llm_invocation_service_factory=(
                operation_flow_llm_invocation_service_factory
            ),
        )

    if (
        operation_route.workflow_name
        == PRODUCT_GATEWAY_CLI_OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME
    ):
        return _run_config_profile_explain_operation_flow_turn(
            args=args,
            user_text=user_text,
            chat_session_id=chat_session_id,
            turn_index=turn_index,
            history=history,
            latest_plan_display_text=latest_plan_display_text,
            latest_plan_snapshot=latest_plan_snapshot,
            operation_route_projection=operation_route_projection,
            operation_route=operation_route,
            operation_flow_llm_invocation_service_factory=(
                operation_flow_llm_invocation_service_factory
            ),
        )

    if (
        operation_route.workflow_name
        == PRODUCT_GATEWAY_CLI_OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME
    ):
        return _run_workspace_evidence_audit_operation_flow_turn(
            args=args,
            user_text=user_text,
            chat_session_id=chat_session_id,
            turn_index=turn_index,
            history=history,
            latest_plan_display_text=latest_plan_display_text,
            latest_plan_snapshot=latest_plan_snapshot,
            operation_route_projection=operation_route_projection,
            operation_route=operation_route,
            operation_flow_llm_invocation_service_factory=(
                operation_flow_llm_invocation_service_factory
            ),
        )

    print(
        "cognition chat operation flow route unsupported: "
        + str(operation_route.workflow_name),
        file=sys.stderr,
    )
    return _operation_flow_exit(
        EXIT_RUNTIME_FAILURE,
        latest_plan_display_text,
        latest_plan_snapshot,
    )


def _run_plan_operation_flow_turn(
    *,
    args: argparse.Namespace,
    user_text: str,
    chat_session_id: str,
    turn_index: int,
    history: MutableSequence[dict[str, str]],
    latest_plan_display_text: str | None,
    latest_plan_snapshot: Any | None,
    operation_route_projection: Any,
    operation_route: Any,
    operation_flow_llm_invocation_service_factory: (
        OperationFlowLlmInvocationServiceFactory | None
    ) = None,
) -> ChatOperationFlowTurnResult:
    turn_args = _chat_turn_args(args, chat_session_id, turn_index)
    blocking_exit_code = _emit_blocking_chat_turn_if_needed(turn_args, turn_index)
    if blocking_exit_code is not None:
        return _operation_flow_exit(
            blocking_exit_code,
            latest_plan_display_text,
            latest_plan_snapshot,
        )
    gateway_result = _execute_operation_flow_through_product_gateway(
        args=turn_args,
        request_draft_input=_chat_plan_workflow_request_draft_input(
            args=turn_args,
            user_text=user_text,
            chat_session_id=chat_session_id,
            turn_index=turn_index,
            history=history,
            previous_plan_text=latest_plan_display_text,
            route=operation_route,
        ),
        operation_route_projection=operation_route_projection,
        operation_flow_llm_invocation_service_factory=operation_flow_llm_invocation_service_factory,
    )
    _print_and_record_operation_flow_result(
        history=history,
        user_text=user_text,
        terminal_display_text=gateway_result.terminal_display_text or "",
    )
    return _operation_flow_continue(
        gateway_result.latest_plan_display_text,
        gateway_result.latest_plan_snapshot,
    )


def _run_reference_review_operation_flow_turn(
    *,
    args: argparse.Namespace,
    user_text: str,
    chat_session_id: str,
    turn_index: int,
    history: MutableSequence[dict[str, str]],
    latest_plan_display_text: str | None,
    latest_plan_snapshot: Any | None,
    operation_route_projection: Any,
    operation_route: Any,
    operation_flow_llm_invocation_service_factory: (
        OperationFlowLlmInvocationServiceFactory | None
    ) = None,
) -> ChatOperationFlowTurnResult:
    turn_args = _chat_turn_args(args, chat_session_id, turn_index)
    blocking_exit_code = _emit_blocking_chat_turn_if_needed(turn_args, turn_index)
    if blocking_exit_code is not None:
        return _operation_flow_exit(
            blocking_exit_code,
            latest_plan_display_text,
            latest_plan_snapshot,
        )
    gateway_result = _execute_operation_flow_through_product_gateway(
        args=turn_args,
        request_draft_input=_chat_reference_review_workflow_request_draft_input(
            args=turn_args,
            user_text=user_text,
            chat_session_id=chat_session_id,
            turn_index=turn_index,
            history=history,
            route=operation_route,
        ),
        operation_route_projection=operation_route_projection,
        operation_flow_llm_invocation_service_factory=operation_flow_llm_invocation_service_factory,
    )
    _print_and_record_operation_flow_result(
        history=history,
        user_text=user_text,
        terminal_display_text=gateway_result.terminal_display_text or "",
    )
    return _operation_flow_continue(latest_plan_display_text, latest_plan_snapshot)


def _run_config_profile_explain_operation_flow_turn(
    *,
    args: argparse.Namespace,
    user_text: str,
    chat_session_id: str,
    turn_index: int,
    history: MutableSequence[dict[str, str]],
    latest_plan_display_text: str | None,
    latest_plan_snapshot: Any | None,
    operation_route_projection: Any,
    operation_route: Any,
    operation_flow_llm_invocation_service_factory: (
        OperationFlowLlmInvocationServiceFactory | None
    ) = None,
) -> ChatOperationFlowTurnResult:
    turn_args = _chat_turn_args(args, chat_session_id, turn_index)
    gateway_result = _execute_operation_flow_through_product_gateway(
        args=turn_args,
        request_draft_input=_chat_config_profile_explain_workflow_request_draft_input(
            args=turn_args,
            user_text=user_text,
            chat_session_id=chat_session_id,
            turn_index=turn_index,
            history=history,
            route=operation_route,
        ),
        operation_route_projection=operation_route_projection,
        operation_flow_llm_invocation_service_factory=operation_flow_llm_invocation_service_factory,
    )
    _print_and_record_operation_flow_result(
        history=history,
        user_text=user_text,
        terminal_display_text=gateway_result.terminal_display_text or "",
    )
    return _operation_flow_continue(latest_plan_display_text, latest_plan_snapshot)


def _run_workspace_evidence_audit_operation_flow_turn(
    *,
    args: argparse.Namespace,
    user_text: str,
    chat_session_id: str,
    turn_index: int,
    history: MutableSequence[dict[str, str]],
    latest_plan_display_text: str | None,
    latest_plan_snapshot: Any | None,
    operation_route_projection: Any,
    operation_route: Any,
    operation_flow_llm_invocation_service_factory: (
        OperationFlowLlmInvocationServiceFactory | None
    ) = None,
) -> ChatOperationFlowTurnResult:
    turn_args = _chat_turn_args(args, chat_session_id, turn_index)
    gateway_result = _execute_operation_flow_through_product_gateway(
        args=turn_args,
        request_draft_input=(
            _chat_run_workspace_evidence_audit_workflow_request_draft_input(
                args=turn_args,
                user_text=user_text,
                chat_session_id=chat_session_id,
                turn_index=turn_index,
                history=history,
                route=operation_route,
            )
        ),
        operation_route_projection=operation_route_projection,
        operation_flow_llm_invocation_service_factory=operation_flow_llm_invocation_service_factory,
    )
    _print_and_record_operation_flow_result(
        history=history,
        user_text=user_text,
        terminal_display_text=gateway_result.terminal_display_text or "",
    )
    return _operation_flow_continue(latest_plan_display_text, latest_plan_snapshot)


def _execute_operation_flow_through_product_gateway(
    *,
    args: argparse.Namespace,
    request_draft_input: ProductGatewayCliOperationFlowRequestDraftInputSchema,
    operation_route_projection: Any,
    operation_flow_llm_invocation_service_factory: (
        OperationFlowLlmInvocationServiceFactory | None
    ) = None,
) -> Any:
    plan_controls = _chat_plan_control_kwargs(args)
    return execute_cli_operation_flow_workflow(
        execution_input=ProductGatewayCliOperationFlowExecutionInputSchema(
            request_id=operation_route_projection.request_id,
            route_projection=operation_route_projection,
            request_draft_input=request_draft_input,
            execution_options=ProductGatewayCliOperationFlowExecutionOptionsSchema(
                config_root=str(args.config_root),
                environment=args.environment,
                profile=args.profile,
                ollama_api_base=args.ollama_api_base,
                reference_profile_config=plan_controls["reference_profile_config"],
                reference_entrypoint_explicit_args=plan_controls[
                    "reference_entrypoint_explicit_args"
                ],
            ),
        ),
        config_context=_chat_plan_runtime_config_context(args),
        llm_invocation_service_factory=operation_flow_llm_invocation_service_factory,
    )


def _emit_blocking_chat_turn_if_needed(
    turn_args: argparse.Namespace,
    turn_index: int,
) -> int | None:
    _apply_run_defaults(turn_args)
    blocking_reasons = _cli_blocking_reasons(turn_args)
    if not blocking_reasons:
        return None
    output = _blocking_output(turn_args, blocking_reasons)
    output["exit_code"] = EXIT_BLOCKING
    print(
        _chat_turn_text_output(
            output,
            CHAT_NO_LIVE_ASSISTANT_MESSAGE,
            turn_index,
        )
    )
    return EXIT_BLOCKING


def _print_and_record_operation_flow_result(
    *,
    history: MutableSequence[dict[str, str]],
    user_text: str,
    terminal_display_text: str,
) -> None:
    print(terminal_display_text)
    history.append(
        _chat_history_entry(
            user_text=user_text,
            assistant_text=terminal_display_text,
        )
    )


def _operation_flow_not_handled(
    latest_plan_display_text: str | None,
    latest_plan_snapshot: Any | None,
) -> ChatOperationFlowTurnResult:
    return ChatOperationFlowTurnResult(
        handled=False,
        exit_code=None,
        latest_plan_display_text=latest_plan_display_text,
        latest_plan_snapshot=latest_plan_snapshot,
    )


def _operation_flow_continue(
    latest_plan_display_text: str | None,
    latest_plan_snapshot: Any | None,
) -> ChatOperationFlowTurnResult:
    return ChatOperationFlowTurnResult(
        handled=True,
        exit_code=None,
        latest_plan_display_text=latest_plan_display_text,
        latest_plan_snapshot=latest_plan_snapshot,
    )


def _operation_flow_exit(
    exit_code: int,
    latest_plan_display_text: str | None,
    latest_plan_snapshot: Any | None,
) -> ChatOperationFlowTurnResult:
    return ChatOperationFlowTurnResult(
        handled=True,
        exit_code=exit_code,
        latest_plan_display_text=latest_plan_display_text,
        latest_plan_snapshot=latest_plan_snapshot,
    )
