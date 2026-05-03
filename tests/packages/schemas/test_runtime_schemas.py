import pytest
from pydantic import ValidationError

from schemas.runtime import (
    InvocationRef,
    RuntimeInput,
    RuntimeStatus,
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
