from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas.product_gateway_cli import (
    PRODUCT_GATEWAY_CLI_SURFACE_PAYLOAD_VERSION,
    PRODUCT_GATEWAY_CLI_OPERATION_FLOW_PLAN_WORKFLOW_NAME,
    ProductGatewayCliOperationFlowExecutionInputSchema,
    ProductGatewayCliOperationFlowExecutionOptionsSchema,
    ProductGatewayCliOperationFlowExecutionResultSchema,
    ProductGatewayCliOperationFlowGovernanceRefsSchema,
    ProductGatewayCliOperationFlowLatestPlanSnapshotSchema,
    ProductGatewayCliOperationFlowReferenceWorkspaceControlsSchema,
    ProductGatewayCliOperationFlowRequestDraftInputSchema,
    ProductGatewayCliOperationFlowRunWorkspaceSnapshotSchema,
    ProductGatewayCliOperationFlowRouteInputSchema,
    ProductGatewayCliOperationFlowRouteProjectionSchema,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_SOURCE_ROOT = REPO_ROOT / "packages" / "schemas" / "src" / "schemas"


def test_product_gateway_cli_route_input_accepts_sanitized_shape() -> None:
    route_input = ProductGatewayCliOperationFlowRouteInputSchema(
        request_id="chat-1/turn-001",
        sanitized_user_text="请基于资料做方案",
        chat_session_id="chat-1",
        turn_index=1,
        reference_paths=("tasks/b1/example.md",),
        metadata={"source": "test"},
    )

    assert PRODUCT_GATEWAY_CLI_SURFACE_PAYLOAD_VERSION
    assert route_input.request_id == "chat-1/turn-001"
    assert route_input.reference_paths == ("tasks/b1/example.md",)


def test_product_gateway_cli_request_draft_accepts_contract_controls() -> None:
    draft = ProductGatewayCliOperationFlowRequestDraftInputSchema(
        workflow_name=PRODUCT_GATEWAY_CLI_OPERATION_FLOW_PLAN_WORKFLOW_NAME,
        sanitized_user_text="设计一个鱼塘方案",
        governance_refs=ProductGatewayCliOperationFlowGovernanceRefsSchema(
            approval_ref="approval://cli-test",
            audit_ref="audit://cli-test",
        ),
        controls=ProductGatewayCliOperationFlowReferenceWorkspaceControlsSchema(
            reference_paths=("tasks/b1/example.md",),
            run_workspace_enabled=True,
            run_workspace_max_write_bytes=65536,
        ),
        live_model_allowed=False,
    )

    assert draft.workflow_name == PRODUCT_GATEWAY_CLI_OPERATION_FLOW_PLAN_WORKFLOW_NAME
    assert draft.controls is not None
    assert draft.controls.run_workspace_enabled is True


def test_product_gateway_cli_route_projection_accepts_summary_shape() -> None:
    projection = ProductGatewayCliOperationFlowRouteProjectionSchema(
        request_id="route-1",
        entry_kind="operation_flow_route",
        execution_mode="preflight_only",
        matched=True,
        workflow_name=PRODUCT_GATEWAY_CLI_OPERATION_FLOW_PLAN_WORKFLOW_NAME,
        route_reason="matched_plan_intent",
        confidence="high",
        source="product_gateway.cli_surface",
        registry_version="v1",
        registry_workflow_count=4,
    )

    assert projection.matched is True
    assert projection.workflow_name == PRODUCT_GATEWAY_CLI_OPERATION_FLOW_PLAN_WORKFLOW_NAME


def test_product_gateway_cli_execution_input_wraps_request_contracts() -> None:
    execution_input = ProductGatewayCliOperationFlowExecutionInputSchema(
        request_id="route-1",
        route_projection=ProductGatewayCliOperationFlowRouteProjectionSchema(
            request_id="route-1",
            entry_kind="operation_flow_route",
            execution_mode="preflight_only",
            matched=True,
            workflow_name=PRODUCT_GATEWAY_CLI_OPERATION_FLOW_PLAN_WORKFLOW_NAME,
            route_reason="matched_plan_intent",
            confidence="high",
            source="product_gateway.cli_surface",
            registry_version="v1",
            registry_workflow_count=4,
        ),
        request_draft_input=ProductGatewayCliOperationFlowRequestDraftInputSchema(
            workflow_name=PRODUCT_GATEWAY_CLI_OPERATION_FLOW_PLAN_WORKFLOW_NAME,
            sanitized_user_text="设计一个鱼塘方案",
        ),
        execution_options=ProductGatewayCliOperationFlowExecutionOptionsSchema(
            config_root="config",
            environment="local",
            profile="local-live",
            reference_entrypoint_explicit_args={"operator_approved": True},
        ),
    )

    assert execution_input.request_id == "route-1"
    assert execution_input.execution_options.environment == "local"


def test_product_gateway_cli_latest_plan_snapshot_accepts_status_shape() -> None:
    snapshot = ProductGatewayCliOperationFlowLatestPlanSnapshotSchema(
        status="no_live_boundary",
        reference_context_status="completed",
        reference_evidence_ref_count=1,
        workspace=ProductGatewayCliOperationFlowRunWorkspaceSnapshotSchema(
            workspace_ref="workspace://test",
            workspace_path="outputs/task-workflows/test",
            workflow_name=PRODUCT_GATEWAY_CLI_OPERATION_FLOW_PLAN_WORKFLOW_NAME,
            run_id="run-1",
            workspace_created=True,
            artifact_refs=("artifact://terminal",),
            evidence_refs=("evidence://reference",),
            result_refs=("result://workflow",),
            max_write_bytes=65536,
        ),
        product_gateway_route_projection={
            "status": "matched",
            "workflow_name": PRODUCT_GATEWAY_CLI_OPERATION_FLOW_PLAN_WORKFLOW_NAME,
        },
        no_live=True,
    )

    assert snapshot.workspace is not None
    assert snapshot.workspace.workspace_created is True
    assert snapshot.reference_evidence_ref_count == 1


def test_product_gateway_cli_execution_result_rejects_raw_summary() -> None:
    with pytest.raises(ValidationError):
        ProductGatewayCliOperationFlowExecutionResultSchema(
            handled=True,
            product_response_summary={
                "request_id": "route-raw",
                "raw_response": {"must": "not leak"},
            },
        )


def test_product_gateway_cli_workspace_snapshot_validates_write_limits() -> None:
    with pytest.raises(ValidationError):
        ProductGatewayCliOperationFlowRunWorkspaceSnapshotSchema(max_write_bytes=0)

    with pytest.raises(ValidationError):
        ProductGatewayCliOperationFlowRunWorkspaceSnapshotSchema(artifact_refs=("",))


def test_product_gateway_cli_execution_input_rejects_mismatched_request_id() -> None:
    with pytest.raises(ValidationError):
        ProductGatewayCliOperationFlowExecutionInputSchema(
            request_id="route-1",
            route_projection=ProductGatewayCliOperationFlowRouteProjectionSchema(
                request_id="route-2",
                entry_kind="operation_flow_route",
                execution_mode="preflight_only",
                matched=True,
                workflow_name=PRODUCT_GATEWAY_CLI_OPERATION_FLOW_PLAN_WORKFLOW_NAME,
                route_reason="matched_plan_intent",
                confidence="high",
                source="product_gateway.cli_surface",
                registry_version="v1",
                registry_workflow_count=4,
            ),
            request_draft_input=ProductGatewayCliOperationFlowRequestDraftInputSchema(
                workflow_name=PRODUCT_GATEWAY_CLI_OPERATION_FLOW_PLAN_WORKFLOW_NAME,
                sanitized_user_text="设计一个鱼塘方案",
            ),
        )


def test_product_gateway_cli_contract_rejects_raw_and_runtime_leakage() -> None:
    with pytest.raises(ValidationError):
        ProductGatewayCliOperationFlowRouteInputSchema(
            request_id="route-raw",
            sanitized_user_text="安全文本",
            metadata={"raw_response": "must not cross boundary"},
        )

    with pytest.raises(ValidationError):
        ProductGatewayCliOperationFlowRouteInputSchema(
            request_id="route-runtime",
            sanitized_user_text="安全文本",
            metadata={"object_module": "runtime_container.entry"},
        )


def test_product_gateway_cli_schema_has_no_execution_layer_imports() -> None:
    source = (SCHEMA_SOURCE_ROOT / "product_gateway_cli.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:product_gateway|cognition_operation_flows|runtime_container|"
        r"composition|adk_adapter|google\.adk|litellm)\b",
        re.MULTILINE,
    )

    assert forbidden_imports.search(source) is None
