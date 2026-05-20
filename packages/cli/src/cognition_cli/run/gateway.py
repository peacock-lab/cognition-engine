"""Product gateway execution adapter for the CLI run channel."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from typing import Any

from product_gateway.cognition_run import execute_cognition_run_gateway_request

from cognition_cli.services.runtime import RunGatewayExecutor


def _run_via_product_gateway(
    args: argparse.Namespace,
    input_payload: Mapping[str, Any],
    *,
    entry_runner: Any | None = None,
    run_gateway_executor: RunGatewayExecutor | None = None,
) -> dict[str, Any]:
    """Execute the default run path through product_gateway."""

    gateway_input = {
        "request_id": args.invocation_id,
        "runtime_id": args.runtime_id,
        "config_root": str(args.config_root),
        "workflow_id": args.workflow_id,
        "workflow_name": args.workflow_name,
        "environment": args.environment,
        "profile": args.profile,
        "input_payload": _product_gateway_input_payload(input_payload),
        "operator_approved": args.operator_approved,
        "approval_ref": args.approval_ref,
        "audit_ref": args.audit_ref,
        "sanitized_evidence_ref": args.sanitized_evidence_ref,
        "governance_summary_output_ref": args.governance_summary_output_ref,
        "request_live_llm": args.request_live_llm,
        "request_ollama": args.request_ollama,
        "allow_live_llm": args.allow_live_llm,
        "allow_ollama": args.allow_ollama,
        "live_llm_approval_ref": args.live_llm_approval_ref,
        "ollama_api_base": args.ollama_api_base,
        "live_llm_timeout_seconds": args.live_llm_timeout_seconds,
        "live_llm_max_tokens": getattr(args, "chat_live_llm_max_tokens", None),
        "response_preview_limit": getattr(
            args,
            "chat_response_preview_limit",
            None,
        ),
        "metadata": {
            "source": "cognition_cli.run.gateway",
            "cli_command": "cognition run",
        },
    }
    if run_gateway_executor is None:
        execution_result = execute_cognition_run_gateway_request(gateway_input)
    else:
        execution_result = run_gateway_executor(
            gateway_input,
            entry_runner=entry_runner,
        )
    runtime_mapping = execution_result.runtime_summary.to_runtime_mapping()
    runtime_mapping["product_response_summary"] = (
        execution_result.product_response_summary
    )
    return runtime_mapping


def _product_gateway_input_payload(
    input_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Convert CLI-friendly input aliases into product-gateway-safe keys."""

    payload = dict(input_payload)
    message = payload.pop("message", None)
    if "input_summary" not in payload and isinstance(message, str):
        payload["input_summary"] = message
    elif message is not None:
        payload["message_omitted_by_product_gateway_boundary"] = True
    return payload
