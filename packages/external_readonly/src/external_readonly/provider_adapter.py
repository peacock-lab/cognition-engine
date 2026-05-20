"""Provider-neutral adapter slot for external read-only reference records."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import ipaddress
from typing import Any
from urllib.parse import urlparse

from external_readonly.url_fetch import (
    EXTERNAL_READONLY_CONTROLLED_OUTPUT_ROOT,
    EXTERNAL_READONLY_EVIDENCE_REF_PREFIX,
    EXTERNAL_READONLY_SECRET_KEY_MARKERS,
    ExternalReadonlyEvidenceEnvelope,
    ExternalReadonlyNetworkGateView,
    coerce_external_readonly_network_gate_view,
    external_readonly_evidence_envelope_status_dict,
)


EXTERNAL_READONLY_ADAPTER_SLOT_STAGES = (
    "adapter_profile_review",
    "network_gate_binding",
    "provider_request_review",
    "sanitized_record_review",
    "evidence_envelope_projection",
    "runtime_disabled_summary",
)
EXTERNAL_READONLY_ADAPTER_ALLOWED_PROVIDER_FAMILIES = frozenset(
    {"fetch", "search", "url_context"}
)
EXTERNAL_READONLY_ADAPTER_ALLOWED_OPERATIONS = frozenset(
    {"fetch", "read", "search"}
)
EXTERNAL_READONLY_ADAPTER_FAMILY_OPERATIONS = {
    "fetch": frozenset({"fetch", "read"}),
    "search": frozenset({"search"}),
    "url_context": frozenset({"fetch", "read"}),
}
EXTERNAL_READONLY_ADAPTER_FORBIDDEN_OPERATION_TOKENS = frozenset(
    {
        "call",
        "create",
        "delete",
        "execute",
        "insert",
        "invoke",
        "login",
        "mutate",
        "patch",
        "post",
        "publish",
        "put",
        "remove",
        "run",
        "send",
        "submit",
        "update",
        "write",
    }
)


@dataclass(frozen=True)
class ExternalReadonlyAdapterProfile:
    """Sanitized provider profile for a future third-party adapter."""

    adapter_name: str
    provider_name: str
    provider_family: str
    supported_operations: tuple[str, ...]
    adapter_ref: str | None = None
    credential_ref: str | None = None
    third_party_runtime_enabled: bool = False
    network_provider_enabled: bool = False
    raw_provider_payload_included: bool = False
    uploads_content: bool = False
    writes_files: bool = False
    mutates_external_system: bool = False
    executes_code: bool = False
    calls_llm: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalReadonlyAdapterRequest:
    """Provider-neutral request facts bound to a governed network gate."""

    request_ref: str
    operation_family: str
    envelope_ref: str
    query_ref: str | None = None
    source_url: str | None = None
    controlled_output_ref: str | None = None
    raw_query_included: bool = False
    raw_url_context_included: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalReadonlyAdapterRecord:
    """One already-sanitized provider record for evidence projection."""

    source_url: str
    retrieved_at: str
    sanitized_excerpt: str
    citation_index: int
    evidence_ref: str
    source_title: str | None = None
    source_provider: str | None = None
    item_type: str | None = None
    content_hash: str | None = None
    language: str | None = None
    mime_type: str | None = None
    raw_provider_payload_included: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalReadonlyAdapterProjectionResult:
    """Sanitized projection result for the provider adapter slot."""

    status: str
    adapter_name: str
    provider_name: str
    provider_family: str
    request_ref: str
    operation_family: str
    allowed_for_model_context: bool
    envelope: ExternalReadonlyEvidenceEnvelope | None
    provider_network_call_performed: bool = False
    external_network_call_performed: bool = False
    tool_execution_performed: bool = False
    third_party_runtime_enabled: bool = False
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


def project_external_readonly_adapter_records(
    *,
    gate: ExternalReadonlyNetworkGateView | Mapping[str, Any] | object,
    profile: ExternalReadonlyAdapterProfile,
    request: ExternalReadonlyAdapterRequest,
    records: Sequence[ExternalReadonlyAdapterRecord],
) -> ExternalReadonlyAdapterProjectionResult:
    """Project sanitized provider records without calling a provider."""

    gate_view = coerce_external_readonly_network_gate_view(gate)
    provider_family = _normalize_token(profile.provider_family)
    operation = _normalize_token(request.operation_family)
    supported = tuple(
        _normalize_token(operation_item)
        for operation_item in profile.supported_operations
    )
    blocking: list[str] = []
    warnings: list[str] = []

    blocking.extend(_gate_blocking_reasons(gate_view, request=request))
    blocking.extend(
        _profile_blocking_reasons(
            profile,
            provider_family=provider_family,
            operation=operation,
            supported=supported,
        )
    )
    blocking.extend(
        _request_blocking_reasons(
            request,
            operation=operation,
        )
    )
    if not records:
        blocking.append("sanitized_records_required")
    for index, record in enumerate(records, start=1):
        blocking.extend(_record_blocking_reasons(record, index=index))

    envelope = None
    if not blocking:
        envelope = _build_adapter_envelope(
            gate=gate_view,
            profile=profile,
            provider_family=provider_family,
            request=request,
            operation=operation,
            records=records,
        )

    allowed = envelope is not None and not blocking
    return ExternalReadonlyAdapterProjectionResult(
        status="completed" if allowed else "blocked",
        adapter_name=profile.adapter_name,
        provider_name=profile.provider_name,
        provider_family=provider_family,
        request_ref=request.request_ref,
        operation_family=operation,
        allowed_for_model_context=allowed,
        envelope=envelope,
        provider_network_call_performed=False,
        external_network_call_performed=False,
        tool_execution_performed=False,
        third_party_runtime_enabled=False,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "external_readonly_core": True,
            "provider_adapter_slot": True,
            "candidate_only": True,
            "reference_only": True,
            "stages": list(EXTERNAL_READONLY_ADAPTER_SLOT_STAGES),
            "adapter_ref": profile.adapter_ref,
            "provider_supported_operations": list(supported),
            "network_gate_status": gate_view.status,
            "network_gate_open": gate_view.network_gate_open,
            "provider_network_call_performed": False,
            "external_network_call_performed": False,
            "tool_execution_performed": False,
            "third_party_runtime_enabled": False,
            "network_provider_enabled": False,
            "raw_provider_payload_included": False,
            "writes_files": False,
            "uploads_content": False,
            "record_count": len(records),
        },
    )


def external_readonly_adapter_projection_status_dict(
    result: ExternalReadonlyAdapterProjectionResult,
) -> dict[str, Any]:
    """Return a JSON-ready sanitized adapter projection result."""

    return {
        "status": result.status,
        "adapter_name": result.adapter_name,
        "provider_name": result.provider_name,
        "provider_family": result.provider_family,
        "request_ref": result.request_ref,
        "operation_family": result.operation_family,
        "allowed_for_model_context": result.allowed_for_model_context,
        "provider_network_call_performed": result.provider_network_call_performed,
        "external_network_call_performed": result.external_network_call_performed,
        "tool_execution_performed": result.tool_execution_performed,
        "third_party_runtime_enabled": result.third_party_runtime_enabled,
        "blocking_reasons": list(result.blocking_reasons),
        "warnings": list(result.warnings),
        "envelope": (
            external_readonly_evidence_envelope_status_dict(result.envelope)
            if result.envelope is not None
            else None
        ),
        "metadata": dict(result.metadata),
    }


def _gate_blocking_reasons(
    gate: ExternalReadonlyNetworkGateView,
    *,
    request: ExternalReadonlyAdapterRequest,
) -> list[str]:
    blocking: list[str] = []
    if gate.status != "passed":
        blocking.append("network_gate_not_passed")
    if not gate.network_gate_open or not gate.allowed_for_network_request:
        blocking.append("network_gate_not_open")
    if not gate.operator_approval_satisfied:
        blocking.append("operator_approval_not_satisfied")
    if not gate.controlled_output_satisfied:
        blocking.append("controlled_output_not_satisfied")
    if gate.request_ref != request.request_ref:
        blocking.append("adapter_request_ref_mismatch")
    if _normalize_token(gate.operation_family) != _normalize_token(
        request.operation_family
    ):
        blocking.append("adapter_operation_mismatch")
    if gate.external_network_call_performed:
        blocking.append("network_gate_has_execution_fact")
    if gate.tool_execution_performed:
        blocking.append("network_gate_has_tool_execution_fact")
    if _raw_secret_keys(gate.metadata):
        blocking.append("raw_credential_material_forbidden")
    return blocking


def _profile_blocking_reasons(
    profile: ExternalReadonlyAdapterProfile,
    *,
    provider_family: str,
    operation: str,
    supported: tuple[str, ...],
) -> list[str]:
    blocking: list[str] = []
    if not _present(profile.adapter_name):
        blocking.append("adapter_name_required")
    if not _present(profile.provider_name):
        blocking.append("provider_name_required")
    if provider_family not in EXTERNAL_READONLY_ADAPTER_ALLOWED_PROVIDER_FAMILIES:
        blocking.append("provider_family_not_allowed")
    if operation not in supported:
        blocking.append("provider_operation_not_supported")
    allowed_for_family = EXTERNAL_READONLY_ADAPTER_FAMILY_OPERATIONS.get(
        provider_family,
        frozenset(),
    )
    if operation not in allowed_for_family:
        blocking.append("provider_family_operation_mismatch")
    if profile.third_party_runtime_enabled:
        blocking.append("third_party_runtime_enabled_forbidden")
    if profile.network_provider_enabled:
        blocking.append("network_provider_enabled_forbidden")
    if profile.raw_provider_payload_included:
        blocking.append("raw_provider_payload_forbidden")
    if profile.credential_ref:
        blocking.append("provider_credential_ref_forbidden")
    if profile.uploads_content:
        blocking.append("upload_forbidden")
    if profile.writes_files:
        blocking.append("writes_files_forbidden")
    if profile.mutates_external_system:
        blocking.append("mutates_external_system_forbidden")
    if profile.executes_code:
        blocking.append("executes_code_forbidden")
    if profile.calls_llm:
        blocking.append("calls_llm_forbidden")
    if _raw_secret_keys(profile.metadata):
        blocking.append("raw_credential_material_forbidden")
    return blocking


def _request_blocking_reasons(
    request: ExternalReadonlyAdapterRequest,
    *,
    operation: str,
) -> list[str]:
    blocking: list[str] = []
    if not _present(request.request_ref):
        blocking.append("request_ref_required")
    if operation not in EXTERNAL_READONLY_ADAPTER_ALLOWED_OPERATIONS:
        blocking.append("operation_family_not_allowed")
    if _operation_contains_forbidden_token(request.operation_family):
        blocking.append("operation_family_contains_side_effect_token")
    if not _evidence_ref_allowed(request.envelope_ref):
        blocking.append("envelope_ref_not_external_readonly")
    if operation == "search" and not _present(request.query_ref):
        blocking.append("query_ref_required")
    if operation in {"fetch", "read"} and not _present(request.source_url):
        blocking.append("source_url_required")
    if request.source_url and not _external_https_url_allowed(request.source_url):
        blocking.append("source_url_not_external_https")
    if request.controlled_output_ref and not _controlled_output_ref_allowed(
        request.controlled_output_ref
    ):
        blocking.append("controlled_output_ref_not_allowed")
    if request.raw_query_included:
        blocking.append("raw_query_forbidden")
    if request.raw_url_context_included:
        blocking.append("raw_url_context_forbidden")
    if _raw_secret_keys(request.metadata):
        blocking.append("raw_credential_material_forbidden")
    return blocking


def _record_blocking_reasons(
    record: ExternalReadonlyAdapterRecord,
    *,
    index: int,
) -> list[str]:
    blocking: list[str] = []
    prefix = f"record_{index}"
    if not _evidence_ref_allowed(record.evidence_ref):
        blocking.append(f"{prefix}:evidence_ref_not_external_readonly")
    if not _external_https_url_allowed(record.source_url):
        blocking.append(f"{prefix}:source_url_not_external_https")
    if not _valid_retrieved_at(record.retrieved_at):
        blocking.append(f"{prefix}:retrieved_at_invalid")
    if not record.sanitized_excerpt.strip():
        blocking.append(f"{prefix}:sanitized_excerpt_required")
    if not isinstance(record.citation_index, int) or record.citation_index <= 0:
        blocking.append(f"{prefix}:citation_index_invalid")
    if record.content_hash and record.content_hash != _sha256_text(
        record.sanitized_excerpt
    ):
        blocking.append(f"{prefix}:content_hash_mismatch")
    if record.raw_provider_payload_included:
        blocking.append(f"{prefix}:raw_provider_payload_forbidden")
    if _raw_secret_keys(record.metadata):
        blocking.append(f"{prefix}:raw_credential_material_forbidden")
    return blocking


def _build_adapter_envelope(
    *,
    gate: ExternalReadonlyNetworkGateView,
    profile: ExternalReadonlyAdapterProfile,
    provider_family: str,
    request: ExternalReadonlyAdapterRequest,
    operation: str,
    records: Sequence[ExternalReadonlyAdapterRecord],
) -> ExternalReadonlyEvidenceEnvelope:
    items = tuple(
        _model_context_item(
            record,
            operation=operation,
            provider_name=profile.provider_name,
        )
        for record in records
    )
    return ExternalReadonlyEvidenceEnvelope(
        envelope_ref=request.envelope_ref,
        request_ref=request.request_ref,
        status="valid",
        allowed_for_model_context=True,
        model_context_items=items,
        evidence_refs=tuple(_ordered_unique([item["evidence_ref"] for item in items])),
        source_urls=tuple(_ordered_unique([item["source_url"] for item in items])),
        total_excerpt_chars=sum(len(item["sanitized_excerpt"]) for item in items),
        metadata={
            "external_readonly_core": True,
            "provider_adapter_slot": True,
            "adapter_name": profile.adapter_name,
            "provider_name": profile.provider_name,
            "provider_family": provider_family,
            "operation_family": operation,
            "network_gate_status": gate.status,
            "network_gate_open": gate.network_gate_open,
            "provider_network_call_performed": False,
            "external_network_call_performed": False,
            "tool_execution_performed": False,
            "third_party_runtime_enabled": False,
            "raw_provider_payload_included": False,
            "writes_files": False,
            "uploads_content": False,
        },
    )


def _model_context_item(
    record: ExternalReadonlyAdapterRecord,
    *,
    operation: str,
    provider_name: str,
) -> dict[str, Any]:
    sanitized_excerpt = record.sanitized_excerpt.strip()
    return {
        "citation_index": record.citation_index,
        "evidence_ref": record.evidence_ref,
        "source_url": record.source_url,
        "source_title": record.source_title,
        "source_provider": record.source_provider or provider_name,
        "retrieved_at": record.retrieved_at,
        "item_type": record.item_type or _item_type_for_operation(operation),
        "sanitized_excerpt": sanitized_excerpt,
        "content_hash": record.content_hash or _sha256_text(sanitized_excerpt),
        "language": record.language,
        "mime_type": record.mime_type,
    }


def _item_type_for_operation(operation: str) -> str:
    if operation == "search":
        return "search_result"
    if operation == "read":
        return "url_context_excerpt"
    return "fetched_excerpt"


def _external_https_url_allowed(value: str) -> bool:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False
    host = parsed.hostname.lower()
    if (
        host in {"localhost"}
        or host.endswith(".localhost")
        or host.endswith(".local")
        or host.endswith(".internal")
    ):
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


def _controlled_output_ref_allowed(value: str | None) -> bool:
    if not _present(value):
        return False
    ref = str(value).strip()
    if ref.startswith(EXTERNAL_READONLY_EVIDENCE_REF_PREFIX):
        return len(ref) > len(EXTERNAL_READONLY_EVIDENCE_REF_PREFIX)
    if not ref.startswith(f"{EXTERNAL_READONLY_CONTROLLED_OUTPUT_ROOT}/"):
        return False
    if not ref.endswith(".json"):
        return False
    return not any(part in {"", ".", ".."} for part in ref.split("/"))


def _evidence_ref_allowed(value: str | None) -> bool:
    return _present(value) and str(value).strip().startswith(
        EXTERNAL_READONLY_EVIDENCE_REF_PREFIX
    ) and len(str(value).strip()) > len(EXTERNAL_READONLY_EVIDENCE_REF_PREFIX)


def _valid_retrieved_at(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _operation_contains_forbidden_token(value: str) -> bool:
    normalized = _normalize_token(value)
    split = set(filter(None, normalized.split("_")))
    return any(
        token in normalized or token in split
        for token in EXTERNAL_READONLY_ADAPTER_FORBIDDEN_OPERATION_TOKENS
    )


def _raw_secret_keys(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            key_text = str(key).lower()
            if any(marker in key_text for marker in EXTERNAL_READONLY_SECRET_KEY_MARKERS):
                return True
            if _raw_secret_keys(nested_value):
                return True
    elif isinstance(value, (list, tuple, set)):
        return any(_raw_secret_keys(item) for item in value)
    return False


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _present(value: str | None) -> bool:
    return bool(value and value.strip())


def _normalize_token(value: str) -> str:
    return "_".join(str(value).strip().lower().replace("-", "_").split())


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
