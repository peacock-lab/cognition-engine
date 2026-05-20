"""Build no-model evidence summary answer results from public contexts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from schemas.evidence_summary_answer import (
    EvidenceSummaryAnswerContextSchema,
    EvidenceSummaryAnswerResultSchema,
    GovernedEvidenceDigestSchema,
)


PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_SOURCE = (
    "product_application_assembly.evidence_summary_answer_result"
)
PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_POLICY_REF = (
    "policy://product-application-assembly/evidence-summary-answer/result/no-model-v1"
)


def build_no_model_evidence_summary_answer_result(
    context: EvidenceSummaryAnswerContextSchema | Mapping[str, Any],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> EvidenceSummaryAnswerResultSchema:
    """Build a deterministic answer result without generating an answer."""

    context_model = _context_model(context)
    digests = context_model.digests
    answerable_digest_found = any(
        digest.answerability == "answerable" for digest in digests
    )
    all_blocked = all(_digest_is_blocked(digest) for digest in digests)

    status = "insufficient_evidence"
    blocking_reasons: list[str] = []
    insufficient_evidence_reason: str | None = (
        "no_answerable_governed_evidence_digest"
    )

    if answerable_digest_found:
        status = "blocked"
        blocking_reasons = [
            "answer_generation_not_configured_for_answerable_context"
        ]
        insufficient_evidence_reason = None
    elif all_blocked:
        status = "blocked"
        blocking_reasons = _blocking_reasons(digests) or [
            "all_governed_evidence_digests_blocked"
        ]
        insufficient_evidence_reason = None

    return EvidenceSummaryAnswerResultSchema(
        request_id=context_model.request_id,
        status=status,
        answer=None,
        answer_preview=None,
        evidence_refs_used=[],
        digest_refs_used=_ordered_unique(digest.digest_ref for digest in digests),
        additional_refs_used=list(context_model.additional_refs),
        insufficient_evidence_reason=insufficient_evidence_reason,
        citation_failures=[],
        blocking_reasons=blocking_reasons,
        warnings=_ordered_unique(
            warning for digest in digests for warning in digest.warnings
        ),
        llm_call_allowed=False,
        llm_call_attempted=False,
        llm_runtime_call_performed=False,
        metadata=_metadata(context_model, metadata or {}),
    )


def evidence_summary_answer_result_status_dict(
    result: EvidenceSummaryAnswerResultSchema | Mapping[str, Any],
) -> dict[str, Any]:
    """Return a JSON-ready public evidence summary answer result dict."""

    model = (
        EvidenceSummaryAnswerResultSchema.model_validate(result)
        if isinstance(result, Mapping)
        else result
    )
    payload = model.model_dump(mode="json")
    raw_boundary_flags = {
        key: value
        for key, value in payload.get("raw_boundary_flags", {}).items()
        if value is True
    }
    payload["raw_boundary_flags"] = raw_boundary_flags
    return payload


def _context_model(
    context: EvidenceSummaryAnswerContextSchema | Mapping[str, Any],
) -> EvidenceSummaryAnswerContextSchema:
    if isinstance(context, EvidenceSummaryAnswerContextSchema):
        return context
    return EvidenceSummaryAnswerContextSchema.model_validate(context)


def _digest_is_blocked(digest: GovernedEvidenceDigestSchema) -> bool:
    return digest.status == "blocked" or digest.answerability == "blocked"


def _blocking_reasons(
    digests: Iterable[GovernedEvidenceDigestSchema],
) -> list[str]:
    return _ordered_unique(
        reason
        for digest in digests
        for reason in digest.blocking_reasons
        if reason
    )


def _metadata(
    context: EvidenceSummaryAnswerContextSchema,
    extra: Mapping[str, Any],
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "source": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_SOURCE,
        "policy_ref": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_POLICY_REF,
        "context_payload_type": context.payload_type,
        "context_payload_version": context.payload_version,
        "digest_count": len(context.digests),
        "no_model": True,
    }
    metadata.update(_compact_metadata(extra))
    return metadata


def _compact_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in metadata.items():
        if not isinstance(key, str):
            continue
        if _sensitive_text(key):
            continue
        if not isinstance(value, bool | int | float | str):
            continue
        if isinstance(value, str) and _sensitive_text(value):
            continue
        compact[key] = value
    return compact


def _sensitive_text(value: str) -> bool:
    normalized = value.lower()
    return any(
        marker in normalized
        for marker in (
            "authorization",
            "config",
            "cookie",
            "header",
            "html",
            "message",
            "observability",
            "password",
            "payload",
            "prompt",
            "raw",
            "response",
            "runtime",
            "secret",
            "token",
        )
    )


def _ordered_unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


__all__ = (
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_POLICY_REF",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_SOURCE",
    "build_no_model_evidence_summary_answer_result",
    "evidence_summary_answer_result_status_dict",
)
