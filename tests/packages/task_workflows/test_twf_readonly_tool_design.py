from __future__ import annotations

from cognition_task_workflows._tools.readonly_tool_design import (
    TWF_READONLY_TOOL_ALLOWED_OPERATIONS,
    TWF_READONLY_TOOL_ALLOWED_ORIGINS,
    TwfReadonlyToolDesignCandidate,
    build_twf_readonly_tool_design_summary,
    review_twf_readonly_tool_design,
    twf_readonly_tool_design_summary_status_dict,
)


def test_adk_mcp_readonly_operations_are_design_allowed_without_runtime() -> None:
    summary = build_twf_readonly_tool_design_summary(
        (
            TwfReadonlyToolDesignCandidate(
                tool_name="read_reference_excerpt",
                tool_origin="adk_function_tool",
                operation_family="read",
                input_schema_ref="schema://adk-tools/read-reference/input",
                output_boundary_ref="boundary://adk-tools/read-reference/excerpt",
                adapter_boundary_ref="boundary://adk-adapter/function-tool/sanitized",
                reads_project_context=True,
            ),
            TwfReadonlyToolDesignCandidate(
                tool_name="mcp_search_docs",
                tool_origin="mcp_toolset",
                operation_family="search",
                toolset_name="project_docs_mcp",
                source_ref="mcp://project-docs",
                input_schema_ref="schema://mcp/search-docs/input",
                output_boundary_ref="boundary://mcp/search-docs/sanitized",
                adapter_boundary_ref="boundary://adk-mcp/toolset/sanitized",
                requires_auth=True,
                touches_external_system=True,
            ),
            TwfReadonlyToolDesignCandidate(
                tool_name="mcp_grep_excerpt",
                tool_origin="mcp_toolset",
                operation_family="grep",
                toolset_name="project_docs_mcp",
                source_ref="mcp://project-docs",
                input_schema_ref="schema://mcp/grep/input",
                output_boundary_ref="boundary://mcp/grep/sanitized",
                adapter_boundary_ref="boundary://adk-mcp/toolset/sanitized",
            ),
        )
    )
    status = twf_readonly_tool_design_summary_status_dict(summary)

    assert summary.status == "allowed"
    assert summary.allowed_tool_names == (
        "read_reference_excerpt",
        "mcp_search_docs",
        "mcp_grep_excerpt",
    )
    assert summary.blocked_tool_names == ()
    assert summary.runtime_enabled is False
    assert summary.tool_execution_enabled is False
    assert summary.mcp_runtime_enabled is False
    assert status["allowed_origins"] == sorted(TWF_READONLY_TOOL_ALLOWED_ORIGINS)
    assert status["allowed_operations"] == sorted(
        TWF_READONLY_TOOL_ALLOWED_OPERATIONS
    )
    assert status["reviews"][0]["confirmation_required"] is True
    assert status["reviews"][1]["risk_level"] == "medium"
    assert status["metadata"]["does_not_execute_tools"] is True


def test_write_or_execute_operation_is_blocked_for_readonly_design() -> None:
    review = review_twf_readonly_tool_design(
        TwfReadonlyToolDesignCandidate(
            tool_name="update_reference_file",
            tool_origin="adk_function_tool",
            operation_family="writeFile",
            input_schema_ref="schema://adk-tools/write/input",
            output_boundary_ref="boundary://adk-tools/write/sanitized",
            adapter_boundary_ref="boundary://adk-adapter/function-tool/sanitized",
            writes_files=True,
            executes_code=True,
        )
    )

    assert review.status == "blocked"
    assert review.allowed_for_design is False
    assert review.risk_level == "blocked"
    assert "operation_family_not_in_readonly_allowlist" in review.blocking_reasons
    assert "operation_family_contains_side_effect_token" in review.blocking_reasons
    assert "writes_files_forbidden" in review.blocking_reasons
    assert "executes_code_forbidden" in review.blocking_reasons


def test_mcp_design_requires_source_schema_and_output_boundary() -> None:
    review = review_twf_readonly_tool_design(
        TwfReadonlyToolDesignCandidate(
            tool_name="mcp_list_docs",
            tool_origin="mcp_toolset",
            operation_family="list",
        )
    )

    assert review.status == "blocked"
    assert "toolset_source_ref_required" in review.blocking_reasons
    assert "input_schema_ref_required" in review.blocking_reasons
    assert "output_boundary_ref_required" in review.blocking_reasons
    assert "adapter_boundary_ref_required" in review.blocking_reasons


def test_runtime_and_raw_payload_flags_are_blocked() -> None:
    review = review_twf_readonly_tool_design(
        TwfReadonlyToolDesignCandidate(
            tool_name="mcp_runtime_passthrough",
            tool_origin="mcp_toolset",
            operation_family="read",
            source_ref="mcp://project-docs",
            input_schema_ref="schema://mcp/read/input",
            output_boundary_ref="boundary://mcp/read/sanitized",
            adapter_boundary_ref="boundary://adk-mcp/toolset/sanitized",
            opens_mcp_runtime=True,
            loads_runtime_objects=True,
            raw_runtime_object_included=True,
            raw_tool_payload_included=True,
            metadata={"api_key": "secret"},
        )
    )

    assert review.status == "blocked"
    assert "mcp_runtime_must_remain_closed" in review.blocking_reasons
    assert "runtime_object_loading_forbidden" in review.blocking_reasons
    assert "raw_runtime_object_forbidden" in review.blocking_reasons
    assert "raw_tool_payload_forbidden" in review.blocking_reasons
    assert "raw_credential_material_forbidden" in review.blocking_reasons


def test_google_search_and_url_context_remain_deferred_candidates() -> None:
    search_review = review_twf_readonly_tool_design(
        TwfReadonlyToolDesignCandidate(
            tool_name="google_search",
            tool_origin="google_search",
            operation_family="search",
            input_schema_ref="schema://external/search/input",
            output_boundary_ref="boundary://external/search/sanitized",
            adapter_boundary_ref="boundary://external/search/adapter",
        )
    )
    url_review = review_twf_readonly_tool_design(
        TwfReadonlyToolDesignCandidate(
            tool_name="url_context_read",
            tool_origin="url_context",
            operation_family="read",
            input_schema_ref="schema://external/url-context/input",
            output_boundary_ref="boundary://external/url-context/sanitized",
            adapter_boundary_ref="boundary://external/url-context/adapter",
        )
    )

    assert search_review.status == "blocked"
    assert url_review.status == "blocked"
    assert "tool_origin_not_allowed_for_adk_mcp_readonly" in (
        search_review.blocking_reasons
    )
    assert "tool_origin_not_allowed_for_adk_mcp_readonly" in (
        url_review.blocking_reasons
    )
    assert search_review.warnings == ("external_readonly_tool_origin_deferred",)
    assert url_review.warnings == ("external_readonly_tool_origin_deferred",)
