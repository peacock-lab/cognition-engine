"""External-readonly governed answer CLI smoke channel."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cognition_cli.constants import (
    EXIT_BLOCKING,
    EXIT_OUTPUT_BOUNDARY_FAILURE,
    EXIT_RUNTIME_FAILURE,
    EXIT_OK,
    PRODUCT_NAME,
)
from cognition_cli.external_readonly.refs import (
    ExternalReadonlyRefsApplicationExecutor,
    build_external_readonly_refs_cli_output,
)
from config_contexts.runtime import (
    RuntimeConfigSelectionContext,
    RuntimeLiveLlmConfigView,
    RuntimeLiveLlmInvocationOptionsContext,
)
from contract_core.external_readonly_archive import (
    external_readonly_fetch_output_boundary_violated,
)
from contract_core.external_readonly_evidence import (
    validate_external_readonly_evidence_path,
)
from contract_core.llm_invocation import (
    GovernedLlmInvocationServiceFactory,
    LlmGovernancePrecondition,
    LlmInvocationRequest,
)
from contract_core.model_routing import ModelRouteFacts
from product_application_assembly import (
    EVIDENCE_SUMMARY_ANSWER_GENERATION_INTERACTION_MODE,
    build_evidence_summary_answer_context,
    build_evidence_summary_answer_llm_invocation_request,
    build_evidence_summary_answer_result_from_llm_invocation_result,
    build_governed_evidence_digest_from_external_readonly_facts,
    build_no_model_evidence_summary_answer_result,
    evidence_summary_answer_result_status_dict,
)


EXTERNAL_READONLY_ANSWER_COMMAND = "cognition external-readonly answer"
EXTERNAL_READONLY_ANSWER_SOURCE = "cognition_cli.external_readonly.answer"
EXTERNAL_READONLY_ANSWER_REQUEST_ID = (
    "external-readonly-answer-request://cli/answer"
)
EXTERNAL_READONLY_ANSWER_INTERACTION_MODE = (
    EVIDENCE_SUMMARY_ANSWER_GENERATION_INTERACTION_MODE
)
EXTERNAL_READONLY_ANSWER_FAILURE = "external_readonly_answer_cli_failure"
EXTERNAL_READONLY_ANSWER_PROVIDER_NOT_INJECTED = (
    "external_readonly_answer_llm_provider_not_injected"
)
EXTERNAL_READONLY_ANSWER_PROVIDER_RESOLUTION_FAILED = (
    "external_readonly_answer_llm_provider_resolution_failed"
)

ExternalReadonlyAnswerLlmInvocationServiceFactory = (
    GovernedLlmInvocationServiceFactory
)


def external_readonly_answer_command(
    args: argparse.Namespace,
    *,
    refs_executor: ExternalReadonlyRefsApplicationExecutor | None = None,
    llm_invocation_service_factory: (
        ExternalReadonlyAnswerLlmInvocationServiceFactory | None
    ) = None,
) -> int:
    """Run an explicit governed LLM answer smoke for archived evidence refs."""

    try:
        exit_code, output = build_external_readonly_answer_cli_output(
            args,
            refs_executor=refs_executor,
            llm_invocation_service_factory=llm_invocation_service_factory,
        )
    except Exception as exc:  # pragma: no cover - defensive product boundary.
        print(f"{EXTERNAL_READONLY_ANSWER_COMMAND} error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_FAILURE
    return _emit_external_readonly_answer_output(args, output, exit_code=exit_code)


def build_external_readonly_answer_cli_output(
    args: argparse.Namespace,
    *,
    refs_executor: ExternalReadonlyRefsApplicationExecutor | None = None,
    llm_invocation_service_factory: (
        ExternalReadonlyAnswerLlmInvocationServiceFactory | None
    ) = None,
) -> tuple[int, dict[str, Any]]:
    """Build the answer smoke output without printing it."""

    request_id = str(args.request_id or EXTERNAL_READONLY_ANSWER_REQUEST_ID)
    evidence_paths = tuple(getattr(args, "evidence_paths", ()) or ())
    question = _normalized_question(getattr(args, "question", None))
    preflight_reasons = _preflight_blocking_reasons(args, evidence_paths, question)
    if preflight_reasons:
        return (
            EXIT_BLOCKING,
            _blocked_output(
                request_id,
                evidence_paths=evidence_paths,
                question=question,
                blocking_reasons=preflight_reasons,
                product_response_summary=None,
            ),
        )

    refs_exit_code, refs_output = build_external_readonly_refs_cli_output(
        evidence_paths,
        request_id=f"{request_id}/refs",
        executor=refs_executor,
        metadata={
            "source": EXTERNAL_READONLY_ANSWER_SOURCE,
            "answer_smoke": True,
            "permanent_product_path": False,
        },
    )
    refs_summary = _allowed_product_response_summary(
        _mapping(refs_output.get("product_response_summary"))
    )
    if refs_exit_code != EXIT_OK or refs_output.get("status") != "success":
        blocking_reasons = _list_value(refs_output.get("blocking_reasons"))
        if "external_readonly_refs_not_success" not in blocking_reasons:
            blocking_reasons.append("external_readonly_refs_not_success")
        return (
            refs_exit_code if refs_exit_code != EXIT_OK else EXIT_BLOCKING,
            _blocked_output(
                request_id,
                evidence_paths=evidence_paths,
                question=question,
                blocking_reasons=tuple(str(item) for item in blocking_reasons),
                product_response_summary=refs_summary or None,
                refs_output=refs_output,
            ),
        )

    bridge = _build_evidence_summary_answer_bridge(
        request_id=request_id,
        evidence_paths=evidence_paths,
        question=question,
    )
    if bridge["blocking_reasons"]:
        return (
            EXIT_BLOCKING,
            _blocked_output(
                request_id,
                evidence_paths=evidence_paths,
                question=question,
                blocking_reasons=tuple(bridge["blocking_reasons"]),
                product_response_summary=refs_summary,
                refs_output=refs_output,
            ),
        )

    context = bridge["context"]
    generation_policy_facts = _generation_policy_facts(context)
    try:
        llm_request = build_evidence_summary_answer_llm_invocation_request(
            context,
            route_facts=_route_facts(args),
            governance_precondition=_governance_precondition(args),
            request_id=f"{request_id}/llm",
            generation_policy_facts=generation_policy_facts,
            metadata={"smoke_only": True},
        )
    except ValueError as exc:
        result = build_no_model_evidence_summary_answer_result(
            context,
            metadata={
                "source": EXTERNAL_READONLY_ANSWER_SOURCE,
                "bridge_reason": str(exc),
            },
        )
        output = _output_from_answer_result(
            request_id,
            evidence_paths=evidence_paths,
            question=question,
            refs_output=refs_output,
            product_response_summary=refs_summary,
            answer_result=evidence_summary_answer_result_status_dict(result),
            llm_request=None,
            resolution_warnings=(),
        )
        return _exit_code_from_output(output), output

    if llm_invocation_service_factory is None:
        return (
            EXIT_BLOCKING,
            _blocked_output(
                request_id,
                evidence_paths=evidence_paths,
                question=question,
                blocking_reasons=(EXTERNAL_READONLY_ANSWER_PROVIDER_NOT_INJECTED,),
                product_response_summary=refs_summary,
                refs_output=refs_output,
            ),
        )

    resolution = _resolve_llm_service(
        args,
        llm_invocation_service_factory,
        request_id=request_id,
    )
    if resolution["blocking_reasons"]:
        return (
            EXIT_BLOCKING,
            _blocked_output(
                request_id,
                evidence_paths=evidence_paths,
                question=question,
                blocking_reasons=tuple(resolution["blocking_reasons"]),
                product_response_summary=refs_summary,
                refs_output=refs_output,
                warnings=tuple(resolution["warnings"]),
            ),
        )

    service = resolution["service"]
    llm_result = service.invoke(llm_request)
    answer_result = build_evidence_summary_answer_result_from_llm_invocation_result(
        context,
        llm_result,
        generation_policy_facts=generation_policy_facts,
        metadata={"smoke_only": True},
    )
    output = _output_from_answer_result(
        request_id,
        evidence_paths=evidence_paths,
        question=question,
        refs_output=refs_output,
        product_response_summary=refs_summary,
        answer_result=evidence_summary_answer_result_status_dict(answer_result),
        llm_request=llm_request,
        resolution_warnings=tuple(resolution["warnings"]),
    )
    return _exit_code_from_output(output), output


def _resolve_llm_service(
    args: argparse.Namespace,
    factory: ExternalReadonlyAnswerLlmInvocationServiceFactory,
    *,
    request_id: str,
) -> dict[str, Any]:
    try:
        resolution = factory.resolve(
            config_context=None,
            config_selection=RuntimeConfigSelectionContext(
                config_root=str(args.config_root) if args.config_root else None,
                environment=args.environment,
                profile=args.profile,
                selection_source=EXTERNAL_READONLY_ANSWER_SOURCE,
                metadata={
                    "request_id": request_id,
                    "surface": EXTERNAL_READONLY_ANSWER_COMMAND,
                    "smoke_only": True,
                },
            ),
            live_llm_options=RuntimeLiveLlmInvocationOptionsContext(
                ollama_api_base=args.ollama_api_base,
                timeout_seconds=args.live_llm_timeout_seconds,
                max_tokens=args.live_llm_max_tokens,
                response_preview_limit=args.answer_preview_limit,
                selection_source=EXTERNAL_READONLY_ANSWER_SOURCE,
                metadata={
                    "request_id": request_id,
                    "surface": EXTERNAL_READONLY_ANSWER_COMMAND,
                    "model_name": _model_name(args),
                    "smoke_only": True,
                },
            ),
        )
    except Exception:
        return {
            "service": None,
            "blocking_reasons": (
                EXTERNAL_READONLY_ANSWER_PROVIDER_RESOLUTION_FAILED,
            ),
            "warnings": ("external_readonly_answer_llm_provider_exception",),
        }
    blocking_reasons = tuple(str(item) for item in resolution.blocking_reasons)
    service = resolution.service
    if blocking_reasons or service is None:
        return {
            "service": None,
            "blocking_reasons": blocking_reasons
            or (EXTERNAL_READONLY_ANSWER_PROVIDER_RESOLUTION_FAILED,),
            "warnings": tuple(str(item) for item in resolution.warnings),
        }
    return {
        "service": service,
        "blocking_reasons": (),
        "warnings": tuple(str(item) for item in resolution.warnings),
    }


def _build_evidence_summary_answer_bridge(
    *,
    request_id: str,
    evidence_paths: tuple[str, ...],
    question: str,
) -> dict[str, Any]:
    facts_payloads, blocking_reasons = _archived_governed_summary_facts(
        evidence_paths,
        repo_root=Path.cwd(),
    )
    if blocking_reasons:
        return {"context": None, "blocking_reasons": blocking_reasons}
    try:
        digests = [
            build_governed_evidence_digest_from_external_readonly_facts(
                facts,
                metadata={
                    "source": EXTERNAL_READONLY_ANSWER_SOURCE,
                    "bridge": "external_readonly_evidence_to_answer_context",
                },
            )
            for facts in facts_payloads
        ]
        context = build_evidence_summary_answer_context(
            request_id=f"{request_id}/context",
            user_question=question,
            digests=digests,
            metadata={
                "source": EXTERNAL_READONLY_ANSWER_SOURCE,
                "bridge": "external_readonly_evidence_to_answer_context",
            },
        )
    except Exception:
        return {
            "context": None,
            "blocking_reasons": (
                "evidence_summary_answer_context_bridge_failed",
            ),
        }
    return {"context": context, "blocking_reasons": ()}


def _archived_governed_summary_facts(
    evidence_paths: tuple[str, ...],
    *,
    repo_root: Path,
) -> tuple[list[Mapping[str, Any]], tuple[str, ...]]:
    payloads: list[Mapping[str, Any]] = []
    blocking_reasons: list[str] = []
    for evidence_path in evidence_paths:
        issue = validate_external_readonly_evidence_path(
            evidence_path=evidence_path,
            repo_root=repo_root,
        )
        if issue:
            blocking_reasons.append(f"{evidence_path}:{issue}")
            continue
        target = (repo_root / evidence_path).resolve()
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            blocking_reasons.append(
                f"{evidence_path}:external_readonly_evidence_archive_unreadable"
            )
            continue
        if not isinstance(payload, Mapping):
            blocking_reasons.append(
                f"{evidence_path}:external_readonly_evidence_archive_not_object"
            )
            continue

        facts = _mapping(payload.get("governed_summary_facts"))
        if facts:
            payloads.append(facts)
            continue
        payloads.append(
            _blocked_governed_summary_facts_payload(
                payload,
                evidence_path=evidence_path,
                reason="external_readonly_governed_summary_facts_required",
            )
        )
    return payloads, tuple(blocking_reasons)


def _blocked_governed_summary_facts_payload(
    archive_payload: Mapping[str, Any],
    *,
    evidence_path: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "payload_type": "external_readonly_governed_summary_facts",
        "payload_version": "external_readonly_governed_summary_facts_v1",
        "status": "blocked",
        "evidence_ref": _archive_evidence_ref(archive_payload, evidence_path),
        "evidence_output_path": evidence_path,
        "reference_review_ready": False,
        "allowed_for_model_context": False,
        "evidence_written": archive_payload.get("evidence_written") is True,
        "facts": [],
        "fact_count": 0,
        "total_fact_chars": 0,
        "blocking_reasons": [reason],
        "warnings": [],
        "metadata": {
            "source": EXTERNAL_READONLY_ANSWER_SOURCE,
            "archive_bridge": True,
        },
    }


def _archive_evidence_ref(
    archive_payload: Mapping[str, Any],
    evidence_path: str,
) -> str:
    value = archive_payload.get("evidence_ref")
    if isinstance(value, str) and value.startswith("evidence://external-readonly/"):
        return value
    try:
        relative = Path(evidence_path).relative_to("outputs/external-readonly")
    except ValueError:
        return "evidence://external-readonly/governed-summary-facts/unavailable"
    return f"evidence://external-readonly/{relative.as_posix()}"


def _route_facts(args: argparse.Namespace) -> ModelRouteFacts:
    model_name = _model_name(args)
    return ModelRouteFacts(
        model_name=model_name,
        provider="litellm",
        source=EXTERNAL_READONLY_ANSWER_SOURCE,
        metadata={
            "backend_provider": "ollama",
            "route_kind": "adk_litellm",
            "route_target": model_name,
            "route_fact_contract": "schemas.model_routing.ModelRouteFacts",
        },
    )


def _governance_precondition(args: argparse.Namespace) -> LlmGovernancePrecondition:
    return LlmGovernancePrecondition(
        allowed=True,
        reason="evidence_summary_answer_explicit_live_generation_smoke",
        decision="allow",
        governance_decision_ref=args.live_llm_approval_ref,
        metadata={
            "surface": EXTERNAL_READONLY_ANSWER_COMMAND,
            "smoke_only": True,
        },
    )


def _generation_policy_facts(context: Any) -> dict[str, Any]:
    return {
        "profile": "controlled_live_answer_generation",
        "allow_answer_generation_success": True,
        "answer_generation_service_ref": (
            "service://cognition-cli/external-readonly-answer/generation"
        ),
        "answer_policy_ref": context.answer_policy_ref,
        "citation_policy_ref": context.citation_policy_ref,
    }


def _output_from_answer_result(
    request_id: str,
    *,
    evidence_paths: tuple[str, ...],
    question: str,
    refs_output: Mapping[str, Any],
    product_response_summary: Mapping[str, Any],
    answer_result: Mapping[str, Any],
    llm_request: LlmInvocationRequest | None,
    resolution_warnings: tuple[str, ...],
) -> dict[str, Any]:
    evidence_refs = _list_value(product_response_summary.get("evidence_refs"))
    additional_refs = _list_value(product_response_summary.get("additional_refs"))
    status = str(answer_result.get("status") or "failed")
    answer = answer_result.get("answer")
    answer_text = answer if isinstance(answer, str) and answer else None
    answer_preview = answer_result.get("answer_preview")
    answer_preview_text = (
        answer_preview if isinstance(answer_preview, str) and answer_preview else None
    )
    return {
        "product": PRODUCT_NAME,
        "command": EXTERNAL_READONLY_ANSWER_COMMAND,
        "status": status,
        "success": status == "success",
        "failure_type": None if status == "success" else EXTERNAL_READONLY_ANSWER_FAILURE,
        "request_id": request_id,
        "refs_request_id": refs_output.get("request_id"),
        "llm_request_id": llm_request.request_id if llm_request is not None else None,
        "model_name": (
            llm_request.route_facts.model_name if llm_request is not None else None
        ),
        "interaction_mode": (
            llm_request.metadata.get("interaction_mode")
            if llm_request is not None
            else EXTERNAL_READONLY_ANSWER_INTERACTION_MODE
        ),
        "evidence_path_count": len(evidence_paths),
        "evidence_ref_count": len(evidence_refs),
        "additional_ref_count": len(additional_refs),
        "readonly_refs_status": refs_output.get("readonly_refs_status"),
        "product_response_summary": dict(product_response_summary),
        "question_preview": _preview(question, limit=120),
        "answer": answer_text,
        "answer_preview": answer_preview_text,
        "answer_length": len(answer_text) if answer_text else None,
        "evidence_summary_answer_result": dict(answer_result),
        "llm_call_allowed": answer_result.get("llm_call_allowed") is True,
        "llm_call_attempted": answer_result.get("llm_call_attempted") is True,
        "llm_runtime_call_performed": (
            answer_result.get("llm_runtime_call_performed") is True
        ),
        "external_readonly_fetch_performed": False,
        "external_readonly_network_call_performed": False,
        "external_network_call_performed": False,
        "raw_response_included": False,
        "raw_html_included": False,
        "response_headers_included": False,
        "uploads_content": False,
        "writes_files": False,
        "blocking_reasons": _string_list(answer_result.get("blocking_reasons")),
        "citation_failures": _string_list(answer_result.get("citation_failures")),
        "warnings": [
            *tuple(str(item) for item in refs_output.get("warnings") or ()),
            *_string_list(answer_result.get("warnings")),
            *resolution_warnings,
        ],
        "exit_code": EXIT_OK if status == "success" else _exit_code_from_status(status),
    }


def _blocked_output(
    request_id: str,
    *,
    evidence_paths: tuple[str, ...],
    question: str,
    blocking_reasons: tuple[str, ...],
    product_response_summary: Mapping[str, Any] | None,
    refs_output: Mapping[str, Any] | None = None,
    warnings: tuple[str, ...] = (),
) -> dict[str, Any]:
    evidence_refs = _list_value(
        product_response_summary.get("evidence_refs")
        if product_response_summary
        else None
    )
    additional_refs = _list_value(
        product_response_summary.get("additional_refs")
        if product_response_summary
        else None
    )
    return {
        "product": PRODUCT_NAME,
        "command": EXTERNAL_READONLY_ANSWER_COMMAND,
        "status": "blocked",
        "success": False,
        "failure_type": EXTERNAL_READONLY_ANSWER_FAILURE,
        "request_id": request_id,
        "refs_request_id": refs_output.get("request_id") if refs_output else None,
        "llm_request_id": None,
        "model_name": None,
        "interaction_mode": EXTERNAL_READONLY_ANSWER_INTERACTION_MODE,
        "evidence_path_count": len(evidence_paths),
        "evidence_ref_count": len(evidence_refs),
        "additional_ref_count": len(additional_refs),
        "readonly_refs_status": (
            refs_output.get("readonly_refs_status") if refs_output else "blocked"
        ),
        "product_response_summary": (
            dict(product_response_summary) if product_response_summary else None
        ),
        "question_preview": _preview(question, limit=120) if question else None,
        "answer": None,
        "answer_preview": None,
        "answer_length": None,
        "llm_call_allowed": False,
        "llm_call_attempted": False,
        "llm_runtime_call_performed": False,
        "external_readonly_fetch_performed": False,
        "external_readonly_network_call_performed": False,
        "external_network_call_performed": False,
        "raw_response_included": False,
        "raw_html_included": False,
        "response_headers_included": False,
        "uploads_content": False,
        "writes_files": False,
        "blocking_reasons": list(blocking_reasons),
        "warnings": list(warnings),
        "exit_code": EXIT_BLOCKING,
    }


def _allowed_product_response_summary(
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    if not summary:
        return {}
    allowed = {
        "request_id": summary.get("request_id"),
        "entry_kind": summary.get("entry_kind"),
        "status": summary.get("status"),
        "exit_code": summary.get("exit_code"),
        "evidence_refs": _allowed_refs(summary.get("evidence_refs")),
        "additional_refs": _allowed_refs(summary.get("additional_refs")),
        "blocking_reasons": _string_list(summary.get("blocking_reasons")),
        "warnings": _string_list(summary.get("warnings")),
        "readonly": summary.get("readonly") is True,
        "summary_only": summary.get("summary_only") is True,
        "refs_only": summary.get("refs_only") is True,
        "candidate_only": summary.get("candidate_only") is True,
        "execution_enabled": summary.get("execution_enabled") is True,
        "runtime_permission_granted": (
            summary.get("runtime_permission_granted") is True
        ),
        "llm_call_enabled": summary.get("llm_call_enabled") is True,
        "tool_execution_enabled": summary.get("tool_execution_enabled") is True,
        "action_execution_enabled": summary.get("action_execution_enabled") is True,
        "gateway_enabled": summary.get("gateway_enabled") is True,
    }
    return {key: value for key, value in allowed.items() if value is not None}


def _allowed_refs(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _list_value(value):
        mapping = _mapping(item)
        if not mapping:
            continue
        refs.append(
            {
                "ref": str(mapping.get("ref") or ""),
                "kind": str(mapping.get("kind") or "unknown"),
                "purpose": mapping.get("purpose"),
            }
        )
    return refs


def _preflight_blocking_reasons(
    args: argparse.Namespace,
    evidence_paths: tuple[str, ...],
    question: str,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not evidence_paths:
        reasons.append("evidence_output_path_required")
    if not question:
        reasons.append("question_required")
    if args.request_live_llm is not True:
        reasons.append("request_live_llm_required")
    if args.request_ollama is not True:
        reasons.append("request_ollama_required")
    if args.allow_live_llm is not True:
        reasons.append("allow_live_llm_required")
    if args.allow_ollama is not True:
        reasons.append("allow_ollama_required")
    if not args.live_llm_approval_ref:
        reasons.append("live_llm_approval_ref_required")
    if (
        args.live_llm_timeout_seconds is not None
        and args.live_llm_timeout_seconds <= 0
    ):
        reasons.append("live_llm_timeout_seconds_must_be_positive")
    if args.live_llm_max_tokens is not None and args.live_llm_max_tokens <= 0:
        reasons.append("live_llm_max_tokens_must_be_positive")
    if args.answer_preview_limit is not None and args.answer_preview_limit <= 0:
        reasons.append("answer_preview_limit_must_be_positive")
    if not _model_name(args):
        reasons.append("model_name_required")
    if args.ollama_api_base and not _local_ollama_api_base(args.ollama_api_base):
        reasons.append("ollama_api_base_must_be_local")
    return tuple(reasons)


def _emit_external_readonly_answer_output(
    args: argparse.Namespace,
    output: Mapping[str, Any],
    *,
    exit_code: int,
) -> int:
    if external_readonly_fetch_output_boundary_violated(output):
        print(
            f"{EXTERNAL_READONLY_ANSWER_COMMAND} output boundary violation",
            file=sys.stderr,
        )
        return EXIT_OUTPUT_BOUNDARY_FAILURE

    if args.format == "json" or args.json:
        print(json.dumps(dict(output), ensure_ascii=False, sort_keys=True))
    else:
        print(_text_output(output))
    return exit_code


def _text_output(output: Mapping[str, Any]) -> str:
    lines = [
        str(output["product"]),
        f"command: {output['command']}",
        f"status: {output['status']}",
        f"request_id: {output['request_id']}",
        f"evidence_path_count: {output['evidence_path_count']}",
        f"evidence_ref_count: {output['evidence_ref_count']}",
        f"additional_ref_count: {output['additional_ref_count']}",
        f"readonly_refs_status: {output['readonly_refs_status']}",
        f"llm_call_attempted: {str(output['llm_call_attempted']).lower()}",
        f"llm_runtime_call_performed: {str(output['llm_runtime_call_performed']).lower()}",
    ]
    blocking = output.get("blocking_reasons") or []
    warnings = output.get("warnings") or []
    if blocking:
        lines.append("blocking_reasons: " + ", ".join(map(str, blocking)))
    if warnings:
        lines.append("warnings: " + ", ".join(map(str, warnings)))
    answer = output.get("answer")
    if answer:
        lines.append("answer:")
        lines.append(str(answer))
    return "\n".join(lines)


def _exit_code_from_output(output: Mapping[str, Any]) -> int:
    return _exit_code_from_status(output.get("status"))


def _exit_code_from_status(status: Any) -> int:
    if status == "success":
        return EXIT_OK
    if status == "blocked":
        return EXIT_BLOCKING
    return EXIT_RUNTIME_FAILURE


def _model_name(args: argparse.Namespace) -> str:
    model_name = getattr(args, "model_name", None)
    if isinstance(model_name, str) and model_name.strip():
        return model_name.strip()
    return RuntimeLiveLlmConfigView().model_name


def _normalized_question(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _preview(value: str, *, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip()


def _local_ollama_api_base(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "http" and parsed.hostname in {
        "127.0.0.1",
        "localhost",
        "::1",
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in _list_value(value)]


__all__ = [
    "EXTERNAL_READONLY_ANSWER_COMMAND",
    "EXTERNAL_READONLY_ANSWER_INTERACTION_MODE",
    "EXTERNAL_READONLY_ANSWER_REQUEST_ID",
    "ExternalReadonlyAnswerLlmInvocationServiceFactory",
    "build_external_readonly_answer_cli_output",
    "external_readonly_answer_command",
]
