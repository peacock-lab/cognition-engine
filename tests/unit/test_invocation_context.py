from __future__ import annotations

import asyncio
from types import SimpleNamespace

from cognition_engine.invocation import (
    ProjectInvocationBindingPlugin,
    build_invocation_binding_summary,
)


class DummyEvent:
    def __init__(self, invocation_id: str | None) -> None:
        self.invocation_id = invocation_id

    def model_copy(self, *, update: dict):
        copied = DummyEvent(self.invocation_id)
        for key, value in update.items():
            setattr(copied, key, value)
        return copied


def test_project_invocation_binding_plugin_binds_context_and_event() -> None:
    plugin = ProjectInvocationBindingPlugin(invocation_id="ce-adk-invocation-sample")
    invocation_context = SimpleNamespace(invocation_id=None)
    event = DummyEvent("adk-native-invocation")

    async def run_plugin():
        await plugin.before_run_callback(invocation_context=invocation_context)
        return await plugin.on_event_callback(
            invocation_context=invocation_context,
            event=event,
        )

    patched_event = asyncio.run(run_plugin())

    assert invocation_context.invocation_id == "ce-adk-invocation-sample"
    assert patched_event.invocation_id == "ce-adk-invocation-sample"
    assert event.invocation_id == "adk-native-invocation"


def test_build_invocation_binding_summary_matches_control_plane_contract() -> None:
    summary = build_invocation_binding_summary(
        project_invocation_id="ce-adk-invocation-sample",
        adk_events=[
            {"adk_invocation_id": "ce-adk-invocation-sample"},
            {"adk_invocation_id": "ce-adk-invocation-sample"},
            {"adk_invocation_id": None},
        ],
    )

    assert summary == {
        "project_invocation_id": "ce-adk-invocation-sample",
        "adk_invocation_id": "ce-adk-invocation-sample",
        "adk_invocation_ids": ["ce-adk-invocation-sample"],
        "adk_invocation_event_count": 2,
        "adk_invocation_missing_count": 1,
        "adk_invocation_bound": False,
        "adk_invocation_mismatch": False,
    }


def test_invocation_readme_is_module_boundary_not_task_log() -> None:
    readme = open("cognition_engine/invocation/README.md", encoding="utf-8").read()

    assert "Module Position" in readme
    assert "ADK Correspondence" in readme
    assert "control_plane Consumption" in readme
    assert "任务" not in readme
    assert "结果包" not in readme
