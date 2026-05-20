from __future__ import annotations

from external_readonly import (
    ExternalReadonlyAdapterProfile,
    ExternalReadonlyAdapterRecord,
    ExternalReadonlyAdapterRequest,
    ExternalReadonlyNetworkGateView,
    external_readonly_adapter_projection_status_dict,
    project_external_readonly_adapter_records,
)


def test_provider_adapter_slot_projects_sanitized_search_records() -> None:
    result = project_external_readonly_adapter_records(
        gate=_gate(),
        profile=_profile(),
        request=_request(),
        records=(_record(),),
    )
    status = external_readonly_adapter_projection_status_dict(result)

    assert result.status == "completed"
    assert result.allowed_for_model_context is True
    assert result.provider_network_call_performed is False
    assert result.external_network_call_performed is False
    assert result.tool_execution_performed is False
    assert result.third_party_runtime_enabled is False
    assert result.envelope is not None
    item = result.envelope.model_context_items[0]
    assert item["item_type"] == "search_result"
    assert item["source_provider"] == "generic_search_provider"
    assert item["sanitized_excerpt"] == "Sanitized search result excerpt."
    assert status["metadata"]["provider_adapter_slot"] is True
    assert status["metadata"]["third_party_runtime_enabled"] is False
    assert status["metadata"]["raw_provider_payload_included"] is False
    assert "api_key" not in str(status).lower()


def test_provider_adapter_slot_blocks_runtime_credentials_and_raw_payloads() -> None:
    result = project_external_readonly_adapter_records(
        gate=_gate(metadata={"token": "secret"}),
        profile=ExternalReadonlyAdapterProfile(
            adapter_name="google_search_adapter",
            provider_name="google_search",
            provider_family="search",
            supported_operations=("search",),
            credential_ref="credential://external-readonly/google-search",
            third_party_runtime_enabled=True,
            network_provider_enabled=True,
            raw_provider_payload_included=True,
            uploads_content=True,
            writes_files=True,
            mutates_external_system=True,
            calls_llm=True,
            metadata={"api_key": "secret"},
        ),
        request=_request(raw_query_included=True, metadata={"cookie": "secret"}),
        records=(
            _record(
                raw_provider_payload_included=True,
                metadata={"authorization": "secret"},
            ),
        ),
    )

    assert result.status == "blocked"
    assert result.envelope is None
    assert "raw_credential_material_forbidden" in result.blocking_reasons
    assert "provider_credential_ref_forbidden" in result.blocking_reasons
    assert "third_party_runtime_enabled_forbidden" in result.blocking_reasons
    assert "network_provider_enabled_forbidden" in result.blocking_reasons
    assert "raw_provider_payload_forbidden" in result.blocking_reasons
    assert "upload_forbidden" in result.blocking_reasons
    assert "writes_files_forbidden" in result.blocking_reasons
    assert "mutates_external_system_forbidden" in result.blocking_reasons
    assert "calls_llm_forbidden" in result.blocking_reasons
    assert "raw_query_forbidden" in result.blocking_reasons
    assert any(
        reason.endswith("raw_provider_payload_forbidden")
        for reason in result.blocking_reasons
    )


def test_provider_adapter_slot_blocks_operation_and_record_mismatches() -> None:
    result = project_external_readonly_adapter_records(
        gate=_gate(operation_family="search"),
        profile=ExternalReadonlyAdapterProfile(
            adapter_name="url_context_adapter",
            provider_name="url_context_provider",
            provider_family="url_context",
            supported_operations=("read",),
        ),
        request=_request(
            operation_family="read",
            query_ref=None,
            source_url="https://example.com/reference",
        ),
        records=(
            _record(
                evidence_ref="evidence://bad/ref",
                source_url="https://127.0.0.1/internal",
                retrieved_at="not-a-date",
                sanitized_excerpt="",
                content_hash="mismatch",
            ),
        ),
    )

    assert result.status == "blocked"
    assert "adapter_operation_mismatch" in result.blocking_reasons
    assert "record_1:evidence_ref_not_external_readonly" in result.blocking_reasons
    assert "record_1:source_url_not_external_https" in result.blocking_reasons
    assert "record_1:retrieved_at_invalid" in result.blocking_reasons
    assert "record_1:sanitized_excerpt_required" in result.blocking_reasons
    assert "record_1:content_hash_mismatch" in result.blocking_reasons


def _profile(**overrides: object) -> ExternalReadonlyAdapterProfile:
    kwargs = {
        "adapter_name": "generic_search_adapter",
        "provider_name": "generic_search_provider",
        "provider_family": "search",
        "supported_operations": ("search",),
        "adapter_ref": "adapter://external-readonly/generic-search",
    }
    kwargs.update(overrides)
    return ExternalReadonlyAdapterProfile(**kwargs)


def _request(**overrides: object) -> ExternalReadonlyAdapterRequest:
    kwargs = {
        "request_ref": "external-readonly-request://adapter/477",
        "operation_family": "search",
        "query_ref": "query://external-readonly/sanitized-topic",
        "envelope_ref": "evidence://external-readonly/envelope/adapter-477",
        "controlled_output_ref": "outputs/external-readonly/adapter/477.json",
    }
    kwargs.update(overrides)
    return ExternalReadonlyAdapterRequest(**kwargs)


def _record(**overrides: object) -> ExternalReadonlyAdapterRecord:
    kwargs = {
        "source_url": "https://example.com/reference",
        "retrieved_at": "2026-05-16T10:00:00+00:00",
        "sanitized_excerpt": "Sanitized search result excerpt.",
        "citation_index": 1,
        "evidence_ref": "evidence://external-readonly/provider-adapter/477/1",
        "source_title": "Example Reference",
    }
    kwargs.update(overrides)
    return ExternalReadonlyAdapterRecord(**kwargs)


def _gate(**overrides: object) -> ExternalReadonlyNetworkGateView:
    kwargs = {
        "request_ref": "external-readonly-request://adapter/477",
        "status": "passed",
        "network_gate_open": True,
        "allowed_for_network_request": True,
        "operator_approval_satisfied": True,
        "controlled_output_satisfied": True,
        "tool_origin": "google_search",
        "operation_family": "search",
        "metadata": {
            "approval_ref_present": True,
            "network_gate_ref_present": True,
        },
    }
    kwargs.update(overrides)
    return ExternalReadonlyNetworkGateView(**kwargs)
