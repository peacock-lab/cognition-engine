"""Thin facade package for Cognition Engine runtime-container entries."""

from importlib import import_module
from types import ModuleType

__all__ = [
    "cli_agent_workflow_admission",
    "cli_agent_workflow_registry_observation",
    "cli_reference_review_workflow",
    "cli_task_control",
    "cli_reference_reader",
    "cli_run_workspace",
    "cli_skill_capability_projection",
    "cli_skill_registry_admission",
    "cli_task_workflow_registry",
    "cli_tool_loading_validation",
    "cli_tool_exposure_profile",
    "cli_toolset_admission",
    "controlled_adk_run_entry",
    "controlled_run_facade",
    "governance_summary_pipeline",
    "llm_invocation_facade",
    "runtime",
]

_EXPORTED_SUBMODULES = frozenset(__all__)


def __getattr__(name: str) -> ModuleType:
    if name in _EXPORTED_SUBMODULES:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | _EXPORTED_SUBMODULES)
