import pytest
from pydantic import ValidationError

from schemas.runtime import (
    AdkLifecycleFactsSummary,
    AdkRunConfigServiceBundleSummary,
    AdkServiceFactsSummaryInput,
    ArtifactLifecycleFacts,
    ArtifactRef,
    ContextStateLifecycleFacts,
    DeltaOperation,
    EventLifecycleFacts,
    InvocationRef,
    RuntimeInput,
    RuntimeProductizationGateEvaluationFacts,
    RuntimeStatus,
    RunConfigGovernanceView,
    RecordedRunEvidenceInput,
    SessionLifecycleFacts,
    ServiceBundleGovernanceView,
    WorkflowRef,
)


def test_runtime_input_accepts_declared_fields() -> None:
    invocation_ref = InvocationRef(invocation_id="inv-1", runtime_id="rt-1")
    workflow_ref = WorkflowRef(workflow_id="wf-1", name="demo")

    runtime_input = RuntimeInput(
        runtime_id="rt-1",
        workflow_ref=workflow_ref,
        invocation_ref=invocation_ref,
        input_payload={"prompt": "hello"},
        adapter_selection="local",
    )

    assert runtime_input.runtime_id == "rt-1"
    assert runtime_input.workflow_ref.workflow_id == "wf-1"
    assert runtime_input.adapter_selection == "local"


def test_runtime_schema_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        InvocationRef(invocation_id="inv-1", unexpected=True)


def test_runtime_status_values_are_stable() -> None:
    assert RuntimeStatus.SUCCESS.value == "success"
    assert RuntimeStatus.RESUMABLE.value == "resumable"


def test_adk_lifecycle_summary_reuses_runtime_refs_and_remains_candidate_only() -> None:
    invocation_ref = InvocationRef(
        invocation_id="inv-lifecycle-1",
        metadata={"session_id": "session-lifecycle-1", "sanitized": True},
    )
    summary = AdkLifecycleFactsSummary(
        summary_id="summary-lifecycle-1",
        runtime_id="runtime-lifecycle-1",
        workflow_id="workflow-lifecycle-1",
        status="success",
        invocation_ref=invocation_ref,
        artifacts=[
            ArtifactLifecycleFacts(
                artifact_ref=ArtifactRef(
                    artifact_id="artifact-1",
                    name="output.txt",
                    version="0",
                ),
                invocation_ref=invocation_ref,
                operation=DeltaOperation.SET,
                version="0",
                service_type_name="InMemoryArtifactService",
                metadata_keys=["raw_artifact_delta"],
                metadata={"sanitized": True},
            )
        ],
        session=SessionLifecycleFacts(
            session_id="session-lifecycle-1",
            app_name="app",
            user_id="user",
            invocation_ref=invocation_ref,
            event_count=2,
            service_type_name="InMemorySessionService",
            metadata={"sanitized": True},
        ),
        events=EventLifecycleFacts(
            event_count=2,
            event_ids=["event-1"],
            event_types=["node_completed"],
            authors=["node"],
            branch_ids=["main"],
            node_paths=["workflow@1/node@1"],
            state_delta_refs=["state-delta-1"],
            artifact_delta_refs=["artifact-1"],
            invocation_ids=["adk-inv-lifecycle-1"],
            state_delta_count=1,
            state_delta_keys=["counter"],
            error_codes=[],
            metadata={"sanitized": True},
        ),
        context_state=ContextStateLifecycleFacts(
            has_session_state=True,
            session_state_keys=["counter"],
            session_state_key_count=1,
            state_delta_refs=["state-delta-1"],
            state_delta_scopes=["session"],
            state_delta_operations=["set"],
            state_delta_count=1,
            state_delta_keys=["counter"],
            state_delta_entity_mode="state_delta_contract_summary",
            custom_metadata_keys=["source"],
            metadata={"sanitized": True, "does_not_include_state_values": True},
        ),
        metadata={"sanitized": True},
    )

    assert summary.candidate_only is True
    assert summary.formal_decision_enabled is False
    assert summary.policy_execution_enabled is False
    assert summary.governance_outcome_enabled is False
    assert summary.artifacts[0].artifact_ref.artifact_id == "artifact-1"
    assert summary.session is not None
    assert summary.session.session_id == "session-lifecycle-1"
    assert summary.context_state.state_delta_keys == ["counter"]
    assert "google.adk" not in repr(summary.model_dump(mode="python"))


def test_lifecycle_contract_rejects_runtime_object_metadata() -> None:
    with pytest.raises(ValidationError):
        ArtifactLifecycleFacts(
            artifact_ref=ArtifactRef(artifact_id="artifact-1"),
            metadata={"object_module": "google.adk.events"},
        )


def test_lifecycle_summary_rejects_formal_boundary_flags() -> None:
    with pytest.raises(ValidationError):
        AdkLifecycleFactsSummary(
            summary_id="summary-lifecycle-1",
            candidate_only=False,
            events=EventLifecycleFacts(),
        )


def test_run_config_service_bundle_summary_remains_candidate_and_no_live() -> None:
    summary = AdkRunConfigServiceBundleSummary(
        summary_id="summary-run-config-service-bundle-1",
        runtime_id="runtime-1",
        workflow_id="workflow-1",
        status="success",
        run_config=RunConfigGovernanceView(
            run_config_source="assembly_options + workflow_result.metadata",
            adk_run_config_version="2.0.0b1",
            official_fields=["max_llm_calls", "tool_thread_pool_config"],
            mapper_supported_fields=["max_llm_calls"],
            field_policies={
                "tool_thread_pool_config": {
                    "status": "deferred_tool_execution",
                    "reason": "tool execution is outside the first lifecycle-core batch",
                }
            },
            deprecated_fields=["save_live_audio"],
            live_media_fields=["save_live_blob", "save_live_audio"],
            declared_fields=["max_llm_calls", "tool_thread_pool_config"],
            mapped_fields=["max_llm_calls", "custom_metadata"],
            unmapped_fields=["tool_thread_pool_config"],
            deferred_fields=["tool_thread_pool_config"],
            custom_metadata_keys=["source"],
            max_llm_calls=17,
            streaming_mode="none",
            adk_run_config_type="RunConfig",
            metadata={"sanitized": True},
        ),
        service_bundle=ServiceBundleGovernanceView(
            service_bundle_source="in_memory",
            persistence_stage="runtime_fact_only",
            persistence_strategy="in_memory_or_provided_service_reference",
            external_persistence_enabled=False,
            artifact_service_present=True,
            session_service_present=True,
            artifact_service_type_name="InMemoryArtifactService",
            session_service_type_name="InMemorySessionService",
            capability_flags=[
                "artifact_service_present",
                "session_service_present",
            ],
            metadata={"sanitized": True},
        ),
        metadata={"sanitized": True},
    )

    assert summary.candidate_only is True
    assert summary.formal_decision_enabled is False
    assert summary.run_config.live_call_enabled is False
    assert summary.run_config.no_live_mode is True
    assert summary.run_config.call_attempted is False
    assert summary.run_config.adk_run_config_version == "2.0.0b1"
    assert summary.run_config.deferred_fields == ["tool_thread_pool_config"]
    assert summary.run_config.field_policies["tool_thread_pool_config"]["status"] == (
        "deferred_tool_execution"
    )
    assert summary.service_bundle.service_bundle_source == "in_memory"
    assert summary.service_bundle.external_persistence_enabled is False
    assert "google.adk" not in repr(summary.model_dump(mode="python"))


def test_run_config_governance_view_rejects_live_boundary_open() -> None:
    with pytest.raises(ValidationError):
        RunConfigGovernanceView(live_call_enabled=True)


def test_service_bundle_governance_view_rejects_runtime_object_metadata() -> None:
    with pytest.raises(ValidationError):
        ServiceBundleGovernanceView(
            metadata={"object_module": "google.adk.sessions"}
        )


def test_context_state_lifecycle_facts_rejects_raw_state_values_boundary() -> None:
    with pytest.raises(ValidationError):
        ContextStateLifecycleFacts(raw_state_values_included=True)


def test_service_bundle_governance_view_rejects_external_persistence_boundary() -> None:
    with pytest.raises(ValidationError):
        ServiceBundleGovernanceView(external_persistence_enabled=True)


def test_recorded_run_evidence_input_contract_requires_sanitized_service_facts() -> None:
    service_facts = AdkServiceFactsSummaryInput(
        evidence_id="service-facts-147",
        lifecycle_summary=AdkLifecycleFactsSummary(
            summary_id="lifecycle-summary-147",
            events=EventLifecycleFacts(),
        ),
        run_config_service_bundle_summary=AdkRunConfigServiceBundleSummary(
            summary_id="run-config-service-bundle-summary-147",
        ),
    )
    recorded = RecordedRunEvidenceInput(
        recorded_run_id="recorded-run-147",
        evidence_bundle_ref="evidence-bundle://recorded-run-147",
        evidence_bundle_observed=True,
        adk_service_facts=service_facts,
    )

    assert recorded.does_not_execute_recorded_run is True
    assert recorded.adk_service_facts.sanitized is True
    assert recorded.evidence_bundle_observed is True


def test_runtime_productization_gate_evaluation_facts_reject_execution_flags() -> None:
    with pytest.raises(ValidationError):
        RuntimeProductizationGateEvaluationFacts(
            gate_id="gate-147",
            adk_run_performed=True,
        )
