import pytest
from pydantic import ValidationError

from config_contexts.runtime import (
    AdapterSelectionConfigView,
    ExecutionMode,
    ResumePolicyConfigView,
    RuntimeConfigView,
)


def test_runtime_config_view_accepts_declared_fields() -> None:
    view = RuntimeConfigView(
        runtime_name="default-runtime",
        execution_mode=ExecutionMode.LOCAL,
        timeout_seconds=60,
    )

    assert view.runtime_name == "default-runtime"
    assert view.default_adapter == "local"
    assert view.timeout_seconds == 60


def test_adapter_selection_config_view_accepts_declared_fields() -> None:
    view = AdapterSelectionConfigView(
        default_runtime_adapter="adk",
        adk_adapter_enabled=True,
        fallback_adapter="local",
    )

    assert view.default_runtime_adapter == "adk"
    assert view.adk_adapter_enabled is True
    assert view.fallback_adapter == "local"


def test_runtime_config_view_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        RuntimeConfigView(runtime_name="default-runtime", unexpected=True)


def test_hitl_requires_resume() -> None:
    with pytest.raises(ValidationError):
        ResumePolicyConfigView(enable_hitl=True, enable_resume=False)
