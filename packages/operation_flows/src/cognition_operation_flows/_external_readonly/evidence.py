"""Candidate-only sanitized evidence envelope for external read-only references."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import ipaddress
import re
from typing import Any
from urllib.parse import urlparse

from cognition_operation_flows._external_readonly.network_gate import (
    TwfExternalReadonlyNetworkGateCandidate,
)


TWF_EXTERNAL_READONLY_EVIDENCE_STAGES = (
    "network_gate_binding",
    "source_boundary_review",
    "sanitized_excerpt_review",
    "content_hash_review",
    "model_context_projection",
    "sanitized_envelope_summary",
)
TWF_EXTERNAL_READONLY_EVIDENCE_REF_PREFIX = "evidence://external-readonly/"
TWF_EXTERNAL_READONLY_ALLOWED_ITEM_TYPES = frozenset(
    {"search_result", "url_context_excerpt", "fetched_excerpt"}
)
TWF_EXTERNAL_READONLY_MAX_EXCERPT_CHARS = 2_000
TWF_EXTERNAL_READONLY_MAX_TOTAL_EXCERPT_CHARS = 8_000
TWF_EXTERNAL_READONLY_SECRET_KEY_MARKERS = (
    "access_token",
    "api_key",
    "authorization",
    "cookie",
    "credential",
    "password",
    "private_key",
    "secret",
    "service_account_json",
    "session",
    "token",
)
TWF_EXTERNAL_READONLY_EXCERPT_FORBIDDEN_MARKERS = (
    "api_key=",
    "authorization:",
    "begin private key",
    "password=",
    "private_key=",
    "secret=",
    "service_account_json",
)


@dataclass(frozen=True)
class TwfExternalReadonlyEvidenceItemCandidate:
    """One sanitized external reference item eligible for model context."""

    evidence_ref: str
    source_url: str
    retrieved_at: str
    sanitized_excerpt: str
    citation_index: int
    item_type: str = "url_context_excerpt"
    source_title: str | None = None
    source_provider: str | None = None
    content_hash: str | None = None
    language: str | None = None
    mime_type: str | None = None
    raw_response_included: bool = False
    raw_html_included: bool = False
    full_page_content_included: bool = False
    raw_query_included: bool = False
    raw_url_context_included: bool = False
    cookies_included: bool = False
    auth_headers_included: bool = False
    tokens_included: bool = False
    script_content_included: bool = False
    form_data_included: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfExternalReadonlyEvidenceItemReviewCandidate:
    """Sanitized validation result for one external-readonly evidence item."""

    evidence_ref: str
    source_url: str
    citation_index: int
    item_type: str
    status: str
    allowed_for_model_context: bool
    excerpt_char_count: int
    content_hash: str
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfExternalReadonlyEvidenceEnvelopeCandidate:
    """Sanitized envelope passed from external retrieval into model context."""

    envelope_ref: str
    request_ref: str
    status: str
    allowed_for_model_context: bool
    item_reviews: tuple[TwfExternalReadonlyEvidenceItemReviewCandidate, ...]
    model_context_items: tuple[dict[str, Any], ...]
    evidence_refs: tuple[str, ...]
    source_urls: tuple[str, ...]
    total_excerpt_chars: int
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


def review_twf_external_readonly_evidence_item(
    item: TwfExternalReadonlyEvidenceItemCandidate,
) -> TwfExternalReadonlyEvidenceItemReviewCandidate:
    """Review one sanitized external evidence item without fetching content."""

    normalized_type = _normalize_token(item.item_type)
    excerpt = item.sanitized_excerpt.strip()
    computed_hash = _sha256_text(excerpt)
    blocking: list[str] = []
    warnings: list[str] = []

    if not _evidence_ref_allowed(item.evidence_ref):
        blocking.append("evidence_ref_not_external_readonly")
    if normalized_type not in TWF_EXTERNAL_READONLY_ALLOWED_ITEM_TYPES:
        blocking.append("item_type_not_allowed")
    if not _external_https_url_allowed(item.source_url):
        blocking.append("source_url_not_external_https")
    if not _valid_retrieved_at(item.retrieved_at):
        blocking.append("retrieved_at_invalid")
    if not isinstance(item.citation_index, int) or item.citation_index <= 0:
        blocking.append("citation_index_invalid")
    if not excerpt:
        blocking.append("sanitized_excerpt_required")
    if len(excerpt) > TWF_EXTERNAL_READONLY_MAX_EXCERPT_CHARS:
        blocking.append("sanitized_excerpt_too_large")
    if _excerpt_contains_forbidden_marker(excerpt):
        blocking.append("sanitized_excerpt_contains_secret_marker")
    if item.content_hash and item.content_hash != computed_hash:
        blocking.append("content_hash_mismatch")
    if item.raw_response_included:
        blocking.append("raw_response_forbidden")
    if item.raw_html_included:
        blocking.append("raw_html_forbidden")
    if item.full_page_content_included:
        blocking.append("full_page_content_forbidden")
    if item.raw_query_included:
        blocking.append("raw_query_forbidden")
    if item.raw_url_context_included:
        blocking.append("raw_url_context_forbidden")
    if item.cookies_included:
        blocking.append("cookies_forbidden")
    if item.auth_headers_included:
        blocking.append("auth_headers_forbidden")
    if item.tokens_included:
        blocking.append("tokens_forbidden")
    if item.script_content_included:
        blocking.append("script_content_forbidden")
    if item.form_data_included:
        blocking.append("form_data_forbidden")
    if _raw_secret_keys(item.metadata):
        blocking.append("raw_credential_material_forbidden")

    return TwfExternalReadonlyEvidenceItemReviewCandidate(
        evidence_ref=item.evidence_ref,
        source_url=item.source_url,
        citation_index=item.citation_index,
        item_type=normalized_type,
        status="valid" if not blocking else "blocked",
        allowed_for_model_context=not blocking,
        excerpt_char_count=len(excerpt),
        content_hash=computed_hash,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "candidate_only": True,
            "reference_only": True,
            "source_title_present": bool(item.source_title),
            "source_provider_present": bool(item.source_provider),
            "language_present": bool(item.language),
            "mime_type_present": bool(item.mime_type),
            "raw_metadata_included": False,
        },
    )


def build_twf_external_readonly_evidence_envelope(
    *,
    gate: TwfExternalReadonlyNetworkGateCandidate,
    items: Sequence[TwfExternalReadonlyEvidenceItemCandidate],
    envelope_ref: str,
    max_total_excerpt_chars: int = TWF_EXTERNAL_READONLY_MAX_TOTAL_EXCERPT_CHARS,
) -> TwfExternalReadonlyEvidenceEnvelopeCandidate:
    """Build a sanitized evidence envelope without network I/O or file writes."""

    item_reviews = tuple(
        review_twf_external_readonly_evidence_item(item) for item in items
    )
    blocking: list[str] = []
    warnings: list[str] = []
    if not _evidence_ref_allowed(envelope_ref):
        blocking.append("envelope_ref_not_external_readonly")
    if gate.status != "passed" or not gate.network_gate_open:
        blocking.append("network_gate_not_open")
    if gate.external_network_call_performed:
        blocking.append("network_gate_has_execution_fact")
    if gate.tool_execution_performed:
        blocking.append("network_gate_has_tool_execution_fact")
    if not items:
        blocking.append("evidence_items_required")
    for review in item_reviews:
        blocking.extend(
            f"{review.evidence_ref}:{reason}"
            for reason in review.blocking_reasons
        )
    evidence_refs = tuple(review.evidence_ref for review in item_reviews)
    source_urls = tuple(review.source_url for review in item_reviews)
    citation_indexes = tuple(review.citation_index for review in item_reviews)
    total_excerpt_chars = sum(review.excerpt_char_count for review in item_reviews)
    if len(evidence_refs) != len(set(evidence_refs)):
        blocking.append("duplicate_evidence_ref")
    if len(citation_indexes) != len(set(citation_indexes)):
        blocking.append("duplicate_citation_index")
    if total_excerpt_chars > max_total_excerpt_chars:
        blocking.append("total_excerpt_chars_exceeds_budget")

    allowed = not blocking
    model_context_items = (
        tuple(_model_context_item(item, review) for item, review in zip(items, item_reviews))
        if allowed
        else ()
    )
    return TwfExternalReadonlyEvidenceEnvelopeCandidate(
        envelope_ref=envelope_ref,
        request_ref=gate.request_ref,
        status="valid" if allowed else "blocked",
        allowed_for_model_context=allowed,
        item_reviews=item_reviews,
        model_context_items=model_context_items,
        evidence_refs=tuple(_ordered_unique(evidence_refs)),
        source_urls=tuple(_ordered_unique(source_urls)),
        total_excerpt_chars=total_excerpt_chars,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "candidate_only": True,
            "reference_only": True,
            "stages": list(TWF_EXTERNAL_READONLY_EVIDENCE_STAGES),
            "network_gate_status": gate.status,
            "network_gate_open": gate.network_gate_open,
            "network_gate_ref_present": bool(
                gate.metadata.get("network_gate_ref_present")
            ),
            "approval_ref_present": bool(gate.metadata.get("approval_ref_present")),
            "audit_ref_present": bool(gate.metadata.get("audit_ref_present")),
            "sanitized_evidence_ref_present": bool(
                gate.metadata.get("sanitized_evidence_ref_present")
            ),
            "does_not_execute_tool": True,
            "does_not_perform_external_network_calls": True,
            "does_not_write_files": True,
            "raw_response_included": False,
            "full_page_content_included": False,
            "raw_metadata_included": False,
            "item_count": len(item_reviews),
            "max_total_excerpt_chars": max_total_excerpt_chars,
        },
    )


def twf_external_readonly_evidence_item_review_status_dict(
    review: TwfExternalReadonlyEvidenceItemReviewCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready sanitized item review summary."""

    return {
        "evidence_ref": review.evidence_ref,
        "source_url": review.source_url,
        "citation_index": review.citation_index,
        "item_type": review.item_type,
        "status": review.status,
        "allowed_for_model_context": review.allowed_for_model_context,
        "excerpt_char_count": review.excerpt_char_count,
        "content_hash": review.content_hash,
        "blocking_reasons": list(review.blocking_reasons),
        "warnings": list(review.warnings),
        "metadata": dict(review.metadata),
    }


def twf_external_readonly_evidence_envelope_status_dict(
    envelope: TwfExternalReadonlyEvidenceEnvelopeCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready sanitized evidence envelope summary."""

    return {
        "envelope_ref": envelope.envelope_ref,
        "request_ref": envelope.request_ref,
        "status": envelope.status,
        "allowed_for_model_context": envelope.allowed_for_model_context,
        "evidence_refs": list(envelope.evidence_refs),
        "source_urls": list(envelope.source_urls),
        "total_excerpt_chars": envelope.total_excerpt_chars,
        "blocking_reasons": list(envelope.blocking_reasons),
        "warnings": list(envelope.warnings),
        "item_reviews": [
            twf_external_readonly_evidence_item_review_status_dict(review)
            for review in envelope.item_reviews
        ],
        "model_context_items": [dict(item) for item in envelope.model_context_items],
        "metadata": dict(envelope.metadata),
    }


def _model_context_item(
    item: TwfExternalReadonlyEvidenceItemCandidate,
    review: TwfExternalReadonlyEvidenceItemReviewCandidate,
) -> dict[str, Any]:
    return {
        "citation_index": item.citation_index,
        "evidence_ref": item.evidence_ref,
        "source_url": item.source_url,
        "source_title": item.source_title,
        "retrieved_at": item.retrieved_at,
        "item_type": review.item_type,
        "sanitized_excerpt": item.sanitized_excerpt.strip(),
        "content_hash": review.content_hash,
    }


def _evidence_ref_allowed(value: str | None) -> bool:
    return _present(value) and str(value).strip().startswith(
        TWF_EXTERNAL_READONLY_EVIDENCE_REF_PREFIX
    ) and len(str(value).strip()) > len(TWF_EXTERNAL_READONLY_EVIDENCE_REF_PREFIX)


def _external_https_url_allowed(value: str) -> bool:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host in {"localhost"} or host.endswith(".localhost") or host.endswith(".local"):
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True
    return not (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _valid_retrieved_at(value: str) -> bool:
    text = value.strip()
    if "T" not in text:
        return False
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _excerpt_contains_forbidden_marker(value: str) -> bool:
    lower = value.lower()
    return any(
        marker in lower for marker in TWF_EXTERNAL_READONLY_EXCERPT_FORBIDDEN_MARKERS
    )


def _raw_secret_keys(raw_config: Mapping[str, Any]) -> tuple[str, ...]:
    keys: list[str] = []
    for key, value in raw_config.items():
        key_text = str(key).lower()
        if any(
            marker in key_text
            for marker in TWF_EXTERNAL_READONLY_SECRET_KEY_MARKERS
        ):
            if value:
                keys.append(str(key))
        if isinstance(value, Mapping):
            nested = _raw_secret_keys(value)
            keys.extend(f"{key}.{item}" for item in nested)
    return tuple(_ordered_unique(keys))


def _present(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def _normalize_token(value: str) -> str:
    return value.strip().replace("-", "_").replace(" ", "_").lower()


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
