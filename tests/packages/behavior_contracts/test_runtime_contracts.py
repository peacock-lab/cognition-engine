from behavior_contracts.runtime import RecordedRunEvidenceProvider, RuntimeRunner
from schemas.runtime import (
    AdkLifecycleFactsSummary,
    AdkRunConfigServiceBundleSummary,
    AdkServiceFactsSummaryInput,
    EventLifecycleFacts,
    InvocationRef,
    RecordedRunEvidenceInput,
    RuntimeInput,
    RuntimeResult,
    RuntimeStatus,
    WorkflowRef,
)


class FakeRuntimeRunner:
    def run(self, runtime_input: RuntimeInput) -> RuntimeResult:
        return RuntimeResult(
            runtime_id=runtime_input.runtime_id,
            status=RuntimeStatus.SUCCESS,
            invocation_ref=runtime_input.invocation_ref,
        )


class FakeRecordedRunEvidenceProvider:
    def build_recorded_run_evidence(
        self, runtime_result: RuntimeResult
    ) -> RecordedRunEvidenceInput:
        return RecordedRunEvidenceInput(
            recorded_run_id=runtime_result.runtime_id,
            adk_service_facts=AdkServiceFactsSummaryInput(
                lifecycle_summary=AdkLifecycleFactsSummary(
                    summary_id="lifecycle-summary-147",
                    events=EventLifecycleFacts(),
                ),
                run_config_service_bundle_summary=AdkRunConfigServiceBundleSummary(
                    summary_id="run-config-service-bundle-summary-147",
                ),
            ),
        )


def test_fake_runtime_runner_satisfies_runtime_contract() -> None:
    runner: RuntimeRunner = FakeRuntimeRunner()
    runtime_input = RuntimeInput(
        runtime_id="rt-1",
        workflow_ref=WorkflowRef(workflow_id="wf-1"),
        invocation_ref=InvocationRef(invocation_id="inv-1"),
    )

    result = runner.run(runtime_input)

    assert result.status == RuntimeStatus.SUCCESS
    assert result.runtime_id == "rt-1"


def test_recorded_run_evidence_provider_satisfies_runtime_contract() -> None:
    provider: RecordedRunEvidenceProvider = FakeRecordedRunEvidenceProvider()
    evidence = provider.build_recorded_run_evidence(
        RuntimeResult(
            runtime_id="runtime-147",
            status=RuntimeStatus.SUCCESS,
            invocation_ref=InvocationRef(invocation_id="inv-147"),
        )
    )

    assert evidence.recorded_run_id == "runtime-147"
    assert evidence.does_not_execute_recorded_run is True
