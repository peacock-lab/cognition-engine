"""Chat task workflow dispatch for the Cognition System CLI."""

from __future__ import annotations

import argparse
import re
from collections.abc import MutableSequence
from dataclasses import dataclass
from typing import Any, Literal

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
    ExternalReadonlyAskLlmInvocationServiceFactory,
    RequestBuilder,
    RunGatewayExecutor,
    TwfLlmInvocationServiceFactory,
)
from cognition_cli.chat.output import (
    _assistant_text_from_chat_turn,
    _chat_turn_text_output,
)
from cognition_cli.chat.external_readonly_bridge import (
    ChatExternalReadonlyAnswerSnapshot,
    ChatExternalReadonlyBridgeState,
    build_chat_external_readonly_bridge_turn,
    chat_external_readonly_ask_text_output,
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
EXTERNAL_READONLY_EVIDENCE_QA_HINT = (
    "当前 chat 入口只把 external-readonly evidence-output 作为 reference-review "
    "资料使用，不作为受控问答或追问入口。请改用 "
    "`cognition external-readonly ask --evidence-path ... --question ...`；"
    "同一证据多轮追问请在同一进程追加 `--follow-up-question ...`。"
)
CHAT_SESSION_OPERATION_SUMMARY_WARNING = "chat_session_operation_summary"
CHAT_SESSION_EXPERIENCE_SUGGESTIONS_WARNING = (
    "chat_session_experience_suggestions"
)
CHAT_SESSION_EXPERIENCE_GUIDE_WARNING = "chat_session_experience_guide"
_URL_RE = re.compile(r"https?://[^\s，。；：,;!！?？）)]+", re.IGNORECASE)


@dataclass(frozen=True)
class ChatTurnDispatchResult:
    exit_code: int | None
    latest_plan_display_text: str | None
    latest_plan_snapshot: Any | None
    pending_reference_path_add: PendingReferencePathAdd | None = None
    external_readonly_bridge_state: ChatExternalReadonlyBridgeState | None = None


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
    external_readonly_bridge_state: ChatExternalReadonlyBridgeState | None,
    entry_runner: EntryRunner | None,
    request_builder: RequestBuilder | None,
    use_gateway_entry: bool = False,
    run_gateway_executor: RunGatewayExecutor | None = None,
    twf_llm_invocation_service_factory: (
        TwfLlmInvocationServiceFactory | None
    ) = None,
    external_readonly_ask_llm_invocation_service_factory: (
        ExternalReadonlyAskLlmInvocationServiceFactory | None
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
            external_readonly_bridge_state=external_readonly_bridge_state,
        )

    session_meta_result = _dispatch_chat_session_meta_message_if_needed(
        user_text=user_text,
        turn_index=turn_index,
        history=history,
        latest_plan_display_text=latest_plan_display_text,
        latest_plan_snapshot=latest_plan_snapshot,
        pending_reference_path_add=pending_reference_path_add,
        external_readonly_bridge_state=external_readonly_bridge_state,
    )
    if session_meta_result is not None:
        return session_meta_result

    external_bridge_result = build_chat_external_readonly_bridge_turn(
        args=args,
        user_text=user_text,
        bridge_state=external_readonly_bridge_state,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        llm_invocation_service_factory=(
            external_readonly_ask_llm_invocation_service_factory
        ),
    )
    if external_bridge_result.handled:
        return _dispatch_external_readonly_bridge_message(
            user_text=user_text,
            turn_index=turn_index,
            history=history,
            latest_plan_display_text=latest_plan_display_text,
            latest_plan_snapshot=latest_plan_snapshot,
            bridge_result=external_bridge_result,
            pending_reference_path_add=pending_reference_path_add,
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
            external_readonly_bridge_state=external_readonly_bridge_state,
        )

    external_readonly_qa_hint = _external_readonly_evidence_qa_hint_if_needed(
        args,
        user_text,
    )
    if external_readonly_qa_hint is not None:
        return _dispatch_reference_path_control_message(
            user_text=user_text,
            turn_index=turn_index,
            history=history,
            latest_plan_display_text=latest_plan_display_text,
            latest_plan_snapshot=latest_plan_snapshot,
            assistant_text=external_readonly_qa_hint,
            warning_code="external_readonly_evidence_qa_requires_ask_entry",
            pending_reference_path_add=None,
            external_readonly_bridge_state=external_readonly_bridge_state,
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


def _external_readonly_evidence_qa_hint_if_needed(
    args: argparse.Namespace,
    user_text: str,
) -> str | None:
    if not tuple(getattr(args, "external_readonly_evidence_paths", ()) or ()):
        return None
    normalized = "".join(user_text.strip().split()).lower()
    if not normalized:
        return None
    if _looks_like_reference_review_intent(normalized):
        return None
    if _looks_like_external_readonly_evidence_qa(normalized):
        return EXTERNAL_READONLY_EVIDENCE_QA_HINT
    return None


def _looks_like_session_operation_summary(user_text: str) -> bool:
    normalized = "".join(user_text.strip().split()).lower()
    if not normalized:
        return False
    has_self_scope = any(
        keyword in normalized
        for keyword in ("我以上", "我上述", "以上操作", "上述操作", "刚才操作", "前面操作")
    )
    has_summary_intent = any(
        keyword in normalized
        for keyword in ("总结", "小结", "概括", "回顾", "整理")
    )
    return has_self_scope and has_summary_intent


def _looks_like_session_experience_suggestions(user_text: str) -> bool:
    normalized = "".join(user_text.strip().split()).lower()
    if not normalized:
        return False
    has_current_scope = any(
        keyword in normalized
        for keyword in (
            "基于以上",
            "基于上述",
            "结合以上",
            "结合上述",
            "以上操作",
            "上述操作",
            "刚才操作",
            "前面操作",
        )
    )
    has_experience_intent = any(
        keyword in normalized
        for keyword in (
            "用户体验",
            "体验",
            "实测",
            "测试",
            "试下",
            "试一下",
            "值得体验",
            "哪些方面",
            "下一步",
        )
    )
    return has_current_scope and has_experience_intent


def _looks_like_session_experience_guide(user_text: str) -> bool:
    normalized = "".join(user_text.strip().split()).lower()
    if not normalized:
        return False
    has_guide_intent = any(
        keyword in normalized
        for keyword in (
            "体验指引",
            "如何操作",
            "如何具体体验",
            "怎么体验",
            "怎样体验",
            "命令行还是自然语言",
            "当前的交互",
            "具体体验",
        )
    )
    has_experience_context = any(
        keyword in normalized
        for keyword in (
            "体验",
            "建议",
            "操作",
            "当前交互",
            "当前的交互",
            "命令行",
            "自然语言",
        )
    )
    return has_guide_intent and has_experience_context


def _dispatch_chat_session_meta_message_if_needed(
    *,
    user_text: str,
    turn_index: int,
    history: MutableSequence[dict[str, str]],
    latest_plan_display_text: str | None,
    latest_plan_snapshot: Any | None,
    pending_reference_path_add: PendingReferencePathAdd | None,
    external_readonly_bridge_state: ChatExternalReadonlyBridgeState | None,
) -> ChatTurnDispatchResult | None:
    if _looks_like_session_operation_summary(user_text):
        return _dispatch_chat_session_operation_summary(
            user_text=user_text,
            turn_index=turn_index,
            history=history,
            latest_plan_display_text=latest_plan_display_text,
            latest_plan_snapshot=latest_plan_snapshot,
            pending_reference_path_add=pending_reference_path_add,
            external_readonly_bridge_state=external_readonly_bridge_state,
        )
    if _looks_like_session_experience_guide(user_text):
        return _dispatch_chat_session_experience_guide(
            user_text=user_text,
            turn_index=turn_index,
            history=history,
            latest_plan_display_text=latest_plan_display_text,
            latest_plan_snapshot=latest_plan_snapshot,
            pending_reference_path_add=pending_reference_path_add,
            external_readonly_bridge_state=external_readonly_bridge_state,
        )
    if _looks_like_session_experience_suggestions(user_text):
        return _dispatch_chat_session_experience_suggestions(
            user_text=user_text,
            turn_index=turn_index,
            history=history,
            latest_plan_display_text=latest_plan_display_text,
            latest_plan_snapshot=latest_plan_snapshot,
            pending_reference_path_add=pending_reference_path_add,
            external_readonly_bridge_state=external_readonly_bridge_state,
        )
    return None


def _dispatch_chat_session_operation_summary(
    *,
    user_text: str,
    turn_index: int,
    history: MutableSequence[dict[str, str]],
    latest_plan_display_text: str | None,
    latest_plan_snapshot: Any | None,
    pending_reference_path_add: PendingReferencePathAdd | None,
    external_readonly_bridge_state: ChatExternalReadonlyBridgeState | None,
) -> ChatTurnDispatchResult:
    assistant_text = _chat_session_operation_summary_text(history)
    print(
        "\n".join(
            [
                f"assistant: {assistant_text}",
                "status: success",
                f"turn: {turn_index}",
                "chat_session_operation_summary: true",
                "live_llm_call_performed: false",
                "ollama_call_performed: false",
                "summary_scope: current_process_only; durable_session=false; "
                "memory_enabled=false",
                f"warnings: {CHAT_SESSION_OPERATION_SUMMARY_WARNING}",
            ]
        )
    )
    entry = _chat_history_entry(user_text=user_text, assistant_text=assistant_text)
    entry.update(
        {
            "status": "success",
            "chat_session_operation_summary": "true",
        }
    )
    history.append(entry)
    next_bridge_state = _bridge_state_with_last_answer(
        external_readonly_bridge_state,
        assistant_text=assistant_text,
        source_kind="chat_session_operation_summary",
        turn_index=turn_index,
    )
    return _chat_turn_continue(
        latest_plan_display_text,
        latest_plan_snapshot,
        pending_reference_path_add=pending_reference_path_add,
        external_readonly_bridge_state=next_bridge_state,
    )


def _dispatch_chat_session_experience_guide(
    *,
    user_text: str,
    turn_index: int,
    history: MutableSequence[dict[str, str]],
    latest_plan_display_text: str | None,
    latest_plan_snapshot: Any | None,
    pending_reference_path_add: PendingReferencePathAdd | None,
    external_readonly_bridge_state: ChatExternalReadonlyBridgeState | None,
) -> ChatTurnDispatchResult:
    assistant_text = _chat_session_experience_guide_text(history)
    print(
        "\n".join(
            [
                f"assistant: {assistant_text}",
                "status: success",
                f"turn: {turn_index}",
                "chat_session_experience_guide: true",
                "live_llm_call_performed: false",
                "ollama_call_performed: false",
                "guide_scope: current_process_only; durable_session=false; "
                "memory_enabled=false",
                f"warnings: {CHAT_SESSION_EXPERIENCE_GUIDE_WARNING}",
            ]
        )
    )
    entry = _chat_history_entry(user_text=user_text, assistant_text=assistant_text)
    entry.update(
        {
            "status": "success",
            "chat_session_experience_guide": "true",
        }
    )
    history.append(entry)
    next_bridge_state = _bridge_state_with_last_answer(
        external_readonly_bridge_state,
        assistant_text=assistant_text,
        source_kind="chat_session_experience_guide",
        turn_index=turn_index,
    )
    return _chat_turn_continue(
        latest_plan_display_text,
        latest_plan_snapshot,
        pending_reference_path_add=pending_reference_path_add,
        external_readonly_bridge_state=next_bridge_state,
    )


def _dispatch_chat_session_experience_suggestions(
    *,
    user_text: str,
    turn_index: int,
    history: MutableSequence[dict[str, str]],
    latest_plan_display_text: str | None,
    latest_plan_snapshot: Any | None,
    pending_reference_path_add: PendingReferencePathAdd | None,
    external_readonly_bridge_state: ChatExternalReadonlyBridgeState | None,
) -> ChatTurnDispatchResult:
    assistant_text = _chat_session_experience_suggestions_text(history)
    print(
        "\n".join(
            [
                f"assistant: {assistant_text}",
                "status: success",
                f"turn: {turn_index}",
                "chat_session_experience_suggestions: true",
                "live_llm_call_performed: false",
                "ollama_call_performed: false",
                "suggestion_scope: current_process_only; durable_session=false; "
                "memory_enabled=false",
                f"warnings: {CHAT_SESSION_EXPERIENCE_SUGGESTIONS_WARNING}",
            ]
        )
    )
    entry = _chat_history_entry(user_text=user_text, assistant_text=assistant_text)
    entry.update(
        {
            "status": "success",
            "chat_session_experience_suggestions": "true",
        }
    )
    history.append(entry)
    next_bridge_state = _bridge_state_with_last_answer(
        external_readonly_bridge_state,
        assistant_text=assistant_text,
        source_kind="chat_session_experience_suggestions",
        turn_index=turn_index,
    )
    return _chat_turn_continue(
        latest_plan_display_text,
        latest_plan_snapshot,
        pending_reference_path_add=pending_reference_path_add,
        external_readonly_bridge_state=next_bridge_state,
    )


def _bridge_state_with_last_answer(
    bridge_state: ChatExternalReadonlyBridgeState | None,
    *,
    assistant_text: str,
    source_kind: Literal[
        "chat_session_operation_summary",
        "chat_session_experience_suggestions",
        "chat_session_experience_guide",
    ],
    turn_index: int,
) -> ChatExternalReadonlyBridgeState:
    state = bridge_state or ChatExternalReadonlyBridgeState()
    answer_text = " ".join(assistant_text.strip().split())
    if not answer_text:
        return state
    return ChatExternalReadonlyBridgeState(
        pending=state.pending,
        ask_session=state.ask_session,
        follow_up_unavailable=state.follow_up_unavailable,
        last_answer=ChatExternalReadonlyAnswerSnapshot(
            answer_text=answer_text,
            source_kind=source_kind,
            source_turn_index=turn_index,
        ),
    )


def _chat_session_experience_guide_text(
    history: MutableSequence[dict[str, str]],
) -> str:
    if history:
        opening = (
            "当前已经在 `uv run cognition chat` 交互里，继续体验主要直接输入自然语言；"
            "不需要重新输入命令。"
        )
    else:
        opening = (
            "建议先在终端运行 `uv run cognition chat`，进入交互后再按提示输入。"
        )
    current_session_steps = [
        "答案态变换：直接输入 `将上面的回答改写成适合初中生理解的版本`。",
        "证据态追问：直接输入 `它是否适合实际运营？`。",
        "当前进程总结：直接输入 `对我以上操作做个总结`。",
        "体验建议 / 指引：直接输入 `基于以上操作，给我下一步体验指引`。",
    ]
    restart_steps = [
        "拒绝授权路径：重新运行 `uv run cognition chat`，输入 URL 和问题后，在外部只读抓取或受控大模型回答处输入 `no`。",
        "输入边界：重新运行后测试空输入、`URL/evidence: https://example.com` 前缀、前后空格和 `/exit`。",
        "中断边界：在提示等待输入时按 Ctrl+C，观察是否给出可理解的 interrupted 提示。",
    ]
    current_text = "；".join(
        f"{index}. {step}" for index, step in enumerate(current_session_steps, start=1)
    )
    restart_text = "；".join(
        f"{index}. {step}" for index, step in enumerate(restart_steps, start=1)
    )
    return (
        f"{opening} 当前交互内可测：{current_text}。需要新开一轮命令行的边界测试："
        f"{restart_text}。本指引只基于当前进程 chat history，不读取长期 Memory，"
        "不代表跨进程会话能力。"
    )


def _chat_session_experience_suggestions_text(
    history: MutableSequence[dict[str, str]],
) -> str:
    if not history:
        return (
            "当前进程内还没有足够操作记录可生成体验建议。建议先完成一次 URL 输入、"
            "资料问题、模型选择和授权确认，再体验追问、答案变换、拒绝授权和退出路径。"
        )

    suggestions: list[str] = []
    has_successful_external_answer = _has_successful_external_readonly_answer(history)
    has_blocked_external_answer = _has_blocked_external_readonly_answer(history)
    if _first_history_url(history):
        suggestions.append(
            "验证外部 URL 输入的容错边界，例如前后空格、`URL/evidence:` 前缀和直接 URL。"
        )
    if has_blocked_external_answer and not has_successful_external_answer:
        suggestions.append(
            "先复验首轮资料问答成功路径：重新输入 URL 和问题，确认外部只读抓取与受控回答没有被治理或传输错误拦截。"
        )
    elif any(_normalized_history_user(item) in {"2", "gemma4"} for item in history):
        suggestions.append(
            "继续比较 Gemma4 本地路径下的证据追问、短摘要和长摘要前置拦截。"
        )
    if has_successful_external_answer and any(
        _looks_like_answer_transform_history_text(item.get("user", ""))
        for item in history
    ):
        suggestions.append(
            "体验答案态变换链路，例如翻译、改成一句话、换表达风格，并确认不重新抓取资料。"
        )
    elif _has_failed_answer_transformation(history):
        suggestions.append(
            "先完成一次成功资料问答，再体验答案态变换；没有上一轮成功答案时，翻译或改写请求应明确 fail closed。"
        )
    if _last_matching_user_text(
        history,
        lambda text: any(keyword in text for keyword in ("适用", "场景", "用途")),
    ):
        if _has_successful_follow_up(history):
            suggestions.append(
                "继续体验证据态追问，例如用途、限制、是否适合实际运营，并确认仍围绕同一证据。"
            )
        elif _has_failed_follow_up(history):
            suggestions.append(
                "先让首轮资料问答形成可追问证据，再体验用途、限制、是否适合实际运营等证据态追问。"
            )
    if any(_looks_like_session_operation_summary(item.get("user", "")) for item in history):
        suggestions.append(
            "体验当前进程操作总结后的追问边界，确认系统会说明只基于本进程 history。"
        )
    suggestions.extend(
        [
            "单独体验拒绝授权路径：外部只读抓取输入 no、受控大模型回答输入 no。",
            "体验结束边界：直接 `/exit`、空输入、以及 Ctrl+C 中断时的提示是否可理解。",
        ]
    )

    deduped: list[str] = []
    for suggestion in suggestions:
        if suggestion not in deduped:
            deduped.append(suggestion)
    numbered = "；".join(
        f"{index}. {suggestion}" for index, suggestion in enumerate(deduped, start=1)
    )
    return (
        f"基于当前进程内已完成的操作，建议继续体验：{numbered}。这些建议只来自当前 "
        "chat history，不读取长期 Memory，不代表跨进程会话能力。"
    )


def _chat_session_operation_summary_text(
    history: MutableSequence[dict[str, str]],
) -> str:
    if not history:
        return (
            "当前会话还没有可总结的操作记录。本摘要只基于当前进程内的 "
            "chat history，不启用长期 Memory 或持久会话。"
        )
    operations: list[str] = []
    url = _first_history_url(history)
    if url:
        operations.append(f"提供外部只读 URL：{url}")
    question = _first_matching_user_text(
        history,
        lambda text: any(
            keyword in text
            for keyword in ("这份资料", "这个资料", "这个网页", "主要说明")
        ),
    )
    if question:
        operations.append(f"提出资料问题：{question}")
    if any(_normalized_history_user(item) in {"2", "gemma4"} for item in history):
        operations.append("选择 Gemma4 本地模型路径。")
    elif any(_normalized_history_user(item) in {"1", "deepseek"} for item in history):
        operations.append("选择 DeepSeek 外部 provider 路径。")
    if any(_normalized_history_user(item) in {"y", "yes", "1", "同意"} for item in history):
        operations.append("输入外部只读抓取 / 受控大模型回答等授权确认。")
    if _has_blocked_external_readonly_answer(history):
        operations.append("首轮 external-readonly 问答被治理或传输条件拦截，未形成资料答案。")
    successful_transformations = [
        user_text
        for item in history
        if (user_text := item.get("user", ""))
        and _looks_like_answer_transform_history_text(user_text)
        and _history_status(item) == "success"
        and item.get("answer_scoped_transformation") == "true"
    ]
    for text in successful_transformations[-3:]:
        operations.append(f"对上一轮答案做变换：{text}")
    failed_transformations = [
        user_text
        for item in history
        if (user_text := item.get("user", ""))
        and _looks_like_answer_transform_history_text(user_text)
        and _history_status(item) != "success"
    ]
    for text in failed_transformations[-2:]:
        operations.append(f"尝试答案变换但未形成结果：{text}")
    follow_up = _last_matching_history_item(
        history,
        lambda text: any(keyword in text for keyword in ("适用", "场景", "用途")),
    )
    if follow_up:
        follow_up_text = follow_up.get("user", "")
        if follow_up.get("follow_up") == "true" and _history_status(follow_up) == "success":
            operations.append(f"围绕同一受治理证据追问：{follow_up_text}")
        else:
            operations.append(f"尝试证据态追问但没有可追问证据：{follow_up_text}")
    if not operations:
        operations.append("进行了当前进程内 chat 交互。")
    numbered = "；".join(
        f"{index}. {operation}" for index, operation in enumerate(operations, start=1)
    )
    return (
        f"以上操作小结：{numbered}。本小结只基于当前进程内 chat history，"
        "不读取长期 Memory，不代表可跨进程恢复的持久会话。"
    )


def _first_history_url(history: MutableSequence[dict[str, str]]) -> str | None:
    for item in history:
        match = _URL_RE.search(item.get("user", ""))
        if match is not None:
            return match.group(0)
    return None


def _first_matching_user_text(
    history: MutableSequence[dict[str, str]],
    predicate: Any,
) -> str | None:
    for item in history:
        text = item.get("user", "")
        if text and predicate(text):
            return text
    return None


def _last_matching_user_text(
    history: MutableSequence[dict[str, str]],
    predicate: Any,
) -> str | None:
    for item in reversed(history):
        text = item.get("user", "")
        if text and predicate(text):
            return text
    return None


def _last_matching_history_item(
    history: MutableSequence[dict[str, str]],
    predicate: Any,
) -> dict[str, str] | None:
    for item in reversed(history):
        text = item.get("user", "")
        if text and predicate(text):
            return item
    return None


def _normalized_history_user(item: dict[str, str]) -> str:
    return "".join(item.get("user", "").strip().lower().split())


def _history_status(item: dict[str, str]) -> str:
    return item.get("status", "").strip().lower()


def _has_successful_external_readonly_answer(
    history: MutableSequence[dict[str, str]],
) -> bool:
    return any(
        item.get("external_readonly_ask") == "true"
        and _history_status(item) == "success"
        and item.get("answer_scoped_transformation") != "true"
        for item in history
    )


def _has_blocked_external_readonly_answer(
    history: MutableSequence[dict[str, str]],
) -> bool:
    return any(
        item.get("external_readonly_ask") == "true"
        and _history_status(item) in {"blocked", "failed"}
        and item.get("answer_scoped_transformation") != "true"
        for item in history
    )


def _has_failed_answer_transformation(
    history: MutableSequence[dict[str, str]],
) -> bool:
    return any(
        _looks_like_answer_transform_history_text(item.get("user", ""))
        and _history_status(item) != "success"
        for item in history
    )


def _has_successful_follow_up(history: MutableSequence[dict[str, str]]) -> bool:
    return any(
        item.get("follow_up") == "true" and _history_status(item) == "success"
        for item in history
    )


def _has_failed_follow_up(history: MutableSequence[dict[str, str]]) -> bool:
    return any(
        any(keyword in item.get("user", "") for keyword in ("适用", "场景", "用途"))
        and not (
            item.get("follow_up") == "true" and _history_status(item) == "success"
        )
        for item in history
    )


def _looks_like_answer_transform_history_text(value: str) -> bool:
    normalized = "".join(value.strip().split()).lower()
    has_answer_target = any(
        keyword in normalized
        for keyword in ("摘要", "上面的回答", "上述回答", "上一轮", "答案", "回答")
    )
    return has_answer_target and any(
        keyword in normalized
        for keyword in ("翻译", "译成", "改成", "改写", "一句话", "总结", "压缩")
    )


def _looks_like_reference_review_intent(normalized: str) -> bool:
    return any(
        keyword in normalized
        for keyword in (
            "审查",
            "复核",
            "检查",
            "评审",
            "风险",
            "问题",
            "建议",
            "是否符合",
            "是否一致",
            "是否需要更新",
        )
    )


def _looks_like_external_readonly_evidence_qa(normalized: str) -> bool:
    has_evidence_target = any(
        keyword in normalized
        for keyword in (
            "这份资料",
            "这个资料",
            "这份证据",
            "这个证据",
            "这个网页",
            "资料",
            "证据",
            "网页",
        )
    )
    has_question_intent = any(
        keyword in normalized
        for keyword in (
            "说明什么",
            "说明了什么",
            "主要说明",
            "讲什么",
            "回答",
            "问答",
            "追问",
            "基于证据",
        )
    )
    return has_evidence_target and has_question_intent


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
    external_readonly_bridge_state: ChatExternalReadonlyBridgeState | None,
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
    entry = _chat_history_entry(user_text=user_text, assistant_text=assistant_text)
    entry.update(
        {
            "status": "skipped",
            "warning": warning,
        }
    )
    history.append(entry)
    return _chat_turn_continue(
        latest_plan_display_text,
        latest_plan_snapshot,
        pending_reference_path_add=pending_reference_path_add,
        external_readonly_bridge_state=external_readonly_bridge_state,
    )


def _dispatch_external_readonly_bridge_message(
    *,
    user_text: str,
    turn_index: int,
    history: MutableSequence[dict[str, str]],
    latest_plan_display_text: str | None,
    latest_plan_snapshot: Any | None,
    bridge_result: Any,
    pending_reference_path_add: PendingReferencePathAdd | None,
) -> ChatTurnDispatchResult:
    assistant_text = bridge_result.assistant_text or ""
    if bridge_result.ask_output is not None:
        print(
            chat_external_readonly_ask_text_output(
                bridge_result.ask_output,
                assistant_text,
                turn_index=turn_index,
            )
        )
    else:
        warning = bridge_result.warning_code or "chat_external_readonly_bridge"
        print(
            "\n".join(
                [
                    f"assistant: {assistant_text}",
                    "status: skipped",
                    f"turn: {turn_index}",
                    "external_readonly_ask: true",
                    "live_llm_call_performed: false",
                    "ollama_call_performed: false",
                    f"warnings: {warning}",
                ]
            )
        )
    entry = _chat_history_entry(user_text=user_text, assistant_text=assistant_text)
    if bridge_result.ask_output is not None:
        output = bridge_result.ask_output
        entry.update(
            {
                "status": str(output.get("status") or ""),
                "external_readonly_ask": "true",
                "answer_scoped_transformation": str(
                    bool(output.get("answer_scoped_transformation"))
                ).lower(),
                "follow_up": str(bool(output.get("follow_up"))).lower(),
                "blocking_reasons": ",".join(
                    map(str, output.get("blocking_reasons") or ())
                ),
            }
        )
    else:
        entry.update(
            {
                "status": "skipped",
                "external_readonly_ask": "true",
                "warning": bridge_result.warning_code
                or "chat_external_readonly_bridge",
            }
        )
    history.append(entry)
    return _chat_turn_continue(
        latest_plan_display_text,
        latest_plan_snapshot,
        pending_reference_path_add=pending_reference_path_add,
        external_readonly_bridge_state=bridge_result.state,
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
    external_readonly_bridge_state: ChatExternalReadonlyBridgeState | None = None,
) -> ChatTurnDispatchResult:
    return ChatTurnDispatchResult(
        exit_code=None,
        latest_plan_display_text=latest_plan_display_text,
        latest_plan_snapshot=latest_plan_snapshot,
        pending_reference_path_add=pending_reference_path_add,
        external_readonly_bridge_state=external_readonly_bridge_state,
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
