"""Build public governed summary facts from sanitized external-readonly envelopes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError
from schemas.evidence_summary_answer import (
    EXTERNAL_READONLY_EVIDENCE_REF_PREFIX,
    SUMMARY_FACT_MAX_CHARS,
)
from schemas.external_readonly_governed_summary_facts import (
    EXTERNAL_READONLY_GOVERNED_SUMMARY_FACT_REF_PREFIX,
    ExternalReadonlyGovernedSummaryFactSchema,
    ExternalReadonlyGovernedSummaryFactsSchema,
)

from external_readonly.url_fetch import ExternalReadonlyEvidenceEnvelope


EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_POLICY_REF = (
    "policy://external-readonly/governed-summary-facts/minimal-v1"
)
_FALLBACK_EVIDENCE_REF = (
    f"{EXTERNAL_READONLY_EVIDENCE_REF_PREFIX}governed-summary-facts/unavailable"
)


def build_external_readonly_governed_summary_facts(
    envelope: ExternalReadonlyEvidenceEnvelope | Mapping[str, Any] | None,
    *,
    evidence_output_path: str | None = None,
    evidence_written: bool = False,
    reference_review_ready: bool = True,
    generation_policy_ref: str | None = (
        EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_POLICY_REF
    ),
    facts_budget: int = SUMMARY_FACT_MAX_CHARS,
) -> ExternalReadonlyGovernedSummaryFactsSchema:
    """Build public governed facts from a sanitized evidence envelope."""

    view = _EnvelopeView.from_input(envelope)
    evidence_ref = _bundle_evidence_ref(view)
    if envelope is None:
        return _empty_facts(
            evidence_ref=evidence_ref,
            generation_policy_ref=generation_policy_ref,
            facts_budget=facts_budget,
            source_item_count=0,
            upstream_blocking_reason_count=0,
            upstream_warning_count=0,
        )

    blocking: list[str] = []
    if view.status != "valid":
        blocking.append("upstream_envelope_not_valid")
    if not view.allowed_for_model_context:
        blocking.append("context_not_allowed")
    if not evidence_written:
        blocking.append("evidence_not_written")
    if not reference_review_ready:
        blocking.append("reference_review_not_ready")
    if not view.items:
        blocking.append("context_items_required")
    if not _valid_evidence_ref(evidence_ref):
        blocking.append("evidence_ref_required")

    fact_inputs: list[_FactInput] = []
    for index, item in enumerate(view.items, start=1):
        item_mapping = _mapping_from_item(item)
        fact_input, item_blocking = _fact_input_from_item(
            item_mapping,
            index=index,
        )
        if item_blocking:
            blocking.extend(f"item_{index}_{reason}" for reason in item_blocking)
            continue
        fact_inputs.append(fact_input)

    if not fact_inputs and "context_items_required" not in blocking:
        blocking.append("governed_fact_text_required")

    if blocking:
        return _blocked_facts(
            evidence_ref=evidence_ref,
            blocking_reasons=blocking,
            generation_policy_ref=generation_policy_ref,
            facts_budget=facts_budget,
            source_item_count=len(view.items),
            upstream_blocking_reason_count=len(view.blocking_reasons),
            upstream_warning_count=len(view.warnings),
        )

    try:
        facts = tuple(
            ExternalReadonlyGovernedSummaryFactSchema(
                fact_ref=_fact_ref(evidence_ref, index),
                fact_text=fact_input.fact_text,
                fact_index=index,
                evidence_ref=evidence_ref,
                source_url_host=fact_input.source_url_host,
                content_hash=fact_input.content_hash,
                metadata=_fact_metadata(fact_input),
            )
            for index, fact_input in enumerate(fact_inputs, start=1)
        )
        source_url_host = _single_value(
            fact_input.source_url_host for fact_input in fact_inputs
        )
        content_hash = _single_value(
            fact_input.content_hash for fact_input in fact_inputs
        )
        total_fact_chars = sum(len(fact.fact_text) for fact in facts)
        return ExternalReadonlyGovernedSummaryFactsSchema(
            status="ready",
            evidence_ref=evidence_ref,
            evidence_output_path=evidence_output_path,
            source_url_host=source_url_host,
            source_url_scheme="https",
            reference_review_ready=True,
            allowed_for_model_context=True,
            evidence_written=True,
            content_hash=content_hash,
            facts=list(facts),
            fact_count=len(facts),
            total_fact_chars=total_fact_chars,
            generation_policy_ref=generation_policy_ref,
            facts_budget=facts_budget,
            metadata={
                "source_package": "external_readonly",
                "source_contract": "ExternalReadonlyEvidenceEnvelope",
                "source_item_count": len(view.items),
                "fact_source_count": len(fact_inputs),
                "upstream_blocking_reason_count": len(view.blocking_reasons),
                "upstream_warning_count": len(view.warnings),
            },
        )
    except ValidationError:
        return _blocked_facts(
            evidence_ref=evidence_ref,
            blocking_reasons=("governed_facts_validation_failed",),
            generation_policy_ref=generation_policy_ref,
            facts_budget=facts_budget,
            source_item_count=len(view.items),
            upstream_blocking_reason_count=len(view.blocking_reasons),
            upstream_warning_count=len(view.warnings),
        )


def external_readonly_governed_summary_facts_status_dict(
    facts: ExternalReadonlyGovernedSummaryFactsSchema | Mapping[str, Any],
) -> dict[str, Any]:
    """Return a JSON-ready public governed facts status dict."""

    model = (
        ExternalReadonlyGovernedSummaryFactsSchema.model_validate(facts)
        if isinstance(facts, Mapping)
        else facts
    )
    payload = model.model_dump(mode="json")
    raw_boundary_flags = {
        key: value
        for key, value in payload.get("raw_boundary_flags", {}).items()
        if value is True
    }
    payload["raw_boundary_flags"] = raw_boundary_flags
    return payload


class _EnvelopeView:
    def __init__(
        self,
        *,
        envelope_ref: str,
        status: str,
        allowed_for_model_context: bool,
        items: tuple[Any, ...],
        evidence_refs: tuple[str, ...],
        source_urls: tuple[str, ...],
        blocking_reasons: tuple[str, ...],
        warnings: tuple[str, ...],
    ) -> None:
        self.envelope_ref = envelope_ref
        self.status = status
        self.allowed_for_model_context = allowed_for_model_context
        self.items = items
        self.evidence_refs = evidence_refs
        self.source_urls = source_urls
        self.blocking_reasons = blocking_reasons
        self.warnings = warnings

    @classmethod
    def from_input(
        cls,
        envelope: ExternalReadonlyEvidenceEnvelope | Mapping[str, Any] | None,
    ) -> "_EnvelopeView":
        if envelope is None:
            return cls(
                envelope_ref="",
                status="",
                allowed_for_model_context=False,
                items=(),
                evidence_refs=(),
                source_urls=(),
                blocking_reasons=(),
                warnings=(),
            )
        return cls(
            envelope_ref=_string_value(_get_value(envelope, "envelope_ref")),
            status=_string_value(_get_value(envelope, "status")),
            allowed_for_model_context=bool(
                _get_value(envelope, "allowed_for_model_context", False)
            ),
            items=_sequence_value(_get_value(envelope, "model_context_items", ())),
            evidence_refs=tuple(
                _string_value(item)
                for item in _sequence_value(_get_value(envelope, "evidence_refs", ()))
            ),
            source_urls=tuple(
                _string_value(item)
                for item in _sequence_value(_get_value(envelope, "source_urls", ()))
            ),
            blocking_reasons=tuple(
                _string_value(item)
                for item in _sequence_value(
                    _get_value(envelope, "blocking_reasons", ())
                )
            ),
            warnings=tuple(
                _string_value(item)
                for item in _sequence_value(_get_value(envelope, "warnings", ()))
            ),
        )


class _FactInput:
    def __init__(
        self,
        *,
        fact_text: str,
        source_evidence_ref: str,
        source_url_host: str,
        content_hash: str,
        citation_index: int | None,
    ) -> None:
        self.fact_text = fact_text
        self.source_evidence_ref = source_evidence_ref
        self.source_url_host = source_url_host
        self.content_hash = content_hash
        self.citation_index = citation_index


def _fact_input_from_item(
    item: Mapping[str, Any],
    *,
    index: int,
) -> tuple[_FactInput, tuple[str, ...]]:
    blocking: list[str] = []
    fact_text = _string_value(item.get("sanitized_excerpt")).strip()
    source_evidence_ref = _string_value(item.get("evidence_ref")).strip()
    source_url = _string_value(item.get("source_url")).strip()
    content_hash = _string_value(item.get("content_hash")).strip()

    if not fact_text:
        blocking.append("governed_fact_text_required")
    if not _valid_evidence_ref(source_evidence_ref):
        blocking.append("evidence_ref_required")
    source_url_host = _https_host(source_url)
    if source_url_host is None:
        blocking.append("source_url_not_https")
        source_url_host = ""
    if not _valid_content_hash(content_hash):
        blocking.append("content_hash_invalid")

    citation_index = item.get("citation_index", index)
    if not isinstance(citation_index, int):
        citation_index = None

    return (
        _FactInput(
            fact_text=fact_text,
            source_evidence_ref=source_evidence_ref,
            source_url_host=source_url_host,
            content_hash=content_hash,
            citation_index=citation_index,
        ),
        tuple(blocking),
    )


def _blocked_facts(
    *,
    evidence_ref: str,
    blocking_reasons: Sequence[str],
    generation_policy_ref: str | None,
    facts_budget: int,
    source_item_count: int,
    upstream_blocking_reason_count: int,
    upstream_warning_count: int,
) -> ExternalReadonlyGovernedSummaryFactsSchema:
    return ExternalReadonlyGovernedSummaryFactsSchema(
        status="blocked",
        evidence_ref=_safe_evidence_ref(evidence_ref),
        allowed_for_model_context=False,
        blocking_reasons=_ordered_unique(blocking_reasons) or (
            "governed_facts_blocked",
        ),
        generation_policy_ref=generation_policy_ref,
        facts_budget=facts_budget,
        metadata={
            "source_package": "external_readonly",
            "source_item_count": source_item_count,
            "upstream_blocking_reason_count": upstream_blocking_reason_count,
            "upstream_warning_count": upstream_warning_count,
        },
    )


def _empty_facts(
    *,
    evidence_ref: str,
    generation_policy_ref: str | None,
    facts_budget: int,
    source_item_count: int,
    upstream_blocking_reason_count: int,
    upstream_warning_count: int,
) -> ExternalReadonlyGovernedSummaryFactsSchema:
    return ExternalReadonlyGovernedSummaryFactsSchema(
        status="empty",
        evidence_ref=_safe_evidence_ref(evidence_ref),
        allowed_for_model_context=False,
        generation_policy_ref=generation_policy_ref,
        facts_budget=facts_budget,
        metadata={
            "source_package": "external_readonly",
            "source_item_count": source_item_count,
            "upstream_blocking_reason_count": upstream_blocking_reason_count,
            "upstream_warning_count": upstream_warning_count,
        },
    )


def _bundle_evidence_ref(view: _EnvelopeView) -> str:
    valid_item_refs = tuple(ref for ref in view.evidence_refs if _valid_evidence_ref(ref))
    if len(valid_item_refs) == 1:
        return valid_item_refs[0]
    if _valid_evidence_ref(view.envelope_ref):
        return view.envelope_ref
    if valid_item_refs:
        return valid_item_refs[0]
    return _FALLBACK_EVIDENCE_REF


def _fact_metadata(fact_input: _FactInput) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "source_evidence_ref": fact_input.source_evidence_ref,
    }
    if fact_input.citation_index is not None:
        metadata["citation_index"] = fact_input.citation_index
    return metadata


def _fact_ref(evidence_ref: str, index: int) -> str:
    digest = hashlib.sha256(f"{evidence_ref}:{index}".encode("utf-8")).hexdigest()
    return f"{EXTERNAL_READONLY_GOVERNED_SUMMARY_FACT_REF_PREFIX}{digest[:16]}-{index}"


def _get_value(source: Mapping[str, Any] | object, key: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def _mapping_from_item(item: Any) -> Mapping[str, Any]:
    if isinstance(item, Mapping):
        return item
    return {}


def _sequence_value(value: Any) -> tuple[Any, ...]:
    if value is None or isinstance(value, (str, bytes, bytearray)):
        return ()
    if isinstance(value, Sequence):
        return tuple(value)
    return ()


def _string_value(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _safe_evidence_ref(evidence_ref: str) -> str:
    return evidence_ref if _valid_evidence_ref(evidence_ref) else _FALLBACK_EVIDENCE_REF


def _valid_evidence_ref(evidence_ref: str) -> bool:
    return evidence_ref.startswith(EXTERNAL_READONLY_EVIDENCE_REF_PREFIX) and (
        len(evidence_ref) > len(EXTERNAL_READONLY_EVIDENCE_REF_PREFIX)
    )


def _https_host(source_url: str) -> str | None:
    parsed = urlparse(source_url)
    if parsed.scheme != "https" or not parsed.hostname:
        return None
    if parsed.username or parsed.password:
        return None
    return parsed.hostname.lower()


def _valid_content_hash(content_hash: str) -> bool:
    if len(content_hash) != 64:
        return False
    return all(char in "0123456789abcdefABCDEF" for char in content_hash)


def _single_value(values: Sequence[str | None] | Any) -> str | None:
    unique = {value for value in values if value}
    if len(unique) == 1:
        return next(iter(unique))
    return None


def _ordered_unique(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return tuple(unique)
