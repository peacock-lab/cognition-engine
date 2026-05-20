"""Chat task workflow dispatch for the Cognition System CLI."""

from __future__ import annotations

import argparse
from collections.abc import MutableSequence
from dataclasses import dataclass
from typing import Any

from cognition_cli.constants import (
    EXIT_OK,
)
from cognition_cli.chat.references import (
    PendingReferencePathAdd,
    apply_confirmed_reference_path,
    build_reference_interaction,
)
from cognition_cli.services.runtime import (
    EntryRunner,
    RequestBuilder,
    RunGatewayExecutor,
    TwfLlmInvocationServiceFactory,
)
from cognition_cli.chat.output import (
    _assistant_text_from_chat_turn,
    _chat_turn_text_output,
)
from cognition_cli.chat.routing import (
    _chat_product_gateway_twf_route_projection,
    _chat_twf_route_from_product_gateway_projection,
)
from cognition_cli.chat.turns import (
    _chat_history_entry,
    _chat_input_payload,
    _chat_turn_args,
    _run_chat_turn,
)
from cognition_cli.chat.task_workflows import (
    _dispatch_chat_task_workflow_turn,
)


REFERENCE_PATH_STARTUP_HINT = (
    "我还没有收到可读取的具体文件路径。你可以直接发送具体文件地址，"
    "或使用 `/reference add <具体文件路径>`；当前版本不做目录扫描。"
)


@dataclass(frozen=True)
class ChatTurnDispatchResult:
    exit_code: int | None
    latest_plan_display_text: str | None
    latest_plan_snapshot: Any | None
    pending_reference_path_add: PendingReferencePathAdd | None = None


def _dispatch_chat_input_turn(
    *,
    args: argparse.Namespace,
    user_text: str,
    chat_session_id: str,
    turn_index: int,
    history: MutableSequence[dict[str, str]],
    latest_plan_display_text: str | None,
    latest_plan_snapshot: Any | None,
    pending_reference_path_add: PendingReferencePathAdd | None,
    entry_runner: EntryRunner | None,
    request_builder: RequestBuilder | None,
    use_gateway_entry: bool = False,
    run_gateway_executor: RunGatewayExecutor | None = None,
    twf_llm_invocation_service_factory: (
        TwfLlmInvocationServiceFactory | None
    ) = None,
) -> ChatTurnDispatchResult:
    reference_interaction = build_reference_interaction(
        args,
        user_text,
        pending_reference_path_add,
    )
    if reference_interaction.action == "confirmed":
        if pending_reference_path_add is not None:
            apply_confirmed_reference_path(args, pending_reference_path_add)
        user_text = reference_interaction.execute_user_text or user_text
        pending_reference_path_add = None
    elif reference_interaction.action in {"pending", "blocked", "cancelled", "waiting"}:
        return _dispatch_reference_path_control_message(
            user_text=user_text,
            turn_index=turn_index,
            history=history,
            latest_plan_display_text=latest_plan_display_text,
            latest_plan_snapshot=latest_plan_snapshot,
            assistant_text=reference_interaction.assistant_text or "",
            warning_code=reference_interaction.warning_code,
            pending_reference_path_add=reference_interaction.pending,
        )

    reference_hint = _reference_path_startup_hint_if_needed(args, user_text)
    if reference_hint is not None:
        return _dispatch_reference_path_control_message(
            user_text=user_text,
            turn_index=turn_index,
            history=history,
            latest_plan_display_text=latest_plan_display_text,
            latest_plan_snapshot=latest_plan_snapshot,
            assistant_text=reference_hint,
            warning_code="reference_path_not_configured",
            pending_reference_path_add=None,
        )

    task_route_projection = _chat_product_gateway_twf_route_projection(
        args=args,
        user_text=user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        history=history,
        previous_terminal_display_text=latest_plan_display_text,
    )
    task_route = _chat_twf_route_from_product_gateway_projection(
        task_route_projection
    )
    task_workflow_result = _dispatch_chat_task_workflow_turn(
        args=args,
        user_text=user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        history=history,
        latest_plan_display_text=latest_plan_display_text,
        latest_plan_snapshot=latest_plan_snapshot,
        task_route_projection=task_route_projection,
        task_route=task_route,
        twf_llm_invocation_service_factory=twf_llm_invocation_service_factory,
    )
    if task_workflow_result.handled:
        return _chat_turn_from_task_workflow_result(task_workflow_result)

    return _dispatch_default_chat_turn(
        args=args,
        user_text=user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        history=history,
        latest_plan_display_text=latest_plan_display_text,
        latest_plan_snapshot=latest_plan_snapshot,
        entry_runner=entry_runner,
        request_builder=request_builder,
        use_gateway_entry=use_gateway_entry,
        run_gateway_executor=run_gateway_executor,
    )


def _reference_path_startup_hint_if_needed(
    args: argparse.Namespace,
    user_text: str,
) -> str | None:
    if tuple(args.reference_paths) or tuple(
        getattr(args, "external_readonly_evidence_paths", ())
    ):
        return None
    if _looks_like_runtime_reference_path_arg(user_text):
        return REFERENCE_PATH_STARTUP_HINT
    if _looks_like_local_reference_material_query(user_text):
        return REFERENCE_PATH_STARTUP_HINT
    return None


def _dispatch_reference_path_control_message(
    *,
    user_text: str,
    turn_index: int,
    history: MutableSequence[dict[str, str]],
    latest_plan_display_text: str | None,
    latest_plan_snapshot: Any | None,
    assistant_text: str,
    warning_code: str | None,
    pending_reference_path_add: PendingReferencePathAdd | None,
) -> ChatTurnDispatchResult:
    warning = warning_code or "reference_path_control_message"
    print(
        "\n".join(
            [
                f"assistant: {assistant_text}",
                "status: skipped",
                f"turn: {turn_index}",
                "live_llm_call_performed: false",
                "ollama_call_performed: false",
                f"warnings: {warning}",
            ]
        )
    )
    history.append(_chat_history_entry(user_text=user_text, assistant_text=assistant_text))
    return _chat_turn_continue(
        latest_plan_display_text,
        latest_plan_snapshot,
        pending_reference_path_add=pending_reference_path_add,
    )


def _looks_like_runtime_reference_path_arg(user_text: str) -> bool:
    return "--reference-path" in user_text


def _looks_like_local_reference_material_query(user_text: str) -> bool:
    normalized = "".join(user_text.strip().split()).lower()
    if not normalized:
        return False
    has_action = any(
        keyword in normalized
        for keyword in (
            "查",
            "查看",
            "查找",
            "找",
            "看下",
            "读取",
            "打开",
            "梳理",
            "审查",
        )
    )
    has_reference_target = any(
        keyword in normalized
        for keyword in (
            "材料",
            "文件",
            "文件夹",
            "目录",
            "任务包",
            "结果包",
            "路径",
        )
    )
    return has_action and has_reference_target


def _dispatch_default_chat_turn(
    *,
    args: argparse.Namespace,
    user_text: str,
    chat_session_id: str,
    turn_index: int,
    history: MutableSequence[dict[str, str]],
    latest_plan_display_text: str | None,
    latest_plan_snapshot: Any | None,
    entry_runner: EntryRunner | None,
    request_builder: RequestBuilder | None,
    use_gateway_entry: bool = False,
    run_gateway_executor: RunGatewayExecutor | None = None,
) -> ChatTurnDispatchResult:
    turn_args = _chat_turn_args(args, chat_session_id, turn_index)
    input_payload = _chat_input_payload(
        input_summary=user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        history=history,
        history_limit=args.history_limit,
    )
    exit_code, output, entry_result = _run_chat_turn(
        turn_args,
        input_payload=input_payload,
        entry_runner=entry_runner,
        request_builder=request_builder,
        use_gateway_entry=use_gateway_entry,
        run_gateway_executor=run_gateway_executor,
    )
    if output is None:
        return _chat_turn_exit(
            exit_code,
            latest_plan_display_text,
            latest_plan_snapshot,
        )
    assistant_text = _assistant_text_from_chat_turn(output, entry_result)
    print(_chat_turn_text_output(output, assistant_text, turn_index))
    if exit_code != EXIT_OK:
        return _chat_turn_exit(
            exit_code,
            latest_plan_display_text,
            latest_plan_snapshot,
        )
    history.append(
        _chat_history_entry(user_text=user_text, assistant_text=assistant_text)
    )
    return _chat_turn_continue(latest_plan_display_text, latest_plan_snapshot)


def _chat_turn_from_task_workflow_result(
    task_workflow_result: Any,
) -> ChatTurnDispatchResult:
    return ChatTurnDispatchResult(
        exit_code=task_workflow_result.exit_code,
        latest_plan_display_text=task_workflow_result.latest_plan_display_text,
        latest_plan_snapshot=task_workflow_result.latest_plan_snapshot,
    )


def _chat_turn_continue(
    latest_plan_display_text: str | None,
    latest_plan_snapshot: Any | None,
    *,
    pending_reference_path_add: PendingReferencePathAdd | None = None,
) -> ChatTurnDispatchResult:
    return ChatTurnDispatchResult(
        exit_code=None,
        latest_plan_display_text=latest_plan_display_text,
        latest_plan_snapshot=latest_plan_snapshot,
        pending_reference_path_add=pending_reference_path_add,
    )


def _chat_turn_exit(
    exit_code: int,
    latest_plan_display_text: str | None,
    latest_plan_snapshot: Any | None,
) -> ChatTurnDispatchResult:
    return ChatTurnDispatchResult(
        exit_code=exit_code,
        latest_plan_display_text=latest_plan_display_text,
        latest_plan_snapshot=latest_plan_snapshot,
        pending_reference_path_add=None,
    )
