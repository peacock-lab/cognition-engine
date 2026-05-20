"""Candidate-only admission gate for task workflow agent workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import re
from typing import Any

from cognition_task_workflows._core.control import MANAGED_GOVERNANCE_PARAMETERS
from cognition_task_workflows._tools.loading_validation import TwfToolLoadingGateCandidate


AGENT_WORKFLOW_LOADING_VALIDATION_STAGES = (
    "agent_workflow_descriptor_resolution",
    "agent_team_source_validation",
    "role_inventory_validation",
    "entry_agent_validation",
    "model_live_gate_validation",
    "tool_dependency_validation",
    "handoff_boundary_validation",
    "risk_gate",
    "input_schema_validation",
    "output_boundary_validation",
    "failure_policy_validation",
    "evidence_projection_validation",
)
AGENT_RISK_LEVEL_ORDER = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "unknown": 4,
    "blocked": 5,
}
AGENT_WORKFLOW_CANDIDATE_EXECUTION_ENGINES = frozenset(
    {"agent_workflow_candidate", "adk_agent_team_candidate"}
)
AGENT_TEAM_KINDS = frozenset(
    {
        "single_agent_candidate",
        "collaborative_agent_candidate",
        "adk_agent_team_candidate",
    }
)
RAW_SECRET_KEY_MARKERS = (
    "access_token",
    "api_key",
    "credential",
    "password",
    "private_key",
    "secret",
    "service_account_json",
    "token",
)


@dataclass(frozen=True)
class AgentWorkflowDescriptorCandidate:
    """Candidate descriptor for an agent workflow before runtime integration."""

    workflow_name: str
    workflow_version: str
    task_kind: str
    display_name: str
    description: str
    runtime_status: str
    execution_engine: str
    agent_team_ref: str | None
    agent_team_kind: str
    agent_team_status: str
    default_risk_level: str
    default_output_budget: int | None
    live_gate_policy: str
    model_route_policy: str
    required_governance_refs: tuple[str, ...] = ()
    required_tools: tuple[str, ...] = ()
    optional_tools: tuple[str, ...] = ()
    workspace_supported: bool = True
    status_projection: str = "agent_workflow_candidate"
    skills_slot_status: str = "candidate_only_frozen"
    agent_slot_status: str = "candidate_descriptor_available"
    admission_profile_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentRoleDeclarationCandidate:
    """Internal candidate role declaration for an agent team."""

    agent_name: str
    agent_kind: str
    role_label: str
    responsibility_summary: str
    input_boundary_ref: str
    output_boundary_ref: str
    allowed_tool_names: tuple[str, ...] = ()
    model_policy_ref: str | None = None
    handoff_allowed: bool = False
    handoff_targets_declared: bool = False
    risk_level: str = "low"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentTeamAdmissionCandidate:
    """Candidate admission review for an agent team before execution."""

    agent_team_name: str
    agent_team_ref: str | None
    agent_team_kind: str
    source_ref: str | None
    runtime_status: str
    admitted: bool
    loadable: bool
    dependencies_satisfied: bool
    entry_agent_declared: bool
    role_declarations: tuple[AgentRoleDeclarationCandidate, ...]
    handoff_policy_declared: bool
    handoff_policy_kind: str
    model_policy_declared: bool
    tool_dependencies_declared: bool
    input_schema_ref: str | None
    output_boundary_ref: str | None
    failure_policy_ref: str | None
    risk_level: str
    confirmation_required: bool
    confirmation_satisfied: bool
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentWorkflowLoadingGateCandidate:
    """Aggregate loading gate for a candidate task workflow agent workflow."""

    status: str
    risk_gate_status: str
    descriptor: AgentWorkflowDescriptorCandidate
    admission: AgentTeamAdmissionCandidate
    allowed_for_candidate_registration: bool
    allowed_for_execution: bool
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentWorkflowEvidenceProjectionCandidate:
    """Sanitized evidence projection for a candidate agent workflow gate."""

    workflow_name: str
    agent_team_name: str
    agent_team_kind: str
    admission_status: str
    risk_level: str
    live_gate_policy: str
    role_count: int
    entry_agent_declared: bool
    handoff_policy_declared: bool
    tool_dependency_gate_status: str
    input_schema_ref: str | None
    output_boundary_ref: str | None
    failure_policy_ref: str | None
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


def build_agent_workflow_descriptor(
    *,
    workflow_name: str,
    task_kind: str,
    agent_team_name: str,
    agent_team_kind: str = "single_agent_candidate",
    workflow_version: str = "v0.7.0-candidate",
    display_name: str | None = None,
    description: str = "Candidate task workflow agent workflow descriptor.",
    default_risk_level: str = "medium",
    default_output_budget: int | None = None,
    live_gate_policy: str = "no_live_or_controlled_live_boundary",
    model_route_policy: str = "candidate_model_route_policy",
    required_governance_refs: Sequence[str] = (
        "approval_ref",
        "audit_ref",
        "sanitized_evidence_ref",
    ),
    required_tools: Sequence[str] = (),
    optional_tools: Sequence[str] = (),
    admission_profile_ref: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> AgentWorkflowDescriptorCandidate:
    """Build a candidate-only descriptor without registering a workflow."""

    normalized_team_kind = _normalize_agent_team_kind(agent_team_kind)
    team_slug = _slug_or_default(agent_team_name, "agent-team")
    return AgentWorkflowDescriptorCandidate(
        workflow_name=workflow_name,
        workflow_version=workflow_version,
        task_kind=task_kind,
        display_name=display_name or workflow_name.replace("_", " "),
        description=description,
        runtime_status="candidate_only_designed",
        execution_engine="agent_workflow_candidate",
        agent_team_ref=f"agent-team-candidate://{team_slug}",
        agent_team_kind=normalized_team_kind,
        agent_team_status="candidate_only",
        default_risk_level=default_risk_level,
        default_output_budget=default_output_budget,
        live_gate_policy=live_gate_policy,
        model_route_policy=model_route_policy,
        required_governance_refs=tuple(_ordered_unique(required_governance_refs)),
        required_tools=tuple(_ordered_unique(required_tools)),
        optional_tools=tuple(_ordered_unique(optional_tools)),
        workspace_supported=True,
        status_projection="agent_workflow_candidate",
        skills_slot_status="candidate_only_frozen",
        agent_slot_status="candidate_descriptor_available",
        admission_profile_ref=admission_profile_ref,
        metadata={
            **dict(metadata or {}),
            "candidate_only": True,
            "does_not_register_workflow": True,
            "does_not_load_agent": True,
            "does_not_execute_agent": True,
            "does_not_call_model": True,
        },
    )


def evaluate_agent_team_admission(
    *,
    agent_team_name: str,
    agent_team_kind: str,
    source_ref: str | None,
    entry_agent_name: str | None,
    role_declarations: Sequence[AgentRoleDeclarationCandidate],
    handoff_policy_declared: bool,
    handoff_policy_kind: str = "none",
    model_policy_ref: str | None = None,
    tool_loading_gate: TwfToolLoadingGateCandidate | None = None,
    input_schema_ref: str | None = None,
    output_boundary_ref: str | None = None,
    failure_policy_ref: str | None = None,
    risk_level: str = "medium",
    max_risk_level: str = "medium",
    live_gate_policy: str = "no_live",
    operator_approved: bool = False,
    approval_ref: str | None = None,
    user_passthrough_parameters: Mapping[str, Any] | None = None,
    raw_config: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> AgentTeamAdmissionCandidate:
    """Evaluate an agent team before it can become a task workflow engine."""

    normalized_team_kind = _normalize_agent_team_kind(agent_team_kind)
    normalized_risk = _normalize_risk(risk_level)
    blocking: list[str] = []
    warnings: list[str] = []
    roles = tuple(role_declarations)
    role_names = tuple(_ordered_unique(role.agent_name for role in roles))

    if not agent_team_name.strip():
        blocking.append("agent_team_name_missing")
    if not normalized_team_kind:
        blocking.append("agent_team_kind_missing")
    if normalized_team_kind not in AGENT_TEAM_KINDS:
        blocking.append("agent_team_kind_unsupported")
    if not source_ref:
        blocking.append("agent_team_source_ref_missing")
    entry_agent_declared = bool(entry_agent_name and entry_agent_name in role_names)
    if not entry_agent_declared:
        blocking.append("entry_agent_missing")
    if not roles:
        blocking.append("role_declaration_missing")
    blocking.extend(_role_blocking_reasons(roles, tool_loading_gate))

    if not handoff_policy_declared:
        blocking.append("handoff_policy_missing")
    if not (model_policy_ref or any(role.model_policy_ref for role in roles)):
        blocking.append("model_policy_missing")
    if not input_schema_ref:
        blocking.append("input_schema_missing")
    if not output_boundary_ref:
        blocking.append("output_boundary_missing")
    if not failure_policy_ref:
        blocking.append("failure_policy_missing")

    tool_dependencies = tuple(
        _ordered_unique(
            tool_name for role in roles for tool_name in role.allowed_tool_names
        )
    )
    if tool_dependencies:
        if tool_loading_gate is None or tool_loading_gate.status != "passed":
            blocking.append("tool_dependency_gate_failed")
        else:
            missing = tuple(
                tool_name
                for tool_name in tool_dependencies
                if tool_name not in tool_loading_gate.allowed_tool_names
            )
            if missing:
                blocking.append("tool_dependency_gate_failed")
    if not _risk_at_or_below(normalized_risk, max_risk_level):
        blocking.append("agent_risk_exceeds_policy")

    confirmation_required = _confirmation_required(
        normalized_risk=normalized_risk,
        live_gate_policy=live_gate_policy,
        agent_team_kind=normalized_team_kind,
        has_tool_dependencies=bool(tool_dependencies),
    )
    confirmation_satisfied = not confirmation_required or (
        operator_approved and bool(approval_ref)
    )
    if confirmation_required and not confirmation_satisfied:
        blocking.append("operator_confirmation_required")

    passthrough_conflicts = tuple(
        key
        for key in (user_passthrough_parameters or {})
        if key in MANAGED_GOVERNANCE_PARAMETERS
    )
    for key in passthrough_conflicts:
        blocking.append(f"managed_governance_parameter_override:{key}")

    if _raw_secret_keys(raw_config or {}):
        blocking.append("raw_credential_material_forbidden")

    dependencies_satisfied = bool(source_ref) and (
        not tool_dependencies or bool(tool_loading_gate and tool_loading_gate.status == "passed")
    )
    loadable = bool(source_ref) and not _raw_secret_keys(raw_config or {})
    admitted = not blocking
    return AgentTeamAdmissionCandidate(
        agent_team_name=agent_team_name,
        agent_team_ref=(
            f"agent-team-candidate://{_slug_or_default(agent_team_name, 'agent-team')}"
            if agent_team_name.strip()
            else None
        ),
        agent_team_kind=normalized_team_kind,
        source_ref=source_ref,
        runtime_status="candidate_only_admitted" if admitted else "blocked",
        admitted=admitted,
        loadable=loadable,
        dependencies_satisfied=dependencies_satisfied,
        entry_agent_declared=entry_agent_declared,
        role_declarations=roles,
        handoff_policy_declared=handoff_policy_declared,
        handoff_policy_kind=handoff_policy_kind,
        model_policy_declared=bool(
            model_policy_ref or any(role.model_policy_ref for role in roles)
        ),
        tool_dependencies_declared=bool(tool_dependencies),
        input_schema_ref=input_schema_ref,
        output_boundary_ref=output_boundary_ref,
        failure_policy_ref=failure_policy_ref,
        risk_level=normalized_risk,
        confirmation_required=confirmation_required,
        confirmation_satisfied=confirmation_satisfied,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            **dict(metadata or {}),
            "stages": list(AGENT_WORKFLOW_LOADING_VALIDATION_STAGES),
            "candidate_only": True,
            "does_not_load_agent": True,
            "does_not_execute_agent": True,
            "does_not_call_model": True,
            "entry_agent_name": entry_agent_name,
            "role_count": len(roles),
            "allowed_tool_names": list(tool_dependencies),
            "tool_loading_gate_status": (
                tool_loading_gate.status if tool_loading_gate else "not_declared"
            ),
            "policy_max_risk_level": max_risk_level,
            "live_gate_policy": live_gate_policy,
        },
    )


def validate_agent_workflow_loading_gate(
    *,
    descriptor: AgentWorkflowDescriptorCandidate,
    admission: AgentTeamAdmissionCandidate,
) -> AgentWorkflowLoadingGateCandidate:
    """Validate descriptor and admission facts without executing agents."""

    blocking: list[str] = list(admission.blocking_reasons)
    warnings: list[str] = list(admission.warnings)
    if not descriptor.workflow_name.strip():
        blocking.append("workflow_name_missing")
    if descriptor.runtime_status != "candidate_only_designed":
        blocking.append("runtime_status_not_candidate_only")
    if descriptor.execution_engine not in AGENT_WORKFLOW_CANDIDATE_EXECUTION_ENGINES:
        blocking.append("execution_engine_not_agent_candidate")
    if descriptor.agent_team_ref != admission.agent_team_ref:
        blocking.append("agent_team_ref_mismatch")
    if descriptor.agent_team_kind != admission.agent_team_kind:
        blocking.append("agent_team_kind_mismatch")
    if descriptor.skills_slot_status != "candidate_only_frozen":
        blocking.append("skills_runtime_not_frozen")
    allowed_for_registration = admission.admitted and not blocking
    status = "passed" if allowed_for_registration else "blocked"
    return AgentWorkflowLoadingGateCandidate(
        status=status,
        risk_gate_status=status,
        descriptor=descriptor,
        admission=admission,
        allowed_for_candidate_registration=allowed_for_registration,
        allowed_for_execution=False,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "stages": list(AGENT_WORKFLOW_LOADING_VALIDATION_STAGES),
            "candidate_only": True,
            "does_not_register_workflow": True,
            "does_not_load_agent": True,
            "does_not_execute_agent": True,
            "does_not_call_model": True,
            "agent_gate_reuses_tools_gate": False,
            "agent_gate_references_tools_gate": True,
        },
    )


def build_agent_workflow_evidence_projection(
    gate: AgentWorkflowLoadingGateCandidate,
) -> AgentWorkflowEvidenceProjectionCandidate:
    """Build a sanitized evidence projection for status or workspace use."""

    admission = gate.admission
    descriptor = gate.descriptor
    return AgentWorkflowEvidenceProjectionCandidate(
        workflow_name=descriptor.workflow_name,
        agent_team_name=admission.agent_team_name,
        agent_team_kind=admission.agent_team_kind,
        admission_status=gate.status,
        risk_level=admission.risk_level,
        live_gate_policy=descriptor.live_gate_policy,
        role_count=len(admission.role_declarations),
        entry_agent_declared=admission.entry_agent_declared,
        handoff_policy_declared=admission.handoff_policy_declared,
        tool_dependency_gate_status=str(
            admission.metadata.get("tool_loading_gate_status", "not_declared")
        ),
        input_schema_ref=admission.input_schema_ref,
        output_boundary_ref=admission.output_boundary_ref,
        failure_policy_ref=admission.failure_policy_ref,
        blocking_reasons=gate.blocking_reasons,
        warnings=gate.warnings,
        metadata={
            "candidate_only": True,
            "sanitized_projection": True,
            "does_not_include_topology_graph": True,
            "does_not_include_handoff_refs": True,
            "does_not_include_role_refs": True,
            "does_not_include_raw_trace": True,
        },
    )


def agent_workflow_descriptor_status_dict(
    descriptor: AgentWorkflowDescriptorCandidate,
) -> dict[str, Any]:
    """Return a sanitized JSON-ready descriptor summary."""

    return {
        "workflow_name": descriptor.workflow_name,
        "workflow_version": descriptor.workflow_version,
        "task_kind": descriptor.task_kind,
        "runtime_status": descriptor.runtime_status,
        "execution_engine": descriptor.execution_engine,
        "agent_team_ref": descriptor.agent_team_ref,
        "agent_team_kind": descriptor.agent_team_kind,
        "agent_team_status": descriptor.agent_team_status,
        "default_risk_level": descriptor.default_risk_level,
        "live_gate_policy": descriptor.live_gate_policy,
        "model_route_policy": descriptor.model_route_policy,
        "required_tools": list(descriptor.required_tools),
        "optional_tools": list(descriptor.optional_tools),
        "workspace_supported": descriptor.workspace_supported,
        "status_projection": descriptor.status_projection,
        "skills_slot_status": descriptor.skills_slot_status,
        "agent_slot_status": descriptor.agent_slot_status,
        "admission_profile_ref": descriptor.admission_profile_ref,
    }


def agent_role_declaration_status_dict(
    role: AgentRoleDeclarationCandidate,
) -> dict[str, Any]:
    """Return a sanitized JSON-ready role declaration summary."""

    return {
        "agent_name": role.agent_name,
        "agent_kind": role.agent_kind,
        "role_label": role.role_label,
        "responsibility_summary": role.responsibility_summary,
        "input_boundary_ref": role.input_boundary_ref,
        "output_boundary_ref": role.output_boundary_ref,
        "allowed_tool_names": list(role.allowed_tool_names),
        "model_policy_ref": role.model_policy_ref,
        "handoff_allowed": role.handoff_allowed,
        "handoff_targets_declared": role.handoff_targets_declared,
        "risk_level": role.risk_level,
    }


def agent_team_admission_status_dict(
    admission: AgentTeamAdmissionCandidate,
) -> dict[str, Any]:
    """Return a sanitized JSON-ready agent team admission summary."""

    return {
        "agent_team_name": admission.agent_team_name,
        "agent_team_ref": admission.agent_team_ref,
        "agent_team_kind": admission.agent_team_kind,
        "source_ref": admission.source_ref,
        "runtime_status": admission.runtime_status,
        "admitted": admission.admitted,
        "loadable": admission.loadable,
        "dependencies_satisfied": admission.dependencies_satisfied,
        "entry_agent_declared": admission.entry_agent_declared,
        "role_declarations": [
            agent_role_declaration_status_dict(role)
            for role in admission.role_declarations
        ],
        "handoff_policy_declared": admission.handoff_policy_declared,
        "handoff_policy_kind": admission.handoff_policy_kind,
        "model_policy_declared": admission.model_policy_declared,
        "tool_dependencies_declared": admission.tool_dependencies_declared,
        "input_schema_ref": admission.input_schema_ref,
        "output_boundary_ref": admission.output_boundary_ref,
        "failure_policy_ref": admission.failure_policy_ref,
        "risk_level": admission.risk_level,
        "confirmation_required": admission.confirmation_required,
        "confirmation_satisfied": admission.confirmation_satisfied,
        "blocking_reasons": list(admission.blocking_reasons),
        "warnings": list(admission.warnings),
        "metadata": dict(admission.metadata),
    }


def agent_workflow_loading_gate_status_dict(
    gate: AgentWorkflowLoadingGateCandidate,
) -> dict[str, Any]:
    """Return a sanitized JSON-ready agent workflow gate summary."""

    return {
        "status": gate.status,
        "risk_gate_status": gate.risk_gate_status,
        "descriptor": agent_workflow_descriptor_status_dict(gate.descriptor),
        "admission": agent_team_admission_status_dict(gate.admission),
        "allowed_for_candidate_registration": (
            gate.allowed_for_candidate_registration
        ),
        "allowed_for_execution": gate.allowed_for_execution,
        "blocking_reasons": list(gate.blocking_reasons),
        "warnings": list(gate.warnings),
        "metadata": dict(gate.metadata),
    }


def agent_workflow_evidence_projection_status_dict(
    projection: AgentWorkflowEvidenceProjectionCandidate,
) -> dict[str, Any]:
    """Return a sanitized JSON-ready evidence projection."""

    return {
        "workflow_name": projection.workflow_name,
        "agent_team_name": projection.agent_team_name,
        "agent_team_kind": projection.agent_team_kind,
        "admission_status": projection.admission_status,
        "risk_level": projection.risk_level,
        "live_gate_policy": projection.live_gate_policy,
        "role_count": projection.role_count,
        "entry_agent_declared": projection.entry_agent_declared,
        "handoff_policy_declared": projection.handoff_policy_declared,
        "tool_dependency_gate_status": projection.tool_dependency_gate_status,
        "input_schema_ref": projection.input_schema_ref,
        "output_boundary_ref": projection.output_boundary_ref,
        "failure_policy_ref": projection.failure_policy_ref,
        "blocking_reasons": list(projection.blocking_reasons),
        "warnings": list(projection.warnings),
        "metadata": dict(projection.metadata),
    }


def _role_blocking_reasons(
    roles: Sequence[AgentRoleDeclarationCandidate],
    tool_loading_gate: TwfToolLoadingGateCandidate | None,
) -> list[str]:
    blocking: list[str] = []
    allowed_tools = set(tool_loading_gate.allowed_tool_names if tool_loading_gate else ())
    for role in roles:
        prefix = f"role:{role.agent_name or '<missing>'}:"
        if not role.agent_name.strip():
            blocking.append("role_agent_name_missing")
        if not role.agent_kind.strip():
            blocking.append(f"{prefix}role_agent_kind_missing")
        if not role.responsibility_summary.strip():
            blocking.append(f"{prefix}role_responsibility_summary_missing")
        if not role.input_boundary_ref.strip():
            blocking.append(f"{prefix}role_input_boundary_missing")
        if not role.output_boundary_ref.strip():
            blocking.append(f"{prefix}role_output_boundary_missing")
        if _normalize_risk(role.risk_level) == "blocked":
            blocking.append(f"{prefix}role_risk_blocked")
        for tool_name in role.allowed_tool_names:
            if tool_loading_gate is None or tool_name not in allowed_tools:
                blocking.append(f"{prefix}role_tool_not_allowed:{tool_name}")
    return blocking


def _confirmation_required(
    *,
    normalized_risk: str,
    live_gate_policy: str,
    agent_team_kind: str,
    has_tool_dependencies: bool,
) -> bool:
    if normalized_risk in {"medium", "high", "unknown", "blocked"}:
        return True
    if "live" in live_gate_policy and live_gate_policy != "no_live":
        return True
    if agent_team_kind in {
        "collaborative_agent_candidate",
        "adk_agent_team_candidate",
    }:
        return True
    return has_tool_dependencies


def _normalize_agent_team_kind(agent_team_kind: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", agent_team_kind.strip().lower()).strip("_")


def _normalize_risk(risk_level: str) -> str:
    normalized = (risk_level or "unknown").strip().lower()
    return normalized if normalized in AGENT_RISK_LEVEL_ORDER else "unknown"


def _risk_at_or_below(risk_level: str, max_risk_level: str) -> bool:
    return AGENT_RISK_LEVEL_ORDER.get(risk_level, AGENT_RISK_LEVEL_ORDER["unknown"]) <= (
        AGENT_RISK_LEVEL_ORDER.get(max_risk_level, AGENT_RISK_LEVEL_ORDER["medium"])
    )


def _raw_secret_keys(raw_config: Mapping[str, Any]) -> tuple[str, ...]:
    keys: list[str] = []
    for key, value in raw_config.items():
        key_text = str(key).lower()
        if any(marker in key_text for marker in RAW_SECRET_KEY_MARKERS):
            keys.append(str(key))
        if isinstance(value, Mapping):
            keys.extend(_raw_secret_keys(value))
    return tuple(_ordered_unique(keys))


def _slug_or_default(value: str, default: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", value.strip().lower()).strip("-")
    return slug or default


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
