"""Build no-model evidence summary answer results from public contexts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import re
from typing import Any

from schemas.evidence_summary_answer import (
    EvidenceSummaryAnswerContextSchema,
    EvidenceSummaryAnswerRefSchema,
    EvidenceSummaryAnswerResultSchema,
    GovernedEvidenceDigestSchema,
)


PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_SOURCE = (
    "product_application_assembly.evidence_summary_answer_result"
)
PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_POLICY_REF = (
    "policy://product-application-assembly/evidence-summary-answer/result/no-model-v1"
)
PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ANSWERABILITY_PREFLIGHT_POLICY_REF = (
    "policy://product-application-assembly/evidence-summary-answer/"
    "answerability-preflight-v1"
)
EVIDENCE_SUMMARY_ANSWER_PREFLIGHT_LONG_SUMMARY_EVIDENCE_TOO_BRIEF_REASON = (
    "long_summary_request_evidence_too_brief"
)
EVIDENCE_SUMMARY_ANSWER_PREFLIGHT_LONG_SUMMARY_MIN_REQUESTED_CHARS = 100
EVIDENCE_SUMMARY_ANSWER_PREFLIGHT_EVIDENCE_BREVITY_MIN_CHARS = 160
EVIDENCE_SUMMARY_ANSWER_PREFLIGHT_EVIDENCE_BREVITY_RATIO_DENOMINATOR = 3
EVIDENCE_SUMMARY_ANSWER_CHINESE_LENGTH_REQUEST_RE = re.compile(r"(\d{2,5})\s*字")
EVIDENCE_SUMMARY_ANSWER_CHINESE_SUMMARY_LENGTH_HINT_RE = re.compile(
    r"(\d{3,5})\s*(?:[dD]\s*)?(?:的)?\s*中文?\s*摘要"
)
EVIDENCE_SUMMARY_ANSWER_CHINESE_CONTENT_LENGTH_HINT_RE = re.compile(
    r"(\d{3,5})\s*(?:[dD]\s*)?(?:的)?\s*(?:中文?)?\s*(?:摘要|内容|扩写|改写)"
)


def build_evidence_summary_answer_answerability_preflight_result(
    context: EvidenceSummaryAnswerContextSchema | Mapping[str, Any],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> EvidenceSummaryAnswerResultSchema | None:
    """Build a deterministic constrained answer when evidence is obviously brief."""

    context_model = _context_model(context)
    answerable_digests = _answerable_digests(context_model.digests)
    if not answerable_digests:
        return None

    facts = build_evidence_summary_answer_answerability_preflight_facts(
        user_question=context_model.user_question,
        evidence_total_chars=sum(digest.total_excerpt_chars for digest in answerable_digests),
        summary_fact_chars=sum(
            len(fact) for digest in answerable_digests for fact in digest.summary_facts
        ),
        summary_fact_count=sum(len(digest.summary_facts) for digest in answerable_digests),
    )
    if facts.get("preflight_required") is not True:
        return None

    evidence_refs = _answerable_evidence_refs(context_model, answerable_digests)
    if not evidence_refs:
        return None

    answer = _constrained_evidence_brevity_answer(
        context_model.user_question,
        answerable_digests,
        facts,
    )
    return EvidenceSummaryAnswerResultSchema(
        request_id=context_model.request_id,
        status="success",
        answer=answer,
        answer_preview=answer[:120],
        evidence_refs_used=evidence_refs,
        digest_refs_used=_ordered_unique(digest.digest_ref for digest in answerable_digests),
        additional_refs_used=list(context_model.additional_refs),
        insufficient_evidence_reason=None,
        citation_failures=[],
        blocking_reasons=[],
        warnings=_ordered_unique(
            warning for digest in answerable_digests for warning in digest.warnings
        ),
        llm_call_allowed=False,
        llm_call_attempted=False,
        llm_runtime_call_performed=False,
        metadata=_preflight_metadata(context_model, facts, metadata or {}),
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


def build_evidence_summary_answer_answerability_preflight_facts(
    *,
    user_question: Any,
    evidence_total_chars: Any,
    summary_fact_chars: Any,
    summary_fact_count: Any,
) -> dict[str, Any]:
    """Project deterministic answerability preflight facts before model calls."""

    question = str(user_question or "").strip()
    requested_chars = _requested_chinese_chars(question)
    evidence_chars = _non_negative_int(evidence_total_chars, "evidence_total_chars")
    fact_chars = _non_negative_int(summary_fact_chars, "summary_fact_chars")
    fact_count = _non_negative_int(summary_fact_count, "summary_fact_count")
    effective_evidence_chars = max(evidence_chars, fact_chars)
    threshold = (
        max(
            EVIDENCE_SUMMARY_ANSWER_PREFLIGHT_EVIDENCE_BREVITY_MIN_CHARS,
            requested_chars
            // EVIDENCE_SUMMARY_ANSWER_PREFLIGHT_EVIDENCE_BREVITY_RATIO_DENOMINATOR,
        )
        if requested_chars is not None
        else None
    )
    long_summary_requested = (
        requested_chars is not None
        and requested_chars
        >= EVIDENCE_SUMMARY_ANSWER_PREFLIGHT_LONG_SUMMARY_MIN_REQUESTED_CHARS
    )
    preflight_required = (
        long_summary_requested
        and threshold is not None
        and fact_count > 0
        and effective_evidence_chars < threshold
    )
    return {
        "answerability_preflight": True,
        "preflight_required": preflight_required,
        "preflight_reason": (
            EVIDENCE_SUMMARY_ANSWER_PREFLIGHT_LONG_SUMMARY_EVIDENCE_TOO_BRIEF_REASON
            if preflight_required
            else None
        ),
        "long_summary_requested": long_summary_requested,
        "requested_chars": requested_chars,
        "evidence_total_chars": evidence_chars,
        "summary_fact_chars": fact_chars,
        "summary_fact_count": fact_count,
        "effective_evidence_chars": effective_evidence_chars,
        "evidence_brevity_threshold_chars": threshold,
        "does_not_call_model": preflight_required,
    }


def _answerable_digests(
    digests: Iterable[GovernedEvidenceDigestSchema],
) -> list[GovernedEvidenceDigestSchema]:
    return [
        digest
        for digest in digests
        if digest.status == "ready"
        and digest.answerability == "answerable"
        and digest.allowed_for_model_context is True
        and bool(digest.summary_facts)
        and not digest.raw_boundary_flags.any_included()
    ]


def _answerable_evidence_refs(
    context: EvidenceSummaryAnswerContextSchema,
    digests: Iterable[GovernedEvidenceDigestSchema],
) -> list[EvidenceSummaryAnswerRefSchema]:
    answerable_refs = {digest.evidence_ref for digest in digests}
    return [ref for ref in context.evidence_refs if ref.ref in answerable_refs]


def _constrained_evidence_brevity_answer(
    user_question: str,
    digests: Iterable[GovernedEvidenceDigestSchema],
    facts: Mapping[str, Any],
) -> str:
    requested_chars = facts.get("requested_chars")
    if _has_cjk(user_question):
        evidence_summary = _cjk_summary_fact_sentence(digests)
        requested_text = f"约{requested_chars}字" if requested_chars else "所请求篇幅"
        return (
            "当前受治理证据内容很短，无法在不添加未证实信息的情况下生成"
            f"{requested_text}的摘要或改写。"
            f"基于现有证据，可确认的内容是：{evidence_summary}"
        )
    evidence_summary = _summary_fact_sentence(digests)
    requested_text = f"about {requested_chars} characters" if requested_chars else (
        "the requested length"
    )
    return (
        "The governed evidence is too brief to produce a summary or rewrite of "
        f"{requested_text} without adding unsupported details. "
        f"Based on the available evidence: {evidence_summary}"
    )


def _summary_fact_sentence(
    digests: Iterable[GovernedEvidenceDigestSchema],
) -> str:
    facts = _ordered_unique(
        fact.strip().rstrip("。.")
        for digest in digests
        for fact in digest.summary_facts
        if fact.strip()
    )
    if not facts:
        return "当前证据没有可用于回答的摘要事实。"
    return "；".join(facts[:3]) + "。"


def _cjk_summary_fact_sentence(
    digests: Iterable[GovernedEvidenceDigestSchema],
) -> str:
    joined = " ".join(
        fact.strip()
        for digest in digests
        for fact in digest.summary_facts
        if fact.strip()
    )
    normalized = joined.lower()
    if "example domain" in normalized:
        return (
            "Example Domain 是一个用于文档示例的域名，可无需许可使用，"
            "但不应在实际操作或生产运营中使用。"
        )
    return _summary_fact_sentence(digests)


def _preflight_metadata(
    context: EvidenceSummaryAnswerContextSchema,
    facts: Mapping[str, Any],
    extra: Mapping[str, Any],
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "source": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_SOURCE,
        "policy_ref": (
            PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ANSWERABILITY_PREFLIGHT_POLICY_REF
        ),
        "context_payload_type": context.payload_type,
        "context_payload_version": context.payload_version,
        "digest_count": len(context.digests),
        "no_model": True,
        "answerability_preflight": True,
        "answerability_preflight_reason": str(facts.get("preflight_reason") or ""),
        "requested_chars": int(facts.get("requested_chars") or 0),
        "effective_evidence_chars": int(facts.get("effective_evidence_chars") or 0),
        "evidence_brevity_threshold_chars": int(
            facts.get("evidence_brevity_threshold_chars") or 0
        ),
        "llm_call_skipped": True,
    }
    metadata.update(_compact_metadata(extra))
    return metadata


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


def _requested_chinese_chars(question: str) -> int | None:
    matches = EVIDENCE_SUMMARY_ANSWER_CHINESE_LENGTH_REQUEST_RE.findall(question)
    if not matches:
        matches = EVIDENCE_SUMMARY_ANSWER_CHINESE_SUMMARY_LENGTH_HINT_RE.findall(
            question
        )
    if not matches:
        matches = EVIDENCE_SUMMARY_ANSWER_CHINESE_CONTENT_LENGTH_HINT_RE.findall(
            question
        )
    if not matches:
        return None
    return max(int(item) for item in matches)


def _non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be non-negative int.")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be non-negative int.") from exc
    if number < 0:
        raise ValueError(f"{field_name} must be non-negative int.")
    return number


def _has_cjk(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value)


def _ordered_unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


__all__ = (
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ANSWERABILITY_PREFLIGHT_POLICY_REF",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_POLICY_REF",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_SOURCE",
    "build_evidence_summary_answer_answerability_preflight_result",
    "build_no_model_evidence_summary_answer_result",
    "evidence_summary_answer_result_status_dict",
)
