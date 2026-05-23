"""Observation slot candidates for task workflow agent workflow registry visibility."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from cognition_operation_flows._agents.workflow_admission import (
    AgentWorkflowEvidenceProjectionCandidate,
    AgentWorkflowLoadingGateCandidate,
    build_agent_workflow_evidence_projection,
)


AGENT_WORKFLOW_REGISTRY_OBSERVATION_STATUSES = frozenset(
    {
        "not_configured",
        "candidate_visible",
        "blocked",
        "stale",
        "not_integrated",
    }
)


@dataclass(frozen=True)
class TwfAgentWorkflowCandidateDescriptorSource:
    """Candidate source summary; not a registered workflow descriptor."""

    source_name: str
    source_kind: str
    agent_gate_status: str
    agent_workflow_descriptor_ref: str | None
    agent_team_admission_ref: str | None
    evidence_projection_ref: str | None
    allowed_for_candidate_registration: bool
    allowed_for_execution: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfAgentWorkflowRegistryObservationCandidate:
    """Registry observation slot for a candidate Agent workflow."""

    observation_name: str
    observation_version: str
    status: str
    source: str
    agent_workflow_name: str | None
    agent_team_name: str | None
    agent_team_kind: str | None
    admission_status: str
    candidate_descriptor_available: bool
    candidate_registration_allowed: bool
    execution_allowed: bool
    risk_level: str
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


def build_twf_agent_workflow_candidate_descriptor_source(
    gate: AgentWorkflowLoadingGateCandidate,
    *,
    evidence_projection: AgentWorkflowEvidenceProjectionCandidate | None = None,
) -> TwfAgentWorkflowCandidateDescriptorSource:
    """Build a candidate descriptor source without registering a workflow."""

    projection = evidence_projection or build_agent_workflow_evidence_projection(gate)
    descriptor = gate.descriptor
    admission = gate.admission
    workflow_slug = _slug_or_default(descriptor.workflow_name, "agent-workflow")
    team_slug = _slug_or_default(admission.agent_team_name, "agent-team")
    return TwfAgentWorkflowCandidateDescriptorSource(
        source_name=f"{workflow_slug}-candidate-descriptor-source",
        source_kind="agent_workflow_admission_gate",
        agent_gate_status=gate.status,
        agent_workflow_descriptor_ref=(
            f"agent-workflow-descriptor://{workflow_slug}"
        ),
        agent_team_admission_ref=f"agent-team-admission://{team_slug}",
        evidence_projection_ref=(
            "agent-workflow-evidence-projection://"
            f"{workflow_slug}/{team_slug}"
        ),
        allowed_for_candidate_registration=(
            gate.allowed_for_candidate_registration
        ),
        allowed_for_execution=False,
        metadata={
            "candidate_only": True,
            "does_not_register_workflow": True,
            "does_not_route_workflow": True,
            "does_not_execute_workflow": True,
            "does_not_load_agent": True,
            "does_not_call_model": True,
            "observation_source": (
                "cognition_operation_flows._agents.workflow_registry_observation"
            ),
            "projection_admission_status": projection.admission_status,
            "projection_role_count": projection.role_count,
        },
    )


def build_twf_agent_workflow_registry_observation(
    gate: AgentWorkflowLoadingGateCandidate,
    *,
    source: TwfAgentWorkflowCandidateDescriptorSource | None = None,
    observation_version: str = "v0.7.0-candidate",
) -> TwfAgentWorkflowRegistryObservationCandidate:
    """Build a registry observation slot without touching the registry."""

    descriptor_source = source or build_twf_agent_workflow_candidate_descriptor_source(
        gate
    )
    descriptor = gate.descriptor
    admission = gate.admission
    status = (
        "candidate_visible"
        if gate.allowed_for_candidate_registration and gate.status == "passed"
        else "blocked"
    )
    return TwfAgentWorkflowRegistryObservationCandidate(
        observation_name=(
            f"{_slug_or_default(descriptor.workflow_name, 'agent-workflow')}-"
            "registry-observation"
        ),
        observation_version=observation_version,
        status=status,
        source=descriptor_source.source_name,
        agent_workflow_name=descriptor.workflow_name,
        agent_team_name=admission.agent_team_name,
        agent_team_kind=admission.agent_team_kind,
        admission_status=gate.status,
        candidate_descriptor_available=True,
        candidate_registration_allowed=gate.allowed_for_candidate_registration,
        execution_allowed=False,
        risk_level=admission.risk_level,
        blocking_reasons=gate.blocking_reasons,
        warnings=gate.warnings,
        metadata={
            "candidate_only": True,
            "does_not_register_workflow": True,
            "does_not_route_workflow": True,
            "does_not_execute_workflow": True,
            "does_not_load_agent": True,
            "does_not_call_model": True,
            "not_in_registry_descriptors": True,
            "router_matched": False,
            "route_reason": None,
            "source_kind": descriptor_source.source_kind,
            "allowed_for_execution_source": (
                descriptor_source.allowed_for_execution
            ),
        },
    )


def twf_agent_workflow_candidate_descriptor_source_status_dict(
    source: TwfAgentWorkflowCandidateDescriptorSource,
) -> dict[str, Any]:
    """Return a JSON-ready candidate descriptor source summary."""

    return {
        "source_name": source.source_name,
        "source_kind": source.source_kind,
        "agent_gate_status": source.agent_gate_status,
        "agent_workflow_descriptor_ref": source.agent_workflow_descriptor_ref,
        "agent_team_admission_ref": source.agent_team_admission_ref,
        "evidence_projection_ref": source.evidence_projection_ref,
        "allowed_for_candidate_registration": (
            source.allowed_for_candidate_registration
        ),
        "allowed_for_execution": source.allowed_for_execution,
        "metadata": dict(source.metadata),
    }


def twf_agent_workflow_registry_observation_status_dict(
    observation: TwfAgentWorkflowRegistryObservationCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready registry observation summary."""

    return {
        "observation_name": observation.observation_name,
        "observation_version": observation.observation_version,
        "status": observation.status,
        "source": observation.source,
        "agent_workflow_name": observation.agent_workflow_name,
        "agent_team_name": observation.agent_team_name,
        "agent_team_kind": observation.agent_team_kind,
        "admission_status": observation.admission_status,
        "candidate_descriptor_available": (
            observation.candidate_descriptor_available
        ),
        "candidate_registration_allowed": (
            observation.candidate_registration_allowed
        ),
        "execution_allowed": observation.execution_allowed,
        "risk_level": observation.risk_level,
        "blocking_reasons": list(observation.blocking_reasons),
        "warnings": list(observation.warnings),
        "metadata": dict(observation.metadata),
    }


def _slug_or_default(value: str, default: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", value.strip().lower()).strip("-")
    return slug or default
