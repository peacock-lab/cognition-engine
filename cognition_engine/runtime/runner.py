"""ADK Runner boundary helpers for the workflow adapter."""

from __future__ import annotations

from typing import Any, Iterable


ADK_RUNTIME_PATH = "Runner -> Workflow -> BaseNode business steps"


def build_adk_runner(
    *,
    app_name: str,
    workflow: Any,
    session_service: Any,
    plugins: Iterable[Any],
) -> Any:
    """Build the ADK App and Runner used by the workflow adapter."""

    from google.adk.apps.app import App
    from google.adk.runners import Runner

    app = App(
        name=app_name,
        root_agent=workflow,
        plugins=list(plugins),
    )
    return Runner(
        app=app,
        session_service=session_service,
    )


async def collect_runner_events(
    runner: Any,
    *,
    user_id: str,
    session_id: str,
    invocation_id: str,
    new_message: Any,
) -> list[Any]:
    """Collect events from ADK Runner.run_async without changing event semantics."""

    events = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        invocation_id=invocation_id,
        new_message=new_message,
    ):
        events.append(event)
    return events


def runtime_path_for_event_trace(
    *,
    event_summary: dict[str, Any],
    workflow_result: dict[str, Any],
) -> Any:
    return event_summary.get("adk_runtime_path") or workflow_result.get("adk_runtime")
