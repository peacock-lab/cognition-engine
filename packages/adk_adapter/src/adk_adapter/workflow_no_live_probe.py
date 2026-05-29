"""No-live Workflow Runtime probe for product-safe facts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from adk_adapter.workflow_runner import AdkWorkflowRunner
from schemas.runtime import InvocationRef, RuntimeStatus, WorkflowInput, WorkflowResult, WorkflowRef


@dataclass(frozen=True)
class AdkWorkflowNoLiveProbeOptions:
    """Options for a no-live Workflow Runtime probe."""

    probe_ref: str = "adk-workflow-no-live-probe://continuable-evidence-session"
    workflow_id: str = "continuable-evidence-session-workflow-no-live"
    workflow_name: str = "continuable_evidence_session_workflow_no_live"
    app_name: str = "cognition_engine_workflow_no_live_probe"
    user_id: str = "cognition-engine-adk-user"
    invocation_id: str = "workflow-no-live-invocation-001"
    prompt_text: str = "Run no-live workflow probe."
    artifact_ref: str = "workflow-summary.txt"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdkWorkflowNoLiveSafeProjection:
    """Safe projection of a Workflow Runtime no-live probe."""

    probe_ref: str
    workflow_ref: str
    workflow_name: str
    invocation_ref: str
    adk_invocation_ref: str | None
    session_binding_ref: str | None
    workflow_status: str
    event_count: int
    node_paths: list[str]
    event_review_refs: list[str]
    artifact_binding_summary_refs: list[str]
    evaluation_summary_ref: str
    service_summary: dict[str, Any]
    raw_object_included: bool = False
    raw_event_payload_included: bool = False
    artifact_body_included: bool = False
    adk_eval_raw_data_included: bool = False
    user_product_path_enabled: bool = False
    default_local_state_dir_enabled: bool = False
    auto_resume_enabled: bool = False
    skills_loaded: bool = False
    memory_enabled: bool = False
    tools_mcp_enabled: bool = False
    callbacks_enabled: bool = False
    plugins_enabled: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_evaluation_projection(self) -> dict[str, Any]:
        """Return a plain safe shape for external evaluation."""

        return {
            "probe_ref": self.probe_ref,
            "workflow_ref": self.workflow_ref,
            "workflow_name": self.workflow_name,
            "invocation_ref": self.invocation_ref,
            "adk_invocation_ref_present": bool(self.adk_invocation_ref),
            "session_binding_ref": self.session_binding_ref,
            "workflow_status": self.workflow_status,
            "event_count": self.event_count,
            "node_paths": list(self.node_paths),
            "event_review_refs": list(self.event_review_refs),
            "artifact_binding_summary_refs": list(self.artifact_binding_summary_refs),
            "evaluation_summary_ref": self.evaluation_summary_ref,
            "service_summary": dict(self.service_summary),
            "raw_object_included": self.raw_object_included,
            "raw_event_payload_included": self.raw_event_payload_included,
            "artifact_body_included": self.artifact_body_included,
            "adk_eval_raw_data_included": self.adk_eval_raw_data_included,
            "user_product_path_enabled": self.user_product_path_enabled,
            "default_local_state_dir_enabled": self.default_local_state_dir_enabled,
            "auto_resume_enabled": self.auto_resume_enabled,
            "skills_loaded": self.skills_loaded,
            "memory_enabled": self.memory_enabled,
            "tools_mcp_enabled": self.tools_mcp_enabled,
            "callbacks_enabled": self.callbacks_enabled,
            "plugins_enabled": self.plugins_enabled,
            "metadata": dict(self.metadata),
        }


def run_workflow_no_live_probe(
    options: AdkWorkflowNoLiveProbeOptions | None = None,
) -> AdkWorkflowNoLiveSafeProjection:
    """Run a no-live Workflow Runtime probe and return safe product facts."""

    options = options or AdkWorkflowNoLiveProbeOptions()
    workflow = _build_no_live_workflow(options)
    runner = AdkWorkflowRunner(
        workflow=workflow,
        app_name=options.app_name,
        user_id=options.user_id,
    )
    result = runner.run_workflow(
        WorkflowInput(
            workflow_ref=WorkflowRef(
                workflow_id=options.workflow_id,
                name=options.workflow_name,
            ),
            invocation_ref=InvocationRef(invocation_id=options.invocation_id),
            input_payload={"message": options.prompt_text},
            metadata={"probe_ref": options.probe_ref},
        )
    )
    return _projection_from_result(result, options=options)


def _projection_from_result(
    result: WorkflowResult,
    *,
    options: AdkWorkflowNoLiveProbeOptions,
) -> AdkWorkflowNoLiveSafeProjection:
    binding = result.metadata.get("adk_invocation_binding") or {}
    service_bundle = (
        result.metadata.get("workflow_service", {})
        .get("runner_service", {})
        .get("service_bundle", {})
    )
    session_id = result.metadata.get("session_id")
    binding_base = (
        "continuable-evidence-session-workflow-binding://"
        f"{_safe_slug(options.workflow_id)}/{_safe_slug(options.invocation_id)}"
    )
    node_paths = sorted(
        {
            str(event.node_ref.metadata["path"])
            for event in result.events
            if event.node_ref is not None and event.node_ref.metadata.get("path")
        }
    )
    artifact_refs = [
        f"{binding_base}/artifact-summary/{index + 1}"
        for index, _delta in enumerate(result.artifact_deltas)
    ]
    return AdkWorkflowNoLiveSafeProjection(
        probe_ref=options.probe_ref,
        workflow_ref=f"adk-workflow://{options.workflow_id}",
        workflow_name=options.workflow_name,
        invocation_ref=options.invocation_id,
        adk_invocation_ref=binding.get("adk_invocation_id")
        or result.metadata.get("adk_invocation_id"),
        session_binding_ref=(
            f"adk-workflow-session-binding://{options.app_name}/{session_id}"
            if session_id
            else None
        ),
        workflow_status=str(result.status.value if isinstance(result.status, RuntimeStatus) else result.status),
        event_count=len(result.events),
        node_paths=node_paths,
        event_review_refs=[
            f"{binding_base}/event-review/{index + 1}"
            for index, _event in enumerate(result.events)
        ],
        artifact_binding_summary_refs=artifact_refs,
        evaluation_summary_ref=f"evaluation://adk-workflow-no-live/{_safe_slug(options.workflow_id)}",
        service_summary={
            "workflow_runner": "AdkWorkflowRunner",
            "workflow_type": result.metadata.get("workflow_service", {}).get(
                "workflow_type"
            ),
            "session_service_type": (service_bundle.get("session_service") or {}).get(
                "adk_service_type"
            ),
            "artifact_service_type": (service_bundle.get("artifact_service") or {}).get(
                "adk_service_type"
            ),
            "in_memory_services": True,
        },
        raw_object_included=False,
        raw_event_payload_included=False,
        artifact_body_included=False,
        adk_eval_raw_data_included=False,
        user_product_path_enabled=False,
        default_local_state_dir_enabled=False,
        auto_resume_enabled=False,
        skills_loaded=False,
        memory_enabled=False,
        tools_mcp_enabled=False,
        callbacks_enabled=False,
        plugins_enabled=False,
        metadata={
            "probe_type": "workflow_runtime_no_live",
            "entry_before_user_path_fact_gate": True,
            "source_event_count": len(result.events),
            "source_artifact_delta_count": len(result.artifact_deltas),
            "source_error_count": len(result.errors),
            "adk_evaluation_utility_absorption": "external_safe_evaluation_only",
            **dict(options.metadata),
        },
    )


def _build_no_live_workflow(options: AdkWorkflowNoLiveProbeOptions) -> Any:
    from google.adk.agents.context import Context
    from google.adk.events import Event
    from google.adk.events.event import NodeInfo
    from google.adk.events.event_actions import EventActions
    from google.adk.workflow import START, BaseNode, Workflow

    class NoLiveFactNode(BaseNode):
        async def _run_impl(self, *, ctx: Context, node_input: Any):
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                node_info=NodeInfo(path=ctx.node_path),
                output={"status": "safe-summary-only"},
                actions=EventActions(
                    state_delta={"workflow_probe_status": "completed"},
                    artifact_delta={options.artifact_ref: 0},
                    route="workflow_no_live_done",
                ),
            )

    return Workflow(
        name=options.workflow_name,
        edges=[(START, NoLiveFactNode(name="workflow_no_live_fact_node"))],
    )


def _safe_slug(value: str) -> str:
    slug = "".join(char if char.isalnum() else "-" for char in value.lower())
    return "-".join(part for part in slug.split("-") if part) or "unavailable"
