from behavior_contracts.runtime import WorkflowRunner
from config_assembly.runtime import RuntimeConfigPayload
from config_contexts.runtime import AdapterSelectionConfigView, RuntimeConfigContextBundle
from schemas.runtime import RuntimeInput, RuntimeResult, RuntimeStatus, WorkflowInput, WorkflowResult

from contract_core import runtime


def test_runtime_facade_reexports_first_batch_runtime_contracts() -> None:
    assert runtime.WorkflowRunner is WorkflowRunner
    assert runtime.RuntimeStatus is RuntimeStatus
    assert runtime.WorkflowInput is WorkflowInput
    assert runtime.WorkflowResult is WorkflowResult
    assert runtime.RuntimeInput is RuntimeInput
    assert runtime.RuntimeResult is RuntimeResult
    assert runtime.RuntimeConfigContextBundle is RuntimeConfigContextBundle
    assert runtime.AdapterSelectionConfigView is AdapterSelectionConfigView
    assert runtime.RuntimeConfigPayload is RuntimeConfigPayload


def test_runtime_facade_exports_are_explicit() -> None:
    expected_exports = {
        "WorkflowRunner",
        "RuntimeStatus",
        "WorkflowInput",
        "WorkflowResult",
        "RuntimeInput",
        "RuntimeResult",
        "RuntimeConfigContextBundle",
        "AdapterSelectionConfigView",
        "RuntimeConfigPayload",
    }

    assert expected_exports <= set(runtime.__all__)
