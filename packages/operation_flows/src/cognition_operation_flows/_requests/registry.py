"""Registry and router candidates for governed operation flows."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from cognition_operation_flows._core.control import (
    OPERATION_FLOW_CONFIG_PRECEDENCE,
    OPERATION_FLOW_CONTROL_STAGES,
    MANAGED_GOVERNANCE_PARAMETERS,
)
from cognition_operation_flows._requests.intent_detectors import (
    OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_TASK_KIND,
    OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
    OPERATION_FLOW_REFERENCE_REVIEW_TASK_KIND,
    OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
    OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_TASK_KIND,
    OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
    CONFIG_PROFILE_EXPLAIN_DISPLAY_PREVIEW_LIMIT,
    PLAN_DISPLAY_PREVIEW_LIMIT,
    RUN_WORKSPACE_EVIDENCE_AUDIT_DISPLAY_PREVIEW_LIMIT,
    detect_operation_flow_config_profile_explain_request,
    detect_operation_flow_plan_request,
    detect_operation_flow_reference_review_request,
    detect_operation_flow_run_workspace_evidence_audit_request,
)


OPERATION_FLOW_PLAN_WORKFLOW_NAME = "operation_flow_plan_workflow"
OPERATION_FLOW_PLAN_TASK_KIND = "plan_design"


@dataclass(frozen=True)
class OperationFlowDescriptorCandidate:
    """Static descriptor for a operation flow exposed to the router."""

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
class OperationFlowTurnRequestCandidate:
    """Input facts used by the operation flow router for one turn."""

    user_text: str
    chat_session_id: str | None = None
    turn_index: int | None = None
    history: tuple[Mapping[str, str], ...] = ()
    previous_terminal_display_text: str | None = None
    live_model_requested: bool = False
    reference_paths: tuple[str, ...] = ()
    external_readonly_evidence_paths: tuple[str, ...] = ()
    run_workspace_requested: bool = False
    audit_run_workspace_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationFlowRouteCandidate:
    """Routing decision for a operation flow turn."""

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
class OperationFlowRegistryCandidate:
    """Registry of local operation flow descriptors."""

    descriptors: tuple[OperationFlowDescriptorCandidate, ...]
    registry_version: str = "v0.7.0-candidate"
    metadata: dict[str, Any] = field(default_factory=dict)


def build_operation_flow_plan_workflow_descriptor() -> OperationFlowDescriptorCandidate:
    """Build the descriptor for the current integrated plan workflow."""

    return OperationFlowDescriptorCandidate(
        workflow_name=OPERATION_FLOW_PLAN_WORKFLOW_NAME,
        workflow_version="v0.7.0-candidate",
        task_kind=OPERATION_FLOW_PLAN_TASK_KIND,
        display_name="Plan operation flow",
        description="Plan/design workflow for structured product-entry tasks.",
        runtime_status="integrated",
        execution_engine="local_python_workflow",
        default_risk_level="low",
        default_output_budget=PLAN_DISPLAY_PREVIEW_LIMIT,
        live_gate_policy="controlled_live_or_no_live_boundary",
        config_precedence=OPERATION_FLOW_CONFIG_PRECEDENCE,
        control_stages=OPERATION_FLOW_CONTROL_STAGES,
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
            "detector": "detect_operation_flow_plan_request",
            "route_source": "cognition_operation_flows._requests.intent_detectors",
        },
    )


def build_operation_flow_reference_review_workflow_descriptor() -> OperationFlowDescriptorCandidate:
    """Build the descriptor for the integrated reference review workflow."""

    return OperationFlowDescriptorCandidate(
        workflow_name=OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
        workflow_version="v0.7.0-candidate",
        task_kind=OPERATION_FLOW_REFERENCE_REVIEW_TASK_KIND,
        display_name="Reference review operation flow",
        description="Reference-backed review workflow for governed document tasks.",
        runtime_status="integrated",
        execution_engine="local_python_workflow",
        default_risk_level="low",
        default_output_budget=PLAN_DISPLAY_PREVIEW_LIMIT,
        live_gate_policy="controlled_live_or_no_live_boundary",
        config_precedence=OPERATION_FLOW_CONFIG_PRECEDENCE,
        control_stages=OPERATION_FLOW_CONTROL_STAGES,
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
            "detector": "detect_operation_flow_reference_review_request",
            "route_source": "cognition_operation_flows._requests.intent_detectors",
        },
    )


def build_operation_flow_config_profile_explain_workflow_descriptor() -> (
    OperationFlowDescriptorCandidate
):
    """Build the descriptor for the integrated config profile explain workflow."""

    return OperationFlowDescriptorCandidate(
        workflow_name=OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
        workflow_version="v0.7.0-candidate",
        task_kind=OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_TASK_KIND,
        display_name="Config profile explain operation flow",
        description="Configuration explanation workflow for operation controls.",
        runtime_status="integrated_candidate",
        execution_engine="local_python_workflow",
        default_risk_level="low",
        default_output_budget=CONFIG_PROFILE_EXPLAIN_DISPLAY_PREVIEW_LIMIT,
        live_gate_policy="no_live_first",
        config_precedence=OPERATION_FLOW_CONFIG_PRECEDENCE,
        control_stages=OPERATION_FLOW_CONTROL_STAGES,
        managed_governance_parameters=tuple(sorted(MANAGED_GOVERNANCE_PARAMETERS)),
        workspace_supported=True,
        status_projection="unchanged",
        skills_slot_status="candidate_only_frozen",
        agent_slot_status="not_integrated",
        metadata={
            "detector": "detect_operation_flow_config_profile_explain_request",
            "route_source": "cognition_operation_flows._requests.intent_detectors",
            "does_not_execute_tools": True,
            "does_not_call_model": True,
        },
    )


def build_operation_flow_run_workspace_evidence_audit_workflow_descriptor() -> (
    OperationFlowDescriptorCandidate
):
    """Build the descriptor for the integrated run workspace audit workflow."""

    return OperationFlowDescriptorCandidate(
        workflow_name=OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
        workflow_version="v0.7.0-candidate",
        task_kind=OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_TASK_KIND,
        display_name="Run workspace evidence audit operation flow",
        description="Read-only audit workflow for run workspace evidence layers.",
        runtime_status="integrated_candidate",
        execution_engine="local_python_workflow",
        default_risk_level="low",
        default_output_budget=RUN_WORKSPACE_EVIDENCE_AUDIT_DISPLAY_PREVIEW_LIMIT,
        live_gate_policy="no_live_first",
        config_precedence=OPERATION_FLOW_CONFIG_PRECEDENCE,
        control_stages=OPERATION_FLOW_CONTROL_STAGES,
        managed_governance_parameters=tuple(sorted(MANAGED_GOVERNANCE_PARAMETERS)),
        workspace_supported=True,
        status_projection="unchanged",
        skills_slot_status="candidate_only_frozen",
        agent_slot_status="not_integrated",
        metadata={
            "detector": "detect_operation_flow_run_workspace_evidence_audit_request",
            "route_source": "cognition_operation_flows._requests.intent_detectors",
            "does_not_execute_tools": True,
            "does_not_call_model": True,
            "does_not_modify_audited_workspace": True,
        },
    )


def build_default_operation_flow_registry() -> OperationFlowRegistryCandidate:
    """Build the default local registry used by cognition chat."""

    return OperationFlowRegistryCandidate(
        descriptors=(
            build_operation_flow_reference_review_workflow_descriptor(),
            build_operation_flow_config_profile_explain_workflow_descriptor(),
            build_operation_flow_run_workspace_evidence_audit_workflow_descriptor(),
            build_operation_flow_plan_workflow_descriptor(),
        ),
        metadata={
            "source": "cognition_operation_flows._requests.registry",
            "router_mode": "local_deterministic",
        },
    )


def list_operation_flow_descriptors(
    registry: OperationFlowRegistryCandidate,
) -> tuple[OperationFlowDescriptorCandidate, ...]:
    """Return registered descriptors in router order."""

    return registry.descriptors


def route_operation_flow_turn(
    registry: OperationFlowRegistryCandidate,
    request: OperationFlowTurnRequestCandidate,
) -> OperationFlowRouteCandidate:
    """Route a turn to at most one registered operation flow."""

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
        return OperationFlowRouteCandidate(
            matched=False,
            route_reason="ambiguous_route",
            confidence="none",
            turn_index=request.turn_index,
            blocking_reasons=("ambiguous_route",),
            metadata={
                "matched_workflow_names": tuple(
                    route.workflow_name for route in high_confidence_matches
                ),
                "source": "cognition_operation_flows._requests.registry",
            },
        )
    if high_confidence_matches:
        return high_confidence_matches[0]
    if matches:
        return matches[0]
    return OperationFlowRouteCandidate(
        matched=False,
        route_reason="no_registered_workflow_matched",
        confidence="none",
        turn_index=request.turn_index,
        metadata={
            "registered_workflow_count": len(registry.descriptors),
            "source": "cognition_operation_flows._requests.registry",
        },
    )


def operation_flow_descriptor_status_dict(
    descriptor: OperationFlowDescriptorCandidate,
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


def operation_flow_route_status_dict(
    route: OperationFlowRouteCandidate,
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


def operation_flow_registry_status_dict(
    registry: OperationFlowRegistryCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready registry summary."""

    return {
        "registry_version": registry.registry_version,
        "workflow_count": len(registry.descriptors),
        "workflow_names": [
            descriptor.workflow_name for descriptor in registry.descriptors
        ],
        "descriptors": [
            operation_flow_descriptor_status_dict(descriptor)
            for descriptor in registry.descriptors
        ],
    }


def _route_descriptor(
    descriptor: OperationFlowDescriptorCandidate,
    request: OperationFlowTurnRequestCandidate,
) -> OperationFlowRouteCandidate:
    if descriptor.workflow_name == OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME:
        return _route_reference_review(descriptor, request)
    if descriptor.workflow_name == OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME:
        return _route_config_profile_explain(descriptor, request)
    if descriptor.workflow_name == OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME:
        return _route_run_workspace_evidence_audit(descriptor, request)
    if descriptor.workflow_name == OPERATION_FLOW_PLAN_WORKFLOW_NAME:
        return _route_plan(descriptor, request)
    return OperationFlowRouteCandidate(
        matched=False,
        workflow_name=descriptor.workflow_name,
        workflow_version=descriptor.workflow_version,
        task_kind=descriptor.task_kind,
        route_reason="descriptor_has_no_local_detector",
        confidence="none",
        turn_index=request.turn_index,
        warnings=("descriptor_has_no_local_detector",),
    )


def _route_reference_review(
    descriptor: OperationFlowDescriptorCandidate,
    request: OperationFlowTurnRequestCandidate,
) -> OperationFlowRouteCandidate:
    matched = detect_operation_flow_reference_review_request(
        request.user_text,
        reference_paths=request.reference_paths,
        external_readonly_evidence_paths=request.external_readonly_evidence_paths,
    )
    if not matched:
        return _unmatched(descriptor, request, "reference_review_request_not_detected")
    return OperationFlowRouteCandidate(
        matched=True,
        workflow_name=descriptor.workflow_name,
        workflow_version=descriptor.workflow_version,
        task_kind=descriptor.task_kind,
        route_reason="reference_review_request_detected",
        confidence="high",
        source="local_detector",
        turn_index=request.turn_index,
        requires_live_model=request.live_model_requested,
        requires_tools=(("local_reference_reader",) if request.reference_paths else ()),
        requires_workspace=request.run_workspace_requested,
        metadata={
            "detector": "detect_operation_flow_reference_review_request",
            "reference_path_count": len(request.reference_paths),
            "external_readonly_evidence_path_count": len(
                request.external_readonly_evidence_paths
            ),
            **request.metadata,
        },
    )


def _route_config_profile_explain(
    descriptor: OperationFlowDescriptorCandidate,
    request: OperationFlowTurnRequestCandidate,
) -> OperationFlowRouteCandidate:
    if detect_operation_flow_reference_review_request(
        request.user_text,
        reference_paths=request.reference_paths,
        external_readonly_evidence_paths=request.external_readonly_evidence_paths,
    ):
        return _unmatched(descriptor, request, "reference_review_takes_precedence")
    if detect_operation_flow_run_workspace_evidence_audit_request(
        request.user_text,
        audit_target_requested=request.audit_run_workspace_requested,
    ):
        return _unmatched(
            descriptor,
            request,
            "run_workspace_evidence_audit_takes_precedence",
        )
    matched = detect_operation_flow_config_profile_explain_request(request.user_text)
    if not matched:
        return _unmatched(
            descriptor,
            request,
            "config_profile_explain_request_not_detected",
        )
    return OperationFlowRouteCandidate(
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
            "detector": "detect_operation_flow_config_profile_explain_request",
            "reference_path_count": len(request.reference_paths),
            "external_readonly_evidence_path_count": len(
                request.external_readonly_evidence_paths
            ),
            **request.metadata,
        },
    )


def _route_run_workspace_evidence_audit(
    descriptor: OperationFlowDescriptorCandidate,
    request: OperationFlowTurnRequestCandidate,
) -> OperationFlowRouteCandidate:
    if detect_operation_flow_reference_review_request(
        request.user_text,
        reference_paths=request.reference_paths,
        external_readonly_evidence_paths=request.external_readonly_evidence_paths,
    ):
        return _unmatched(descriptor, request, "reference_review_takes_precedence")
    matched = detect_operation_flow_run_workspace_evidence_audit_request(
        request.user_text,
        audit_target_requested=request.audit_run_workspace_requested,
    )
    if not matched:
        return _unmatched(
            descriptor,
            request,
            "run_workspace_evidence_audit_request_not_detected",
        )
    return OperationFlowRouteCandidate(
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
            "detector": "detect_operation_flow_run_workspace_evidence_audit_request",
            "reference_path_count": len(request.reference_paths),
            "external_readonly_evidence_path_count": len(
                request.external_readonly_evidence_paths
            ),
            "audit_run_workspace_requested": request.audit_run_workspace_requested,
            **request.metadata,
        },
    )


def _route_plan(
    descriptor: OperationFlowDescriptorCandidate,
    request: OperationFlowTurnRequestCandidate,
) -> OperationFlowRouteCandidate:
    if detect_operation_flow_reference_review_request(
        request.user_text,
        reference_paths=request.reference_paths,
        external_readonly_evidence_paths=request.external_readonly_evidence_paths,
    ):
        return _unmatched(descriptor, request, "reference_review_takes_precedence")
    if detect_operation_flow_config_profile_explain_request(request.user_text):
        return _unmatched(
            descriptor,
            request,
            "config_profile_explain_takes_precedence",
        )
    if detect_operation_flow_run_workspace_evidence_audit_request(
        request.user_text,
        audit_target_requested=request.audit_run_workspace_requested,
    ):
        return _unmatched(
            descriptor,
            request,
            "run_workspace_evidence_audit_takes_precedence",
        )
    matched = detect_operation_flow_plan_request(
        request.user_text,
        history=request.history,
        previous_plan_text=request.previous_terminal_display_text,
    )
    if not matched:
        return _unmatched(descriptor, request, "plan_request_not_detected")
    return OperationFlowRouteCandidate(
        matched=True,
        workflow_name=descriptor.workflow_name,
        workflow_version=descriptor.workflow_version,
        task_kind=descriptor.task_kind,
        route_reason="plan_request_detected",
        confidence="high",
        source="local_detector",
        turn_index=request.turn_index,
        requires_live_model=request.live_model_requested,
        requires_tools=(("local_reference_reader",) if request.reference_paths else ()),
        requires_workspace=request.run_workspace_requested,
        metadata={
            "detector": "detect_operation_flow_plan_request",
            "reference_path_count": len(request.reference_paths),
            "external_readonly_evidence_path_count": len(
                request.external_readonly_evidence_paths
            ),
            "previous_terminal_display_present": bool(
                request.previous_terminal_display_text
            ),
            **request.metadata,
        },
    )


def _unmatched(
    descriptor: OperationFlowDescriptorCandidate,
    request: OperationFlowTurnRequestCandidate,
    reason: str,
) -> OperationFlowRouteCandidate:
    return OperationFlowRouteCandidate(
        matched=False,
        workflow_name=descriptor.workflow_name,
        workflow_version=descriptor.workflow_version,
        task_kind=descriptor.task_kind,
        route_reason=reason,
        confidence="none",
        source="local_detector",
        turn_index=request.turn_index,
        metadata={"detector": descriptor.metadata.get("detector", "unknown")},
    )
