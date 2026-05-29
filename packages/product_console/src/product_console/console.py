"""Minimal product console renderer.

The console renders product display facts only. It does not call CLI internals,
ProductGateway projections, model routers, providers, or ADK runtime objects.
"""

from __future__ import annotations

import json
import getpass
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from product_application_assembly.evidence_summary_answer_ask_entry import (
    EVIDENCE_SUMMARY_ANSWER_ASK_EXTERNAL_FETCH_DECLINED,
    EVIDENCE_SUMMARY_ANSWER_ASK_LIVE_LLM_DECLINED,
    EVIDENCE_SUMMARY_ANSWER_ASK_QUESTION_REQUIRED,
    EvidenceSummaryAnswerAskEntryRequest,
    EvidenceSummaryAnswerAskEntryServices,
    run_evidence_summary_answer_ask_entry,
    run_evidence_summary_answer_ask_follow_up_entry,
)
from product_application_assembly.evidence_summary_answer_provider_key_setup import (
    EvidenceSummaryAnswerProviderKeyPromptHandlers,
    EvidenceSummaryAnswerProviderKeySetupInput,
    resolve_evidence_summary_answer_provider_key_setup,
)
from product_application_assembly.product_console_display import (
    ProductConsoleHomeDisplay,
    build_product_console_ask_output_display,
    build_product_console_home_display,
    product_console_ask_output_display_dict,
    product_console_home_display_dict,
)


PRODUCT_CONSOLE_ASK_COMMAND = "cognition-console ask"
PRODUCT_CONSOLE_ASK_REQUEST_ID = "external-readonly-ask-request://product-console/ask"
PRODUCT_CONSOLE_EXTERNAL_PROVIDER_DECLINED = (
    "external_readonly_ask_guided_external_provider_declined"
)
PRODUCT_CONSOLE_PROVIDER_KEY_REQUIRED = "deepseek_provider_key_required"
PRODUCT_CONSOLE_PROVIDER_KEY_PROMPT_UNAVAILABLE_FOR_JSON_OUTPUT = (
    "provider_key_prompt_unavailable_for_json_output"
)
PRODUCT_CONSOLE_PROVIDER_KEY_PROMPT_REQUIRES_INTERACTIVE_TERMINAL = (
    "provider_key_prompt_requires_interactive_terminal"
)
PRODUCT_CONSOLE_PROVIDER_KEY_INPUT_REQUIRED = "provider_key_input_required"
PRODUCT_CONSOLE_PROVIDER_KEY_PROMPT_CANCELLED = "provider_key_prompt_cancelled"
PRODUCT_CONSOLE_PROVIDER_KEY_STORED_CREDENTIAL_NOT_FOUND = (
    "provider_key_stored_credential_not_found"
)
PRODUCT_CONSOLE_PROVIDER_KEY_STORED_CREDENTIAL_LOAD_FAILED = (
    "provider_key_stored_credential_load_failed"
)
PRODUCT_CONSOLE_PROVIDER_KEY_PERSISTENT_SAVE_FAILED = (
    "provider_key_persistent_save_failed"
)
PRODUCT_CONSOLE_INPUT_INTERRUPTED = "product_console_input_interrupted"
DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"
ProductConsoleAskRunner = Callable[
    [EvidenceSummaryAnswerAskEntryRequest],
    Any,
]
ProductConsoleAskFollowUpRunner = Callable[..., Any]
ProductConsoleProviderCredentialStoreFactory = Callable[[], Any]
ProductConsoleSessionSaveHandler = Callable[[Mapping[str, Any]], Mapping[str, Any]]
ProductConsoleSessionActionHandler = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def build_product_console_home_payload(
    display: ProductConsoleHomeDisplay | None = None,
) -> dict[str, Any]:
    display = display or build_product_console_home_display()
    return {
        "command": "cognition-console",
        "status": "success",
        "product_console": True,
        "display": product_console_home_display_dict(display),
    }


def render_product_console_home(
    display: ProductConsoleHomeDisplay | None = None,
) -> str:
    payload = build_product_console_home_payload(display)
    display_payload = payload["display"]

    lines = [
        "Cognition System / 认知系统产品控制台",
        "",
        "这里用于查看认知系统当前可用的产品入口、下一步操作和安全边界。",
        "默认首页只展示产品入口；ask 子入口会在明确授权后运行可复查资料问答。",
        "",
        "当前可用产品",
    ]
    for product in display_payload["products"]:
        lines.extend(
            [
                f"- {product['title']}",
                "  用途：基于你授权读取的 URL 或 evidence path 回答问题，"
                "并提供可复查依据。",
                f"  开始使用：{product['entrypoint']}",
                "  当前可做：",
            ]
        )
        for action in product["actions"]:
            lines.append(f"  - {_user_facing_action_line(action)}")
        lines.extend(
            [
                "  复查能力：完成资料问答后，后续控制台视图会组织回答运行、",
                "    证据引用、回答追踪和失败原因等可复查信息。",
            ]
        )

    lines.extend(
        [
            "",
            "安全边界",
            "- 当前入口不会联网、不会调用模型、不会读取或保存模型服务密钥。",
            "- ask 子入口只有在你明确授权后才会读取外部资料或调用受控模型。",
            "- 当前入口不会生成长期记忆、长期任务或工作流运行状态。",
            "- 机器可读产品显示数据请使用：cognition-console --json",
            "",
            "下一步",
            "- 要开始可复查资料问答，请运行：cognition-console ask --guided",
        ]
    )
    return "\n".join(lines)


def run_product_console(
    argv: Sequence[str] | None = None,
    *,
    output_writer: Callable[[str], None] | None = None,
    input_reader: Callable[[str], str] | None = None,
    ask_services: EvidenceSummaryAnswerAskEntryServices | None = None,
    ask_runner: ProductConsoleAskRunner | None = None,
    ask_follow_up_runner: ProductConsoleAskFollowUpRunner | None = None,
    session_save_handler: ProductConsoleSessionSaveHandler | None = None,
    session_action_handler: ProductConsoleSessionActionHandler | None = None,
    provider_credential_store_factory: (
        ProductConsoleProviderCredentialStoreFactory | None
    ) = None,
    provider_key_prompt_handlers: (
        EvidenceSummaryAnswerProviderKeyPromptHandlers | None
    ) = None,
) -> int:
    args = tuple(argv if argv is not None else sys.argv[1:])
    writer = output_writer or print
    reader = input_reader or _read_console_line

    if args[:1] == ("ask",):
        return _run_product_console_ask(
            args[1:],
            writer=writer,
            input_reader=reader,
            ask_services=ask_services,
            ask_runner=ask_runner,
            ask_follow_up_runner=ask_follow_up_runner,
            session_save_handler=session_save_handler,
            provider_credential_store_factory=provider_credential_store_factory,
            provider_key_prompt_handlers=provider_key_prompt_handlers,
        )

    if args[:1] == ("session",):
        return _run_product_console_session(
            args[1:],
            writer=writer,
            session_action_handler=session_action_handler,
        )

    if "--json" in args:
        payload = build_product_console_home_payload()
        writer(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if "--help" in args or "-h" in args:
        writer(render_product_console_help())
        return 0

    writer(render_product_console_home())
    return 0


def render_product_console_help() -> str:
    return "\n".join(
        (
            "用法：cognition-console [--json] [--help]",
            "",
            "认知系统产品控制台，用于查看当前可用产品入口、下一步操作和安全边界。",
            "",
            "不带参数：",
            "  展示用户可读的产品控制台首页。",
            "",
            "--json：",
            "  输出机器可读产品显示数据，供后续界面、自动化测试和研发复查消费。",
            "",
            "--help, -h：",
            "  显示本帮助。",
            "",
            "开始可复查资料问答：",
            "  cognition-console ask --guided",
            "",
            "管理已保存的资料问答会话：",
            "  cognition-console session list --state-root <path>",
            "  cognition-console session resume-preview --state-root <path> --session-id <id>",
            "  cognition-console session delete --state-root <path> --session-id <id> --yes",
            "  cognition-console session expire --state-root <path> --now <iso-time>",
            "",
            "安全边界：",
            "  默认首页不联网、不调用模型、不读取或保存模型服务密钥；",
            "  ask 子入口只有在你明确授权后才会运行可复查资料问答。",
        )
    )


def _user_facing_action_line(action: dict[str, Any]) -> str:
    if action["action_id"] == "start_external_readonly_ask" and action["ref"]:
        return f"{action['label']}：运行 {action['ref']}"
    if action["status"] == "candidate_display_only":
        return f"{action['label']}：后续复查视图继续完善"
    return action["label"]


def _run_product_console_ask(
    args: Sequence[str],
    *,
    writer: Callable[[str], None],
    input_reader: Callable[[str], str],
    ask_services: EvidenceSummaryAnswerAskEntryServices | None,
    ask_runner: ProductConsoleAskRunner | None,
    ask_follow_up_runner: ProductConsoleAskFollowUpRunner | None,
    session_save_handler: ProductConsoleSessionSaveHandler | None,
    provider_credential_store_factory: (
        ProductConsoleProviderCredentialStoreFactory | None
    ),
    provider_key_prompt_handlers: (
        EvidenceSummaryAnswerProviderKeyPromptHandlers | None
    ),
) -> int:
    json_output = "--json" in args
    if "--help" in args or "-h" in args:
        writer(render_product_console_ask_help())
        return 0
    if "--guided" not in args:
        writer(render_product_console_ask_help())
        return 3

    try:
        request = _guided_ask_request(
            input_reader,
            json_output=json_output,
            provider_credential_store_factory=provider_credential_store_factory,
            provider_key_prompt_handlers=provider_key_prompt_handlers,
        )
    except KeyboardInterrupt:
        writer(
            _render_product_console_ask_output(
                _product_console_interrupted_output(),
                json_output=json_output,
            )
        )
        return 130
    except EOFError:
        writer(
            _render_product_console_ask_output(
                _product_console_closed_output(),
                json_output=json_output,
            )
        )
        return 0
    runner = ask_runner or _default_ask_runner(ask_services)
    follow_up_runner = ask_follow_up_runner or _default_ask_follow_up_runner()
    result = runner(request)
    rendered_output = (
        _with_session_save_hint(result.output)
        if json_output and session_save_handler is not None
        else result.output
    )
    writer(_render_product_console_ask_output(rendered_output, json_output=json_output))
    if json_output:
        return int(result.exit_code)
    return _run_product_console_ask_follow_up_loop(
        result,
        writer=writer,
        input_reader=input_reader,
        follow_up_runner=follow_up_runner,
        session_save_handler=session_save_handler,
        json_output=json_output,
    )


def _default_ask_runner(
    ask_services: EvidenceSummaryAnswerAskEntryServices | None,
) -> ProductConsoleAskRunner:
    def _run(request: EvidenceSummaryAnswerAskEntryRequest) -> Any:
        return run_evidence_summary_answer_ask_entry(
            request,
            services=ask_services,
        )

    return _run


def _default_ask_follow_up_runner() -> ProductConsoleAskFollowUpRunner:
    def _run(
        state: Any,
        follow_up_question: str,
        *,
        previous_output: Mapping[str, Any],
        turns: tuple[Mapping[str, Any], ...],
        request_id: str,
        follow_up_index: int,
    ) -> Any:
        return run_evidence_summary_answer_ask_follow_up_entry(
            state,
            follow_up_question,
            previous_output=previous_output,
            turns=turns,
            request_id=request_id,
            follow_up_index=follow_up_index,
        )

    return _run


def _product_console_interrupted_output() -> dict[str, Any]:
    return {
        "request_id": PRODUCT_CONSOLE_ASK_REQUEST_ID,
        "command": PRODUCT_CONSOLE_ASK_COMMAND,
        "status": "interrupted",
        "answer_run_ref": None,
        "answer_run_status": "unavailable",
        "answer_run_unavailable_reason": PRODUCT_CONSOLE_INPUT_INTERRUPTED,
        "blocking_reasons": (PRODUCT_CONSOLE_INPUT_INTERRUPTED,),
        "failure_explanation": "用户中断了本次产品控制台输入，未进入资料抓取或模型回答。",
        "recovery_hints": (
            "如需继续，请重新运行 cognition-console ask --guided。",
        ),
        "follow_up_available": False,
    }


def _product_console_closed_output() -> dict[str, Any]:
    return {
        "request_id": PRODUCT_CONSOLE_ASK_REQUEST_ID,
        "command": PRODUCT_CONSOLE_ASK_COMMAND,
        "status": "closed",
        "answer_run_ref": None,
        "answer_run_status": "unavailable",
        "answer_run_unavailable_reason": "product_console_input_closed",
        "blocking_reasons": ("product_console_input_closed",),
        "failure_explanation": "输入已结束，未进入资料抓取或模型回答。",
        "recovery_hints": (
            "如需继续，请重新运行 cognition-console ask --guided。",
        ),
        "follow_up_available": False,
    }


def _run_product_console_session(
    args: Sequence[str],
    *,
    writer: Callable[[str], None],
    session_action_handler: ProductConsoleSessionActionHandler | None,
) -> int:
    json_output = "--json" in args
    if "--help" in args or "-h" in args or not args:
        writer(render_product_console_session_help())
        return 0
    if session_action_handler is None:
        writer(
            _render_product_console_session_result(
                {
                    "status": "unavailable",
                    "reason": "session_action_handler_unavailable",
                    "recovery_hints": (
                        "请通过安装态 cognition-console 入口使用 session 子命令。",
                    ),
                },
                json_output=json_output,
            )
        )
        return 3
    action = args[0]
    request = {
        "action": action,
        "state_root": _option_value(args, "--state-root"),
        "session_id": _option_value(args, "--session-id"),
        "now": _option_value(args, "--now"),
        "confirmed": "--yes" in args,
        "json_output": json_output,
    }
    if action == "delete" and not request["confirmed"]:
        writer(
            _render_product_console_session_result(
                {
                    "status": "confirmation_required",
                    "action": "delete",
                    "session_id": request["session_id"],
                    "recovery_hints": ("如确认删除，请追加 --yes。",),
                },
                json_output=json_output,
            )
        )
        return 3
    try:
        result = session_action_handler(request)
    except Exception as exc:  # pragma: no cover - defensive product boundary.
        result = {
            "status": "failed",
            "action": action,
            "reason": "session_action_failed",
            "message": str(exc),
        }
    writer(_render_product_console_session_result(result, json_output=json_output))
    return 0 if result.get("status") == "success" else 3


def _run_product_console_ask_follow_up_loop(
    initial_result: Any,
    *,
    writer: Callable[[str], None],
    input_reader: Callable[[str], str],
    follow_up_runner: ProductConsoleAskFollowUpRunner,
    session_save_handler: ProductConsoleSessionSaveHandler | None,
    json_output: bool,
) -> int:
    output = _mapping(initial_result.output)
    exit_code = int(initial_result.exit_code)
    state = getattr(initial_result, "next_state", None)
    if not _product_console_follow_up_available(output, state):
        return _maybe_save_product_console_session(
            output,
            writer=writer,
            input_reader=input_reader,
            session_save_handler=session_save_handler,
            turns=(_product_console_session_turn_summary(output, turn_index=1),),
            exit_code=exit_code,
        )

    writer(_product_console_follow_up_scope_hint())
    turns: list[Mapping[str, Any]] = [
        _product_console_turn_summary(output, turn_index=1)
    ]
    session_turns: list[Mapping[str, Any]] = [
        _product_console_session_turn_summary(output, turn_index=1)
    ]
    previous_output = output
    request_id = str(previous_output.get("request_id") or PRODUCT_CONSOLE_ASK_REQUEST_ID)
    follow_up_index = 0
    while _product_console_follow_up_available(previous_output, state):
        try:
            raw_decision = input_reader(
                "继续追问或变换上一轮答案；直接输入问题，或输入 no 结束: "
            )
        except KeyboardInterrupt:
            writer("session: interrupted")
            return 130
        except EOFError:
            writer("session: closed")
            return 0

        decision = raw_decision.strip()
        if not decision:
            writer("请输入追问问题，或输入 no 结束。")
            continue
        if _product_console_follow_up_exit_requested(decision):
            return _maybe_save_product_console_session(
                previous_output,
                writer=writer,
                input_reader=input_reader,
                session_save_handler=session_save_handler,
                turns=tuple(session_turns),
                exit_code=0,
            )

        follow_up_index += 1
        result = follow_up_runner(
            state,
            decision,
            previous_output=previous_output,
            turns=tuple(turns),
            request_id=request_id,
            follow_up_index=follow_up_index,
        )
        output = _mapping(result.output)
        writer("")
        writer(_render_product_console_ask_output(output, json_output=json_output))
        exit_code = int(result.exit_code)
        state = getattr(result, "next_state", state)
        previous_output = output
        turns.append(
            _product_console_turn_summary(
                output,
                turn_index=len(turns) + 1,
            )
        )
        session_turns.append(
            _product_console_session_turn_summary(
                output,
                turn_index=len(session_turns) + 1,
            )
        )
        if output.get("status") != "success":
            return exit_code

    return _maybe_save_product_console_session(
        previous_output,
        writer=writer,
        input_reader=input_reader,
        session_save_handler=session_save_handler,
        turns=tuple(session_turns),
        exit_code=exit_code,
    )


def _product_console_follow_up_available(
    output: Mapping[str, Any],
    state: Any,
) -> bool:
    return (
        state is not None
        and output.get("status") == "success"
        and output.get("follow_up_available") is True
    )


def _product_console_follow_up_scope_hint() -> str:
    return (
        "提示：追问和答案变换仅在当前进程内有效；"
        "不启用长期 Memory、持久 Session 或 durable workflow。"
    )


def _product_console_follow_up_exit_requested(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in {
        "no",
        "n",
        "取消",
        "不用",
        "不追问",
        "结束",
        "退出",
        "exit",
        "/exit",
    }


def _product_console_turn_summary(
    output: Mapping[str, Any],
    *,
    turn_index: int,
) -> Mapping[str, Any]:
    return {
        "turn_index": turn_index,
        "request_id": output.get("request_id"),
        "status": output.get("status"),
        "follow_up": output.get("follow_up") is True,
        "follow_up_turn_index": output.get("follow_up_turn_index"),
        "question_preview": output.get("question_preview"),
        "answer": output.get("answer"),
        "runtime_visible_summary": _product_console_runtime_visible_summary(output),
        "evidence_refs": output.get("evidence_refs") or [],
        "additional_refs": output.get("additional_refs") or [],
    }


def _product_console_session_turn_summary(
    output: Mapping[str, Any],
    *,
    turn_index: int,
) -> Mapping[str, Any]:
    return {
        "turn_index": turn_index,
        "request_id": output.get("request_id"),
        "status": output.get("status"),
        "follow_up": output.get("follow_up") is True,
        "answer_scoped_transformation": output.get("answer_scoped_transformation")
        is True,
        "question_preview": _safe_preview(output.get("question_preview"), limit=160),
        "answer_preview": _safe_preview(output.get("answer"), limit=220),
        "answer_run_ref": output.get("answer_run_ref"),
        "answer_trace_ref": output.get("answer_trace_ref"),
        "answer_artifact_ref": output.get("answer_artifact_ref"),
        "observability_summary_ref": output.get("observability_summary_ref"),
        "trace_inspect_ref": output.get("trace_inspect_ref"),
        "runtime_visible_summary": _product_console_runtime_visible_summary(output),
        "evidence_refs": output.get("evidence_refs") or [],
        "additional_refs": output.get("additional_refs") or [],
    }


def _maybe_save_product_console_session(
    output: Mapping[str, Any],
    *,
    writer: Callable[[str], None],
    input_reader: Callable[[str], str],
    session_save_handler: ProductConsoleSessionSaveHandler | None,
    turns: tuple[Mapping[str, Any], ...],
    exit_code: int,
) -> int:
    if (
        session_save_handler is None
        or exit_code != 0
        or output.get("status") != "success"
    ):
        return exit_code
    try:
        save_choice = _read_session_save_choice(
            input_reader=input_reader,
            writer=writer,
        )
        if save_choice is None:
            writer("session_save: skipped")
            return exit_code
        save_mode, prompt_selected_state_root = save_choice
        _write_session_save_boundary(writer)
    except KeyboardInterrupt:
        writer("session_save: interrupted")
        return 130
    except EOFError:
        writer("session_save: closed")
        return exit_code
    try:
        result = session_save_handler(
            {
                "action": "save",
                "save_mode": save_mode,
                "prompt_selected_state_root": prompt_selected_state_root,
                "output": _product_console_session_output_summary(output),
                "turns": turns,
            }
        )
    except Exception as exc:  # pragma: no cover - defensive product boundary.
        result = {
            "status": "failed",
            "reason": "session_save_failed",
            "message": str(exc),
        }
    writer(_render_product_console_session_result(result, json_output=False))
    return exit_code


def _product_console_session_output_summary(
    output: Mapping[str, Any],
) -> Mapping[str, Any]:
    return {
        "request_id": output.get("request_id"),
        "status": output.get("status"),
        "question_preview": _safe_preview(output.get("question_preview"), limit=160),
        "answer_preview": _safe_preview(output.get("answer"), limit=220),
        "answer_run_ref": output.get("answer_run_ref"),
        "answer_trace_ref": output.get("answer_trace_ref"),
        "answer_artifact_ref": output.get("answer_artifact_ref"),
        "observability_summary_ref": output.get("observability_summary_ref"),
        "trace_inspect_ref": output.get("trace_inspect_ref"),
        "runtime_visible_summary": _product_console_runtime_visible_summary(output),
        "evidence_refs": output.get("evidence_refs") or [],
        "additional_refs": output.get("additional_refs") or [],
    }


def _with_session_save_hint(output: Any) -> Mapping[str, Any]:
    data = dict(_mapping(output))
    data["session_save_available"] = data.get("status") == "success"
    if data["session_save_available"]:
        data["session_save_hint"] = (
            "text 模式可在本轮成功后显式保存到默认本地状态目录或另选目录；"
            "JSON 模式不进入保存交互。"
        )
        data["session_save_default_local_state_dir_available"] = True
        data["session_save_next_actions"] = (
            "text_save_default",
            "text_save_other_state_root",
            "text_do_not_save",
        )
    return data


def render_product_console_session_help() -> str:
    return "\n".join(
        (
            "用法：cognition-console session <action> [options]",
            "",
            "管理已保存的可继续资料问答会话。默认读取本地状态目录；",
            "也可以通过 --state-root 指定其他目录。",
            "",
            "可用 action：",
            "  list [--state-root <path>]",
            "  resume-preview --session-id <id> [--state-root <path>]",
            "  delete --session-id <id> --yes [--state-root <path>]",
            "  expire --now <iso-time> [--state-root <path>]",
            "",
            "安全边界：",
            "  本入口只展示 refs 与安全摘要；不重新读取资料、不调用模型、",
            "  不恢复 ADK Session、不启用 Memory。",
        )
    )


def _render_product_console_session_result(
    result: Mapping[str, Any],
    *,
    json_output: bool,
) -> str:
    if json_output:
        return json.dumps(dict(result), ensure_ascii=False, indent=2, sort_keys=True)
    lines = [
        "Cognition System / 认知系统产品控制台",
        "product: 可继续资料问答会话",
        f"status: {result.get('status') or 'unknown'}",
    ]
    for field_name in (
        "action",
        "session_id",
        "continuable_evidence_session_ref",
        "state_root",
        "state_root_source",
        "deleted",
        "remaining_index_count",
        "reason",
        "message",
    ):
        if field_name in result:
            value = result.get(field_name)
            lines.append(f"{field_name}: {value}")
    expired_session_ids = result.get("expired_session_ids")
    if isinstance(expired_session_ids, list | tuple) and expired_session_ids:
        lines.append("expired_session_ids:")
        for session_id in expired_session_ids:
            lines.append(f"- {session_id}")
    entries = result.get("entries")
    if isinstance(entries, list):
        lines.append("entries:")
        for entry in entries:
            if isinstance(entry, Mapping):
                lines.append(
                    "- "
                    + ", ".join(
                        str(part)
                        for part in (
                            entry.get("session_id"),
                            entry.get("session_status"),
                            entry.get("latest_resume_summary_preview"),
                        )
                        if part
                    )
                )
    preview = result.get("resume_preview")
    if isinstance(preview, Mapping):
        lines.append("resume_preview:")
        for key in (
            "session_id",
            "record_status",
            "session_status",
            "updated_at",
            "expires_at",
            "latest_resume_summary_preview",
            "source_scope_summary",
            "requires_external_readonly_authorization",
            "requires_model_authorization",
        ):
            if key in preview:
                lines.append(f"- {key}: {preview[key]}")
        runtime_summary = preview.get("runtime_summary")
        if isinstance(runtime_summary, Mapping):
            lines.extend(_runtime_summary_text_lines(runtime_summary, prefix="- "))
    hints = result.get("recovery_hints")
    if isinstance(hints, list | tuple) and hints:
        lines.append("recovery_hints:")
        for hint in hints:
            lines.append(f"- {hint}")
    return "\n".join(lines)


def _read_session_save_choice(
    *,
    input_reader: Callable[[str], str],
    writer: Callable[[str], None],
) -> tuple[str, str | None] | None:
    while True:
        choice = input_reader(
            "是否保存此会话以便下次继续？"
            " 1=保存到默认本地状态目录 / 2=选择其他目录 / "
            "3=不保存 / 4=查看将保存什么: "
        ).strip().lower()
        if choice in {"", "1", "y", "yes", "是", "同意", "默认"}:
            return ("default_local_state_root", None)
        if choice in {"2", "other", "其他", "另选"}:
            state_root = _read_required(input_reader, "请输入 session state root 路径: ")
            return ("prompt_selected_state_root", state_root)
        if choice in {"3", "n", "no", "否", "不保存"}:
            return None
        if choice in {"4", "view", "查看"}:
            _write_session_save_boundary(writer)
            continue
        writer("session_save: unknown_choice")


def _write_session_save_boundary(writer: Callable[[str], None]) -> None:
    writer(
        "session_save_boundary: 仅保存 refs 与安全摘要；不保存 raw evidence、"
        "raw prompt、raw provider response、完整答案、secret 或 config context；"
        "不启用 Memory，不创建 ADK Session。"
    )


def _option_value(args: Sequence[str], option_name: str) -> str | None:
    for index, value in enumerate(args):
        if value == option_name and index + 1 < len(args):
            return args[index + 1]
        prefix = f"{option_name}="
        if value.startswith(prefix):
            return value[len(prefix) :]
    return None


def _safe_preview(value: Any, *, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    normalized = text.replace("\n", " ")
    return normalized[:limit]


def _product_console_runtime_visible_summary(
    output: Mapping[str, Any],
) -> Mapping[str, Any]:
    direct = _mapping(output.get("runtime_visible_summary"))
    if direct:
        return direct
    review = _mapping(output.get("review"))
    runtime = _mapping(review.get("runtime"))
    if runtime:
        return {
            "runtime_summary_ref": runtime.get("runtime_summary_ref"),
            "runtime_availability_hint": runtime.get("availability_hint"),
            "runtime_trajectory_summary": runtime.get("trajectory_summary"),
            "runtime_artifact_index": runtime.get("artifact_index"),
            "runtime_evaluation_summary": runtime.get("evaluation_summary"),
        }
    if any(
        key in output
        for key in (
            "runtime_summary_ref",
            "runtime_availability_hint",
            "runtime_trajectory_summary",
            "runtime_artifact_index",
            "runtime_evaluation_summary",
        )
    ):
        return {
            "runtime_summary_ref": output.get("runtime_summary_ref"),
            "runtime_availability_hint": output.get("runtime_availability_hint"),
            "runtime_trajectory_summary": output.get("runtime_trajectory_summary"),
            "runtime_artifact_index": output.get("runtime_artifact_index"),
            "runtime_evaluation_summary": output.get("runtime_evaluation_summary"),
        }
    return {}


def _runtime_review_has_visible_facts(runtime: Any) -> bool:
    return any(
        (
            getattr(runtime, "runtime_summary_ref", None),
            getattr(runtime, "availability_hint", None),
            getattr(runtime, "trajectory_summary", None),
            getattr(runtime, "artifact_index", None),
            getattr(runtime, "evaluation_summary", None),
        )
    )


def _runtime_review_text_lines(runtime: Any) -> list[str]:
    availability = _mapping(getattr(runtime, "availability_hint", None))
    evaluation = _mapping(getattr(runtime, "evaluation_summary", None))
    lines = ["", "runtime_summary:"]
    if getattr(runtime, "runtime_summary_ref", None):
        lines.append(f"- runtime_summary_ref: {runtime.runtime_summary_ref}")
    if availability.get("runtime_binding_status"):
        lines.append(
            f"- runtime_binding_status: {availability['runtime_binding_status']}"
        )
    if availability.get("hint"):
        lines.append(f"- availability_hint: {availability['hint']}")
    if evaluation.get("evaluation_status"):
        lines.append(f"- evaluation_status: {evaluation['evaluation_status']}")
    if evaluation.get("evaluation_summary_ref"):
        lines.append(
            f"- evaluation_summary_ref: {evaluation['evaluation_summary_ref']}"
        )
    artifact_refs = tuple(
        item.get("ref")
        for item in _mapping_tuple(getattr(runtime, "artifact_index", None))
        if item.get("ref")
    )
    if artifact_refs:
        lines.append("- artifact_refs:")
        for ref in artifact_refs:
            lines.append(f"  - {ref}")
    lines.extend(
        (
            "- boundary: 仅展示 runtime 安全摘要；不执行 ADK runtime。",
            "- boundary: 不自动恢复回答、不调用模型、不重放 Workflow。",
        )
    )
    return lines


def _runtime_summary_text_lines(
    runtime_summary: Mapping[str, Any],
    *,
    prefix: str,
) -> list[str]:
    lines = [f"{prefix}runtime_summary:"]
    for key in (
        "has_runtime_visible_summary",
        "runtime_visible_summary_ref",
        "runtime_binding_status",
        "runtime_availability_hint",
        "evaluation_status",
        "evaluation_summary_ref",
        "user_product_runtime_path_enabled",
        "auto_resume_answer_enabled",
        "workflow_replay_enabled",
    ):
        if key in runtime_summary:
            lines.append(f"{prefix}  {key}: {runtime_summary[key]}")
    artifact_refs = runtime_summary.get("artifact_refs")
    if isinstance(artifact_refs, list | tuple) and artifact_refs:
        lines.append(f"{prefix}  artifact_refs:")
        for ref in artifact_refs:
            lines.append(f"{prefix}    - {ref}")
    boundary_hints = runtime_summary.get("boundary_hints")
    if isinstance(boundary_hints, list | tuple) and boundary_hints:
        lines.append(f"{prefix}  boundary_hints:")
        for hint in boundary_hints:
            lines.append(f"{prefix}    - {hint}")
    return lines


def _mapping_tuple(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _guided_ask_request(
    input_reader: Callable[[str], str],
    *,
    json_output: bool,
    provider_credential_store_factory: (
        ProductConsoleProviderCredentialStoreFactory | None
    ),
    provider_key_prompt_handlers: (
        EvidenceSummaryAnswerProviderKeyPromptHandlers | None
    ),
) -> EvidenceSummaryAnswerAskEntryRequest:
    source_value = _read_required(input_reader, "请输入 URL 或 evidence path: ")
    question = _read_required(input_reader, "请输入问题: ")
    model_alias = _normalize_model_alias(
        input_reader(
            "请选择模型：1) deepseek  2) gemma4\n"
            "请输入 1、2、deepseek 或 gemma4: "
        )
    )
    source_url = source_value if _looks_like_url(source_value) else None
    evidence_paths = () if source_url else (source_value,)
    allow_fetch = True
    fetch_confirmation = None
    if source_url:
        allow_fetch = _read_yes(
            input_reader,
            "允许本次外部只读抓取该 URL？ 输入 yes/no: ",
        )
        fetch_confirmation = "同意外部只读抓取" if allow_fetch else None
    allow_llm = _read_yes(
        input_reader,
        "允许本次受控大模型回答？ 输入 yes/no: ",
    )

    channel_blocking_reasons: list[str] = []
    if not question:
        channel_blocking_reasons.append(EVIDENCE_SUMMARY_ANSWER_ASK_QUESTION_REQUIRED)
    if source_url and not allow_fetch:
        channel_blocking_reasons.append(
            EVIDENCE_SUMMARY_ANSWER_ASK_EXTERNAL_FETCH_DECLINED
        )
    if not allow_llm:
        channel_blocking_reasons.append(EVIDENCE_SUMMARY_ANSWER_ASK_LIVE_LLM_DECLINED)
    provider_key = None
    provider_key_metadata: Mapping[str, Any] = {}
    if model_alias == "deepseek" and not channel_blocking_reasons:
        if not _read_yes(
            input_reader,
            "允许本次外部模型 provider 调用？ 输入 yes/no: ",
        ):
            channel_blocking_reasons.append(PRODUCT_CONSOLE_EXTERNAL_PROVIDER_DECLINED)
        else:
            environment_key_present = bool(os.getenv(DEEPSEEK_API_KEY_ENV))
            key_mode = (
                "environment"
                if environment_key_present
                else _read_deepseek_provider_key_mode(input_reader)
            )
            if key_mode == "cancel":
                channel_blocking_reasons.append(
                    PRODUCT_CONSOLE_PROVIDER_KEY_PROMPT_CANCELLED
                )
            elif key_mode is None:
                channel_blocking_reasons.append(
                    PRODUCT_CONSOLE_PROVIDER_KEY_INPUT_REQUIRED
                )
            else:
                setup_result = resolve_evidence_summary_answer_provider_key_setup(
                    EvidenceSummaryAnswerProviderKeySetupInput(
                        provider_selected=True,
                        environment_key_present=environment_key_present,
                        use_stored_provider_key=key_mode == "stored",
                        prompt_provider_key=key_mode == "prompt",
                        json_output=json_output,
                        prompt_available=_provider_key_prompt_available(
                            provider_key_prompt_handlers
                        ),
                    ),
                    prompt_handlers=(
                        provider_key_prompt_handlers
                        or _default_provider_key_prompt_handlers()
                    ),
                    credential_store_factory=provider_credential_store_factory,
                    provider_key_required_reason=(
                        PRODUCT_CONSOLE_PROVIDER_KEY_REQUIRED
                    ),
                    prompt_unavailable_for_json_reason=(
                        PRODUCT_CONSOLE_PROVIDER_KEY_PROMPT_UNAVAILABLE_FOR_JSON_OUTPUT
                    ),
                    prompt_requires_terminal_reason=(
                        PRODUCT_CONSOLE_PROVIDER_KEY_PROMPT_REQUIRES_INTERACTIVE_TERMINAL
                    ),
                    input_required_reason=PRODUCT_CONSOLE_PROVIDER_KEY_INPUT_REQUIRED,
                    prompt_cancelled_reason=PRODUCT_CONSOLE_PROVIDER_KEY_PROMPT_CANCELLED,
                    stored_not_found_reason=(
                        PRODUCT_CONSOLE_PROVIDER_KEY_STORED_CREDENTIAL_NOT_FOUND
                    ),
                    stored_load_failed_reason=(
                        PRODUCT_CONSOLE_PROVIDER_KEY_STORED_CREDENTIAL_LOAD_FAILED
                    ),
                    persistent_save_failed_reason=(
                        PRODUCT_CONSOLE_PROVIDER_KEY_PERSISTENT_SAVE_FAILED
                    ),
                )
                provider_key = setup_result.provider_key
                provider_key_metadata = setup_result.metadata
                channel_blocking_reasons.extend(setup_result.blocking_reasons)

    return EvidenceSummaryAnswerAskEntryRequest(
        request_id=PRODUCT_CONSOLE_ASK_REQUEST_ID,
        source_url=source_url,
        evidence_paths=evidence_paths,
        question=question,
        command=PRODUCT_CONSOLE_ASK_COMMAND,
        input_channel="product_console",
        source="product_console.console",
        model_alias=model_alias,
        request_live_llm=allow_llm,
        allow_live_llm=allow_llm,
        request_ollama=model_alias == "gemma4",
        allow_ollama=allow_llm and model_alias == "gemma4",
        live_llm_approval_ref=(
            "operator-approval://product-console/live-llm"
            if allow_llm
            else None
        ),
        network_gate_open=allow_fetch,
        operator_approved=allow_fetch,
        approval_ref=(
            "operator-approval://product-console/external-readonly-fetch"
            if allow_fetch
            else None
        ),
        runtime_fetch_approval_ref=(
            "runtime-fetch-approval://product-console/external-readonly-fetch"
            if allow_fetch
            else None
        ),
        audit_ref=(
            "audit://product-console/external-readonly-ask" if allow_fetch else None
        ),
        allow_runtime_fetch=allow_fetch,
        use_live_transport=allow_fetch,
        confirm_external_readonly_fetch=fetch_confirmation,
        provider_key=provider_key,
        provider_key_metadata=provider_key_metadata,
        channel_blocking_reasons=tuple(channel_blocking_reasons),
        metadata={"product_console_ask": True},
    )


def render_product_console_ask_help() -> str:
    return "\n".join(
        (
            "用法：cognition-console ask --guided",
            "",
            "在产品控制台中启动可复查资料问答。",
            "",
            "本入口会采集资料、问题、模型选择和授权确认，然后调用 ask 产品入口服务。",
            "它不调用 CLI wrapper，不解析 CLI 输出，也不保存长期会话。",
        )
    )


def render_product_console_ask_output(output: Mapping[str, Any]) -> str:
    display = build_product_console_ask_output_display(
        output,
        command=PRODUCT_CONSOLE_ASK_COMMAND,
    )
    lines = [
        "Cognition System / 认知系统产品控制台",
        f"product: {display.product_title}",
        f"command: {display.command}",
        f"status: {display.status}",
    ]
    if display.review.answer_run_ref:
        lines.append(f"answer_run_ref: {display.review.answer_run_ref}")
        lines.append(f"answer_run_status: {display.review.status}")
        if display.review.detail_available:
            lines.append(
                "details: 使用 --json 查看 trace / artifact / "
                "observability / inspect 详情。"
            )
    else:
        lines.append(f"review: {display.review.explanation}")
    if _runtime_review_has_visible_facts(display.review.runtime):
        lines.extend(_runtime_review_text_lines(display.review.runtime))
    if display.blocking_reasons:
        lines.append("blocking_reasons: " + ", ".join(display.blocking_reasons))
    if display.failure_explanation:
        lines.append(f"failure_explanation: {display.failure_explanation}")
    if display.recovery_hints:
        lines.append("recovery_hints:")
        for hint in display.recovery_hints:
            lines.append(f"- {hint}")
    if display.answer:
        lines.extend(["", "answer:", display.answer])
    elif display.status == "success":
        lines.extend(["", "answer:", "本轮未形成可展示答案。"])
    if display.follow_up_text:
        lines.append("")
        lines.append(f"follow_up: {display.follow_up_text}")
    return "\n".join(lines)


def render_product_console_ask_output_json(output: Mapping[str, Any]) -> str:
    display = build_product_console_ask_output_display(
        output,
        command=PRODUCT_CONSOLE_ASK_COMMAND,
    )
    payload = product_console_ask_output_display_dict(display)
    if "session_save_available" in output:
        payload["session_save_available"] = bool(output.get("session_save_available"))
    if output.get("session_save_hint"):
        payload["session_save_hint"] = output["session_save_hint"]
    if "session_save_default_local_state_dir_available" in output:
        payload["session_save_default_local_state_dir_available"] = bool(
            output.get("session_save_default_local_state_dir_available")
        )
    if output.get("session_save_next_actions"):
        payload["session_save_next_actions"] = list(
            output["session_save_next_actions"]
        )
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _render_product_console_ask_output(
    output: Mapping[str, Any],
    *,
    json_output: bool,
) -> str:
    if json_output:
        return render_product_console_ask_output_json(output)
    return render_product_console_ask_output(output)


def _read_required(
    input_reader: Callable[[str], str],
    prompt: str,
) -> str:
    return input_reader(prompt).strip()


def _read_yes(
    input_reader: Callable[[str], str],
    prompt: str,
) -> bool:
    return input_reader(prompt).strip().lower() in {"y", "yes", "1", "是", "同意"}


def _read_console_line(prompt: str) -> str:
    print(prompt, end="", file=sys.stderr, flush=True)
    raw_value = sys.stdin.readline()
    if raw_value == "":
        raise EOFError
    return raw_value.rstrip("\n")


def _read_deepseek_provider_key_mode(
    input_reader: Callable[[str], str],
) -> str | None:
    choice = input_reader(
        "请选择 DeepSeek key 使用方式：1) 使用已保存  2) 输入 key  3) 取消\n"
        "请输入 1、2 或 3: "
    )
    normalized = choice.strip().lower()
    if normalized in {"1", "stored", "saved", "use-stored", "使用已保存"}:
        return "stored"
    if normalized in {"2", "prompt", "input", "输入", "输入key", "输入 key"}:
        return "prompt"
    if normalized in {"3", "cancel", "取消"}:
        return "cancel"
    return None


def _provider_key_prompt_available(
    prompt_handlers: EvidenceSummaryAnswerProviderKeyPromptHandlers | None,
) -> bool:
    if prompt_handlers is not None:
        return True
    if os.getenv("CI"):
        return False
    return sys.stdin.isatty() and sys.stderr.isatty()


def _default_provider_key_prompt_handlers(
) -> EvidenceSummaryAnswerProviderKeyPromptHandlers:
    return EvidenceSummaryAnswerProviderKeyPromptHandlers(
        read_secret=_read_provider_key_secret,
        read_persistence_choice=_read_provider_key_persistence_choice,
    )


def _read_provider_key_secret() -> str | None:
    try:
        return getpass.getpass("请输入 DeepSeek API key: ", stream=sys.stderr)
    except (EOFError, KeyboardInterrupt):
        return None


def _read_provider_key_persistence_choice() -> str:
    print(
        "请选择 DeepSeek key 使用方式：1) 仅本次使用  2) 长期保存  3) 取消",
        file=sys.stderr,
    )
    print("请输入 1、2 或 3：", end="", file=sys.stderr, flush=True)
    try:
        raw_choice = sys.stdin.readline()
    except KeyboardInterrupt:
        return "cancel"
    normalized = raw_choice.strip().lower()
    if normalized in {"1", "once", "one-time", "本次", "仅本次", "仅本次使用"}:
        return "once"
    if normalized in {"2", "store", "save", "persist", "长期", "长期保存"}:
        return "store"
    return "cancel"


def _normalize_model_alias(raw_value: str) -> str:
    value = raw_value.strip().lower()
    if value in {"1", "deepseek"}:
        return "deepseek"
    if value in {"2", "gemma4", "gemma"}:
        return "gemma4"
    return value


def _looks_like_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = (
    "build_product_console_home_payload",
    "render_product_console_ask_help",
    "render_product_console_ask_output",
    "render_product_console_ask_output_json",
    "render_product_console_home",
    "render_product_console_help",
    "run_product_console",
)
