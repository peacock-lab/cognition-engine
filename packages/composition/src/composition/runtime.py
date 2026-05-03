"""Runtime composition root for Cognition Engine."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from behavior_contracts.runtime import (
    InvocationTracker,
    RuntimeEventPublisher,
    WorkflowRunner,
)
from config_assembly.runtime import assemble_runtime_config_payload
from config_contexts.runtime import RuntimeConfigContextBundle
from config_contexts.runtime_builder import build_runtime_config_contexts
from runtime.orchestrator import RuntimeDependencies, StandardRuntimeRunner


@dataclass(frozen=True)
class RuntimeCompositionOptions:
    """Options for composing a standard runtime runner."""

    config_root: Path
    environment: str = "local"


def build_runtime_config_context(
    options: RuntimeCompositionOptions,
) -> RuntimeConfigContextBundle:
    """Build runtime configuration context bundle from project config."""

    payload = assemble_runtime_config_payload(
        options.config_root,
        environment=options.environment,
    )

    return build_runtime_config_contexts(payload)


def build_standard_runtime_runner(
    *,
    options: RuntimeCompositionOptions,
    workflow_runner: WorkflowRunner,
    invocation_tracker: InvocationTracker | None = None,
    event_publisher: RuntimeEventPublisher | None = None,
) -> StandardRuntimeRunner:
    """Build a StandardRuntimeRunner from config and injected dependencies."""

    config_context = build_runtime_config_context(options)

    return StandardRuntimeRunner(
        config_context=config_context,
        dependencies=RuntimeDependencies(
            workflow_runner=workflow_runner,
            invocation_tracker=invocation_tracker,
            event_publisher=event_publisher,
        ),
    )
