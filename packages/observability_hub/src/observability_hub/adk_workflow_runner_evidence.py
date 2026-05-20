"""ADK2 WorkflowRunner execution evidence candidates."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import Field

from contract_core.runtime import (
    AdkServiceFactsProvider,
    AdkServiceFactsSummaryInput,
    RecordedRunEvidenceInput,
    RecordedRunEvidenceProvider,
)
from schemas.runtime import (
    AdkLifecycleFactsSummary,
    AdkRunConfigServiceBundleSummary,
    ArtifactDelta,
    ArtifactLifecycleFacts,
    ArtifactRef,
    ContextStateLifecycleFacts,
    DeltaOperation,
    EventLifecycleFacts,
    InvocationRef,
    RuntimeEvent,
    RuntimeResult,
    RunConfigGovernanceView,
    SessionLifecycleFacts,
    ServiceBundleGovernanceView,
    StateDelta,
)

from observability_hub.errors import ObservabilityHubInputError
from observability_hub.models import EvidenceBundle, ObservabilityBaseModel


EVIDENCE_BUNDLE_REF_PREFIX = "evidence-bundle://"


class AdkWorkflowRunnerEvidence(ObservabilityBaseModel):
    """Candidate evidence from the ADK2 WorkflowRunner assembly execution chain."""

    evidence_id: str
    source: str
    runtime_kind: str
    runtime_id: str
    workflow_id: str | None = None
    workflow_name: str | None = None
    status: str
    app_name: str | None = None
    user_id: str | None = None
    assembly_options: dict[str, Any] = Field(default_factory=dict)
    service_bundle: dict[str, Any] = Field(default_factory=dict)
    run_config: dict[str, Any] = Field(default_factory=dict)
    artifact_summary: dict[str, Any] = Field(default_factory=dict)
    session_summary: dict[str, Any] = Field(default_factory=dict)
    event_summary: dict[str, Any] = Field(default_factory=dict)
    state_delta_summary: dict[str, Any] = Field(default_factory=dict)
    graph_summary: dict[str, Any] = Field(default_factory=dict)
    trace_summary: dict[str, Any] = Field(default_factory=dict)
    lifecycle_summary: dict[str, Any] = Field(default_factory=dict)
    run_config_service_bundle_summary: dict[str, Any] = Field(default_factory=dict)
    metadata_keys: list[str] = Field(default_factory=list)
    observability_candidate: str | None = None
    contract_candidate_notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: str


class AdkWorkflowRunnerRecordedRunEvidenceProvider(RecordedRunEvidenceProvider):
    """Recorded-run evidence provider for sanitized ADK WorkflowRunner facts."""

    def __init__(
        self,
        *,
        assembly_metadata: dict[str, Any] | None = None,
        evidence_bundle_ref: str | None = None,
        evidence_bundle: EvidenceBundle | str | None = None,
    ) -> None:
        self._assembly_metadata = _sanitize(assembly_metadata or {})
        self._evidence_bundle_ref = _resolve_evidence_bundle_ref(
            evidence_bundle_ref=evidence_bundle_ref,
            evidence_bundle=evidence_bundle,
        )

    def build_recorded_run_evidence(
        self,
        runtime_result: RuntimeResult,
    ) -> RecordedRunEvidenceInput:
        """Build contractized recorded-run evidence from a runtime result."""

        return build_recorded_run_evidence_from_adk_workflow_runner(
            runtime_result,
            assembly_metadata=self._assembly_metadata,
            evidence_bundle_ref=self._evidence_bundle_ref,
        )


class AdkWorkflowRunnerAdkServiceFactsProvider(AdkServiceFactsProvider):
    """ADK service facts provider for sanitized ADK WorkflowRunner facts."""

    def __init__(
        self,
        *,
        assembly_metadata: dict[str, Any] | None = None,
    ) -> None:
        self._assembly_metadata = _sanitize(assembly_metadata or {})

    def build_adk_service_facts(
        self,
        runtime_result: RuntimeResult,
    ) -> AdkServiceFactsSummaryInput:
        """Build contractized ADK service facts from a runtime result."""

        return build_adk_service_facts_from_adk_workflow_runner(
            runtime_result,
            assembly_metadata=self._assembly_metadata,
        )


def build_evidence_bundle_ref(evidence_bundle: EvidenceBundle | str) -> str:
    """Build the stable reference id used to link an upstream EvidenceBundle.

    The returned value is a reference identifier only. It must not carry the
    EvidenceBundle body, prompts, responses, provider payloads, or secrets.
    """

    if isinstance(evidence_bundle, EvidenceBundle):
        bundle_id = evidence_bundle.bundle_id
    else:
        bundle_id = evidence_bundle

    ref = _required_string(bundle_id, "EvidenceBundle.bundle_id")
    if ref.startswith(EVIDENCE_BUNDLE_REF_PREFIX):
        return ref
    return f"{EVIDENCE_BUNDLE_REF_PREFIX}{ref}"


def build_adk_service_facts_from_adk_workflow_runner(
    runtime_result: RuntimeResult | dict[str, Any],
    *,
    assembly_metadata: dict[str, Any] | None = None,
) -> AdkServiceFactsSummaryInput:
    """Build sanitized ADK service facts for governance summary injection."""

    evidence = build_adk_workflow_runner_evidence(
        runtime_result,
        assembly_metadata=assembly_metadata,
    )
    return _build_adk_service_facts_from_evidence(evidence)


def build_adk_workflow_runner_evidence(
    runtime_result: RuntimeResult | dict[str, Any],
    *,
    assembly_metadata: dict[str, Any] | None = None,
) -> AdkWorkflowRunnerEvidence:
    """Build an ADK2 WorkflowRunner execution evidence candidate."""

    parsed_runtime_result = _as_runtime_result(runtime_result)
    workflow_result = parsed_runtime_result.workflow_result
    runtime_metadata = _sanitize(parsed_runtime_result.metadata)
    workflow_metadata = _sanitize(workflow_result.metadata if workflow_result else {})
    assembly = _sanitize(assembly_metadata or {})
    workflow_service = _mapping(workflow_metadata.get("workflow_service"))
    runner_service = _mapping(workflow_service.get("runner_service"))

    warnings: list[str] = []
    if not assembly:
        warnings.append("assembly_metadata was not provided; assembly facts are partial.")
    if workflow_result is None:
        warnings.append("RuntimeResult.workflow_result was not available.")

    events = _select_event_source(parsed_runtime_result)
    artifacts = _select_artifact_source(parsed_runtime_result)
    state_deltas = _select_state_delta_source(parsed_runtime_result)
    run_config = _build_run_config_summary(
        assembly_options=_mapping(assembly.get("assembly_options")),
        workflow_metadata=workflow_metadata,
        runner_service=runner_service,
    )
    service_bundle = _mapping(assembly.get("service_bundle")) or _mapping(
        runner_service.get("service_bundle")
    )

    workflow_id = (
        workflow_result.workflow_ref.workflow_id
        if workflow_result is not None
        else parsed_runtime_result.invocation_ref.workflow_id
    )
    workflow_name = _first_non_empty(
        assembly,
        "workflow_name",
    ) or (workflow_result.workflow_ref.name if workflow_result is not None else None)

    metadata_sources = [runtime_metadata, workflow_metadata, assembly]
    artifact_summary = _build_artifact_summary(artifacts)
    session_summary = _build_session_summary(
        workflow_metadata=workflow_metadata,
        metadata_sources=metadata_sources,
    )
    event_summary = _build_event_summary(events)
    state_delta_summary = _build_state_delta_summary(state_deltas, events)
    graph_summary = _build_graph_summary(
        event_summary=event_summary,
        workflow_id=workflow_id,
        workflow_name=workflow_name,
    )
    trace_summary = _build_trace_summary(event_summary)
    evidence_id = f"adk-workflow-runner-evidence-{uuid4()}"
    lifecycle_summary = build_adk_lifecycle_facts_summary(
        {
            "evidence_id": evidence_id,
            "source": "observability_hub.adk_workflow_runner_evidence",
            "runtime_id": parsed_runtime_result.runtime_id,
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "status": parsed_runtime_result.status.value,
            "artifact_summary": artifact_summary,
            "session_summary": session_summary,
            "event_summary": event_summary,
            "state_delta_summary": state_delta_summary,
            "run_config": run_config,
            "service_bundle": service_bundle,
        }
    )
    run_config_service_bundle_summary = build_adk_run_config_service_bundle_summary(
        {
            "evidence_id": evidence_id,
            "source": "observability_hub.adk_workflow_runner_evidence",
            "runtime_id": parsed_runtime_result.runtime_id,
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "status": parsed_runtime_result.status.value,
            "assembly_options": _mapping(assembly.get("assembly_options")),
            "run_config": run_config,
            "service_bundle": service_bundle,
        }
    )

    return AdkWorkflowRunnerEvidence(
        evidence_id=evidence_id,
        source="observability_hub.adk_workflow_runner_evidence",
        runtime_kind="adk2_workflow_runner",
        runtime_id=parsed_runtime_result.runtime_id,
        workflow_id=workflow_id,
        workflow_name=workflow_name,
        status=parsed_runtime_result.status.value,
        app_name=_first_non_empty(*metadata_sources, "app_name"),
        user_id=_first_non_empty(*metadata_sources, "user_id"),
        assembly_options=_mapping(assembly.get("assembly_options")),
        service_bundle=service_bundle,
        run_config=run_config,
        artifact_summary=artifact_summary,
        session_summary=session_summary,
        event_summary=event_summary,
        state_delta_summary=state_delta_summary,
        graph_summary=graph_summary,
        trace_summary=trace_summary,
        lifecycle_summary=lifecycle_summary.model_dump(mode="python"),
        run_config_service_bundle_summary=run_config_service_bundle_summary.model_dump(
            mode="python"
        ),
        metadata_keys=sorted(
            {
                key
                for metadata in metadata_sources
                for key in metadata
                if isinstance(key, str)
            }
        ),
        observability_candidate=_first_non_empty(
            assembly,
            "observability_candidate",
        ),
        contract_candidate_notes=[
            "Candidate evidence only; not a public contract.",
            "Candidate evidence only; not a governance decision object.",
            "ADK native objects are summarized as plain metadata.",
            "Workflow graph and trace summaries are candidate summary-only facts.",
        ],
        warnings=warnings,
        created_at=datetime.now(UTC).isoformat(),
    )


def build_recorded_run_evidence_from_adk_workflow_runner(
    runtime_result: RuntimeResult | dict[str, Any],
    *,
    assembly_metadata: dict[str, Any] | None = None,
    evidence_bundle_ref: str | None = None,
    evidence_bundle: EvidenceBundle | str | None = None,
    recorded_run_id: str | None = None,
) -> RecordedRunEvidenceInput:
    """Build contractized recorded-run evidence for runtime_container injection."""

    resolved_evidence_bundle_ref = _resolve_evidence_bundle_ref(
        evidence_bundle_ref=evidence_bundle_ref,
        evidence_bundle=evidence_bundle,
    )
    evidence = build_adk_workflow_runner_evidence(
        runtime_result,
        assembly_metadata=assembly_metadata,
    )
    service_facts = _build_adk_service_facts_from_evidence(
        evidence,
        metadata={
            "evidence_bundle_ref": resolved_evidence_bundle_ref,
            "evidence_bundle_ref_semantics": "stable_reference_identifier_only",
            "does_not_include_evidence_bundle_content": True,
        },
    )
    return RecordedRunEvidenceInput(
        recorded_run_id=recorded_run_id or evidence.runtime_id,
        evidence_id=evidence.evidence_id,
        source=(
            "observability_hub.adk_workflow_runner_evidence."
            "RecordedRunEvidenceInput"
        ),
        adk_service_facts=service_facts,
        adk_workflow_runner_evidence_ref=(
            f"adk-workflow-runner-evidence://{evidence.evidence_id}"
        ),
        evidence_bundle_ref=resolved_evidence_bundle_ref,
        evidence_bundle_observed=resolved_evidence_bundle_ref is not None,
        adk_workflow_runner_evidence_observed=True,
        does_not_execute_recorded_run=True,
        metadata={
            "source_evidence_id": evidence.evidence_id,
            "observability_source": evidence.source,
            "runtime_kind": evidence.runtime_kind,
            "sanitized": True,
            "does_not_include_adk_native_objects": True,
            "does_not_execute_runtime": True,
            "does_not_call_live_llm": True,
            "does_not_call_ollama": True,
            "evidence_bundle_ref": resolved_evidence_bundle_ref,
            "evidence_bundle_ref_semantics": "stable_reference_identifier_only",
            "does_not_include_evidence_bundle_content": True,
        },
    )


def create_adk_workflow_runner_recorded_run_evidence_provider(
    *,
    assembly_metadata: dict[str, Any] | None = None,
    evidence_bundle_ref: str | None = None,
    evidence_bundle: EvidenceBundle | str | None = None,
) -> RecordedRunEvidenceProvider:
    """Create a RecordedRunEvidenceProvider for ADK WorkflowRunner facts."""

    return AdkWorkflowRunnerRecordedRunEvidenceProvider(
        assembly_metadata=assembly_metadata,
        evidence_bundle_ref=evidence_bundle_ref,
        evidence_bundle=evidence_bundle,
    )


def create_adk_workflow_runner_adk_service_facts_provider(
    *,
    assembly_metadata: dict[str, Any] | None = None,
) -> AdkServiceFactsProvider:
    """Create an AdkServiceFactsProvider for ADK WorkflowRunner facts."""

    return AdkWorkflowRunnerAdkServiceFactsProvider(
        assembly_metadata=assembly_metadata,
    )


def build_adk_lifecycle_facts_summary(
    evidence: AdkWorkflowRunnerEvidence | dict[str, Any],
) -> AdkLifecycleFactsSummary:
    """Build sanitized ADK artifact/session/event lifecycle summary facts."""

    evidence_mapping = _evidence_mapping(evidence)
    evidence_id = _plain_str(evidence_mapping.get("evidence_id"))
    artifact_summary = _mapping(evidence_mapping.get("artifact_summary"))
    session_summary = _mapping(evidence_mapping.get("session_summary"))
    event_summary = _mapping(evidence_mapping.get("event_summary"))
    state_delta_summary = _mapping(evidence_mapping.get("state_delta_summary"))
    service_bundle = _mapping(evidence_mapping.get("service_bundle"))
    artifact_service = _mapping(service_bundle.get("artifact_service"))
    session_service = _mapping(service_bundle.get("session_service"))
    invocation_ref = _build_invocation_ref(session_summary)

    summary_id = (
        f"adk-lifecycle-summary-{evidence_id}"
        if evidence_id
        else f"adk-lifecycle-summary-{uuid4()}"
    )
    return AdkLifecycleFactsSummary(
        summary_id=summary_id,
        source="observability_hub.adk_workflow_runner_evidence.lifecycle_summary",
        runtime_id=_plain_str(evidence_mapping.get("runtime_id")),
        workflow_id=_plain_str(evidence_mapping.get("workflow_id")),
        workflow_name=_plain_str(evidence_mapping.get("workflow_name")),
        status=_plain_str(evidence_mapping.get("status")),
        invocation_ref=invocation_ref,
        artifacts=_build_artifact_lifecycle_facts(
            artifact_summary,
            invocation_ref=invocation_ref,
            service_type_name=_plain_str(artifact_service.get("adk_service_type")),
        ),
        session=_build_session_lifecycle_facts(
            session_summary,
            invocation_ref=invocation_ref,
            service_type_name=_plain_str(session_service.get("adk_service_type")),
        ),
        events=_build_event_lifecycle_facts(event_summary),
        context_state=_build_context_state_lifecycle_facts(
            session_summary=session_summary,
            event_summary=event_summary,
            state_delta_summary=state_delta_summary,
            run_config=_mapping(evidence_mapping.get("run_config")),
            runtime_metadata=_mapping(evidence_mapping.get("metadata")),
        ),
        metadata={
            "source_evidence_id": evidence_id,
            "candidate_contract": "schemas.runtime.AdkLifecycleFactsSummary",
            "sanitized": True,
            "does_not_include_adk_native_objects": True,
        },
    )


def build_adk_run_config_service_bundle_summary(
    evidence: AdkWorkflowRunnerEvidence | dict[str, Any],
) -> AdkRunConfigServiceBundleSummary:
    """Build sanitized ADK RunConfig and ServiceBundle governance facts."""

    evidence_mapping = _evidence_mapping(evidence)
    evidence_id = _plain_str(evidence_mapping.get("evidence_id"))
    assembly_options = _mapping(evidence_mapping.get("assembly_options"))
    service_bundle_options = _mapping(assembly_options.get("service_bundle_options"))
    run_config = _mapping(evidence_mapping.get("run_config"))
    service_bundle = _mapping(evidence_mapping.get("service_bundle"))

    summary_id = (
        f"adk-run-config-service-bundle-summary-{evidence_id}"
        if evidence_id
        else f"adk-run-config-service-bundle-summary-{uuid4()}"
    )
    return AdkRunConfigServiceBundleSummary(
        summary_id=summary_id,
        source=(
            "observability_hub.adk_workflow_runner_evidence."
            "run_config_service_bundle_summary"
        ),
        runtime_id=_plain_str(evidence_mapping.get("runtime_id")),
        workflow_id=_plain_str(evidence_mapping.get("workflow_id")),
        workflow_name=_plain_str(evidence_mapping.get("workflow_name")),
        status=_plain_str(evidence_mapping.get("status")),
        run_config=_build_run_config_governance_view(
            run_config,
            evidence_id=evidence_id,
        ),
        service_bundle=_build_service_bundle_governance_view(
            service_bundle,
            service_bundle_options=service_bundle_options,
            evidence_id=evidence_id,
        ),
        metadata={
            "source_evidence_id": evidence_id,
            "candidate_contract": "schemas.runtime.AdkRunConfigServiceBundleSummary",
            "sanitized": True,
            "does_not_include_adk_native_objects": True,
            "does_not_enable_live_call": True,
        },
    )


def _build_adk_service_facts_from_evidence(
    evidence: AdkWorkflowRunnerEvidence,
    *,
    metadata: dict[str, Any] | None = None,
) -> AdkServiceFactsSummaryInput:
    service_metadata = {
        "source_evidence_id": evidence.evidence_id,
        "observability_source": evidence.source,
        "runtime_kind": evidence.runtime_kind,
        "sanitized": True,
        "does_not_include_adk_native_objects": True,
        "does_not_execute_runtime": True,
        "does_not_call_live_llm": True,
        "does_not_call_ollama": True,
    }
    service_metadata.update(_sanitize(metadata or {}))
    return AdkServiceFactsSummaryInput(
        evidence_id=evidence.evidence_id,
        source=(
            "observability_hub.adk_workflow_runner_evidence."
            "AdkServiceFactsSummaryInput"
        ),
        lifecycle_summary=AdkLifecycleFactsSummary.model_validate(
            evidence.lifecycle_summary
        ),
        run_config_service_bundle_summary=(
            AdkRunConfigServiceBundleSummary.model_validate(
                evidence.run_config_service_bundle_summary
            )
        ),
        sanitized=True,
        metadata=service_metadata,
    )


def _as_runtime_result(runtime_result: RuntimeResult | dict[str, Any]) -> RuntimeResult:
    if isinstance(runtime_result, RuntimeResult):
        return runtime_result
    if isinstance(runtime_result, dict):
        return RuntimeResult.model_validate(runtime_result)
    raise ObservabilityHubInputError(
        "build_adk_workflow_runner_evidence expects a RuntimeResult or compatible mapping."
    )


def _resolve_evidence_bundle_ref(
    *,
    evidence_bundle_ref: str | None = None,
    evidence_bundle: EvidenceBundle | str | None = None,
) -> str | None:
    if evidence_bundle_ref is not None:
        explicit_ref = build_evidence_bundle_ref(evidence_bundle_ref)
        if evidence_bundle is None:
            return explicit_ref

        derived_ref = build_evidence_bundle_ref(evidence_bundle)
        if explicit_ref != derived_ref:
            raise ObservabilityHubInputError(
                "evidence_bundle_ref must match the supplied EvidenceBundle.bundle_id."
            )
        return explicit_ref

    if evidence_bundle is not None:
        return build_evidence_bundle_ref(evidence_bundle)
    return None


def _select_event_source(runtime_result: RuntimeResult) -> list[RuntimeEvent]:
    if runtime_result.events:
        return runtime_result.events
    workflow_result = runtime_result.workflow_result
    if workflow_result is not None and workflow_result.events:
        return workflow_result.events
    return []


def _select_artifact_source(runtime_result: RuntimeResult) -> list[ArtifactDelta]:
    if runtime_result.artifact_deltas:
        return runtime_result.artifact_deltas
    workflow_result = runtime_result.workflow_result
    if workflow_result is not None and workflow_result.artifact_deltas:
        return workflow_result.artifact_deltas
    return []


def _select_state_delta_source(runtime_result: RuntimeResult) -> list[StateDelta]:
    if runtime_result.state_deltas:
        return runtime_result.state_deltas
    workflow_result = runtime_result.workflow_result
    if workflow_result is not None and workflow_result.state_deltas:
        return workflow_result.state_deltas
    return []


def _build_run_config_summary(
    *,
    assembly_options: dict[str, Any],
    workflow_metadata: dict[str, Any],
    runner_service: dict[str, Any],
) -> dict[str, Any]:
    run_config_options = _mapping(assembly_options.get("run_config_options"))
    workflow_run_config = _mapping(workflow_metadata.get("run_config"))
    runner_run_config = _mapping(runner_service.get("run_config"))
    return {
        "source": "assembly_options + workflow_result.metadata",
        "adk_run_config_version": (
            run_config_options.get("adk_run_config_version")
            or workflow_run_config.get("adk_run_config_version")
            or runner_run_config.get("adk_run_config_version")
        ),
        "official_fields": list(
            run_config_options.get(
                "official_fields",
                runner_run_config.get("official_fields", []),
            )
        ),
        "mapper_supported_fields": list(
            run_config_options.get(
                "mapper_supported_fields",
                runner_run_config.get("mapper_supported_fields", []),
            )
        ),
        "field_policies": dict(
            run_config_options.get(
                "field_policies",
                runner_run_config.get("field_policies", {}),
            )
        ),
        "deprecated_fields": list(
            run_config_options.get(
                "deprecated_fields",
                runner_run_config.get("deprecated_fields", []),
            )
        ),
        "live_media_fields": list(
            run_config_options.get(
                "live_media_fields",
                runner_run_config.get("live_media_fields", []),
            )
        ),
        "legacy_input_fields": list(
            run_config_options.get(
                "legacy_input_fields",
                runner_run_config.get("legacy_input_fields", []),
            )
        ),
        "translated_fields": list(
            run_config_options.get(
                "translated_fields",
                runner_run_config.get("translated_fields", []),
            )
        ),
        "declared_fields": list(run_config_options.get("declared_fields", [])),
        "mapped_fields": list(run_config_options.get("mapped_fields", [])),
        "unmapped_fields": list(run_config_options.get("unmapped_fields", [])),
        "deferred_fields": list(run_config_options.get("deferred_fields", [])),
        "custom_metadata_keys": list(
            workflow_run_config.get(
                "custom_metadata_keys",
                runner_run_config.get("custom_metadata_keys", []),
            )
        ),
        "max_llm_calls": workflow_run_config.get(
            "max_llm_calls",
            runner_run_config.get("max_llm_calls"),
        ),
        "streaming_mode": workflow_run_config.get(
            "streaming_mode",
            runner_run_config.get("streaming_mode"),
        ),
        "adk_run_config_type": workflow_run_config.get(
            "adk_run_config_type",
            runner_run_config.get("adk_run_config_type"),
        ),
        "live_blob_save_requested": bool(
            workflow_run_config.get(
                "live_blob_save_requested",
                runner_run_config.get("live_blob_save_requested", False),
            )
        ),
        "live_audio_save_requested": bool(
            run_config_options.get(
                "live_audio_save_requested",
                workflow_run_config.get(
                    "live_audio_save_requested",
                    runner_run_config.get("live_audio_save_requested", False),
                ),
            )
        ),
    }


def _build_run_config_governance_view(
    run_config: dict[str, Any],
    *,
    evidence_id: str | None,
) -> RunConfigGovernanceView:
    return RunConfigGovernanceView(
        source="observability_hub.adk_workflow_runner_evidence.run_config",
        run_config_source=_plain_str(run_config.get("source")),
        adk_run_config_version=_plain_str(run_config.get("adk_run_config_version")),
        official_fields=_string_list(run_config.get("official_fields")),
        mapper_supported_fields=_string_list(run_config.get("mapper_supported_fields")),
        field_policies=_field_policy_mapping(run_config.get("field_policies")),
        deprecated_fields=_string_list(run_config.get("deprecated_fields")),
        live_media_fields=_string_list(run_config.get("live_media_fields")),
        legacy_input_fields=_string_list(run_config.get("legacy_input_fields")),
        translated_fields=_string_list(run_config.get("translated_fields")),
        declared_fields=_string_list(run_config.get("declared_fields")),
        mapped_fields=_string_list(run_config.get("mapped_fields")),
        unmapped_fields=_string_list(run_config.get("unmapped_fields")),
        deferred_fields=_string_list(run_config.get("deferred_fields")),
        custom_metadata_keys=_string_list(run_config.get("custom_metadata_keys")),
        max_llm_calls=_optional_int(run_config.get("max_llm_calls")),
        streaming_mode=_plain_str(run_config.get("streaming_mode")),
        adk_run_config_type=_plain_str(run_config.get("adk_run_config_type")),
        live_blob_save_requested=bool(run_config.get("live_blob_save_requested")),
        live_audio_save_requested=bool(run_config.get("live_audio_save_requested")),
        live_call_enabled=False,
        no_live_mode=True,
        call_attempted=False,
        metadata={
            "source_evidence_id": evidence_id,
            "sanitized": True,
            "source_summary_key": "run_config",
            "does_not_include_raw_run_config": True,
        },
    )


def _build_service_bundle_governance_view(
    service_bundle: dict[str, Any],
    *,
    service_bundle_options: dict[str, Any],
    evidence_id: str | None,
) -> ServiceBundleGovernanceView:
    artifact_service = _mapping(service_bundle.get("artifact_service"))
    session_service = _mapping(service_bundle.get("session_service"))
    service_bundle_source = _plain_str(service_bundle.get("source")) or _plain_str(
        service_bundle_options.get("source")
    )
    capability_flags = []
    if artifact_service:
        capability_flags.append("artifact_service_present")
    if session_service:
        capability_flags.append("session_service_present")
    return ServiceBundleGovernanceView(
        source="observability_hub.adk_workflow_runner_evidence.service_bundle",
        service_bundle_source=service_bundle_source,
        persistence_stage="runtime_fact_only",
        persistence_strategy=(
            "in_memory_or_provided_service_reference"
            if service_bundle_source in {"in_memory", "provided_services"}
            else "not_configured"
        ),
        external_persistence_enabled=False,
        artifact_service_present=bool(artifact_service),
        session_service_present=bool(session_service),
        artifact_service_type_name=_plain_str(artifact_service.get("adk_service_type")),
        session_service_type_name=_plain_str(session_service.get("adk_service_type")),
        artifact_service_source=_plain_str(
            service_bundle_options.get("artifact_service_source")
        ),
        session_service_source=_plain_str(
            service_bundle_options.get("session_service_source")
        ),
        capability_flags=capability_flags,
        metadata={
            "source_evidence_id": evidence_id,
            "sanitized": True,
            "source_summary_key": "service_bundle",
            "does_not_include_raw_service_bundle": True,
        },
    )


def _build_artifact_summary(artifacts: list[ArtifactDelta]) -> dict[str, Any]:
    artifact_ids = [artifact.artifact_ref.artifact_id for artifact in artifacts]
    artifact_names = [
        artifact.artifact_ref.name
        for artifact in artifacts
        if artifact.artifact_ref.name is not None
    ]
    versions = [
        artifact.metadata.get("raw_artifact_delta")
        for artifact in artifacts
        if isinstance(artifact.metadata.get("raw_artifact_delta"), int)
    ]
    operations = sorted({artifact.operation.value for artifact in artifacts})
    metadata_keys = sorted(
        {
            key
            for artifact in artifacts
            for key in artifact.metadata
            if isinstance(key, str)
        }
    )
    artifact_refs = [
        {
            "artifact_id": artifact.artifact_ref.artifact_id,
            "name": artifact.artifact_ref.name,
            "version": artifact.artifact_ref.version,
            "operation": artifact.operation.value,
            "artifact_source": _plain_str(artifact.artifact_ref.metadata.get("source")),
            "metadata_keys": sorted(
                key for key in artifact.metadata if isinstance(key, str)
            ),
        }
        for artifact in artifacts
    ]
    return {
        "source": "runtime_result.artifact_deltas or workflow_result.artifact_deltas",
        "artifact_count": len(artifacts),
        "artifact_ids": artifact_ids,
        "artifact_names": artifact_names,
        "versions": versions,
        "operations": operations,
        "metadata_keys": metadata_keys,
        "artifact_refs": artifact_refs,
        "artifact_sources": sorted(
            {
                str(source)
                for artifact in artifacts
                if (source := artifact.artifact_ref.metadata.get("source"))
            }
        ),
        "has_artifacts": bool(artifacts),
    }


def _build_session_summary(
    *,
    workflow_metadata: dict[str, Any],
    metadata_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    binding = _mapping(workflow_metadata.get("adk_invocation_binding"))
    return {
        "source": "workflow_result.metadata",
        "session_id": _first_non_empty(*metadata_sources, "session_id")
        or binding.get("session_id"),
        "app_name": _first_non_empty(*metadata_sources, "app_name") or binding.get("app_name"),
        "user_id": _first_non_empty(*metadata_sources, "user_id") or binding.get("user_id"),
        "event_count": workflow_metadata.get("event_count"),
        "adk_invocation_id": _first_non_empty(*metadata_sources, "adk_invocation_id")
        or binding.get("adk_invocation_id"),
        "requested_invocation_id": _first_non_empty(
            *metadata_sources,
            "requested_invocation_id",
        )
        or binding.get("requested_invocation_id"),
        "state_keys": _first_list(*metadata_sources, key="state_keys"),
        "metadata_keys": sorted(
            {
                key
                for source in metadata_sources
                for key in source
                if isinstance(key, str)
            }
        ),
    }


def _build_event_summary(events: list[RuntimeEvent]) -> dict[str, Any]:
    event_ids = sorted({event.event_id for event in events if event.event_id})
    node_paths = sorted(
        {
            event.metadata.get("node_path")
            for event in events
            if event.metadata.get("node_path")
        }
    )
    authors = sorted(
        {
            event.metadata.get("author")
            for event in events
            if event.metadata.get("author")
        }
    )
    branch_ids = sorted(
        {
            branch
            for event in events
            if (branch := event.metadata.get("branch"))
        }
    )
    state_delta_refs = sorted(
        {
            state_delta_ref
            for event in events
            for state_delta_ref in event.state_delta_refs
        }
    )
    artifact_delta_refs = sorted(
        {
            artifact_delta_ref
            for event in events
            for artifact_delta_ref in event.artifact_delta_refs
        }
    )
    state_delta_keys = sorted(
        {
            key
            for event in events
            for key in _state_delta_keys(event.payload.get("state_delta"))
        }
    )
    invocation_ids = sorted(
        {
            invocation_id
            for event in events
            if (invocation_id := event.metadata.get("adk_invocation_id"))
        }
    )
    metadata_keys = sorted(
        {
            key
            for event in events
            for key in event.metadata
            if isinstance(key, str)
        }
    )
    error_codes = sorted(
        {
            error_code
            for event in events
            if (error_code := event.metadata.get("error_code"))
        }
    )
    return {
        "source": "runtime_result.events or workflow_result.events",
        "event_count": len(events),
        "event_ids": event_ids,
        "event_types": sorted({event.event_type.value for event in events}),
        "node_paths": node_paths,
        "authors": authors,
        "branch_ids": branch_ids,
        "state_delta_refs": state_delta_refs,
        "artifact_delta_refs": artifact_delta_refs,
        "invocation_ids": invocation_ids,
        "state_delta_count": sum(
            _state_delta_count(event.payload.get("state_delta")) for event in events
        ),
        "state_delta_keys": state_delta_keys,
        "error_count": sum(
            1
            for event in events
            if event.metadata.get("error_code") or event.metadata.get("error_message")
        ),
        "error_codes": error_codes,
        "has_error": any(
            event.metadata.get("error_code") or event.metadata.get("error_message")
            for event in events
        ),
        "metadata_keys": metadata_keys,
    }


def _build_graph_summary(
    *,
    event_summary: dict[str, Any],
    workflow_id: str | None,
    workflow_name: str | None,
) -> dict[str, Any]:
    node_paths = _string_list(event_summary.get("node_paths"))
    branch_ids = _string_list(event_summary.get("branch_ids"))
    return {
        "source": "observability_hub.adk_workflow_runner_evidence.graph_summary",
        "workflow_id": workflow_id,
        "workflow_name": workflow_name,
        "node_paths": node_paths,
        "node_path_count": len(node_paths),
        "branch_ids": branch_ids,
        "has_branching": bool(branch_ids),
        "graph_inferred_from": [
            "event_summary.node_paths",
            "event_summary.branch_ids",
        ],
        "candidate_only": True,
        "summary_only": True,
        "refs_only": True,
        "raw_adk_object_included": False,
        "raw_graph_object_included": False,
    }


def _build_trace_summary(event_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "observability_hub.adk_workflow_runner_evidence.trace_summary",
        "event_count": _non_negative_int(event_summary.get("event_count")),
        "event_ids": _string_list(event_summary.get("event_ids")),
        "event_types": _string_list(event_summary.get("event_types")),
        "invocation_ids": _string_list(event_summary.get("invocation_ids")),
        "state_delta_refs": _string_list(event_summary.get("state_delta_refs")),
        "artifact_delta_refs": _string_list(event_summary.get("artifact_delta_refs")),
        "has_error": bool(event_summary.get("has_error")),
        "trace_inferred_from": [
            "event_summary.event_ids",
            "event_summary.event_types",
            "event_summary.invocation_ids",
            "event_summary.state_delta_refs",
            "event_summary.artifact_delta_refs",
        ],
        "candidate_only": True,
        "summary_only": True,
        "refs_only": True,
        "raw_event_included": False,
        "raw_payload_included": False,
    }


def _evidence_mapping(
    evidence: AdkWorkflowRunnerEvidence | dict[str, Any],
) -> dict[str, Any]:
    if isinstance(evidence, AdkWorkflowRunnerEvidence):
        return evidence.model_dump(mode="python")
    if isinstance(evidence, dict):
        return _sanitize(evidence)
    raise ObservabilityHubInputError(
        "build_adk_lifecycle_facts_summary expects an ADK workflow evidence mapping."
    )


def _build_invocation_ref(session_summary: dict[str, Any]) -> InvocationRef | None:
    invocation_id = _plain_str(session_summary.get("requested_invocation_id")) or _plain_str(
        session_summary.get("adk_invocation_id")
    )
    if invocation_id is None:
        return None
    return InvocationRef(
        invocation_id=invocation_id,
        source="observability_hub.adk_workflow_runner_evidence.lifecycle_summary",
        metadata={
            "session_id": _plain_str(session_summary.get("session_id")),
            "app_name": _plain_str(session_summary.get("app_name")),
            "user_id": _plain_str(session_summary.get("user_id")),
            "sanitized": True,
        },
    )


def _build_artifact_lifecycle_facts(
    artifact_summary: dict[str, Any],
    *,
    invocation_ref: InvocationRef | None,
    service_type_name: str | None,
) -> list[ArtifactLifecycleFacts]:
    artifact_refs = _list(artifact_summary.get("artifact_refs"))
    if artifact_refs:
        return [
            ArtifactLifecycleFacts(
                artifact_ref=ArtifactRef(
                artifact_id=_required_string(ref.get("artifact_id"), "artifact_id"),
                name=_plain_str(ref.get("name")),
                version=_optional_string(ref.get("version")),
            ),
            invocation_ref=invocation_ref,
            operation=_delta_operation(ref.get("operation")),
            version=_optional_string(ref.get("version")),
            artifact_source=_plain_str(ref.get("artifact_source")),
            service_type_name=service_type_name,
                source="observability_hub.adk_workflow_runner_evidence.artifact_summary",
                metadata_keys=_string_list(ref.get("metadata_keys")),
                metadata={"sanitized": True},
            )
            for ref in (_mapping(item) for item in artifact_refs)
        ]

    artifact_ids = _string_list(artifact_summary.get("artifact_ids"))
    artifact_names = _string_list(artifact_summary.get("artifact_names"))
    versions = _list(artifact_summary.get("versions"))
    operation = _delta_operation(_first_item(artifact_summary.get("operations")))
    return [
        ArtifactLifecycleFacts(
            artifact_ref=ArtifactRef(
                artifact_id=artifact_id,
                name=artifact_names[index] if index < len(artifact_names) else None,
                version=_optional_string(versions[index]) if index < len(versions) else None,
            ),
            invocation_ref=invocation_ref,
            operation=operation,
            version=_optional_string(versions[index]) if index < len(versions) else None,
            service_type_name=service_type_name,
            source="observability_hub.adk_workflow_runner_evidence.artifact_summary",
            metadata_keys=_string_list(artifact_summary.get("metadata_keys")),
            metadata={"sanitized": True},
        )
        for index, artifact_id in enumerate(artifact_ids)
    ]


def _build_session_lifecycle_facts(
    session_summary: dict[str, Any],
    *,
    invocation_ref: InvocationRef | None,
    service_type_name: str | None,
) -> SessionLifecycleFacts | None:
    if not session_summary:
        return None
    return SessionLifecycleFacts(
        session_id=_plain_str(session_summary.get("session_id")),
        app_name=_plain_str(session_summary.get("app_name")),
        user_id=_plain_str(session_summary.get("user_id")),
        invocation_ref=invocation_ref,
        event_count=_non_negative_int(session_summary.get("event_count")),
        has_state=bool(session_summary.get("state_keys")),
        state_keys=_string_list(session_summary.get("state_keys")),
        state_key_count=len(_string_list(session_summary.get("state_keys"))),
        service_type_name=service_type_name,
        source="observability_hub.adk_workflow_runner_evidence.session_summary",
        metadata_keys=_string_list(session_summary.get("metadata_keys")),
        metadata={"sanitized": True},
    )


def _build_event_lifecycle_facts(event_summary: dict[str, Any]) -> EventLifecycleFacts:
    return EventLifecycleFacts(
        event_count=_non_negative_int(event_summary.get("event_count")),
        event_ids=_string_list(event_summary.get("event_ids")),
        event_types=_string_list(event_summary.get("event_types")),
        authors=_string_list(event_summary.get("authors")),
        branch_ids=_string_list(event_summary.get("branch_ids")),
        node_paths=_string_list(event_summary.get("node_paths")),
        state_delta_refs=_string_list(event_summary.get("state_delta_refs")),
        artifact_delta_refs=_string_list(event_summary.get("artifact_delta_refs")),
        invocation_ids=_string_list(event_summary.get("invocation_ids")),
        state_delta_count=_non_negative_int(event_summary.get("state_delta_count")),
        state_delta_keys=_string_list(event_summary.get("state_delta_keys")),
        error_count=_non_negative_int(event_summary.get("error_count")),
        error_codes=_string_list(event_summary.get("error_codes")),
        has_error=bool(event_summary.get("has_error")),
        source="observability_hub.adk_workflow_runner_evidence.event_summary",
        metadata_keys=_string_list(event_summary.get("metadata_keys")),
        metadata={"sanitized": True},
    )


def _build_state_delta_summary(
    state_deltas: list[StateDelta],
    events: list[RuntimeEvent],
) -> dict[str, Any]:
    event_state_delta_count = sum(
        _state_delta_count(event.payload.get("state_delta")) for event in events
    )
    event_state_delta_keys = sorted(
        {
            key
            for event in events
            for key in _state_delta_keys(event.payload.get("state_delta"))
        }
    )
    if not state_deltas:
        return {
            "source": "runtime_result.events or workflow_result.events",
            "state_delta_entity_mode": "event_payload_summary_only",
            "state_delta_count": event_state_delta_count,
            "state_delta_refs": sorted(
                {
                    ref
                    for event in events
                    for ref in event.state_delta_refs
                    if ref
                }
            ),
            "state_delta_scopes": [],
            "state_delta_keys": event_state_delta_keys,
            "state_delta_operations": [],
            "raw_state_values_included": False,
            "metadata_keys": [],
        }

    return {
        "source": "runtime_result.state_deltas or workflow_result.state_deltas",
        "state_delta_entity_mode": "state_delta_contract_summary",
        "state_delta_count": len(state_deltas),
        "state_delta_refs": sorted(delta.delta_id for delta in state_deltas),
        "state_delta_scopes": sorted({delta.scope for delta in state_deltas}),
        "state_delta_keys": sorted({delta.key for delta in state_deltas}),
        "state_delta_operations": sorted(
            {delta.operation.value for delta in state_deltas}
        ),
        "raw_state_values_included": False,
        "metadata_keys": sorted(
            {
                key
                for delta in state_deltas
                for key in delta.metadata
                if isinstance(key, str)
            }
        ),
    }


def _build_context_state_lifecycle_facts(
    *,
    session_summary: dict[str, Any],
    event_summary: dict[str, Any],
    state_delta_summary: dict[str, Any],
    run_config: dict[str, Any],
    runtime_metadata: dict[str, Any],
) -> ContextStateLifecycleFacts:
    session_state_keys = _string_list(session_summary.get("state_keys"))
    state_delta_keys = _string_list(
        state_delta_summary.get("state_delta_keys")
    ) or _string_list(event_summary.get("state_delta_keys"))
    return ContextStateLifecycleFacts(
        source="observability_hub.adk_workflow_runner_evidence.context_state",
        has_session_state=bool(session_state_keys),
        session_state_keys=session_state_keys,
        session_state_key_count=len(session_state_keys),
        state_delta_refs=_string_list(state_delta_summary.get("state_delta_refs"))
        or _string_list(event_summary.get("state_delta_refs")),
        state_delta_scopes=_string_list(state_delta_summary.get("state_delta_scopes")),
        state_delta_operations=_string_list(
            state_delta_summary.get("state_delta_operations")
        ),
        state_delta_count=(
            _non_negative_int(state_delta_summary.get("state_delta_count"))
            or _non_negative_int(event_summary.get("state_delta_count"))
        ),
        state_delta_keys=state_delta_keys,
        state_delta_entity_mode=_plain_str(
            state_delta_summary.get("state_delta_entity_mode")
        )
        or "summary_only",
        raw_state_values_included=False,
        custom_metadata_keys=_string_list(run_config.get("custom_metadata_keys")),
        runtime_metadata_keys=sorted(
            key for key in runtime_metadata if isinstance(key, str)
        ),
        sanitized=True,
        metadata={
            "sanitized": True,
            "does_not_include_state_values": True,
            "does_not_include_runtime_payload": True,
        },
    )


def _state_delta_count(value: Any) -> int:
    if isinstance(value, dict):
        return len(value)
    if isinstance(value, list):
        return len(value)
    return 0


def _state_delta_keys(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [str(key) for key in value if key not in (None, "")]
    if isinstance(value, list):
        keys: list[str] = []
        for item in value:
            if isinstance(item, dict):
                key = item.get("key") or item.get("name")
                if key not in (None, ""):
                    keys.append(str(key))
        return keys
    return []


def _plain_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _required_string(value: Any, field_name: str) -> str:
    text = _optional_string(value)
    if text is None:
        raise ObservabilityHubInputError(f"{field_name} is required.")
    return text


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in _list(value) if item not in (None, "")]


def _field_policy_mapping(value: Any) -> dict[str, dict[str, str]]:
    if not isinstance(value, dict):
        return {}
    policies: dict[str, dict[str, str]] = {}
    for field_name, policy in value.items():
        if not isinstance(policy, dict):
            continue
        policies[str(field_name)] = {
            str(key): str(item)
            for key, item in policy.items()
            if item not in (None, "", [], {})
        }
    return policies


def _first_item(value: Any) -> Any | None:
    values = _list(value)
    return values[0] if values else None


def _non_negative_int(value: Any) -> int:
    if isinstance(value, int) and value >= 0:
        return value
    return 0


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _delta_operation(value: Any) -> DeltaOperation | None:
    if value is None:
        return None
    try:
        return DeltaOperation(str(value))
    except ValueError:
        return None


def _first_non_empty(*sources: dict[str, Any], key: str | None = None) -> Any:
    if key is not None:
        keys = [key]
        metadata_sources = list(sources)
    else:
        *metadata_sources, last = sources
        keys = [last] if isinstance(last, str) else []
    for source in metadata_sources:
        for candidate_key in keys:
            value = source.get(candidate_key)
            if value not in (None, "", [], {}):
                return value
    return None


def _first_list(*sources: dict[str, Any], key: str) -> list[Any]:
    value = _first_non_empty(*sources, key=key)
    return _list(value)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _sanitize(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return {"object_type": type(value).__name__, "object_module": type(value).__module__}
