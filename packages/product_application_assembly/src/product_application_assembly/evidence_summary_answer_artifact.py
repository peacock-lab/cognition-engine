"""Build product-level answer artifacts for evidence summary answers."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
import re
from typing import Any

from schemas.evidence_summary_answer import (
    EVIDENCE_SUMMARY_ANSWER_ARTIFACT_REF_PREFIX,
    EvidenceSummaryAnswerArtifactSchema,
    EvidenceSummaryAnswerContextSchema,
    EvidenceSummaryAnswerTraceSchema,
)


PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ARTIFACT_SOURCE = (
    "product_application_assembly.evidence_summary_answer_artifact"
)
PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ARTIFACT_POLICY_REF = (
    "policy://product-application-assembly/evidence-summary-answer/artifact-v1"
)


def build_evidence_summary_answer_artifact(
    context: EvidenceSummaryAnswerContextSchema | Mapping[str, Any],
    answer_result: Mapping[str, Any],
    trace: EvidenceSummaryAnswerTraceSchema | Mapping[str, Any],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> EvidenceSummaryAnswerArtifactSchema:
    """Build a sanitized, product-level answer artifact contract."""

    context_model = _context_model(context)
    trace_model = _trace_model(trace)
    status = str(answer_result.get("status") or trace_model.answer_status)
    artifact_id = _artifact_id(
        request_id=str(answer_result.get("request_id") or context_model.request_id),
        status=status,
        trace_ref=trace_model.trace_ref,
        evidence_refs=[ref.ref for ref in trace_model.evidence_refs],
        digest_refs=list(trace_model.digest_refs),
    )
    artifact_ref = f"{EVIDENCE_SUMMARY_ANSWER_ARTIFACT_REF_PREFIX}{artifact_id}"
    metadata_payload = {
        "source": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ARTIFACT_SOURCE,
        "policy_ref": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ARTIFACT_POLICY_REF,
        "context_payload_type": context_model.payload_type,
        "context_payload_version": context_model.payload_version,
        "result_payload_type": _optional_string(answer_result.get("payload_type")),
        "result_payload_version": _optional_string(answer_result.get("payload_version")),
        "trace_payload_type": trace_model.payload_type,
        "trace_payload_version": trace_model.payload_version,
        "task_api_fact_gate": "compatible_not_runtime_backed",
        "workflow_runtime_fact_gate": "compatible_not_runtime_backed",
        "adk_artifact_service_fact_gate": "product_contract_only",
    }
    metadata_payload.update(_compact_metadata(metadata or {}))

    answer = _optional_string(answer_result.get("answer"))
    answer_preview = _optional_string(answer_result.get("answer_preview"))
    if answer_preview is None:
        answer_preview = trace_model.answer_preview

    return EvidenceSummaryAnswerArtifactSchema(
        artifact_id=artifact_id,
        artifact_ref=artifact_ref,
        request_id=str(answer_result.get("request_id") or context_model.request_id),
        answer_status=status,
        artifact_status=status,
        trace_ref=trace_model.trace_ref,
        artifact_policy_ref=PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ARTIFACT_POLICY_REF,
        evidence_ref_count=trace_model.evidence_ref_count,
        additional_ref_count=trace_model.additional_ref_count,
        digest_ref_count=trace_model.digest_ref_count,
        evidence_refs=list(trace_model.evidence_refs),
        additional_refs=list(trace_model.additional_refs),
        digest_refs=list(trace_model.digest_refs),
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
        llm_route_provider=trace_model.llm_route_provider,
        llm_route_model=trace_model.llm_route_model,
        provider_profile_ref=trace_model.provider_profile_ref,
        model_profile_ref=trace_model.model_profile_ref,
        output_governance_profile_ref=trace_model.output_governance_profile_ref,
        answerability_preflight_applied=trace_model.answerability_preflight_applied,
        answerability_preflight_reason=trace_model.answerability_preflight_reason,
        answer_ref=trace_model.answer_ref,
        answer=answer,
        answer_preview=answer_preview,
        export_allowed=False,
        delete_supported=True,
        retention_policy_ref=None,
        durable_session=False,
        memory_enabled=False,
        task_compatible=True,
        workflow_compatible=True,
        backed_by_adk_task_runtime=False,
        backed_by_adk_workflow_runtime=False,
        metadata=metadata_payload,
    )


def evidence_summary_answer_artifact_status_dict(
    artifact: EvidenceSummaryAnswerArtifactSchema | Mapping[str, Any],
) -> dict[str, Any]:
    """Return a JSON-ready public answer artifact dict."""

    model = (
        EvidenceSummaryAnswerArtifactSchema.model_validate(artifact)
        if isinstance(artifact, Mapping)
        else artifact
    )
    payload = model.model_dump(mode="json")
    raw_boundary_flags = {
        key: value
        for key, value in payload.get("raw_boundary_flags", {}).items()
        if value is True
    }
    payload["raw_boundary_flags"] = raw_boundary_flags
    return payload


def evidence_summary_answer_artifact_summary_dict(
    artifact: EvidenceSummaryAnswerArtifactSchema | Mapping[str, Any],
) -> dict[str, Any]:
    """Return ProductGateway-safe answer artifact summary facts."""

    payload = evidence_summary_answer_artifact_status_dict(artifact)
    return {
        "artifact_ref": payload["artifact_ref"],
        "artifact_status": payload["artifact_status"],
        "request_id": payload["request_id"],
        "trace_ref": payload["trace_ref"],
        "artifact_policy_ref": payload["artifact_policy_ref"],
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
        "answer_present": bool(payload.get("answer")),
        "answer_preview_present": bool(payload.get("answer_preview")),
        "export_allowed": payload["export_allowed"],
        "delete_supported": payload["delete_supported"],
        "durable_session": False,
        "memory_enabled": False,
        "task_compatible": payload["task_compatible"],
        "workflow_compatible": payload["workflow_compatible"],
        "backed_by_adk_task_runtime": False,
        "backed_by_adk_workflow_runtime": False,
    }


def _context_model(
    context: EvidenceSummaryAnswerContextSchema | Mapping[str, Any],
) -> EvidenceSummaryAnswerContextSchema:
    if isinstance(context, EvidenceSummaryAnswerContextSchema):
        return context
    return EvidenceSummaryAnswerContextSchema.model_validate(context)


def _trace_model(
    trace: EvidenceSummaryAnswerTraceSchema | Mapping[str, Any],
) -> EvidenceSummaryAnswerTraceSchema:
    if isinstance(trace, EvidenceSummaryAnswerTraceSchema):
        return trace
    return EvidenceSummaryAnswerTraceSchema.model_validate(trace)


def _artifact_id(
    *,
    request_id: str,
    status: str,
    trace_ref: str,
    evidence_refs: list[str],
    digest_refs: list[str],
) -> str:
    seed = json.dumps(
        {
            "request_id": request_id,
            "status": status,
            "trace_ref": trace_ref,
            "evidence_refs": sorted(evidence_refs),
            "digest_refs": sorted(digest_refs),
        },
        ensure_ascii=True,
        sort_keys=True,
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return f"artifact-{digest}"


def _string_items(value: Any) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return _ordered_unique(str(item) for item in value if isinstance(item, str) and item)


def _ordered_unique(values: list[str]) -> list[str]:
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
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ARTIFACT_POLICY_REF",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ARTIFACT_SOURCE",
    "build_evidence_summary_answer_artifact",
    "evidence_summary_answer_artifact_status_dict",
    "evidence_summary_answer_artifact_summary_dict",
)
