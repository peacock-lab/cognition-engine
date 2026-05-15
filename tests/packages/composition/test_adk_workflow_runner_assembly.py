from __future__ import annotations

from pathlib import Path
from typing import Any

from adk_adapter import AdkRunConfigOptions, AdkRunnerServiceBundleOptions
from config_contexts.runtime import (
    AdapterSelectionConfigView,
    AdkRunConfigView,
    ArtifactPolicyConfigView,
    EventPolicyConfigView,
    NodeExecutionConfigView,
    ResumePolicyConfigView,
    RuntimeConfigContextBundle,
    RuntimeConfigView,
    WorkflowExecutionConfigView,
)
from composition.adk_workflow_runner_assembly import (
    AdkWorkflowRunnerGovernanceSummaryProviderAssembly,
    AdkWorkflowRunnerAssemblyOptions,
    AdkWorkflowRunnerRuntimeAssembly,
    AdkWorkflowRunnerServiceFactsProviderAssembly,
    build_adk_run_config_options_from_runtime_config,
    build_adk_workflow_runner_governance_summary_provider,
    build_adk_workflow_runner_runtime,
    build_adk_workflow_runner_service_facts_provider,
)
from composition.runtime import RuntimeCompositionOptions
from contract_core.runtime import AdkServiceFactsProvider, RecordedRunEvidenceProvider
from runtime_container.governance_summary_pipeline import (
    build_runtime_container_governance_summary_payload,
    build_runtime_container_governance_summary_payload_from_recorded_run,
)
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
    WorkflowRef,
    WorkflowResult,
)


def test_composition_maps_runtime_config_context_to_adk_run_config_options() -> None:
    config_context = RuntimeConfigContextBundle(
        runtime=RuntimeConfigView(runtime_name="mapped-runtime"),
        workflow_execution=WorkflowExecutionConfigView(workflow_name="mapped-workflow"),
        node_execution=NodeExecutionConfigView(),
        resume_policy=ResumePolicyConfigView(),
        event_policy=EventPolicyConfigView(),
        artifact_policy=ArtifactPolicyConfigView(),
        adapter_selection=AdapterSelectionConfigView(
            default_runtime_adapter="adk",
            adk_adapter_enabled=True,
        ),
        adk_run_config=AdkRunConfigView(
            max_llm_calls=9,
            response_modalities=("TEXT",),
            save_input_blobs_as_artifacts=True,
            support_cfc=False,
            streaming_mode="sse",
            speech_config={"language_code": "zh-CN"},
            context_window_compression={"kind": "registered-only"},
            enable_affective_dialog=False,
            save_live_blob=False,
            get_session_num_recent_events=2,
            custom_metadata={"source": "config-context"},
        ),
    )

    options = build_adk_run_config_options_from_runtime_config(config_context)

    assert options is not None
    assert options.max_llm_calls == 9
    assert options.response_modalities == ("TEXT",)
    assert options.save_input_blobs_as_artifacts is True
    assert options.support_cfc is False
    assert options.streaming_mode == "sse"
    assert options.speech_config == {"language_code": "zh-CN"}
    assert options.context_window_compression == {"kind": "registered-only"}
    assert options.enable_affective_dialog is False
    assert options.save_live_blob is False
    assert options.get_session_num_recent_events == 2
    assert options.custom_metadata == {"source": "config-context"}
    assert options.deferred_fields() == [
        "speech_config",
        "context_window_compression",
    ]


def test_composition_returns_no_adk_run_config_options_for_empty_runtime_view() -> None:
    config_context = RuntimeConfigContextBundle(
        runtime=RuntimeConfigView(runtime_name="empty-runtime"),
        workflow_execution=WorkflowExecutionConfigView(workflow_name="empty-workflow"),
        node_execution=NodeExecutionConfigView(),
        resume_policy=ResumePolicyConfigView(),
        event_policy=EventPolicyConfigView(),
        artifact_policy=ArtifactPolicyConfigView(),
        adapter_selection=AdapterSelectionConfigView(),
    )

    assert build_adk_run_config_options_from_runtime_config(config_context) is None


def test_adk_runtime_assembly_uses_config_context_run_config_when_not_explicit(
    tmp_path: Path,
) -> None:
    config_root = tmp_path / "config"
    (config_root / "base").mkdir(parents=True)
    (config_root / "env").mkdir()
    (config_root / "base" / "runtime.yaml").write_text(
        """
runtime:
  runtime_name: config-runtime
workflow_execution:
  workflow_name: config-workflow
node_execution: {}
resume_policy: {}
event_policy: {}
artifact_policy: {}
adapter_selection:
  default_runtime_adapter: adk
  adk_adapter_enabled: true
adk_run_config:
  max_llm_calls: 4
  streaming_mode: none
  custom_metadata:
    source: config-context
""",
        encoding="utf-8",
    )

    assembly = build_adk_workflow_runner_runtime(
        options=RuntimeCompositionOptions(config_root=config_root, environment="local"),
        workflow=object(),
    )

    assert assembly.assembly_options.run_config_options is not None
    assert assembly.assembly_options.run_config_options.max_llm_calls == 4
    assert assembly.assembly_options.run_config_options.streaming_mode == "none"
    assert assembly.assembly_options.run_config_options.custom_metadata == {
        "source": "config-context"
    }


def test_composition_builds_governance_summary_provider_from_runtime_assembly_metadata() -> None:
    runtime_assembly = AdkWorkflowRunnerRuntimeAssembly(
        runtime_runner=object(),
        workflow_runner=object(),
        service_bundle=object(),
        assembly_options=AdkWorkflowRunnerAssemblyOptions(
            app_name="composition-provider-app",
            user_id="composition-provider-user",
            workflow_name="composition-provider-workflow",
        ),
        metadata=_governance_summary_assembly_metadata(),
    )

    provider_assembly = build_adk_workflow_runner_governance_summary_provider(
        runtime_assembly=runtime_assembly,
        evidence_bundle_ref="evidence-bundle://composition-provider-149",
    )

    assert isinstance(
        provider_assembly,
        AdkWorkflowRunnerGovernanceSummaryProviderAssembly,
    )
    provider: RecordedRunEvidenceProvider = (
        provider_assembly.recorded_run_evidence_provider
    )
    assert provider_assembly.assembly_metadata["workflow_name"] == (
        "composition-provider-workflow"
    )
    assert provider_assembly.evidence_bundle_ref == (
        "evidence-bundle://composition-provider-149"
    )

    recorded = provider.build_recorded_run_evidence(_governance_summary_runtime_result())

    assert recorded.recorded_run_id == "runtime-composition-provider-149"
    assert recorded.evidence_bundle_ref == "evidence-bundle://composition-provider-149"
    assert recorded.evidence_bundle_observed is True
    assert recorded.adk_workflow_runner_evidence_observed is True
    assert recorded.adk_service_facts.lifecycle_summary.workflow_name == (
        "composition-provider-workflow"
    )


def test_composition_provider_can_be_injected_into_runtime_container_pipeline() -> None:
    runtime_assembly = AdkWorkflowRunnerRuntimeAssembly(
        runtime_runner=object(),
        workflow_runner=object(),
        service_bundle=object(),
        assembly_options=AdkWorkflowRunnerAssemblyOptions(
            app_name="composition-provider-app",
            user_id="composition-provider-user",
            workflow_name="composition-provider-workflow",
        ),
        metadata=_governance_summary_assembly_metadata(),
    )
    provider_assembly = build_adk_workflow_runner_governance_summary_provider(
        runtime_assembly=runtime_assembly,
        evidence_bundle_ref="evidence-bundle://composition-provider-149",
    )

    payload = build_runtime_container_governance_summary_payload_from_recorded_run(
        runtime_result=_governance_summary_runtime_result(),
        recorded_run_evidence_provider=(
            provider_assembly.recorded_run_evidence_provider
        ),
    )

    assert payload["recorded_run"]["recorded_run_id"] == (
        "runtime-composition-provider-149"
    )
    assert payload["recorded_run"]["evidence_bundle_ref"] == (
        "evidence-bundle://composition-provider-149"
    )
    assert payload["recorded_run"]["has_evidence_bundle"] is True
    assert payload["summary_generation"][
        "uses_recorded_run_evidence_provider_contract"
    ] is True
    assert payload["lifecycle_summary"]["workflow_name"] == (
        "composition-provider-workflow"
    )
    assert payload["run_config_service_bundle_summary"]["service_bundle"][
        "service_bundle_source"
    ] == "in_memory"


def test_composition_builds_service_facts_provider_from_runtime_assembly_metadata() -> None:
    runtime_assembly = AdkWorkflowRunnerRuntimeAssembly(
        runtime_runner=object(),
        workflow_runner=object(),
        service_bundle=object(),
        assembly_options=AdkWorkflowRunnerAssemblyOptions(
            app_name="composition-provider-app",
            user_id="composition-provider-user",
            workflow_name="composition-provider-workflow",
        ),
        metadata=_governance_summary_assembly_metadata(),
    )

    provider_assembly = build_adk_workflow_runner_service_facts_provider(
        runtime_assembly=runtime_assembly,
    )

    assert isinstance(
        provider_assembly,
        AdkWorkflowRunnerServiceFactsProviderAssembly,
    )
    provider: AdkServiceFactsProvider = provider_assembly.adk_service_facts_provider
    assert provider_assembly.assembly_metadata["workflow_name"] == (
        "composition-provider-workflow"
    )

    service_facts = provider.build_adk_service_facts(
        _governance_summary_runtime_result()
    )

    assert service_facts.sanitized is True
    assert service_facts.lifecycle_summary.workflow_name == (
        "composition-provider-workflow"
    )
    assert service_facts.lifecycle_summary.events.event_count == 1
    assert (
        service_facts.run_config_service_bundle_summary.service_bundle
        .service_bundle_source
        == "in_memory"
    )


def test_composition_service_facts_provider_can_feed_runtime_container_pipeline() -> None:
    runtime_assembly = AdkWorkflowRunnerRuntimeAssembly(
        runtime_runner=object(),
        workflow_runner=object(),
        service_bundle=object(),
        assembly_options=AdkWorkflowRunnerAssemblyOptions(
            app_name="composition-provider-app",
            user_id="composition-provider-user",
            workflow_name="composition-provider-workflow",
        ),
        metadata=_governance_summary_assembly_metadata(),
    )
    provider_assembly = build_adk_workflow_runner_service_facts_provider(
        runtime_assembly=runtime_assembly,
    )
    service_facts = provider_assembly.adk_service_facts_provider.build_adk_service_facts(
        _governance_summary_runtime_result()
    )

    payload = build_runtime_container_governance_summary_payload(
        adk_service_facts=service_facts,
        evidence_id="runtime-container-governance-summary-151",
    )

    assert payload["evidence_id"] == "runtime-container-governance-summary-151"
    assert payload["summary_generation"]["input_kind"] == (
        "observability_hub.adk_workflow_runner_evidence."
        "AdkServiceFactsSummaryInput"
    )
    assert payload["lifecycle_summary"]["workflow_name"] == (
        "composition-provider-workflow"
    )
    assert payload["run_config_service_bundle_summary"]["service_bundle"][
        "service_bundle_source"
    ] == "in_memory"


def test_composition_builds_adk2_workflow_runner_service_chain() -> None:
    from google.adk.agents.context import Context
    from google.adk.events import Event
    from google.adk.events.event import NodeInfo
    from google.adk.workflow import START, BaseNode, Workflow
    from google.genai import types

    class ArtifactNode(BaseNode):
        async def _run_impl(self, *, ctx: Context, node_input: Any):
            version = await ctx.save_artifact(
                "composition-output.txt",
                types.Part(text="composition artifact payload"),
                custom_metadata={"source": "composition-assembly-test"},
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

    bundle_options = AdkRunnerServiceBundleOptions(source="in_memory")
    run_config_options = AdkRunConfigOptions(
        max_llm_calls=11,
        custom_metadata={"source": "composition-options-test"},
        response_modalities=("TEXT",),
        streaming_mode="none",
        get_session_num_recent_events=4,
    )
    assembly_options = AdkWorkflowRunnerAssemblyOptions(
        app_name="test_composition_adk2_options",
        user_id="composition-options-user",
        workflow_name="composition-options-workflow",
        service_bundle_options=bundle_options,
        run_config_options=run_config_options,
        metadata={"test_case": "composition-options"},
    )
    workflow = Workflow(
        name="composition_adk2_workflow",
        edges=[(START, ArtifactNode(name="artifact_node"))],
    )
    assembly = build_adk_workflow_runner_runtime(
        options=RuntimeCompositionOptions(config_root=Path("config"), environment="local"),
        workflow=workflow,
        assembly_options=assembly_options,
    )

    runtime_result = assembly.runtime_runner.run(
        RuntimeInput(
            runtime_id="runtime-composition-adk2-001",
            workflow_ref=WorkflowRef(workflow_id="workflow-composition-adk2-001"),
            invocation_ref=InvocationRef(invocation_id="inv-composition-adk2-001"),
            input_payload={"message": "hello"},
        )
    )
    session_id = runtime_result.workflow_result.metadata["session_id"]
    workflow_service_metadata = runtime_result.workflow_result.metadata["workflow_service"]
    run_config_metadata = runtime_result.workflow_result.metadata["run_config"]

    assert runtime_result.status == RuntimeStatus.SUCCESS
    assert runtime_result.workflow_result.status == RuntimeStatus.SUCCESS
    assert assembly.assembly_options is assembly_options
    assert assembly.metadata["observability_candidate"] == (
        "observability_hub.adk_workflow_runner_intake"
    )
    assert assembly.metadata["app_name"] == "test_composition_adk2_options"
    assert assembly.metadata["user_id"] == "composition-options-user"
    assert assembly.metadata["workflow_name"] == "composition-options-workflow"
    assert assembly.metadata["assembly_options"]["service_bundle_options"]["source"] == (
        "in_memory"
    )
    assert assembly.metadata["assembly_options"]["run_config_options"]["mapped_fields"] == [
        "max_llm_calls",
        "custom_metadata",
        "response_modalities",
        "streaming_mode",
        "get_session_config",
    ]
    assert "official_fields" in assembly.metadata["assembly_options"]["run_config_options"]
    assert "tool_thread_pool_config" in (
        assembly.metadata["assembly_options"]["run_config_options"]["unmapped_fields"]
    )
    assert workflow_service_metadata["adapter"] == "adk_adapter.workflow_service"
    assert workflow_service_metadata["runner_service"]["run_config"]["max_llm_calls"] == 11
    assert run_config_metadata["max_llm_calls"] == 11
    assert run_config_metadata["custom_metadata_keys"] == ["source"]
    assert runtime_result.workflow_result.artifact_deltas[0].artifact_ref.artifact_id == (
        "composition-output.txt"
    )
    assert any(
        event.payload["output"]
        and event.payload["output"].get("max_llm_calls") == 11
        and event.payload["output"].get("run_config_source") == "composition-options-test"
        for event in runtime_result.workflow_result.events
    )

    loaded_artifact = assembly.service_bundle.artifact_service.load_artifact_sync(
        filename="composition-output.txt",
        session_id=session_id,
    )
    loaded_session = assembly.service_bundle.session_service.get_session_sync(
        session_id=session_id
    )

    assert loaded_artifact.text == "composition artifact payload"
    assert loaded_session.id == session_id
    assert len(loaded_session.events) >= 2


def _governance_summary_runtime_result() -> RuntimeResult:
    invocation_ref = InvocationRef(
        invocation_id="inv-composition-provider-149",
        runtime_id="runtime-composition-provider-149",
        workflow_id="workflow-composition-provider-149",
        metadata={"session_id": "session-composition-provider-149"},
    )
    workflow_ref = WorkflowRef(
        workflow_id="workflow-composition-provider-149",
        name="composition-provider-workflow",
    )
    event = RuntimeEvent(
        event_id="event-composition-provider-149",
        event_type=RuntimeEventType.NODE_COMPLETED,
        invocation_ref=invocation_ref,
        workflow_ref=workflow_ref,
        payload={"output": {"ok": True}},
        metadata={
            "node_path": "workflow@1/composition_provider_node@1",
            "author": "composition_provider_node",
            "requested_invocation_id": "inv-composition-provider-149",
            "adk_invocation_id": "adk-composition-provider-149",
            "session_id": "session-composition-provider-149",
            "app_name": "composition-provider-app",
            "user_id": "composition-provider-user",
        },
    )
    artifact_delta = ArtifactDelta(
        delta_id="artifact-delta-composition-provider-149",
        invocation_ref=invocation_ref,
        artifact_ref=ArtifactRef(
            artifact_id="composition-provider-artifact.json",
            name="composition-provider-artifact.json",
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
            "session_id": "session-composition-provider-149",
            "app_name": "composition-provider-app",
            "user_id": "composition-provider-user",
            "run_config": {
                "max_llm_calls": 3,
                "streaming_mode": "none",
                "adk_run_config_type": "RunConfig",
                "custom_metadata_keys": ["source"],
            },
        },
    )
    return RuntimeResult(
        runtime_id="runtime-composition-provider-149",
        status=RuntimeStatus.SUCCESS,
        invocation_ref=invocation_ref,
        workflow_result=workflow_result,
        events=[event],
        artifact_deltas=[artifact_delta],
        metadata={"runtime_name": "composition-provider-runtime"},
    )


def _governance_summary_assembly_metadata() -> dict[str, object]:
    return {
        "assembly": "composition.adk_workflow_runner_assembly",
        "workflow_type": "SyntheticWorkflow",
        "workflow_name": "composition-provider-workflow",
        "app_name": "composition-provider-app",
        "user_id": "composition-provider-user",
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
        "observability_candidate": "observability_hub.adk_workflow_runner_intake",
    }
