from __future__ import annotations

from pathlib import Path
from typing import Any

from adk_adapter import AdkRunConfigOptions, AdkRunnerServiceBundleOptions
from composition.adk_workflow_runner_assembly import (
    AdkWorkflowRunnerAssemblyOptions,
    build_adk_workflow_runner_runtime,
)
from composition.runtime import RuntimeCompositionOptions
from contract_core.runtime import (
    AdkServiceFactsProvider,
    AdkServiceFactsSummaryInput,
    RecordedRunEvidenceInput,
    RecordedRunEvidenceProvider,
)
from observability_hub import (
    AdkWorkflowRunnerAdkServiceFactsProvider,
    AdkWorkflowRunnerRecordedRunEvidenceProvider,
    AdkWorkflowRunnerEvidence,
    build_adk_service_facts_from_adk_workflow_runner,
    build_evidence_bundle,
    build_evidence_bundle_ref,
    build_adk_lifecycle_facts_summary,
    build_adk_run_config_service_bundle_summary,
    build_adk_workflow_runner_evidence,
    build_recorded_run_evidence_from_adk_workflow_runner,
    create_adk_workflow_runner_adk_service_facts_provider,
    create_adk_workflow_runner_recorded_run_evidence_provider,
)
from schemas.runtime import AdkLifecycleFactsSummary, AdkRunConfigServiceBundleSummary
from schemas.runtime import (
    ArtifactDelta,
    ArtifactRef,
    DeltaOperation,
    InvocationRef,
    RuntimeEvent,
    RuntimeEventType,
    RuntimeInput,
    RuntimeResult,
    RuntimeStatus,
    StateDelta,
    WorkflowRef,
    WorkflowResult,
)


def test_build_adk_workflow_runner_evidence_from_runtime_assembly_execution() -> None:
    from google.adk.agents.context import Context
    from google.adk.events import Event
    from google.adk.events.event import NodeInfo
    from google.adk.workflow import START, BaseNode, Workflow
    from google.genai import types

    class EvidenceArtifactNode(BaseNode):
        async def _run_impl(self, *, ctx: Context, node_input: Any):
            version = await ctx.save_artifact(
                "evidence-output.txt",
                types.Part(text="evidence artifact payload"),
                custom_metadata={"source": "observability-evidence-test"},
            )
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                node_info=NodeInfo(path=ctx.node_path),
                output={
                    "version": version,
                    "keys": await ctx.list_artifacts(),
                    "max_llm_calls": ctx.run_config.max_llm_calls,
                    "run_config_source": ctx.run_config.custom_metadata["source"],
                },
            )

    assembly_options = AdkWorkflowRunnerAssemblyOptions(
        app_name="test_observability_adk2",
        user_id="observability-user",
        workflow_name="observability-evidence-workflow",
        service_bundle_options=AdkRunnerServiceBundleOptions(source="in_memory"),
        run_config_options=AdkRunConfigOptions(
            max_llm_calls=17,
            custom_metadata={"source": "observability-run-config"},
            response_modalities=("TEXT",),
            streaming_mode="none",
        ),
        metadata={"test_case": "adk-workflow-runner-evidence"},
    )
    workflow = Workflow(
        name="observability_adk2_workflow",
        edges=[(START, EvidenceArtifactNode(name="evidence_node"))],
    )
    assembly = build_adk_workflow_runner_runtime(
        options=RuntimeCompositionOptions(
            config_root=Path("config"),
            environment="local",
        ),
        workflow=workflow,
        assembly_options=assembly_options,
    )

    runtime_result = assembly.runtime_runner.run(
        RuntimeInput(
            runtime_id="runtime-observability-adk2-001",
            workflow_ref=WorkflowRef(workflow_id="workflow-observability-adk2-001"),
            invocation_ref=InvocationRef(invocation_id="inv-observability-adk2-001"),
            input_payload={"message": "hello"},
        )
    )
    evidence = build_adk_workflow_runner_evidence(
        runtime_result,
        assembly_metadata=assembly.metadata,
    )

    assert isinstance(evidence, AdkWorkflowRunnerEvidence)
    assert runtime_result.status == RuntimeStatus.SUCCESS
    assert evidence.runtime_kind == "adk2_workflow_runner"
    assert evidence.runtime_id == "runtime-observability-adk2-001"
    assert evidence.workflow_id == "workflow-observability-adk2-001"
    assert evidence.workflow_name == "observability-evidence-workflow"
    assert evidence.app_name == "test_observability_adk2"
    assert evidence.user_id == "observability-user"

    assert evidence.run_config["mapped_fields"] == [
        "max_llm_calls",
        "custom_metadata",
        "response_modalities",
        "streaming_mode",
    ]
    assert "tool_thread_pool_config" in evidence.run_config["unmapped_fields"]
    assert evidence.run_config["max_llm_calls"] == 17
    assert evidence.run_config["custom_metadata_keys"] == ["source"]
    assert evidence.run_config["adk_run_config_version"] == "2.1.0"
    assert "speech_config" in evidence.run_config["official_fields"]
    assert evidence.run_config["field_policies"]["tool_thread_pool_config"][
        "status"
    ] == "deferred_tool_execution"
    assert "save_live_audio" in evidence.run_config["deprecated_fields"]
    assert evidence.run_config["legacy_input_fields"] == []
    assert evidence.run_config["translated_fields"] == []
    assert evidence.run_config["declared_fields"] == [
        "max_llm_calls",
        "custom_metadata",
        "response_modalities",
        "streaming_mode",
    ]

    assert evidence.service_bundle["artifact_service"]["adk_service_type"] == (
        "InMemoryArtifactService"
    )
    assert evidence.service_bundle["session_service"]["adk_service_type"] == (
        "InMemorySessionService"
    )
    assert evidence.assembly_options["service_bundle_options"]["source"] == "in_memory"

    assert evidence.artifact_summary["artifact_count"] == 1
    assert evidence.artifact_summary["artifact_ids"] == ["evidence-output.txt"]
    assert evidence.artifact_summary["versions"] == [0]
    assert evidence.session_summary["session_id"]
    assert evidence.session_summary["event_count"] >= 2
    assert evidence.session_summary["adk_invocation_id"]
    assert evidence.event_summary["event_count"] >= 2
    assert evidence.event_summary["event_ids"]
    assert evidence.state_delta_summary["state_delta_entity_mode"] in {
        "event_payload_summary_only",
        "state_delta_contract_summary",
    }
    assert "observability_adk2_workflow@1/evidence_node@1" in (
        evidence.event_summary["node_paths"]
    )
    assert evidence.graph_summary["source"] == (
        "observability_hub.adk_workflow_runner_evidence.graph_summary"
    )
    assert evidence.graph_summary["workflow_id"] == "workflow-observability-adk2-001"
    assert evidence.graph_summary["workflow_name"] == "observability-evidence-workflow"
    assert "observability_adk2_workflow@1/evidence_node@1" in (
        evidence.graph_summary["node_paths"]
    )
    assert evidence.graph_summary["node_path_count"] == len(
        evidence.graph_summary["node_paths"]
    )
    assert evidence.graph_summary["branch_ids"] == evidence.event_summary["branch_ids"]
    assert evidence.graph_summary["candidate_only"] is True
    assert evidence.graph_summary["summary_only"] is True
    assert evidence.graph_summary["refs_only"] is True
    assert evidence.graph_summary["raw_adk_object_included"] is False
    assert evidence.graph_summary["raw_graph_object_included"] is False
    assert evidence.trace_summary["source"] == (
        "observability_hub.adk_workflow_runner_evidence.trace_summary"
    )
    assert evidence.trace_summary["event_count"] == evidence.event_summary["event_count"]
    assert evidence.trace_summary["event_ids"] == evidence.event_summary["event_ids"]
    assert evidence.trace_summary["event_types"] == evidence.event_summary["event_types"]
    assert evidence.trace_summary["invocation_ids"] == (
        evidence.event_summary["invocation_ids"]
    )
    assert evidence.trace_summary["state_delta_refs"] == (
        evidence.event_summary["state_delta_refs"]
    )
    assert evidence.trace_summary["artifact_delta_refs"] == (
        evidence.event_summary["artifact_delta_refs"]
    )
    assert evidence.trace_summary["candidate_only"] is True
    assert evidence.trace_summary["summary_only"] is True
    assert evidence.trace_summary["refs_only"] is True
    assert evidence.trace_summary["raw_event_included"] is False
    assert evidence.trace_summary["raw_payload_included"] is False
    assert evidence.lifecycle_summary["candidate_only"] is True
    assert evidence.lifecycle_summary["formal_decision_enabled"] is False
    assert evidence.lifecycle_summary["artifacts"][0]["artifact_ref"]["artifact_id"] == (
        "evidence-output.txt"
    )
    assert evidence.lifecycle_summary["session"]["service_type_name"] == (
        "InMemorySessionService"
    )
    assert evidence.lifecycle_summary["events"]["event_count"] >= 2
    assert evidence.lifecycle_summary["context_state"]["custom_metadata_keys"] == [
        "source"
    ]
    assert (
        evidence.lifecycle_summary["context_state"]["raw_state_values_included"]
        is False
    )
    assert evidence.run_config_service_bundle_summary["candidate_only"] is True
    assert (
        evidence.run_config_service_bundle_summary["run_config"]["mapped_fields"]
        == evidence.run_config["mapped_fields"]
    )
    assert (
        evidence.run_config_service_bundle_summary["run_config"][
            "adk_run_config_version"
        ]
        == "2.1.0"
    )
    assert (
        evidence.run_config_service_bundle_summary["service_bundle"][
            "persistence_stage"
        ]
        == "runtime_fact_only"
    )
    assert (
        evidence.run_config_service_bundle_summary["run_config"]["live_call_enabled"]
        is False
    )
    assert (
        evidence.run_config_service_bundle_summary["service_bundle"][
            "service_bundle_source"
        ]
        == "in_memory"
    )
    assert evidence.observability_candidate == "observability_hub.adk_workflow_runner_intake"
    assert evidence.contract_candidate_notes

    evidence_dump = evidence.model_dump(mode="python")
    assert "cognition_governance" not in repr(evidence_dump)
    assert "Runner(" not in repr(evidence_dump)
    assert "RunConfig(" not in repr(evidence_dump)
    assert "InMemoryArtifactService(" not in repr(evidence_dump)
    assert "raw_event_body" not in repr(evidence.trace_summary)
    assert "raw_payload_body" not in repr(evidence.trace_summary)


def test_build_adk_workflow_runner_evidence_allows_missing_assembly_metadata() -> None:
    runtime_result = {
        "runtime_id": "runtime-missing-assembly",
        "status": "success",
        "invocation_ref": {"invocation_id": "inv-missing-assembly"},
        "metadata": {},
    }

    evidence = build_adk_workflow_runner_evidence(runtime_result)

    assert evidence.runtime_id == "runtime-missing-assembly"
    assert evidence.assembly_options == {}
    assert evidence.service_bundle == {}
    assert evidence.graph_summary["node_paths"] == []
    assert evidence.graph_summary["node_path_count"] == 0
    assert evidence.graph_summary["raw_adk_object_included"] is False
    assert evidence.trace_summary["event_count"] == 0
    assert evidence.trace_summary["event_ids"] == []
    assert evidence.trace_summary["raw_event_included"] is False
    assert any("assembly_metadata" in warning for warning in evidence.warnings)


def test_recorded_run_evidence_provider_outputs_contract_input() -> None:
    provider: RecordedRunEvidenceProvider = (
        create_adk_workflow_runner_recorded_run_evidence_provider(
            assembly_metadata=_assembly_metadata(),
            evidence_bundle_ref="evidence-bundle://observability-148",
        )
    )

    recorded = provider.build_recorded_run_evidence(_runtime_result())

    assert isinstance(recorded, RecordedRunEvidenceInput)
    assert recorded.recorded_run_id == "runtime-observability-provider-148"
    assert recorded.evidence_bundle_ref == "evidence-bundle://observability-148"
    assert recorded.evidence_bundle_observed is True
    assert recorded.adk_workflow_runner_evidence_observed is True
    assert recorded.does_not_execute_recorded_run is True
    assert recorded.adk_service_facts.sanitized is True
    assert recorded.adk_service_facts.lifecycle_summary.summary_id.startswith(
        "adk-lifecycle-summary-adk-workflow-runner-evidence-"
    )
    assert recorded.adk_service_facts.lifecycle_summary.events.event_count == 1
    assert (
        recorded.adk_service_facts.run_config_service_bundle_summary.run_config
        .live_call_enabled
        is False
    )
    assert "google.adk" not in repr(recorded.model_dump(mode="python"))
    assert "adk_adapter" not in repr(recorded.model_dump(mode="python"))


def test_adk_service_facts_provider_outputs_contract_input() -> None:
    provider: AdkServiceFactsProvider = (
        create_adk_workflow_runner_adk_service_facts_provider(
            assembly_metadata=_assembly_metadata(),
        )
    )

    service_facts = provider.build_adk_service_facts(_runtime_result())

    assert isinstance(service_facts, AdkServiceFactsSummaryInput)
    assert service_facts.sanitized is True
    assert service_facts.source == (
        "observability_hub.adk_workflow_runner_evidence."
        "AdkServiceFactsSummaryInput"
    )
    assert service_facts.lifecycle_summary.workflow_name == (
        "observability-provider-workflow"
    )
    assert service_facts.lifecycle_summary.events.event_count == 1
    assert (
        service_facts.run_config_service_bundle_summary.run_config.live_call_enabled
        is False
    )
    assert service_facts.metadata["does_not_call_live_llm"] is True
    assert service_facts.metadata["does_not_call_ollama"] is True
    dumped = service_facts.model_dump(mode="python")
    assert "google.adk" not in repr(dumped)
    assert "adk_adapter" not in repr(dumped)


def test_build_adk_service_facts_from_adk_workflow_runner_function() -> None:
    service_facts = build_adk_service_facts_from_adk_workflow_runner(
        _runtime_result(),
        assembly_metadata=_assembly_metadata(),
    )

    assert isinstance(service_facts, AdkServiceFactsSummaryInput)
    assert service_facts.evidence_id is not None
    assert service_facts.lifecycle_summary.summary_id.startswith(
        "adk-lifecycle-summary-adk-workflow-runner-evidence-"
    )
    assert (
        service_facts.run_config_service_bundle_summary.service_bundle
        .service_bundle_source
        == "in_memory"
    )


def test_evidence_bundle_ref_can_enter_recorded_run_without_bundle_content() -> None:
    runtime_result = _runtime_result()
    evidence_bundle = build_evidence_bundle(runtime_result)
    evidence_bundle_ref = build_evidence_bundle_ref(evidence_bundle)

    recorded = build_recorded_run_evidence_from_adk_workflow_runner(
        runtime_result,
        assembly_metadata=_assembly_metadata(),
        evidence_bundle=evidence_bundle,
    )

    assert evidence_bundle_ref == f"evidence-bundle://{evidence_bundle.bundle_id}"
    assert build_evidence_bundle_ref(evidence_bundle.bundle_id) == evidence_bundle_ref
    assert build_evidence_bundle_ref(evidence_bundle_ref) == evidence_bundle_ref
    assert recorded.evidence_bundle_ref == evidence_bundle_ref
    assert recorded.evidence_bundle_observed is True
    assert recorded.metadata["evidence_bundle_ref_semantics"] == (
        "stable_reference_identifier_only"
    )
    assert recorded.metadata["does_not_include_evidence_bundle_content"] is True

    recorded_dump = recorded.model_dump(mode="python")
    recorded_repr = repr(recorded_dump)
    assert "run_record" not in recorded_repr
    assert "event_trace" not in recorded_repr
    assert "artifact_manifest" not in recorded_repr


def test_build_recorded_run_evidence_from_adk_workflow_runner_function() -> None:
    recorded = build_recorded_run_evidence_from_adk_workflow_runner(
        _runtime_result(),
        assembly_metadata=_assembly_metadata(),
        recorded_run_id="recorded-run-observability-148",
    )

    assert isinstance(recorded, RecordedRunEvidenceInput)
    assert recorded.recorded_run_id == "recorded-run-observability-148"
    assert recorded.source == (
        "observability_hub.adk_workflow_runner_evidence."
        "RecordedRunEvidenceInput"
    )
    assert recorded.adk_workflow_runner_evidence_ref is not None


def test_recorded_run_evidence_provider_class_is_public() -> None:
    provider = AdkWorkflowRunnerRecordedRunEvidenceProvider(
        assembly_metadata=_assembly_metadata()
    )

    assert isinstance(
        provider.build_recorded_run_evidence(_runtime_result()),
        RecordedRunEvidenceInput,
    )


def test_adk_service_facts_provider_class_is_public() -> None:
    provider = AdkWorkflowRunnerAdkServiceFactsProvider(
        assembly_metadata=_assembly_metadata()
    )

    assert isinstance(
        provider.build_adk_service_facts(_runtime_result()),
        AdkServiceFactsSummaryInput,
    )


def test_build_adk_lifecycle_facts_summary_from_evidence_mapping() -> None:
    summary = build_adk_lifecycle_facts_summary(
        {
            "evidence_id": "evidence-lifecycle-001",
            "runtime_id": "runtime-lifecycle-001",
            "workflow_id": "workflow-lifecycle-001",
            "workflow_name": "lifecycle-workflow",
            "status": "success",
            "service_bundle": {
                "artifact_service": {"adk_service_type": "InMemoryArtifactService"},
                "session_service": {"adk_service_type": "InMemorySessionService"},
            },
            "artifact_summary": {
                "artifact_count": 1,
                "artifact_ids": ["artifact-output.txt"],
                "artifact_names": ["artifact-output.txt"],
                "versions": [0],
                "operations": ["set"],
                "metadata_keys": ["raw_artifact_delta"],
            },
            "session_summary": {
                "session_id": "session-lifecycle-001",
                "app_name": "lifecycle-app",
                "user_id": "lifecycle-user",
                "event_count": 2,
                "requested_invocation_id": "inv-lifecycle-001",
            },
            "event_summary": {
                "event_count": 2,
                "event_ids": ["event-lifecycle-001"],
                "event_types": ["node_completed"],
                "authors": ["node"],
                "branch_ids": ["main"],
                "node_paths": ["workflow@1/node@1"],
                "state_delta_refs": ["state-delta-lifecycle-001"],
                "artifact_delta_refs": ["artifact-output.txt"],
                "invocation_ids": ["adk-lifecycle-001"],
                "state_delta_count": 1,
                "state_delta_keys": ["counter"],
                "has_error": False,
            },
            "state_delta_summary": {
                "state_delta_entity_mode": "state_delta_contract_summary",
                "state_delta_count": 1,
                "state_delta_refs": ["state-delta-lifecycle-001"],
                "state_delta_scopes": ["session"],
                "state_delta_keys": ["counter"],
                "state_delta_operations": ["set"],
                "raw_state_values_included": False,
            },
            "run_config": {"custom_metadata_keys": ["source"]},
        }
    )

    assert isinstance(summary, AdkLifecycleFactsSummary)
    assert summary.summary_id == "adk-lifecycle-summary-evidence-lifecycle-001"
    assert summary.artifacts[0].artifact_ref.artifact_id == "artifact-output.txt"
    assert summary.artifacts[0].operation is not None
    assert summary.artifacts[0].operation.value == "set"
    assert summary.artifacts[0].service_type_name == "InMemoryArtifactService"
    assert summary.session is not None
    assert summary.session.session_id == "session-lifecycle-001"
    assert summary.session.service_type_name == "InMemorySessionService"
    assert summary.events.event_count == 2
    assert summary.events.event_ids == ["event-lifecycle-001"]
    assert summary.events.artifact_delta_refs == ["artifact-output.txt"]
    assert summary.events.state_delta_refs == ["state-delta-lifecycle-001"]
    assert summary.events.state_delta_count == 1
    assert summary.context_state.state_delta_entity_mode == (
        "state_delta_contract_summary"
    )
    assert summary.context_state.state_delta_refs == ["state-delta-lifecycle-001"]
    assert summary.context_state.state_delta_keys == ["counter"]
    assert summary.context_state.custom_metadata_keys == ["source"]
    dumped = summary.model_dump(mode="python")
    assert "google.adk" not in repr(dumped)
    assert "Runner(" not in repr(dumped)


def test_build_adk_run_config_service_bundle_summary_from_evidence_mapping() -> None:
    summary = build_adk_run_config_service_bundle_summary(
        {
            "evidence_id": "evidence-config-bundle-001",
            "runtime_id": "runtime-config-bundle-001",
            "workflow_id": "workflow-config-bundle-001",
            "workflow_name": "config-bundle-workflow",
            "status": "success",
            "assembly_options": {
                "service_bundle_options": {"source": "in_memory"},
            },
            "run_config": {
                "adk_run_config_version": "2.1.0",
                "official_fields": ["max_llm_calls", "tool_thread_pool_config"],
                "mapper_supported_fields": ["max_llm_calls"],
                "field_policies": {
                    "tool_thread_pool_config": {
                        "status": "deferred_tool_execution",
                        "reason": (
                            "tool execution is outside the first lifecycle-core batch"
                        ),
                    }
                },
                "deprecated_fields": ["save_live_audio"],
                "live_media_fields": ["save_live_blob", "save_live_audio"],
                "legacy_input_fields": ["save_live_audio"],
                "translated_fields": ["save_live_audio->save_live_blob"],
                "declared_fields": ["max_llm_calls", "tool_thread_pool_config"],
                "source": "assembly_options + workflow_result.metadata",
                "mapped_fields": [
                    "max_llm_calls",
                    "custom_metadata",
                    "streaming_mode",
                ],
                "unmapped_fields": ["tool_thread_pool_config"],
                "deferred_fields": ["tool_thread_pool_config"],
                "custom_metadata_keys": ["source"],
                "max_llm_calls": 17,
                "streaming_mode": "none",
                "adk_run_config_type": "RunConfig",
            },
            "service_bundle": {
                "artifact_service": {
                    "adk_service_type": "InMemoryArtifactService"
                },
                "session_service": {"adk_service_type": "InMemorySessionService"},
            },
        }
    )

    assert isinstance(summary, AdkRunConfigServiceBundleSummary)
    assert summary.summary_id == (
        "adk-run-config-service-bundle-summary-evidence-config-bundle-001"
    )
    assert summary.run_config.mapped_fields == [
        "max_llm_calls",
        "custom_metadata",
        "streaming_mode",
    ]
    assert summary.run_config.adk_run_config_version == "2.1.0"
    assert summary.run_config.legacy_input_fields == ["save_live_audio"]
    assert summary.run_config.translated_fields == ["save_live_audio->save_live_blob"]
    assert summary.run_config.declared_fields == [
        "max_llm_calls",
        "tool_thread_pool_config",
    ]
    assert summary.run_config.deferred_fields == ["tool_thread_pool_config"]
    assert summary.run_config.field_policies["tool_thread_pool_config"]["status"] == (
        "deferred_tool_execution"
    )
    assert summary.run_config.live_call_enabled is False
    assert summary.run_config.no_live_mode is True
    assert summary.run_config.call_attempted is False
    assert summary.service_bundle.service_bundle_source == "in_memory"
    assert summary.service_bundle.persistence_stage == "runtime_fact_only"
    assert summary.service_bundle.external_persistence_enabled is False
    assert summary.service_bundle.artifact_service_present is True
    assert summary.service_bundle.session_service_type_name == "InMemorySessionService"
    dumped = summary.model_dump(mode="python")
    assert "google.adk" not in repr(dumped)
    assert "adk_adapter" not in repr(dumped)


def _runtime_result() -> RuntimeResult:
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
        payload={"output": {"ok": True}, "state_delta": {"counter": 1}},
        state_delta_refs=["state-delta-observability-provider-148"],
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
    state_delta = StateDelta(
        delta_id="state-delta-observability-provider-148",
        invocation_ref=invocation_ref,
        scope="session",
        key="counter",
        value={"hidden": "not exported"},
        operation=DeltaOperation.SET,
        metadata={"sanitized": True},
    )
    workflow_result = WorkflowResult(
        workflow_ref=workflow_ref,
        status=RuntimeStatus.SUCCESS,
        invocation_ref=invocation_ref,
        events=[event],
        state_deltas=[state_delta],
        artifact_deltas=[artifact_delta],
        metadata={
            "session_id": "session-observability-provider-148",
            "app_name": "observability-provider-app",
            "user_id": "observability-provider-user",
            "state_keys": ["counter"],
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
        state_deltas=[state_delta],
        artifact_deltas=[artifact_delta],
        metadata={"runtime_name": "observability-provider-runtime"},
    )


def _assembly_metadata() -> dict[str, object]:
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
                "adk_run_config_version": "2.1.0",
                "field_policies": {
                    "tool_thread_pool_config": {
                        "status": "deferred_tool_execution",
                        "reason": (
                            "tool execution is outside the first lifecycle-core batch"
                        ),
                    }
                },
                "deprecated_fields": ["save_live_audio"],
                "live_media_fields": ["save_live_blob", "save_live_audio"],
                "legacy_input_fields": ["save_live_audio"],
                "translated_fields": ["save_live_audio->save_live_blob"],
                "mapped_fields": ["max_llm_calls", "custom_metadata"],
                "unmapped_fields": ["tool_thread_pool_config"],
                "deferred_fields": ["tool_thread_pool_config"],
            },
        },
    }
