"""Explicit chat bridge into the external-readonly ask product path."""

from __future__ import annotations

import argparse
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from cognition_cli.constants import CHAT_RESPONSE_PREVIEW_LIMIT
from cognition_cli.services.runtime import (
    ExternalReadonlyAskLlmInvocationServiceFactory,
    ExternalReadonlyAskProviderCredentialStoreFactory,
)
from cognition_cli.external_readonly.fetch import (
    REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION,
)
from cognition_cli.parser import build_parser
from product_application_assembly.evidence_summary_answer_ask_interaction import (
    EvidenceSummaryAnswerAskInteractionResult,
    EvidenceSummaryAnswerAskInteractionState,
)


CHAT_EXTERNAL_READONLY_BRIDGE_WARNING = "chat_external_readonly_bridge"
CHAT_EXTERNAL_READONLY_BRIDGE_PENDING_WARNING = (
    "chat_external_readonly_bridge_pending"
)
CHAT_EXTERNAL_READONLY_BRIDGE_DECLINED_WARNING = (
    "chat_external_readonly_bridge_declined"
)
CHAT_ANSWER_TRANSFORMATION_SNAPSHOT_MISSING_WARNING = (
    "chat_answer_transformation_snapshot_missing"
)
CHAT_ANSWER_TRANSFORMATION_WARNING = "chat_answer_scoped_transformation"
CHAT_ANSWER_TRANSFORMATION_FAILURE = "chat_answer_scoped_transformation_failed"

ChatExternalReadonlyInitialAskRunner = Callable[
    ...,
    EvidenceSummaryAnswerAskInteractionResult,
]
ChatExternalReadonlyFollowUpAskRunner = Callable[
    ...,
    EvidenceSummaryAnswerAskInteractionResult,
]

_URL_RE = re.compile(
    r"https?://[^\s，。；：,;!！?？）)]+",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ChatExternalReadonlyPendingAsk:
    """Current in-chat external-readonly ask onboarding state."""

    stage: Literal[
        "await_question",
        "await_model",
        "await_fetch_confirm",
        "await_live_llm_confirm",
        "await_provider_confirm",
        "await_deepseek_key_mode",
    ]
    source_url: str | None
    evidence_paths: tuple[str, ...]
    question: str | None
    model_alias: str | None = None


@dataclass(frozen=True)
class ChatExternalReadonlyAnswerSnapshot:
    """CLI-local last answer text; not durable Session or Memory."""

    answer_text: str
    source_kind: Literal[
        "external_readonly_ask_answer",
        "external_readonly_follow_up",
        "answer_scoped_transformation",
        "chat_session_operation_summary",
        "chat_session_experience_suggestions",
        "chat_session_experience_guide",
    ]
    source_turn_index: int
    evidence_refs: tuple[str, ...] = ()
    additional_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChatExternalReadonlyBridgeState:
    """Temporary chat bridge state; not durable Session or Memory."""

    pending: ChatExternalReadonlyPendingAsk | None = None
    ask_session: EvidenceSummaryAnswerAskInteractionState | None = None
    follow_up_unavailable: bool = False
    last_answer: ChatExternalReadonlyAnswerSnapshot | None = None


@dataclass(frozen=True)
class ChatExternalReadonlyBridgeResult:
    handled: bool
    assistant_text: str | None = None
    warning_code: str | None = None
    ask_output: Mapping[str, Any] | None = None
    state: ChatExternalReadonlyBridgeState | None = None


def build_chat_external_readonly_bridge_turn(
    *,
    args: argparse.Namespace,
    user_text: str,
    bridge_state: ChatExternalReadonlyBridgeState | None,
    chat_session_id: str,
    turn_index: int,
    llm_invocation_service_factory: (
        ExternalReadonlyAskLlmInvocationServiceFactory | None
    ),
    provider_credential_store_factory: (
        ExternalReadonlyAskProviderCredentialStoreFactory | None
    ) = None,
    initial_ask_runner: ChatExternalReadonlyInitialAskRunner | None = None,
    follow_up_ask_runner: ChatExternalReadonlyFollowUpAskRunner | None = None,
) -> ChatExternalReadonlyBridgeResult:
    """Return an explicit chat-to-external-readonly turn, if applicable."""

    state = bridge_state or ChatExternalReadonlyBridgeState()
    if state.pending is not None:
        return _continue_pending(
            args=args,
            user_text=user_text,
            pending=state.pending,
            previous_state=state,
            chat_session_id=chat_session_id,
            turn_index=turn_index,
            llm_invocation_service_factory=llm_invocation_service_factory,
            provider_credential_store_factory=provider_credential_store_factory,
            initial_ask_runner=initial_ask_runner,
            follow_up_ask_runner=follow_up_ask_runner,
        )

    if _looks_like_answer_transformation(user_text):
        if state.last_answer is None:
            if "资料" in user_text:
                return ChatExternalReadonlyBridgeResult(handled=False, state=state)
            return _control_message(
                "当前没有可变换的上一轮答案；请先完成一次 external-readonly "
                "问答，或明确输入 URL/evidence 后提问。",
                previous_state=state,
                pending=None,
                warning_code=CHAT_ANSWER_TRANSFORMATION_SNAPSHOT_MISSING_WARNING,
            )
        return _run_answer_transformation(
            user_text=user_text,
            state=state,
            turn_index=turn_index,
            follow_up_ask_runner=follow_up_ask_runner,
        )

    if state.ask_session is not None and _looks_like_follow_up(user_text):
        if follow_up_ask_runner is None:
            return ChatExternalReadonlyBridgeResult(handled=False, state=state)
        return _run_follow_up(
            user_text=user_text,
            state=state,
            turn_index=turn_index,
            follow_up_ask_runner=follow_up_ask_runner,
        )

    if state.follow_up_unavailable and _looks_like_follow_up(user_text):
        return _control_message(
            "上一轮 external-readonly 问答未形成可追问证据；"
            "请重新输入 URL 或 evidence path 后再提问。",
            previous_state=state,
            pending=None,
        )

    pending = _pending_from_user_text(args, user_text)
    if pending is None:
        return ChatExternalReadonlyBridgeResult(handled=False, state=state)
    if llm_invocation_service_factory is None or initial_ask_runner is None:
        return ChatExternalReadonlyBridgeResult(handled=False, state=state)
    return _prompt_for_next(pending, previous_state=state)


def chat_external_readonly_ask_text_output(
    output: Mapping[str, Any],
    assistant_text: str,
    *,
    turn_index: int,
) -> str:
    """Render a chat turn backed by external-readonly ask output."""

    lines = [
        f"assistant: {assistant_text}",
        f"status: {output.get('status') or 'unknown'}",
        f"turn: {turn_index}",
        "external_readonly_ask: true",
        f"answer_run_ref: {output.get('answer_run_ref') or 'unavailable'}",
        f"answer_trace_ref: {output.get('answer_trace_ref') or 'unavailable'}",
        f"answer_artifact_ref: {output.get('answer_artifact_ref') or 'unavailable'}",
        "observability_summary_ref: "
        f"{output.get('observability_summary_ref') or 'unavailable'}",
        f"trace_inspect_ref: {output.get('trace_inspect_ref') or 'unavailable'}",
        f"readonly_refs_status: {output.get('readonly_refs_status') or 'unknown'}",
        "llm_call_attempted: "
        f"{str(output.get('llm_call_attempted') is True).lower()}",
        "llm_runtime_call_performed: "
        f"{str(output.get('llm_runtime_call_performed') is True).lower()}",
    ]
    if output.get("answer_scoped_transformation"):
        lines.extend(
            [
                "answer_scoped_transformation: true",
                "answer_scope: answer_scoped; temporary_only; "
                "durable_session=false; memory_enabled=false",
                "answer_transform_hint: 本轮仅基于上一轮回答文本变换；"
                "不重新抓取资料，不启用长期 Memory 或持久会话。",
            ]
        )
    else:
        lines.extend(
            [
                "follow_up_scope: temporary_only; durable_session=false; "
                "memory_enabled=false",
                "follow_up_hint: 追问仅在当前进程内围绕同一受治理证据继续；"
                "不启用长期 Memory 或持久会话。",
            ]
        )
    if output.get("follow_up"):
        lines.append(f"follow_up_turn_index: {output.get('follow_up_turn_index')}")
    if output.get("answer_run_status"):
        lines.append(f"answer_run_status: {output.get('answer_run_status')}")
    if output.get("answer_run_unavailable_reason"):
        lines.append(
            "answer_run_unavailable_reason: "
            f"{output.get('answer_run_unavailable_reason')}"
        )
    if output.get("answer_trace_status"):
        lines.append(f"answer_trace_status: {output.get('answer_trace_status')}")
    if output.get("answer_trace_unavailable_reason"):
        lines.append(
            "answer_trace_unavailable_reason: "
            f"{output.get('answer_trace_unavailable_reason')}"
        )
    if output.get("answer_artifact_status"):
        lines.append(
            f"answer_artifact_status: {output.get('answer_artifact_status')}"
        )
    if output.get("answer_artifact_unavailable_reason"):
        lines.append(
            "answer_artifact_unavailable_reason: "
            f"{output.get('answer_artifact_unavailable_reason')}"
        )
    if output.get("observability_summary_status"):
        lines.append(
            "observability_summary_status: "
            f"{output.get('observability_summary_status')}"
        )
    if output.get("observability_summary_unavailable_reason"):
        lines.append(
            "observability_summary_unavailable_reason: "
            f"{output.get('observability_summary_unavailable_reason')}"
        )
    if output.get("trace_inspect_status"):
        lines.append(f"trace_inspect_status: {output.get('trace_inspect_status')}")
    if output.get("trace_inspect_unavailable_reason"):
        lines.append(
            "trace_inspect_unavailable_reason: "
            f"{output.get('trace_inspect_unavailable_reason')}"
        )
    trace_inspect_summary = output.get("trace_inspect_summary")
    if isinstance(trace_inspect_summary, Mapping):
        reason = trace_inspect_summary.get("inspect_reason")
        if reason:
            lines.append(f"trace_inspect_reason: {reason}")
        explanation = trace_inspect_summary.get("user_explanation")
        if explanation:
            lines.append(f"trace_inspect_explanation: {explanation}")
    safe_observability_summary = output.get("safe_observability_summary")
    observability_explanation_printed = False
    if isinstance(safe_observability_summary, Mapping):
        reason = safe_observability_summary.get("reason")
        if reason:
            lines.append(f"observability_reason: {reason}")
        explanation = safe_observability_summary.get("user_explanation")
        if explanation:
            lines.append(f"observability_explanation: {explanation}")
            observability_explanation_printed = True
    if output.get("observability_explanation") and not observability_explanation_printed:
        lines.append(
            f"observability_explanation: {output.get('observability_explanation')}"
        )
    blocking_reasons = output.get("blocking_reasons") or []
    warnings = output.get("warnings") or []
    if blocking_reasons:
        lines.append("blocking_reasons: " + ", ".join(map(str, blocking_reasons)))
    if warnings:
        lines.append("warnings: " + ", ".join(map(str, warnings)))
    return "\n".join(lines)


def _continue_pending(
    *,
    args: argparse.Namespace,
    user_text: str,
    pending: ChatExternalReadonlyPendingAsk,
    previous_state: ChatExternalReadonlyBridgeState,
    chat_session_id: str,
    turn_index: int,
    llm_invocation_service_factory: ExternalReadonlyAskLlmInvocationServiceFactory,
    provider_credential_store_factory: (
        ExternalReadonlyAskProviderCredentialStoreFactory | None
    ) = None,
    initial_ask_runner: ChatExternalReadonlyInitialAskRunner | None = None,
    follow_up_ask_runner: ChatExternalReadonlyFollowUpAskRunner | None = None,
) -> ChatExternalReadonlyBridgeResult:
    if pending.stage == "await_question":
        question = _normalized_text(user_text)
        if not question:
            return _prompt_for_next(pending, previous_state=previous_state)
        return _prompt_for_next(
            ChatExternalReadonlyPendingAsk(
                stage="await_model",
                source_url=pending.source_url,
                evidence_paths=pending.evidence_paths,
                question=question,
            ),
            previous_state=previous_state,
        )

    if pending.stage == "await_model":
        model_alias = _model_alias(user_text)
        if model_alias is None:
            return _control_message(
                "请选择模型：1) deepseek  2) gemma4",
                previous_state=previous_state,
                pending=pending,
            )
        next_stage: ChatExternalReadonlyPendingAsk
        if pending.source_url:
            next_stage = ChatExternalReadonlyPendingAsk(
                stage="await_fetch_confirm",
                source_url=pending.source_url,
                evidence_paths=pending.evidence_paths,
                question=pending.question,
                model_alias=model_alias,
            )
        else:
            next_stage = ChatExternalReadonlyPendingAsk(
                stage="await_live_llm_confirm",
                source_url=pending.source_url,
                evidence_paths=pending.evidence_paths,
                question=pending.question,
                model_alias=model_alias,
            )
        return _prompt_for_next(next_stage, previous_state=previous_state)

    if pending.stage == "await_fetch_confirm":
        if not _affirmative(user_text):
            return _declined("用户未授权本次外部只读抓取，已停止进入问答。")
        return _prompt_for_next(
            ChatExternalReadonlyPendingAsk(
                stage="await_live_llm_confirm",
                source_url=pending.source_url,
                evidence_paths=pending.evidence_paths,
                question=pending.question,
                model_alias=pending.model_alias,
            ),
            previous_state=previous_state,
        )

    if pending.stage == "await_live_llm_confirm":
        if not _affirmative(user_text):
            return _declined("用户未授权本次受控大模型回答，已停止进入模型调用。")
        if pending.model_alias == "deepseek":
            return _prompt_for_next(
                ChatExternalReadonlyPendingAsk(
                    stage="await_provider_confirm",
                    source_url=pending.source_url,
                    evidence_paths=pending.evidence_paths,
                    question=pending.question,
                    model_alias=pending.model_alias,
                ),
                previous_state=previous_state,
            )
        return _execute_initial(
            args=args,
            pending=pending,
            chat_session_id=chat_session_id,
            turn_index=turn_index,
            llm_invocation_service_factory=llm_invocation_service_factory,
            provider_credential_store_factory=provider_credential_store_factory,
            initial_ask_runner=initial_ask_runner,
        )

    if pending.stage == "await_provider_confirm":
        if not _affirmative(user_text):
            return _declined("用户未授权本次外部 provider 调用，已停止进入模型调用。")
        return _prompt_for_next(
            ChatExternalReadonlyPendingAsk(
                stage="await_deepseek_key_mode",
                source_url=pending.source_url,
                evidence_paths=pending.evidence_paths,
                question=pending.question,
                model_alias=pending.model_alias,
            ),
            previous_state=previous_state,
        )

    if pending.stage == "await_deepseek_key_mode":
        key_mode = _deepseek_key_mode(user_text)
        if key_mode is None:
            return _declined("用户取消 DeepSeek key 使用方式，已停止进入模型调用。")
        return _execute_initial(
            args=args,
            pending=pending,
            chat_session_id=chat_session_id,
            turn_index=turn_index,
            llm_invocation_service_factory=llm_invocation_service_factory,
            provider_credential_store_factory=provider_credential_store_factory,
            deepseek_key_mode=key_mode,
            initial_ask_runner=initial_ask_runner,
        )

    return ChatExternalReadonlyBridgeResult(handled=False, state=previous_state)


def _execute_initial(
    *,
    args: argparse.Namespace,
    pending: ChatExternalReadonlyPendingAsk,
    chat_session_id: str,
    turn_index: int,
    llm_invocation_service_factory: ExternalReadonlyAskLlmInvocationServiceFactory,
    provider_credential_store_factory: (
        ExternalReadonlyAskProviderCredentialStoreFactory | None
    ) = None,
    deepseek_key_mode: Literal["stored", "prompt"] | None = None,
    initial_ask_runner: ChatExternalReadonlyInitialAskRunner | None = None,
) -> ChatExternalReadonlyBridgeResult:
    ask_args = _ask_args_from_pending(
        args,
        pending,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        deepseek_key_mode=deepseek_key_mode,
    )
    if initial_ask_runner is None:
        return ChatExternalReadonlyBridgeResult(handled=False)
    interaction = initial_ask_runner(
        ask_args,
        llm_invocation_service_factory=llm_invocation_service_factory,
        provider_credential_store_factory=provider_credential_store_factory,
    )
    output = interaction.output
    next_session = interaction.next_state
    next_snapshot = _answer_snapshot_from_output(
        output,
        turn_index=turn_index,
        source_kind="external_readonly_ask_answer",
    )
    next_state = ChatExternalReadonlyBridgeState(
        ask_session=next_session,
        follow_up_unavailable=next_session is None,
        last_answer=next_snapshot,
    )
    return ChatExternalReadonlyBridgeResult(
        handled=True,
        assistant_text=_assistant_text_from_ask_output(output),
        ask_output=output,
        state=next_state,
    )


def _run_follow_up(
    *,
    user_text: str,
    state: ChatExternalReadonlyBridgeState,
    turn_index: int,
    follow_up_ask_runner: ChatExternalReadonlyFollowUpAskRunner,
) -> ChatExternalReadonlyBridgeResult:
    if state.ask_session is None:
        return ChatExternalReadonlyBridgeResult(handled=False, state=state)
    interaction = follow_up_ask_runner(
        state.ask_session,
        user_text,
    )
    output = interaction.output
    next_session = interaction.next_state or state.ask_session
    next_snapshot = (
        _answer_snapshot_from_output(
            output,
            turn_index=turn_index,
            source_kind="external_readonly_follow_up",
        )
        or state.last_answer
    )
    return ChatExternalReadonlyBridgeResult(
        handled=True,
        assistant_text=_assistant_text_from_ask_output(output),
        ask_output=output,
        state=ChatExternalReadonlyBridgeState(
            ask_session=next_session,
            last_answer=next_snapshot,
        ),
    )


def _run_answer_transformation(
    *,
    user_text: str,
    state: ChatExternalReadonlyBridgeState,
    turn_index: int,
    follow_up_ask_runner: ChatExternalReadonlyFollowUpAskRunner | None,
) -> ChatExternalReadonlyBridgeResult:
    snapshot = state.last_answer
    session = state.ask_session
    if snapshot is None:
        return ChatExternalReadonlyBridgeResult(handled=False, state=state)
    if snapshot.source_kind in {
        "chat_session_operation_summary",
        "chat_session_experience_suggestions",
        "chat_session_experience_guide",
    }:
        local_answer = _local_meta_answer_transformation_text(
            snapshot=snapshot,
            question=user_text,
        )
        if local_answer is not None:
            output = _local_answer_transformation_output(
                request_id=f"chat-answer-transformation://turn-{turn_index:03d}",
                question=user_text,
                snapshot=snapshot,
                status="success",
                answer=local_answer,
            )
            next_snapshot = (
                _answer_snapshot_from_output(
                    output,
                    turn_index=turn_index,
                    source_kind="answer_scoped_transformation",
                )
                or snapshot
            )
            return ChatExternalReadonlyBridgeResult(
                handled=True,
                assistant_text=_assistant_text_from_ask_output(output),
                warning_code=CHAT_ANSWER_TRANSFORMATION_WARNING,
                ask_output=output,
                state=ChatExternalReadonlyBridgeState(
                    pending=state.pending,
                    ask_session=session,
                    follow_up_unavailable=state.follow_up_unavailable,
                    last_answer=next_snapshot,
                ),
            )
    if session is not None:
        if follow_up_ask_runner is None:
            return _control_message(
                "当前没有可用的 external-readonly ask 产品入口服务，"
                "无法执行答案范围变换。",
                previous_state=state,
                pending=state.pending,
                warning_code=CHAT_ANSWER_TRANSFORMATION_FAILURE,
            )
        interaction = follow_up_ask_runner(
            session,
            user_text,
            previous_output=_answer_snapshot_previous_output(snapshot),
            turns=(),
            request_id=session.request_id,
            follow_up_index=turn_index,
        )
        output = interaction.output
        next_session = interaction.next_state or session
        next_snapshot = (
            _answer_snapshot_from_output(
                output,
                turn_index=turn_index,
                source_kind="answer_scoped_transformation",
            )
            if output.get("status") == "success"
            else snapshot
        )
        return ChatExternalReadonlyBridgeResult(
            handled=True,
            assistant_text=_assistant_text_from_ask_output(output),
            warning_code=(
                CHAT_ANSWER_TRANSFORMATION_WARNING
                if output.get("status") == "success"
                else CHAT_ANSWER_TRANSFORMATION_FAILURE
            ),
            ask_output=output,
            state=ChatExternalReadonlyBridgeState(
                pending=state.pending,
                ask_session=next_session,
                follow_up_unavailable=state.follow_up_unavailable,
                last_answer=next_snapshot,
            ),
        )

    local_answer = _local_meta_answer_transformation_text(
        snapshot=snapshot,
        question=user_text,
    )
    if local_answer is not None:
        request_root = (
            session.request_id
            if session is not None
            else "chat-answer-transformation://local"
        )
        output = _local_answer_transformation_output(
            request_id=f"{request_root}/answer-transform-{turn_index:03d}",
            question=user_text,
            snapshot=snapshot,
            status="success",
            answer=local_answer,
        )
        next_snapshot = (
            _answer_snapshot_from_output(
                output,
                turn_index=turn_index,
                source_kind="answer_scoped_transformation",
            )
            or snapshot
        )
        return ChatExternalReadonlyBridgeResult(
            handled=True,
            assistant_text=_assistant_text_from_ask_output(output),
            warning_code=CHAT_ANSWER_TRANSFORMATION_WARNING,
            ask_output=output,
            state=ChatExternalReadonlyBridgeState(
                pending=state.pending,
                ask_session=session,
                follow_up_unavailable=state.follow_up_unavailable,
                last_answer=next_snapshot,
            ),
        )
    output = _local_answer_transformation_output(
        request_id=f"chat-answer-transformation://turn-{turn_index:03d}",
        question=user_text,
        snapshot=snapshot,
        status="failed",
        blocking_reasons=("chat_answer_transformation_provider_unavailable",),
    )
    return ChatExternalReadonlyBridgeResult(
        handled=True,
        assistant_text=_assistant_text_from_ask_output(output),
        warning_code=CHAT_ANSWER_TRANSFORMATION_FAILURE,
        ask_output=output,
        state=state,
    )


def _pending_from_user_text(
    args: argparse.Namespace,
    user_text: str,
) -> ChatExternalReadonlyPendingAsk | None:
    source_url, question = _source_url_and_question(user_text)
    if source_url:
        if question:
            stage = "await_model"
        else:
            stage = "await_question"
        return ChatExternalReadonlyPendingAsk(
            stage=stage,
            source_url=source_url,
            evidence_paths=(),
            question=question,
        )
    evidence_paths = tuple(getattr(args, "external_readonly_evidence_paths", ()) or ())
    if evidence_paths and _looks_like_external_readonly_evidence_qa(user_text):
        return ChatExternalReadonlyPendingAsk(
            stage="await_model",
            source_url=None,
            evidence_paths=evidence_paths,
            question=_normalized_text(user_text),
        )
    return None


def _prompt_for_next(
    pending: ChatExternalReadonlyPendingAsk,
    *,
    previous_state: ChatExternalReadonlyBridgeState,
) -> ChatExternalReadonlyBridgeResult:
    return _control_message(
        _prompt_text(pending),
        previous_state=previous_state,
        pending=pending,
    )


def _control_message(
    assistant_text: str,
    *,
    previous_state: ChatExternalReadonlyBridgeState,
    pending: ChatExternalReadonlyPendingAsk | None,
    warning_code: str | None = None,
) -> ChatExternalReadonlyBridgeResult:
    return ChatExternalReadonlyBridgeResult(
        handled=True,
        assistant_text=assistant_text,
        warning_code=warning_code or CHAT_EXTERNAL_READONLY_BRIDGE_PENDING_WARNING,
        state=ChatExternalReadonlyBridgeState(
            pending=pending,
            ask_session=previous_state.ask_session,
            follow_up_unavailable=previous_state.follow_up_unavailable,
            last_answer=previous_state.last_answer,
        ),
    )


def _declined(assistant_text: str) -> ChatExternalReadonlyBridgeResult:
    return ChatExternalReadonlyBridgeResult(
        handled=True,
        assistant_text=assistant_text,
        warning_code=CHAT_EXTERNAL_READONLY_BRIDGE_DECLINED_WARNING,
        state=ChatExternalReadonlyBridgeState(),
    )


def _prompt_text(pending: ChatExternalReadonlyPendingAsk) -> str:
    if pending.stage == "await_question":
        return "已收到外部只读 URL。请单独输入要基于这份资料回答的问题。"
    if pending.stage == "await_model":
        return "请选择模型：1) deepseek  2) gemma4"
    if pending.stage == "await_fetch_confirm":
        return "允许本次外部只读抓取该 URL？ 输入 yes/no"
    if pending.stage == "await_live_llm_confirm":
        return "允许本次受控大模型回答？ 输入 yes/no"
    if pending.stage == "await_provider_confirm":
        return "允许本次外部模型 provider 调用？ 输入 yes/no"
    if pending.stage == "await_deepseek_key_mode":
        return "请选择 DeepSeek key 使用方式：1) 使用已保存  2) 输入 key  3) 取消"
    return "请继续补齐 external-readonly 受控问答所需信息。"


def _ask_args_from_pending(
    chat_args: argparse.Namespace,
    pending: ChatExternalReadonlyPendingAsk,
    *,
    chat_session_id: str,
    turn_index: int,
    deepseek_key_mode: Literal["stored", "prompt"] | None,
) -> argparse.Namespace:
    request_suffix = f"{_safe_ref_part(chat_session_id)}/turn-{turn_index:03d}"
    argv = [
        "external-readonly",
        "ask",
        "--question",
        str(pending.question or ""),
        "--model",
        str(pending.model_alias or "gemma4"),
        "--request-id",
        f"external-readonly-ask-request://chat/{request_suffix}",
        "--envelope-ref",
        f"evidence://external-readonly/envelope/chat-{request_suffix}",
        "--evidence-ref",
        f"evidence://external-readonly/item/chat-{request_suffix}",
        "--controlled-output-ref",
        f"outputs/external-readonly/chat-{request_suffix}.json",
        "--sanitized-evidence-ref",
        f"evidence://external-readonly/chat-{request_suffix}",
        "--governance-summary-ref",
        f"summary://external-readonly/chat-{request_suffix}",
        "--config-root",
        str(chat_args.config_root),
        "--environment",
        str(chat_args.environment),
        "--request-live-llm",
        "--allow-live-llm",
        "--live-llm-approval-ref",
        f"approval://chat-external-readonly/live-llm/{request_suffix}",
        "--answer-preview-limit",
        str(CHAT_RESPONSE_PREVIEW_LIMIT),
    ]
    if getattr(chat_args, "profile", None):
        argv.extend(["--profile", str(chat_args.profile)])
    if pending.source_url:
        argv.extend(
            [
                "--source-url",
                pending.source_url,
                "--confirm-external-readonly-fetch",
                REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION,
                "--operator-approved",
                "--approval-ref",
                f"approval://chat-external-readonly/fetch/{request_suffix}",
                "--runtime-fetch-approval-ref",
                f"approval://chat-external-readonly/runtime-fetch/{request_suffix}",
                "--audit-ref",
                f"audit://chat-external-readonly/{request_suffix}",
                "--network-gate-open",
                "--allow-runtime-fetch",
                "--use-live-transport",
            ]
        )
    else:
        for evidence_path in pending.evidence_paths:
            argv.extend(["--evidence-path", evidence_path])
    if pending.model_alias == "gemma4":
        argv.extend(["--request-ollama", "--allow-ollama"])
        if getattr(chat_args, "ollama_api_base", None):
            argv.extend(["--ollama-api-base", str(chat_args.ollama_api_base)])
    if pending.model_alias == "deepseek":
        argv.extend(
            [
                "--operator-approved",
                "--audit-ref",
                f"audit://chat-external-readonly/provider/{request_suffix}",
                "--network-gate-open",
            ]
        )
        if deepseek_key_mode == "stored":
            argv.append("--use-stored-provider-key")
        elif deepseek_key_mode == "prompt":
            argv.append("--prompt-provider-key")
    if getattr(chat_args, "live_llm_timeout_seconds", None):
        argv.extend(
            [
                "--live-llm-timeout-seconds",
                str(chat_args.live_llm_timeout_seconds),
            ]
        )
    return build_parser().parse_args(argv)


def _source_url_and_question(user_text: str) -> tuple[str | None, str | None]:
    match = _URL_RE.search(user_text)
    if match is None:
        return None, None
    source_url = match.group(0).strip()
    question = (
        user_text[: match.start()] + " " + user_text[match.end() :]
    ).strip()
    question = re.sub(
        r"^(?:url/evidence|evidence\s+path|source|url)\s*[:：]\s*$",
        "",
        question,
        flags=re.IGNORECASE,
    ).strip()
    return source_url, question or None


def _assistant_text_from_ask_output(output: Mapping[str, Any]) -> str:
    answer = output.get("answer")
    if isinstance(answer, str) and answer.strip():
        return " ".join(answer.strip().split())
    failure = output.get("failure_explanation")
    if isinstance(failure, str) and failure.strip():
        return " ".join(failure.strip().split())
    blocking_reasons = output.get("blocking_reasons") or []
    if blocking_reasons:
        return "本轮 external-readonly 问答被治理条件拦截：" + ", ".join(
            map(str, blocking_reasons)
        )
    return "本轮 external-readonly 问答未形成可展示答案。"


def _local_meta_answer_transformation_text(
    *,
    snapshot: ChatExternalReadonlyAnswerSnapshot,
    question: str,
) -> str | None:
    if snapshot.source_kind not in {
        "chat_session_operation_summary",
        "chat_session_experience_suggestions",
        "chat_session_experience_guide",
    }:
        return None
    normalized = "".join(question.strip().split()).lower()
    if not normalized:
        return None
    if any(keyword in normalized for keyword in ("一句话", "一句话总结", "压缩")):
        return (
            "一句话说：当前聊天里大多数体验直接用自然语言继续输入，只有拒绝授权、"
            "空输入、退出和 Ctrl+C 这类边界测试需要重新运行 `uv run cognition chat`。"
        )
    wants_simple_rewrite = any(
        keyword in normalized
        for keyword in (
            "初中生",
            "通俗",
            "简单",
            "易懂",
            "口语",
            "改写",
            "改成",
            "版本",
        )
    )
    if not wants_simple_rewrite:
        return None
    if snapshot.source_kind == "chat_session_operation_summary":
        return (
            "你刚才做了几步测试：先给了一个网页地址，再问它讲了什么，接着让系统翻译、"
            "总结和追问，最后让系统回顾这些操作。这个回顾只记当前这次聊天，不会保存成长期记忆。"
        )
    return (
        "你现在已经在聊天模式里了。想继续试，大多数时候直接输入一句自然语言就行，"
        "比如让它改写上一句、继续追问、总结刚才操作，或者给下一步体验建议。"
        "只有想测试拒绝授权、空输入、退出或 Ctrl+C 这类边界情况时，才需要重新运行 "
        "`uv run cognition chat`。"
    )


def _answer_snapshot_previous_output(
    snapshot: ChatExternalReadonlyAnswerSnapshot,
) -> Mapping[str, Any]:
    return {
        "status": "success",
        "answer": snapshot.answer_text,
        "source_url_present": False,
        "evidence_path_count": 0,
        "evidence_refs": [
            {
                "kind": "source_external_readonly_evidence",
                "ref": ref,
                "purpose": "source_answer_context",
            }
            for ref in snapshot.evidence_refs
        ],
        "additional_refs": [
            {
                "kind": "source_external_readonly_additional_ref",
                "ref": ref,
                "purpose": "source_answer_context",
            }
            for ref in snapshot.additional_refs
        ],
        "readonly_refs_status": "ready",
        "warnings": (),
    }


def _local_answer_transformation_output(
    *,
    request_id: str,
    question: str,
    snapshot: ChatExternalReadonlyAnswerSnapshot,
    status: str,
    answer: str | None = None,
    blocking_reasons: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "status": status,
        "success": status == "success",
        "request_id": request_id,
        "question_preview": _preview_text(question, limit=120),
        "answer": answer,
        "answer_preview": _preview_text(answer, limit=400) if answer else None,
        "answer_scoped_transformation": True,
        "answer_scope": "answer_scoped",
        "readonly_refs_status": "ready",
        "llm_call_attempted": False,
        "llm_runtime_call_performed": False,
        "evidence_refs": _answer_snapshot_previous_output(snapshot)["evidence_refs"],
        "additional_refs": _answer_snapshot_previous_output(snapshot)[
            "additional_refs"
        ],
        "blocking_reasons": list(blocking_reasons),
        "warnings": (
            [CHAT_ANSWER_TRANSFORMATION_WARNING] if status == "success" else []
        ),
        "answer_snapshot_source_turn_index": snapshot.source_turn_index,
        "answer_snapshot_source_kind": snapshot.source_kind,
    }


def _answer_snapshot_from_output(
    output: Mapping[str, Any],
    *,
    turn_index: int,
    source_kind: Literal[
        "external_readonly_ask_answer",
        "external_readonly_follow_up",
        "answer_scoped_transformation",
        "chat_session_operation_summary",
        "chat_session_experience_suggestions",
        "chat_session_experience_guide",
    ],
) -> ChatExternalReadonlyAnswerSnapshot | None:
    if output.get("status") != "success":
        return None
    answer = output.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return None
    return ChatExternalReadonlyAnswerSnapshot(
        answer_text=_normalized_text(answer),
        source_kind=source_kind,
        source_turn_index=turn_index,
        evidence_refs=_ref_values(output.get("evidence_refs")),
        additional_refs=_ref_values(output.get("additional_refs")),
    )


def _ref_values(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        return ()
    refs: list[str] = []
    for item in value:
        if isinstance(item, Mapping):
            ref = item.get("ref")
            if isinstance(ref, str) and ref:
                refs.append(ref)
    return tuple(dict.fromkeys(refs))


def _looks_like_external_readonly_evidence_qa(user_text: str) -> bool:
    normalized = "".join(user_text.strip().split()).lower()
    if not normalized or _looks_like_reference_review_intent(normalized):
        return False
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
            "摘要",
        )
    )
    return has_evidence_target and has_question_intent


def _looks_like_follow_up(user_text: str) -> bool:
    normalized = "".join(user_text.strip().split()).lower()
    if not normalized or _looks_like_reference_review_intent(normalized):
        return False
    if _looks_like_pronoun_follow_up(normalized):
        return True
    return any(
        keyword in normalized
        for keyword in (
            "它",
            "其",
            "该",
            "这个",
            "这份",
            "上述",
            "首页",
            "资料",
            "证据",
            "网页",
            "内容",
            "摘要",
            "翻译",
            "改写",
            "生成",
            "更详细",
            "适合",
            "用途",
        )
    )


def _looks_like_answer_transformation(user_text: str) -> bool:
    normalized = "".join(user_text.strip().split()).lower()
    if not normalized or _looks_like_reference_review_intent(normalized):
        return False
    if re.search(r"[/\\][^\s]+[.](?:md|txt|json|toml|ya?ml)\b", user_text):
        return False
    has_answer_target = any(
        keyword in normalized
        for keyword in (
            "摘要",
            "上面的回答",
            "上述回答",
            "以上答案",
            "以上回答",
            "上一轮",
            "本轮答案",
            "该摘要",
            "这个摘要",
            "我的答案",
            "你的答案",
            "你回复的内容",
            "你给我的答案",
            "摘要内容",
            "答案内容",
            "回复内容",
        )
    )
    if not has_answer_target:
        return False
    return any(
        keyword in normalized
        for keyword in (
            "翻译",
            "英文",
            "english",
            "韩文",
            "korean",
            "排版",
            "格式",
            "三点式",
            "摘要",
            "总结",
            "一句话",
            "压缩",
            "改写",
            "改成",
            "润色",
            "通俗",
            "初中生",
        )
    )


def _looks_like_pronoun_follow_up(normalized: str) -> bool:
    return bool(
        re.match(
            r"^[他她它其](?:适|用|有|是|可|能|应|不|会|需|属|有没有|是否|可否)",
            normalized,
        )
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


def _model_alias(user_text: str) -> Literal["deepseek", "gemma4"] | None:
    normalized = " ".join(user_text.strip().lower().split())
    if normalized in {"1", "deepseek"}:
        return "deepseek"
    if normalized in {"2", "gemma4"}:
        return "gemma4"
    return None


def _deepseek_key_mode(user_text: str) -> Literal["stored", "prompt"] | None:
    normalized = " ".join(user_text.strip().lower().split())
    if normalized in {"1", "stored", "saved", "使用已保存"}:
        return "stored"
    if normalized in {"2", "prompt", "input", "输入", "输入 key", "输入key"}:
        return "prompt"
    return None


def _affirmative(user_text: str) -> bool:
    normalized = " ".join(user_text.strip().lower().split())
    return normalized in {"y", "yes", "true", "1", "同意", "确认", "允许", "好", "好的"}


def _normalized_text(value: str) -> str:
    return " ".join(value.strip().split())


def _preview_text(value: str | None, *, limit: int) -> str | None:
    if value is None:
        return None
    normalized = _normalized_text(value)
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip()


def _safe_ref_part(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "chat"


__all__ = [
    "CHAT_EXTERNAL_READONLY_BRIDGE_DECLINED_WARNING",
    "CHAT_EXTERNAL_READONLY_BRIDGE_PENDING_WARNING",
    "CHAT_EXTERNAL_READONLY_BRIDGE_WARNING",
    "CHAT_ANSWER_TRANSFORMATION_FAILURE",
    "CHAT_ANSWER_TRANSFORMATION_SNAPSHOT_MISSING_WARNING",
    "CHAT_ANSWER_TRANSFORMATION_WARNING",
    "ChatExternalReadonlyAnswerSnapshot",
    "ChatExternalReadonlyBridgeResult",
    "ChatExternalReadonlyFollowUpAskRunner",
    "ChatExternalReadonlyInitialAskRunner",
    "ChatExternalReadonlyBridgeState",
    "ChatExternalReadonlyPendingAsk",
    "build_chat_external_readonly_bridge_turn",
    "chat_external_readonly_ask_text_output",
]
