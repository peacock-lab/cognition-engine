"""Provider-neutral fake adapter for external read-only reference retrieval."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from cognition_operation_flows._external_readonly.evidence import (
    TwfExternalReadonlyEvidenceEnvelopeCandidate,
    TwfExternalReadonlyEvidenceItemCandidate,
    build_twf_external_readonly_evidence_envelope,
    twf_external_readonly_evidence_envelope_status_dict,
)
from cognition_operation_flows._external_readonly.network_gate import (
    TwfExternalReadonlyNetworkGateCandidate,
)


TWF_EXTERNAL_READONLY_PROVIDER_ADAPTER_STAGES = (
    "network_gate_binding",
    "provider_profile_review",
    "provider_request_review",
    "fake_provider_record_projection",
    "evidence_envelope_build",
    "sanitized_adapter_summary",
)
TWF_EXTERNAL_READONLY_FAKE_PROVIDER_KINDS = frozenset(
    {"fake_fetch", "fake_search", "fake_url_context"}
)
TWF_EXTERNAL_READONLY_PROVIDER_KIND_OPERATIONS = {
    "fake_fetch": frozenset({"fetch", "read"}),
    "fake_search": frozenset({"search"}),
    "fake_url_context": frozenset({"fetch", "read"}),
}
TWF_EXTERNAL_READONLY_PROVIDER_SECRET_KEY_MARKERS = (
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


@dataclass(frozen=True)
class TwfExternalReadonlyProviderProfileCandidate:
    """Provider profile facts for a future external-readonly adapter."""

    provider_name: str
    provider_kind: str
    supported_operations: tuple[str, ...]
    fake_provider: bool = True
    network_provider_enabled: bool = False
    raw_provider_payload_included: bool = False
    credential_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfExternalReadonlyProviderRequestCandidate:
    """Provider-neutral request facts passed after the network gate."""

    request_ref: str
    operation_family: str
    envelope_ref: str
    query_ref: str | None = None
    source_url: str | None = None
    raw_query_included: bool = False
    raw_url_context_included: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfExternalReadonlyFakeProviderRecordCandidate:
    """One fake provider record already sanitized before envelope projection."""

    source_url: str
    retrieved_at: str
    sanitized_excerpt: str
    citation_index: int
    source_title: str | None = None
    source_provider: str | None = None
    item_type: str | None = None
    evidence_ref: str | None = None
    content_hash: str | None = None
    language: str | None = None
    mime_type: str | None = None
    raw_provider_payload_included: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfExternalReadonlyProviderAdapterResultCandidate:
    """Sanitized result for a provider-neutral fake adapter run."""

    status: str
    provider_name: str
    provider_kind: str
    request_ref: str
    operation_family: str
    envelope: TwfExternalReadonlyEvidenceEnvelopeCandidate | None
    allowed_for_model_context: bool
    provider_network_call_performed: bool = False
    external_network_call_performed: bool = False
    tool_execution_performed: bool = False
    fake_provider_used: bool = True
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


def run_twf_external_readonly_fake_provider_adapter(
    *,
    gate: TwfExternalReadonlyNetworkGateCandidate,
    profile: TwfExternalReadonlyProviderProfileCandidate,
    request: TwfExternalReadonlyProviderRequestCandidate,
    records: Sequence[TwfExternalReadonlyFakeProviderRecordCandidate],
) -> TwfExternalReadonlyProviderAdapterResultCandidate:
    """Project fake provider records into an evidence envelope without I/O."""

    provider_kind = _normalize_token(profile.provider_kind)
    operation = _normalize_token(request.operation_family)
    blocking: list[str] = []
    warnings: list[str] = []

    if gate.status != "passed" or not gate.network_gate_open:
        blocking.append("network_gate_not_open")
    if gate.request_ref != request.request_ref:
        blocking.append("provider_request_ref_mismatch")
    if gate.operation_family != operation:
        blocking.append("provider_request_operation_mismatch")
    if not _present(profile.provider_name):
        blocking.append("provider_name_required")
    if provider_kind not in TWF_EXTERNAL_READONLY_FAKE_PROVIDER_KINDS:
        blocking.append("provider_kind_not_fake")
    if not profile.fake_provider:
        blocking.append("fake_provider_required_for_465")
    if profile.network_provider_enabled:
        blocking.append("network_provider_enabled_forbidden")
    if profile.raw_provider_payload_included:
        blocking.append("raw_provider_payload_forbidden")
    if _raw_secret_keys(profile.metadata) or profile.credential_ref:
        blocking.append("provider_credential_material_forbidden")

    supported = tuple(_normalize_token(item) for item in profile.supported_operations)
    if operation not in supported:
        blocking.append("provider_operation_not_supported")
    allowed_for_kind = TWF_EXTERNAL_READONLY_PROVIDER_KIND_OPERATIONS.get(
        provider_kind,
        frozenset(),
    )
    if operation not in allowed_for_kind:
        blocking.append("provider_kind_operation_mismatch")
    if operation == "search" and not _present(request.query_ref):
        blocking.append("provider_query_ref_required")
    if operation in {"fetch", "read"} and not _present(request.source_url):
        blocking.append("provider_source_url_required")
    if request.raw_query_included:
        blocking.append("raw_query_forbidden")
    if request.raw_url_context_included:
        blocking.append("raw_url_context_forbidden")
    if _raw_secret_keys(request.metadata):
        blocking.append("raw_credential_material_forbidden")
    if not records:
        blocking.append("fake_provider_records_required")
    for record in records:
        if record.raw_provider_payload_included:
            blocking.append("raw_provider_payload_forbidden")
        if _raw_secret_keys(record.metadata):
            blocking.append("raw_credential_material_forbidden")

    item_type = _item_type_for_operation(operation)
    items = tuple(
        _evidence_item_from_record(
            record,
            provider_name=profile.provider_name,
            item_type=item_type,
            index=index,
        )
        for index, record in enumerate(records, start=1)
    )
    envelope = build_twf_external_readonly_evidence_envelope(
        gate=gate,
        items=items,
        envelope_ref=request.envelope_ref,
    )
    if not envelope.allowed_for_model_context:
        blocking.extend(
            f"evidence_envelope:{reason}"
            for reason in envelope.blocking_reasons
        )

    allowed = not blocking
    return TwfExternalReadonlyProviderAdapterResultCandidate(
        status="completed" if allowed else "blocked",
        provider_name=profile.provider_name,
        provider_kind=provider_kind,
        request_ref=request.request_ref,
        operation_family=operation,
        envelope=envelope if allowed else None,
        allowed_for_model_context=allowed,
        provider_network_call_performed=False,
        external_network_call_performed=False,
        tool_execution_performed=False,
        fake_provider_used=True,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "candidate_only": True,
            "reference_only": True,
            "stages": list(TWF_EXTERNAL_READONLY_PROVIDER_ADAPTER_STAGES),
            "provider_supported_operations": list(supported),
            "network_gate_status": gate.status,
            "network_gate_open": gate.network_gate_open,
            "does_not_perform_external_network_calls": True,
            "does_not_execute_tool": True,
            "does_not_write_files": True,
            "raw_provider_payload_included": False,
            "fake_provider_used": True,
            "record_count": len(records),
        },
    )


def twf_external_readonly_provider_adapter_result_status_dict(
    result: TwfExternalReadonlyProviderAdapterResultCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready sanitized provider adapter summary."""

    return {
        "status": result.status,
        "provider_name": result.provider_name,
        "provider_kind": result.provider_kind,
        "request_ref": result.request_ref,
        "operation_family": result.operation_family,
        "allowed_for_model_context": result.allowed_for_model_context,
        "provider_network_call_performed": result.provider_network_call_performed,
        "external_network_call_performed": result.external_network_call_performed,
        "tool_execution_performed": result.tool_execution_performed,
        "fake_provider_used": result.fake_provider_used,
        "blocking_reasons": list(result.blocking_reasons),
        "warnings": list(result.warnings),
        "envelope": (
            twf_external_readonly_evidence_envelope_status_dict(result.envelope)
            if result.envelope is not None
            else None
        ),
        "metadata": dict(result.metadata),
    }


def _evidence_item_from_record(
    record: TwfExternalReadonlyFakeProviderRecordCandidate,
    *,
    provider_name: str,
    item_type: str,
    index: int,
) -> TwfExternalReadonlyEvidenceItemCandidate:
    return TwfExternalReadonlyEvidenceItemCandidate(
        evidence_ref=record.evidence_ref
        or f"evidence://external-readonly/{provider_name}/{index}",
        source_url=record.source_url,
        retrieved_at=record.retrieved_at,
        sanitized_excerpt=record.sanitized_excerpt,
        citation_index=record.citation_index,
        item_type=record.item_type or item_type,
        source_title=record.source_title,
        source_provider=record.source_provider or provider_name,
        content_hash=record.content_hash,
        language=record.language,
        mime_type=record.mime_type,
        raw_response_included=record.raw_provider_payload_included,
        metadata=record.metadata,
    )


def _item_type_for_operation(operation: str) -> str:
    if operation == "search":
        return "search_result"
    if operation == "fetch":
        return "fetched_excerpt"
    return "url_context_excerpt"


def _raw_secret_keys(raw_config: Mapping[str, Any]) -> tuple[str, ...]:
    keys: list[str] = []
    for key, value in raw_config.items():
        key_text = str(key).lower()
        if any(
            marker in key_text
            for marker in TWF_EXTERNAL_READONLY_PROVIDER_SECRET_KEY_MARKERS
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
