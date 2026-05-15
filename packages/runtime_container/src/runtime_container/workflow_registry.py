"""Workflow registry for productized controlled-run request construction."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class WorkflowRegistryError(ValueError):
    """Base error for controlled-run workflow registry lookup."""


class WorkflowRegistryEntryNotFound(WorkflowRegistryError):
    """Raised when a requested workflow is not registered."""


class WorkflowRegistryAssemblyUnavailable(WorkflowRegistryError):
    """Raised when a workflow has no runtime assembly provider."""


@dataclass(frozen=True)
class WorkflowRegistryBuildContext:
    """Inputs a workflow assembly provider may need to build an assembly."""

    config_root: Path
    environment: str
    profile: str | None
    runtime_id: str
    workflow_id: str
    workflow_name: str
    input_payload: Mapping[str, Any] = field(default_factory=dict)


RuntimeAssemblyProvider = Callable[[WorkflowRegistryBuildContext], Any]


@dataclass(frozen=True)
class WorkflowRegistryEntry:
    """Registered workflow selection metadata for controlled runs."""

    workflow_id: str
    workflow_name: str
    description: str
    runtime_assembly_provider: RuntimeAssemblyProvider | None = None
    no_live_default: bool = True
    live_llm_allowed: bool = False
    ollama_allowed: bool = False
    external_persistence_enabled: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def matches(self, *, workflow_id: str | None, workflow_name: str | None) -> bool:
        """Return whether this entry matches the requested identity."""

        return (
            bool(workflow_id and workflow_id == self.workflow_id)
            or bool(workflow_name and workflow_name == self.workflow_name)
        )


class WorkflowRegistry:
    """Select workflow builders without executing runtime work."""

    def __init__(
        self,
        entries: list[WorkflowRegistryEntry] | tuple[WorkflowRegistryEntry, ...],
    ) -> None:
        self._entries_by_id = {entry.workflow_id: entry for entry in entries}
        self._entries_by_name = {entry.workflow_name: entry for entry in entries}

    def resolve(
        self,
        *,
        workflow_id: str | None = None,
        workflow_name: str | None = None,
    ) -> WorkflowRegistryEntry:
        """Resolve a workflow by id, name, or the default controlled workflow."""

        if workflow_id and workflow_id in self._entries_by_id:
            return self._entries_by_id[workflow_id]
        if workflow_name and workflow_name in self._entries_by_name:
            return self._entries_by_name[workflow_name]
        if workflow_id is None and workflow_name is None:
            return self.default_entry()
        requested = workflow_id or workflow_name or "<unspecified>"
        raise WorkflowRegistryEntryNotFound(
            f"controlled-run workflow is not registered: {requested}"
        )

    def default_entry(self) -> WorkflowRegistryEntry:
        """Return the first registered workflow."""

        try:
            return next(iter(self._entries_by_id.values()))
        except StopIteration as exc:  # pragma: no cover - defensive guard.
            raise WorkflowRegistryEntryNotFound(
                "controlled-run workflow registry is empty"
            ) from exc

    def build_runtime_assembly(
        self,
        entry: WorkflowRegistryEntry,
        context: WorkflowRegistryBuildContext,
    ) -> Any:
        """Build a runtime assembly through the entry provider without executing it."""

        if entry.runtime_assembly_provider is None:
            raise WorkflowRegistryAssemblyUnavailable(
                "controlled-run workflow registry entry has no runtime assembly "
                f"provider: {entry.workflow_name}"
            )
        return entry.runtime_assembly_provider(context)

    def entries(self) -> list[WorkflowRegistryEntry]:
        """Return registered entries for inspection."""

        return list(self._entries_by_id.values())


def build_default_workflow_registry(
    *,
    runtime_assembly_provider: RuntimeAssemblyProvider | None = None,
) -> WorkflowRegistry:
    """Build the first-version controlled-run workflow registry."""

    provider_boundary = (
        "composition_no_live_runtime_assembly_provider"
        if runtime_assembly_provider is not None
        else "runtime_assembly_provider_required"
    )
    return WorkflowRegistry(
        entries=[
            WorkflowRegistryEntry(
                workflow_id="workflow-controlled-adk-run",
                workflow_name="controlled-adk-run",
                description="First-version controlled no-live ADK run workflow.",
                runtime_assembly_provider=runtime_assembly_provider,
                metadata={
                    "source": "runtime_container.workflow_registry",
                    "provider_boundary": provider_boundary,
                    "does_not_execute_runtime": True,
                    "does_not_call_adk_runner": True,
                    "does_not_call_live_llm": True,
                },
            )
        ]
    )
