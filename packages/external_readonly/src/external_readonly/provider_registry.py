"""Registry for reserved external-readonly third-party adapter profiles."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from external_readonly.provider_adapter import (
    EXTERNAL_READONLY_ADAPTER_ALLOWED_OPERATIONS,
    EXTERNAL_READONLY_ADAPTER_ALLOWED_PROVIDER_FAMILIES,
    EXTERNAL_READONLY_ADAPTER_FAMILY_OPERATIONS,
    ExternalReadonlyAdapterProfile,
)
from external_readonly.url_fetch import EXTERNAL_READONLY_SECRET_KEY_MARKERS


EXTERNAL_READONLY_ADAPTER_REGISTRY_VERSION = "v0.7.0-candidate"
EXTERNAL_READONLY_ADAPTER_ENTRY_STATUSES = frozenset(
    {"candidate_reserved", "disabled", "experimental_reserved"}
)
EXTERNAL_READONLY_DEFAULT_ADAPTER_NAMES = (
    "provider_neutral_url_fetch",
    "google_search_reference_lookup",
    "url_context_reference_read",
)


@dataclass(frozen=True)
class ExternalReadonlyAdapterRegistryEntry:
    """Candidate registry entry for one external-readonly adapter slot."""

    adapter_name: str
    provider_name: str
    provider_family: str
    supported_operations: tuple[str, ...]
    adapter_ref: str
    status: str = "candidate_reserved"
    requires_provider_credentials: bool = False
    credential_ref: str | None = None
    third_party_runtime_enabled: bool = False
    network_provider_enabled: bool = False
    raw_provider_payload_allowed: bool = False
    uploads_content: bool = False
    writes_files: bool = False
    mutates_external_system: bool = False
    executes_code: bool = False
    calls_llm: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalReadonlyAdapterRegistryReview:
    """Sanitized review result for one registry entry."""

    adapter_name: str
    provider_name: str
    provider_family: str
    status: str
    allowed_for_projection: bool
    enabled_for_runtime: bool
    requires_provider_credentials: bool
    supported_operations: tuple[str, ...]
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalReadonlyAdapterRegistry:
    """Sanitized registry summary for external-readonly adapter slots."""

    status: str
    registry_version: str
    entries: tuple[ExternalReadonlyAdapterRegistryEntry, ...]
    reviews: tuple[ExternalReadonlyAdapterRegistryReview, ...]
    projection_adapter_names: tuple[str, ...]
    blocked_adapter_names: tuple[str, ...]
    runtime_enabled_adapter_names: tuple[str, ...] = ()
    third_party_runtime_enabled: bool = False
    network_provider_enabled: bool = False
    external_network_call_performed: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


def build_default_external_readonly_adapter_registry() -> ExternalReadonlyAdapterRegistry:
    """Build the default reserved adapter registry without enabling providers."""

    return build_external_readonly_adapter_registry(
        (
            ExternalReadonlyAdapterRegistryEntry(
                adapter_name="provider_neutral_url_fetch",
                provider_name="provider_neutral_fetch",
                provider_family="fetch",
                supported_operations=("fetch", "read"),
                adapter_ref="adapter://external-readonly/provider-neutral/url-fetch",
                metadata={
                    "serves_local_models": True,
                    "current_core": "external_readonly.url_fetch",
                },
            ),
            ExternalReadonlyAdapterRegistryEntry(
                adapter_name="google_search_reference_lookup",
                provider_name="google_search",
                provider_family="search",
                supported_operations=("search",),
                adapter_ref="adapter://external-readonly/google-search/reference-lookup",
                requires_provider_credentials=True,
                metadata={
                    "candidate_source": "462_google_search_url_context_design",
                    "provider_runtime_deferred": True,
                },
            ),
            ExternalReadonlyAdapterRegistryEntry(
                adapter_name="url_context_reference_read",
                provider_name="url_context",
                provider_family="url_context",
                supported_operations=("fetch", "read"),
                adapter_ref="adapter://external-readonly/url-context/reference-read",
                requires_provider_credentials=True,
                metadata={
                    "candidate_source": "462_google_search_url_context_design",
                    "provider_runtime_deferred": True,
                },
            ),
        )
    )


def build_external_readonly_adapter_registry(
    entries: Sequence[ExternalReadonlyAdapterRegistryEntry],
) -> ExternalReadonlyAdapterRegistry:
    """Review and summarize adapter registry entries without provider calls."""

    reviews = tuple(review_external_readonly_adapter_registry_entry(entry) for entry in entries)
    projection_adapter_names = tuple(
        review.adapter_name for review in reviews if review.allowed_for_projection
    )
    blocked_adapter_names = tuple(
        review.adapter_name for review in reviews if not review.allowed_for_projection
    )
    runtime_enabled_adapter_names = tuple(
        review.adapter_name for review in reviews if review.enabled_for_runtime
    )
    return ExternalReadonlyAdapterRegistry(
        status="blocked" if blocked_adapter_names else "reserved",
        registry_version=EXTERNAL_READONLY_ADAPTER_REGISTRY_VERSION,
        entries=tuple(entries),
        reviews=reviews,
        projection_adapter_names=projection_adapter_names,
        blocked_adapter_names=blocked_adapter_names,
        runtime_enabled_adapter_names=runtime_enabled_adapter_names,
        third_party_runtime_enabled=False,
        network_provider_enabled=False,
        external_network_call_performed=False,
        metadata={
            "external_readonly_core": True,
            "provider_adapter_registry": True,
            "candidate_only": True,
            "projection_only": True,
            "default_adapter_names": list(EXTERNAL_READONLY_DEFAULT_ADAPTER_NAMES),
            "does_not_call_provider": True,
            "does_not_access_network": True,
            "does_not_upload": True,
            "does_not_write_files": True,
        },
    )


def review_external_readonly_adapter_registry_entry(
    entry: ExternalReadonlyAdapterRegistryEntry,
) -> ExternalReadonlyAdapterRegistryReview:
    """Review one adapter registry entry for projection-only admission."""

    provider_family = _normalize_token(entry.provider_family)
    supported = tuple(_normalize_token(item) for item in entry.supported_operations)
    blocking: list[str] = []
    warnings: list[str] = []

    if not _present(entry.adapter_name):
        blocking.append("adapter_name_required")
    if not _present(entry.provider_name):
        blocking.append("provider_name_required")
    if provider_family not in EXTERNAL_READONLY_ADAPTER_ALLOWED_PROVIDER_FAMILIES:
        blocking.append("provider_family_not_allowed")
    if not supported:
        blocking.append("supported_operations_required")
    for operation in supported:
        if operation not in EXTERNAL_READONLY_ADAPTER_ALLOWED_OPERATIONS:
            blocking.append("supported_operation_not_allowed")
        allowed_for_family = EXTERNAL_READONLY_ADAPTER_FAMILY_OPERATIONS.get(
            provider_family,
            frozenset(),
        )
        if operation not in allowed_for_family:
            blocking.append("provider_family_operation_mismatch")
    if not _present(entry.adapter_ref):
        blocking.append("adapter_ref_required")
    elif not str(entry.adapter_ref).startswith("adapter://external-readonly/"):
        blocking.append("adapter_ref_not_external_readonly")
    if entry.status not in EXTERNAL_READONLY_ADAPTER_ENTRY_STATUSES:
        blocking.append("adapter_status_not_reserved")
    if entry.credential_ref:
        blocking.append("credential_ref_forbidden")
    if entry.third_party_runtime_enabled:
        blocking.append("third_party_runtime_enabled_forbidden")
    if entry.network_provider_enabled:
        blocking.append("network_provider_enabled_forbidden")
    if entry.raw_provider_payload_allowed:
        blocking.append("raw_provider_payload_allowed_forbidden")
    if entry.uploads_content:
        blocking.append("upload_forbidden")
    if entry.writes_files:
        blocking.append("writes_files_forbidden")
    if entry.mutates_external_system:
        blocking.append("mutates_external_system_forbidden")
    if entry.executes_code:
        blocking.append("executes_code_forbidden")
    if entry.calls_llm:
        blocking.append("calls_llm_forbidden")
    if _raw_secret_keys(entry.metadata):
        blocking.append("raw_credential_material_forbidden")
    if entry.requires_provider_credentials:
        warnings.append("provider_credentials_deferred")

    allowed = not blocking
    return ExternalReadonlyAdapterRegistryReview(
        adapter_name=entry.adapter_name,
        provider_name=entry.provider_name,
        provider_family=provider_family,
        status="reserved" if allowed else "blocked",
        allowed_for_projection=allowed,
        enabled_for_runtime=False,
        requires_provider_credentials=entry.requires_provider_credentials,
        supported_operations=supported,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "external_readonly_core": True,
            "provider_adapter_registry_entry": True,
            "adapter_ref": entry.adapter_ref,
            "entry_status": entry.status,
            "third_party_runtime_enabled": False,
            "network_provider_enabled": False,
            "credential_ref_present": False,
            "raw_provider_payload_allowed": False,
            "projection_only": True,
            "does_not_call_provider": True,
        },
    )


def external_readonly_adapter_profile_from_registry_entry(
    entry: ExternalReadonlyAdapterRegistryEntry,
) -> ExternalReadonlyAdapterProfile:
    """Project a safe provider-adapter profile from a reviewed registry entry."""

    return ExternalReadonlyAdapterProfile(
        adapter_name=entry.adapter_name,
        provider_name=entry.provider_name,
        provider_family=_normalize_token(entry.provider_family),
        supported_operations=tuple(
            _normalize_token(item) for item in entry.supported_operations
        ),
        adapter_ref=entry.adapter_ref,
        credential_ref=None,
        third_party_runtime_enabled=False,
        network_provider_enabled=False,
        raw_provider_payload_included=False,
        uploads_content=False,
        writes_files=False,
        mutates_external_system=False,
        executes_code=False,
        calls_llm=False,
        metadata={
            "source": "external_readonly.provider_registry",
            "registry_version": EXTERNAL_READONLY_ADAPTER_REGISTRY_VERSION,
            "requires_provider_credentials": entry.requires_provider_credentials,
            "provider_runtime_deferred": True,
        },
    )


def external_readonly_adapter_registry_status_dict(
    registry: ExternalReadonlyAdapterRegistry,
) -> dict[str, Any]:
    """Return a JSON-ready sanitized adapter registry summary."""

    return {
        "status": registry.status,
        "registry_version": registry.registry_version,
        "entry_count": len(registry.entries),
        "projection_adapter_names": list(registry.projection_adapter_names),
        "blocked_adapter_names": list(registry.blocked_adapter_names),
        "runtime_enabled_adapter_names": list(registry.runtime_enabled_adapter_names),
        "third_party_runtime_enabled": registry.third_party_runtime_enabled,
        "network_provider_enabled": registry.network_provider_enabled,
        "external_network_call_performed": registry.external_network_call_performed,
        "reviews": [
            external_readonly_adapter_registry_review_status_dict(review)
            for review in registry.reviews
        ],
        "metadata": dict(registry.metadata),
    }


def external_readonly_adapter_registry_review_status_dict(
    review: ExternalReadonlyAdapterRegistryReview,
) -> dict[str, Any]:
    """Return a JSON-ready sanitized adapter registry review."""

    return {
        "adapter_name": review.adapter_name,
        "provider_name": review.provider_name,
        "provider_family": review.provider_family,
        "status": review.status,
        "allowed_for_projection": review.allowed_for_projection,
        "enabled_for_runtime": review.enabled_for_runtime,
        "requires_provider_credentials": review.requires_provider_credentials,
        "supported_operations": list(review.supported_operations),
        "blocking_reasons": list(review.blocking_reasons),
        "warnings": list(review.warnings),
        "metadata": dict(review.metadata),
    }


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
