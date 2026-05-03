from behavior_contracts.runtime import RuntimeRunner
from schemas.runtime import InvocationRef, RuntimeInput, RuntimeResult, RuntimeStatus, WorkflowRef


class FakeRuntimeRunner:
    def run(self, runtime_input: RuntimeInput) -> RuntimeResult:
        return RuntimeResult(
            runtime_id=runtime_input.runtime_id,
            status=RuntimeStatus.SUCCESS,
            invocation_ref=runtime_input.invocation_ref,
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
