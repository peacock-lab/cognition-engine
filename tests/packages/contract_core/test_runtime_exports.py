from behavior_contracts.runtime import (
    AdkServiceFactsProvider,
    RecordedRunEvidenceProvider,
    WorkflowRunner,
)
from config_contexts.runtime import (
    AdapterSelectionConfigView,
    AdkRunConfigView,
    RuntimeConfigContextBundle,
    RuntimeLiveLlmConfigView,
    RuntimeProductizationGateConfigView,
    SessionPolicyConfigView,
)
from schemas.runtime import (
    AdkLifecycleFactsSummary,
    AdkRunConfigServiceBundleSummary,
    AdkServiceFactsSummaryInput,
    ArtifactLifecycleFacts,
    ContextStateLifecycleFacts,
    EventLifecycleFacts,
    RecordedRunEvidenceInput,
    RuntimeInput,
    RuntimeProductizationGateEvaluationFacts,
    RuntimeResult,
    RuntimeStatus,
    RunConfigGovernanceView,
    SessionLifecycleFacts,
    ServiceBundleGovernanceView,
    WorkflowInput,
    WorkflowResult,
)

from contract_core import runtime


def test_runtime_facade_reexports_first_batch_runtime_contracts() -> None:
    assert runtime.WorkflowRunner is WorkflowRunner
    assert runtime.RuntimeStatus is RuntimeStatus
    assert runtime.WorkflowInput is WorkflowInput
    assert runtime.WorkflowResult is WorkflowResult
    assert runtime.RuntimeInput is RuntimeInput
    assert runtime.RuntimeResult is RuntimeResult
    assert runtime.AdkLifecycleFactsSummary is AdkLifecycleFactsSummary
    assert runtime.AdkRunConfigServiceBundleSummary is AdkRunConfigServiceBundleSummary
    assert runtime.ArtifactLifecycleFacts is ArtifactLifecycleFacts
    assert runtime.ContextStateLifecycleFacts is ContextStateLifecycleFacts
    assert runtime.SessionLifecycleFacts is SessionLifecycleFacts
    assert runtime.EventLifecycleFacts is EventLifecycleFacts
    assert runtime.RunConfigGovernanceView is RunConfigGovernanceView
    assert runtime.ServiceBundleGovernanceView is ServiceBundleGovernanceView
    assert runtime.RuntimeConfigContextBundle is RuntimeConfigContextBundle
    assert runtime.AdapterSelectionConfigView is AdapterSelectionConfigView
    assert runtime.AdkRunConfigView is AdkRunConfigView
    assert runtime.RuntimeLiveLlmConfigView is RuntimeLiveLlmConfigView
    assert runtime.RuntimeProductizationGateConfigView is (
        RuntimeProductizationGateConfigView
    )
    assert runtime.SessionPolicyConfigView is SessionPolicyConfigView
    assert runtime.RuntimeProductizationGateEvaluationFacts is (
        RuntimeProductizationGateEvaluationFacts
    )
    assert runtime.AdkServiceFactsSummaryInput is AdkServiceFactsSummaryInput
    assert runtime.RecordedRunEvidenceInput is RecordedRunEvidenceInput
    assert runtime.AdkServiceFactsProvider is AdkServiceFactsProvider
    assert runtime.RecordedRunEvidenceProvider is RecordedRunEvidenceProvider


def test_runtime_facade_exports_are_explicit() -> None:
    expected_exports = {
        "WorkflowRunner",
        "RuntimeStatus",
        "WorkflowInput",
        "WorkflowResult",
        "RuntimeInput",
        "RuntimeResult",
        "AdkLifecycleFactsSummary",
        "AdkRunConfigServiceBundleSummary",
        "ArtifactLifecycleFacts",
        "ContextStateLifecycleFacts",
        "SessionLifecycleFacts",
        "EventLifecycleFacts",
        "RunConfigGovernanceView",
        "ServiceBundleGovernanceView",
        "RuntimeConfigContextBundle",
        "AdapterSelectionConfigView",
        "AdkRunConfigView",
        "RuntimeLiveLlmConfigView",
        "RuntimeProductizationGateConfigView",
        "SessionPolicyConfigView",
        "RuntimeProductizationGateEvaluationFacts",
        "AdkServiceFactsSummaryInput",
        "AdkServiceFactsProvider",
        "RecordedRunEvidenceInput",
        "RecordedRunEvidenceProvider",
    }

    assert expected_exports <= set(runtime.__all__)
