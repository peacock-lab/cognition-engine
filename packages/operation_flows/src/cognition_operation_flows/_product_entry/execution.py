"""Private product-entry workflow execution helpers."""

from __future__ import annotations

from typing import Any

from cognition_operation_flows._product_entry.types import (
    OPERATION_FLOW_PRODUCT_ENTRY_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
    OPERATION_FLOW_PRODUCT_ENTRY_PLAN_WORKFLOW_NAME,
    OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_REVIEW_WORKFLOW_NAME,
    OPERATION_FLOW_PRODUCT_ENTRY_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
)
from cognition_operation_flows._workflows.config_profile_explain import (
    run_operation_flow_config_profile_explain_workflow,
)
from cognition_operation_flows._workflows.plan import (
    DEFAULT_PLAN_MODEL_NAME,
    OperationFlowPlanWorkflowResultCandidate,
    run_operation_flow_plan_workflow,
)
from cognition_operation_flows._workflows.reference_review import (
    run_operation_flow_reference_review_workflow,
)
from cognition_operation_flows._requests.builder import (
    OperationFlowWorkflowRequestCandidate,
)
from cognition_operation_flows._workflows.run_workspace_evidence_audit import (
    run_operation_flow_run_workspace_evidence_audit_workflow,
)


def run_operation_flow_product_entry_workflow(
    workflow_name: str,
    workflow_request: OperationFlowWorkflowRequestCandidate,
) -> Any:
    """Run an operation flow workflow by name for product-entry consumers."""

    if workflow_name == OPERATION_FLOW_PRODUCT_ENTRY_PLAN_WORKFLOW_NAME:
        return run_operation_flow_plan_workflow(workflow_request)
    if workflow_name == OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_REVIEW_WORKFLOW_NAME:
        return run_operation_flow_reference_review_workflow(workflow_request)
    if workflow_name == OPERATION_FLOW_PRODUCT_ENTRY_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME:
        return run_operation_flow_config_profile_explain_workflow(workflow_request)
    if (
        workflow_name
        == OPERATION_FLOW_PRODUCT_ENTRY_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME
    ):
        return run_operation_flow_run_workspace_evidence_audit_workflow(workflow_request)
    raise ValueError(f"unsupported OperationFlow workflow: {workflow_name}")


def operation_flow_product_entry_result_updates_latest_plan(workflow_result: Any) -> bool:
    """Return whether a workflow result should update latest plan state."""

    return isinstance(workflow_result, OperationFlowPlanWorkflowResultCandidate)


def get_operation_flow_product_entry_result_display_text(workflow_result: Any) -> str:
    """Return sanitized terminal display text from a workflow result."""

    return str(getattr(workflow_result, "terminal_display_text", "") or "")


def get_operation_flow_product_entry_default_model_name() -> str:
    """Return the default model name used by operation flow product-entry request building."""

    return DEFAULT_PLAN_MODEL_NAME


__all__ = [
    "get_operation_flow_product_entry_default_model_name",
    "get_operation_flow_product_entry_result_display_text",
    "run_operation_flow_product_entry_workflow",
    "operation_flow_product_entry_result_updates_latest_plan",
]
