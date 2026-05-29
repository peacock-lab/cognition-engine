"""Isolated ADK Agent/Session/Event/ArtifactService binding probe."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from adk_adapter.agent_service import (
    AdkAgentServiceAdapter,
    AdkAgentShellOptions,
    create_no_live_adk_llm_agent,
)
from adk_adapter.async_utils import run_sync


@dataclass(frozen=True)
class AdkRuntimeBindingProbeOptions:
    """Options for a no-live runtime binding probe."""

    probe_ref: str = "adk-runtime-binding-probe://agent-session-event-artifactservice"
    app_name: str = "cognition_engine_runtime_binding_probe"
    user_id: str = "cognition-engine-adk-user"
    agent_name: str = "runtime_binding_probe_agent"
    model: str = "adk-no-live/runtime-binding-probe"
    instruction: str = "Return a deterministic no-live runtime binding probe response."
    response_text: str = "No-live runtime binding probe completed."
    prompt_text: str = "Run isolated ADK runtime binding probe."
    session_id: str = "runtime-binding-session-001"
    invocation_id: str = "runtime-binding-invocation-001"
    artifact_filename: str = "runtime-binding-summary.txt"
    artifact_text: str = "safe runtime binding artifact summary"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdkRuntimeBindingSafeProjection:
    """Safe projection of an isolated ADK runtime binding probe."""

    probe_ref: str
    agent_ref: str
    agent_type: str
    app_name: str
    session_binding_ref: str
    invocation_ref: str
    adk_invocation_ref: str | None
    event_count: int
    event_summaries: list[dict[str, Any]]
    artifact_summary: dict[str, Any]
    service_summary: dict[str, Any]
    raw_object_included: bool = False
    user_product_path_enabled: bool = False
    default_local_state_dir_enabled: bool = False
    auto_resume_enabled: bool = False
    skills_loaded: bool = False
    memory_enabled: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_evaluation_projection(self) -> dict[str, Any]:
        """Return a plain safe shape for cognition_evaluation."""

        return {
            "probe_ref": self.probe_ref,
            "agent_ref": self.agent_ref,
            "agent_type": self.agent_type,
            "app_name": self.app_name,
            "session_binding_ref": self.session_binding_ref,
            "invocation_ref": self.invocation_ref,
            "adk_invocation_ref_present": bool(self.adk_invocation_ref),
            "event_count": self.event_count,
            "event_summaries": [dict(event) for event in self.event_summaries],
            "artifact_summary": dict(self.artifact_summary),
            "service_summary": dict(self.service_summary),
            "raw_object_included": self.raw_object_included,
            "user_product_path_enabled": self.user_product_path_enabled,
            "default_local_state_dir_enabled": self.default_local_state_dir_enabled,
            "auto_resume_enabled": self.auto_resume_enabled,
            "skills_loaded": self.skills_loaded,
            "memory_enabled": self.memory_enabled,
            "metadata": dict(self.metadata),
        }


def run_agent_session_event_artifactservice_probe(
    options: AdkRuntimeBindingProbeOptions | None = None,
) -> AdkRuntimeBindingSafeProjection:
    """Run a no-live Agent/Session/Event/ArtifactService binding probe."""

    options = options or AdkRuntimeBindingProbeOptions()
    agent = create_no_live_adk_llm_agent(
        AdkAgentShellOptions(
            name=options.agent_name,
            model=options.model,
            instruction=options.instruction,
            mode="chat",
            metadata=options.metadata,
        ),
        response_text=options.response_text,
    )
    adapter = AdkAgentServiceAdapter(
        agent=agent,
        app_name=options.app_name,
        user_id=options.user_id,
    )
    result = run_sync(
        adapter.run_text_async(
            text=options.prompt_text,
            invocation_id=options.invocation_id,
            session_id=options.session_id,
            state={"probe_ref": options.probe_ref},
        )
    )
    artifact_adapter = adapter.service_bundle.artifact_service
    version = artifact_adapter.save_artifact_sync(
        filename=options.artifact_filename,
        session_id=result.session_id,
        artifact=_text_part(options.artifact_text),
        custom_metadata={"probe_ref": options.probe_ref},
    )
    loaded_artifact = artifact_adapter.load_artifact_sync(
        filename=options.artifact_filename,
        session_id=result.session_id,
        version=version,
    )
    artifact_keys_before_delete = artifact_adapter.list_artifact_keys_sync(
        session_id=result.session_id
    )
    versions_before_delete = artifact_adapter.list_versions_sync(
        filename=options.artifact_filename,
        session_id=result.session_id,
    )
    run_sync(
        artifact_adapter.delete_artifact(
            filename=options.artifact_filename,
            session_id=result.session_id,
        )
    )
    artifact_keys_after_delete = artifact_adapter.list_artifact_keys_sync(
        session_id=result.session_id
    )

    session = adapter.service_bundle.session_service.get_session_sync(
        session_id=result.session_id
    )

    return AdkRuntimeBindingSafeProjection(
        probe_ref=options.probe_ref,
        agent_ref=f"adk-agent://{result.agent_name}",
        agent_type=result.agent_type,
        app_name=options.app_name,
        session_binding_ref=f"adk-session-binding://{options.app_name}/{result.session_id}",
        invocation_ref=result.requested_invocation_id,
        adk_invocation_ref=result.adk_invocation_id,
        event_count=len(result.runtime_events),
        event_summaries=[
            {
                "event_ref": f"adk-event://{event.event_id}",
                "event_type": str(event.event_type),
                "author": event.metadata.get("author"),
                "branch": event.metadata.get("branch"),
                "has_error": bool(event.metadata.get("error_code")),
                "payload_keys": sorted(event.payload),
            }
            for event in result.runtime_events
        ],
        artifact_summary={
            "artifact_ref": f"adk-artifact-binding://{result.session_id}/{options.artifact_filename}",
            "filename": options.artifact_filename,
            "version": version,
            "versions_before_delete": versions_before_delete,
            "keys_before_delete": artifact_keys_before_delete,
            "keys_after_delete": artifact_keys_after_delete,
            "loaded_text_length": len(getattr(loaded_artifact, "text", "") or ""),
            "body_included": False,
            "deleted_after_probe": options.artifact_filename not in artifact_keys_after_delete,
        },
        service_summary={
            "session_service_type": type(
                adapter.service_bundle.session_service.adk_service
            ).__name__,
            "artifact_service_type": type(
                adapter.service_bundle.artifact_service.adk_service
            ).__name__,
            "session_event_count": len(getattr(session, "events", []) if session else []),
            "in_memory_services": True,
        },
        raw_object_included=False,
        user_product_path_enabled=False,
        default_local_state_dir_enabled=False,
        auto_resume_enabled=False,
        skills_loaded=False,
        memory_enabled=False,
        metadata={
            "probe_type": "agent_session_event_artifactservice",
            "no_live_execution_observed": result.metadata.get(
                "no_live_execution_observed"
            ),
            "evaluation_projection_only": True,
        },
    )


def _text_part(text: str) -> Any:
    from google.genai import types

    return types.Part(text=text)
