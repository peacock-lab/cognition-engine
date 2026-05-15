"""Production no-live runtime assembly provider for controlled ADK runs."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from adk_adapter import AdkRunConfigOptions, AdkRunnerServiceBundleOptions

from composition.adk_workflow_runner_assembly import (
    AdkWorkflowRunnerAssemblyOptions,
    AdkWorkflowRunnerRuntimeAssembly,
    build_adk_workflow_runner_runtime,
)
from composition.runtime import RuntimeCompositionOptions


ControlledAdkRunRuntimeAssemblyProvider = Callable[
    [Any], AdkWorkflowRunnerRuntimeAssembly
]


def build_controlled_adk_run_runtime_assembly_provider(
    *,
    app_name: str = "cognition_engine_controlled_adk_run",
    user_id: str = "cognition-engine-controlled-run-user",
) -> ControlledAdkRunRuntimeAssemblyProvider:
    """Build a provider callable for the production controlled no-live workflow."""

    def provider(context: Any) -> AdkWorkflowRunnerRuntimeAssembly:
        return build_controlled_adk_run_runtime_assembly(
            context,
            app_name=app_name,
            user_id=user_id,
        )

    return provider


def build_controlled_adk_run_runtime_assembly(
    context: Any,
    *,
    app_name: str = "cognition_engine_controlled_adk_run",
    user_id: str = "cognition-engine-controlled-run-user",
) -> AdkWorkflowRunnerRuntimeAssembly:
    """Build the no-live runtime assembly through the composition root."""

    context_view = _ProviderContextView.from_context(context)
    workflow = _build_no_live_workflow(context_view.workflow_name)
    assembly_options = AdkWorkflowRunnerAssemblyOptions(
        app_name=app_name,
        user_id=user_id,
        workflow_name=context_view.workflow_name,
        service_bundle_options=AdkRunnerServiceBundleOptions(source="in_memory"),
        run_config_options=AdkRunConfigOptions(
            max_llm_calls=1,
            custom_metadata={
                "source": "composition.controlled_adk_run_provider",
                "workflow_id": context_view.workflow_id,
                "workflow_name": context_view.workflow_name,
                "no_live_default": True,
            },
            response_modalities=("TEXT",),
            streaming_mode="none",
            save_live_blob=False,
        ),
        metadata={
            "provider": "composition.controlled_adk_run_provider",
            "provider_role": "production_no_live_runtime_assembly_provider",
            "runtime_id": context_view.runtime_id,
            "workflow_id": context_view.workflow_id,
            "workflow_name": context_view.workflow_name,
            "environment": context_view.environment,
            "profile": context_view.profile,
            "input_payload_keys": sorted(context_view.input_payload),
            "does_not_call_live_llm": True,
            "does_not_call_ollama": True,
            "does_not_enable_external_persistence": True,
            "does_not_enable_tool_eval_memory_mcp_a2a": True,
        },
    )
    return build_adk_workflow_runner_runtime(
        options=RuntimeCompositionOptions(
            config_root=context_view.config_root,
            environment=context_view.environment,
        ),
        workflow=workflow,
        assembly_options=assembly_options,
    )


def _build_no_live_workflow(workflow_name: str) -> Any:
    from google.adk.agents.context import Context
    from google.adk.events import Event
    from google.adk.events.event import NodeInfo
    from google.adk.workflow import START, BaseNode, Workflow

    class ControlledNoLiveNode(BaseNode):
        async def _run_impl(self, *, ctx: Context, node_input: Any):
            input_keys = sorted(node_input) if isinstance(node_input, Mapping) else []
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                node_info=NodeInfo(path=ctx.node_path),
                output={
                    "status": "completed",
                    "execution_mode": "production_controlled_no_live",
                    "input_payload_keys": input_keys,
                    "run_config_source": ctx.run_config.custom_metadata.get("source"),
                    "live_llm_call_performed": False,
                    "ollama_call_performed": False,
                },
            )

    return Workflow(
        name=_adk_workflow_name(workflow_name),
        edges=[(START, ControlledNoLiveNode(name="controlled_no_live_node"))],
    )


def _adk_workflow_name(workflow_name: str) -> str:
    safe_name = "".join(
        character if character.isalnum() or character == "_" else "_"
        for character in workflow_name
    ).strip("_")
    return safe_name or "controlled_adk_run"


class _ProviderContextView:
    def __init__(
        self,
        *,
        config_root: Path,
        environment: str,
        profile: str | None,
        runtime_id: str,
        workflow_id: str,
        workflow_name: str,
        input_payload: Mapping[str, Any],
    ) -> None:
        self.config_root = config_root
        self.environment = environment
        self.profile = profile
        self.runtime_id = runtime_id
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.input_payload = input_payload

    @classmethod
    def from_context(cls, context: Any) -> "_ProviderContextView":
        return cls(
            config_root=Path(_read_context_field(context, "config_root", Path("config"))),
            environment=str(_read_context_field(context, "environment", "local")),
            profile=_optional_string(_read_context_field(context, "profile", None)),
            runtime_id=str(_read_context_field(context, "runtime_id", "")),
            workflow_id=str(_read_context_field(context, "workflow_id", "")),
            workflow_name=str(
                _read_context_field(context, "workflow_name", "controlled-adk-run")
            ),
            input_payload=_mapping(
                _read_context_field(context, "input_payload", {}),
            ),
        )


def _read_context_field(context: Any, key: str, default: Any) -> Any:
    if isinstance(context, Mapping):
        return context.get(key, default)
    return getattr(context, key, default)


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None
