from __future__ import annotations

from pathlib import Path
from typing import Any

import contract_core.runtime as contract_runtime
from adk_adapter import AdkWorkflowRunner
from observability_hub import (
    ArtifactManifest,
    EvidenceBundle,
    EventTrace,
    InvocationBindingRecord,
    RunRecord,
    build_evidence_bundle,
)
from composition.runtime import RuntimeCompositionOptions, build_standard_runtime_runner
from runtime.orchestrator import StandardRuntimeRunner


def test_minimal_runtime_observability_loop_builds_evidence_bundle_from_runtime_result() -> None:
    from google.adk.agents.context import Context
    from google.adk.events import Event
    from google.adk.events.event import NodeInfo
    from google.adk.workflow import START, BaseNode, Workflow

    class MinimalNode(BaseNode):
        async def _run_impl(self, *, ctx: Context, node_input: Any):
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                node_info=NodeInfo(path=ctx.node_path),
                output={
                    "ok": True,
                    "node": self.name,
                    "echo": "hello from minimal runtime observability loop",
                },
            )

    workflow = Workflow(
        name="minimal_runtime_observability_loop_workflow",
        edges=[(START, MinimalNode(name="minimal_runtime_observability_node"))],
    )
    runtime_runner = build_standard_runtime_runner(
        options=RuntimeCompositionOptions(
            config_root=Path("config"),
            environment="local",
        ),
        workflow_runner=AdkWorkflowRunner(
            workflow=workflow,
            app_name="test_minimal_runtime_observability_loop",
            user_id="minimal-runtime-observability-user",
        ),
    )

    runtime_result = runtime_runner.run(
        contract_runtime.RuntimeInput(
            runtime_id="runtime-minimal-observability-001",
            workflow_ref=contract_runtime.WorkflowRef(
                workflow_id="workflow-minimal-observability-001",
                name="minimal_runtime_observability_loop_workflow",
            ),
            invocation_ref=contract_runtime.InvocationRef(invocation_id="requested-loop-001"),
            input_payload={"message": "hello from minimal runtime observability loop"},
            metadata={"requested_invocation_id": "requested-loop-001"},
        )
    )
    evidence_bundle = build_evidence_bundle(runtime_result)

    assert isinstance(runtime_runner, StandardRuntimeRunner)
    assert isinstance(runtime_result, contract_runtime.RuntimeResult)
    assert runtime_result.status == contract_runtime.RuntimeStatus.SUCCESS
    assert runtime_result.workflow_result is not None
    assert isinstance(runtime_result.workflow_result, contract_runtime.WorkflowResult)
    assert runtime_result.workflow_result.status == contract_runtime.RuntimeStatus.SUCCESS
    assert runtime_result.events
    assert len(runtime_result.events) >= 2
    assert all(isinstance(event, contract_runtime.RuntimeEvent) for event in runtime_result.events)

    workflow_result = runtime_result.workflow_result
    assert workflow_result.metadata["adapter"] == "adk_adapter"
    assert workflow_result.metadata["requested_invocation_id"] == "requested-loop-001"
    assert workflow_result.metadata["adk_invocation_id"]
    assert workflow_result.metadata["event_count"] >= 2

    assert isinstance(evidence_bundle, EvidenceBundle)
    assert evidence_bundle.source_type == "runtime_result"
    assert evidence_bundle.runtime_id == "runtime-minimal-observability-001"
    assert isinstance(evidence_bundle.run_record, RunRecord)
    assert isinstance(evidence_bundle.event_trace, EventTrace)
    assert isinstance(evidence_bundle.artifact_manifest, ArtifactManifest)
    assert isinstance(evidence_bundle.invocation, InvocationBindingRecord)

    assert evidence_bundle.run_record.status == runtime_result.status.value
    assert evidence_bundle.run_record.event_count == evidence_bundle.event_trace.event_count
    assert evidence_bundle.event_trace.event_count >= 1
    assert (
        "minimal_runtime_observability_loop_workflow@1/"
        "minimal_runtime_observability_node@1"
    ) in evidence_bundle.event_trace.node_paths
    assert "minimal_runtime_observability_loop_workflow" in evidence_bundle.event_trace.authors

    assert evidence_bundle.invocation.requested_invocation_id == "requested-loop-001"
    assert evidence_bundle.invocation.adk_invocation_id == workflow_result.metadata["adk_invocation_id"]
    assert evidence_bundle.invocation.actual_invocation_id == "requested-loop-001"
    assert evidence_bundle.invocation.workflow_id == "workflow-minimal-observability-001"

    assert evidence_bundle.artifact_manifest is not None
    assert evidence_bundle.artifact_manifest.artifact_count == 0
    assert evidence_bundle.artifact_manifest.artifacts == []
    assert any("ArtifactManifest was built empty" in warning for warning in evidence_bundle.warnings)
    assert any("Runtime timing fields were incomplete" in warning for warning in evidence_bundle.warnings)

    assert evidence_bundle.metadata["evidence_contract"]["input_type"] == "schemas.runtime.RuntimeResult"
    assert evidence_bundle.metadata["evidence_contract"]["missing_facts_kept_in"] == ["warnings", "metadata"]
