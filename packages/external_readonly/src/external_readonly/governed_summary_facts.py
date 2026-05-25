"""Build public governed summary facts from sanitized external-readonly envelopes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError
from schemas.evidence_summary_answer import (
    EXTERNAL_READONLY_EVIDENCE_REF_PREFIX,
    SUMMARY_FACT_ITEM_MAX_CHARS,
    SUMMARY_FACT_MAX_CHARS,
    SUMMARY_FACT_MAX_ITEMS,
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
EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_CHUNKING_POLICY_REF = (
    "policy://external-readonly/chunking/fact-slice-v1"
)
_FALLBACK_EVIDENCE_REF = (
    f"{EXTERNAL_READONLY_EVIDENCE_REF_PREFIX}governed-summary-facts/unavailable"
)
_CHUNK_BOUNDARY_MARKERS = (
    "\n\n",
    "\n",
    "。",
    "！",
    "？",
    ".",
    "!",
    "?",
    "；",
    ";",
    "，",
    ",",
    " ",
)
_MIN_NATURAL_CHUNK_CHARS = 120


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
    fact_chars_used = 0
    source_items_chunked = 0
    chunk_warnings: list[str] = []
    stop_collecting = False
    for index, item in enumerate(view.items, start=1):
        item_mapping = _mapping_from_item(item)
        item_fact_inputs, item_blocking, item_warnings = _fact_inputs_from_item(
            item_mapping,
            index=index,
        )
        chunk_warnings.extend(item_warnings)
        if item_blocking:
            blocking.extend(f"item_{index}_{reason}" for reason in item_blocking)
            continue
        if len(item_fact_inputs) > 1:
            source_items_chunked += 1
        for fact_input in item_fact_inputs:
            if len(fact_inputs) >= SUMMARY_FACT_MAX_ITEMS:
                chunk_warnings.append("governed_facts_chunk_item_limit_exhausted")
                stop_collecting = True
                break
            next_fact_chars = fact_chars_used + len(fact_input.fact_text)
            if next_fact_chars > facts_budget:
                chunk_warnings.append("governed_facts_chunk_budget_exhausted")
                stop_collecting = True
                break
            fact_inputs.append(fact_input)
            fact_chars_used = next_fact_chars
        if stop_collecting:
            break

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
        source_item_indexes = {
            fact_input.source_item_index for fact_input in fact_inputs
        }
        chunked = any(fact_input.chunk_count > 1 for fact_input in fact_inputs)
        metadata: dict[str, Any] = {
            "source_package": "external_readonly",
            "source_contract": "ExternalReadonlyEvidenceEnvelope",
            "source_item_count": len(view.items),
            "fact_source_count": len(source_item_indexes),
            "upstream_blocking_reason_count": len(view.blocking_reasons),
            "upstream_warning_count": len(view.warnings),
            "chunked": chunked,
            "fact_slice_count": len(fact_inputs),
            "chunked_source_item_count": source_items_chunked,
        }
        if chunked:
            metadata["chunking_strategy_ref"] = (
                EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_CHUNKING_POLICY_REF
            )
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
            warnings=_ordered_unique(chunk_warnings),
            metadata=metadata,
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
        source_item_index: int,
        chunk_index: int,
        chunk_count: int,
        source_char_start: int,
        source_char_end: int,
        source_excerpt_chars: int,
        chunking_strategy_ref: str | None,
    ) -> None:
        self.fact_text = fact_text
        self.source_evidence_ref = source_evidence_ref
        self.source_url_host = source_url_host
        self.content_hash = content_hash
        self.citation_index = citation_index
        self.source_item_index = source_item_index
        self.chunk_index = chunk_index
        self.chunk_count = chunk_count
        self.source_char_start = source_char_start
        self.source_char_end = source_char_end
        self.source_excerpt_chars = source_excerpt_chars
        self.chunking_strategy_ref = chunking_strategy_ref


class _FactChunk:
    def __init__(
        self,
        *,
        text: str,
        start: int,
        end: int,
    ) -> None:
        self.text = text
        self.start = start
        self.end = end


def _fact_inputs_from_item(
    item: Mapping[str, Any],
    *,
    index: int,
) -> tuple[tuple[_FactInput, ...], tuple[str, ...], tuple[str, ...]]:
    blocking: list[str] = []
    warnings: list[str] = []
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

    if blocking:
        return (), tuple(blocking), tuple(warnings)

    chunks = _split_fact_text(fact_text, max_chars=SUMMARY_FACT_ITEM_MAX_CHARS)
    chunk_count = len(chunks)
    if chunk_count > 1:
        warnings.append("governed_facts_chunked")

    fact_inputs = tuple(
        _FactInput(
            fact_text=chunk.text,
            source_evidence_ref=source_evidence_ref,
            source_url_host=source_url_host,
            content_hash=content_hash,
            citation_index=citation_index,
            source_item_index=index,
            chunk_index=chunk_index,
            chunk_count=chunk_count,
            source_char_start=chunk.start,
            source_char_end=chunk.end,
            source_excerpt_chars=len(fact_text),
            chunking_strategy_ref=(
                EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_CHUNKING_POLICY_REF
                if chunk_count > 1
                else None
            ),
        )
        for chunk_index, chunk in enumerate(chunks, start=1)
    )
    return fact_inputs, tuple(blocking), tuple(warnings)


def _split_fact_text(text: str, *, max_chars: int) -> tuple[_FactChunk, ...]:
    if len(text) <= max_chars:
        return (_FactChunk(text=text, start=0, end=len(text)),)

    chunks: list[_FactChunk] = []
    cursor = 0
    text_length = len(text)
    while cursor < text_length:
        while cursor < text_length and text[cursor].isspace():
            cursor += 1
        if cursor >= text_length:
            break

        hard_end = min(cursor + max_chars, text_length)
        end = hard_end
        if hard_end < text_length:
            end = _best_chunk_boundary(text, start=cursor, hard_end=hard_end)

        chunk_text = text[cursor:end].strip()
        if chunk_text:
            raw_chunk = text[cursor:end]
            stripped_start = cursor + len(raw_chunk) - len(raw_chunk.lstrip())
            stripped_end = end - (len(raw_chunk) - len(raw_chunk.rstrip()))
            chunks.append(
                _FactChunk(
                    text=chunk_text,
                    start=stripped_start,
                    end=stripped_end,
                )
            )
        cursor = end

    if not chunks:
        return (_FactChunk(text=text, start=0, end=len(text)),)
    return tuple(chunks)


def _best_chunk_boundary(text: str, *, start: int, hard_end: int) -> int:
    min_end = min(start + _MIN_NATURAL_CHUNK_CHARS, hard_end)
    best = hard_end
    for marker in _CHUNK_BOUNDARY_MARKERS:
        index = text.rfind(marker, min_end, hard_end)
        if index >= min_end:
            candidate = index + len(marker)
            if candidate > best or best == hard_end:
                best = candidate
    return best


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
        "source_item_index": fact_input.source_item_index,
        "chunk_index": fact_input.chunk_index,
        "chunk_count": fact_input.chunk_count,
        "source_char_start": fact_input.source_char_start,
        "source_char_end": fact_input.source_char_end,
        "source_excerpt_chars": fact_input.source_excerpt_chars,
    }
    if fact_input.citation_index is not None:
        metadata["citation_index"] = fact_input.citation_index
    if fact_input.chunking_strategy_ref is not None:
        metadata["chunking_strategy_ref"] = fact_input.chunking_strategy_ref
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
