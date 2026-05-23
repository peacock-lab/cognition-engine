from __future__ import annotations

from cognition_operation_flows._external_readonly.tool_design import (
    TWF_EXTERNAL_READONLY_ALLOWED_OPERATIONS,
    TWF_EXTERNAL_READONLY_ALLOWED_ORIGINS,
    TwfExternalReadonlyToolDesignCandidate,
    build_twf_external_readonly_tool_design_summary,
    review_twf_external_readonly_tool_design,
    twf_external_readonly_tool_design_summary_status_dict,
)


def _valid_external_design(
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


def test_google_search_and_url_context_are_design_allowed_without_execution() -> None:
    summary = build_twf_external_readonly_tool_design_summary(
        (
            _valid_external_design(),
            _valid_external_design(
                tool_name="url_context_reference_read",
                tool_origin="url_context",
                operation_family="read",
            ),
            _valid_external_design(
                tool_name="url_context_reference_fetch",
                tool_origin="url_context",
                operation_family="fetch",
            ),
        )
    )
    status = twf_external_readonly_tool_design_summary_status_dict(summary)

    assert summary.status == "allowed"
    assert summary.allowed_tool_names == (
        "google_search_reference_lookup",
        "url_context_reference_read",
        "url_context_reference_fetch",
    )
    assert summary.blocked_tool_names == ()
    assert summary.network_enabled_by_default is False
    assert summary.external_tool_runtime_enabled is False
    assert summary.tool_execution_enabled is False
    assert summary.external_network_call_performed is False
    assert status["allowed_origins"] == sorted(
        TWF_EXTERNAL_READONLY_ALLOWED_ORIGINS
    )
    assert status["allowed_operations"] == sorted(
        TWF_EXTERNAL_READONLY_ALLOWED_OPERATIONS
    )
    assert status["reviews"][0]["risk_level"] == "medium"
    assert status["reviews"][0]["network_gate_required"] is True
    assert status["reviews"][0]["confirmation_required"] is True
    assert status["reviews"][0]["metadata"]["does_not_execute_tool"] is True
    assert (
        status["reviews"][0]["metadata"]["external_network_call_performed"]
        is False
    )
    assert status["metadata"]["does_not_execute_tools"] is True
    assert status["metadata"]["does_not_perform_external_network_calls"] is True


def test_origin_operation_mismatch_is_blocked() -> None:
    search_fetch_review = review_twf_external_readonly_tool_design(
        _valid_external_design(operation_family="fetch")
    )
    url_search_review = review_twf_external_readonly_tool_design(
        _valid_external_design(
            tool_name="url_context_reference_search",
            tool_origin="url_context",
            operation_family="search",
        )
    )

    assert search_fetch_review.status == "blocked"
    assert "operation_family_not_allowed_for_tool_origin" in (
        search_fetch_review.blocking_reasons
    )
    assert url_search_review.status == "blocked"
    assert "operation_family_not_allowed_for_tool_origin" in (
        url_search_review.blocking_reasons
    )


def test_external_design_requires_source_schema_adapter_and_evidence_boundaries() -> None:
    review = review_twf_external_readonly_tool_design(
        TwfExternalReadonlyToolDesignCandidate(
            tool_name="url_context_reference_read",
            tool_origin="url_context",
            operation_family="read",
        )
    )

    assert review.status == "blocked"
    assert "source_ref_required" in review.blocking_reasons
    assert "input_schema_ref_required" in review.blocking_reasons
    assert "output_boundary_ref_required" in review.blocking_reasons
    assert "adapter_boundary_ref_required" in review.blocking_reasons
    assert "evidence_boundary_ref_required" in review.blocking_reasons


def test_default_network_runtime_raw_storage_and_credentials_are_blocked() -> None:
    review = review_twf_external_readonly_tool_design(
        _valid_external_design(
            network_enabled_by_default=True,
            external_tool_runtime_enabled=True,
            tool_execution_enabled=True,
            stores_raw_response=True,
            stores_full_page_content=True,
            stores_cookies=True,
            stores_tokens=True,
            raw_tool_payload_included=True,
            raw_network_response_included=True,
            metadata={"auth": {"api_key": "secret"}},
        )
    )

    assert review.status == "blocked"
    assert "network_enabled_by_default_forbidden" in review.blocking_reasons
    assert "external_tool_runtime_must_remain_closed" in review.blocking_reasons
    assert "tool_execution_enabled_forbidden" in review.blocking_reasons
    assert "raw_response_storage_forbidden" in review.blocking_reasons
    assert "full_page_content_storage_forbidden" in review.blocking_reasons
    assert "cookie_storage_forbidden" in review.blocking_reasons
    assert "token_storage_forbidden" in review.blocking_reasons
    assert "raw_tool_payload_forbidden" in review.blocking_reasons
    assert "raw_network_response_forbidden" in review.blocking_reasons
    assert "raw_credential_material_forbidden" in review.blocking_reasons


def test_interaction_side_effects_and_write_actions_are_blocked() -> None:
    review = review_twf_external_readonly_tool_design(
        _valid_external_design(
            operation_family="submitSearch",
            allows_login=True,
            allows_form_submission=True,
            executes_javascript_action=True,
            follows_unbounded_redirects=True,
            writes_files=True,
            mutates_external_system=True,
            executes_code=True,
            executes_shell=True,
            calls_llm=True,
        )
    )

    assert review.status == "blocked"
    assert "operation_family_contains_side_effect_token" in review.blocking_reasons
    assert "login_flow_forbidden" in review.blocking_reasons
    assert "form_submission_forbidden" in review.blocking_reasons
    assert "javascript_action_forbidden" in review.blocking_reasons
    assert "unbounded_redirects_forbidden" in review.blocking_reasons
    assert "writes_files_forbidden" in review.blocking_reasons
    assert "mutates_external_system_forbidden" in review.blocking_reasons
    assert "executes_code_forbidden" in review.blocking_reasons
    assert "executes_shell_forbidden" in review.blocking_reasons
    assert "calls_llm_forbidden" in review.blocking_reasons


def test_external_network_requirement_can_be_warned_without_enabling_network() -> None:
    review = review_twf_external_readonly_tool_design(
        _valid_external_design(network_access_required=False)
    )

    assert review.status == "allowed"
    assert review.warnings == ("external_tool_network_access_not_declared",)
    assert review.metadata["network_enabled_by_default"] is False
    assert review.metadata["external_network_call_performed"] is False
