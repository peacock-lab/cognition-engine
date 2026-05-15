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


def test_workflow_runner_maps_dynamic_workflow_route_event_without_private_adk_imports() -> None:
    from google.adk.agents.context import Context
    from google.adk.events import Event
    from google.adk.events.event import NodeInfo
    from google.adk.events.event_actions import EventActions
    from google.adk.workflow import START, BaseNode, Workflow

    class DynamicLeafNode(BaseNode):
        async def _run_impl(self, *, ctx: Context, node_input: Any):
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                node_info=NodeInfo(path=ctx.node_path),
                output={
                    "dynamic_leaf": True,
                    "node": self.name,
                    "input": node_input,
                },
                actions=EventActions(route="dynamic_leaf_done"),
            )

    class DynamicDispatcherNode(BaseNode):
        async def _run_impl(self, *, ctx: Context, node_input: Any):
            dynamic_output = await ctx.run_node(
                DynamicLeafNode(name="dynamic_leaf", rerun_on_resume=True),
                {"source": self.name, "message": node_input},
                run_id="dynamic-leaf-run",
                use_sub_branch=True,
            )
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                node_info=NodeInfo(path=ctx.node_path),
                output={
                    "dispatcher": self.name,
                    "dynamic_output": dynamic_output,
                },
                actions=EventActions(route="dispatcher_done"),
            )

    workflow = Workflow(
        name="dynamic_route_workflow",
        edges=[
            (
                START,
                DynamicDispatcherNode(
                    name="dynamic_dispatcher",
                    rerun_on_resume=True,
                ),
            ),
        ],
    )
    runner = AdkWorkflowRunner(
        workflow=workflow,
        app_name="test_adk_adapter_dynamic",
        user_id="test-user",
    )

    result = runner.run_workflow(
        WorkflowInput(
            workflow_ref=WorkflowRef(
                workflow_id="workflow-dynamic-001",
                name="dynamic-route",
            ),
            invocation_ref=InvocationRef(invocation_id="requested-dynamic-001"),
            input_payload={"message": "dynamic hello"},
        )
    )

    route_values = {
        event.payload.get("route")
        for event in result.events
        if event.payload.get("route") is not None
    }
    node_paths = [
        event.node_ref.metadata["path"]
        for event in result.events
        if event.node_ref is not None and event.node_ref.metadata.get("path")
    ]
    branch_values = {
        event.metadata.get("branch")
        for event in result.events
        if event.metadata.get("branch") is not None
    }

    assert result.status == RuntimeStatus.SUCCESS
    assert result.invocation_ref.invocation_id == "requested-dynamic-001"
    assert result.metadata["adk_invocation_binding"]["requested_invocation_id"] == (
        "requested-dynamic-001"
    )
    assert "dynamic_leaf_done" in route_values
    assert "dispatcher_done" in route_values
    assert any("dynamic_leaf" in path for path in node_paths)
    assert any("dynamic_dispatcher" in path for path in node_paths)
    assert branch_values


def test_non_adk_layers_do_not_import_google_adk_or_adk_adapter() -> None:
    package_roots_without_adk = [
        Path("packages/runtime/src/runtime"),
        Path("packages/behavior_contracts/src/behavior_contracts"),
        Path("packages/schemas/src/schemas"),
        Path("packages/config_contexts/src/config_contexts"),
    ]

    for package_root in package_roots_without_adk:
        for source_file in package_root.rglob("*.py"):
            source = source_file.read_text(encoding="utf-8")
            assert not re.search(r"^\s*(from|import)\s+google\.adk\b", source, re.MULTILINE), source_file

    for package_root in package_roots_without_adk[1:]:
        for source_file in package_root.rglob("*.py"):
            source = source_file.read_text(encoding="utf-8")
            assert not re.search(r"^\s*(from|import)\s+adk_adapter\b", source, re.MULTILINE), source_file


def test_adk_adapter_dynamic_workflow_evidence_does_not_import_private_workflow_modules() -> None:
    private_workflow_import_pattern = re.compile(
        r"^\s*(from|import)\s+google\.adk\.workflow\." + "_",
        re.MULTILINE,
    )

    for package_root in (
        Path("packages/adk_adapter/src/adk_adapter"),
        Path("tests/packages/adk_adapter"),
    ):
        for source_file in package_root.rglob("*.py"):
            source = source_file.read_text(encoding="utf-8")
            assert not private_workflow_import_pattern.search(source), source_file
