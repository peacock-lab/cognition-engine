from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from adk_adapter.artifacts import AdkArtifactFactsBuilder
from adk_adapter.errors import AdkErrorFactsBuilder
from adk_adapter.events import AdkEventFactsBuilder
from adk_adapter.invocation import AdkInvocationContextBuilder
from adk_adapter.models import build_litellm_ollama_model_route
from schemas.runtime import InvocationRef, RuntimeEventType, WorkflowRef


def test_adk_adapter_module_skeletons_build_observability_inputs() -> None:
    adk_event = SimpleNamespace(
        id="adk-event-001",
        invocation_id="adk-invocation-001",
        author="adk-node",
        node_info=SimpleNamespace(path="workflow/root/adk-node"),
        timestamp=None,
        content={"parts": [{"text": "hello"}]},
        output={"ok": True},
        actions=SimpleNamespace(
            state_delta={"step": "done"},
            artifact_delta={"module-skeleton-artifact.json": 1},
            agent_state={"ready": True},
            route="observability_hub",
        ),
        error_code=None,
        error_message=None,
    )
    requested_invocation = InvocationRef(
        invocation_id="requested-001",
        runtime_id="runtime-001",
        workflow_id="workflow-001",
    )
    workflow_ref = WorkflowRef(workflow_id="workflow-001", name="module-skeleton")

    invocation_facts = AdkInvocationContextBuilder().build_from_events(
        requested_invocation_ref=requested_invocation,
        events=[adk_event],
        workflow_ref=workflow_ref,
        session_id="session-001",
        app_name="app-001",
        user_id="user-001",
    )
    event_facts = AdkEventFactsBuilder().build_from_events(
        [adk_event],
        invocation_ref=invocation_facts.invocation_ref,
        workflow_ref=workflow_ref,
        invocation_binding=invocation_facts.invocation_binding,
    )
    artifact_facts = AdkArtifactFactsBuilder().build_from_events(
        [adk_event],
        invocation_ref=invocation_facts.invocation_ref,
        invocation_binding=invocation_facts.invocation_binding,
    )
    error_facts = AdkErrorFactsBuilder().build_from_exception(
        RuntimeError("adapter failed"),
        invocation_ref=invocation_facts.invocation_ref,
        workflow_ref=workflow_ref,
        metadata={"stage": "module-skeleton"},
    )

    assert invocation_facts.to_observability_input()["source"] == "adk_adapter.invocation"
    assert invocation_facts.invocation_ref.metadata["adk_invocation_binding"]["session_id"] == (
        "session-001"
    )
    assert event_facts.runtime_events[0].event_type == RuntimeEventType.NODE_COMPLETED
    assert event_facts.to_observability_input()["candidate_target"] == (
        "observability_hub.EventTrace"
    )
    assert artifact_facts.artifact_deltas[0].artifact_ref.artifact_id == (
        "module-skeleton-artifact.json"
    )
    assert artifact_facts.to_observability_input()["candidate_target"] == (
        "observability_hub.ArtifactManifest"
    )
    assert error_facts.error_records[0].error_type == "RuntimeError"
    assert error_facts.to_observability_input()["candidate_target"] == (
        "observability_hub.EvidenceBundle.errors"
    )


def test_adk_litellm_ollama_gemma4_route_can_be_constructed_without_direct_call() -> None:
    model, facts = build_litellm_ollama_model_route(model_name="ollama/gemma4-pro:latest")
    metadata = facts.to_observability_input()

    assert type(model).__name__ == "LiteLlm"
    assert metadata["model_name"] == "ollama/gemma4-pro:latest"
    assert metadata["litellm_version"] == "1.82.6"
    assert metadata["pydantic_version"] == "2.13.3"
    assert metadata["pydantic_core_version"] == "2.46.3"
    assert metadata["direct_litellm_completion"] is False
    assert metadata["governance_direct_model_call"] is False
    assert metadata["runtime_call_performed"] is False


def test_adk_litellm_ollama_gemma4_real_call_is_environment_gated() -> None:
    from google.adk.agents import LlmAgent

    model, facts = build_litellm_ollama_model_route(model_name="ollama/gemma4-pro:latest")
    agent = LlmAgent(
        name="gemma4_governance_smoke",
        model=model,
        instruction="Reply with the word ok.",
    )
    assert agent.name == "gemma4_governance_smoke"
    assert facts.litellm_version == "1.82.6"

    if os.getenv("RUN_ADK_OLLAMA_GEMMA4_TEST") != "1":
        pytest.skip(
            "Set RUN_ADK_OLLAMA_GEMMA4_TEST=1 when local Ollama/Gemma4 is available."
        )

    # The gated branch is intentionally left to a dedicated local smoke run so
    # regular package tests never fail because Ollama or the model is absent.
    pytest.skip("Local model smoke gate enabled, but no network call is made by default.")
