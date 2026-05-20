"""Build evidence summary answer contexts from public governed digests."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from schemas.evidence_summary_answer import (
    EvidenceSummaryAnswerContextSchema,
    EvidenceSummaryAnswerRefSchema,
    GovernedEvidenceDigestSchema,
)


PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_SOURCE = (
    "product_application_assembly.evidence_summary_answer_context"
)
PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_ANSWER_POLICY_REF = (
    "policy://product-application-assembly/evidence-summary-answer/answer/minimal-v1"
)
PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_CITATION_POLICY_REF = (
    "policy://product-application-assembly/evidence-summary-answer/citation/minimal-v1"
)


def build_evidence_summary_answer_context(
    *,
    request_id: str,
    user_question: str,
    digests: Sequence[GovernedEvidenceDigestSchema | Mapping[str, Any]],
    evidence_refs: Sequence[EvidenceSummaryAnswerRefSchema | Mapping[str, Any]]
    | None = None,
    additional_refs: Sequence[EvidenceSummaryAnswerRefSchema | Mapping[str, Any]]
    | None = None,
    answer_policy_ref: str | None = (
        PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_ANSWER_POLICY_REF
    ),
    citation_policy_ref: str | None = (
        PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_CITATION_POLICY_REF
    ),
    model_context_budget: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> EvidenceSummaryAnswerContextSchema:
    """Build a structured evidence summary answer context."""

    digest_models = [_digest_model(digest) for digest in digests]
    context_evidence_refs = (
        [_ref_model(ref) for ref in evidence_refs]
        if evidence_refs is not None
        else _default_evidence_refs(digest_models)
    )
    context_additional_refs = (
        [_ref_model(ref) for ref in additional_refs]
        if additional_refs is not None
        else _default_additional_refs(digest_models)
    )

    return EvidenceSummaryAnswerContextSchema(
        request_id=request_id,
        user_question=user_question,
        digests=digest_models,
        evidence_refs=context_evidence_refs,
        additional_refs=context_additional_refs,
        answer_policy_ref=answer_policy_ref,
        citation_policy_ref=citation_policy_ref,
        model_context_budget=model_context_budget,
        metadata=_metadata(digest_models, metadata or {}, evidence_refs),
    )


def evidence_summary_answer_context_status_dict(
    context: EvidenceSummaryAnswerContextSchema | Mapping[str, Any],
) -> dict[str, Any]:
    """Return a JSON-ready public evidence summary answer context dict."""

    model = (
        EvidenceSummaryAnswerContextSchema.model_validate(context)
        if isinstance(context, Mapping)
        else context
    )
    return model.model_dump(mode="json")


def _digest_model(
    digest: GovernedEvidenceDigestSchema | Mapping[str, Any],
) -> GovernedEvidenceDigestSchema:
    if isinstance(digest, GovernedEvidenceDigestSchema):
        return digest
    return GovernedEvidenceDigestSchema.model_validate(digest)


def _ref_model(
    ref: EvidenceSummaryAnswerRefSchema | Mapping[str, Any],
) -> EvidenceSummaryAnswerRefSchema:
    if isinstance(ref, EvidenceSummaryAnswerRefSchema):
        return ref
    return EvidenceSummaryAnswerRefSchema.model_validate(ref)


def _default_evidence_refs(
    digests: Sequence[GovernedEvidenceDigestSchema],
) -> list[EvidenceSummaryAnswerRefSchema]:
    return [
        EvidenceSummaryAnswerRefSchema(
            ref=evidence_ref,
            kind="external_readonly_evidence",
            purpose="answer_context",
        )
        for evidence_ref in _ordered_unique(digest.evidence_ref for digest in digests)
    ]


def _default_additional_refs(
    digests: Sequence[GovernedEvidenceDigestSchema],
) -> list[EvidenceSummaryAnswerRefSchema]:
    return [
        EvidenceSummaryAnswerRefSchema(
            ref=digest_ref,
            kind="governed_evidence_digest",
            purpose="digest_context",
        )
        for digest_ref in _ordered_unique(digest.digest_ref for digest in digests)
    ]


def _metadata(
    digests: Sequence[GovernedEvidenceDigestSchema],
    extra: Mapping[str, Any],
    evidence_refs: Sequence[EvidenceSummaryAnswerRefSchema | Mapping[str, Any]]
    | None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "source": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_SOURCE,
        "digest_count": len(digests),
        "refs_source": "explicit" if evidence_refs is not None else "derived_from_digest",
        "readonly": True,
        "summary_only": True,
        "does_not_read_files": True,
        "does_not_write_files": True,
        "does_not_call_network": True,
        "does_not_call_model": True,
        "does_not_call_runtime": True,
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
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_ANSWER_POLICY_REF",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_CITATION_POLICY_REF",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_SOURCE",
    "build_evidence_summary_answer_context",
    "evidence_summary_answer_context_status_dict",
)
