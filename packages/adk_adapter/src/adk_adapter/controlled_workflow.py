"""Controlled no-live Workflow builders owned by the ADK adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def build_controlled_no_live_workflow(
    *,
    workflow_name: str,
    metadata: Mapping[str, Any] | None = None,
) -> Any:
    """Build the controlled no-live ADK Workflow without leaking raw ADK objects."""

    from google.adk.agents.context import Context
    from google.adk.events import Event
    from google.adk.events.event import NodeInfo
    from google.adk.workflow import START, BaseNode, Workflow

    safe_metadata = dict(metadata or {})

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
                    "adapter_boundary": "adk_adapter.controlled_workflow",
                    "metadata_keys": sorted(safe_metadata),
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
