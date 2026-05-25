from __future__ import annotations

from cognition_operation_flows._tools.toolset_admission import (
    OperationFlowToolOperationFactsCandidate,
    build_operation_flow_toolset_inventory,
    operation_flow_toolset_inventory_status_dict,
    evaluate_operation_flow_toolset_admission,
    review_operation_flow_tool_operation_risk,
)


def test_dynamic_toolset_requires_filter_or_allowlist() -> None:
    admission = evaluate_operation_flow_toolset_admission(
        toolset_name="api_hub_customer",
        toolset_kind="api_hub",
        source_ref="apihub://projects/demo/locations/us/apis/customer",
        discovery_credential_ref="credential://discovery",
        execution_credential_ref="credential://execution",
    )

    assert admission.admitted is False
    assert "tool_filter_or_allowlist_required" in admission.blocking_reasons
    assert admission.tool_filter_required is True


def test_toolset_admission_blocks_raw_credential_material() -> None:
    admission = evaluate_operation_flow_toolset_admission(
        toolset_name="application_integration",
        toolset_kind="application_integration",
        source_ref="integration://projects/demo/locations/us/integrations/order",
        tool_filter=("list_orders",),
        raw_config={"service_account_json": "{\"private_key\":\"secret\"}"},
    )

    assert admission.admitted is False
    assert "raw_credential_material_forbidden" in admission.blocking_reasons
    assert admission.credential_boundary["raw_credential_material_included"] is False
    assert admission.credential_boundary["raw_credential_key_count"] == 1


def test_readonly_external_operation_is_allowed_with_confirmation() -> None:
    review = review_operation_flow_tool_operation_risk(
        OperationFlowToolOperationFactsCandidate(
            tool_name="list_customers",
            toolset_name="api_hub_customer",
            toolset_kind="api_hub",
            operation_id="listCustomers",
            http_method="GET",
            path="/customers",
            requires_auth=True,
            touches_external_system=True,
        )
    )

    assert review.risk_level == "medium"
    assert review.readonly_operation is True
    assert review.allowed_for_readonly is True
    assert review.confirmation_required is True
    assert review.blocking_reasons == ()


def test_side_effect_operation_is_not_allowed_for_readonly_exposure() -> None:
    review = review_operation_flow_tool_operation_risk(
        OperationFlowToolOperationFactsCandidate(
            tool_name="create_customer",
            toolset_name="api_hub_customer",
            toolset_kind="api_hub",
            operation_id="createCustomer",
            http_method="POST",
            path="/customers",
            has_request_body=True,
        )
    )

    assert review.risk_level == "high"
    assert review.readonly_operation is False
    assert review.allowed_for_readonly is False
    assert "tool_not_readonly" in review.blocking_reasons


def test_missing_operation_identity_blocks_risk_review() -> None:
    review = review_operation_flow_tool_operation_risk(
        OperationFlowToolOperationFactsCandidate(
            tool_name="mystery_tool",
            toolset_name="unknown",
            toolset_kind="toolset",
        )
    )

    assert review.risk_level == "blocked"
    assert review.allowed_for_readonly is False
    assert "tool_operation_identity_missing" in review.blocking_reasons


def test_camel_case_operation_id_is_split_for_risk_review() -> None:
    readonly = review_operation_flow_tool_operation_risk(
        OperationFlowToolOperationFactsCandidate(
            tool_name="list_customers",
            toolset_name="api_hub_customer",
            toolset_kind="api_hub",
            operation_id="listCustomers",
            touches_external_system=False,
        )
    )
    side_effect = review_operation_flow_tool_operation_risk(
        OperationFlowToolOperationFactsCandidate(
            tool_name="create_customer",
            toolset_name="api_hub_customer",
            toolset_kind="api_hub",
            operation_id="createCustomer",
            touches_external_system=False,
        )
    )

    assert readonly.allowed_for_readonly is True
    assert readonly.risk_level == "low"
    assert side_effect.allowed_for_readonly is False
    assert "tool_not_readonly" in side_effect.blocking_reasons


def test_inventory_exposes_only_selected_readonly_tools() -> None:
    admission = evaluate_operation_flow_toolset_admission(
        toolset_name="api_hub_customer",
        toolset_kind="api_hub",
        source_ref="apihub://projects/demo/locations/us/apis/customer",
        tool_filter=("list_customers", "create_customer"),
        discovery_credential_ref="credential://discovery",
        execution_credential_ref="credential://execution",
    )
    inventory = build_operation_flow_toolset_inventory(
        admission,
        (
            OperationFlowToolOperationFactsCandidate(
                tool_name="list_customers",
                toolset_name="api_hub_customer",
                toolset_kind="api_hub",
                operation_id="listCustomers",
                http_method="GET",
                path="/customers",
                requires_auth=True,
            ),
            OperationFlowToolOperationFactsCandidate(
                tool_name="create_customer",
                toolset_name="api_hub_customer",
                toolset_kind="api_hub",
                operation_id="createCustomer",
                http_method="POST",
                path="/customers",
                has_request_body=True,
            ),
            OperationFlowToolOperationFactsCandidate(
                tool_name="delete_customer",
                toolset_name="api_hub_customer",
                toolset_kind="api_hub",
                operation_id="deleteCustomer",
                http_method="DELETE",
                path="/customers/{id}",
            ),
        ),
    )
    status = operation_flow_toolset_inventory_status_dict(inventory)

    assert admission.admitted is True
    assert inventory.exposed_tool_names == ("list_customers",)
    assert inventory.blocked_tool_names == ("create_customer",)
    assert "delete_customer" not in inventory.blocked_tool_names
    assert status["selection"]["exposed_tool_names"] == ["list_customers"]
    assert status["tools"][0]["confirmation_required"] is True
    assert status["toolset"]["credential_boundary"] == {
        "discovery_credential_ref_present": True,
        "execution_credential_ref_present": True,
        "raw_credential_material_included": False,
        "raw_credential_key_count": 0,
    }
