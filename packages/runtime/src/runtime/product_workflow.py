"""Minimal product workflow runner for the v0.6.0 connection point.

This module is intentionally only a first-patch bridge from minimal product
facts into the standard runtime/evidence chain. It does not generate product
briefs, decision packs, LLM responses, ADK-backed workflows, or files.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from behavior_contracts.runtime import WorkflowRunner
from schemas.runtime import (
    ArtifactDelta,
    ArtifactRef,
    DeltaOperation,
    NodeRef,
    RuntimeEvent,
    RuntimeEventType,
    RuntimeStatus,
    WorkflowInput,
    WorkflowResult,
)

MINIMAL_PRODUCT_WORKFLOW_KIND = "minimal_product_workflow"
MINIMAL_PRODUCT_OUTPUT_KIND = "product_summary"


@dataclass(frozen=True)
class MinimalProductWorkflowRunner(WorkflowRunner):
    """Map minimal product facts into WorkflowResult for EvidenceBundle intake."""

    workflow_kind: str = MINIMAL_PRODUCT_WORKFLOW_KIND
    product_output_kind: str = MINIMAL_PRODUCT_OUTPUT_KIND
    node_id: str = "minimal-product-summary"

    def run_workflow(self, workflow_input: WorkflowInput) -> WorkflowResult:
        insight_id = self._insight_id(workflow_input)
        summary = self._summary(workflow_input, insight_id)
        product_fact = {
            "workflow_kind": self.workflow_kind,
            "product_output_kind": self.product_output_kind,
            "insight_id": insight_id,
            "summary": summary,
        }
        node_ref = NodeRef(
            node_id=self.node_id,
            name="minimal product summary",
            source="runtime.product_workflow",
            metadata={"workflow_kind": self.workflow_kind},
        )
        artifact_delta = ArtifactDelta(
            delta_id=f"{workflow_input.invocation_ref.invocation_id}:product-summary",
            invocation_ref=workflow_input.invocation_ref,
            artifact_ref=ArtifactRef(
                artifact_id=f"{workflow_input.invocation_ref.invocation_id}:product-summary",
                name="minimal-product-summary",
                metadata=product_fact,
            ),
            operation=DeltaOperation.SET,
            metadata=product_fact,
        )
        event = RuntimeEvent(
            event_id=f"{workflow_input.invocation_ref.invocation_id}:product-workflow-completed",
            event_type=RuntimeEventType.WORKFLOW_COMPLETED,
            invocation_ref=workflow_input.invocation_ref,
            workflow_ref=workflow_input.workflow_ref,
            node_ref=node_ref,
            payload=product_fact,
            artifact_delta_refs=[artifact_delta.delta_id],
            metadata={
                **product_fact,
                "adapter_name": "minimal_product_workflow_runner",
                "node_path": f"{workflow_input.workflow_ref.workflow_id}/{self.node_id}",
                "author": self.workflow_kind,
            },
        )
        return WorkflowResult(
            workflow_ref=workflow_input.workflow_ref,
            status=RuntimeStatus.SUCCESS,
            invocation_ref=workflow_input.invocation_ref,
            events=[event],
            artifact_deltas=[artifact_delta],
            metadata={
                **workflow_input.metadata,
                **product_fact,
                "adapter_name": "minimal_product_workflow_runner",
                "requested_invocation_id": workflow_input.invocation_ref.invocation_id,
                "actual_invocation_id": workflow_input.invocation_ref.invocation_id,
            },
        )

    def _insight_id(self, workflow_input: WorkflowInput) -> str:
        raw_value = workflow_input.input_payload.get("insight_id") or workflow_input.metadata.get(
            "insight_id"
        )
        if isinstance(raw_value, str) and raw_value.strip():
            return raw_value.strip()
        return "unknown-insight"

    def _summary(self, workflow_input: WorkflowInput, insight_id: str) -> str:
        raw_value: Any = workflow_input.input_payload.get("summary")
        if isinstance(raw_value, str) and raw_value.strip():
            return raw_value.strip()
        return f"Minimal product workflow accepted insight {insight_id}."
