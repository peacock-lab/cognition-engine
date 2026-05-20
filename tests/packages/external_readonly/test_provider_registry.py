from __future__ import annotations

from external_readonly import (
    EXTERNAL_READONLY_DEFAULT_ADAPTER_NAMES,
    ExternalReadonlyAdapterRegistryEntry,
    build_default_external_readonly_adapter_registry,
    build_external_readonly_adapter_registry,
    external_readonly_adapter_profile_from_registry_entry,
    external_readonly_adapter_registry_status_dict,
)


def test_default_adapter_registry_reserves_google_search_and_url_context() -> None:
    registry = build_default_external_readonly_adapter_registry()
    status = external_readonly_adapter_registry_status_dict(registry)

    assert registry.status == "reserved"
    assert registry.projection_adapter_names == EXTERNAL_READONLY_DEFAULT_ADAPTER_NAMES
    assert registry.blocked_adapter_names == ()
    assert registry.runtime_enabled_adapter_names == ()
    assert registry.third_party_runtime_enabled is False
    assert registry.network_provider_enabled is False
    assert registry.external_network_call_performed is False
    assert status["metadata"]["does_not_call_provider"] is True
    assert status["metadata"]["does_not_access_network"] is True
    assert "google_search_reference_lookup" in status["projection_adapter_names"]
    assert "url_context_reference_read" in status["projection_adapter_names"]
    credential_warnings = [
        warning
        for review in status["reviews"]
        for warning in review["warnings"]
    ]
    assert "provider_credentials_deferred" in credential_warnings


def test_registry_entry_projects_safe_adapter_profile() -> None:
    entry = next(
        entry
        for entry in build_default_external_readonly_adapter_registry().entries
        if entry.adapter_name == "google_search_reference_lookup"
    )

    profile = external_readonly_adapter_profile_from_registry_entry(entry)

    assert profile.adapter_name == "google_search_reference_lookup"
    assert profile.provider_name == "google_search"
    assert profile.provider_family == "search"
    assert profile.supported_operations == ("search",)
    assert profile.credential_ref is None
    assert profile.third_party_runtime_enabled is False
    assert profile.network_provider_enabled is False
    assert profile.raw_provider_payload_included is False
    assert profile.uploads_content is False
    assert profile.writes_files is False
    assert profile.calls_llm is False
    assert profile.metadata["provider_runtime_deferred"] is True


def test_adapter_registry_blocks_enabled_runtime_credentials_and_side_effects() -> None:
    registry = build_external_readonly_adapter_registry(
        (
            ExternalReadonlyAdapterRegistryEntry(
                adapter_name="unsafe_google_search",
                provider_name="google_search",
                provider_family="search",
                supported_operations=("search", "write"),
                adapter_ref="adapter://external-readonly/google-search/unsafe",
                status="enabled",
                requires_provider_credentials=True,
                credential_ref="credential://external-readonly/google-search",
                third_party_runtime_enabled=True,
                network_provider_enabled=True,
                raw_provider_payload_allowed=True,
                uploads_content=True,
                writes_files=True,
                mutates_external_system=True,
                executes_code=True,
                calls_llm=True,
                metadata={"api_key": "secret"},
            ),
        )
    )
    status = external_readonly_adapter_registry_status_dict(registry)
    blocking = status["reviews"][0]["blocking_reasons"]

    assert registry.status == "blocked"
    assert registry.projection_adapter_names == ()
    assert registry.blocked_adapter_names == ("unsafe_google_search",)
    assert "supported_operation_not_allowed" in blocking
    assert "provider_family_operation_mismatch" in blocking
    assert "adapter_status_not_reserved" in blocking
    assert "credential_ref_forbidden" in blocking
    assert "third_party_runtime_enabled_forbidden" in blocking
    assert "network_provider_enabled_forbidden" in blocking
    assert "raw_provider_payload_allowed_forbidden" in blocking
    assert "upload_forbidden" in blocking
    assert "writes_files_forbidden" in blocking
    assert "mutates_external_system_forbidden" in blocking
    assert "executes_code_forbidden" in blocking
    assert "calls_llm_forbidden" in blocking
    assert "raw_credential_material_forbidden" in blocking


def test_provider_registry_source_keeps_external_readonly_boundary() -> None:
    import pathlib

    repo_root = pathlib.Path(__file__).resolve().parents[3]
    source = (
        repo_root
        / "packages"
        / "external_readonly"
        / "src"
        / "external_readonly"
        / "provider_registry.py"
    ).read_text(encoding="utf-8")

    assert "runtime_container" not in source
    assert "product_gateway" not in source
    assert "cognition_cli" not in source
    assert "google.adk" not in source
    assert "litellm" not in source
