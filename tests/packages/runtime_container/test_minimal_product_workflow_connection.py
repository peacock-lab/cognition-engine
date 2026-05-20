from pathlib import Path
from typing import Any

import contract_core.runtime as contract_runtime
from observability_hub import EvidenceBundle, build_evidence_bundle
from runtime.product_workflow import (
    MINIMAL_PRODUCT_OUTPUT_KIND,
    MINIMAL_PRODUCT_WORKFLOW_KIND,
    MinimalProductWorkflowRunner,
)
from composition.runtime import RuntimeCompositionOptions, build_standard_runtime_runner
from runtime.orchestrator import StandardRuntimeRunner

FULL_PRODUCT_OUTPUT_KEYS = {
    "product_brief",
    "decision_pack",
    "llm_response",
    "model_enhancement",
    "output_file",
    "file_path",
    "adk_workflow",
    "dashboard",
}


def _build_minimal_product_evidence() -> tuple[
    object,
    contract_runtime.RuntimeResult,
    EvidenceBundle,
]:
    runtime_runner = build_standard_runtime_runner(
        options=RuntimeCompositionOptions(
            config_root=Path("config"),
            environment="local",
        ),
        workflow_runner=MinimalProductWorkflowRunner(),
    )
    runtime_input = contract_runtime.RuntimeInput(
        runtime_id="runtime-product-001",
        workflow_ref=contract_runtime.WorkflowRef(
            workflow_id="workflow-product-minimal-001",
            name=MINIMAL_PRODUCT_WORKFLOW_KIND,
            source="v0.6.0-minimal-product-connection",
        ),
        invocation_ref=contract_runtime.InvocationRef(
            invocation_id="inv-product-001",
            runtime_id="runtime-product-001",
            workflow_id="workflow-product-minimal-001",
        ),
        input_payload={
            "insight_id": "insight-adk-runner-centrality",
            "summary": "Runner is the minimal product workflow anchor.",
        },
        metadata={"connection_task": "074"},
    )

    runtime_result = runtime_runner.run(runtime_input)
    evidence_bundle = build_evidence_bundle(runtime_result)

    return runtime_runner, runtime_result, evidence_bundle


def _has_forbidden_key(value: Any, forbidden_keys: set[str]) -> bool:
    if isinstance(value, dict):
        return any(
            str(key) in forbidden_keys or _has_forbidden_key(item, forbidden_keys)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_has_forbidden_key(item, forbidden_keys) for item in value)
    return False


def test_minimal_product_workflow_connects_runtime_result_to_evidence_bundle() -> None:
    runtime_runner, runtime_result, evidence_bundle = _build_minimal_product_evidence()

    assert isinstance(runtime_runner, StandardRuntimeRunner)
    assert runtime_result.status == contract_runtime.RuntimeStatus.SUCCESS
    assert runtime_result.workflow_result is not None
    assert runtime_result.workflow_result.status == contract_runtime.RuntimeStatus.SUCCESS
    assert runtime_result.workflow_result.metadata["workflow_kind"] == MINIMAL_PRODUCT_WORKFLOW_KIND
    assert runtime_result.workflow_result.metadata["product_output_kind"] == MINIMAL_PRODUCT_OUTPUT_KIND
    assert runtime_result.workflow_result.metadata["insight_id"] == "insight-adk-runner-centrality"
    assert runtime_result.workflow_result.metadata["requested_invocation_id"] == "inv-product-001"
    assert runtime_result.events[0].payload["summary"] == "Runner is the minimal product workflow anchor."
    assert runtime_result.artifact_deltas[0].metadata["product_output_kind"] == MINIMAL_PRODUCT_OUTPUT_KIND

    assert isinstance(evidence_bundle, EvidenceBundle)
    assert evidence_bundle.runtime_id == "runtime-product-001"
    assert evidence_bundle.workflow_id == "workflow-product-minimal-001"
    assert evidence_bundle.run_record.workflow_id == "workflow-product-minimal-001"
    assert evidence_bundle.run_record.adapter_name == "minimal_product_workflow_runner"
    assert evidence_bundle.event_trace.event_count == 1
    assert evidence_bundle.event_trace.events[0]["metadata"]["workflow_kind"] == MINIMAL_PRODUCT_WORKFLOW_KIND
    assert evidence_bundle.event_trace.events[0]["metadata"]["insight_id"] == "insight-adk-runner-centrality"
    assert evidence_bundle.artifact_manifest.artifact_count == 1
    assert (
        evidence_bundle.artifact_manifest.artifacts[0]["metadata"]["product_output_kind"]
        == MINIMAL_PRODUCT_OUTPUT_KIND
    )
    assert evidence_bundle.invocation is not None
    assert evidence_bundle.invocation.requested_invocation_id == "inv-product-001"
    assert evidence_bundle.invocation.actual_invocation_id == "inv-product-001"
    assert not any("EventTrace was built empty" in warning for warning in evidence_bundle.warnings)
    assert not any("ArtifactManifest was built empty" in warning for warning in evidence_bundle.warnings)


def test_minimal_product_workflow_keeps_full_output_boundary_out_of_runner() -> None:
    runtime_runner, runtime_result, evidence_bundle = _build_minimal_product_evidence()

    assert isinstance(runtime_runner, StandardRuntimeRunner)
    assert runtime_result.workflow_result is not None
    workflow_result = runtime_result.workflow_result
    boundary_surfaces = [
        workflow_result.metadata,
        runtime_result.events[0].payload,
        runtime_result.events[0].metadata,
        runtime_result.artifact_deltas[0].metadata,
        evidence_bundle.event_trace.events[0]["payload"],
        evidence_bundle.event_trace.events[0]["metadata"],
        evidence_bundle.artifact_manifest.artifacts[0]["metadata"],
        evidence_bundle.run_record.metadata["workflow_metadata"],
        evidence_bundle.metadata["workflow_metadata"],
    ]

    assert workflow_result.metadata["workflow_kind"] == MINIMAL_PRODUCT_WORKFLOW_KIND
    assert workflow_result.metadata["product_output_kind"] == MINIMAL_PRODUCT_OUTPUT_KIND
    assert evidence_bundle.event_trace.metadata["source"] == "runtime_result.events"
    assert evidence_bundle.artifact_manifest.metadata["source"] == "runtime_result.artifact_deltas"
    assert (
        evidence_bundle.metadata["evidence_contract"]["input_type"]
        == "schemas.runtime.RuntimeResult"
    )
    assert evidence_bundle.artifact_manifest.artifacts[0]["path"] is None
    assert not any(
        _has_forbidden_key(surface, FULL_PRODUCT_OUTPUT_KEYS) for surface in boundary_surfaces
    )
