from __future__ import annotations

from cognition_operation_flows._external_readonly.network_gate import (
    TwfExternalReadonlyNetworkApprovalCandidate,
    TwfExternalReadonlyNetworkRequestCandidate,
    evaluate_twf_external_readonly_network_gate,
)
from cognition_operation_flows._external_readonly.provider_adapter import (
    TwfExternalReadonlyFakeProviderRecordCandidate,
    TwfExternalReadonlyProviderProfileCandidate,
    TwfExternalReadonlyProviderRequestCandidate,
    run_twf_external_readonly_fake_provider_adapter,
    twf_external_readonly_provider_adapter_result_status_dict,
)
from cognition_operation_flows._external_readonly.tool_design import (
    TwfExternalReadonlyToolDesignCandidate,
)


def test_fake_search_provider_projects_records_into_evidence_envelope() -> None:
    result = run_twf_external_readonly_fake_provider_adapter(
        gate=_passed_gate(),
        profile=_search_profile(),
        request=_provider_request(),
        records=(
            _record(
                evidence_ref="evidence://external-readonly/fake-search/1",
                citation_index=1,
            ),
        ),
    )
    status = twf_external_readonly_provider_adapter_result_status_dict(result)

    assert result.status == "completed"
    assert result.allowed_for_model_context is True
    assert result.provider_network_call_performed is False
    assert result.external_network_call_performed is False
    assert result.tool_execution_performed is False
    assert result.envelope is not None
    assert result.envelope.allowed_for_model_context is True
    assert status["metadata"]["fake_provider_used"] is True
    assert status["metadata"]["does_not_perform_external_network_calls"] is True
    assert status["envelope"]["model_context_items"][0]["item_type"] == (
        "search_result"
    )
    assert "approval://external-readonly/001" not in str(status)


def test_fake_fetch_provider_uses_source_url_request_and_fetched_excerpt() -> None:
    result = run_twf_external_readonly_fake_provider_adapter(
        gate=_passed_gate(
            tool_name="url_context_reference_fetch",
            tool_origin="url_context",
            operation_family="fetch",
            query_ref=None,
            source_url="https://example.com/reference",
        ),
        profile=TwfExternalReadonlyProviderProfileCandidate(
            provider_name="fake_fetch_provider",
            provider_kind="fake_fetch",
            supported_operations=("fetch",),
        ),
        request=TwfExternalReadonlyProviderRequestCandidate(
            request_ref="external-readonly-request://url-context/001",
            operation_family="fetch",
            source_url="https://example.com/reference",
            envelope_ref="evidence://external-readonly/envelope/fetch-001",
        ),
        records=(
            _record(
                evidence_ref="evidence://external-readonly/fake-fetch/1",
                citation_index=1,
                source_url="https://example.com/reference",
            ),
        ),
    )

    assert result.status == "completed"
    assert result.envelope is not None
    assert result.envelope.model_context_items[0]["item_type"] == "fetched_excerpt"


def test_fake_provider_blocks_closed_gate_and_request_mismatch() -> None:
    result = run_twf_external_readonly_fake_provider_adapter(
        gate=_blocked_gate(),
        profile=_search_profile(),
        request=_provider_request(request_ref="external-readonly-request://other/001"),
        records=(_record(),),
    )

    assert result.status == "blocked"
    assert result.envelope is None
    assert "network_gate_not_open" in result.blocking_reasons
    assert "provider_request_ref_mismatch" in result.blocking_reasons
    assert any(
        reason.startswith("evidence_envelope:network_gate_not_open")
        for reason in result.blocking_reasons
    )


def test_fake_provider_blocks_real_provider_credentials_and_raw_payload() -> None:
    result = run_twf_external_readonly_fake_provider_adapter(
        gate=_passed_gate(),
        profile=TwfExternalReadonlyProviderProfileCandidate(
            provider_name="real_search",
            provider_kind="real_search",
            supported_operations=("search",),
            fake_provider=False,
            network_provider_enabled=True,
            raw_provider_payload_included=True,
            credential_ref="credential://search",
            metadata={"api_key": "secret"},
        ),
        request=_provider_request(metadata={"token": "secret"}),
        records=(
            _record(
                raw_provider_payload_included=True,
                metadata={"cookie": "secret"},
            ),
        ),
    )

    assert result.status == "blocked"
    assert "provider_kind_not_fake" in result.blocking_reasons
    assert "fake_provider_required_for_465" in result.blocking_reasons
    assert "network_provider_enabled_forbidden" in result.blocking_reasons
    assert "raw_provider_payload_forbidden" in result.blocking_reasons
    assert "provider_credential_material_forbidden" in result.blocking_reasons
    assert "raw_credential_material_forbidden" in result.blocking_reasons


def test_fake_provider_blocks_operation_mismatch_and_missing_query_or_source() -> None:
    search_result = run_twf_external_readonly_fake_provider_adapter(
        gate=_passed_gate(),
        profile=TwfExternalReadonlyProviderProfileCandidate(
            provider_name="fake_fetch_provider",
            provider_kind="fake_fetch",
            supported_operations=("fetch",),
        ),
        request=_provider_request(operation_family="fetch", query_ref=None),
        records=(_record(),),
    )
    missing_query = run_twf_external_readonly_fake_provider_adapter(
        gate=_passed_gate(),
        profile=_search_profile(),
        request=_provider_request(query_ref=None),
        records=(_record(),),
    )

    assert search_result.status == "blocked"
    assert "provider_request_operation_mismatch" in search_result.blocking_reasons
    assert "provider_source_url_required" in search_result.blocking_reasons
    assert missing_query.status == "blocked"
    assert "provider_query_ref_required" in missing_query.blocking_reasons


def test_fake_provider_blocks_invalid_evidence_records() -> None:
    result = run_twf_external_readonly_fake_provider_adapter(
        gate=_passed_gate(),
        profile=_search_profile(),
        request=_provider_request(),
        records=(
            _record(
                evidence_ref="evidence://bad/ref",
                source_url="https://127.0.0.1/internal",
                sanitized_excerpt="",
            ),
        ),
    )

    assert result.status == "blocked"
    assert result.envelope is None
    assert any(
        reason.startswith("evidence_envelope:evidence://bad/ref:")
        for reason in result.blocking_reasons
    )


def _search_profile() -> TwfExternalReadonlyProviderProfileCandidate:
    return TwfExternalReadonlyProviderProfileCandidate(
        provider_name="fake_search_provider",
        provider_kind="fake_search",
        supported_operations=("search",),
    )


def _provider_request(**overrides: object) -> TwfExternalReadonlyProviderRequestCandidate:
    kwargs = {
        "request_ref": "external-readonly-request://google-search/001",
        "operation_family": "search",
        "query_ref": "query://reference-review/sanitized-topic",
        "envelope_ref": "evidence://external-readonly/envelope/search-001",
    }
    kwargs.update(overrides)
    return TwfExternalReadonlyProviderRequestCandidate(**kwargs)


def _record(**overrides: object) -> TwfExternalReadonlyFakeProviderRecordCandidate:
    kwargs = {
        "evidence_ref": "evidence://external-readonly/fake-search/1",
        "source_url": "https://example.com/reference",
        "retrieved_at": "2026-05-16T10:00:00+00:00",
        "sanitized_excerpt": "Fake provider sanitized excerpt.",
        "citation_index": 1,
        "source_title": "Fake Provider Reference",
    }
    kwargs.update(overrides)
    return TwfExternalReadonlyFakeProviderRecordCandidate(**kwargs)


def _passed_gate(
    *,
    tool_name: str = "google_search_reference_lookup",
    tool_origin: str = "google_search",
    operation_family: str = "search",
    query_ref: str | None = "query://reference-review/sanitized-topic",
    source_url: str | None = None,
):
    return evaluate_twf_external_readonly_network_gate(
        design=TwfExternalReadonlyToolDesignCandidate(
            tool_name=tool_name,
            tool_origin=tool_origin,
            operation_family=operation_family,
            source_ref=f"external-readonly://{tool_origin}/source",
            input_schema_ref=f"schema://{tool_origin}/{operation_family}/input",
            output_boundary_ref=f"boundary://{tool_origin}/sanitized-excerpt",
            adapter_boundary_ref=f"boundary://{tool_origin}/adapter/no-runtime",
            evidence_boundary_ref=f"evidence://{tool_origin}/source-url-timestamp",
        ),
        request=TwfExternalReadonlyNetworkRequestCandidate(
            request_ref=(
                "external-readonly-request://google-search/001"
                if tool_origin == "google_search"
                else "external-readonly-request://url-context/001"
            ),
            tool_name=tool_name,
            tool_origin=tool_origin,
            operation_family=operation_family,
            scope_ref="scope://reference-review/external-readonly",
            query_ref=query_ref,
            source_url=source_url,
            controlled_output_ref="outputs/external-readonly/request.json",
            network_enabled_for_request=True,
        ),
        approval=TwfExternalReadonlyNetworkApprovalCandidate(
            operator_approved=True,
            allow_external_network=True,
            approval_ref="approval://external-readonly/001",
            approved_by="operator://test",
            network_gate_ref="network-gate://external-readonly/001",
            audit_ref="audit://external-readonly/001",
            sanitized_evidence_ref="evidence://external-readonly/request",
        ),
    )


def _blocked_gate():
    return evaluate_twf_external_readonly_network_gate(
        design=TwfExternalReadonlyToolDesignCandidate(
            tool_name="google_search_reference_lookup",
            tool_origin="google_search",
            operation_family="search",
            source_ref="external-readonly://google-search/source",
            input_schema_ref="schema://google-search/search/input",
            output_boundary_ref="boundary://google-search/sanitized-excerpt",
            adapter_boundary_ref="boundary://google-search/adapter/no-runtime",
            evidence_boundary_ref="evidence://google-search/source-url-timestamp",
        ),
        request=TwfExternalReadonlyNetworkRequestCandidate(
            request_ref="external-readonly-request://google-search/001",
            tool_name="google_search_reference_lookup",
            tool_origin="google_search",
            operation_family="search",
            scope_ref="scope://reference-review/external-readonly",
            query_ref="query://reference-review/sanitized-topic",
        ),
        approval=TwfExternalReadonlyNetworkApprovalCandidate(),
    )
