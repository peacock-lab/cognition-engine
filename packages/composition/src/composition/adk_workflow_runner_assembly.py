"""Composition entries for ADK2 WorkflowRunner service chains."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from adk_adapter import (
    AdkPluginBundle,
    AdkPluginBundleOptions,
    AdkRunConfigOptions,
    AdkRunnerServiceAdapter,
    AdkRunnerServiceBundle,
    AdkRunnerServiceBundleOptions,
    AdkWorkflowRunner,
    AdkWorkflowServiceAdapter,
)
from config_contexts.runtime import RuntimeConfigContextBundle
from contract_core.runtime import AdkServiceFactsProvider, RecordedRunEvidenceProvider
from observability_hub import (
    create_adk_workflow_runner_adk_service_facts_provider,
    create_adk_workflow_runner_recorded_run_evidence_provider,
)
from runtime.orchestrator import StandardRuntimeRunner

from composition.runtime import (
    RuntimeCompositionOptions,
    build_runtime_config_context,
    build_standard_runtime_runner,
)

GOVERNANCE_DECISION_SHAPE_FIELDS = ("decision", "metadata")
GOVERNANCE_DECISION_METADATA_PRECONDITION_FIELD = (
    "composition_precondition_allowed"
)
GOVERNANCE_DECISION_METADATA_BLOCK_FIELD = "block_on_violation"


@dataclass(frozen=True)
class AdkWorkflowRunnerAssemblyOptions:
    """Local composition options for ADK2 WorkflowRunner assembly."""

    app_name: str = "cognition_engine_adk_adapter"
    user_id: str = "cognition-engine-adk-user"
    workflow_name: str | None = None
    service_bundle_options: AdkRunnerServiceBundleOptions = field(
        default_factory=AdkRunnerServiceBundleOptions
    )
    plugin_bundle_options: AdkPluginBundleOptions = field(
        default_factory=AdkPluginBundleOptions
    )
    run_config_options: AdkRunConfigOptions | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        """Return options metadata for later observability intake."""

        return {
            "options_type": "composition.adk_workflow_runner_assembly."
            "AdkWorkflowRunnerAssemblyOptions",
            "app_name": self.app_name,
            "user_id": self.user_id,
            "workflow_name": self.workflow_name,
            "service_bundle_options": self.service_bundle_options.metadata(),
            "plugin_bundle_options": self.plugin_bundle_options.metadata(),
            "run_config_options": (
                self.run_config_options.to_metadata()
                if self.run_config_options is not None
                else None
            ),
            "metadata_keys": sorted(self.metadata),
        }


@dataclass(frozen=True)
class AdkWorkflowRunnerAssembly:
    """Assemble an ADK2 WorkflowRunner with injectable ADK services."""

    workflow: Any
    app_name: str = "cognition_engine_adk_adapter"
    user_id: str = "cognition-engine-adk-user"
    service_bundle: AdkRunnerServiceBundle | None = None
    service_bundle_options: AdkRunnerServiceBundleOptions | None = None
    plugin_bundle: AdkPluginBundle | None = None
    plugin_bundle_options: AdkPluginBundleOptions | None = None
    run_config_options: AdkRunConfigOptions | None = None
    assembly_options: AdkWorkflowRunnerAssemblyOptions | None = None

    def build_service_bundle(self) -> AdkRunnerServiceBundle:
        """Return the provided or default in-memory ADK service bundle."""

        options = self.options()
        return self.service_bundle or options.service_bundle_options.build_service_bundle(
            app_name=options.app_name,
            user_id=options.user_id,
        )

    def build_plugin_bundle(self) -> AdkPluginBundle:
        """Return the provided or default empty ADK plugin bundle."""

        options = self.options()
        return self.plugin_bundle or options.plugin_bundle_options.build_plugin_bundle()

    def build_workflow_service(self) -> AdkWorkflowServiceAdapter:
        """Build the workflow service adapter over the ADK graph workflow."""

        options = self.options()
        runner_service = AdkRunnerServiceAdapter(
            workflow=self.workflow,
            app_name=options.app_name,
            user_id=options.user_id,
            service_bundle=self.build_service_bundle(),
            run_config_options=options.run_config_options,
            plugin_bundle=self.build_plugin_bundle(),
        )
        return AdkWorkflowServiceAdapter(
            workflow=self.workflow,
            runner_service=runner_service,
            app_name=options.app_name,
            user_id=options.user_id,
        )

    def build_workflow_runner(self) -> AdkWorkflowRunner:
        """Build an AdkWorkflowRunner backed by the service injection chain."""

        return AdkWorkflowRunner(
            workflow=self.workflow,
            app_name=self.options().app_name,
            user_id=self.options().user_id,
            workflow_service=self.build_workflow_service(),
        )

    def metadata(self) -> dict[str, Any]:
        """Return assembly metadata for later observability intake."""

        service_bundle = self.build_service_bundle()
        options = self.options()
        return {
            "assembly": "composition.adk_workflow_runner_assembly",
            "workflow_type": type(self.workflow).__name__,
            "workflow_name": options.workflow_name or getattr(self.workflow, "name", None),
            "app_name": options.app_name,
            "user_id": options.user_id,
            "service_bundle": service_bundle.metadata(),
            "plugin_bundle": self.build_plugin_bundle().metadata(),
            "assembly_options": options.to_metadata(),
            "metadata": dict(options.metadata),
            "observability_candidate": "observability_hub.adk_workflow_runner_intake",
        }

    def options(self) -> AdkWorkflowRunnerAssemblyOptions:
        """Resolve explicit assembly options from legacy constructor arguments."""

        if self.assembly_options is not None:
            return self.assembly_options
        return AdkWorkflowRunnerAssemblyOptions(
            app_name=self.app_name,
            user_id=self.user_id,
            workflow_name=getattr(self.workflow, "name", None),
            service_bundle_options=self.service_bundle_options
            or AdkRunnerServiceBundleOptions(),
            plugin_bundle_options=self.plugin_bundle_options
            or AdkPluginBundleOptions(),
            run_config_options=self.run_config_options,
        )


@dataclass(frozen=True)
class AdkWorkflowRunnerRuntimeAssembly:
    """Runtime-container-facing holder for an assembled ADK workflow runner."""

    runtime_runner: StandardRuntimeRunner
    workflow_runner: AdkWorkflowRunner
    service_bundle: AdkRunnerServiceBundle
    assembly_options: AdkWorkflowRunnerAssemblyOptions
    metadata: dict[str, Any]


@dataclass(frozen=True)
class AdkWorkflowRunnerGovernanceSummaryProviderAssembly:
    """Governance summary provider assembly for ADK WorkflowRunner facts."""

    recorded_run_evidence_provider: RecordedRunEvidenceProvider
    assembly_metadata: dict[str, Any]
    evidence_bundle_ref: str | None = None
    source: str = (
        "composition.adk_workflow_runner_assembly."
        "AdkWorkflowRunnerGovernanceSummaryProviderAssembly"
    )


@dataclass(frozen=True)
class AdkWorkflowRunnerServiceFactsProviderAssembly:
    """Service facts provider assembly for ADK WorkflowRunner facts."""

    adk_service_facts_provider: AdkServiceFactsProvider
    assembly_metadata: dict[str, Any]
    source: str = (
        "composition.adk_workflow_runner_assembly."
        "AdkWorkflowRunnerServiceFactsProviderAssembly"
    )


@dataclass(frozen=True)
class GovernanceAssemblyPrecondition:
    """Composition-local view of the stable governance decision shape."""

    allowed: bool
    reason: str
    decision: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        """Return serializable precondition metadata."""

        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "decision": self.decision,
            "metadata": dict(self.metadata),
        }


def evaluate_governance_assembly_precondition(
    governance_decision: Any | None,
) -> GovernanceAssemblyPrecondition:
    """Evaluate an optional governance decision shape before assembly proceeds."""

    if governance_decision is None:
        return GovernanceAssemblyPrecondition(
            allowed=True,
            reason="governance_decision_not_provided",
        )

    decision = _read_governance_field(governance_decision, "decision", None)
    metadata = _read_governance_field(governance_decision, "metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    if metadata.get(GOVERNANCE_DECISION_METADATA_PRECONDITION_FIELD) is False:
        return GovernanceAssemblyPrecondition(
            allowed=False,
            reason="governance_decision_precondition_denied",
            decision=str(decision),
            metadata=metadata,
        )
    if decision == "block":
        return GovernanceAssemblyPrecondition(
            allowed=False,
            reason="governance_decision_blocked",
            decision=str(decision),
            metadata=metadata,
        )
    if (
        decision == "need_evidence"
        and metadata.get(GOVERNANCE_DECISION_METADATA_BLOCK_FIELD) is True
    ):
        return GovernanceAssemblyPrecondition(
            allowed=False,
            reason="governance_decision_requires_evidence",
            decision=str(decision),
            metadata=metadata,
        )

    return GovernanceAssemblyPrecondition(
        allowed=True,
        reason="governance_decision_allowed",
        decision=str(decision),
        metadata=metadata,
    )


def create_default_adk_workflow_runner_bundle(
    *,
    app_name: str = "cognition_engine_adk_adapter",
    user_id: str = "cognition-engine-adk-user",
    service_bundle_options: AdkRunnerServiceBundleOptions | None = None,
) -> AdkRunnerServiceBundle:
    """Create the default ADK service bundle used by composition."""

    options = service_bundle_options or AdkRunnerServiceBundleOptions()
    return options.build_service_bundle(app_name=app_name, user_id=user_id)


def create_adk_workflow_runner(
    *,
    workflow: Any,
    app_name: str = "cognition_engine_adk_adapter",
    user_id: str = "cognition-engine-adk-user",
    service_bundle: AdkRunnerServiceBundle | None = None,
    assembly_options: AdkWorkflowRunnerAssemblyOptions | None = None,
    service_bundle_options: AdkRunnerServiceBundleOptions | None = None,
    plugin_bundle: AdkPluginBundle | None = None,
    plugin_bundle_options: AdkPluginBundleOptions | None = None,
    run_config_options: AdkRunConfigOptions | None = None,
) -> AdkWorkflowRunner:
    """Create an AdkWorkflowRunner through the composition assembly path."""

    return AdkWorkflowRunnerAssembly(
        workflow=workflow,
        app_name=app_name,
        user_id=user_id,
        service_bundle=service_bundle,
        assembly_options=assembly_options,
        service_bundle_options=service_bundle_options,
        plugin_bundle=plugin_bundle,
        plugin_bundle_options=plugin_bundle_options,
        run_config_options=run_config_options,
    ).build_workflow_runner()


def build_adk_run_config_options_from_runtime_config(
    config_context: RuntimeConfigContextBundle,
) -> AdkRunConfigOptions | None:
    """Map runtime configuration context to local ADK RunConfig options."""

    view = config_context.adk_run_config
    options = AdkRunConfigOptions(
        speech_config=view.speech_config,
        max_llm_calls=view.max_llm_calls,
        custom_metadata=dict(view.custom_metadata),
        response_modalities=view.response_modalities,
        avatar_config=view.avatar_config,
        support_cfc=view.support_cfc,
        streaming_mode=view.streaming_mode,
        output_audio_transcription=view.output_audio_transcription,
        input_audio_transcription=view.input_audio_transcription,
        realtime_input_config=view.realtime_input_config,
        enable_affective_dialog=view.enable_affective_dialog,
        proactivity=view.proactivity,
        session_resumption=view.session_resumption,
        context_window_compression=view.context_window_compression,
        save_live_blob=view.save_live_blob,
        tool_thread_pool_config=view.tool_thread_pool_config,
        save_live_audio=view.save_live_audio,
        get_session_num_recent_events=view.get_session_num_recent_events,
        get_session_after_timestamp=view.get_session_after_timestamp,
    )

    if not options.declared_fields():
        return None
    return options


def build_adk_workflow_runner_runtime(
    *,
    options: RuntimeCompositionOptions,
    workflow: Any,
    app_name: str = "cognition_engine_adk_adapter",
    user_id: str = "cognition-engine-adk-user",
    service_bundle: AdkRunnerServiceBundle | None = None,
    assembly_options: AdkWorkflowRunnerAssemblyOptions | None = None,
    service_bundle_options: AdkRunnerServiceBundleOptions | None = None,
    plugin_bundle: AdkPluginBundle | None = None,
    plugin_bundle_options: AdkPluginBundleOptions | None = None,
    run_config_options: AdkRunConfigOptions | None = None,
    governance_decision: Any | None = None,
) -> AdkWorkflowRunnerRuntimeAssembly:
    """Build a StandardRuntimeRunner around an ADK2 WorkflowRunner service chain."""

    governance_precondition = evaluate_governance_assembly_precondition(
        governance_decision
    )
    if not governance_precondition.allowed:
        raise ValueError(
            "Governance precondition denied ADK workflow runner assembly: "
            f"{governance_precondition.reason}"
        )

    config_context = build_runtime_config_context(options)
    config_run_config_options = build_adk_run_config_options_from_runtime_config(
        config_context
    )
    if assembly_options is not None:
        resolved_options = assembly_options
        if run_config_options is not None:
            resolved_options = replace(
                resolved_options,
                run_config_options=run_config_options,
            )
        elif resolved_options.run_config_options is None:
            resolved_options = replace(
                resolved_options,
                run_config_options=config_run_config_options,
            )
        if plugin_bundle_options is not None:
            resolved_options = replace(
                resolved_options,
                plugin_bundle_options=plugin_bundle_options,
            )
    else:
        resolved_options = AdkWorkflowRunnerAssemblyOptions(
            app_name=app_name,
            user_id=user_id,
            workflow_name=getattr(workflow, "name", None),
            service_bundle_options=service_bundle_options
            or AdkRunnerServiceBundleOptions(),
            plugin_bundle_options=plugin_bundle_options or AdkPluginBundleOptions(),
            run_config_options=run_config_options or config_run_config_options,
        )
    bundle = service_bundle or create_default_adk_workflow_runner_bundle(
        app_name=resolved_options.app_name,
        user_id=resolved_options.user_id,
        service_bundle_options=resolved_options.service_bundle_options,
    )
    assembly = AdkWorkflowRunnerAssembly(
        workflow=workflow,
        app_name=resolved_options.app_name,
        user_id=resolved_options.user_id,
        service_bundle=bundle,
        plugin_bundle=plugin_bundle,
        assembly_options=resolved_options,
    )
    workflow_runner = assembly.build_workflow_runner()
    runtime_runner = build_standard_runtime_runner(
        options=options,
        workflow_runner=workflow_runner,
        config_context=config_context,
    )
    return AdkWorkflowRunnerRuntimeAssembly(
        runtime_runner=runtime_runner,
        workflow_runner=workflow_runner,
        service_bundle=bundle,
        assembly_options=resolved_options,
        metadata={
            **assembly.metadata(),
            "governance_precondition": governance_precondition.to_metadata(),
        },
    )


def build_adk_workflow_runner_governance_summary_provider(
    *,
    runtime_assembly: AdkWorkflowRunnerRuntimeAssembly,
    evidence_bundle_ref: str | None = None,
) -> AdkWorkflowRunnerGovernanceSummaryProviderAssembly:
    """Build a RecordedRunEvidenceProvider from ADK runtime assembly metadata."""

    assembly_metadata = dict(runtime_assembly.metadata)
    return AdkWorkflowRunnerGovernanceSummaryProviderAssembly(
        recorded_run_evidence_provider=(
            create_adk_workflow_runner_recorded_run_evidence_provider(
                assembly_metadata=assembly_metadata,
                evidence_bundle_ref=evidence_bundle_ref,
            )
        ),
        assembly_metadata=assembly_metadata,
        evidence_bundle_ref=evidence_bundle_ref,
    )


def build_adk_workflow_runner_service_facts_provider(
    *,
    runtime_assembly: AdkWorkflowRunnerRuntimeAssembly,
) -> AdkWorkflowRunnerServiceFactsProviderAssembly:
    """Build an AdkServiceFactsProvider from ADK runtime assembly metadata."""

    assembly_metadata = dict(runtime_assembly.metadata)
    return AdkWorkflowRunnerServiceFactsProviderAssembly(
        adk_service_facts_provider=(
            create_adk_workflow_runner_adk_service_facts_provider(
                assembly_metadata=assembly_metadata,
            )
        ),
        assembly_metadata=assembly_metadata,
    )


def _read_governance_field(source: Any, key: str, default: Any) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    if hasattr(source, "model_dump"):
        dumped = source.model_dump()
        if isinstance(dumped, dict):
            return dumped.get(key, default)
    return getattr(source, key, default)
