"""Chat command channel for the Cognition System CLI."""

from __future__ import annotations

import argparse
import sys
import uuid

from cognition_cli.constants import (
    EXIT_OK,
    EXIT_USAGE_ERROR,
)
from cognition_cli.services.runtime import (
    EntryRunner,
    RequestBuilder,
    RunGatewayExecutor,
    TwfLlmInvocationServiceFactory,
)
from cognition_cli.chat.output import (
    _chat_banner,
    _chat_help_text,
)
from cognition_cli.chat.controls import (
    _chat_plan_manual_control_missing_governance,
    _chat_plan_manual_controls_requested,
    _chat_plan_runtime_config_context,
)
from cognition_cli.chat.status_artifacts import _persist_chat_status_summary
from cognition_cli.chat.status_presenter import (
    _chat_status_command,
    _chat_status_json_command,
    _chat_status_json_text,
    _chat_status_text,
)
from cognition_cli.chat.references import (
    clear_reference_paths,
    reference_list_text,
)
from cognition_cli.chat.task_dispatch import (
    _dispatch_chat_input_turn,
)


def _chat_command(
    args: argparse.Namespace,
    *,
    entry_runner: EntryRunner | None,
    request_builder: RequestBuilder | None,
    use_gateway_entry: bool = False,
    run_gateway_executor: RunGatewayExecutor | None = None,
    twf_llm_invocation_service_factory: (
        TwfLlmInvocationServiceFactory | None
    ) = None,
) -> int:
    usage_error = _chat_usage_error(args)
    if usage_error is not None:
        print(f"cognition chat error: {usage_error}", file=sys.stderr)
        return EXIT_USAGE_ERROR

    chat_session_id = _chat_session_id(args)
    if not args.no_banner:
        print(_chat_banner(chat_session_id))

    history: list[dict[str, str]] = []
    latest_plan_display_text: str | None = None
    latest_plan_snapshot = None
    pending_reference_path_add = None
    turn_index = 0
    try:
        while args.max_turns is None or turn_index < args.max_turns:
            if sys.stdin.isatty():
                print("user> ", end="", flush=True)
            raw_line = sys.stdin.readline()
            if raw_line == "":
                break
            line = raw_line.strip()
            if not line:
                continue
            if line == "/exit":
                print("session: closed")
                return EXIT_OK
            if line == "/help":
                print(_chat_help_text())
                continue
            if line == "/reference list":
                print(reference_list_text(args))
                continue
            if line == "/reference clear":
                clear_reference_paths(args)
                pending_reference_path_add = None
                print("已清空当前会话的受控资料文件和外部只读证据。")
                continue
            if _chat_status_command(line):
                latest_plan_snapshot, status_summary_artifact_ref = (
                    _persist_chat_status_summary(
                        args,
                        chat_session_id,
                        turn_index,
                        latest_plan_snapshot=latest_plan_snapshot,
                    )
                )
                if _chat_status_json_command(line):
                    print(
                        _chat_status_json_text(
                            args,
                            chat_session_id,
                            turn_index,
                            latest_plan_snapshot=latest_plan_snapshot,
                            status_summary_artifact_ref=status_summary_artifact_ref,
                        )
                    )
                    continue
                print(
                    _chat_status_text(
                        args,
                        chat_session_id,
                        turn_index,
                        latest_plan_snapshot=latest_plan_snapshot,
                        status_summary_artifact_ref=status_summary_artifact_ref,
                    )
                )
                continue

            turn_index += 1
            turn_result = _dispatch_chat_input_turn(
                args=args,
                user_text=line,
                chat_session_id=chat_session_id,
                turn_index=turn_index,
                history=history,
                entry_runner=entry_runner,
                request_builder=request_builder,
                use_gateway_entry=use_gateway_entry,
                run_gateway_executor=run_gateway_executor,
                twf_llm_invocation_service_factory=(
                    twf_llm_invocation_service_factory
                ),
                latest_plan_display_text=latest_plan_display_text,
                latest_plan_snapshot=latest_plan_snapshot,
                pending_reference_path_add=pending_reference_path_add,
            )
            latest_plan_display_text = turn_result.latest_plan_display_text
            latest_plan_snapshot = turn_result.latest_plan_snapshot
            pending_reference_path_add = turn_result.pending_reference_path_add
            if turn_result.exit_code is not None:
                return turn_result.exit_code
    except KeyboardInterrupt:
        print("\nsession: interrupted")
        return EXIT_OK

    if args.max_turns is not None and turn_index >= args.max_turns:
        print(f"session: max_turns_reached ({args.max_turns})")
    return EXIT_OK


def _chat_usage_error(args: argparse.Namespace) -> str | None:
    if args.max_turns is not None and args.max_turns <= 0:
        return "--max-turns must be positive"
    if args.history_limit < 0:
        return "--history-limit must not be negative"
    if args.chat_session_id is not None and not args.chat_session_id.strip():
        return "--chat-session-id must not be blank"
    for reference_path in args.reference_paths:
        if not reference_path.strip():
            return "--reference-path must not be blank"
    for evidence_path in getattr(args, "external_readonly_evidence_paths", ()):
        if not evidence_path.strip():
            return "--external-readonly-evidence-path must not be blank"
    if (
        args.tool_exposure_profile is not None
        and not args.tool_exposure_profile.strip()
    ):
        return "--tool-exposure-profile must not be blank"
    if (
        args.run_workspace_root is not None
        and not str(args.run_workspace_root).strip()
    ):
        return "--run-workspace-root must not be blank"
    if (
        args.run_workspace_max_write_bytes is not None
        and args.run_workspace_max_write_bytes <= 0
    ):
        return "--run-workspace-max-write-bytes must be positive"
    if (
        args.audit_run_workspace_ref is not None
        and not args.audit_run_workspace_ref.strip()
    ):
        return "--audit-run-workspace-ref must not be blank"
    if (
        args.audit_run_workspace_path is not None
        and not str(args.audit_run_workspace_path).strip()
    ):
        return "--audit-run-workspace-path must not be blank"
    if (
        args.audit_run_workspace_root is not None
        and not str(args.audit_run_workspace_root).strip()
    ):
        return "--audit-run-workspace-root must not be blank"
    if args.audit_run_workspace_ref and args.audit_run_workspace_root is None:
        return "--audit-run-workspace-ref requires --audit-run-workspace-root"
    for audit_focus in args.audit_focus:
        if not audit_focus.strip():
            return "--audit-focus must not be blank"
    if _chat_plan_manual_controls_requested(args):
        missing = _chat_plan_manual_control_missing_governance(args)
        if missing:
            return (
                "manual reference/workspace controls require "
                + ", ".join(missing)
                + "; audit controls share this boundary"
            )
        try:
            _chat_plan_runtime_config_context(args)
        except Exception as exc:
            return f"manual reference/workspace config unavailable: {exc}"
    return None


def _chat_session_id(args: argparse.Namespace) -> str:
    if args.chat_session_id:
        return args.chat_session_id.strip()
    return f"cli-chat-{uuid.uuid4().hex[:8]}"
