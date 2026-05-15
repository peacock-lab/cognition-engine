from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError


PACKAGE_SRC = Path(__file__).resolve().parents[3] / "packages" / "cognition_agent" / "src"
sys.path.insert(0, str(PACKAGE_SRC))

from cognition_agent.models import (  # noqa: E402
    AgentCapabilityViewCandidate,
    AgentContextCandidate,
    AgentInteractionCandidate,
    AgentTaskCandidate,
)


def test_agent_task_candidate_is_constructable_and_non_executing() -> None:
    candidate = AgentTaskCandidate(
        candidate_id="agent-task-1",
        source="unit-test",
        summary="Candidate task only.",
        governance_refs=["decision-1"],
        config_refs=["action-config"],
        task_intent="summarize governance candidate",
    )

    assert candidate.candidate_type == "agent_task_candidate"
    assert candidate.execution_enabled is False
    assert candidate.requires_governance_view is True


def test_agent_interaction_candidate_is_not_chat_or_llm() -> None:
    candidate = AgentInteractionCandidate(
        candidate_id="agent-interaction-1",
        source="unit-test",
        summary="Candidate interaction only.",
        interaction_kind="candidate_note",
    )

    assert candidate.candidate_type == "agent_interaction_candidate"
    assert candidate.chat_enabled is False
    assert candidate.llm_call_enabled is False

    with pytest.raises(ValidationError):
        AgentInteractionCandidate(
            candidate_id="agent-interaction-2",
            source="unit-test",
            summary="Invalid chat attempt.",
            chat_enabled=True,
        )


def test_agent_context_candidate_is_readonly_and_secret_free() -> None:
    candidate = AgentContextCandidate(
        candidate_id="agent-context-1",
        source="unit-test",
        summary="Read-only context.",
        context_refs=["case-1"],
    )

    assert candidate.readonly is True
    assert candidate.secret_context_allowed is False

    with pytest.raises(ValidationError):
        AgentContextCandidate(
            candidate_id="agent-context-2",
            source="unit-test",
            summary="Invalid secret context.",
            secret_context_allowed=True,
        )


def test_agent_capability_view_candidate_does_not_expose_tools_runtime_or_gateway() -> None:
    candidate = AgentCapabilityViewCandidate(
        candidate_id="agent-capability-1",
        source="unit-test",
        summary="Candidate capability view.",
        capability_refs=["read-governance-candidates"],
    )

    assert candidate.tool_execution_enabled is False
    assert candidate.agent_runtime_enabled is False
    assert candidate.gateway_enabled is False

    with pytest.raises(ValidationError):
        AgentCapabilityViewCandidate(
            candidate_id="agent-capability-2",
            source="unit-test",
            summary="Invalid tool capability.",
            tool_execution_enabled=True,
        )


def test_agent_candidates_reject_sensitive_and_runtime_object_metadata() -> None:
    with pytest.raises(ValidationError):
        AgentTaskCandidate(
            candidate_id="agent-task-2",
            source="unit-test",
            summary="Invalid sensitive metadata.",
            metadata={"token": "secret"},
        )

    with pytest.raises(ValidationError):
        AgentTaskCandidate(
            candidate_id="agent-task-3",
            source="unit-test",
            summary="Invalid runtime object metadata.",
            metadata={"object_module": "google.adk.runners"},
        )
