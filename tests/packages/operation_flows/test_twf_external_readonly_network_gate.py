from __future__ import annotations

from cognition_operation_flows._external_readonly.network_gate import (
    TwfExternalReadonlyNetworkApprovalCandidate,
    TwfExternalReadonlyNetworkRequestCandidate,
    build_twf_external_readonly_network_gate_summary,
    evaluate_twf_external_readonly_network_gate,
    twf_external_readonly_network_gate_status_dict,
    twf_external_readonly_network_gate_summary_status_dict,
)
from cognition_operation_flows._external_readonly.tool_design import (
    TwfExternalReadonlyToolDesignCandidate,
)


def _valid_design(
    *,
    tool_name: str = "google_search_reference_lookup",
    tool_origin: str = "google_search",
    operation_family: str = "search",
    **overrides: object,
) -> TwfExternalReadonlyToolDesignCandidate:
    kwargs = {
        "tool_name": tool_name,
        "tool_origin": tool_origin,
        "operation_family": operation_family,
        "source_ref": f"external-readonly://{tool_origin}/source",
        "input_schema_ref": f"schema://{tool_origin}/{operation_family}/input",
        "output_boundary_ref": f"boundary://{tool_origin}/sanitized-excerpt",
        "adapter_boundary_ref": f"boundary://{tool_origin}/adapter/no-runtime",
        "evidence_boundary_ref": f"evidence://{tool_origin}/source-url-timestamp",
    }
    kwargs.update(overrides)
    return TwfExternalReadonlyToolDesignCandidate(**kwargs)


def _valid_request(
    *,
    request_ref: str = "external-readonly-request://google-search/001",
    tool_name: str = "google_search_reference_lookup",
    tool_origin: str = "google_search",
    operation_family: str = "search",
    **overrides: object,
) -> TwfExternalReadonlyNetworkRequestCandidate:
    kwargs = {
        "request_ref": request_ref,
        "tool_name": tool_name,
        "tool_origin": tool_origin,
        "operation_family": operation_family,
        "scope_ref": "scope://reference-review/external-readonly",
        "query_ref": "query://reference-review/sanitized-topic",
        "controlled_output_ref": "outputs/external-readonly/google-search-001.json",
        "network_enabled_for_request": True,
    }
    kwargs.update(overrides)
    return TwfExternalReadonlyNetworkRequestCandidate(**kwargs)


def _valid_approval(**overrides: object) -> TwfExternalReadonlyNetworkApprovalCandidate:
    kwargs = {
        "operator_approved": True,
        "allow_external_network": True,
        "approval_ref": "approval://external-readonly/001",
        "approved_by": "operator://test",
        "network_gate_ref": "network-gate://external-readonly/001",
        "audit_ref": "audit://external-readonly/001",
        "sanitized_evidence_ref": "evidence://external-readonly/google-search-001",
    }
    kwargs.update(overrides)
    return TwfExternalReadonlyNetworkApprovalCandidate(**kwargs)


def test_google_search_network_gate_passes_without_network_call() -> None:
    gate = evaluate_twf_external_readonly_network_gate(
        design=_valid_design(),
        request=_valid_request(),
        approval=_valid_approval(),
    )
    status = twf_external_readonly_network_gate_status_dict(gate)

    assert gate.status == "passed"
    assert gate.allowed_for_network_request is True
    assert gate.network_gate_open is True
    assert gate.operator_approval_satisfied is True
    assert gate.controlled_output_satisfied is True
    assert gate.external_network_call_performed is False
    assert gate.tool_execution_performed is False
    assert status["metadata"]["does_not_perform_external_network_calls"] is True
    assert status["metadata"]["approval_ref_present"] is True
    assert "approval://external-readonly/001" not in str(status)
    assert "audit://external-readonly/001" not in str(status)


def test_url_context_network_gate_requires_external_https_source_url() -> None:
    gate = evaluate_twf_external_readonly_network_gate(
        design=_valid_design(
            tool_name="url_context_reference_read",
            tool_origin="url_context",
            operation_family="read",
        ),
        request=_valid_request(
            request_ref="external-readonly-request://url-context/001",
            tool_name="url_context_reference_read",
            tool_origin="url_context",
            operation_family="read",
            query_ref=None,
            source_url="https://example.com/reference",
            controlled_output_ref="evidence://external-readonly/url-context-001",
        ),
        approval=_valid_approval(
            sanitized_evidence_ref="evidence://external-readonly/url-context-001",
        ),
    )

    assert gate.status == "passed"
    assert gate.tool_origin == "url_context"
    assert gate.operation_family == "read"
    assert gate.metadata["source_url_present"] is True
    assert gate.external_network_call_performed is False


def test_network_gate_blocks_missing_explicit_network_and_operator_approval() -> None:
    gate = evaluate_twf_external_readonly_network_gate(
        design=_valid_design(),
        request=_valid_request(network_enabled_for_request=False),
        approval=TwfExternalReadonlyNetworkApprovalCandidate(),
    )

    assert gate.status == "blocked"
    assert gate.network_gate_open is False
    assert "network_enabled_for_request_required" in gate.blocking_reasons
    assert "operator_approval_not_true" in gate.blocking_reasons
    assert "operator_approval_external_network_not_true" in gate.blocking_reasons
    assert "approval_ref_required" in gate.blocking_reasons
    assert "network_gate_ref_required" in gate.blocking_reasons
    assert "sanitized_evidence_ref_required" in gate.blocking_reasons


def test_network_gate_blocks_design_failure_and_request_identity_mismatch() -> None:
    gate = evaluate_twf_external_readonly_network_gate(
        design=_valid_design(network_enabled_by_default=True),
        request=_valid_request(
            tool_name="url_context_reference_read",
            tool_origin="url_context",
            operation_family="search",
        ),
        approval=_valid_approval(),
    )

    assert gate.status == "blocked"
    assert "design_review_not_allowed" in gate.blocking_reasons
    assert "request_tool_identity_mismatch" in gate.blocking_reasons
    assert "operation_family_not_allowed_for_tool_origin" in gate.blocking_reasons


def test_network_gate_blocks_private_url_and_unbounded_request_limits() -> None:
    gate = evaluate_twf_external_readonly_network_gate(
        design=_valid_design(
            tool_name="url_context_reference_fetch",
            tool_origin="url_context",
            operation_family="fetch",
        ),
        request=_valid_request(
            tool_name="url_context_reference_fetch",
            tool_origin="url_context",
            operation_family="fetch",
            query_ref=None,
            source_url="https://127.0.0.1/admin",
            max_result_count=11,
            max_bytes=50_001,
            timeout_seconds=31,
            redirect_limit=4,
        ),
        approval=_valid_approval(),
    )

    assert gate.status == "blocked"
    assert "source_url_not_external_https" in gate.blocking_reasons
    assert "max_result_count_out_of_bounds" in gate.blocking_reasons
    assert "max_bytes_out_of_bounds" in gate.blocking_reasons
    assert "timeout_seconds_out_of_bounds" in gate.blocking_reasons
    assert "redirect_limit_out_of_bounds" in gate.blocking_reasons


def test_network_gate_blocks_raw_payloads_side_effects_and_secret_metadata() -> None:
    gate = evaluate_twf_external_readonly_network_gate(
        design=_valid_design(),
        request=_valid_request(
            controlled_output_ref="outputs/external-readonly/../leak.json",
            raw_query_included=True,
            raw_request_payload_included=True,
            raw_network_response_included=True,
            stores_raw_response=True,
            stores_full_page_content=True,
            uploads_content=True,
            allows_auth_headers=True,
            allows_cookies=True,
            allows_login=True,
            allows_form_submission=True,
            executes_javascript_action=True,
            follows_unbounded_redirects=True,
            writes_files=True,
            mutates_external_system=True,
            executes_code=True,
            executes_shell=True,
            calls_llm=True,
            tool_execution_performed=True,
            external_network_call_performed=True,
            metadata={"auth": {"token": "secret"}},
        ),
        approval=_valid_approval(metadata={"api_key": "secret"}),
    )

    assert gate.status == "blocked"
    assert "controlled_output_ref_required" in gate.blocking_reasons
    assert "external_network_call_forbidden_in_gate" in gate.blocking_reasons
    assert "tool_execution_forbidden_in_gate" in gate.blocking_reasons
    assert "raw_query_forbidden" in gate.blocking_reasons
    assert "raw_request_payload_forbidden" in gate.blocking_reasons
    assert "raw_network_response_forbidden" in gate.blocking_reasons
    assert "raw_response_storage_forbidden" in gate.blocking_reasons
    assert "full_page_content_storage_forbidden" in gate.blocking_reasons
    assert "upload_forbidden" in gate.blocking_reasons
    assert "auth_headers_forbidden" in gate.blocking_reasons
    assert "cookies_forbidden" in gate.blocking_reasons
    assert "login_flow_forbidden" in gate.blocking_reasons
    assert "form_submission_forbidden" in gate.blocking_reasons
    assert "javascript_action_forbidden" in gate.blocking_reasons
    assert "unbounded_redirects_forbidden" in gate.blocking_reasons
    assert "writes_files_forbidden" in gate.blocking_reasons
    assert "mutates_external_system_forbidden" in gate.blocking_reasons
    assert "executes_code_forbidden" in gate.blocking_reasons
    assert "executes_shell_forbidden" in gate.blocking_reasons
    assert "calls_llm_forbidden" in gate.blocking_reasons
    assert "raw_credential_material_forbidden" in gate.blocking_reasons


def test_network_gate_summary_is_sanitized_and_non_executing() -> None:
    allowed = evaluate_twf_external_readonly_network_gate(
        design=_valid_design(),
        request=_valid_request(),
        approval=_valid_approval(),
    )
    blocked = evaluate_twf_external_readonly_network_gate(
        design=_valid_design(
            tool_name="url_context_reference_read",
            tool_origin="url_context",
            operation_family="read",
        ),
        request=_valid_request(
            request_ref="external-readonly-request://url-context/blocked",
            tool_name="url_context_reference_read",
            tool_origin="url_context",
            operation_family="read",
            query_ref=None,
        ),
        approval=_valid_approval(),
    )

    summary = build_twf_external_readonly_network_gate_summary((allowed, blocked))
    status = twf_external_readonly_network_gate_summary_status_dict(summary)

    assert summary.status == "blocked"
    assert summary.allowed_request_refs == (
        "external-readonly-request://google-search/001",
    )
    assert summary.blocked_request_refs == (
        "external-readonly-request://url-context/blocked",
    )
    assert status["external_network_call_performed"] is False
    assert status["tool_execution_performed"] is False
    assert status["metadata"]["does_not_execute_tools"] is True
    assert status["metadata"]["does_not_perform_external_network_calls"] is True
