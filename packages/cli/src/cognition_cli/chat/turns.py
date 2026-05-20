"""Chat turn construction and default run fallback for the Cognition System CLI."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from typing import Any

from cognition_cli.constants import (
    CHAT_LIVE_LLM_MAX_TOKENS,
    CHAT_RESPONSE_PREVIEW_LIMIT,
    EXIT_BLOCKING,
    EXIT_OK,
    EXIT_OUTPUT_BOUNDARY_FAILURE,
    EXIT_RUNTIME_FAILURE,
)
from cognition_cli.output_boundary import (
    violates_output_boundary as _violates_output_boundary,
)
from cognition_cli.run.controls import (
    _apply_run_defaults,
    _cli_blocking_reasons,
)
from cognition_cli.run.output import (
    _blocking_output,
    _cli_output_from_entry_result,
)
from cognition_cli.run.gateway import _run_via_product_gateway
from cognition_cli.services.runtime import (
    EntryRunner,
    RequestBuilder,
    RunGatewayExecutor,
)


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
        external_readonly_evidence_paths=tuple(
            getattr(args, "external_readonly_evidence_paths", ())
        ),
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


def _chat_input_payload(
    *,
    input_summary: str,
    chat_session_id: str,
    turn_index: int,
    history: Sequence[Mapping[str, str]],
    history_limit: int,
) -> dict[str, Any]:
    if history_limit == 0:
        history_summary: list[Mapping[str, str]] = []
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
    entry_runner: EntryRunner | None,
    request_builder: RequestBuilder | None,
    use_gateway_entry: bool = False,
    run_gateway_executor: RunGatewayExecutor | None = None,
) -> tuple[int, dict[str, Any] | None, Mapping[str, Any] | None]:
    _apply_run_defaults(args)
    blocking_reasons = _cli_blocking_reasons(args)
    if blocking_reasons:
        output = _blocking_output(args, blocking_reasons)
        output["exit_code"] = EXIT_BLOCKING
        return EXIT_BLOCKING, output, None

    try:
        if use_gateway_entry:
            entry_result = _run_via_product_gateway(
                args,
                input_payload,
                entry_runner=entry_runner,
                run_gateway_executor=run_gateway_executor,
            )
        else:
            if entry_runner is None or request_builder is None:
                raise ValueError(
                    "entry_runner and request_builder are required for "
                    "direct test execution."
                )
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
