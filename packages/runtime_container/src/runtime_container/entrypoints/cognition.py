"""Internal cognition CLI shell for controlled runtime execution."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
import warnings
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

from runtime_container.cli_config_profile_explain_workflow import (
    CLI_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
    CliConfigProfileExplainWorkflowRequestCandidate,
    run_cli_config_profile_explain_workflow,
)
from runtime_container.cli_plan_workflow import (
    CliPlanWorkflowRequestCandidate,
    CliPlanWorkflowResultCandidate,
    run_cli_plan_workflow,
)
from runtime_container.cli_reference_review_workflow import (
    CLI_REFERENCE_REVIEW_WORKFLOW_NAME,
    CliReferenceReviewWorkflowRequestCandidate,
    run_cli_reference_review_workflow,
)
from runtime_container.cli_run_workspace_evidence_audit_workflow import (
    CLI_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
    CliRunWorkspaceEvidenceAuditWorkflowRequestCandidate,
    run_cli_run_workspace_evidence_audit_workflow,
)
from runtime_container.cli_task_workflow_registry import (
    CLI_PLAN_WORKFLOW_NAME,
    CliTaskWorkflowRouteCandidate,
    CliTaskWorkflowTurnRequestCandidate,
    build_default_cli_task_workflow_registry,
    cli_task_workflow_route_status_dict,
    route_cli_task_workflow_turn,
)

if TYPE_CHECKING:
    from runtime_container.controlled_adk_run_entry import ControlledAdkRunRequest

PRODUCT_NAME = "Cognition System / 认知系统"
PRODUCT_DEFINITION = "受控运行与智能体治理系统"
CLI_COMMAND = "cognition"
BACKEND = "cognition-system v0.7.0"
AGENT_FRAMEWORK = "Google ADK 2.0.0b1"
ADAPTER = "adk_adapter"
MODE = "controlled · no-live · observable"
DEFAULT_WORKFLOW_NAME = "controlled-adk-run"
DEFAULT_WORKFLOW_ID = "workflow-controlled-adk-run"
CHAT_NO_LIVE_ASSISTANT_MESSAGE = "no-live 模式已完成受控运行，本轮未调用本地模型。"
CHAT_LIVE_NO_PREVIEW_MESSAGE = "controlled-live 模型调用已完成，但未返回可展示的脱敏预览。"
CHAT_LIVE_LLM_MAX_TOKENS = 2048
CHAT_RESPONSE_PREVIEW_LIMIT = 4000
CHAT_RUN_WORKSPACE_RETENTION_POLICIES = ("keep", "ephemeral", "delete_on_success")
CHAT_RUN_WORKSPACE_CLEANUP_POLICIES = (
    "manual",
    "delete_on_success",
    "delete_always",
)

EXIT_OK = 0
EXIT_USAGE_ERROR = 2
EXIT_BLOCKING = 3
EXIT_RUNTIME_FAILURE = 4
EXIT_OUTPUT_WRITE_FAILURE = 5
EXIT_OUTPUT_BOUNDARY_FAILURE = 6

FORBIDDEN_TOP_LEVEL_FIELDS = {
    "recorded_run",
    "raw_adk_object",
    "raw_adk_object_included",
    "raw_state_value",
    "raw_state_values_included",
    "artifact_content",
    "artifact_content_included",
    "secret",
    "token",
    "credential",
    "live_model_payload",
    "llm_invocation_result",
    "llm_call_observation_candidate",
    "agent_llm_invocation_summary_candidate",
    "llm_invocation_readonly_facts",
    "llm_invocation_audit",
    "agent_shell_audit",
    "tool_audit",
    "live_profile",
    "prompt",
    "messages",
    "raw_response",
    "raw_provider_response",
    "response_text",
}
ALLOWED_TOP_LEVEL_FIELDS = {
    "product",
    "command",
    "execution_mode",
    "runtime_id",
    "invocation_id",
    "workflow_id",
    "workflow_name",
    "adk_run_allowed",
    "adk_run_performed",
    "execution_performed",
    "live_llm_call_performed",
    "ollama_call_performed",
    "blocking_reasons",
    "warnings",
    "final_preflight",
    "lifecycle_facts",
    "run_config_service_bundle_facts",
    "governance_summary_payload_ref",
    "llm_invocation_result_ref",
    "llm_invocation_observation_ref",
    "llm_invocation_summary_ref",
    "llm_invocation_call_allowed",
    "llm_invocation_call_attempted",
    "llm_invocation_runtime_call_performed",
    "llm_invocation_failure_type",
    "tool_evidence_ref",
    "tool_run_ref",
    "tool_status",
    "tool_failure_type",
    "tool_runtime_call_performed",
    "controlled_live_llm_preflight",
    "sanitized_evidence_ref",
    "audit_ref",
    "output_ref",
    "status",
    "exit_code",
}

EntryRunner = Callable[["ControlledAdkRunRequest"], Mapping[str, Any]]
RequestBuilder = Callable[
    [argparse.Namespace, Mapping[str, Any]], "ControlledAdkRunRequest"
]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the internal cognition CLI."""

    return run_cli(argv)


def run_cli(
    argv: Sequence[str] | None = None,
    *,
    entry_runner: EntryRunner | None = None,
    request_builder: RequestBuilder | None = None,
) -> int:
    """Run the CLI with injectable execution hooks for tests."""

    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return _exit_code(exc.code)

    if args.command is None:
        return _print_startup(args)

    if args.command == "run":
        with _known_cli_warning_discipline():
            return _run_command(
                args,
                entry_runner=entry_runner or _default_entry_runner,
                request_builder=request_builder or _default_request_builder,
            )

    if args.command == "chat":
        with _known_cli_warning_discipline():
            return _chat_command(
                args,
                entry_runner=entry_runner or _default_entry_runner,
                request_builder=request_builder or _default_request_builder,
            )

    if args.command == "config" and args.config_command == "init":
        return _config_init_command(args)

    parser.print_help()
    return EXIT_USAGE_ERROR


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=CLI_COMMAND,
        description="Cognition System controlled runtime CLI.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON status output.",
    )
    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="Suppress the startup banner.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser(
        "run",
        help="Run a controlled workflow through the productized entry.",
        description="Run a controlled workflow through the productized entry.",
    )
    run_parser.add_argument("--config-root", type=Path, default=Path(".") / "config")
    run_parser.add_argument("--environment", default="local")
    run_parser.add_argument("--profile")
    run_parser.add_argument("--runtime-id")
    run_parser.add_argument("--workflow-id")
    run_parser.add_argument("--workflow-name")
    input_group = run_parser.add_mutually_exclusive_group()
    input_group.add_argument("--input-json")
    input_group.add_argument("--input-file", type=Path)
    input_group.add_argument("--input-text")
    run_parser.add_argument("--operator-approved", action="store_true")
    run_parser.add_argument("--approval-ref")
    run_parser.add_argument("--audit-ref")
    run_parser.add_argument("--sanitized-evidence-ref")
    run_parser.add_argument("--governance-summary-output-ref")
    run_parser.add_argument("--request-live-llm", action="store_true")
    run_parser.add_argument("--request-ollama", action="store_true")
    run_parser.add_argument("--allow-live-llm", action="store_true")
    run_parser.add_argument("--allow-ollama", action="store_true")
    run_parser.add_argument("--live-llm-approval-ref")
    run_parser.add_argument("--ollama-api-base")
    run_parser.add_argument("--live-llm-timeout-seconds", type=int)
    run_parser.add_argument("--format", choices=("text", "json"), default="text")
    run_parser.add_argument("--json", action="store_true")
    run_parser.add_argument("--output", type=Path)
    run_parser.add_argument("--no-banner", action="store_true")
    run_parser.add_argument("--preflight-only", action="store_true")

    chat_parser = subparsers.add_parser(
        "chat",
        help="Start a controlled multi-turn terminal chat.",
        description="Start a controlled multi-turn terminal chat.",
    )
    chat_parser.add_argument("--config-root", type=Path, default=Path(".") / "config")
    chat_parser.add_argument("--environment", default="local")
    chat_parser.add_argument("--profile")
    chat_parser.add_argument("--workflow-id")
    chat_parser.add_argument("--workflow-name")
    chat_parser.add_argument("--operator-approved", action="store_true")
    chat_parser.add_argument("--approval-ref")
    chat_parser.add_argument("--audit-ref")
    chat_parser.add_argument("--sanitized-evidence-ref")
    chat_parser.add_argument("--governance-summary-output-ref")
    chat_parser.add_argument("--request-live-llm", action="store_true")
    chat_parser.add_argument("--request-ollama", action="store_true")
    chat_parser.add_argument("--allow-live-llm", action="store_true")
    chat_parser.add_argument("--allow-ollama", action="store_true")
    chat_parser.add_argument("--live-llm-approval-ref")
    chat_parser.add_argument("--ollama-api-base")
    chat_parser.add_argument("--live-llm-timeout-seconds", type=int)
    chat_parser.add_argument("--chat-session-id")
    chat_parser.add_argument("--max-turns", type=int)
    chat_parser.add_argument("--history-limit", type=int, default=6)
    chat_parser.add_argument(
        "--reference-path",
        dest="reference_paths",
        action="append",
        default=[],
        help="Add a governed local reference path for plan workflow turns.",
    )
    chat_parser.add_argument(
        "--tool-exposure-profile",
        help="Select the configured readonly tool exposure profile for references.",
    )
    chat_parser.add_argument(
        "--enable-run-workspace",
        action="store_true",
        help="Create a governed run workspace for plan workflow turns.",
    )
    chat_parser.add_argument("--run-workspace-root", type=Path)
    chat_parser.add_argument(
        "--run-workspace-retention-policy",
        choices=CHAT_RUN_WORKSPACE_RETENTION_POLICIES,
    )
    chat_parser.add_argument(
        "--run-workspace-cleanup-policy",
        choices=CHAT_RUN_WORKSPACE_CLEANUP_POLICIES,
    )
    chat_parser.add_argument("--run-workspace-max-write-bytes", type=int)
    audit_target_group = chat_parser.add_mutually_exclusive_group()
    audit_target_group.add_argument(
        "--audit-run-workspace-path",
        type=Path,
        help="Read-only run workspace path to audit.",
    )
    audit_target_group.add_argument(
        "--audit-run-workspace-ref",
        help="Read-only run workspace ref to audit.",
    )
    chat_parser.add_argument(
        "--audit-run-workspace-root",
        type=Path,
        help="Root used to resolve --audit-run-workspace-ref.",
    )
    chat_parser.add_argument(
        "--audit-focus",
        action="append",
        default=[],
        help="Add a bounded audit focus for run workspace evidence audit.",
    )
    chat_parser.add_argument("--no-banner", action="store_true")

    config_parser = subparsers.add_parser(
        "config",
        help="Initialize and inspect the Cognition System config center.",
        description="Initialize and inspect the Cognition System config center.",
    )
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True)
    config_init_parser = config_subparsers.add_parser(
        "init",
        help="Create a user-owned config/ directory from packaged defaults.",
        description="Create a user-owned config/ directory from packaged defaults.",
    )
    config_init_parser.add_argument(
        "--config-root",
        type=Path,
        default=Path(".") / "config",
        help="Target config root to initialize.",
    )
    config_init_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing packaged baseline files.",
    )
    config_init_parser.add_argument("--json", action="store_true")
    return parser


def _print_startup(args: argparse.Namespace) -> int:
    status = _startup_status()
    if args.json:
        print(json.dumps(status, ensure_ascii=False, sort_keys=True))
        return EXIT_OK
    if args.no_banner:
        return EXIT_OK
    print(_startup_text(status))
    return EXIT_OK


def _config_init_command(args: argparse.Namespace) -> int:
    try:
        from config_assembly.runtime import init_default_config_root

        result = init_default_config_root(
            args.config_root,
            overwrite=args.overwrite,
        )
    except Exception as exc:  # pragma: no cover - defensive packaging boundary.
        print(f"cognition config init error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_FAILURE

    payload = {
        "command": "cognition config init",
        "config_root": result.config_root,
        "source": result.source,
        "files": [file.to_json_dict() for file in result.files],
        "status": "succeeded",
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return EXIT_OK

    lines = [
        "Cognition System config initialized",
        f"config_root: {result.config_root}",
        f"source: {result.source}",
    ]
    lines.extend(f"{file.status}: {file.relative_path}" for file in result.files)
    lines.append("next: cognition chat --config-root " + result.config_root)
    print("\n".join(lines))
    return EXIT_OK


def _run_command(
    args: argparse.Namespace,
    *,
    entry_runner: EntryRunner,
    request_builder: RequestBuilder,
) -> int:
    try:
        input_payload = _load_input_payload(args)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"cognition run error: {exc}", file=sys.stderr)
        return EXIT_USAGE_ERROR

    _apply_run_defaults(args)
    blocking_reasons = _cli_blocking_reasons(args)
    if args.preflight_only:
        output = _preflight_only_output(args, blocking_reasons)
        exit_code = EXIT_OK if not blocking_reasons else EXIT_BLOCKING
        output["exit_code"] = exit_code
        return _emit_run_output(args, output, exit_code=exit_code)

    if blocking_reasons:
        output = _blocking_output(args, blocking_reasons)
        return _emit_run_output(args, output, exit_code=EXIT_BLOCKING)

    try:
        request = request_builder(args, input_payload)
        entry_result = dict(entry_runner(request))
    except Exception as exc:  # pragma: no cover - defensive runtime boundary.
        print(f"cognition run runtime error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_FAILURE

    output = _cli_output_from_entry_result(args, entry_result)
    if _violates_output_boundary(output):
        print("cognition run output boundary violation", file=sys.stderr)
        return EXIT_OUTPUT_BOUNDARY_FAILURE

    if output["blocking_reasons"]:
        exit_code = EXIT_BLOCKING
    elif output["execution_performed"] is True:
        exit_code = EXIT_OK
    else:
        exit_code = EXIT_RUNTIME_FAILURE
    output["exit_code"] = exit_code
    return _emit_run_output(args, output, exit_code=exit_code)


def _chat_command(
    args: argparse.Namespace,
    *,
    entry_runner: EntryRunner,
    request_builder: RequestBuilder,
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
    latest_plan_result: CliPlanWorkflowResultCandidate | None = None
    task_workflow_registry = build_default_cli_task_workflow_registry()
    turn_index = 0
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
        if _chat_status_command(line):
            latest_plan_result, status_summary_artifact_ref = (
                _persist_chat_status_summary(
                    args,
                    chat_session_id,
                    turn_index,
                    latest_plan_result=latest_plan_result,
                )
            )
            if _chat_status_json_command(line):
                print(
                    _chat_status_json_text(
                        args,
                        chat_session_id,
                        turn_index,
                        latest_plan_result=latest_plan_result,
                        status_summary_artifact_ref=status_summary_artifact_ref,
                    )
                )
                continue
            print(
                _chat_status_text(
                    args,
                    chat_session_id,
                    turn_index,
                    latest_plan_result=latest_plan_result,
                    status_summary_artifact_ref=status_summary_artifact_ref,
                )
            )
            continue

        turn_index += 1
        task_route = route_cli_task_workflow_turn(
            task_workflow_registry,
            _chat_task_workflow_turn_request(
                args=args,
                user_text=line,
                chat_session_id=chat_session_id,
                turn_index=turn_index,
                history=history,
                previous_terminal_display_text=latest_plan_display_text,
            ),
        )
        if task_route.matched and task_route.workflow_name == CLI_PLAN_WORKFLOW_NAME:
            turn_args = _chat_turn_args(args, chat_session_id, turn_index)
            _apply_run_defaults(turn_args)
            blocking_reasons = _cli_blocking_reasons(turn_args)
            if blocking_reasons:
                output = _blocking_output(turn_args, blocking_reasons)
                output["exit_code"] = EXIT_BLOCKING
                assistant_text = CHAT_NO_LIVE_ASSISTANT_MESSAGE
                print(_chat_turn_text_output(output, assistant_text, turn_index))
                return EXIT_BLOCKING
            plan_result = run_cli_plan_workflow(
                _chat_plan_workflow_request(
                    args=turn_args,
                    user_text=line,
                    chat_session_id=chat_session_id,
                    turn_index=turn_index,
                    history=history,
                    previous_plan_text=latest_plan_display_text,
                    route=task_route,
                )
            )
            print(plan_result.terminal_display_text)
            latest_plan_display_text = plan_result.terminal_display_text
            latest_plan_result = plan_result
            history.append(
                _chat_history_entry(
                    user_text=line,
                    assistant_text=plan_result.terminal_display_text,
                )
            )
            continue
        if (
            task_route.matched
            and task_route.workflow_name == CLI_REFERENCE_REVIEW_WORKFLOW_NAME
        ):
            turn_args = _chat_turn_args(args, chat_session_id, turn_index)
            _apply_run_defaults(turn_args)
            blocking_reasons = _cli_blocking_reasons(turn_args)
            if blocking_reasons:
                output = _blocking_output(turn_args, blocking_reasons)
                output["exit_code"] = EXIT_BLOCKING
                assistant_text = CHAT_NO_LIVE_ASSISTANT_MESSAGE
                print(_chat_turn_text_output(output, assistant_text, turn_index))
                return EXIT_BLOCKING
            review_result = run_cli_reference_review_workflow(
                _chat_reference_review_workflow_request(
                    args=turn_args,
                    user_text=line,
                    chat_session_id=chat_session_id,
                    turn_index=turn_index,
                    history=history,
                    route=task_route,
                )
            )
            print(review_result.terminal_display_text)
            history.append(
                _chat_history_entry(
                    user_text=line,
                    assistant_text=review_result.terminal_display_text,
                )
            )
            continue
        if (
            task_route.matched
            and task_route.workflow_name == CLI_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME
        ):
            turn_args = _chat_turn_args(args, chat_session_id, turn_index)
            config_explain_result = run_cli_config_profile_explain_workflow(
                _chat_config_profile_explain_workflow_request(
                    args=turn_args,
                    user_text=line,
                    chat_session_id=chat_session_id,
                    turn_index=turn_index,
                    history=history,
                    route=task_route,
                )
            )
            print(config_explain_result.terminal_display_text)
            history.append(
                _chat_history_entry(
                    user_text=line,
                    assistant_text=config_explain_result.terminal_display_text,
                )
            )
            continue
        if (
            task_route.matched
            and task_route.workflow_name
            == CLI_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME
        ):
            turn_args = _chat_turn_args(args, chat_session_id, turn_index)
            audit_result = run_cli_run_workspace_evidence_audit_workflow(
                _chat_run_workspace_evidence_audit_workflow_request(
                    args=turn_args,
                    user_text=line,
                    chat_session_id=chat_session_id,
                    turn_index=turn_index,
                    history=history,
                    route=task_route,
                )
            )
            print(audit_result.terminal_display_text)
            history.append(
                _chat_history_entry(
                    user_text=line,
                    assistant_text=audit_result.terminal_display_text,
                )
            )
            continue
        if task_route.matched:
            print(
                "cognition chat task workflow route unsupported: "
                + str(task_route.workflow_name),
                file=sys.stderr,
            )
            return EXIT_RUNTIME_FAILURE

        turn_args = _chat_turn_args(args, chat_session_id, turn_index)
        input_payload = _chat_input_payload(
            input_summary=line,
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
        )
        if output is None:
            return exit_code
        assistant_text = _assistant_text_from_chat_turn(output, entry_result)
        print(_chat_turn_text_output(output, assistant_text, turn_index))
        if exit_code != EXIT_OK:
            return exit_code
        history.append(
            _chat_history_entry(user_text=line, assistant_text=assistant_text)
        )

    if args.max_turns is not None and turn_index >= args.max_turns:
        print(f"session: max_turns_reached ({args.max_turns})")
    return EXIT_OK


def _chat_task_workflow_turn_request(
    *,
    args: argparse.Namespace,
    user_text: str,
    chat_session_id: str,
    turn_index: int,
    history: Sequence[Mapping[str, str]],
    previous_terminal_display_text: str | None,
) -> CliTaskWorkflowTurnRequestCandidate:
    return CliTaskWorkflowTurnRequestCandidate(
        user_text=user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        history=tuple(history),
        previous_terminal_display_text=previous_terminal_display_text,
        live_model_requested=args.request_live_llm,
        reference_paths=tuple(args.reference_paths),
        run_workspace_requested=_chat_plan_workspace_args_requested(args),
        audit_run_workspace_requested=_chat_audit_workspace_args_requested(args),
        metadata={"source": "runtime_container.entrypoints.cognition"},
    )


def _chat_plan_workflow_request(
    *,
    args: argparse.Namespace,
    user_text: str,
    chat_session_id: str,
    turn_index: int,
    history: Sequence[Mapping[str, str]],
    previous_plan_text: str | None,
    route: CliTaskWorkflowRouteCandidate | None = None,
) -> CliPlanWorkflowRequestCandidate:
    live_model_allowed = _full_controlled_live_args(args)
    plan_controls = _chat_plan_control_kwargs(args)
    return CliPlanWorkflowRequestCandidate(
        user_text=user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        history=tuple(history),
        previous_plan_text=previous_plan_text,
        live_model_allowed=live_model_allowed,
        llm_invocation_service=(
            _default_llm_invocation_service(args) if live_model_allowed else None
        ),
        approval_ref=args.approval_ref,
        audit_ref=args.audit_ref,
        sanitized_evidence_ref=args.sanitized_evidence_ref,
        metadata={
            "source": "runtime_container.entrypoints.cognition",
            "chat_entry_is_trigger_only": True,
            "task_workflow_route": (
                cli_task_workflow_route_status_dict(route) if route else None
            ),
            **plan_controls.pop("metadata", {}),
        },
        **plan_controls,
    )


def _chat_reference_review_workflow_request(
    *,
    args: argparse.Namespace,
    user_text: str,
    chat_session_id: str,
    turn_index: int,
    history: Sequence[Mapping[str, str]],
    route: CliTaskWorkflowRouteCandidate | None = None,
) -> CliReferenceReviewWorkflowRequestCandidate:
    live_model_allowed = _full_controlled_live_args(args)
    review_controls = _chat_plan_control_kwargs(args)
    return CliReferenceReviewWorkflowRequestCandidate(
        user_text=user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        history=tuple(history),
        live_model_allowed=live_model_allowed,
        llm_invocation_service=(
            _default_llm_invocation_service(args) if live_model_allowed else None
        ),
        approval_ref=args.approval_ref,
        audit_ref=args.audit_ref,
        sanitized_evidence_ref=args.sanitized_evidence_ref,
        metadata={
            "source": "runtime_container.entrypoints.cognition",
            "chat_entry_is_trigger_only": True,
            "task_workflow_route": (
                cli_task_workflow_route_status_dict(route) if route else None
            ),
            **review_controls.pop("metadata", {}),
        },
        **review_controls,
    )


def _chat_config_profile_explain_workflow_request(
    *,
    args: argparse.Namespace,
    user_text: str,
    chat_session_id: str,
    turn_index: int,
    history: Sequence[Mapping[str, str]],
    route: CliTaskWorkflowRouteCandidate | None = None,
) -> CliConfigProfileExplainWorkflowRequestCandidate:
    plan_controls = _chat_plan_control_kwargs(args)
    control_metadata = dict(plan_controls.get("metadata") or {})
    return CliConfigProfileExplainWorkflowRequestCandidate(
        user_text=user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        history=tuple(history),
        config_context=_chat_plan_runtime_config_context(args),
        config_root=str(args.config_root),
        environment=args.environment,
        profile=args.profile,
        request_live_llm=args.request_live_llm,
        request_ollama=args.request_ollama,
        allow_live_llm=args.allow_live_llm,
        allow_ollama=args.allow_ollama,
        ollama_api_base=args.ollama_api_base,
        live_llm_timeout_seconds=args.live_llm_timeout_seconds,
        operator_approved=args.operator_approved,
        approval_ref=args.approval_ref,
        audit_ref=args.audit_ref,
        sanitized_evidence_ref=args.sanitized_evidence_ref,
        governance_summary_output_ref=args.governance_summary_output_ref,
        reference_paths=tuple(args.reference_paths),
        tool_exposure_profile=args.tool_exposure_profile,
        cli_explicit_args=_chat_config_profile_cli_explicit_args(args),
        session_args={},
        run_workspace_root=plan_controls["run_workspace_root"],
        run_workspace_enabled=plan_controls["run_workspace_enabled"],
        run_workspace_retention_policy=plan_controls[
            "run_workspace_retention_policy"
        ],
        run_workspace_cleanup_policy=plan_controls["run_workspace_cleanup_policy"],
        run_workspace_max_write_bytes=plan_controls["run_workspace_max_write_bytes"],
        metadata={
            "source": "runtime_container.entrypoints.cognition",
            "chat_entry_is_trigger_only": True,
            "task_workflow_route": (
                cli_task_workflow_route_status_dict(route) if route else None
            ),
            **control_metadata,
        },
    )


def _chat_run_workspace_evidence_audit_workflow_request(
    *,
    args: argparse.Namespace,
    user_text: str,
    chat_session_id: str,
    turn_index: int,
    history: Sequence[Mapping[str, str]],
    route: CliTaskWorkflowRouteCandidate | None = None,
) -> CliRunWorkspaceEvidenceAuditWorkflowRequestCandidate:
    plan_controls = _chat_plan_control_kwargs(args)
    control_metadata = dict(plan_controls.get("metadata") or {})
    return CliRunWorkspaceEvidenceAuditWorkflowRequestCandidate(
        user_text=user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        history=tuple(history),
        audit_run_workspace_path=args.audit_run_workspace_path,
        audit_run_workspace_ref=args.audit_run_workspace_ref,
        audit_run_workspace_root=args.audit_run_workspace_root,
        audit_focus=tuple(args.audit_focus),
        approval_ref=args.approval_ref,
        audit_ref=args.audit_ref,
        sanitized_evidence_ref=args.sanitized_evidence_ref,
        user_passthrough_parameters={},
        run_workspace_root=plan_controls["run_workspace_root"],
        run_workspace_enabled=plan_controls["run_workspace_enabled"],
        run_workspace_retention_policy=plan_controls[
            "run_workspace_retention_policy"
        ],
        run_workspace_cleanup_policy=plan_controls["run_workspace_cleanup_policy"],
        run_workspace_max_write_bytes=plan_controls["run_workspace_max_write_bytes"],
        metadata={
            "source": "runtime_container.entrypoints.cognition",
            "chat_entry_is_trigger_only": True,
            "task_workflow_route": (
                cli_task_workflow_route_status_dict(route) if route else None
            ),
            "governance_summary_output_ref_present": bool(
                args.governance_summary_output_ref
            ),
            **control_metadata,
        },
    )


def _chat_config_profile_cli_explicit_args(
    args: argparse.Namespace,
) -> dict[str, Any]:
    cli_explicit_args: dict[str, Any] = {}
    if args.tool_exposure_profile:
        cli_explicit_args["tool_exposure_profile"] = args.tool_exposure_profile
    if args.enable_run_workspace:
        cli_explicit_args["enable_run_workspace"] = True
    if args.run_workspace_root is not None:
        cli_explicit_args["run_workspace_root"] = str(args.run_workspace_root)
    if args.run_workspace_retention_policy is not None:
        cli_explicit_args["run_workspace_retention_policy"] = (
            args.run_workspace_retention_policy
        )
    if args.run_workspace_cleanup_policy is not None:
        cli_explicit_args["run_workspace_cleanup_policy"] = (
            args.run_workspace_cleanup_policy
        )
    if args.run_workspace_max_write_bytes is not None:
        cli_explicit_args["run_workspace_max_write_bytes"] = (
            args.run_workspace_max_write_bytes
        )
    if args.request_live_llm:
        cli_explicit_args["request_live_llm"] = True
    if args.request_ollama:
        cli_explicit_args["request_ollama"] = True
    if args.allow_live_llm:
        cli_explicit_args["allow_live_llm"] = True
    if args.allow_ollama:
        cli_explicit_args["allow_ollama"] = True
    if args.ollama_api_base:
        cli_explicit_args["ollama_api_base"] = args.ollama_api_base
    if args.live_llm_timeout_seconds is not None:
        cli_explicit_args["live_llm_timeout_seconds"] = (
            args.live_llm_timeout_seconds
        )
    return cli_explicit_args


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


def _chat_banner(chat_session_id: str) -> str:
    return "\n".join(
        [
            f"{PRODUCT_NAME} chat",
            f"session: {chat_session_id}",
            "type /help, /status or /exit",
        ]
    )


def _chat_help_text() -> str:
    return "\n".join(
        [
            "commands:",
            "  /help    show chat commands",
            "  /status  show current chat session status",
            "  /status --json  show machine-readable status",
            "  /exit    close the chat session",
        ]
    )


def _chat_status_command(line: str) -> bool:
    return line in {"/status", "/status --json", "/status json", "/status-json"}


def _chat_status_json_command(line: str) -> bool:
    return line in {"/status --json", "/status json", "/status-json"}


def _chat_status_text(
    args: argparse.Namespace,
    chat_session_id: str,
    turn_count: int,
    *,
    latest_plan_result: CliPlanWorkflowResultCandidate | None = None,
    status_summary_artifact_ref: str | None = None,
) -> str:
    payload = _chat_status_payload(
        args,
        chat_session_id,
        turn_count,
        latest_plan_result=latest_plan_result,
        status_summary_artifact_ref=status_summary_artifact_ref,
    )
    tools = payload["tools"]
    workspace = payload["workspace"]
    skills = payload["skills"]
    skill_projection = skills.get("capability_projection") or {}
    latest = payload["latest_plan"]
    return "\n".join(
        [
            f"session: {payload['chat_session_id']}",
            f"turn_count: {payload['turn_count']}",
            f"history_limit: {payload['history_limit']}",
            f"live_llm_requested: {str(payload['live_llm_requested']).lower()}",
            f"ollama_requested: {str(payload['ollama_requested']).lower()}",
            f"reference_path_count: {payload['reference_path_count']}",
            "run_workspace_requested: "
            f"{str(payload['run_workspace_requested']).lower()}",
            f"tool_profile: {tools['profile_name']}",
            f"tool_exposure_status: {tools['status']}",
            "exposed_tools: "
            + _chat_status_csv(tools.get("exposed_tool_names") or []),
            "blocked_tools: "
            + _chat_status_csv(tools.get("blocked_tool_names") or []),
            f"reference_reader_status: {tools['reference_reader_status']}",
            "tool_config_precedence: "
            + _chat_status_csv(tools.get("config_precedence") or []),
            f"run_workspace_enabled: {str(workspace['enabled']).lower()}",
            f"run_workspace_root: {workspace['root'] or 'none'}",
            f"run_workspace_retention_policy: {workspace['retention_policy']}",
            f"run_workspace_cleanup_policy: {workspace['cleanup_policy']}",
            f"run_workspace_max_write_bytes: {workspace['max_write_bytes']}",
            f"skills_status: {skills['status']}",
            "skills_metadata_view_available: "
            f"{str(skills['metadata_view_available']).lower()}",
            "skills_runtime_integrated: "
            f"{str(skills['runtime_integrated']).lower()}",
            "skill_toolset_runtime_enabled: "
            f"{str(skills['skill_toolset_runtime_enabled']).lower()}",
            "skill_registry_runtime_enabled: "
            f"{str(skills['skill_registry_runtime_enabled']).lower()}",
            "skills_capability_projection_status: "
            + str(skill_projection.get("status") or "not_configured"),
            "skills_capability_projection_count: "
            + str(skill_projection.get("projection_count") or 0),
            "skills_workflow_slot_reference_count: "
            + str(skill_projection.get("workflow_slot_reference_count") or 0),
            "skills_active_slot_reference_count: "
            + str(skill_projection.get("active_slot_reference_count") or 0),
            "skills_projection_runtime_enabled: "
            + str(skill_projection.get("runtime_enabled", False)).lower(),
            "skills_projection_public_schema_enabled: "
            + str(skill_projection.get("public_schema_enabled", False)).lower(),
            "latest_plan_status: " + str(latest["status"]),
            "latest_reference_context_status: "
            + str(latest["reference_context_status"]),
            "latest_reference_evidence_ref_count: "
            + str(latest["reference_evidence_ref_count"]),
            "latest_workspace_created: "
            + str(latest["workspace_created"]).lower(),
            "latest_workspace_ref: " + str(latest["workspace_ref"] or "none"),
            "latest_workspace_artifact_ref_count: "
            + str(latest["workspace_artifact_ref_count"]),
            "latest_workspace_result_ref_count: "
            + str(latest["workspace_result_ref_count"]),
            "status_summary_artifact_ref: "
            + str(payload["status_summary_artifact_ref"] or "none"),
        ]
    )


def _chat_status_json_text(
    args: argparse.Namespace,
    chat_session_id: str,
    turn_count: int,
    *,
    latest_plan_result: CliPlanWorkflowResultCandidate | None = None,
    status_summary_artifact_ref: str | None = None,
) -> str:
    payload = _chat_status_payload(
        args,
        chat_session_id,
        turn_count,
        latest_plan_result=latest_plan_result,
        status_summary_artifact_ref=status_summary_artifact_ref,
    )
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _chat_status_payload(
    args: argparse.Namespace,
    chat_session_id: str,
    turn_count: int,
    *,
    latest_plan_result: CliPlanWorkflowResultCandidate | None = None,
    status_summary_artifact_ref: str | None = None,
) -> dict[str, Any]:
    control_status = _chat_control_status(args, latest_plan_result)
    return {
        "product": PRODUCT_NAME,
        "command": "cognition chat /status",
        "chat_session_id": chat_session_id,
        "turn_count": turn_count,
        "history_limit": args.history_limit,
        "live_llm_requested": args.request_live_llm,
        "ollama_requested": args.request_ollama,
        "reference_path_count": len(args.reference_paths),
        "run_workspace_requested": _chat_plan_workspace_args_requested(args),
        "tools": control_status["tools"],
        "workspace": control_status["workspace"],
        "skills": control_status["skills"],
        "latest_plan": control_status["latest_plan"],
        "status_summary_artifact_ref": status_summary_artifact_ref,
    }


def _chat_turn_args(
    args: argparse.Namespace,
    chat_session_id: str,
    turn_index: int,
) -> argparse.Namespace:
    turn_id = _chat_turn_id(turn_index)
    return argparse.Namespace(
        command="run",
        config_root=args.config_root,
        environment=args.environment,
        profile=args.profile,
        runtime_id=f"runtime-{chat_session_id}-{turn_id}",
        workflow_id=args.workflow_id,
        workflow_name=args.workflow_name,
        input_json=None,
        input_file=None,
        input_text=None,
        operator_approved=args.operator_approved,
        approval_ref=_derive_chat_ref(args.approval_ref, chat_session_id, turn_id),
        audit_ref=_derive_chat_ref(args.audit_ref, chat_session_id, turn_id),
        sanitized_evidence_ref=_derive_chat_ref(
            args.sanitized_evidence_ref, chat_session_id, turn_id
        ),
        governance_summary_output_ref=_derive_chat_ref(
            args.governance_summary_output_ref, chat_session_id, turn_id
        ),
        request_live_llm=args.request_live_llm,
        request_ollama=args.request_ollama,
        allow_live_llm=args.allow_live_llm,
        allow_ollama=args.allow_ollama,
        live_llm_approval_ref=_derive_chat_ref(
            args.live_llm_approval_ref, chat_session_id, turn_id
        ),
        ollama_api_base=args.ollama_api_base,
        live_llm_timeout_seconds=args.live_llm_timeout_seconds,
        chat_live_llm_max_tokens=CHAT_LIVE_LLM_MAX_TOKENS,
        chat_response_preview_limit=CHAT_RESPONSE_PREVIEW_LIMIT,
        reference_paths=tuple(args.reference_paths),
        tool_exposure_profile=args.tool_exposure_profile,
        enable_run_workspace=args.enable_run_workspace,
        run_workspace_root=args.run_workspace_root,
        run_workspace_retention_policy=args.run_workspace_retention_policy,
        run_workspace_cleanup_policy=args.run_workspace_cleanup_policy,
        run_workspace_max_write_bytes=args.run_workspace_max_write_bytes,
        audit_run_workspace_path=args.audit_run_workspace_path,
        audit_run_workspace_ref=args.audit_run_workspace_ref,
        audit_run_workspace_root=args.audit_run_workspace_root,
        audit_focus=tuple(args.audit_focus),
        format="text",
        json=False,
        output=None,
        no_banner=True,
        preflight_only=False,
    )


def _chat_turn_id(turn_index: int) -> str:
    return f"turn-{turn_index:03d}"


def _derive_chat_ref(
    base_ref: str | None,
    chat_session_id: str,
    turn_id: str,
) -> str | None:
    if not base_ref:
        return None
    return f"{base_ref.rstrip('/')}/{chat_session_id}/{turn_id}"


def _chat_plan_manual_controls_requested(args: argparse.Namespace) -> bool:
    return bool(
        args.reference_paths
        or args.tool_exposure_profile
        or _chat_plan_workspace_args_requested(args)
        or _chat_audit_workspace_args_requested(args)
    )


def _chat_audit_workspace_args_requested(args: argparse.Namespace) -> bool:
    return bool(
        getattr(args, "audit_run_workspace_path", None) is not None
        or getattr(args, "audit_run_workspace_ref", None)
        or getattr(args, "audit_run_workspace_root", None) is not None
        or getattr(args, "audit_focus", ())
    )


def _chat_plan_workspace_args_requested(args: argparse.Namespace) -> bool:
    return bool(
        args.enable_run_workspace
        or args.run_workspace_root is not None
        or args.run_workspace_retention_policy is not None
        or args.run_workspace_cleanup_policy is not None
        or args.run_workspace_max_write_bytes is not None
    )


def _persist_chat_status_summary(
    args: argparse.Namespace,
    chat_session_id: str,
    turn_count: int,
    *,
    latest_plan_result: CliPlanWorkflowResultCandidate | None,
) -> tuple[CliPlanWorkflowResultCandidate | None, str | None]:
    if latest_plan_result is None or latest_plan_result.run_workspace is None:
        return latest_plan_result, None
    workspace = latest_plan_result.run_workspace
    if not workspace.workspace_created or workspace.cleanup_performed:
        return latest_plan_result, None

    from runtime_container.cli_run_workspace import (
        finalize_cli_run_workspace,
        write_cli_run_workspace_json,
    )

    payload = _chat_status_payload(
        args,
        chat_session_id,
        turn_count,
        latest_plan_result=latest_plan_result,
    )
    max_write_bytes = int(workspace.metadata.get("max_write_bytes") or 65536)
    workspace, write_result = write_cli_run_workspace_json(
        workspace,
        relative_path="artifacts/status_summary.json",
        payload=payload,
        kind="artifact",
        max_write_bytes=max_write_bytes,
    )
    if write_result.status != "succeeded":
        return latest_plan_result, None
    latest_plan_result = replace(latest_plan_result, run_workspace=workspace)
    payload = _chat_status_payload(
        args,
        chat_session_id,
        turn_count,
        latest_plan_result=latest_plan_result,
        status_summary_artifact_ref=write_result.ref,
    )
    workspace, write_result = write_cli_run_workspace_json(
        workspace,
        relative_path="artifacts/status_summary.json",
        payload=payload,
        kind="artifact",
        max_write_bytes=max_write_bytes,
    )
    if write_result.status != "succeeded":
        return latest_plan_result, None
    workspace = finalize_cli_run_workspace(
        workspace,
        status=_chat_plan_result_status(latest_plan_result),
        metadata={"status_summary_artifact_ref": write_result.ref},
    )
    latest_plan_result = replace(latest_plan_result, run_workspace=workspace)
    return latest_plan_result, write_result.ref


def _chat_control_status(
    args: argparse.Namespace,
    latest_plan_result: CliPlanWorkflowResultCandidate | None,
) -> dict[str, Any]:
    plan_controls = _chat_plan_control_kwargs(args)
    return {
        "tools": _chat_tools_status(
            profile_name=plan_controls["reference_profile_name"],
            profile_config=plan_controls["reference_profile_config"],
            repo_root=plan_controls["reference_repo_root"],
            cli_explicit_args=plan_controls["reference_cli_explicit_args"],
            operator_approved=args.operator_approved,
            approval_ref=args.approval_ref,
        ),
        "workspace": _chat_workspace_status(plan_controls),
        "skills": _chat_skills_status(),
        "latest_plan": _chat_latest_plan_status(latest_plan_result),
    }


def _chat_tools_status(
    *,
    profile_name: str,
    profile_config: Mapping[str, Any] | None,
    repo_root: str,
    cli_explicit_args: Mapping[str, Any],
    operator_approved: bool,
    approval_ref: str | None,
) -> dict[str, Any]:
    from runtime_container.cli_tool_loading_validation import (
        cli_tool_loading_gate_status_dict,
        validate_cli_tool_loading_gate,
    )
    from runtime_container.cli_tool_exposure_profile import (
        cli_tool_exposure_profile_status_dict,
        resolve_cli_tool_exposure_profile,
    )

    resolution = resolve_cli_tool_exposure_profile(
        profile_name=profile_name,
        profile_config=profile_config,
        repo_root=repo_root,
        cli_explicit_args=cli_explicit_args,
    )
    status = cli_tool_exposure_profile_status_dict(resolution)
    loading_gate = validate_cli_tool_loading_gate(
        resolution,
        operator_approved=operator_approved,
        approval_ref=approval_ref,
    )
    loading_status = cli_tool_loading_gate_status_dict(loading_gate)
    profile = status["profile"]
    selection = status["selection"]
    reference_policy = status["reference_reader_policy"]
    return {
        "profile_name": profile["name"],
        "status": profile["status"],
        "config_precedence": profile["config_precedence"],
        "blocking_reasons": profile["blocking_reasons"],
        "warnings": profile["warnings"],
        "exposed_tool_names": selection["exposed_tool_names"],
        "blocked_tool_names": selection["blocked_tool_names"],
        "loading_validation_status": loading_status["status"],
        "risk_gate_status": loading_status["risk_gate_status"],
        "loading_allowed_tool_names": loading_status["allowed_tool_names"],
        "loading_blocked_tool_names": loading_status["blocked_tool_names"],
        "loading_blocking_reasons": loading_status["blocking_reasons"],
        "loading_warnings": loading_status["warnings"],
        "tool_loading_validations": loading_status["validations"],
        "reference_reader_status": "enabled" if reference_policy else "not_exposed",
        "reference_reader_policy": reference_policy,
    }


def _chat_workspace_status(plan_controls: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "enabled": bool(plan_controls["run_workspace_enabled"]),
        "root": plan_controls["run_workspace_root"],
        "retention_policy": plan_controls["run_workspace_retention_policy"],
        "cleanup_policy": plan_controls["run_workspace_cleanup_policy"],
        "max_write_bytes": plan_controls["run_workspace_max_write_bytes"],
    }


def _chat_skills_status() -> dict[str, Any]:
    try:
        from config_contexts import SkillCandidateFlags, SkillMetadataViewCandidate

        flags = SkillCandidateFlags()
        metadata_view_available = SkillMetadataViewCandidate is not None
    except Exception:
        return {
            "status": "candidate_view_unavailable",
            "metadata_view_available": False,
            "runtime_integrated": False,
            "skill_toolset_runtime_enabled": False,
            "skill_registry_runtime_enabled": False,
            "real_skill_loading_enabled": False,
            "capability_projection": _chat_skill_capability_projection_status(),
        }
    return {
        "status": "candidate_only_frozen",
        "metadata_view_available": metadata_view_available,
        "runtime_integrated": False,
        "skill_toolset_runtime_enabled": flags.skill_toolset_runtime_enabled,
        "skill_registry_runtime_enabled": flags.skill_registry_runtime_enabled,
        "real_skill_loading_enabled": False,
        "capability_projection": _chat_skill_capability_projection_status(),
    }


def _chat_skill_capability_projection_status() -> dict[str, Any]:
    try:
        from runtime_container.cli_skill_capability_projection import (
            build_default_cli_skill_capability_projection_status_summary,
            cli_skill_capability_projection_status_summary_status_dict,
        )

        return cli_skill_capability_projection_status_summary_status_dict(
            build_default_cli_skill_capability_projection_status_summary()
        )
    except Exception as exc:
        return {
            "status": "candidate_summary_unavailable",
            "source": "runtime_container.cli_skill_capability_projection",
            "projection_count": 0,
            "workflow_slot_reference_count": 0,
            "active_slot_reference_count": 0,
            "blocked_slot_reference_count": 0,
            "projection_refs": [],
            "workflow_slot_refs": [],
            "workflow_names": [],
            "skill_ids": [],
            "capability_ids": [],
            "reference_modes": [],
            "allowed_use_summary": {},
            "forbidden_use_summary": {},
            "evidence_refs": [],
            "runtime_enabled": False,
            "skill_file_loading_enabled": False,
            "resources_loading_enabled": False,
            "scripts_execution_enabled": False,
            "tool_exposure_enabled": False,
            "agent_runtime_enabled": False,
            "prompt_context_enabled": False,
            "public_schema_enabled": False,
            "metadata": {
                "candidate_only": True,
                "reference_only": True,
                "unavailable_error_type": type(exc).__name__,
            },
        }


def _chat_latest_plan_status(
    latest_plan_result: CliPlanWorkflowResultCandidate | None,
) -> dict[str, Any]:
    if latest_plan_result is None:
        return {
            "status": "not_run",
            "reference_context_status": "not_run",
            "reference_evidence_ref_count": 0,
            "workspace_created": False,
            "workspace_ref": None,
            "workspace_artifact_ref_count": 0,
            "workspace_result_ref_count": 0,
        }
    reference_context = latest_plan_result.reference_context
    workspace = latest_plan_result.run_workspace
    return {
        "status": _chat_plan_result_status(latest_plan_result),
        "reference_context_status": (
            reference_context.status if reference_context is not None else "not_run"
        ),
        "reference_evidence_ref_count": (
            len(reference_context.evidence_refs)
            if reference_context is not None
            else 0
        ),
        "workspace_created": bool(
            workspace is not None and workspace.workspace_created
        ),
        "workspace_ref": workspace.workspace_ref if workspace is not None else None,
        "workspace_artifact_ref_count": (
            len(workspace.artifact_refs) if workspace is not None else 0
        ),
        "workspace_result_ref_count": (
            len(workspace.result_refs) if workspace is not None else 0
        ),
    }


def _chat_plan_result_status(
    plan_result: CliPlanWorkflowResultCandidate,
) -> str:
    if plan_result.fail_safe:
        return "failed" if not plan_result.no_live else "blocked"
    if plan_result.no_live:
        return "no_live_boundary"
    return "succeeded" if plan_result.quality_review else "triggered"


def _chat_status_csv(values: Sequence[Any]) -> str:
    normalized = [str(value) for value in values if str(value)]
    return ", ".join(normalized) if normalized else "none"


def _chat_plan_manual_control_missing_governance(
    args: argparse.Namespace,
) -> list[str]:
    missing: list[str] = []
    if args.operator_approved is not True:
        missing.append("--operator-approved")
    if not args.approval_ref:
        missing.append("--approval-ref")
    if not args.audit_ref:
        missing.append("--audit-ref")
    if not args.sanitized_evidence_ref:
        missing.append("--sanitized-evidence-ref")
    if not args.governance_summary_output_ref:
        missing.append("--governance-summary-output-ref")
    return missing


def _chat_plan_control_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    config_context = _chat_plan_runtime_config_context(args)
    tool_exposure = getattr(config_context, "tool_exposure", None)
    run_workspace = getattr(config_context, "run_workspace", None)

    profile_name = (
        args.tool_exposure_profile
        or getattr(tool_exposure, "default_profile", None)
        or "readonly_reference"
    )
    profile_config = (
        tool_exposure.to_profile_config() if tool_exposure is not None else None
    )
    workspace_config_kwargs = (
        run_workspace.to_policy_kwargs() if run_workspace is not None else {}
    )
    workspace_enabled = bool(
        _chat_plan_workspace_args_requested(args)
        or getattr(run_workspace, "enabled_by_default", False)
    )
    workspace_root = _chat_plan_workspace_root(
        args,
        configured_root=workspace_config_kwargs.get("workspace_root"),
    )
    if not workspace_enabled:
        workspace_root = None

    cli_explicit_args: dict[str, Any] = {}
    if args.tool_exposure_profile:
        cli_explicit_args["profile_name"] = args.tool_exposure_profile

    return {
        "reference_paths": tuple(args.reference_paths),
        "reference_repo_root": str(_chat_plan_repo_root(args.config_root)),
        "reference_profile_name": profile_name,
        "reference_profile_config": profile_config,
        "reference_cli_explicit_args": cli_explicit_args,
        "run_workspace_root": workspace_root,
        "run_workspace_enabled": workspace_enabled,
        "run_workspace_retention_policy": (
            args.run_workspace_retention_policy
            or str(workspace_config_kwargs.get("retention_policy") or "keep")
        ),
        "run_workspace_cleanup_policy": (
            args.run_workspace_cleanup_policy
            or str(workspace_config_kwargs.get("cleanup_policy") or "manual")
        ),
        "run_workspace_max_write_bytes": (
            args.run_workspace_max_write_bytes
            or int(workspace_config_kwargs.get("max_write_bytes") or 65536)
        ),
        "metadata": {
            "manual_reference_paths_requested": bool(args.reference_paths),
            "manual_run_workspace_requested": _chat_plan_workspace_args_requested(
                args
            ),
            "tool_exposure_profile_source": (
                "cli_explicit_args"
                if args.tool_exposure_profile
                else (
                    "profile_config"
                    if tool_exposure is not None
                    else "default_values"
                )
            ),
            "run_workspace_config_source": (
                "cli_explicit_args"
                if _chat_plan_workspace_args_requested(args)
                else (
                    "profile_config"
                    if getattr(run_workspace, "enabled_by_default", False)
                    else "default_values"
                )
            ),
        },
    }


def _chat_plan_runtime_config_context(args: argparse.Namespace) -> Any | None:
    if getattr(args, "_chat_plan_runtime_config_context_resolved", False):
        return getattr(args, "_chat_plan_runtime_config_context", None)
    try:
        from composition.runtime import (
            RuntimeCompositionOptions,
            build_runtime_config_context,
        )

        config_context = build_runtime_config_context(
            RuntimeCompositionOptions(
                config_root=args.config_root,
                environment=args.environment,
            )
        )
        args._chat_plan_runtime_config_context = config_context
        args._chat_plan_runtime_config_context_resolved = True
        return config_context
    except Exception:
        if _chat_plan_manual_controls_requested(args):
            raise
        args._chat_plan_runtime_config_context = None
        args._chat_plan_runtime_config_context_resolved = True
        return None


def _chat_plan_workspace_root(
    args: argparse.Namespace,
    *,
    configured_root: Any,
) -> str | None:
    if args.run_workspace_root is not None:
        return str(args.run_workspace_root)
    if configured_root:
        root = Path(str(configured_root)).expanduser()
        if not root.is_absolute():
            root = _chat_plan_repo_root(args.config_root) / root
        return str(root)
    return None


def _chat_plan_repo_root(config_root: Path) -> Path:
    root = Path(config_root).expanduser()
    if root.name == "config":
        return root.parent.resolve()
    return Path.cwd().resolve()


def _chat_input_payload(
    *,
    input_summary: str,
    chat_session_id: str,
    turn_index: int,
    history: Sequence[Mapping[str, str]],
    history_limit: int,
) -> dict[str, Any]:
    if history_limit == 0:
        history_summary: list[str] = []
    else:
        history_summary = list(history[-history_limit:])
    return {
        "input_summary": input_summary,
        "chat_session_id": chat_session_id,
        "turn_index": turn_index,
        "turn_history_summary": history_summary,
    }


def _chat_history_entry(*, user_text: str, assistant_text: str) -> dict[str, str]:
    return {
        "user": _normalize_chat_history_text(user_text),
        "assistant": _normalize_chat_history_text(assistant_text),
    }


def _normalize_chat_history_text(value: str, *, limit: int = 240) -> str:
    normalized = " ".join(value.strip().split())
    if len(normalized) > limit:
        return normalized[:limit]
    return normalized


def _run_chat_turn(
    args: argparse.Namespace,
    *,
    input_payload: Mapping[str, Any],
    entry_runner: EntryRunner,
    request_builder: RequestBuilder,
) -> tuple[int, dict[str, Any] | None, Mapping[str, Any] | None]:
    _apply_run_defaults(args)
    blocking_reasons = _cli_blocking_reasons(args)
    if blocking_reasons:
        output = _blocking_output(args, blocking_reasons)
        output["exit_code"] = EXIT_BLOCKING
        return EXIT_BLOCKING, output, None

    try:
        request = request_builder(args, input_payload)
        entry_result = dict(entry_runner(request))
    except Exception as exc:  # pragma: no cover - defensive runtime boundary.
        print(f"cognition chat runtime error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_FAILURE, None, None

    output = _cli_output_from_entry_result(args, entry_result)
    if _violates_output_boundary(output):
        print("cognition chat output boundary violation", file=sys.stderr)
        return EXIT_OUTPUT_BOUNDARY_FAILURE, None, None

    if output["blocking_reasons"]:
        exit_code = EXIT_BLOCKING
    elif output["execution_performed"] is True:
        exit_code = EXIT_OK
    else:
        exit_code = EXIT_RUNTIME_FAILURE
    output["exit_code"] = exit_code
    return exit_code, output, entry_result


def _assistant_text_from_chat_turn(
    output: Mapping[str, Any],
    entry_result: Mapping[str, Any] | None,
) -> str:
    if output.get("live_llm_call_performed") is True:
        preview = _find_sanitized_response_preview(entry_result)
        if preview:
            return _normalize_chat_assistant_preview(preview)
        return CHAT_LIVE_NO_PREVIEW_MESSAGE
    return CHAT_NO_LIVE_ASSISTANT_MESSAGE


def _normalize_chat_assistant_preview(preview: str) -> str:
    normalized = preview.strip()
    if not normalized:
        return normalized
    try:
        decoded = json.loads(normalized)
    except json.JSONDecodeError:
        return normalized
    if isinstance(decoded, Mapping):
        for key in ("response", "answer", "content"):
            value = decoded.get(key)
            if isinstance(value, str) and value.strip():
                return " ".join(value.strip().split())
    return normalized


def _find_sanitized_response_preview(value: Any) -> str | None:
    if isinstance(value, Mapping):
        display = value.get("sanitized_response_display")
        if isinstance(display, str) and display.strip():
            return display.strip()
        preview = value.get("sanitized_response_preview")
        if isinstance(preview, str) and preview.strip():
            return preview.strip()
        for nested in value.values():
            found = _find_sanitized_response_preview(nested)
            if found:
                return found
    elif isinstance(value, list | tuple):
        for item in value:
            found = _find_sanitized_response_preview(item)
            if found:
                return found
    return None


def _chat_turn_text_output(
    output: Mapping[str, Any],
    assistant_text: str,
    turn_index: int,
) -> str:
    lines = [
        f"assistant: {assistant_text}",
        f"status: {output['status']}",
        f"turn: {turn_index}",
        f"live_llm_call_performed: {str(output['live_llm_call_performed']).lower()}",
        f"ollama_call_performed: {str(output['ollama_call_performed']).lower()}",
    ]
    blocking_reasons = output.get("blocking_reasons") or []
    warnings = output.get("warnings") or []
    if blocking_reasons:
        lines.append("blocking_reasons: " + ", ".join(map(str, blocking_reasons)))
    if warnings:
        lines.append("warnings: " + ", ".join(map(str, warnings)))
    return "\n".join(lines)


def _default_request_builder(
    args: argparse.Namespace,
    input_payload: Mapping[str, Any],
) -> "ControlledAdkRunRequest":
    from runtime_container.controlled_adk_run_request_builder import (
        ControlledAdkRunRequestBuildInput,
        build_controlled_adk_run_request_from_registry,
    )
    from runtime_container.workflow_registry import build_default_workflow_registry

    return build_controlled_adk_run_request_from_registry(
        build_input=ControlledAdkRunRequestBuildInput(
            config_root=args.config_root,
            environment=args.environment,
            profile=args.profile,
            runtime_id=args.runtime_id,
            invocation_id=args.invocation_id,
            workflow_id=args.workflow_id,
            workflow_name=args.workflow_name,
            input_payload=dict(input_payload),
            operator_approved=args.operator_approved,
            approval_ref=args.approval_ref,
            audit_ref=args.audit_ref,
            sanitized_evidence_ref=args.sanitized_evidence_ref,
            governance_summary_output_ref=args.governance_summary_output_ref,
            request_live_llm=args.request_live_llm,
            request_ollama=args.request_ollama,
            allow_live_llm=args.allow_live_llm,
            allow_ollama=args.allow_ollama,
            live_llm_approval_ref=args.live_llm_approval_ref,
            llm_invocation_service=_default_llm_invocation_service(args),
        ),
        workflow_registry=build_default_workflow_registry(
            runtime_assembly_provider=_default_runtime_assembly_provider()
        ),
    )


def _default_entry_runner(request: "ControlledAdkRunRequest") -> Mapping[str, Any]:
    from runtime_container.controlled_adk_run_entry import (
        run_productized_controlled_adk_run,
    )

    return run_productized_controlled_adk_run(request)


@contextmanager
def _known_cli_warning_discipline() -> Iterator[None]:
    with warnings.catch_warnings():
        litellm_logger = logging.getLogger("LiteLLM")
        litellm_previous_level = litellm_logger.level
        litellm_logger.setLevel(logging.ERROR)
        try:
            from authlib.deprecate import AuthlibDeprecationWarning
        except ImportError:
            warnings.filterwarnings(
                "ignore",
                message=r"authlib\.jose module is deprecated.*",
                category=Warning,
            )
        else:
            warnings.filterwarnings("ignore", category=AuthlibDeprecationWarning)
        warnings.filterwarnings(
            "ignore",
            message=(
                r"\[EXPERIMENTAL\] feature FeatureName\."
                r"(?:PLUGGABLE_AUTH|TOOL_CONFIRMATION) is enabled\."
            ),
            category=UserWarning,
        )
        try:
            yield
        finally:
            litellm_logger.setLevel(litellm_previous_level)


def _default_runtime_assembly_provider() -> Callable[[Any], Any]:
    from composition.controlled_adk_run_provider import (
        build_controlled_adk_run_runtime_assembly_provider,
    )

    return build_controlled_adk_run_runtime_assembly_provider()


def _default_llm_invocation_service(args: argparse.Namespace | None = None) -> Any:
    if args is not None and _full_controlled_live_args(args):
        from composition.llm_invocation_assembly import (
            build_controlled_live_adk_governed_llm_invocation_service_from_runtime_config,
        )
        from composition.runtime import (
            RuntimeCompositionOptions,
            build_runtime_config_context,
        )

        config_context = build_runtime_config_context(
            RuntimeCompositionOptions(
                config_root=args.config_root,
                environment=args.environment,
            )
        )
        chat_live_llm_max_tokens = getattr(args, "chat_live_llm_max_tokens", None)
        live_metadata = {
            "source": "runtime_container.entrypoints.cognition",
            "cli_controlled_live": True,
            "cli_ollama_api_base_override": args.ollama_api_base is not None,
            "cli_timeout_seconds_override": (
                args.live_llm_timeout_seconds is not None
            ),
        }
        if chat_live_llm_max_tokens is not None:
            live_metadata.update(
                {
                    "cli_chat_controlled_live": True,
                    "response_preview_limit": getattr(
                        args,
                        "chat_response_preview_limit",
                        CHAT_RESPONSE_PREVIEW_LIMIT,
                    ),
                }
            )
        return build_controlled_live_adk_governed_llm_invocation_service_from_runtime_config(
            config_context=config_context,
            ollama_api_base=args.ollama_api_base,
            timeout_seconds=args.live_llm_timeout_seconds,
            max_tokens=chat_live_llm_max_tokens,
            metadata=live_metadata,
        )

    from composition.llm_invocation_assembly import (
        build_adk_governed_llm_invocation_service,
    )

    return build_adk_governed_llm_invocation_service()


def _apply_run_defaults(args: argparse.Namespace) -> None:
    if not args.runtime_id:
        args.runtime_id = f"runtime-cli-{uuid.uuid4().hex[:8]}"
    if not args.workflow_name:
        args.workflow_name = DEFAULT_WORKFLOW_NAME
    if not args.workflow_id:
        args.workflow_id = DEFAULT_WORKFLOW_ID
    args.invocation_id = f"inv-{args.runtime_id}"
    if args.json:
        args.format = "json"


def _load_input_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.input_file is not None:
        payload = json.loads(args.input_file.read_text(encoding="utf-8"))
    elif args.input_json is not None:
        payload = json.loads(args.input_json)
    elif args.input_text is not None:
        input_text = args.input_text.strip()
        if not input_text:
            raise ValueError("--input-text must not be blank")
        payload = {"input_summary": input_text}
    else:
        payload = {}
    if not isinstance(payload, dict):
        raise TypeError("input payload must be a JSON object")
    return payload


def _cli_blocking_reasons(args: argparse.Namespace) -> list[str]:
    reasons: list[str] = []
    if args.operator_approved is not True:
        reasons.append("operator_approval_not_true")
    if not args.approval_ref:
        reasons.append("operator_approval_ref_missing")
    if not args.audit_ref:
        reasons.append("audit_ref_missing")
    if not args.sanitized_evidence_ref:
        reasons.append("sanitized_evidence_ref_missing")
    if not args.governance_summary_output_ref:
        reasons.append("governance_summary_output_ref_missing")
    reasons.extend(_controlled_live_blocking_reasons(args))
    return reasons


def _controlled_live_blocking_reasons(args: argparse.Namespace) -> list[str]:
    if not _controlled_live_args_present(args):
        return []

    reasons: list[str] = []
    if args.request_live_llm is not True:
        reasons.append("controlled_live_request_live_llm_missing")
    if args.request_ollama is not True:
        reasons.append("controlled_live_request_ollama_missing")
    if args.allow_live_llm is not True:
        reasons.append("controlled_live_allow_live_llm_missing")
    if args.allow_ollama is not True:
        reasons.append("controlled_live_allow_ollama_missing")
    if not args.live_llm_approval_ref:
        reasons.append("controlled_live_llm_approval_ref_missing")
    if (
        args.live_llm_timeout_seconds is not None
        and args.live_llm_timeout_seconds <= 0
    ):
        reasons.append("controlled_live_timeout_seconds_not_positive")
    return reasons


def _controlled_live_args_present(args: argparse.Namespace) -> bool:
    return any(
        (
            args.request_live_llm,
            args.request_ollama,
            args.allow_live_llm,
            args.allow_ollama,
            bool(args.live_llm_approval_ref),
            bool(args.ollama_api_base),
            args.live_llm_timeout_seconds is not None,
        )
    )


def _full_controlled_live_args(args: argparse.Namespace) -> bool:
    return (
        args.request_live_llm is True
        and args.request_ollama is True
        and args.allow_live_llm is True
        and args.allow_ollama is True
        and bool(args.live_llm_approval_ref)
        and (
            args.live_llm_timeout_seconds is None
            or args.live_llm_timeout_seconds > 0
        )
    )


def _preflight_only_output(
    args: argparse.Namespace,
    blocking_reasons: Sequence[str],
) -> dict[str, Any]:
    return _base_cli_output(
        args,
        status="blocked" if blocking_reasons else "preflight_allowed",
        adk_run_allowed=not blocking_reasons,
        adk_run_performed=False,
        execution_performed=False,
        blocking_reasons=list(blocking_reasons),
        warnings=["preflight_only_runtime_not_executed"],
        final_preflight={
            "allowed": not blocking_reasons,
            "execution_scope": "cognition_internal_cli_preflight",
            "blocking_reasons": list(blocking_reasons),
            "runtime_not_executed": True,
        },
    )


def _blocking_output(
    args: argparse.Namespace,
    blocking_reasons: Sequence[str],
) -> dict[str, Any]:
    return _base_cli_output(
        args,
        status="blocked",
        adk_run_allowed=False,
        adk_run_performed=False,
        execution_performed=False,
        blocking_reasons=list(blocking_reasons),
        warnings=[],
        final_preflight={
            "allowed": False,
            "execution_scope": "cognition_internal_cli",
            "blocking_reasons": list(blocking_reasons),
            "runtime_not_executed": True,
        },
    )


def _cli_output_from_entry_result(
    args: argparse.Namespace,
    entry_result: Mapping[str, Any],
) -> dict[str, Any]:
    output = _base_cli_output(
        args,
        status=_entry_status(entry_result),
        adk_run_allowed=bool(entry_result.get("adk_run_allowed")),
        adk_run_performed=bool(entry_result.get("adk_run_performed")),
        execution_performed=bool(entry_result.get("execution_performed")),
        blocking_reasons=list(entry_result.get("blocking_reasons") or []),
        warnings=list(entry_result.get("warnings") or []),
        final_preflight=_safe_mapping(entry_result.get("final_preflight")),
    )
    output["live_llm_call_performed"] = bool(
        entry_result.get("live_llm_call_performed", False)
    )
    output["ollama_call_performed"] = bool(
        entry_result.get("ollama_call_performed", False)
    )
    output["invocation_id"] = entry_result.get("invocation_id") or args.invocation_id
    output["lifecycle_facts"] = entry_result.get("lifecycle_facts")
    output["run_config_service_bundle_facts"] = entry_result.get(
        "run_config_service_bundle_facts"
    )
    output["governance_summary_payload_ref"] = entry_result.get(
        "governance_summary_payload_ref"
    ) or entry_result.get("governance_summary_output_ref")
    output["llm_invocation_result_ref"] = entry_result.get(
        "llm_invocation_result_ref"
    )
    output["llm_invocation_observation_ref"] = entry_result.get(
        "llm_invocation_observation_ref"
    )
    output["llm_invocation_summary_ref"] = entry_result.get(
        "llm_invocation_summary_ref"
    )
    output["llm_invocation_call_allowed"] = bool(
        entry_result.get("llm_invocation_call_allowed", False)
    )
    output["llm_invocation_call_attempted"] = bool(
        entry_result.get("llm_invocation_call_attempted", False)
    )
    output["llm_invocation_runtime_call_performed"] = bool(
        entry_result.get("llm_invocation_runtime_call_performed", False)
    )
    output["llm_invocation_failure_type"] = entry_result.get(
        "llm_invocation_failure_type"
    )
    output["tool_evidence_ref"] = entry_result.get("tool_evidence_ref")
    output["tool_run_ref"] = entry_result.get("tool_run_ref")
    output["tool_status"] = entry_result.get("tool_status")
    output["tool_failure_type"] = entry_result.get("tool_failure_type")
    output["tool_runtime_call_performed"] = bool(
        entry_result.get("tool_runtime_call_performed", False)
    )
    output["controlled_live_llm_preflight"] = entry_result.get(
        "controlled_live_llm_preflight"
    )
    output["sanitized_evidence_ref"] = entry_result.get(
        "sanitized_evidence_ref"
    ) or args.sanitized_evidence_ref
    output["audit_ref"] = entry_result.get("audit_ref") or args.audit_ref
    return _whitelist_output(output)


def _base_cli_output(
    args: argparse.Namespace,
    *,
    status: str,
    adk_run_allowed: bool,
    adk_run_performed: bool,
    execution_performed: bool,
    blocking_reasons: list[str],
    warnings: list[str],
    final_preflight: Mapping[str, Any],
) -> dict[str, Any]:
    return _whitelist_output(
        {
            "product": PRODUCT_NAME,
            "command": "cognition run",
            "execution_mode": "cognition_internal_cli_controlled_run",
            "runtime_id": args.runtime_id,
            "invocation_id": args.invocation_id,
            "workflow_id": args.workflow_id,
            "workflow_name": args.workflow_name,
            "adk_run_allowed": adk_run_allowed,
            "adk_run_performed": adk_run_performed,
            "execution_performed": execution_performed,
            "live_llm_call_performed": False,
            "ollama_call_performed": False,
            "blocking_reasons": blocking_reasons,
            "warnings": warnings,
            "final_preflight": dict(final_preflight),
            "lifecycle_facts": None,
            "run_config_service_bundle_facts": None,
            "governance_summary_payload_ref": args.governance_summary_output_ref,
            "llm_invocation_result_ref": None,
            "llm_invocation_observation_ref": None,
            "llm_invocation_summary_ref": None,
            "llm_invocation_call_allowed": False,
            "llm_invocation_call_attempted": False,
            "llm_invocation_runtime_call_performed": False,
            "llm_invocation_failure_type": None,
            "controlled_live_llm_preflight": None,
            "sanitized_evidence_ref": args.sanitized_evidence_ref,
            "audit_ref": args.audit_ref,
            "output_ref": str(args.output) if args.output else None,
            "status": status,
            "exit_code": EXIT_BLOCKING if blocking_reasons else EXIT_OK,
        }
    )


def _emit_run_output(
    args: argparse.Namespace,
    output: Mapping[str, Any],
    *,
    exit_code: int,
) -> int:
    if _violates_output_boundary(output):
        print("cognition run output boundary violation", file=sys.stderr)
        return EXIT_OUTPUT_BOUNDARY_FAILURE
    if args.output is not None:
        try:
            args.output.write_text(
                json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            print(f"cognition run output error: {exc}", file=sys.stderr)
            return EXIT_OUTPUT_WRITE_FAILURE

    if args.format == "json":
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    else:
        print(_run_text_output(output))
    return exit_code


def _run_text_output(output: Mapping[str, Any]) -> str:
    lines = [
        f"{PRODUCT_NAME}",
        f"status: {output['status']}",
        f"runtime_id: {output['runtime_id']}",
        f"workflow_id: {output['workflow_id']}",
        f"adk_run_allowed: {str(output['adk_run_allowed']).lower()}",
        f"adk_run_performed: {str(output['adk_run_performed']).lower()}",
        f"execution_performed: {str(output['execution_performed']).lower()}",
        f"live_llm_call_performed: {str(output['live_llm_call_performed']).lower()}",
        f"ollama_call_performed: {str(output['ollama_call_performed']).lower()}",
        "llm_invocation_call_allowed: "
        f"{str(output['llm_invocation_call_allowed']).lower()}",
        "llm_invocation_call_attempted: "
        f"{str(output['llm_invocation_call_attempted']).lower()}",
        "llm_invocation_runtime_call_performed: "
        f"{str(output['llm_invocation_runtime_call_performed']).lower()}",
    ]
    if output.get("llm_invocation_failure_type"):
        lines.append(
            f"llm_invocation_failure_type: {output['llm_invocation_failure_type']}"
        )
    controlled_live_preflight = output.get("controlled_live_llm_preflight") or {}
    if controlled_live_preflight:
        lines.append(
            "controlled_live_llm_preflight_allowed: "
            f"{str(controlled_live_preflight.get('allowed', False)).lower()}"
        )
    blocking_reasons = output.get("blocking_reasons") or []
    warnings = output.get("warnings") or []
    if blocking_reasons:
        lines.append("blocking_reasons: " + ", ".join(map(str, blocking_reasons)))
    if warnings:
        lines.append("warnings: " + ", ".join(map(str, warnings)))
    return "\n".join(lines)


def _startup_status() -> dict[str, Any]:
    return {
        "product": PRODUCT_NAME,
        "definition": PRODUCT_DEFINITION,
        "cli": CLI_COMMAND,
        "backend": BACKEND,
        "agent_framework": AGENT_FRAMEWORK,
        "adapter": ADAPTER,
        "mode": MODE,
        "governance": "enabled",
        "evidence": "enabled",
        "workspace": str(Path.cwd()),
        "session": "not-created",
        "available_commands": [
            "cognition run",
            "cognition chat",
            "cognition config init",
        ],
    }


def _startup_text(status: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            str(status["product"]),
            PRODUCT_DEFINITION,
            "",
            f"CLI: {status['cli']}",
            f"Backend: {status['backend']}",
            f"Agent Framework: {status['agent_framework']}",
            f"Adapter: {status['adapter']}",
            f"Mode: {status['mode']}",
            f"Governance: {status['governance']}",
            f"Evidence: {status['evidence']}",
            f"Workspace: {status['workspace']}",
            f"Session: {status['session']}",
            "",
            "Available commands:",
            "  cognition run",
            "  cognition chat",
            "  cognition config init",
        ]
    )


def _entry_status(entry_result: Mapping[str, Any]) -> str:
    if entry_result.get("blocking_reasons"):
        return "blocked"
    if entry_result.get("execution_performed") is True:
        return "succeeded"
    return "failed"


def _whitelist_output(output: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: _sanitize_value(value)
        for key, value in output.items()
        if key in ALLOWED_TOP_LEVEL_FIELDS and key not in FORBIDDEN_TOP_LEVEL_FIELDS
    }


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _sanitize_value(nested)
            for key, nested in value.items()
            if str(key) not in FORBIDDEN_TOP_LEVEL_FIELDS
        }
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_value(item) for item in value]
    return value


def _violates_output_boundary(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in FORBIDDEN_TOP_LEVEL_FIELDS:
                return True
            if _violates_output_boundary(nested):
                return True
    elif isinstance(value, list | tuple):
        return any(_violates_output_boundary(item) for item in value)
    return False


def _safe_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _exit_code(code: object) -> int:
    if isinstance(code, int):
        return code
    if code is None:
        return EXIT_OK
    return EXIT_USAGE_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
