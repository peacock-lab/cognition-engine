"""Build governed evidence digests from public governed facts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from typing import Any

from schemas.evidence_summary_answer import (
    GOVERNED_EVIDENCE_DIGEST_REF_PREFIX,
    GovernedEvidenceDigestSchema,
)
from schemas.external_readonly_governed_summary_facts import (
    ExternalReadonlyGovernedSummaryFactsSchema,
)


PRODUCT_APPLICATION_GOVERNED_EVIDENCE_DIGEST_SOURCE = (
    "product_application_assembly.governed_evidence_digest"
)
PRODUCT_APPLICATION_GOVERNED_EVIDENCE_DIGEST_POLICY_REF = (
    "policy://product-application-assembly/governed-evidence-digest/minimal-v1"
)


def build_governed_evidence_digest_from_external_readonly_facts(
    facts: ExternalReadonlyGovernedSummaryFactsSchema | Mapping[str, Any],
    *,
    digest_id: str | None = None,
    digest_ref: str | None = None,
    digest_generation_policy_ref: str | None = (
        PRODUCT_APPLICATION_GOVERNED_EVIDENCE_DIGEST_POLICY_REF
    ),
    topic_labels: Sequence[str] = (),
    risk_labels: Sequence[str] = (),
    metadata: Mapping[str, Any] | None = None,
) -> GovernedEvidenceDigestSchema:
    """Build one governed evidence digest from public governed facts."""

    facts_model = _facts_model(facts)
    resolved_digest_id = digest_id or _default_digest_id(facts_model)
    resolved_digest_ref = digest_ref or (
        f"{GOVERNED_EVIDENCE_DIGEST_REF_PREFIX}{resolved_digest_id}"
    )
    summary_facts = _summary_facts(facts_model)
    status = _digest_status(facts_model)
    answerability = _answerability(facts_model)
    allowed_for_model_context = (
        facts_model.status == "ready" and facts_model.allowed_for_model_context
    )
    blocking_reasons = _blocking_reasons(facts_model)
    warnings = _warnings(facts_model)

    return GovernedEvidenceDigestSchema(
        digest_id=resolved_digest_id,
        digest_ref=resolved_digest_ref,
        evidence_ref=facts_model.evidence_ref,
        evidence_output_ref=facts_model.evidence_output_path,
        source_url_host=facts_model.source_url_host,
        source_url_scheme=facts_model.source_url_scheme,
        runtime_status=f"governed_summary_facts_{facts_model.status}",
        status=status,
        reference_review_ready=facts_model.reference_review_ready,
        allowed_for_model_context=allowed_for_model_context,
        evidence_written=facts_model.evidence_written,
        content_hash=facts_model.content_hash,
        total_excerpt_chars=facts_model.total_fact_chars,
        blocking_reasons=blocking_reasons,
        warnings=warnings,
        summary_facts=summary_facts,
        topic_labels=list(topic_labels),
        risk_labels=list(risk_labels),
        answerability=answerability,
        digest_generation_policy_ref=digest_generation_policy_ref,
        digest_budget=facts_model.facts_budget,
        metadata=_metadata(facts_model, metadata or {}),
    )


def governed_evidence_digest_status_dict(
    digest: GovernedEvidenceDigestSchema | Mapping[str, Any],
) -> dict[str, Any]:
    """Return a JSON-ready public governed digest status dict."""

    model = (
        GovernedEvidenceDigestSchema.model_validate(digest)
        if isinstance(digest, Mapping)
        else digest
    )
    payload = model.model_dump(mode="json")
    raw_boundary_flags = {
        key: value
        for key, value in payload.get("raw_boundary_flags", {}).items()
        if value is True
    }
    payload["raw_boundary_flags"] = raw_boundary_flags
    return payload


def _facts_model(
    facts: ExternalReadonlyGovernedSummaryFactsSchema | Mapping[str, Any],
) -> ExternalReadonlyGovernedSummaryFactsSchema:
    if isinstance(facts, ExternalReadonlyGovernedSummaryFactsSchema):
        return facts
    return ExternalReadonlyGovernedSummaryFactsSchema.model_validate(facts)


def _summary_facts(
    facts: ExternalReadonlyGovernedSummaryFactsSchema,
) -> list[str]:
    if facts.status != "ready":
        return []
    return [fact.fact_text for fact in facts.facts]


def _digest_status(facts: ExternalReadonlyGovernedSummaryFactsSchema) -> str:
    if facts.status == "ready":
        return "ready"
    if facts.status == "blocked":
        return "blocked"
    return "empty"


def _answerability(facts: ExternalReadonlyGovernedSummaryFactsSchema) -> str:
    if facts.status == "ready":
        return "answerable"
    if facts.status == "blocked":
        return "blocked"
    return "insufficient_evidence"


def _blocking_reasons(
    facts: ExternalReadonlyGovernedSummaryFactsSchema,
) -> list[str]:
    if facts.status != "blocked":
        return []
    return list(facts.blocking_reasons) or [
        "upstream_governed_summary_facts_blocked"
    ]


def _warnings(facts: ExternalReadonlyGovernedSummaryFactsSchema) -> list[str]:
    warnings = list(facts.warnings)
    if facts.status == "empty":
        warnings.append("upstream_governed_summary_facts_empty")
    return _ordered_unique(warnings)


def _metadata(
    facts: ExternalReadonlyGovernedSummaryFactsSchema,
    extra: Mapping[str, Any],
) -> dict[str, Any]:
    source_metadata = _compact_metadata(facts.metadata)
    metadata: dict[str, Any] = {
        "source": PRODUCT_APPLICATION_GOVERNED_EVIDENCE_DIGEST_SOURCE,
        "source_contract": "ExternalReadonlyGovernedSummaryFactsSchema",
        "upstream_payload_type": facts.payload_type,
        "upstream_payload_version": facts.payload_version,
        "upstream_generation_policy_ref": facts.generation_policy_ref,
        "upstream_fact_count": facts.fact_count,
        "total_excerpt_chars_source": "governed_summary_facts.total_fact_chars",
    }
    for key in (
        "chunked",
        "fact_slice_count",
        "chunked_source_item_count",
        "chunking_strategy_ref",
    ):
        if key in source_metadata:
            metadata[f"upstream_{key}"] = source_metadata[key]
    metadata.update(_compact_metadata(extra))
    return {key: value for key, value in metadata.items() if value is not None}


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
            "message",
            "password",
            "payload",
            "prompt",
            "raw",
            "response",
            "secret",
            "token",
        )
    )


def _default_digest_id(facts: ExternalReadonlyGovernedSummaryFactsSchema) -> str:
    digest = hashlib.sha256(facts.evidence_ref.encode("utf-8")).hexdigest()
    return f"external-readonly-{digest[:16]}"


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


__all__ = (
    "PRODUCT_APPLICATION_GOVERNED_EVIDENCE_DIGEST_POLICY_REF",
    "PRODUCT_APPLICATION_GOVERNED_EVIDENCE_DIGEST_SOURCE",
    "build_governed_evidence_digest_from_external_readonly_facts",
    "governed_evidence_digest_status_dict",
)
