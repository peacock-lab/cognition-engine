from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from cognition_agent import build_agent_governance_evidence_summary_view
from contract_core.runtime import (
    AdkServiceFactsProvider,
    AdkServiceFactsSummaryInput,
    ArtifactDelta,
    ArtifactRef,
    DeltaOperation,
    InvocationRef,
    RecordedRunEvidenceInput,
    RuntimeEvent,
    RuntimeEventType,
    RuntimeProductizationGateConfigView,
    RuntimeResult,
    RuntimeStatus,
    WorkflowRef,
    WorkflowResult,
)
from observability_hub import (
    create_adk_workflow_runner_adk_service_facts_provider,
    create_adk_workflow_runner_recorded_run_evidence_provider,
)
import runtime_container.governance_summary_pipeline as governance_summary_pipeline
from runtime_container.governance_summary_pipeline import (
    build_runtime_container_governance_summary_payload,
    build_runtime_container_governance_summary_payload_from_recorded_run,
    evaluate_runtime_productization_gating,
    write_runtime_container_governance_summary_payload,
    write_runtime_container_governance_summary_payload_from_recorded_run,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_CONTAINER_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "runtime_container" / "src" / "runtime_container"
)


def test_productization_gating_defaults_to_no_live_no_adk_run_no_ollama() -> None:
    evaluation = evaluate_runtime_productization_gating()

    assert evaluation.runtime_execution_ready is False
    assert evaluation.adk_run_allowed is False
    assert evaluation.live_llm_allowed is False
    assert evaluation.ollama_allowed is False
    assert evaluation.default_no_live is True
    assert evaluation.default_no_adk_run is True
    assert evaluation.default_no_ollama is True
    assert evaluation.execution_performed is False
    assert evaluation.adk_run_performed is False
    assert evaluation.live_llm_call_performed is False
    assert evaluation.ollama_call_performed is False


def test_productization_gating_models_explicit_conditions_before_readiness() -> None:
    evaluation = evaluate_runtime_productization_gating(
        RuntimeProductizationGateConfigView(
            gate_id="gate-adk-live-1",
            request_adk_run=True,
            request_live_llm=True,
            allow_adk_run=True,
            allow_live_llm=True,
            sanitized_evidence_ref="evidence://sanitized/adk-run-1",
            governance_summary_output_ref="artifact://governance-summary/adk-run-1",
            audit_ref="audit://runtime-productization/adk-run-1",
            reason="controlled productization rehearsal",
        )
    )

    assert evaluation.runtime_execution_ready is False
    assert evaluation.adk_run_allowed is False
    assert evaluation.live_llm_allowed is False
    assert evaluation.missing_conditions == ["explicit_operator_approval"]

    ready = evaluate_runtime_productization_gating(
        RuntimeProductizationGateConfigView(
            gate_id="gate-adk-live-2",
            request_adk_run=True,
            request_live_llm=True,
            allow_adk_run=True,
            allow_live_llm=True,
            explicit_operator_approval=True,
            sanitized_evidence_ref="evidence://sanitized/adk-run-2",
            governance_summary_output_ref="artifact://governance-summary/adk-run-2",
            audit_ref="audit://runtime-productization/adk-run-2",
            reason="controlled productization rehearsal",
        )
    )

    assert ready.runtime_execution_ready is True
    assert ready.adk_run_allowed is True
    assert ready.live_llm_allowed is True
    assert ready.execution_performed is False
    assert ready.adk_run_performed is False
    assert ready.live_llm_call_performed is False


def test_builds_cli_consumable_governance_summary_payload_from_adk_service_facts() -> None:
    payload = build_runtime_container_governance_summary_payload(
        adk_service_facts=_adk_service_facts(),
        gating=RuntimeProductizationGateConfigView(gate_id="gate-default-145"),
        evidence_id="runtime-container-governance-summary-145",
    )

    assert payload["evidence_id"] == "runtime-container-governance-summary-145"
    assert payload["sanitized"] is True
    assert payload["productization_gating"]["execution_performed"] is False
    assert payload["productization_gating"]["adk_run_performed"] is False
    assert payload["productization_gating"]["live_llm_call_performed"] is False
    assert payload["productization_gating"]["ollama_call_performed"] is False
    assert payload["summary_generation"]["does_not_call_adk_runner"] is True
    assert payload["summary_generation"]["does_not_call_live_llm"] is True

    view = build_agent_governance_evidence_summary_view(
        candidate_id=f"agent-governance-summary-cli-view:{payload['evidence_id']}",
        governance_evidence_metadata=payload,
    )

    assert view.lifecycle_summary_id == "adk-lifecycle-summary-145"
    assert view.run_config_service_bundle_summary_id == (
        "adk-run-config-service-bundle-summary-145"
    )
    assert view.workflow_name == "runtime-productization-workflow"
    assert view.artifact_count == 1
    assert view.event_count == 2
    assert view.run_config_no_live_mode is True
    assert view.run_config_call_attempted is False
    assert view.runtime_container_call_enabled is False
    assert view.llm_call_enabled is False


def test_builds_governance_summary_payload_from_recorded_evidence_contract() -> None:
    payload = build_runtime_container_governance_summary_payload_from_recorded_run(
        recorded_run=RecordedRunEvidenceInput(
            recorded_run_id="recorded-run-146",
            evidence_bundle_ref="evidence-bundle://recorded-run-146",
            adk_workflow_runner_evidence_ref=(
                "adk-workflow-runner-evidence://recorded-run-146"
            ),
            evidence_bundle_observed=True,
            adk_workflow_runner_evidence_observed=True,
            adk_service_facts=_adk_service_facts(),
        ),
        gating=RuntimeProductizationGateConfigView(
            gate_id="gate-recorded-146",
            sanitized_evidence_ref="evidence://recorded-run-146",
            governance_summary_output_ref="artifact://governance-summary-146",
            audit_ref="audit://recorded-run-146",
        ),
        evidence_id="runtime-container-governance-summary-146",
    )

    assert payload["evidence_id"] == "runtime-container-governance-summary-146"
    assert payload["recorded_run"]["recorded_run_id"] == "recorded-run-146"
    assert payload["recorded_run"]["evidence_bundle_ref"] == (
        "evidence-bundle://recorded-run-146"
    )
    assert payload["recorded_run"]["has_evidence_bundle"] is True
    assert payload["recorded_run"]["has_adk_workflow_runner_evidence"] is True
    assert payload["recorded_run"]["does_not_execute_recorded_run"] is True
    assert payload["summary_generation"]["accepts_observability_evidence"] is True
    assert payload["summary_generation"]["input_kind"] == (
        "schemas.runtime.RecordedRunEvidenceInput"
    )
    assert payload["productization_gating"]["execution_performed"] is False
    assert payload["productization_gating"]["adk_run_performed"] is False
    assert payload["productization_gating"]["live_llm_call_performed"] is False


def test_recorded_runtime_result_uses_recorded_run_evidence_provider_contract() -> None:
    class FixtureRecordedRunEvidenceProvider:
        def build_recorded_run_evidence(
            self, runtime_result: RuntimeResult
        ) -> RecordedRunEvidenceInput:
            assert runtime_result.runtime_id == "runtime-recorded-146"
            return RecordedRunEvidenceInput(
                recorded_run_id=runtime_result.runtime_id,
                adk_workflow_runner_evidence_ref=(
                    "adk-workflow-runner-evidence://recorded-run-146"
                ),
                adk_workflow_runner_evidence_observed=True,
                adk_service_facts=_adk_service_facts(),
            )

    payload = build_runtime_container_governance_summary_payload_from_recorded_run(
        runtime_result=RuntimeResult(
            runtime_id="runtime-recorded-146",
            status=RuntimeStatus.SUCCESS,
            invocation_ref=InvocationRef(invocation_id="inv-recorded-146"),
        ),
        recorded_run_evidence_provider=FixtureRecordedRunEvidenceProvider(),
    )

    assert payload["summary_generation"]["input_kind"] == (
        "schemas.runtime.RecordedRunEvidenceInput"
    )
    assert payload["summary_generation"][
        "uses_recorded_run_evidence_provider_contract"
    ] is True
    assert payload["lifecycle_summary"]["summary_id"] == "adk-lifecycle-summary-145"


def test_runtime_container_consumes_observability_hub_recorded_run_provider() -> None:
    provider = create_adk_workflow_runner_recorded_run_evidence_provider(
        assembly_metadata=_observability_assembly_metadata(),
        evidence_bundle_ref="evidence-bundle://runtime-container-148",
    )

    payload = build_runtime_container_governance_summary_payload_from_recorded_run(
        runtime_result=_observability_runtime_result(),
        recorded_run_evidence_provider=provider,
    )

    assert payload["recorded_run"]["recorded_run_id"] == (
        "runtime-observability-provider-148"
    )
    assert payload["recorded_run"]["evidence_bundle_ref"] == (
        "evidence-bundle://runtime-container-148"
    )
    assert payload["recorded_run"]["has_evidence_bundle"] is True
    assert payload["recorded_run"]["has_adk_workflow_runner_evidence"] is True
    assert payload["summary_generation"][
        "uses_recorded_run_evidence_provider_contract"
    ] is True
    assert payload["summary_generation"]["input_kind"] == (
        "observability_hub.adk_workflow_runner_evidence."
        "RecordedRunEvidenceInput"
    )
    assert payload["lifecycle_summary"]["events"]["event_count"] == 1
    assert payload["run_config_service_bundle_summary"]["run_config"][
        "live_call_enabled"
    ] is False


def test_runtime_container_consumes_adk_service_facts_provider_output() -> None:
    provider: AdkServiceFactsProvider = (
        create_adk_workflow_runner_adk_service_facts_provider(
            assembly_metadata=_observability_assembly_metadata(),
        )
    )
    service_facts = provider.build_adk_service_facts(_observability_runtime_result())

    payload = build_runtime_container_governance_summary_payload(
        adk_service_facts=service_facts,
        evidence_id="runtime-container-governance-summary-151",
    )

    assert payload["evidence_id"] == "runtime-container-governance-summary-151"
    assert payload["summary_generation"]["input_kind"] == (
        "observability_hub.adk_workflow_runner_evidence."
        "AdkServiceFactsSummaryInput"
    )
    assert payload["summary_generation"]["does_not_call_adk_runner"] is True
    assert payload["lifecycle_summary"]["workflow_name"] == (
        "observability-provider-workflow"
    )
    assert payload["lifecycle_summary"]["events"]["event_count"] == 1
    assert payload["run_config_service_bundle_summary"]["run_config"][
        "live_call_enabled"
    ] is False


def test_writes_governance_summary_payload_json_for_cli_consumption(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "governance-summary-payload.json"
    payload = build_runtime_container_governance_summary_payload_from_recorded_run(
        recorded_run=RecordedRunEvidenceInput(
            recorded_run_id="recorded-run-146",
            adk_workflow_runner_evidence_ref=(
                "adk-workflow-runner-evidence://recorded-run-146"
            ),
            adk_workflow_runner_evidence_observed=True,
            adk_service_facts=_adk_service_facts(),
        ),
        evidence_id="runtime-container-governance-summary-146",
    )

    written_path = write_runtime_container_governance_summary_payload(
        payload=payload,
        output_path=output_path,
    )
    persisted = json.loads(written_path.read_text(encoding="utf-8"))

    assert written_path == output_path
    assert persisted["evidence_id"] == "runtime-container-governance-summary-146"
    assert persisted["recorded_run"]["does_not_execute_recorded_run"] is True
    view = build_agent_governance_evidence_summary_view(
        candidate_id=f"agent-governance-summary-cli-view:{persisted['evidence_id']}",
        governance_evidence_metadata=persisted,
    )
    assert view.workflow_name == "runtime-productization-workflow"
    assert view.runtime_container_call_enabled is False
    assert view.llm_call_enabled is False


def test_writes_governance_summary_payload_from_recorded_run(tmp_path: Path) -> None:
    output_path = tmp_path / "recorded-run-governance-summary.json"

    written_path = write_runtime_container_governance_summary_payload_from_recorded_run(
        recorded_run=RecordedRunEvidenceInput(
            recorded_run_id="recorded-run-146",
            adk_workflow_runner_evidence_ref=(
                "adk-workflow-runner-evidence://recorded-run-146"
            ),
            adk_workflow_runner_evidence_observed=True,
            adk_service_facts=_adk_service_facts(),
        ),
        output_path=output_path,
    )

    assert written_path == output_path
    assert json.loads(written_path.read_text(encoding="utf-8"))["sanitized"] is True
    with pytest.raises(FileExistsError):
        write_runtime_container_governance_summary_payload_from_recorded_run(
            recorded_run=RecordedRunEvidenceInput(
                recorded_run_id="recorded-run-146",
                adk_workflow_runner_evidence_ref=(
                    "adk-workflow-runner-evidence://recorded-run-146"
                ),
                adk_workflow_runner_evidence_observed=True,
                adk_service_facts=_adk_service_facts(),
            ),
            output_path=output_path,
        )


def test_governance_summary_pipeline_rejects_missing_public_summaries() -> None:
    with pytest.raises(ValueError, match="lifecycle_summary is required"):
        build_runtime_container_governance_summary_payload(
            adk_service_facts={
                "run_config_service_bundle_summary": _adk_service_facts().model_dump(
                    mode="python"
                )["run_config_service_bundle_summary"],
            }
        )

    with pytest.raises(ValueError, match="RecordedRunEvidenceInput contract"):
        build_runtime_container_governance_summary_payload_from_recorded_run(
            recorded_run=None
        )


def test_runtime_container_governance_summary_pipeline_has_no_execution_dependencies() -> None:
    source = (RUNTIME_CONTAINER_SOURCE_ROOT / "governance_summary_pipeline.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:adk_adapter|google\.adk|litellm|cognition_governance|"
        r"observability_hub|cognition_agent)\b",
        re.MULTILINE,
    )
    forbidden_calls = re.compile(
        r"\b(?:completion|acompletion|service\.invoke|run_async|runner\.run)\s*\("
    )

    assert runtime_container_public_module_is_exported()
    assert forbidden_imports.search(source) is None
    assert forbidden_calls.search(source) is None
    assert "live_enabled=True" not in source
    assert "ToolExecutor" not in source
    assert "AgentRuntime" not in source
    assert "Chat" not in source
    assert "Gateway" not in source


def runtime_container_public_module_is_exported() -> bool:
    return governance_summary_pipeline.build_runtime_container_governance_summary_payload is (
        build_runtime_container_governance_summary_payload
    )


def _adk_service_facts() -> AdkServiceFactsSummaryInput:
    return AdkServiceFactsSummaryInput.model_validate(
        {
        "evidence_id": "adk-service-facts-145",
        "lifecycle_summary": {
            "summary_id": "adk-lifecycle-summary-145",
            "runtime_id": "runtime-productization-145",
            "workflow_id": "workflow-productization-145",
            "workflow_name": "runtime-productization-workflow",
            "status": "success",
            "artifacts": [
                {
                    "artifact_ref": {
                        "artifact_id": "artifact-productization-145",
                        "name": "governance-summary.json",
                    },
                    "operation": "set",
                    "service_type_name": "InMemoryArtifactService",
                    "metadata": {"sanitized": True},
                }
            ],
            "session": {
                "session_id": "session-productization-145",
                "event_count": 2,
                "service_type_name": "InMemorySessionService",
                "metadata": {"sanitized": True},
            },
            "events": {
                "event_count": 2,
                "event_types": ["workflow_started", "workflow_completed"],
                "metadata": {"sanitized": True},
            },
            "metadata": {
                "source_evidence_id": "adk-service-facts-145",
                "sanitized": True,
                "does_not_include_adk_native_objects": True,
            },
        },
        "run_config_service_bundle_summary": {
            "summary_id": "adk-run-config-service-bundle-summary-145",
            "runtime_id": "runtime-productization-145",
            "workflow_id": "workflow-productization-145",
            "workflow_name": "runtime-productization-workflow",
            "status": "success",
            "run_config": {
                "run_config_source": "assembly_options + workflow_result.metadata",
                "mapped_fields": ["max_llm_calls", "custom_metadata"],
                "unmapped_fields": ["tool_thread_pool_config"],
                "custom_metadata_keys": ["source"],
                "max_llm_calls": 4,
                "streaming_mode": "none",
                "adk_run_config_type": "RunConfig",
                "live_call_enabled": False,
                "no_live_mode": True,
                "call_attempted": False,
                "metadata": {"sanitized": True},
            },
            "service_bundle": {
                "service_bundle_source": "in_memory",
                "artifact_service_present": True,
                "session_service_present": True,
                "artifact_service_type_name": "InMemoryArtifactService",
                "session_service_type_name": "InMemorySessionService",
                "capability_flags": [
                    "artifact_service_present",
                    "session_service_present",
                ],
                "metadata": {"sanitized": True},
            },
            "metadata": {
                "source_evidence_id": "adk-service-facts-145",
                "sanitized": True,
                "does_not_enable_live_call": True,
            },
        },
        }
    )


def _observability_runtime_result() -> RuntimeResult:
    invocation_ref = InvocationRef(
        invocation_id="inv-observability-provider-148",
        runtime_id="runtime-observability-provider-148",
        workflow_id="workflow-observability-provider-148",
        metadata={"session_id": "session-observability-provider-148"},
    )
    workflow_ref = WorkflowRef(
        workflow_id="workflow-observability-provider-148",
        name="observability-provider-workflow",
    )
    event = RuntimeEvent(
        event_id="event-observability-provider-148",
        event_type=RuntimeEventType.NODE_COMPLETED,
        invocation_ref=invocation_ref,
        workflow_ref=workflow_ref,
        payload={"output": {"ok": True}},
        metadata={
            "node_path": "workflow@1/provider_node@1",
            "author": "provider_node",
            "requested_invocation_id": "inv-observability-provider-148",
            "adk_invocation_id": "adk-observability-provider-148",
            "session_id": "session-observability-provider-148",
            "app_name": "observability-provider-app",
            "user_id": "observability-provider-user",
        },
    )
    artifact_delta = ArtifactDelta(
        delta_id="artifact-delta-observability-provider-148",
        invocation_ref=invocation_ref,
        artifact_ref=ArtifactRef(
            artifact_id="provider-artifact.json",
            name="provider-artifact.json",
            version="0",
        ),
        operation=DeltaOperation.SET,
        metadata={"raw_artifact_delta": 0, "sanitized": True},
    )
    workflow_result = WorkflowResult(
        workflow_ref=workflow_ref,
        status=RuntimeStatus.SUCCESS,
        invocation_ref=invocation_ref,
        events=[event],
        artifact_deltas=[artifact_delta],
        metadata={
            "session_id": "session-observability-provider-148",
            "app_name": "observability-provider-app",
            "user_id": "observability-provider-user",
            "run_config": {
                "max_llm_calls": 3,
                "streaming_mode": "none",
                "adk_run_config_type": "RunConfig",
                "custom_metadata_keys": ["source"],
            },
        },
    )
    return RuntimeResult(
        runtime_id="runtime-observability-provider-148",
        status=RuntimeStatus.SUCCESS,
        invocation_ref=invocation_ref,
        workflow_result=workflow_result,
        events=[event],
        artifact_deltas=[artifact_delta],
        metadata={"runtime_name": "observability-provider-runtime"},
    )


def _observability_assembly_metadata() -> dict[str, object]:
    return {
        "workflow_name": "observability-provider-workflow",
        "app_name": "observability-provider-app",
        "user_id": "observability-provider-user",
        "service_bundle": {
            "source": "in_memory",
            "artifact_service": {
                "adk_service_type": "InMemoryArtifactService",
            },
            "session_service": {
                "adk_service_type": "InMemorySessionService",
            },
        },
        "assembly_options": {
            "service_bundle_options": {"source": "in_memory"},
            "run_config_options": {
                "mapped_fields": ["max_llm_calls", "custom_metadata"],
                "unmapped_fields": ["tool_thread_pool_config"],
            },
        },
    }
