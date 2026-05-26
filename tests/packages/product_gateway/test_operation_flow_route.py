from __future__ import annotations

import pytest
from pydantic import ValidationError

from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayExecutionMode,
)
from product_gateway._operation_flows.route import (
    InternalOperationFlowRouteInput,
    build_internal_operation_flow_route_projection,
    build_internal_operation_flow_route_request,
)


def test_product_gateway_operation_flow_route_request_is_prefight_only() -> None:
    request = build_internal_operation_flow_route_request(
        InternalOperationFlowRouteInput(
            request_id="operation_flow-route-request-1",
            sanitized_user_text="我要建一个鱼塘，帮我设计建设方案",
        )
    )

    assert request.entry_kind is ProductGatewayEntryKind.TASK_WORKFLOW_ROUTE
    assert request.execution_mode is ProductGatewayExecutionMode.PREFLIGHT_ONLY
    assert request.input_payload == {
        "sanitized_user_text": "我要建一个鱼塘，帮我设计建设方案",
        "reference_path_count": 0,
        "external_readonly_evidence_path_count": 0,
        "run_workspace_requested": False,
        "audit_run_workspace_requested": False,
    }
    assert request.metadata["source"] == "product_gateway._operation_flows.route"
    assert request.metadata["route_only"] is True
    assert request.metadata["workflow_execution_enabled"] is False


def test_product_gateway_operation_flow_route_projection_routes_plan_without_execution() -> None:
    projection = build_internal_operation_flow_route_projection(
        {
            "request_id": "operation_flow-route-plan",
            "sanitized_user_text": "我要建一个鱼塘，500平米大，请帮我设计建设方案",
            "turn_index": 3,
            "run_workspace_requested": True,
        }
    )

    assert projection.entry_kind == "operation_flow_route"
    assert projection.execution_mode == "preflight_only"
    assert projection.matched is True
    assert projection.workflow_name == "operation_flow_plan_workflow"
    assert projection.task_kind == "plan_design"
    assert projection.turn_index == 3
    assert projection.requires_workspace is True
    assert projection.registry_workflow_count == 4
    assert projection.metadata["route_only"] is True
    assert projection.metadata["workflow_execution_enabled"] is False


def test_product_gateway_operation_flow_route_projection_routes_reference_review() -> None:
    projection = build_internal_operation_flow_route_projection(
        {
            "request_id": "operation_flow-route-reference-review",
            "sanitized_user_text": "请审查这些资料，指出是否符合当前主线",
            "reference_paths": ("tasks/b1/example.md",),
        }
    )

    assert projection.matched is True
    assert projection.workflow_name == "operation_flow_reference_review_workflow"
    assert projection.requires_tools == ("local_reference_reader",)
    assert projection.metadata["route_status"]["workflow_name"] == (
        "operation_flow_reference_review_workflow"
    )


def test_product_gateway_operation_flow_route_projection_routes_external_readonly_evidence_review() -> None:
    projection = build_internal_operation_flow_route_projection(
        {
            "request_id": "operation_flow-route-external-evidence-review",
            "sanitized_user_text": "请审查这份外部只读证据摘要",
            "external_readonly_evidence_paths": (
                "outputs/external-readonly/cli-fetch/example.json",
            ),
        }
    )

    assert projection.matched is True
    assert projection.workflow_name == "operation_flow_reference_review_workflow"
    assert projection.requires_tools == ()
    assert projection.metadata["route_metadata"][
        "external_readonly_evidence_path_count"
    ] == 1


def test_product_gateway_operation_flow_route_input_rejects_empty_reference_path() -> None:
    with pytest.raises(ValidationError):
        InternalOperationFlowRouteInput(
            request_id="operation_flow-route-invalid",
            sanitized_user_text="请审查资料",
            reference_paths=("",),
        )


def test_product_gateway_operation_flow_route_input_rejects_empty_external_evidence_path() -> None:
    with pytest.raises(ValidationError):
        InternalOperationFlowRouteInput(
            request_id="operation_flow-route-invalid-external-evidence",
            sanitized_user_text="请审查资料",
            external_readonly_evidence_paths=("",),
        )


@pytest.mark.parametrize(
    "raw_payload",
    [
        {"prompt": "raw prompt"},
        {"messages": [{"role": "user", "content": "raw"}]},
        {"raw_user_message": "raw"},
    ],
)
def test_product_gateway_operation_flow_route_request_rejects_raw_metadata(
    raw_payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        build_internal_operation_flow_route_request(
            {
                "request_id": "operation_flow-route-raw",
                "sanitized_user_text": "请审查资料",
                "metadata": raw_payload,
            }
        )
