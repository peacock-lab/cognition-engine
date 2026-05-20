"""External-readonly fetch CLI channel."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from cognition_cli.constants import (
    EXIT_BLOCKING,
    EXIT_OUTPUT_BOUNDARY_FAILURE,
    EXIT_RUNTIME_FAILURE,
    EXIT_OK,
    PRODUCT_NAME,
)
from contract_core.external_readonly_archive import (
    EXTERNAL_READONLY_FETCH_ARCHIVE_CONTROLLED_ROOT,
    EXTERNAL_READONLY_FETCH_ARCHIVE_FORBIDDEN_OUTPUT_KEYS,
    EXTERNAL_READONLY_FETCH_ARCHIVE_REF_PREFIX,
    build_external_readonly_fetch_evidence_archive,
    external_readonly_fetch_evidence_output_blocked_payload,
    external_readonly_fetch_evidence_ref_for_output,
    external_readonly_fetch_output_boundary_violated,
    preview_external_readonly_text,
    sanitize_external_readonly_fetch_output,
    validate_external_readonly_fetch_evidence_output_path as validate_archive_path,
)
from external_readonly.governed_summary_facts import (
    build_external_readonly_governed_summary_facts,
    external_readonly_governed_summary_facts_status_dict,
)
from product_gateway.external_readonly import (
    execute_external_readonly_fetch_gateway_request,
)


REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION = "同意外部只读抓取"
EXTERNAL_READONLY_FETCH_COMMAND = "cognition external-readonly fetch"
EXTERNAL_READONLY_FETCH_EXECUTION_MODE = "external_readonly_cli_fetch"
EXTERNAL_READONLY_FETCH_SOURCE = "cognition_cli.external_readonly.fetch"
EXTERNAL_READONLY_FETCH_FAILURE = "external_readonly_fetch_cli_failure"
CONTROLLED_EXTERNAL_READONLY_FETCH_EVIDENCE_ROOT = (
    EXTERNAL_READONLY_FETCH_ARCHIVE_CONTROLLED_ROOT
)
CONTROLLED_EXTERNAL_READONLY_FETCH_EVIDENCE_REF_PREFIX = (
    EXTERNAL_READONLY_FETCH_ARCHIVE_REF_PREFIX
)

ExternalReadonlyFetchExecutor = Callable[[Mapping[str, Any]], Any]

FORBIDDEN_EXTERNAL_READONLY_CLI_OUTPUT_KEYS = (
    EXTERNAL_READONLY_FETCH_ARCHIVE_FORBIDDEN_OUTPUT_KEYS
)


def external_readonly_fetch_command(
    args: argparse.Namespace,
    *,
    executor: ExternalReadonlyFetchExecutor | None = None,
) -> int:
    """Run the external-readonly fetch CLI channel."""

    if not _natural_language_confirmation_satisfied(args):
        output = _blocked_confirmation_output(args)
        return _finalize_external_readonly_fetch_output(args, output)

    evidence_output_issue = _evidence_output_preflight_issue(args)
    if evidence_output_issue:
        output = _blocked_evidence_output_preflight_output(
            args,
            issue=evidence_output_issue,
        )
        return _emit_external_readonly_fetch_output(
            args,
            output,
            exit_code=EXIT_BLOCKING,
        )

    try:
        execution = (executor or execute_external_readonly_fetch_gateway_request)(
            _gateway_input_from_args(args)
        )
    except Exception as exc:  # pragma: no cover - defensive product boundary.
        print(f"{EXTERNAL_READONLY_FETCH_COMMAND} error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_FAILURE

    output = _output_from_execution(args, execution)
    if _violates_external_readonly_fetch_output_boundary(output):
        print(
            f"{EXTERNAL_READONLY_FETCH_COMMAND} output boundary violation",
            file=sys.stderr,
        )
        return EXIT_OUTPUT_BOUNDARY_FAILURE

    exit_code = _exit_code_from_output(output)
    output["exit_code"] = exit_code
    return _finalize_external_readonly_fetch_output(args, output)


def write_external_readonly_fetch_evidence(
    output: Mapping[str, Any],
    *,
    root: Path,
    evidence_output: str,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Write sanitized CLI fetch evidence to a controlled JSON output path."""

    archived = build_external_readonly_fetch_evidence_archive(
        output,
        root=root,
        evidence_output=evidence_output,
        overwrite=overwrite,
    )
    if not archived.get("evidence_written"):
        archived.pop("governed_summary_facts", None)
        return archived
    if "governed_summary_facts" not in archived:
        archived["governed_summary_facts"] = _governed_summary_facts_status(
            None,
            evidence_output_path=str(archived.get("evidence_output_path") or ""),
            evidence_written=True,
        )

    relative_path = Path(evidence_output)
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(archived, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return archived


def validate_external_readonly_fetch_evidence_output_path(
    *,
    root: Path,
    evidence_output: str,
    overwrite: bool = False,
) -> str | None:
    """Return a blocking reason if the evidence output path is not controlled."""

    return validate_archive_path(
        root=root,
        evidence_output=evidence_output,
        overwrite=overwrite,
    )


def _gateway_input_from_args(args: argparse.Namespace) -> dict[str, Any]:
    operator_approval_satisfied = bool(
        args.operator_approved
        and args.approval_ref
        and args.runtime_fetch_approval_ref
    )
    controlled_output_satisfied = bool(
        args.controlled_output_ref
        and args.audit_ref
        and args.sanitized_evidence_ref
    )
    gate_passed = bool(
        args.network_gate_open
        and operator_approval_satisfied
        and controlled_output_satisfied
    )
    return {
        "request_id": args.request_id,
        "source_url": args.source_url,
        "envelope_ref": args.envelope_ref,
        "evidence_ref": args.evidence_ref,
        "network_gate": {
            "request_ref": args.request_id,
            "status": "passed" if gate_passed else "blocked",
            "network_gate_open": args.network_gate_open,
            "allowed_for_network_request": args.network_gate_open,
            "operator_approval_satisfied": operator_approval_satisfied,
            "controlled_output_satisfied": controlled_output_satisfied,
            "tool_origin": "url_context",
            "operation_family": "fetch",
            "external_network_call_performed": False,
            "tool_execution_performed": False,
            "metadata": {
                "source": EXTERNAL_READONLY_FETCH_SOURCE,
                "network_gate_ref_present": args.network_gate_open,
                "approval_ref_present": bool(args.approval_ref),
                "audit_ref_present": bool(args.audit_ref),
                "sanitized_evidence_ref_present": bool(
                    args.sanitized_evidence_ref
                ),
            },
        },
        "source_title": args.source_title,
        "controlled_output_ref": args.controlled_output_ref,
        "operator_approved": args.operator_approved,
        "approval_ref": args.approval_ref,
        "audit_ref": args.audit_ref,
        "sanitized_evidence_ref": args.sanitized_evidence_ref,
        "governance_summary_ref": args.governance_summary_ref,
        "allow_runtime_fetch": args.allow_runtime_fetch,
        "runtime_fetch_approval_ref": args.runtime_fetch_approval_ref,
        "use_live_transport": args.use_live_transport,
        "max_bytes": args.max_bytes,
        "max_excerpt_chars": args.max_excerpt_chars,
        "timeout_seconds": args.timeout_seconds,
        "redirect_limit": args.redirect_limit,
        "metadata": {
            "source": EXTERNAL_READONLY_FETCH_SOURCE,
            "cli_command": EXTERNAL_READONLY_FETCH_COMMAND,
            "natural_language_confirmation_satisfied": True,
            "raw_response_included": False,
            "response_headers_included": False,
            "uploads_content": False,
            "writes_files": False,
        },
    }


def _output_from_execution(
    args: argparse.Namespace,
    execution: Any,
) -> dict[str, Any]:
    response = execution.product_response
    runtime_result = getattr(execution, "runtime_result", None)
    metadata = dict(response.metadata or {})
    status = response.status.value
    output = {
        "product": PRODUCT_NAME,
        "command": EXTERNAL_READONLY_FETCH_COMMAND,
        "execution_mode": EXTERNAL_READONLY_FETCH_EXECUTION_MODE,
        "status": status,
        "success": status == "success",
        "failure_type": (
            None if status == "success" else EXTERNAL_READONLY_FETCH_FAILURE
        ),
        "request_id": response.request_id,
        "source_url": args.source_url,
        "operator_approved": bool(args.operator_approved),
        "confirmation_required_text": REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION,
        "natural_language_confirmation_satisfied": True,
        "approval_ref_present": bool(args.approval_ref),
        "runtime_fetch_approval_ref_present": bool(
            args.runtime_fetch_approval_ref
        ),
        "audit_ref_present": bool(args.audit_ref),
        "network_gate_open": bool(args.network_gate_open),
        "allow_runtime_fetch": bool(args.allow_runtime_fetch),
        "use_live_transport": bool(args.use_live_transport),
        "runtime_fetch_performed": bool(
            metadata.get("runtime_fetch_performed", False)
        ),
        "transport_called": bool(metadata.get("transport_called", False)),
        "external_network_call_performed": bool(
            metadata.get("external_network_call_performed", False)
        ),
        "allowed_for_model_context": bool(
            metadata.get("allowed_for_model_context", False)
        ),
        "blocking_reasons": list(response.blocking_reasons),
        "warnings": list(response.warnings),
        "evidence_refs": [ref.ref for ref in response.evidence_refs],
        "runtime": _runtime_summary(runtime_result),
        "raw_response_included": False,
        "raw_html_included": False,
        "response_headers_included": False,
        "uploads_content": False,
        "writes_files": False,
    }
    if args.evidence_output:
        output["governed_summary_facts"] = _governed_summary_facts_status(
            runtime_result,
            evidence_output_path=args.evidence_output,
            evidence_written=True,
        )
    return _sanitize_external_readonly_fetch_output(output)


def _blocked_confirmation_output(args: argparse.Namespace) -> dict[str, Any]:
    return _sanitize_external_readonly_fetch_output(
        {
            "product": PRODUCT_NAME,
            "command": EXTERNAL_READONLY_FETCH_COMMAND,
            "execution_mode": EXTERNAL_READONLY_FETCH_EXECUTION_MODE,
            "status": "blocked",
            "success": False,
            "failure_type": EXTERNAL_READONLY_FETCH_FAILURE,
            "request_id": args.request_id,
            "source_url": args.source_url,
            "operator_approved": bool(args.operator_approved),
            "confirmation_required_text": (
                REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION
            ),
            "natural_language_confirmation_satisfied": False,
            "approval_ref_present": bool(args.approval_ref),
            "runtime_fetch_approval_ref_present": bool(
                args.runtime_fetch_approval_ref
            ),
            "audit_ref_present": bool(args.audit_ref),
            "network_gate_open": bool(args.network_gate_open),
            "allow_runtime_fetch": bool(args.allow_runtime_fetch),
            "use_live_transport": bool(args.use_live_transport),
            "runtime_fetch_performed": False,
            "transport_called": False,
            "external_network_call_performed": False,
            "allowed_for_model_context": False,
            "blocking_reasons": [
                "external_readonly_natural_language_confirmation_required"
            ],
            "warnings": [],
            "evidence_refs": [],
            "runtime": None,
            "raw_response_included": False,
            "raw_html_included": False,
            "response_headers_included": False,
            "uploads_content": False,
            "writes_files": False,
            "exit_code": EXIT_BLOCKING,
        }
    )


def _blocked_evidence_output_preflight_output(
    args: argparse.Namespace,
    *,
    issue: str,
) -> dict[str, Any]:
    return _sanitize_external_readonly_fetch_output(
        {
            "product": PRODUCT_NAME,
            "command": EXTERNAL_READONLY_FETCH_COMMAND,
            "execution_mode": EXTERNAL_READONLY_FETCH_EXECUTION_MODE,
            "status": "blocked",
            "success": False,
            "failure_type": "external_readonly_evidence_output_blocked",
            "request_id": args.request_id,
            "source_url": args.source_url,
            "operator_approved": bool(args.operator_approved),
            "confirmation_required_text": (
                REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION
            ),
            "natural_language_confirmation_satisfied": True,
            "approval_ref_present": bool(args.approval_ref),
            "runtime_fetch_approval_ref_present": bool(
                args.runtime_fetch_approval_ref
            ),
            "audit_ref_present": bool(args.audit_ref),
            "network_gate_open": bool(args.network_gate_open),
            "allow_runtime_fetch": bool(args.allow_runtime_fetch),
            "use_live_transport": bool(args.use_live_transport),
            "runtime_fetch_performed": False,
            "transport_called": False,
            "external_network_call_performed": False,
            "allowed_for_model_context": False,
            "blocking_reasons": [issue],
            "warnings": [],
            "evidence_refs": [],
            "runtime": None,
            "evidence_written": False,
            "evidence_output_path": args.evidence_output,
            "evidence_ref": None,
            "raw_response_included": False,
            "raw_html_included": False,
            "response_headers_included": False,
            "uploads_content": False,
            "writes_files": False,
            "exit_code": EXIT_BLOCKING,
        }
    )


def _runtime_summary(runtime_result: Any | None) -> dict[str, Any] | None:
    if runtime_result is None:
        return None
    envelope = runtime_result.envelope
    item = (
        envelope.model_context_items[0]
        if envelope is not None and envelope.model_context_items
        else {}
    )
    sanitized_excerpt = str(item.get("sanitized_excerpt") or "")
    return {
        "status": runtime_result.status,
        "runtime_fetch_performed": runtime_result.runtime_fetch_performed,
        "transport_called": runtime_result.transport_called,
        "external_network_call_performed": (
            runtime_result.external_network_call_performed
        ),
        "allowed_for_model_context": runtime_result.allowed_for_model_context,
        "blocking_reasons": list(runtime_result.blocking_reasons),
        "warnings": list(runtime_result.warnings),
        "envelope_ref": envelope.envelope_ref if envelope is not None else None,
        "evidence_refs": list(envelope.evidence_refs) if envelope is not None else [],
        "source_urls": list(envelope.source_urls) if envelope is not None else [],
        "total_excerpt_chars": (
            envelope.total_excerpt_chars if envelope is not None else 0
        ),
        "content_hash": item.get("content_hash"),
        "sanitized_excerpt_preview": _preview(sanitized_excerpt),
    }


def _governed_summary_facts_status(
    runtime_result: Any | None,
    *,
    evidence_output_path: str,
    evidence_written: bool,
) -> dict[str, Any]:
    envelope = getattr(runtime_result, "envelope", None)
    reference_review_ready = bool(
        runtime_result is not None
        and getattr(runtime_result, "status", None) == "completed"
        and getattr(runtime_result, "allowed_for_model_context", False) is True
        and evidence_written
    )
    facts = build_external_readonly_governed_summary_facts(
        envelope,
        evidence_output_path=evidence_output_path or None,
        evidence_written=evidence_written,
        reference_review_ready=reference_review_ready,
    )
    return external_readonly_governed_summary_facts_status_dict(facts)


def _natural_language_confirmation_satisfied(args: argparse.Namespace) -> bool:
    return (
        str(args.confirm_external_readonly_fetch or "").strip()
        == REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION
    )


def _emit_external_readonly_fetch_output(
    args: argparse.Namespace,
    output: Mapping[str, Any],
    *,
    exit_code: int,
) -> int:
    if _violates_external_readonly_fetch_output_boundary(output):
        print(
            f"{EXTERNAL_READONLY_FETCH_COMMAND} output boundary violation",
            file=sys.stderr,
        )
        return EXIT_OUTPUT_BOUNDARY_FAILURE

    if args.format == "json" or args.json:
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    else:
        print(_text_output(output))
    return exit_code


def _evidence_output_preflight_issue(args: argparse.Namespace) -> str | None:
    if not args.evidence_output:
        return None
    return validate_external_readonly_fetch_evidence_output_path(
        root=Path.cwd(),
        evidence_output=args.evidence_output,
        overwrite=args.overwrite_evidence_output,
    )


def _finalize_external_readonly_fetch_output(
    args: argparse.Namespace,
    output: Mapping[str, Any],
) -> int:
    payload = dict(output)
    payload["exit_code"] = int(
        payload.get("exit_code") or _exit_code_from_output(payload)
    )
    if args.evidence_output:
        payload = write_external_readonly_fetch_evidence(
            payload,
            root=Path.cwd(),
            evidence_output=args.evidence_output,
            overwrite=args.overwrite_evidence_output,
        )
        payload["exit_code"] = _exit_code_from_output(payload)
    exit_code = int(payload["exit_code"])
    return _emit_external_readonly_fetch_output(args, payload, exit_code=exit_code)


def _text_output(output: Mapping[str, Any]) -> str:
    lines = [
        str(output["product"]),
        f"command: {output['command']}",
        f"status: {output['status']}",
        f"request_id: {output['request_id']}",
        f"source_url: {output['source_url']}",
        "natural_language_confirmation_satisfied: "
        f"{str(output['natural_language_confirmation_satisfied']).lower()}",
        f"network_gate_open: {str(output['network_gate_open']).lower()}",
        f"allow_runtime_fetch: {str(output['allow_runtime_fetch']).lower()}",
        f"use_live_transport: {str(output['use_live_transport']).lower()}",
        "runtime_fetch_performed: "
        f"{str(output['runtime_fetch_performed']).lower()}",
        f"transport_called: {str(output['transport_called']).lower()}",
        "external_network_call_performed: "
        f"{str(output['external_network_call_performed']).lower()}",
        "allowed_for_model_context: "
        f"{str(output['allowed_for_model_context']).lower()}",
    ]
    blocking = output.get("blocking_reasons") or []
    warnings = output.get("warnings") or []
    if blocking:
        lines.append("blocking_reasons: " + ", ".join(map(str, blocking)))
    if warnings:
        lines.append("warnings: " + ", ".join(map(str, warnings)))
    if output.get("evidence_output_path"):
        lines.append(
            f"evidence_written: {str(output.get('evidence_written', False)).lower()}"
        )
        lines.append(f"evidence_output_path: {output['evidence_output_path']}")
    if output.get("evidence_ref"):
        lines.append(f"evidence_ref: {output['evidence_ref']}")
    runtime = output.get("runtime") or {}
    if isinstance(runtime, Mapping) and runtime.get("sanitized_excerpt_preview"):
        lines.append(
            "sanitized_excerpt_preview: "
            f"{runtime['sanitized_excerpt_preview']}"
        )
    return "\n".join(lines)


def _exit_code_from_output(output: Mapping[str, Any]) -> int:
    if output.get("status") == "success":
        return EXIT_OK
    if output.get("status") == "blocked":
        return EXIT_BLOCKING
    return EXIT_RUNTIME_FAILURE


def _sanitize_external_readonly_fetch_output(
    output: Mapping[str, Any],
) -> dict[str, Any]:
    return sanitize_external_readonly_fetch_output(output)


def _violates_external_readonly_fetch_output_boundary(value: Any) -> bool:
    return external_readonly_fetch_output_boundary_violated(value)


def _evidence_output_blocked_payload(
    payload: Mapping[str, Any],
    *,
    evidence_output: str,
    issue: str,
) -> dict[str, Any]:
    return external_readonly_fetch_evidence_output_blocked_payload(
        payload,
        evidence_output=evidence_output,
        issue=issue,
    )


def _evidence_ref_for_output(path: Path) -> str:
    return external_readonly_fetch_evidence_ref_for_output(path)


def _preview(value: str, *, limit: int = 500) -> str:
    return preview_external_readonly_text(value, limit=limit)


__all__ = [
    "CONTROLLED_EXTERNAL_READONLY_FETCH_EVIDENCE_ROOT",
    "REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION",
    "external_readonly_fetch_command",
    "validate_external_readonly_fetch_evidence_output_path",
    "write_external_readonly_fetch_evidence",
]
