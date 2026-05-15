"""Build productized controlled ADK run requests from product inputs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from contract_core.llm_invocation import GovernedLlmInvocationService
from contract_core.runtime import (
    InvocationRef,
    RuntimeInput,
    RuntimeProductizationGateConfigView,
    WorkflowRef,
)

from runtime_container.controlled_adk_run_entry import (
    ControlledAdkRunRequest,
    OperatorApprovalFacts,
)
from runtime_container.workflow_registry import (
    WorkflowRegistry,
    WorkflowRegistryBuildContext,
)


@dataclass(frozen=True)
class ControlledAdkRunRequestBuildInput:
    """Product input mapped from CLI/Gateway/UI into the controlled run request."""

    config_root: Path
    environment: str
    profile: str | None
    runtime_id: str
    invocation_id: str
    workflow_id: str
    workflow_name: str
    input_payload: Mapping[str, Any] = field(default_factory=dict)
    operator_approved: bool = False
    approval_ref: str | None = None
    audit_ref: str | None = None
    request_live_llm: bool = False
    request_ollama: bool = False
    allow_live_llm: bool = False
    allow_ollama: bool = False
    live_llm_approval_ref: str | None = None
    allow_tool_confirmation: bool | None = None
    tool_confirmation_approval_ref: str | None = None
    tool_confirmation_decision_source: str | None = None
    sanitized_evidence_ref: str | None = None
    governance_summary_output_ref: str | None = None
    runtime_assembly: Any | None = None
    evidence_id: str | None = None
    llm_invocation_service: GovernedLlmInvocationService | None = None
    agent_shell_live_client: Any | None = None


def build_controlled_adk_run_request(
    build_input: ControlledAdkRunRequestBuildInput,
) -> ControlledAdkRunRequest:
    """Build the 166 product entry request from a product-safe input object."""

    if build_input.runtime_assembly is None:
        raise ValueError("runtime_assembly is required to build a controlled run request")

    runtime_input = build_runtime_input(build_input)
    productization_gate = build_productization_gate(build_input)
    operator_approval = build_operator_approval_facts(build_input)

    return ControlledAdkRunRequest(
        runtime_assembly=build_input.runtime_assembly,
        runtime_input=runtime_input,
        productization_gate=productization_gate,
        operator_approval=operator_approval,
        evidence_id=build_input.evidence_id or f"cognition-cli-{build_input.runtime_id}",
        llm_invocation_service=build_input.llm_invocation_service,
        agent_shell_live_client=build_input.agent_shell_live_client,
    )


def build_controlled_adk_run_request_from_registry(
    *,
    build_input: ControlledAdkRunRequestBuildInput,
    workflow_registry: WorkflowRegistry,
) -> ControlledAdkRunRequest:
    """Resolve a workflow registry entry and build a controlled run request."""

    entry = workflow_registry.resolve(
        workflow_id=build_input.workflow_id,
        workflow_name=build_input.workflow_name,
    )
    runtime_assembly = workflow_registry.build_runtime_assembly(
        entry,
        WorkflowRegistryBuildContext(
            config_root=build_input.config_root,
            environment=build_input.environment,
            profile=build_input.profile,
            runtime_id=build_input.runtime_id,
            workflow_id=entry.workflow_id,
            workflow_name=entry.workflow_name,
            input_payload=dict(build_input.input_payload),
        ),
    )
    resolved_input = ControlledAdkRunRequestBuildInput(
        config_root=build_input.config_root,
        environment=build_input.environment,
        profile=build_input.profile,
        runtime_id=build_input.runtime_id,
        invocation_id=build_input.invocation_id,
        workflow_id=entry.workflow_id,
        workflow_name=entry.workflow_name,
        input_payload=dict(build_input.input_payload),
        operator_approved=build_input.operator_approved,
        approval_ref=build_input.approval_ref,
        audit_ref=build_input.audit_ref,
        request_live_llm=build_input.request_live_llm,
        request_ollama=build_input.request_ollama,
        allow_live_llm=build_input.allow_live_llm,
        allow_ollama=build_input.allow_ollama,
        live_llm_approval_ref=build_input.live_llm_approval_ref,
        allow_tool_confirmation=build_input.allow_tool_confirmation,
        tool_confirmation_approval_ref=(
            build_input.tool_confirmation_approval_ref
        ),
        tool_confirmation_decision_source=(
            build_input.tool_confirmation_decision_source
        ),
        sanitized_evidence_ref=build_input.sanitized_evidence_ref,
        governance_summary_output_ref=build_input.governance_summary_output_ref,
        runtime_assembly=runtime_assembly,
        evidence_id=build_input.evidence_id,
        llm_invocation_service=build_input.llm_invocation_service,
        agent_shell_live_client=build_input.agent_shell_live_client,
    )
    return build_controlled_adk_run_request(resolved_input)


def build_runtime_input(
    build_input: ControlledAdkRunRequestBuildInput,
) -> RuntimeInput:
    """Build RuntimeInput from product request fields."""

    return RuntimeInput(
        runtime_id=build_input.runtime_id,
        workflow_ref=WorkflowRef(
            workflow_id=build_input.workflow_id,
            name=build_input.workflow_name,
            source="runtime_container.controlled_adk_run_request_builder",
        ),
        invocation_ref=InvocationRef(
            invocation_id=build_input.invocation_id,
            runtime_id=build_input.runtime_id,
            workflow_id=build_input.workflow_id,
            source="runtime_container.controlled_adk_run_request_builder",
            metadata={
                "audit_ref": build_input.audit_ref,
                "sanitized_evidence_ref": build_input.sanitized_evidence_ref,
            },
        ),
        input_payload=dict(build_input.input_payload),
        metadata={
            "entry_source": "runtime_container.entrypoints.cognition",
            "config_root": str(build_input.config_root),
            "environment": build_input.environment,
            "profile": build_input.profile,
        },
    )


def build_productization_gate(
    build_input: ControlledAdkRunRequestBuildInput,
) -> RuntimeProductizationGateConfigView:
    """Build the productization gate consumed by the 166 product entry."""

    return RuntimeProductizationGateConfigView(
        gate_id=f"gate-{build_input.runtime_id}",
        request_adk_run=True,
        request_live_llm=build_input.request_live_llm,
        request_ollama=build_input.request_ollama,
        allow_adk_run=True,
        allow_live_llm=build_input.allow_live_llm,
        allow_ollama=build_input.allow_ollama,
        explicit_operator_approval=build_input.operator_approved,
        sanitized_evidence_ref=build_input.sanitized_evidence_ref,
        governance_summary_output_ref=build_input.governance_summary_output_ref,
        audit_ref=build_input.audit_ref,
        reason="cognition run controlled no-live product request",
        metadata={
            "source": "runtime_container.controlled_adk_run_request_builder",
            "profile": build_input.profile,
            "workflow_name": build_input.workflow_name,
            "request_live_llm": build_input.request_live_llm,
            "request_ollama": build_input.request_ollama,
        },
    )


def build_operator_approval_facts(
    build_input: ControlledAdkRunRequestBuildInput,
) -> OperatorApprovalFacts:
    """Build operator approval facts consumed by final preflight."""

    explicit_controlled_live_requested = _explicit_controlled_live_requested(
        build_input
    )
    return OperatorApprovalFacts(
        approved=build_input.operator_approved,
        approval_ref=build_input.approval_ref,
        approved_by="operator://cognition-run",
        audit_ref=build_input.audit_ref,
        request_adk_run=True,
        allow_adk_run=True,
        allow_live_llm=build_input.allow_live_llm,
        allow_ollama=build_input.allow_ollama,
        live_llm_approval_ref=build_input.live_llm_approval_ref,
        allow_tool_confirmation=build_input.allow_tool_confirmation,
        tool_confirmation_approval_ref=build_input.tool_confirmation_approval_ref,
        tool_confirmation_decision_source=(
            build_input.tool_confirmation_decision_source
        ),
        does_not_trigger_live_llm=not explicit_controlled_live_requested,
        metadata={
            "source": "runtime_container.controlled_adk_run_request_builder",
            "workflow_name": build_input.workflow_name,
            "request_live_llm": build_input.request_live_llm,
            "request_ollama": build_input.request_ollama,
            "explicit_controlled_live_requested": explicit_controlled_live_requested,
        },
    )


def _explicit_controlled_live_requested(
    build_input: ControlledAdkRunRequestBuildInput,
) -> bool:
    return (
        build_input.request_live_llm is True
        and build_input.request_ollama is True
        and build_input.allow_live_llm is True
        and build_input.allow_ollama is True
        and bool(build_input.live_llm_approval_ref)
    )
