"""Build same-process evidence summary answer follow-up contracts."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from product_application_assembly.evidence_summary_answer_context import (
    build_evidence_summary_answer_context,
)
from schemas.evidence_summary_answer import (
    EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_REF_PREFIX,
    EvidenceSummaryAnswerContextSchema,
    EvidenceSummaryAnswerFollowUpSeedSchema,
    EvidenceSummaryAnswerRefSchema,
    EvidenceSummaryAnswerResultSchema,
    GovernedEvidenceDigestSchema,
)


PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_SOURCE = (
    "product_application_assembly.evidence_summary_answer_follow_up"
)
PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_POLICY_REF = (
    "policy://product-application-assembly/evidence-summary-answer/"
    "follow-up/same-process-v1"
)
EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_INTERACTION_MODE = (
    "evidence_summary_answer_follow_up_generation"
)


def build_evidence_summary_answer_follow_up_seed(
    result: EvidenceSummaryAnswerResultSchema | Mapping[str, Any],
    *,
    seed_id: str | None = None,
    seed_ref: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> EvidenceSummaryAnswerFollowUpSeedSchema:
    """Build a public seed for same-process follow-up over the same evidence."""

    result_model = _result_model(result)
    derived_seed_id = seed_id or _stable_seed_id(
        result_model.request_id,
        result_model.digest_refs_used,
    )
    derived_seed_ref = seed_ref or f"{EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_REF_PREFIX}{derived_seed_id}"
    follow_up_allowed = (
        result_model.status == "success"
        and bool(result_model.digest_refs_used)
        and bool(result_model.evidence_refs_used)
    )
    blocking_reasons = [] if follow_up_allowed else _blocking_reasons(result_model)
    return EvidenceSummaryAnswerFollowUpSeedSchema(
        seed_id=derived_seed_id,
        seed_ref=derived_seed_ref,
        source_request_id=result_model.request_id,
        source_result_status=result_model.status,
        digest_refs=_ordered_unique(result_model.digest_refs_used),
        evidence_refs=list(result_model.evidence_refs_used),
        additional_refs=list(result_model.additional_refs_used),
        follow_up_allowed=follow_up_allowed,
        temporary_only=True,
        durable_session=False,
        memory_enabled=False,
        blocking_reasons=blocking_reasons,
        warnings=_ordered_unique(result_model.warnings),
        metadata=_metadata(
            {
                "digest_ref_count": len(result_model.digest_refs_used),
                "evidence_ref_count": len(result_model.evidence_refs_used),
                **dict(metadata or {}),
            }
        ),
    )


def build_evidence_summary_answer_follow_up_context(
    seed: EvidenceSummaryAnswerFollowUpSeedSchema | Mapping[str, Any],
    *,
    request_id: str,
    follow_up_question: str,
    digests: Sequence[GovernedEvidenceDigestSchema | Mapping[str, Any]],
    model_context_budget: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> EvidenceSummaryAnswerContextSchema:
    """Build a new answer context from a follow-up seed and existing digests."""

    seed_model = _seed_model(seed)
    if not seed_model.follow_up_allowed:
        raise ValueError("evidence_summary_answer_follow_up_not_allowed")

    digest_models = _digest_models(digests)
    _raise_if_seed_digest_refs_not_covered(seed_model, digest_models)
    return build_evidence_summary_answer_context(
        request_id=request_id,
        user_question=follow_up_question,
        digests=digest_models,
        evidence_refs=list(seed_model.evidence_refs),
        additional_refs=list(seed_model.additional_refs),
        model_context_budget=model_context_budget,
        metadata={
            "source": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_SOURCE,
            "policy_ref": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_POLICY_REF,
            "interaction_mode": EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_INTERACTION_MODE,
            "follow_up": True,
            "follow_up_seed_ref": seed_model.seed_ref,
            "follow_up_source_request_id": seed_model.source_request_id,
            "temporary_only": True,
            "durable_session": False,
            "memory_enabled": False,
            **dict(metadata or {}),
        },
    )


def evidence_summary_answer_follow_up_seed_status_dict(
    seed: EvidenceSummaryAnswerFollowUpSeedSchema | Mapping[str, Any],
) -> dict[str, Any]:
    """Return a JSON-ready public follow-up seed dict."""

    model = _seed_model(seed)
    return model.model_dump(mode="json")


def _result_model(
    result: EvidenceSummaryAnswerResultSchema | Mapping[str, Any],
) -> EvidenceSummaryAnswerResultSchema:
    if isinstance(result, EvidenceSummaryAnswerResultSchema):
        return result
    return EvidenceSummaryAnswerResultSchema.model_validate(result)


def _seed_model(
    seed: EvidenceSummaryAnswerFollowUpSeedSchema | Mapping[str, Any],
) -> EvidenceSummaryAnswerFollowUpSeedSchema:
    if isinstance(seed, EvidenceSummaryAnswerFollowUpSeedSchema):
        return seed
    return EvidenceSummaryAnswerFollowUpSeedSchema.model_validate(seed)


def _digest_models(
    digests: Sequence[GovernedEvidenceDigestSchema | Mapping[str, Any]],
) -> list[GovernedEvidenceDigestSchema]:
    return [
        item
        if isinstance(item, GovernedEvidenceDigestSchema)
        else GovernedEvidenceDigestSchema.model_validate(item)
        for item in digests
    ]


def _raise_if_seed_digest_refs_not_covered(
    seed: EvidenceSummaryAnswerFollowUpSeedSchema,
    digests: Sequence[GovernedEvidenceDigestSchema],
) -> None:
    available_refs = {digest.digest_ref for digest in digests}
    missing = sorted(set(seed.digest_refs) - available_refs)
    if missing:
        raise ValueError(
            "follow-up seed digest_refs are not covered by digests: "
            + ", ".join(missing)
        )


def _blocking_reasons(result: EvidenceSummaryAnswerResultSchema) -> list[str]:
    if result.status != "success":
        return [f"source_result_status_not_success:{result.status}"]
    reasons = []
    if not result.digest_refs_used:
        reasons.append("source_result_digest_refs_missing")
    if not result.evidence_refs_used:
        reasons.append("source_result_evidence_refs_missing")
    return reasons or ["source_result_follow_up_not_available"]


def _stable_seed_id(request_id: str, digest_refs: Sequence[str]) -> str:
    seed_material = "\n".join((request_id, *_ordered_unique(digest_refs)))
    digest = hashlib.sha256(seed_material.encode("utf-8")).hexdigest()[:16]
    return f"seed-{digest}"


def _metadata(extra: Mapping[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "source": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_SOURCE,
        "policy_ref": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_POLICY_REF,
        "temporary_only": True,
        "durable_session": False,
        "memory_enabled": False,
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
    "EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_INTERACTION_MODE",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_POLICY_REF",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_SOURCE",
    "build_evidence_summary_answer_follow_up_context",
    "build_evidence_summary_answer_follow_up_seed",
    "evidence_summary_answer_follow_up_seed_status_dict",
)
