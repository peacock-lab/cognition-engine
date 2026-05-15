"""Registry and router candidates for governed CLI task workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from runtime_container.cli_config_profile_explain_workflow import (
    CLI_CONFIG_PROFILE_EXPLAIN_TASK_KIND,
    CLI_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
    CONFIG_PROFILE_EXPLAIN_DISPLAY_PREVIEW_LIMIT,
    detect_cli_config_profile_explain_request,
)
from runtime_container.cli_plan_workflow import (
    PLAN_DISPLAY_PREVIEW_LIMIT,
    detect_cli_plan_request,
)
from runtime_container.cli_reference_review_workflow import (
    CLI_REFERENCE_REVIEW_TASK_KIND,
    CLI_REFERENCE_REVIEW_WORKFLOW_NAME,
    detect_cli_reference_review_request,
)
from runtime_container.cli_run_workspace_evidence_audit_workflow import (
    CLI_RUN_WORKSPACE_EVIDENCE_AUDIT_TASK_KIND,
    CLI_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
    RUN_WORKSPACE_EVIDENCE_AUDIT_DISPLAY_PREVIEW_LIMIT,
    detect_cli_run_workspace_evidence_audit_request,
)
from runtime_container.cli_task_control import (
    CLI_TASK_CONFIG_PRECEDENCE,
    CLI_TASK_CONTROL_STAGES,
    MANAGED_GOVERNANCE_PARAMETERS,
)


CLI_PLAN_WORKFLOW_NAME = "cli_plan_workflow"
CLI_PLAN_TASK_KIND = "plan_design"


@dataclass(frozen=True)
class CliTaskWorkflowDescriptorCandidate:
    """Static descriptor for a CLI task workflow exposed to the router."""

    workflow_name: str
    workflow_version: str
    task_kind: str
    display_name: str
    description: str
    runtime_status: str
    execution_engine: str
    default_risk_level: str
    default_output_budget: int | None
    live_gate_policy: str
    config_precedence: tuple[str, ...]
    control_stages: tuple[str, ...]
    managed_governance_parameters: tuple[str, ...]
    required_governance_refs: tuple[str, ...] = ()
    supported_tool_profiles: tuple[str, ...] = ()
    required_tools: tuple[str, ...] = ()
    optional_tools: tuple[str, ...] = ()
    workspace_required: bool = False
    workspace_supported: bool = False
    status_projection: str = "none"
    skills_slot_status: str = "candidate_only_frozen"
    agent_slot_status: str = "not_integrated"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CliTaskWorkflowTurnRequestCandidate:
    """Input facts used by the CLI task workflow router for one chat turn."""

    user_text: str
    chat_session_id: str | None = None
    turn_index: int | None = None
    history: tuple[Mapping[str, str], ...] = ()
    previous_terminal_display_text: str | None = None
    live_model_requested: bool = False
    reference_paths: tuple[str, ...] = ()
    run_workspace_requested: bool = False
    audit_run_workspace_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CliTaskWorkflowRouteCandidate:
    """Routing decision for a CLI task workflow turn."""

    matched: bool
    workflow_name: str | None = None
    workflow_version: str | None = None
    task_kind: str | None = None
    route_reason: str = "no_registered_workflow_matched"
    confidence: str = "none"
    source: str = "local_router"
    turn_index: int | None = None
    requires_live_model: bool = False
    requires_tools: tuple[str, ...] = ()
    requires_workspace: bool = False
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CliTaskWorkflowRegistryCandidate:
    """Registry of local CLI task workflow descriptors."""

    descriptors: tuple[CliTaskWorkflowDescriptorCandidate, ...]
    registry_version: str = "v0.7.0-candidate"
    metadata: dict[str, Any] = field(default_factory=dict)


def build_cli_plan_workflow_descriptor() -> CliTaskWorkflowDescriptorCandidate:
    """Build the descriptor for the current integrated CLI plan workflow."""

    return CliTaskWorkflowDescriptorCandidate(
        workflow_name=CLI_PLAN_WORKFLOW_NAME,
        workflow_version="v0.7.0-candidate",
        task_kind=CLI_PLAN_TASK_KIND,
        display_name="CLI plan workflow",
        description="Plan/design workflow for structured terminal planning tasks.",
        runtime_status="integrated",
        execution_engine="local_python_workflow",
        default_risk_level="low",
        default_output_budget=PLAN_DISPLAY_PREVIEW_LIMIT,
        live_gate_policy="controlled_live_or_no_live_boundary",
        config_precedence=CLI_TASK_CONFIG_PRECEDENCE,
        control_stages=CLI_TASK_CONTROL_STAGES,
        managed_governance_parameters=tuple(sorted(MANAGED_GOVERNANCE_PARAMETERS)),
        required_governance_refs=(
            "approval_ref",
            "audit_ref",
            "sanitized_evidence_ref",
        ),
        supported_tool_profiles=("readonly_reference",),
        optional_tools=("local_reference_reader",),
        workspace_supported=True,
        status_projection="latest_plan_compat",
        skills_slot_status="candidate_only_frozen",
        agent_slot_status="not_integrated",
        metadata={
            "detector": "detect_cli_plan_request",
            "route_source": "runtime_container.cli_plan_workflow",
        },
    )


def build_cli_reference_review_workflow_descriptor() -> CliTaskWorkflowDescriptorCandidate:
    """Build the descriptor for the integrated CLI reference review workflow."""

    return CliTaskWorkflowDescriptorCandidate(
        workflow_name=CLI_REFERENCE_REVIEW_WORKFLOW_NAME,
        workflow_version="v0.7.0-candidate",
        task_kind=CLI_REFERENCE_REVIEW_TASK_KIND,
        display_name="CLI reference review workflow",
        description="Reference-backed review workflow for governed document tasks.",
        runtime_status="integrated",
        execution_engine="local_python_workflow",
        default_risk_level="low",
        default_output_budget=PLAN_DISPLAY_PREVIEW_LIMIT,
        live_gate_policy="controlled_live_or_no_live_boundary",
        config_precedence=CLI_TASK_CONFIG_PRECEDENCE,
        control_stages=CLI_TASK_CONTROL_STAGES,
        managed_governance_parameters=tuple(sorted(MANAGED_GOVERNANCE_PARAMETERS)),
        required_governance_refs=(
            "approval_ref",
            "audit_ref",
            "sanitized_evidence_ref",
        ),
        supported_tool_profiles=("readonly_reference",),
        required_tools=("local_reference_reader",),
        workspace_supported=True,
        status_projection="latest_task_minimal",
        skills_slot_status="candidate_only_frozen",
        agent_slot_status="not_integrated",
        metadata={
            "detector": "detect_cli_reference_review_request",
            "route_source": "runtime_container.cli_reference_review_workflow",
        },
    )


def build_cli_config_profile_explain_workflow_descriptor() -> CliTaskWorkflowDescriptorCandidate:
    """Build the descriptor for the integrated CLI config profile explain workflow."""

    return CliTaskWorkflowDescriptorCandidate(
        workflow_name=CLI_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
        workflow_version="v0.7.0-candidate",
        task_kind=CLI_CONFIG_PROFILE_EXPLAIN_TASK_KIND,
        display_name="CLI config profile explain workflow",
        description="Configuration explanation workflow for CLI task controls.",
        runtime_status="integrated_candidate",
        execution_engine="local_python_workflow",
        default_risk_level="low",
        default_output_budget=CONFIG_PROFILE_EXPLAIN_DISPLAY_PREVIEW_LIMIT,
        live_gate_policy="no_live_first",
        config_precedence=CLI_TASK_CONFIG_PRECEDENCE,
        control_stages=CLI_TASK_CONTROL_STAGES,
        managed_governance_parameters=tuple(sorted(MANAGED_GOVERNANCE_PARAMETERS)),
        required_governance_refs=(),
        workspace_supported=True,
        status_projection="unchanged",
        skills_slot_status="candidate_only_frozen",
        agent_slot_status="not_integrated",
        metadata={
            "detector": "detect_cli_config_profile_explain_request",
            "route_source": "runtime_container.cli_config_profile_explain_workflow",
            "does_not_execute_tools": True,
            "does_not_call_model": True,
        },
    )


def build_cli_run_workspace_evidence_audit_workflow_descriptor() -> CliTaskWorkflowDescriptorCandidate:
    """Build the descriptor for the integrated CLI run workspace audit workflow."""

    return CliTaskWorkflowDescriptorCandidate(
        workflow_name=CLI_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
        workflow_version="v0.7.0-candidate",
        task_kind=CLI_RUN_WORKSPACE_EVIDENCE_AUDIT_TASK_KIND,
        display_name="CLI run workspace evidence audit workflow",
        description="Read-only audit workflow for run workspace evidence layers.",
        runtime_status="integrated_candidate",
        execution_engine="local_python_workflow",
        default_risk_level="low",
        default_output_budget=RUN_WORKSPACE_EVIDENCE_AUDIT_DISPLAY_PREVIEW_LIMIT,
        live_gate_policy="no_live_first",
        config_precedence=CLI_TASK_CONFIG_PRECEDENCE,
        control_stages=CLI_TASK_CONTROL_STAGES,
        managed_governance_parameters=tuple(sorted(MANAGED_GOVERNANCE_PARAMETERS)),
        required_governance_refs=(),
        required_tools=(),
        optional_tools=(),
        workspace_supported=True,
        status_projection="unchanged",
        skills_slot_status="candidate_only_frozen",
        agent_slot_status="not_integrated",
        metadata={
            "detector": "detect_cli_run_workspace_evidence_audit_request",
            "route_source": (
                "runtime_container.cli_run_workspace_evidence_audit_workflow"
            ),
            "does_not_execute_tools": True,
            "does_not_call_model": True,
            "does_not_modify_audited_workspace": True,
        },
    )


def build_default_cli_task_workflow_registry() -> CliTaskWorkflowRegistryCandidate:
    """Build the default local registry used by cognition chat."""

    return CliTaskWorkflowRegistryCandidate(
        descriptors=(
            build_cli_reference_review_workflow_descriptor(),
            build_cli_config_profile_explain_workflow_descriptor(),
            build_cli_run_workspace_evidence_audit_workflow_descriptor(),
            build_cli_plan_workflow_descriptor(),
        ),
        metadata={
            "source": "runtime_container.cli_task_workflow_registry",
            "router_mode": "local_deterministic",
        },
    )


def list_cli_task_workflow_descriptors(
    registry: CliTaskWorkflowRegistryCandidate,
) -> tuple[CliTaskWorkflowDescriptorCandidate, ...]:
    """Return registered descriptors in router order."""

    return registry.descriptors


def route_cli_task_workflow_turn(
    registry: CliTaskWorkflowRegistryCandidate,
    request: CliTaskWorkflowTurnRequestCandidate,
) -> CliTaskWorkflowRouteCandidate:
    """Route a chat turn to at most one registered CLI task workflow."""

    matches = tuple(
        route
        for route in (
            _route_descriptor(descriptor, request)
            for descriptor in registry.descriptors
        )
        if route.matched
    )
    high_confidence_matches = tuple(
        route for route in matches if route.confidence == "high"
    )
    if len(high_confidence_matches) > 1:
        return CliTaskWorkflowRouteCandidate(
            matched=False,
            route_reason="ambiguous_route",
            confidence="none",
            turn_index=request.turn_index,
            blocking_reasons=("ambiguous_route",),
            metadata={
                "matched_workflow_names": tuple(
                    route.workflow_name for route in high_confidence_matches
                ),
                "source": "runtime_container.cli_task_workflow_registry",
            },
        )
    if high_confidence_matches:
        return high_confidence_matches[0]
    if matches:
        return matches[0]
    return CliTaskWorkflowRouteCandidate(
        matched=False,
        route_reason="no_registered_workflow_matched",
        confidence="none",
        turn_index=request.turn_index,
        metadata={
            "registered_workflow_count": len(registry.descriptors),
            "source": "runtime_container.cli_task_workflow_registry",
        },
    )


def cli_task_workflow_descriptor_status_dict(
    descriptor: CliTaskWorkflowDescriptorCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready descriptor summary."""

    return {
        "workflow_name": descriptor.workflow_name,
        "workflow_version": descriptor.workflow_version,
        "task_kind": descriptor.task_kind,
        "runtime_status": descriptor.runtime_status,
        "execution_engine": descriptor.execution_engine,
        "default_risk_level": descriptor.default_risk_level,
        "live_gate_policy": descriptor.live_gate_policy,
        "supported_tool_profiles": list(descriptor.supported_tool_profiles),
        "required_tools": list(descriptor.required_tools),
        "optional_tools": list(descriptor.optional_tools),
        "workspace_required": descriptor.workspace_required,
        "workspace_supported": descriptor.workspace_supported,
        "status_projection": descriptor.status_projection,
        "skills_slot_status": descriptor.skills_slot_status,
        "agent_slot_status": descriptor.agent_slot_status,
    }


def cli_task_workflow_route_status_dict(
    route: CliTaskWorkflowRouteCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready route summary."""

    return {
        "matched": route.matched,
        "workflow_name": route.workflow_name,
        "workflow_version": route.workflow_version,
        "task_kind": route.task_kind,
        "route_reason": route.route_reason,
        "confidence": route.confidence,
        "source": route.source,
        "turn_index": route.turn_index,
        "requires_live_model": route.requires_live_model,
        "requires_tools": list(route.requires_tools),
        "requires_workspace": route.requires_workspace,
        "blocking_reasons": list(route.blocking_reasons),
        "warnings": list(route.warnings),
    }


def cli_task_workflow_registry_status_dict(
    registry: CliTaskWorkflowRegistryCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready registry summary."""

    return {
        "registry_version": registry.registry_version,
        "workflow_count": len(registry.descriptors),
        "workflow_names": [
            descriptor.workflow_name for descriptor in registry.descriptors
        ],
        "descriptors": [
            cli_task_workflow_descriptor_status_dict(descriptor)
            for descriptor in registry.descriptors
        ],
    }


def _route_descriptor(
    descriptor: CliTaskWorkflowDescriptorCandidate,
    request: CliTaskWorkflowTurnRequestCandidate,
) -> CliTaskWorkflowRouteCandidate:
    if descriptor.workflow_name == CLI_REFERENCE_REVIEW_WORKFLOW_NAME:
        matched = detect_cli_reference_review_request(
            request.user_text,
            reference_paths=request.reference_paths,
        )
        if not matched:
            return CliTaskWorkflowRouteCandidate(
                matched=False,
                workflow_name=descriptor.workflow_name,
                workflow_version=descriptor.workflow_version,
                task_kind=descriptor.task_kind,
                route_reason="reference_review_request_not_detected",
                confidence="none",
                source="local_detector",
                turn_index=request.turn_index,
                metadata={"detector": "detect_cli_reference_review_request"},
            )
        return CliTaskWorkflowRouteCandidate(
            matched=True,
            workflow_name=descriptor.workflow_name,
            workflow_version=descriptor.workflow_version,
            task_kind=descriptor.task_kind,
            route_reason="reference_review_request_detected",
            confidence="high",
            source="local_detector",
            turn_index=request.turn_index,
            requires_live_model=request.live_model_requested,
            requires_tools=("local_reference_reader",),
            requires_workspace=request.run_workspace_requested,
            metadata={
                "detector": "detect_cli_reference_review_request",
                "reference_path_count": len(request.reference_paths),
                **request.metadata,
            },
        )

    if descriptor.workflow_name != CLI_PLAN_WORKFLOW_NAME:
        if descriptor.workflow_name == CLI_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME:
            if detect_cli_reference_review_request(
                request.user_text,
                reference_paths=request.reference_paths,
            ):
                return CliTaskWorkflowRouteCandidate(
                    matched=False,
                    workflow_name=descriptor.workflow_name,
                    workflow_version=descriptor.workflow_version,
                    task_kind=descriptor.task_kind,
                    route_reason="reference_review_takes_precedence",
                    confidence="none",
                    source="local_detector",
                    turn_index=request.turn_index,
                    metadata={
                        "detector": "detect_cli_config_profile_explain_request",
                    },
                )
            if detect_cli_run_workspace_evidence_audit_request(
                request.user_text,
                audit_target_requested=request.audit_run_workspace_requested,
            ):
                return CliTaskWorkflowRouteCandidate(
                    matched=False,
                    workflow_name=descriptor.workflow_name,
                    workflow_version=descriptor.workflow_version,
                    task_kind=descriptor.task_kind,
                    route_reason="run_workspace_evidence_audit_takes_precedence",
                    confidence="none",
                    source="local_detector",
                    turn_index=request.turn_index,
                    metadata={
                        "detector": "detect_cli_config_profile_explain_request",
                    },
                )
            matched = detect_cli_config_profile_explain_request(request.user_text)
            if not matched:
                return CliTaskWorkflowRouteCandidate(
                    matched=False,
                    workflow_name=descriptor.workflow_name,
                    workflow_version=descriptor.workflow_version,
                    task_kind=descriptor.task_kind,
                    route_reason="config_profile_explain_request_not_detected",
                    confidence="none",
                    source="local_detector",
                    turn_index=request.turn_index,
                    metadata={
                        "detector": "detect_cli_config_profile_explain_request",
                    },
                )
            return CliTaskWorkflowRouteCandidate(
                matched=True,
                workflow_name=descriptor.workflow_name,
                workflow_version=descriptor.workflow_version,
                task_kind=descriptor.task_kind,
                route_reason="config_profile_explain_request_detected",
                confidence="high",
                source="local_detector",
                turn_index=request.turn_index,
                requires_live_model=False,
                requires_tools=(),
                requires_workspace=request.run_workspace_requested,
                metadata={
                    "detector": "detect_cli_config_profile_explain_request",
                    "reference_path_count": len(request.reference_paths),
                    **request.metadata,
                },
            )
        if descriptor.workflow_name == CLI_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME:
            if detect_cli_reference_review_request(
                request.user_text,
                reference_paths=request.reference_paths,
            ):
                return CliTaskWorkflowRouteCandidate(
                    matched=False,
                    workflow_name=descriptor.workflow_name,
                    workflow_version=descriptor.workflow_version,
                    task_kind=descriptor.task_kind,
                    route_reason="reference_review_takes_precedence",
                    confidence="none",
                    source="local_detector",
                    turn_index=request.turn_index,
                    metadata={
                        "detector": (
                            "detect_cli_run_workspace_evidence_audit_request"
                        ),
                    },
                )
            matched = detect_cli_run_workspace_evidence_audit_request(
                request.user_text,
                audit_target_requested=request.audit_run_workspace_requested,
            )
            if not matched:
                return CliTaskWorkflowRouteCandidate(
                    matched=False,
                    workflow_name=descriptor.workflow_name,
                    workflow_version=descriptor.workflow_version,
                    task_kind=descriptor.task_kind,
                    route_reason="run_workspace_evidence_audit_request_not_detected",
                    confidence="none",
                    source="local_detector",
                    turn_index=request.turn_index,
                    metadata={
                        "detector": (
                            "detect_cli_run_workspace_evidence_audit_request"
                        ),
                    },
                )
            return CliTaskWorkflowRouteCandidate(
                matched=True,
                workflow_name=descriptor.workflow_name,
                workflow_version=descriptor.workflow_version,
                task_kind=descriptor.task_kind,
                route_reason="run_workspace_evidence_audit_request_detected",
                confidence="high",
                source="local_detector",
                turn_index=request.turn_index,
                requires_live_model=False,
                requires_tools=(),
                requires_workspace=request.run_workspace_requested,
                metadata={
                    "detector": (
                        "detect_cli_run_workspace_evidence_audit_request"
                    ),
                    "reference_path_count": len(request.reference_paths),
                    "audit_run_workspace_requested": (
                        request.audit_run_workspace_requested
                    ),
                    **request.metadata,
                },
            )
        return CliTaskWorkflowRouteCandidate(
            matched=False,
            workflow_name=descriptor.workflow_name,
            workflow_version=descriptor.workflow_version,
            task_kind=descriptor.task_kind,
            route_reason="descriptor_has_no_local_detector",
            confidence="none",
            turn_index=request.turn_index,
            warnings=("descriptor_has_no_local_detector",),
        )

    if detect_cli_reference_review_request(
        request.user_text,
        reference_paths=request.reference_paths,
    ):
        return CliTaskWorkflowRouteCandidate(
            matched=False,
            workflow_name=descriptor.workflow_name,
            workflow_version=descriptor.workflow_version,
            task_kind=descriptor.task_kind,
            route_reason="reference_review_takes_precedence",
            confidence="none",
            source="local_detector",
            turn_index=request.turn_index,
            metadata={"detector": "detect_cli_plan_request"},
        )

    if detect_cli_config_profile_explain_request(request.user_text):
        return CliTaskWorkflowRouteCandidate(
            matched=False,
            workflow_name=descriptor.workflow_name,
            workflow_version=descriptor.workflow_version,
            task_kind=descriptor.task_kind,
            route_reason="config_profile_explain_takes_precedence",
            confidence="none",
            source="local_detector",
            turn_index=request.turn_index,
            metadata={"detector": "detect_cli_plan_request"},
        )

    if detect_cli_run_workspace_evidence_audit_request(
        request.user_text,
        audit_target_requested=request.audit_run_workspace_requested,
    ):
        return CliTaskWorkflowRouteCandidate(
            matched=False,
            workflow_name=descriptor.workflow_name,
            workflow_version=descriptor.workflow_version,
            task_kind=descriptor.task_kind,
            route_reason="run_workspace_evidence_audit_takes_precedence",
            confidence="none",
            source="local_detector",
            turn_index=request.turn_index,
            metadata={"detector": "detect_cli_plan_request"},
        )

    matched = detect_cli_plan_request(
        request.user_text,
        history=request.history,
        previous_plan_text=request.previous_terminal_display_text,
    )
    if not matched:
        return CliTaskWorkflowRouteCandidate(
            matched=False,
            workflow_name=descriptor.workflow_name,
            workflow_version=descriptor.workflow_version,
            task_kind=descriptor.task_kind,
            route_reason="plan_request_not_detected",
            confidence="none",
            source="local_detector",
            turn_index=request.turn_index,
            metadata={"detector": "detect_cli_plan_request"},
        )

    return CliTaskWorkflowRouteCandidate(
        matched=True,
        workflow_name=descriptor.workflow_name,
        workflow_version=descriptor.workflow_version,
        task_kind=descriptor.task_kind,
        route_reason="plan_request_detected",
        confidence="high",
        source="local_detector",
        turn_index=request.turn_index,
        requires_live_model=request.live_model_requested,
        requires_tools=(
            ("local_reference_reader",) if request.reference_paths else ()
        ),
        requires_workspace=request.run_workspace_requested,
        metadata={
            "detector": "detect_cli_plan_request",
            "reference_path_count": len(request.reference_paths),
            "previous_terminal_display_present": bool(
                request.previous_terminal_display_text
            ),
            **request.metadata,
        },
    )
