"""Build product-level answer run aggregate refs for evidence summary answers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import hashlib
import json
from typing import Any

from schemas.evidence_summary_answer import (
    EVIDENCE_SUMMARY_ANSWER_RUN_REF_PREFIX,
    EvidenceSummaryAnswerRefSchema,
    EvidenceSummaryAnswerRunSchema,
)


PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RUN_SOURCE = (
    "product_application_assembly.evidence_summary_answer_run"
)
PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RUN_POLICY_REF = (
    "policy://product-application-assembly/evidence-summary-answer/run-v1"
)


def build_evidence_summary_answer_run(
    *,
    request_id: str,
    answer_status: str | None,
    readonly_refs_status: str | None = None,
    evidence_refs: Iterable[Mapping[str, Any]] | None = None,
    additional_refs: Iterable[Mapping[str, Any]] | None = None,
    answer_trace_ref: str | None = None,
    answer_artifact_ref: str | None = None,
    observability_summary_ref: str | None = None,
    trace_inspect_ref: str | None = None,
    follow_up_seed_ref: str | None = None,
    parent_answer_run_ref: str | None = None,
    blocking_reasons: Iterable[str] | None = None,
    warnings: Iterable[str] | None = None,
    recovery_hints: Iterable[str] | None = None,
    unavailable_reason: str | None = None,
    follow_up: bool = False,
    follow_up_turn_index: int | None = None,
    answer_scoped_transformation: bool = False,
    metadata: Mapping[str, Any] | None = None,
) -> EvidenceSummaryAnswerRunSchema:
    """Build a sanitized, non-runtime-backed answer run aggregate ref."""

    normalized_evidence_refs = _refs(evidence_refs)
    normalized_additional_refs = _refs(additional_refs)
    status = _answer_run_status(
        answer_status=answer_status,
        evidence_refs=normalized_evidence_refs,
        answer_trace_ref=answer_trace_ref,
        answer_artifact_ref=answer_artifact_ref,
        unavailable_reason=unavailable_reason,
    )
    reason = _unavailable_reason(
        status=status,
        answer_status=answer_status,
        evidence_refs=normalized_evidence_refs,
        answer_trace_ref=answer_trace_ref,
        answer_artifact_ref=answer_artifact_ref,
        unavailable_reason=unavailable_reason,
    )
    run_id = _run_id(
        request_id=request_id,
        answer_run_status=status,
        answer_status=answer_status,
        parent_answer_run_ref=parent_answer_run_ref,
        answer_trace_ref=answer_trace_ref,
        answer_artifact_ref=answer_artifact_ref,
        observability_summary_ref=observability_summary_ref,
        trace_inspect_ref=trace_inspect_ref,
        follow_up_turn_index=follow_up_turn_index,
    )
    metadata_payload = {
        "source": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RUN_SOURCE,
        "policy_ref": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RUN_POLICY_REF,
        "task_api_fact_gate": "compatible_not_runtime_backed",
        "workflow_runtime_fact_gate": "compatible_not_runtime_backed",
        "adk_artifact_service_fact_gate": "product_contract_only",
        "adk_event_stream_fact_gate": "product_contract_only",
    }
    metadata_payload.update(_safe_scalar_mapping(metadata or {}))

    return EvidenceSummaryAnswerRunSchema(
        run_id=run_id,
        answer_run_ref=f"{EVIDENCE_SUMMARY_ANSWER_RUN_REF_PREFIX}{run_id}",
        request_id=request_id,
        source_request_id=request_id,
        parent_answer_run_ref=parent_answer_run_ref,
        answer_run_status=status,
        answer_status=answer_status,
        readonly_refs_status=readonly_refs_status,
        answer_trace_ref=answer_trace_ref,
        answer_artifact_ref=answer_artifact_ref,
        observability_summary_ref=observability_summary_ref,
        trace_inspect_ref=trace_inspect_ref,
        follow_up_seed_ref=follow_up_seed_ref,
        evidence_ref_count=len(normalized_evidence_refs),
        additional_ref_count=len(normalized_additional_refs),
        evidence_refs=normalized_evidence_refs,
        additional_refs=normalized_additional_refs,
        blocking_reasons=_string_items(blocking_reasons),
        warnings=_string_items(warnings),
        recovery_hints=_string_items(recovery_hints),
        unavailable_reason=reason,
        follow_up=follow_up,
        follow_up_turn_index=follow_up_turn_index,
        answer_scoped_transformation=answer_scoped_transformation,
        task_compatible=True,
        workflow_compatible=True,
        runtime_backed=False,
        backed_by_adk_task_runtime=False,
        backed_by_adk_workflow_runtime=False,
        backed_by_adk_artifact_service=False,
        backed_by_adk_event_stream=False,
        durable_session=False,
        memory_enabled=False,
        metadata=metadata_payload,
    )


def evidence_summary_answer_run_status_dict(
    answer_run: EvidenceSummaryAnswerRunSchema | Mapping[str, Any],
) -> dict[str, Any]:
    """Return a JSON-ready public answer run dict."""

    model = (
        EvidenceSummaryAnswerRunSchema.model_validate(answer_run)
        if isinstance(answer_run, Mapping)
        else answer_run
    )
    return model.model_dump(mode="json")


def evidence_summary_answer_run_summary_dict(
    answer_run: EvidenceSummaryAnswerRunSchema | Mapping[str, Any],
) -> dict[str, Any]:
    """Return ProductGateway-safe answer run summary facts."""

    payload = evidence_summary_answer_run_status_dict(answer_run)
    return {
        "answer_run_ref": payload["answer_run_ref"],
        "answer_run_status": payload["answer_run_status"],
        "request_id": payload["request_id"],
        "source_request_id": payload.get("source_request_id"),
        "parent_answer_run_ref": payload.get("parent_answer_run_ref"),
        "answer_status": payload.get("answer_status"),
        "readonly_refs_status": payload.get("readonly_refs_status"),
        "answer_trace_ref": payload.get("answer_trace_ref"),
        "answer_artifact_ref": payload.get("answer_artifact_ref"),
        "observability_summary_ref": payload.get("observability_summary_ref"),
        "trace_inspect_ref": payload.get("trace_inspect_ref"),
        "follow_up_seed_ref": payload.get("follow_up_seed_ref"),
        "evidence_ref_count": payload["evidence_ref_count"],
        "additional_ref_count": payload["additional_ref_count"],
        "blocking_reason_count": len(payload.get("blocking_reasons") or []),
        "warning_count": len(payload.get("warnings") or []),
        "recovery_hint_count": len(payload.get("recovery_hints") or []),
        "unavailable_reason": payload.get("unavailable_reason"),
        "follow_up": payload["follow_up"],
        "follow_up_turn_index": payload.get("follow_up_turn_index"),
        "answer_scoped_transformation": payload["answer_scoped_transformation"],
        "task_compatible": payload["task_compatible"],
        "workflow_compatible": payload["workflow_compatible"],
        "runtime_backed": payload["runtime_backed"],
        "backed_by_adk_task_runtime": payload["backed_by_adk_task_runtime"],
        "backed_by_adk_workflow_runtime": (
            payload["backed_by_adk_workflow_runtime"]
        ),
        "backed_by_adk_artifact_service": payload[
            "backed_by_adk_artifact_service"
        ],
        "backed_by_adk_event_stream": payload["backed_by_adk_event_stream"],
        "durable_session": payload["durable_session"],
        "memory_enabled": payload["memory_enabled"],
    }


def _answer_run_status(
    *,
    answer_status: str | None,
    evidence_refs: tuple[EvidenceSummaryAnswerRefSchema, ...],
    answer_trace_ref: str | None,
    answer_artifact_ref: str | None,
    unavailable_reason: str | None,
) -> str:
    if unavailable_reason:
        return "unavailable"
    if answer_status == "success":
        if evidence_refs and answer_trace_ref and answer_artifact_ref:
            return "success"
        return "unavailable"
    if answer_status in {"insufficient_evidence", "blocked", "failed"}:
        return answer_status
    return "unavailable"


def _unavailable_reason(
    *,
    status: str,
    answer_status: str | None,
    evidence_refs: tuple[EvidenceSummaryAnswerRefSchema, ...],
    answer_trace_ref: str | None,
    answer_artifact_ref: str | None,
    unavailable_reason: str | None,
) -> str | None:
    if unavailable_reason:
        return unavailable_reason
    if status != "unavailable":
        return None
    if answer_status == "success" and not evidence_refs:
        return "answer_run_requires_evidence_refs"
    if answer_status == "success" and not answer_trace_ref:
        return "answer_run_requires_answer_trace"
    if answer_status == "success" and not answer_artifact_ref:
        return "answer_run_requires_answer_artifact"
    return "answer_run_requires_product_output_context"


def _refs(
    values: Iterable[Mapping[str, Any]] | None,
) -> tuple[EvidenceSummaryAnswerRefSchema, ...]:
    refs: list[EvidenceSummaryAnswerRefSchema] = []
    for value in values or ():
        if isinstance(value, EvidenceSummaryAnswerRefSchema):
            refs.append(value)
        elif isinstance(value, Mapping):
            refs.append(EvidenceSummaryAnswerRefSchema.model_validate(dict(value)))
    return tuple(refs)


def _run_id(
    *,
    request_id: str,
    answer_run_status: str,
    answer_status: str | None,
    parent_answer_run_ref: str | None,
    answer_trace_ref: str | None,
    answer_artifact_ref: str | None,
    observability_summary_ref: str | None,
    trace_inspect_ref: str | None,
    follow_up_turn_index: int | None,
) -> str:
    seed = json.dumps(
        {
            "request_id": request_id,
            "answer_run_status": answer_run_status,
            "answer_status": answer_status,
            "parent_answer_run_ref": parent_answer_run_ref,
            "answer_trace_ref": answer_trace_ref,
            "answer_artifact_ref": answer_artifact_ref,
            "observability_summary_ref": observability_summary_ref,
            "trace_inspect_ref": trace_inspect_ref,
            "follow_up_turn_index": follow_up_turn_index,
        },
        ensure_ascii=True,
        sort_keys=True,
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return f"run-{digest}"


def _string_items(values: Iterable[str] | None) -> list[str]:
    return _ordered_unique(
        str(item) for item in values or () if isinstance(item, str) and item
    )


def _ordered_unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def _safe_scalar_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str) or _sensitive_text(key):
            continue
        if not isinstance(item, bool | int | float | str):
            continue
        if isinstance(item, str) and _sensitive_text(item):
            continue
        compact[key] = item
    return compact


def _sensitive_text(value: str) -> bool:
    normalized = value.lower()
    return any(
        marker in normalized
        for marker in (
            "authorization",
            "config",
            "cookie",
            "credential",
            "header",
            "html",
            "password",
            "raw",
            "secret",
            "token",
        )
    )


__all__ = (
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RUN_POLICY_REF",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RUN_SOURCE",
    "build_evidence_summary_answer_run",
    "evidence_summary_answer_run_status_dict",
    "evidence_summary_answer_run_summary_dict",
)
