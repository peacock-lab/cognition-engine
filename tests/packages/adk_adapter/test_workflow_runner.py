from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from adk_adapter import AdkWorkflowRunner
from schemas.runtime import InvocationRef, RuntimeStatus, WorkflowInput, WorkflowRef


def test_workflow_runner_runs_minimal_custom_base_node_workflow() -> None:
    from google.adk.agents.context import Context
    from google.adk.events import Event
    from google.adk.events.event import NodeInfo
    from google.adk.workflow import START, BaseNode, Workflow

    class MinimalNode(BaseNode):
        async def _run_impl(self, *, ctx: Context, node_input: Any):
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                node_info=NodeInfo(path=ctx.node_path),
                output={"ok": True, "node": self.name},
            )

    workflow = Workflow(
        name="minimal_custom_workflow",
        edges=[(START, MinimalNode(name="minimal_node"))],
    )
    runner = AdkWorkflowRunner(
        workflow=workflow,
        app_name="test_adk_adapter",
        user_id="test-user",
    )

    result = runner.run_workflow(
        WorkflowInput(
            workflow_ref=WorkflowRef(workflow_id="workflow-001", name="minimal"),
            invocation_ref=InvocationRef(invocation_id="requested-001"),
            input_payload={"message": "hello"},
        )
    )

    assert result.status == RuntimeStatus.SUCCESS
    assert result.workflow_ref.workflow_id == "workflow-001"
    assert result.invocation_ref.invocation_id == "requested-001"
    assert result.metadata["requested_invocation_id"] == "requested-001"
    assert result.metadata["adk_invocation_id"]
    assert result.metadata["session_id"]
    assert len(result.events) >= 2
    assert any(event.payload["output"] == {"ok": True, "node": "minimal_node"} for event in result.events)


def test_runtime_container_and_contract_core_do_not_import_google_adk_or_adk_adapter() -> None:
    package_roots = [
        Path("packages/runtime/src/runtime"),
        Path("packages/composition/src/composition"),
        Path("packages/behavior_contracts/src/behavior_contracts"),
        Path("packages/schemas/src/schemas"),
        Path("packages/config_contexts/src/config_contexts"),
    ]

    for package_root in package_roots:
        for source_file in package_root.rglob("*.py"):
            source = source_file.read_text(encoding="utf-8")
            assert "google.adk" not in source, source_file

    for package_root in package_roots[2:]:
        for source_file in package_root.rglob("*.py"):
            source = source_file.read_text(encoding="utf-8")
            assert not re.search(r"^\s*(from|import)\s+adk_adapter\b", source, re.MULTILINE), source_file
