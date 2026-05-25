"""Build product-level answer trace facts for evidence summary answers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import hashlib
import json
import re
from typing import Any

from schemas.evidence_summary_answer import (
    EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX,
    EvidenceSummaryAnswerContextSchema,
    EvidenceSummaryAnswerRefSchema,
    EvidenceSummaryAnswerTraceSchema,
)


PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_TRACE_SOURCE = (
    "product_application_assembly.evidence_summary_answer_trace"
)
PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_TRACE_POLICY_REF = (
    "policy://product-application-assembly/evidence-summary-answer/trace-v1"
)


def build_evidence_summary_answer_trace(
    context: EvidenceSummaryAnswerContextSchema | Mapping[str, Any],
    answer_result: Mapping[str, Any],
    *,
    readonly_refs_status: str | None = None,
    evidence_refs: Iterable[Mapping[str, Any]] | None = None,
    additional_refs: Iterable[Mapping[str, Any]] | None = None,
    follow_up: bool = False,
    follow_up_turn_index: int | None = None,
    follow_up_seed_ref: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> EvidenceSummaryAnswerTraceSchema:
    """Build a sanitized Task/Workflow-compatible answer trace."""

    context_model = _context_model(context)
    status = str(answer_result.get("status") or "failed")
    result_evidence_refs = _refs(
        evidence_refs
        if evidence_refs is not None
        else answer_result.get("evidence_refs_used")
    )
    if not result_evidence_refs:
        result_evidence_refs = list(context_model.evidence_refs)

    result_additional_refs = _refs(
        additional_refs
        if additional_refs is not None
        else answer_result.get("additional_refs_used")
    )
    if not result_additional_refs:
        result_additional_refs = list(context_model.additional_refs)

    digest_refs = _ordered_unique(
        _string_items(answer_result.get("digest_refs_used"))
        or [digest.digest_ref for digest in context_model.digests]
    )
    answer_preview = _optional_string(answer_result.get("answer_preview"))
    trace_id = _trace_id(
        request_id=str(answer_result.get("request_id") or context_model.request_id),
        status=status,
        evidence_refs=[ref.ref for ref in result_evidence_refs],
        digest_refs=digest_refs,
        follow_up_turn_index=follow_up_turn_index,
    )
    trace_ref = f"{EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX}{trace_id}"
    metadata_payload = {
        "source": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_TRACE_SOURCE,
        "policy_ref": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_TRACE_POLICY_REF,
        "context_payload_type": context_model.payload_type,
        "context_payload_version": context_model.payload_version,
        "result_payload_type": _optional_string(answer_result.get("payload_type")),
        "result_payload_version": _optional_string(answer_result.get("payload_version")),
        "task_api_fact_gate": "compatible_not_runtime_backed",
        "workflow_runtime_fact_gate": "compatible_not_runtime_backed",
    }
    metadata_payload.update(_compact_metadata(metadata or {}))

    return EvidenceSummaryAnswerTraceSchema(
        trace_id=trace_id,
        trace_ref=trace_ref,
        request_id=str(answer_result.get("request_id") or context_model.request_id),
        answer_status=status,
        readonly_refs_status=readonly_refs_status,
        evidence_ref_count=len(result_evidence_refs),
        additional_ref_count=len(result_additional_refs),
        digest_ref_count=len(digest_refs),
        evidence_refs=result_evidence_refs,
        additional_refs=result_additional_refs,
        digest_refs=digest_refs,
        blocking_reasons=_string_items(answer_result.get("blocking_reasons")),
        warnings=_string_items(answer_result.get("warnings")),
        insufficient_evidence_reason=_optional_string(
            answer_result.get("insufficient_evidence_reason")
        ),
        citation_failures=_string_items(answer_result.get("citation_failures")),
        llm_call_allowed=answer_result.get("llm_call_allowed") is True,
        llm_call_attempted=answer_result.get("llm_call_attempted") is True,
        llm_runtime_call_performed=(
            answer_result.get("llm_runtime_call_performed") is True
        ),
        llm_route_provider=_metadata_or_extra_string(
            answer_result,
            metadata or {},
            "llm_route_provider",
        ),
        llm_route_model=_metadata_or_extra_string(
            answer_result,
            metadata or {},
            "llm_route_model",
        ),
        provider_profile_ref=_metadata_or_extra_string(
            answer_result,
            metadata or {},
            "provider_profile_ref",
        ),
        model_profile_ref=_metadata_or_extra_string(
            answer_result,
            metadata or {},
            "model_profile_ref",
        ),
        output_governance_profile_ref=_metadata_or_extra_string(
            answer_result,
            metadata or {},
            "output_governance_profile_ref",
        ),
        answerability_preflight_applied=_metadata_bool(
            answer_result,
            "answerability_preflight",
        ),
        answerability_preflight_reason=_metadata_string(
            answer_result,
            "answerability_preflight_reason",
        ),
        answer_ref=f"{trace_ref}/answer" if answer_preview else None,
        answer_preview=answer_preview,
        follow_up=follow_up,
        follow_up_turn_index=follow_up_turn_index,
        follow_up_seed_ref=follow_up_seed_ref,
        temporary_follow_up=True,
        durable_session=False,
        memory_enabled=False,
        task_compatible=True,
        workflow_compatible=True,
        backed_by_adk_task_runtime=False,
        backed_by_adk_workflow_runtime=False,
        metadata=metadata_payload,
    )


def evidence_summary_answer_trace_status_dict(
    trace: EvidenceSummaryAnswerTraceSchema | Mapping[str, Any],
) -> dict[str, Any]:
    """Return a JSON-ready public answer trace dict."""

    model = (
        EvidenceSummaryAnswerTraceSchema.model_validate(trace)
        if isinstance(trace, Mapping)
        else trace
    )
    payload = model.model_dump(mode="json")
    raw_boundary_flags = {
        key: value
        for key, value in payload.get("raw_boundary_flags", {}).items()
        if value is True
    }
    payload["raw_boundary_flags"] = raw_boundary_flags
    return payload


def evidence_summary_answer_trace_summary_dict(
    trace: EvidenceSummaryAnswerTraceSchema | Mapping[str, Any],
) -> dict[str, Any]:
    """Return ProductGateway-safe trace summary facts."""

    payload = evidence_summary_answer_trace_status_dict(trace)
    metadata = payload.get("metadata")
    metadata = metadata if isinstance(metadata, Mapping) else {}
    return {
        "trace_ref": payload["trace_ref"],
        "trace_status": payload["answer_status"],
        "request_id": payload["request_id"],
        "readonly_refs_status": payload.get("readonly_refs_status"),
        "evidence_ref_count": payload["evidence_ref_count"],
        "additional_ref_count": payload["additional_ref_count"],
        "digest_ref_count": payload["digest_ref_count"],
        "blocking_reason_count": len(payload.get("blocking_reasons") or []),
        "warning_count": len(payload.get("warnings") or []),
        "llm_call_allowed": payload["llm_call_allowed"],
        "llm_call_attempted": payload["llm_call_attempted"],
        "llm_runtime_call_performed": payload["llm_runtime_call_performed"],
        "llm_route_provider": payload.get("llm_route_provider"),
        "llm_route_model": payload.get("llm_route_model"),
        "provider_profile_ref": payload.get("provider_profile_ref"),
        "model_profile_ref": payload.get("model_profile_ref"),
        "output_governance_profile_ref": payload.get(
            "output_governance_profile_ref"
        ),
        "answerability_preflight_applied": payload[
            "answerability_preflight_applied"
        ],
        "follow_up": payload["follow_up"],
        "follow_up_turn_index": payload.get("follow_up_turn_index"),
        "temporary_follow_up": payload["temporary_follow_up"],
        "durable_session": False,
        "memory_enabled": False,
        "task_compatible": payload["task_compatible"],
        "workflow_compatible": payload["workflow_compatible"],
        "backed_by_adk_task_runtime": False,
        "backed_by_adk_workflow_runtime": False,
        "summary_fact_count": metadata.get("summary_fact_count"),
        "evidence_chunked": metadata.get("evidence_chunked"),
        "fact_slice_count": metadata.get("fact_slice_count"),
        "chunked_source_item_count": metadata.get("chunked_source_item_count"),
    }


def _context_model(
    context: EvidenceSummaryAnswerContextSchema | Mapping[str, Any],
) -> EvidenceSummaryAnswerContextSchema:
    if isinstance(context, EvidenceSummaryAnswerContextSchema):
        return context
    return EvidenceSummaryAnswerContextSchema.model_validate(context)


def _refs(values: Any) -> list[EvidenceSummaryAnswerRefSchema]:
    refs: list[EvidenceSummaryAnswerRefSchema] = []
    if not isinstance(values, Iterable) or isinstance(values, (str, bytes, Mapping)):
        return refs
    for value in values:
        if isinstance(value, EvidenceSummaryAnswerRefSchema):
            refs.append(value)
        elif isinstance(value, Mapping):
            refs.append(EvidenceSummaryAnswerRefSchema.model_validate(dict(value)))
    return refs


def _trace_id(
    *,
    request_id: str,
    status: str,
    evidence_refs: list[str],
    digest_refs: list[str],
    follow_up_turn_index: int | None,
) -> str:
    seed = json.dumps(
        {
            "request_id": request_id,
            "status": status,
            "evidence_refs": sorted(evidence_refs),
            "digest_refs": sorted(digest_refs),
            "follow_up_turn_index": follow_up_turn_index,
        },
        ensure_ascii=True,
        sort_keys=True,
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return f"trace-{digest}"


def _string_items(value: Any) -> list[str]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return []
    return _ordered_unique(str(item) for item in value if isinstance(item, str) and item)


def _ordered_unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def _optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _metadata_bool(answer_result: Mapping[str, Any], key: str) -> bool:
    metadata = answer_result.get("metadata")
    return isinstance(metadata, Mapping) and metadata.get(key) is True


def _metadata_string(answer_result: Mapping[str, Any], key: str) -> str | None:
    metadata = answer_result.get("metadata")
    if not isinstance(metadata, Mapping):
        return None
    return _optional_string(metadata.get(key))


def _metadata_or_extra_string(
    answer_result: Mapping[str, Any],
    extra: Mapping[str, Any],
    key: str,
) -> str | None:
    return _metadata_string(answer_result, key) or _optional_string(extra.get(key))


def _compact_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in metadata.items():
        if not isinstance(key, str) or _sensitive_text(key):
            continue
        if not isinstance(value, bool | int | float | str):
            continue
        if isinstance(value, str) and _sensitive_text(value):
            continue
        compact[key] = value
    return compact


def _sensitive_text(value: str) -> bool:
    normalized = value.lower()
    return bool(
        re.search(
            r"(authorization|config|cookie|header|html|message|observability|"
            r"password|payload|prompt|raw|response|secret|token)",
            normalized,
        )
    )


__all__ = (
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_TRACE_POLICY_REF",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_TRACE_SOURCE",
    "build_evidence_summary_answer_trace",
    "evidence_summary_answer_trace_status_dict",
    "evidence_summary_answer_trace_summary_dict",
)
