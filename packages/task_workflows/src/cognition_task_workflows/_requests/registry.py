"""Registry and router candidates for governed task workflows."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from cognition_task_workflows._core.control import (
    TWF_CONFIG_PRECEDENCE,
    TWF_CONTROL_STAGES,
    MANAGED_GOVERNANCE_PARAMETERS,
)
from cognition_task_workflows._requests.intent_detectors import (
    TWF_CONFIG_PROFILE_EXPLAIN_TASK_KIND,
    TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
    TWF_REFERENCE_REVIEW_TASK_KIND,
    TWF_REFERENCE_REVIEW_WORKFLOW_NAME,
    TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_TASK_KIND,
    TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
    CONFIG_PROFILE_EXPLAIN_DISPLAY_PREVIEW_LIMIT,
    PLAN_DISPLAY_PREVIEW_LIMIT,
    RUN_WORKSPACE_EVIDENCE_AUDIT_DISPLAY_PREVIEW_LIMIT,
    detect_twf_config_profile_explain_request,
    detect_twf_plan_request,
    detect_twf_reference_review_request,
    detect_twf_run_workspace_evidence_audit_request,
)


TWF_PLAN_WORKFLOW_NAME = "twf_plan_workflow"
TWF_PLAN_TASK_KIND = "plan_design"


@dataclass(frozen=True)
class TwfDescriptorCandidate:
    """Static descriptor for a task workflow exposed to the router."""

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
class TwfTurnRequestCandidate:
    """Input facts used by the task workflow router for one turn."""

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
class TwfRouteCandidate:
    """Routing decision for a task workflow turn."""

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
class TwfRegistryCandidate:
    """Registry of local task workflow descriptors."""

    descriptors: tuple[TwfDescriptorCandidate, ...]
    registry_version: str = "v0.7.0-candidate"
    metadata: dict[str, Any] = field(default_factory=dict)


def build_twf_plan_workflow_descriptor() -> TwfDescriptorCandidate:
    """Build the descriptor for the current integrated plan workflow."""

    return TwfDescriptorCandidate(
        workflow_name=TWF_PLAN_WORKFLOW_NAME,
        workflow_version="v0.7.0-candidate",
        task_kind=TWF_PLAN_TASK_KIND,
        display_name="Plan task workflow",
        description="Plan/design workflow for structured product-entry tasks.",
        runtime_status="integrated",
        execution_engine="local_python_workflow",
        default_risk_level="low",
        default_output_budget=PLAN_DISPLAY_PREVIEW_LIMIT,
        live_gate_policy="controlled_live_or_no_live_boundary",
        config_precedence=TWF_CONFIG_PRECEDENCE,
        control_stages=TWF_CONTROL_STAGES,
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
            "detector": "detect_twf_plan_request",
            "route_source": "cognition_task_workflows._requests.intent_detectors",
        },
    )


def build_twf_reference_review_workflow_descriptor() -> TwfDescriptorCandidate:
    """Build the descriptor for the integrated reference review workflow."""

    return TwfDescriptorCandidate(
        workflow_name=TWF_REFERENCE_REVIEW_WORKFLOW_NAME,
        workflow_version="v0.7.0-candidate",
        task_kind=TWF_REFERENCE_REVIEW_TASK_KIND,
        display_name="Reference review task workflow",
        description="Reference-backed review workflow for governed document tasks.",
        runtime_status="integrated",
        execution_engine="local_python_workflow",
        default_risk_level="low",
        default_output_budget=PLAN_DISPLAY_PREVIEW_LIMIT,
        live_gate_policy="controlled_live_or_no_live_boundary",
        config_precedence=TWF_CONFIG_PRECEDENCE,
        control_stages=TWF_CONTROL_STAGES,
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
            "detector": "detect_twf_reference_review_request",
            "route_source": "cognition_task_workflows._requests.intent_detectors",
        },
    )


def build_twf_config_profile_explain_workflow_descriptor() -> (
    TwfDescriptorCandidate
):
    """Build the descriptor for the integrated config profile explain workflow."""

    return TwfDescriptorCandidate(
        workflow_name=TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
        workflow_version="v0.7.0-candidate",
        task_kind=TWF_CONFIG_PROFILE_EXPLAIN_TASK_KIND,
        display_name="Config profile explain task workflow",
        description="Configuration explanation workflow for task controls.",
        runtime_status="integrated_candidate",
        execution_engine="local_python_workflow",
        default_risk_level="low",
        default_output_budget=CONFIG_PROFILE_EXPLAIN_DISPLAY_PREVIEW_LIMIT,
        live_gate_policy="no_live_first",
        config_precedence=TWF_CONFIG_PRECEDENCE,
        control_stages=TWF_CONTROL_STAGES,
        managed_governance_parameters=tuple(sorted(MANAGED_GOVERNANCE_PARAMETERS)),
        workspace_supported=True,
        status_projection="unchanged",
        skills_slot_status="candidate_only_frozen",
        agent_slot_status="not_integrated",
        metadata={
            "detector": "detect_twf_config_profile_explain_request",
            "route_source": "cognition_task_workflows._requests.intent_detectors",
            "does_not_execute_tools": True,
            "does_not_call_model": True,
        },
    )


def build_twf_run_workspace_evidence_audit_workflow_descriptor() -> (
    TwfDescriptorCandidate
):
    """Build the descriptor for the integrated run workspace audit workflow."""

    return TwfDescriptorCandidate(
        workflow_name=TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
        workflow_version="v0.7.0-candidate",
        task_kind=TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_TASK_KIND,
        display_name="Run workspace evidence audit task workflow",
        description="Read-only audit workflow for run workspace evidence layers.",
        runtime_status="integrated_candidate",
        execution_engine="local_python_workflow",
        default_risk_level="low",
        default_output_budget=RUN_WORKSPACE_EVIDENCE_AUDIT_DISPLAY_PREVIEW_LIMIT,
        live_gate_policy="no_live_first",
        config_precedence=TWF_CONFIG_PRECEDENCE,
        control_stages=TWF_CONTROL_STAGES,
        managed_governance_parameters=tuple(sorted(MANAGED_GOVERNANCE_PARAMETERS)),
        workspace_supported=True,
        status_projection="unchanged",
        skills_slot_status="candidate_only_frozen",
        agent_slot_status="not_integrated",
        metadata={
            "detector": "detect_twf_run_workspace_evidence_audit_request",
            "route_source": "cognition_task_workflows._requests.intent_detectors",
            "does_not_execute_tools": True,
            "does_not_call_model": True,
            "does_not_modify_audited_workspace": True,
        },
    )


def build_default_twf_registry() -> TwfRegistryCandidate:
    """Build the default local registry used by cognition chat."""

    return TwfRegistryCandidate(
        descriptors=(
            build_twf_reference_review_workflow_descriptor(),
            build_twf_config_profile_explain_workflow_descriptor(),
            build_twf_run_workspace_evidence_audit_workflow_descriptor(),
            build_twf_plan_workflow_descriptor(),
        ),
        metadata={
            "source": "cognition_task_workflows._requests.registry",
            "router_mode": "local_deterministic",
        },
    )


def list_twf_descriptors(
    registry: TwfRegistryCandidate,
) -> tuple[TwfDescriptorCandidate, ...]:
    """Return registered descriptors in router order."""

    return registry.descriptors


def route_twf_turn(
    registry: TwfRegistryCandidate,
    request: TwfTurnRequestCandidate,
) -> TwfRouteCandidate:
    """Route a turn to at most one registered task workflow."""

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
        return TwfRouteCandidate(
            matched=False,
            route_reason="ambiguous_route",
            confidence="none",
            turn_index=request.turn_index,
            blocking_reasons=("ambiguous_route",),
            metadata={
                "matched_workflow_names": tuple(
                    route.workflow_name for route in high_confidence_matches
                ),
                "source": "cognition_task_workflows._requests.registry",
            },
        )
    if high_confidence_matches:
        return high_confidence_matches[0]
    if matches:
        return matches[0]
    return TwfRouteCandidate(
        matched=False,
        route_reason="no_registered_workflow_matched",
        confidence="none",
        turn_index=request.turn_index,
        metadata={
            "registered_workflow_count": len(registry.descriptors),
            "source": "cognition_task_workflows._requests.registry",
        },
    )


def twf_descriptor_status_dict(
    descriptor: TwfDescriptorCandidate,
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


def twf_route_status_dict(
    route: TwfRouteCandidate,
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


def twf_registry_status_dict(
    registry: TwfRegistryCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready registry summary."""

    return {
        "registry_version": registry.registry_version,
        "workflow_count": len(registry.descriptors),
        "workflow_names": [
            descriptor.workflow_name for descriptor in registry.descriptors
        ],
        "descriptors": [
            twf_descriptor_status_dict(descriptor)
            for descriptor in registry.descriptors
        ],
    }


def _route_descriptor(
    descriptor: TwfDescriptorCandidate,
    request: TwfTurnRequestCandidate,
) -> TwfRouteCandidate:
    if descriptor.workflow_name == TWF_REFERENCE_REVIEW_WORKFLOW_NAME:
        return _route_reference_review(descriptor, request)
    if descriptor.workflow_name == TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME:
        return _route_config_profile_explain(descriptor, request)
    if descriptor.workflow_name == TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME:
        return _route_run_workspace_evidence_audit(descriptor, request)
    if descriptor.workflow_name == TWF_PLAN_WORKFLOW_NAME:
        return _route_plan(descriptor, request)
    return TwfRouteCandidate(
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
    descriptor: TwfDescriptorCandidate,
    request: TwfTurnRequestCandidate,
) -> TwfRouteCandidate:
    matched = detect_twf_reference_review_request(
        request.user_text,
        reference_paths=request.reference_paths,
        external_readonly_evidence_paths=request.external_readonly_evidence_paths,
    )
    if not matched:
        return _unmatched(descriptor, request, "reference_review_request_not_detected")
    return TwfRouteCandidate(
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
            "detector": "detect_twf_reference_review_request",
            "reference_path_count": len(request.reference_paths),
            "external_readonly_evidence_path_count": len(
                request.external_readonly_evidence_paths
            ),
            **request.metadata,
        },
    )


def _route_config_profile_explain(
    descriptor: TwfDescriptorCandidate,
    request: TwfTurnRequestCandidate,
) -> TwfRouteCandidate:
    if detect_twf_reference_review_request(
        request.user_text,
        reference_paths=request.reference_paths,
        external_readonly_evidence_paths=request.external_readonly_evidence_paths,
    ):
        return _unmatched(descriptor, request, "reference_review_takes_precedence")
    if detect_twf_run_workspace_evidence_audit_request(
        request.user_text,
        audit_target_requested=request.audit_run_workspace_requested,
    ):
        return _unmatched(
            descriptor,
            request,
            "run_workspace_evidence_audit_takes_precedence",
        )
    matched = detect_twf_config_profile_explain_request(request.user_text)
    if not matched:
        return _unmatched(
            descriptor,
            request,
            "config_profile_explain_request_not_detected",
        )
    return TwfRouteCandidate(
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
            "detector": "detect_twf_config_profile_explain_request",
            "reference_path_count": len(request.reference_paths),
            "external_readonly_evidence_path_count": len(
                request.external_readonly_evidence_paths
            ),
            **request.metadata,
        },
    )


def _route_run_workspace_evidence_audit(
    descriptor: TwfDescriptorCandidate,
    request: TwfTurnRequestCandidate,
) -> TwfRouteCandidate:
    if detect_twf_reference_review_request(
        request.user_text,
        reference_paths=request.reference_paths,
        external_readonly_evidence_paths=request.external_readonly_evidence_paths,
    ):
        return _unmatched(descriptor, request, "reference_review_takes_precedence")
    matched = detect_twf_run_workspace_evidence_audit_request(
        request.user_text,
        audit_target_requested=request.audit_run_workspace_requested,
    )
    if not matched:
        return _unmatched(
            descriptor,
            request,
            "run_workspace_evidence_audit_request_not_detected",
        )
    return TwfRouteCandidate(
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
            "detector": "detect_twf_run_workspace_evidence_audit_request",
            "reference_path_count": len(request.reference_paths),
            "external_readonly_evidence_path_count": len(
                request.external_readonly_evidence_paths
            ),
            "audit_run_workspace_requested": request.audit_run_workspace_requested,
            **request.metadata,
        },
    )


def _route_plan(
    descriptor: TwfDescriptorCandidate,
    request: TwfTurnRequestCandidate,
) -> TwfRouteCandidate:
    if detect_twf_reference_review_request(
        request.user_text,
        reference_paths=request.reference_paths,
        external_readonly_evidence_paths=request.external_readonly_evidence_paths,
    ):
        return _unmatched(descriptor, request, "reference_review_takes_precedence")
    if detect_twf_config_profile_explain_request(request.user_text):
        return _unmatched(
            descriptor,
            request,
            "config_profile_explain_takes_precedence",
        )
    if detect_twf_run_workspace_evidence_audit_request(
        request.user_text,
        audit_target_requested=request.audit_run_workspace_requested,
    ):
        return _unmatched(
            descriptor,
            request,
            "run_workspace_evidence_audit_takes_precedence",
        )
    matched = detect_twf_plan_request(
        request.user_text,
        history=request.history,
        previous_plan_text=request.previous_terminal_display_text,
    )
    if not matched:
        return _unmatched(descriptor, request, "plan_request_not_detected")
    return TwfRouteCandidate(
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
            "detector": "detect_twf_plan_request",
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
    descriptor: TwfDescriptorCandidate,
    request: TwfTurnRequestCandidate,
    reason: str,
) -> TwfRouteCandidate:
    return TwfRouteCandidate(
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
