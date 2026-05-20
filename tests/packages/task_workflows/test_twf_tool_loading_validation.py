from __future__ import annotations

from cognition_task_workflows._tools.reference_reader import REFERENCE_READER_TOOL_NAME
from cognition_task_workflows._tools.exposure_profile import resolve_twf_tool_exposure_profile
from cognition_task_workflows._tools.loading_validation import (
    LOCAL_REFERENCE_READER_INPUT_SCHEMA_REF,
    LOCAL_REFERENCE_READER_OUTPUT_BOUNDARY_REF,
    twf_tool_loading_gate_status_dict,
    validate_twf_tool_loading_gate,
)
from cognition_task_workflows._tools.toolset_admission import TwfToolOperationFactsCandidate


def test_default_reference_reader_passes_loading_validation(tmp_path) -> None:
    resolution = resolve_twf_tool_exposure_profile(repo_root=tmp_path)

    gate = validate_twf_tool_loading_gate(resolution)
    status = twf_tool_loading_gate_status_dict(gate)

    assert gate.status == "passed"
    assert gate.risk_gate_status == "passed"
    assert gate.allowed_tool_names == (REFERENCE_READER_TOOL_NAME,)
    assert gate.blocked_tool_names == ()
    assert gate.blocking_reasons == ()
    validation = gate.validations[0]
    assert validation.tool_name == REFERENCE_READER_TOOL_NAME
    assert validation.loadable is True
    assert validation.dependencies_satisfied is True
    assert validation.risk_level == "low"
    assert validation.input_schema_satisfied is True
    assert validation.output_boundary_declared is True
    assert validation.metadata["input_schema_ref"] == (
        LOCAL_REFERENCE_READER_INPUT_SCHEMA_REF
    )
    assert validation.metadata["output_boundary_ref"] == (
        LOCAL_REFERENCE_READER_OUTPUT_BOUNDARY_REF
    )
    assert status["validations"][0]["allowed_for_execution"] is True


def test_external_readonly_tool_requires_operator_confirmation(tmp_path) -> None:
    resolution = _resolve_external_readonly_tool(tmp_path)

    gate = validate_twf_tool_loading_gate(resolution)

    assert resolution.exposed_tool_names == ("list_customers",)
    assert gate.status == "blocked"
    assert gate.blocked_tool_names == ("list_customers",)
    assert "list_customers:operator_confirmation_required" in (
        gate.blocking_reasons
    )


def test_external_readonly_tool_passes_with_confirmation_and_boundaries(
    tmp_path,
) -> None:
    resolution = _resolve_external_readonly_tool(tmp_path)

    gate = validate_twf_tool_loading_gate(
        resolution,
        operator_approved=True,
        approval_ref="approval://external-readonly",
    )

    assert gate.status == "passed"
    assert gate.allowed_tool_names == ("list_customers",)
    assert gate.validations[0].confirmation_required is True
    assert gate.validations[0].confirmation_satisfied is True


def test_loading_validation_blocks_missing_schema_and_output_boundary(
    tmp_path,
) -> None:
    resolution = resolve_twf_tool_exposure_profile(
        profile_name="external_readonly",
        repo_root=tmp_path,
        profile_config=_external_readonly_profile(max_risk_level="low"),
        operation_facts_by_toolset={
            "api_hub_customer": (
                TwfToolOperationFactsCandidate(
                    tool_name="list_customers",
                    toolset_name="api_hub_customer",
                    toolset_kind="api_hub",
                    operation_id="listCustomers",
                    http_method="GET",
                    path="/customers",
                    touches_external_system=False,
                ),
            )
        },
    )

    gate = validate_twf_tool_loading_gate(resolution)

    assert resolution.exposed_tool_names == ("list_customers",)
    assert gate.status == "blocked"
    assert "list_customers:tool_input_schema_missing" in gate.blocking_reasons
    assert "list_customers:tool_output_boundary_missing" in gate.blocking_reasons


def test_side_effect_tool_is_blocked_by_loading_gate(tmp_path) -> None:
    resolution = resolve_twf_tool_exposure_profile(
        profile_name="external_write",
        repo_root=tmp_path,
        profile_config={
            "profiles": {
                "external_write": {
                    "toolsets": [
                        {
                            "toolset_name": "api_hub_customer",
                            "toolset_kind": "api_hub",
                            "source_ref": "apihub://customer",
                            "allowlist_tool_names": ["create_customer"],
                            "tool_filter": ["create_customer"],
                            "max_risk_level": "high",
                            "discovery_credential_ref": "credential://discovery",
                            "execution_credential_ref": "credential://execution",
                        }
                    ],
                }
            }
        },
        operation_facts_by_toolset={
            "api_hub_customer": (
                TwfToolOperationFactsCandidate(
                    tool_name="create_customer",
                    toolset_name="api_hub_customer",
                    toolset_kind="api_hub",
                    operation_id="createCustomer",
                    http_method="POST",
                    path="/customers",
                    has_request_body=True,
                    metadata={
                        "input_schema_ref": "schema://api-hub/create-customer",
                        "output_boundary_ref": "boundary://api-hub/sanitized-create",
                    },
                ),
            )
        },
    )

    gate = validate_twf_tool_loading_gate(
        resolution,
        operator_approved=True,
        approval_ref="approval://external-write",
    )

    assert resolution.blocked_tool_names == ("create_customer",)
    assert gate.status == "blocked"
    assert "create_customer:tool_not_exposed" in gate.blocking_reasons
    assert "create_customer:tool_not_allowed_for_readonly" in (
        gate.blocking_reasons
    )


def _resolve_external_readonly_tool(tmp_path):
    return resolve_twf_tool_exposure_profile(
        profile_name="external_readonly",
        repo_root=tmp_path,
        profile_config=_external_readonly_profile(max_risk_level="medium"),
        operation_facts_by_toolset={
            "api_hub_customer": (
                TwfToolOperationFactsCandidate(
                    tool_name="list_customers",
                    toolset_name="api_hub_customer",
                    toolset_kind="api_hub",
                    operation_id="listCustomers",
                    http_method="GET",
                    path="/customers",
                    requires_auth=True,
                    touches_external_system=True,
                    metadata={
                        "input_schema_ref": "schema://api-hub/list-customers",
                        "output_boundary_ref": "boundary://api-hub/sanitized-list",
                    },
                ),
            )
        },
    )


def _external_readonly_profile(*, max_risk_level: str) -> dict[str, object]:
    return {
        "profiles": {
            "external_readonly": {
                "toolsets": [
                    {
                        "toolset_name": "api_hub_customer",
                        "toolset_kind": "api_hub",
                        "source_ref": "apihub://customer",
                        "allowlist_tool_names": ["list_customers"],
                        "tool_filter": ["list_customers"],
                        "max_risk_level": max_risk_level,
                        "discovery_credential_ref": "credential://discovery",
                        "execution_credential_ref": "credential://execution",
                    }
                ],
            }
        }
    }
