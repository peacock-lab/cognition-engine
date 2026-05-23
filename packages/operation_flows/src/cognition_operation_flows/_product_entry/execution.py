"""Private product-entry workflow execution helpers."""

from __future__ import annotations

from typing import Any

from cognition_operation_flows._product_entry.types import (
    TWF_PRODUCT_ENTRY_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
    TWF_PRODUCT_ENTRY_PLAN_WORKFLOW_NAME,
    TWF_PRODUCT_ENTRY_REFERENCE_REVIEW_WORKFLOW_NAME,
    TWF_PRODUCT_ENTRY_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
)
from cognition_operation_flows._workflows.config_profile_explain import (
    run_twf_config_profile_explain_workflow,
)
from cognition_operation_flows._workflows.plan import (
    DEFAULT_PLAN_MODEL_NAME,
    TwfPlanWorkflowResultCandidate,
    run_twf_plan_workflow,
)
from cognition_operation_flows._workflows.reference_review import (
    run_twf_reference_review_workflow,
)
from cognition_operation_flows._requests.builder import (
    TwfWorkflowRequestCandidate,
)
from cognition_operation_flows._workflows.run_workspace_evidence_audit import (
    run_twf_run_workspace_evidence_audit_workflow,
)


def run_twf_product_entry_workflow(
    workflow_name: str,
    workflow_request: TwfWorkflowRequestCandidate,
) -> Any:
    """Run a TWF workflow by name for product-entry consumers."""

    if workflow_name == TWF_PRODUCT_ENTRY_PLAN_WORKFLOW_NAME:
        return run_twf_plan_workflow(workflow_request)
    if workflow_name == TWF_PRODUCT_ENTRY_REFERENCE_REVIEW_WORKFLOW_NAME:
        return run_twf_reference_review_workflow(workflow_request)
    if workflow_name == TWF_PRODUCT_ENTRY_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME:
        return run_twf_config_profile_explain_workflow(workflow_request)
    if (
        workflow_name
        == TWF_PRODUCT_ENTRY_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME
    ):
        return run_twf_run_workspace_evidence_audit_workflow(workflow_request)
    raise ValueError(f"unsupported Twf workflow: {workflow_name}")


def twf_product_entry_result_updates_latest_plan(workflow_result: Any) -> bool:
    """Return whether a workflow result should update latest plan state."""

    return isinstance(workflow_result, TwfPlanWorkflowResultCandidate)


def get_twf_product_entry_result_display_text(workflow_result: Any) -> str:
    """Return sanitized terminal display text from a workflow result."""

    return str(getattr(workflow_result, "terminal_display_text", "") or "")


def get_twf_product_entry_default_model_name() -> str:
    """Return the default model name used by TWF product-entry request building."""

    return DEFAULT_PLAN_MODEL_NAME


__all__ = [
    "get_twf_product_entry_default_model_name",
    "get_twf_product_entry_result_display_text",
    "run_twf_product_entry_workflow",
    "twf_product_entry_result_updates_latest_plan",
]
