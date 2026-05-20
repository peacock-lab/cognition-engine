"""Run command output assembly and presentation for the Cognition System CLI."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from typing import Any

from cognition_cli.constants import (
    EXIT_BLOCKING,
    EXIT_OK,
    EXIT_OUTPUT_BOUNDARY_FAILURE,
    EXIT_OUTPUT_WRITE_FAILURE,
    PRODUCT_NAME,
)
from cognition_cli.output_boundary import (
    safe_mapping as _safe_mapping,
    violates_output_boundary as _violates_output_boundary,
    whitelist_output as _whitelist_output,
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
    if "product_response_summary" in entry_result:
        output["product_response_summary"] = entry_result.get(
            "product_response_summary"
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


def _entry_status(entry_result: Mapping[str, Any]) -> str:
    if entry_result.get("blocking_reasons"):
        return "blocked"
    if entry_result.get("execution_performed") is True:
        return "succeeded"
    return "failed"
