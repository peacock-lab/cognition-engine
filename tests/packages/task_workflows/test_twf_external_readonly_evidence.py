from __future__ import annotations

import hashlib

from cognition_task_workflows._external_readonly.evidence import (
    TwfExternalReadonlyEvidenceItemCandidate,
    build_twf_external_readonly_evidence_envelope,
    review_twf_external_readonly_evidence_item,
    twf_external_readonly_evidence_envelope_status_dict,
)
from cognition_task_workflows._external_readonly.network_gate import (
    TwfExternalReadonlyNetworkApprovalCandidate,
    TwfExternalReadonlyNetworkRequestCandidate,
    evaluate_twf_external_readonly_network_gate,
)
from cognition_task_workflows._external_readonly.tool_design import (
    TwfExternalReadonlyToolDesignCandidate,
)


def test_evidence_envelope_projects_only_sanitized_model_context() -> None:
    gate = _passed_gate()
    item = _valid_item()

    envelope = build_twf_external_readonly_evidence_envelope(
        gate=gate,
        items=(item,),
        envelope_ref="evidence://external-readonly/envelope/google-search-001",
    )
    status = twf_external_readonly_evidence_envelope_status_dict(envelope)

    assert envelope.status == "valid"
    assert envelope.allowed_for_model_context is True
    assert envelope.evidence_refs == ("evidence://external-readonly/item/001",)
    assert envelope.source_urls == ("https://example.com/reference",)
    assert status["metadata"]["does_not_perform_external_network_calls"] is True
    assert status["metadata"]["does_not_write_files"] is True
    assert status["metadata"]["approval_ref_present"] is True
    assert status["model_context_items"] == [
        {
            "citation_index": 1,
            "evidence_ref": "evidence://external-readonly/item/001",
            "source_url": "https://example.com/reference",
            "source_title": "Example Reference",
            "retrieved_at": "2026-05-16T10:00:00+00:00",
            "item_type": "url_context_excerpt",
            "sanitized_excerpt": "External reference excerpt for model context.",
            "content_hash": _hash("External reference excerpt for model context."),
        }
    ]
    assert "approval://external-readonly/001" not in str(status)
    assert "audit://external-readonly/001" not in str(status)


def test_item_review_blocks_invalid_source_timestamp_ref_and_hash() -> None:
    review = review_twf_external_readonly_evidence_item(
        _valid_item(
            evidence_ref="evidence://other/item",
            source_url="https://127.0.0.1/admin",
            retrieved_at="2026-05-16 10:00:00",
            citation_index=0,
            content_hash="not-the-hash",
            item_type="raw_html",
        )
    )

    assert review.status == "blocked"
    assert "evidence_ref_not_external_readonly" in review.blocking_reasons
    assert "source_url_not_external_https" in review.blocking_reasons
    assert "retrieved_at_invalid" in review.blocking_reasons
    assert "citation_index_invalid" in review.blocking_reasons
    assert "content_hash_mismatch" in review.blocking_reasons
    assert "item_type_not_allowed" in review.blocking_reasons


def test_item_review_blocks_raw_content_and_secret_material() -> None:
    review = review_twf_external_readonly_evidence_item(
        _valid_item(
            sanitized_excerpt="This leaked api_key=abc and must be rejected.",
            raw_response_included=True,
            raw_html_included=True,
            full_page_content_included=True,
            raw_query_included=True,
            raw_url_context_included=True,
            cookies_included=True,
            auth_headers_included=True,
            tokens_included=True,
            script_content_included=True,
            form_data_included=True,
            metadata={"auth": {"token": "secret"}},
        )
    )

    assert review.status == "blocked"
    assert "sanitized_excerpt_contains_secret_marker" in review.blocking_reasons
    assert "raw_response_forbidden" in review.blocking_reasons
    assert "raw_html_forbidden" in review.blocking_reasons
    assert "full_page_content_forbidden" in review.blocking_reasons
    assert "raw_query_forbidden" in review.blocking_reasons
    assert "raw_url_context_forbidden" in review.blocking_reasons
    assert "cookies_forbidden" in review.blocking_reasons
    assert "auth_headers_forbidden" in review.blocking_reasons
    assert "tokens_forbidden" in review.blocking_reasons
    assert "script_content_forbidden" in review.blocking_reasons
    assert "form_data_forbidden" in review.blocking_reasons
    assert "raw_credential_material_forbidden" in review.blocking_reasons


def test_envelope_blocks_closed_gate_empty_items_and_invalid_envelope_ref() -> None:
    gate = _blocked_gate()

    envelope = build_twf_external_readonly_evidence_envelope(
        gate=gate,
        items=(),
        envelope_ref="evidence://other/envelope",
    )

    assert envelope.status == "blocked"
    assert envelope.allowed_for_model_context is False
    assert "network_gate_not_open" in envelope.blocking_reasons
    assert "evidence_items_required" in envelope.blocking_reasons
    assert "envelope_ref_not_external_readonly" in envelope.blocking_reasons
    assert envelope.model_context_items == ()


def test_envelope_blocks_duplicate_refs_duplicate_citations_and_budget() -> None:
    first = _valid_item(sanitized_excerpt="A" * 20, citation_index=1)
    second = _valid_item(
        sanitized_excerpt="B" * 20,
        citation_index=1,
    )

    envelope = build_twf_external_readonly_evidence_envelope(
        gate=_passed_gate(),
        items=(first, second),
        envelope_ref="evidence://external-readonly/envelope/duplicate",
        max_total_excerpt_chars=30,
    )

    assert envelope.status == "blocked"
    assert "duplicate_evidence_ref" in envelope.blocking_reasons
    assert "duplicate_citation_index" in envelope.blocking_reasons
    assert "total_excerpt_chars_exceeds_budget" in envelope.blocking_reasons
    assert envelope.model_context_items == ()


def test_envelope_blocks_item_review_failures_with_item_prefix() -> None:
    bad_item = _valid_item(
        evidence_ref="evidence://external-readonly/item/bad",
        sanitized_excerpt="",
    )

    envelope = build_twf_external_readonly_evidence_envelope(
        gate=_passed_gate(),
        items=(bad_item,),
        envelope_ref="evidence://external-readonly/envelope/bad-item",
    )

    assert envelope.status == "blocked"
    assert (
        "evidence://external-readonly/item/bad:sanitized_excerpt_required"
        in envelope.blocking_reasons
    )
    assert envelope.model_context_items == ()


def _valid_item(**overrides: object) -> TwfExternalReadonlyEvidenceItemCandidate:
    excerpt = str(
        overrides.get(
            "sanitized_excerpt",
            "External reference excerpt for model context.",
        )
    )
    kwargs = {
        "evidence_ref": "evidence://external-readonly/item/001",
        "source_url": "https://example.com/reference",
        "retrieved_at": "2026-05-16T10:00:00+00:00",
        "sanitized_excerpt": excerpt,
        "citation_index": 1,
        "source_title": "Example Reference",
        "content_hash": _hash(excerpt),
    }
    kwargs.update(overrides)
    return TwfExternalReadonlyEvidenceItemCandidate(**kwargs)


def _passed_gate():
    return evaluate_twf_external_readonly_network_gate(
        design=_valid_design(),
        request=_valid_request(),
        approval=_valid_approval(),
    )


def _blocked_gate():
    return evaluate_twf_external_readonly_network_gate(
        design=_valid_design(),
        request=_valid_request(network_enabled_for_request=False),
        approval=TwfExternalReadonlyNetworkApprovalCandidate(),
    )


def _valid_design() -> TwfExternalReadonlyToolDesignCandidate:
    return TwfExternalReadonlyToolDesignCandidate(
        tool_name="google_search_reference_lookup",
        tool_origin="google_search",
        operation_family="search",
        source_ref="external-readonly://google-search/source",
        input_schema_ref="schema://google-search/search/input",
        output_boundary_ref="boundary://google-search/sanitized-excerpt",
        adapter_boundary_ref="boundary://google-search/adapter/no-runtime",
        evidence_boundary_ref="evidence://google-search/source-url-timestamp",
    )


def _valid_request(**overrides: object) -> TwfExternalReadonlyNetworkRequestCandidate:
    kwargs = {
        "request_ref": "external-readonly-request://google-search/001",
        "tool_name": "google_search_reference_lookup",
        "tool_origin": "google_search",
        "operation_family": "search",
        "scope_ref": "scope://reference-review/external-readonly",
        "query_ref": "query://reference-review/sanitized-topic",
        "controlled_output_ref": "outputs/external-readonly/google-search-001.json",
        "network_enabled_for_request": True,
    }
    kwargs.update(overrides)
    return TwfExternalReadonlyNetworkRequestCandidate(**kwargs)


def _valid_approval() -> TwfExternalReadonlyNetworkApprovalCandidate:
    return TwfExternalReadonlyNetworkApprovalCandidate(
        operator_approved=True,
        allow_external_network=True,
        approval_ref="approval://external-readonly/001",
        approved_by="operator://test",
        network_gate_ref="network-gate://external-readonly/001",
        audit_ref="audit://external-readonly/001",
        sanitized_evidence_ref="evidence://external-readonly/google-search-001",
    )


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
