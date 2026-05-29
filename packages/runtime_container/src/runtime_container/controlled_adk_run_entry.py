"""Productized controlled ADK run entry for runtime-container."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol
from contract_core.llm_invocation import (
    GovernedLlmInvocationService,
    LlmGovernancePrecondition,
    LlmInvocationResult,
)
from contract_core.model_routing import ModelRouteFacts
from contract_core.runtime import RuntimeInput, RuntimeProductizationGateConfigView

from runtime_container.governance_summary_pipeline import (
    build_runtime_container_governance_summary_payload_from_recorded_run,
    evaluate_runtime_productization_gating,
)
from runtime_container.llm_invocation_facade import (
    RuntimeContainerLlmInvocationFacade,
    build_runtime_container_llm_invocation_request,
)


DEFAULT_LLM_ROUTE_MODEL_NAME = "ollama/gemma4-pro:latest"
DEFAULT_PROMPT_PREVIEW_SANITIZED = "cognition run product input"
PROMPT_PREVIEW_KEYS = ("message", "input_summary", "instruction", "task", "prompt")
PROMPT_PREVIEW_MAX_LENGTH = 80
CHAT_CONTEXT_TEXT_MAX_LENGTH = 240


class RuntimeRunnerProtocol(Protocol):
    """Runtime runner shape consumed by the controlled run entry."""

    def run(self, runtime_input: RuntimeInput) -> Any:
        """Run a runtime input and return a runtime result."""


class RuntimeAssemblyProtocol(Protocol):
    """Runtime assembly shape consumed through a protocol boundary."""

    runtime_runner: RuntimeRunnerProtocol
    metadata: Mapping[str, Any]


class GovernanceSummaryProviderAssemblyProtocol(Protocol):
    """Recorded-run provider holder consumed by governance summary projection."""

    recorded_run_evidence_provider: Any
    source: str


@dataclass(frozen=True)
class ControlledRunAgentShellRequest:
    """Provider request for controlled agent-shell audit execution."""

    options_metadata: Mapping[str, Any]
    input_text: str
    invocation_id: str
    runtime_id: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    live_enabled: bool = False
    live_client: Any | None = None


@dataclass(frozen=True)
class ControlledRunFunctionToolRequest:
    """Provider request for controlled function-tool audit execution."""

    options_metadata: Mapping[str, Any]
    task_ref: str
    task_kind: str
    evidence_ref: str | None
    invocation_id: str
    runtime_id: str
    tool_confirmation_granted: bool | None
    tool_approval_ref: str | None
    tool_confirmation_decision_source: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ControlledRunReadonlyBundleRequest:
    """Provider request for LLM invocation read-only product refs."""

    invocation_result: LlmInvocationResult
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ControlledRunSupportProviders:
    """Provider protocol set required by the controlled run entry."""

    governance_summary_provider_factory: Any
    no_live_agent_shell_runner: Any | None = None
    controlled_live_agent_shell_runner: Any | None = None
    no_live_function_tool_runner: Any | None = None
    llm_invocation_readonly_bundle_builder: Any | None = None


@dataclass(frozen=True)
class OperatorApprovalFacts:
    """Operator approval facts consumed before productized ADK execution."""

    approved: bool = False
    approval_ref: str | None = None
    approved_by: str | None = None
    audit_ref: str | None = None
    request_adk_run: bool | None = None
    allow_adk_run: bool | None = None
    allow_live_llm: bool | None = None
    allow_ollama: bool | None = None
    live_llm_approval_ref: str | None = None
    allow_tool_confirmation: bool | None = None
    tool_confirmation_approval_ref: str | None = None
    tool_confirmation_decision_source: str | None = None
    does_not_trigger_live_llm: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(
        cls,
        value: "OperatorApprovalFacts | Mapping[str, Any] | None",
    ) -> "OperatorApprovalFacts":
        """Build approval facts from a public mapping-like payload."""

        if value is None:
            return cls()
        if isinstance(value, cls):
            return value
        return cls(
            approved=bool(value.get("approved", False)),
            approval_ref=_optional_string(value.get("approval_ref")),
            approved_by=_optional_string(value.get("approved_by")),
            audit_ref=_optional_string(value.get("audit_ref")),
            request_adk_run=_optional_bool(value.get("request_adk_run")),
            allow_adk_run=_optional_bool(value.get("allow_adk_run")),
            allow_live_llm=_optional_bool(value.get("allow_live_llm")),
            allow_ollama=_optional_bool(value.get("allow_ollama")),
            live_llm_approval_ref=_optional_string(
                value.get("live_llm_approval_ref")
            ),
            allow_tool_confirmation=_optional_bool(
                value.get("allow_tool_confirmation")
            ),
            tool_confirmation_approval_ref=_optional_string(
                value.get("tool_confirmation_approval_ref")
            ),
            tool_confirmation_decision_source=_optional_string(
                value.get("tool_confirmation_decision_source")
            ),
            does_not_trigger_live_llm=bool(
                value.get("does_not_trigger_live_llm", True)
            ),
            metadata=dict(value.get("metadata") or {}),
        )

    def to_metadata(self) -> dict[str, Any]:
        """Return a sanitized approval summary without raw payloads."""

        return {
            "approved": self.approved,
            "approval_ref": self.approval_ref,
            "approved_by": self.approved_by,
            "audit_ref": self.audit_ref,
            "request_adk_run": self.request_adk_run,
            "allow_adk_run": self.allow_adk_run,
            "allow_live_llm": self.allow_live_llm,
            "allow_ollama": self.allow_ollama,
            "live_llm_approval_ref": self.live_llm_approval_ref,
            "allow_tool_confirmation": self.allow_tool_confirmation,
            "tool_confirmation_approval_ref": self.tool_confirmation_approval_ref,
            "tool_confirmation_decision_source": (
                self.tool_confirmation_decision_source
            ),
            "does_not_trigger_live_llm": self.does_not_trigger_live_llm,
            "metadata_keys": sorted(self.metadata),
        }


@dataclass(frozen=True)
class ControlledAdkRunRequest:
    """First-version product entry request for controlled ADK runs."""

    runtime_assembly: RuntimeAssemblyProtocol
    runtime_input: RuntimeInput
    productization_gate: RuntimeProductizationGateConfigView = field(
        default_factory=RuntimeProductizationGateConfigView
    )
    operator_approval: OperatorApprovalFacts | Mapping[str, Any] | None = None
    evidence_id: str | None = None
    llm_invocation_service: GovernedLlmInvocationService | None = None
    agent_shell_live_client: Any | None = field(default=None, repr=False)
    support_providers: ControlledRunSupportProviders | None = None


def evaluate_controlled_adk_run_final_preflight(
    *,
    productization_gate: RuntimeProductizationGateConfigView | None = None,
    operator_approval: OperatorApprovalFacts | Mapping[str, Any] | None = None,
    runtime_assembly_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate the final safety gate immediately before runtime execution."""

    gate = productization_gate or RuntimeProductizationGateConfigView()
    approval = OperatorApprovalFacts.from_value(operator_approval)
    gate_evaluation = evaluate_runtime_productization_gating(gate)
    metadata = dict(runtime_assembly_metadata or {})
    service_bundle = _mapping(metadata.get("service_bundle"))
    service_bundle_options = _mapping(
        _mapping(metadata.get("assembly_options")).get("service_bundle_options")
    )

    checked_fields: dict[str, bool] = {}
    blocking_reasons: list[str] = []
    warnings: list[str] = []

    def check(name: str, condition: bool, reason: str) -> None:
        checked_fields[name] = condition
        if not condition:
            blocking_reasons.append(reason)

    check(
        "productization_gating.runtime_execution_ready",
        gate_evaluation.runtime_execution_ready is True,
        "runtime_execution_ready_not_true",
    )
    check(
        "productization_gating.adk_run_allowed",
        gate_evaluation.adk_run_allowed is True,
        "adk_run_allowed_not_true",
    )
    check(
        "operator_approval.approved",
        approval.approved is True,
        "operator_approval_not_true",
    )
    check(
        "operator_approval.approval_ref",
        bool(approval.approval_ref),
        "operator_approval_ref_missing",
    )
    check(
        "operator_approval.does_not_trigger_live_llm",
        approval.does_not_trigger_live_llm is True,
        "operator_approval_live_llm_boundary_not_true",
    )
    check(
        "productization_gating.live_llm_allowed",
        gate_evaluation.live_llm_allowed is False,
        "live_llm_allowed_not_false",
    )
    check(
        "productization_gating.ollama_allowed",
        gate_evaluation.ollama_allowed is False,
        "ollama_allowed_not_false",
    )
    check(
        "productization_gating.adk_run_performed",
        gate_evaluation.adk_run_performed is False,
        "preflight_adk_run_performed_not_false",
    )
    check(
        "productization_gating.execution_performed",
        gate_evaluation.execution_performed is False,
        "preflight_execution_performed_not_false",
    )
    for field_name, reason in (
        ("sanitized_evidence_ref", "sanitized_evidence_ref_missing"),
        ("governance_summary_output_ref", "governance_summary_output_ref_missing"),
        ("audit_ref", "audit_ref_missing"),
    ):
        check(
            f"productization_gate.{field_name}",
            bool(getattr(gate, field_name)),
            reason,
        )

    if approval.request_adk_run is not None:
        check(
            "operator_approval.request_adk_run",
            approval.request_adk_run is True,
            "operator_approval_request_adk_run_not_true",
        )
    if approval.allow_adk_run is not None:
        check(
            "operator_approval.allow_adk_run",
            approval.allow_adk_run is True,
            "operator_approval_allow_adk_run_not_true",
        )
    if approval.audit_ref is not None:
        check(
            "operator_approval.audit_ref_matches_gate",
            approval.audit_ref == gate.audit_ref,
            "operator_approval_audit_ref_mismatch",
        )

    if service_bundle or service_bundle_options:
        service_source = service_bundle.get("source") or service_bundle_options.get(
            "source"
        )
        checked_fields["service_bundle.external_persistence_enabled"] = (
            service_bundle.get("external_persistence_enabled") is not True
            and service_bundle_options.get("external_persistence_enabled") is not True
        )
        if (
            service_bundle.get("external_persistence_enabled") is True
            or service_bundle_options.get("external_persistence_enabled") is True
        ):
            blocking_reasons.append("external_persistence_enabled_not_false")
        if service_source == "in_memory":
            warnings.append("service_bundle_source_in_memory")

    missing_conditions = list(gate_evaluation.missing_conditions)
    for reason in missing_conditions:
        if reason not in blocking_reasons:
            blocking_reasons.append(reason)

    return {
        "allowed": not blocking_reasons,
        "execution_scope": "productized_controlled_adk_run",
        "degrade_to_no_live": True,
        "blocking_reasons": blocking_reasons,
        "warnings": warnings,
        "checked_fields": checked_fields,
        "productization_gating": gate_evaluation.model_dump(mode="python"),
        "operator_approval": approval.to_metadata(),
        "sanitized_evidence_ref": gate.sanitized_evidence_ref,
        "governance_summary_output_ref": gate.governance_summary_output_ref,
        "audit_ref": gate.audit_ref,
    }


def evaluate_controlled_live_adk_run_final_preflight(
    *,
    productization_gate: RuntimeProductizationGateConfigView | None = None,
    operator_approval: OperatorApprovalFacts | Mapping[str, Any] | None = None,
    runtime_assembly_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate the final controlled-live gate without invoking a model."""

    gate = productization_gate or RuntimeProductizationGateConfigView()
    approval = OperatorApprovalFacts.from_value(operator_approval)
    gate_evaluation = evaluate_runtime_productization_gating(gate)
    live_preflight = evaluate_controlled_live_llm_preflight(
        productization_gate=gate,
        operator_approval=approval,
    )
    metadata = dict(runtime_assembly_metadata or {})
    service_bundle = _mapping(metadata.get("service_bundle"))
    service_bundle_options = _mapping(
        _mapping(metadata.get("assembly_options")).get("service_bundle_options")
    )

    checked_fields: dict[str, bool] = {}
    blocking_reasons: list[str] = []
    warnings: list[str] = []

    def check(name: str, condition: bool, reason: str) -> None:
        checked_fields[name] = condition
        if not condition:
            blocking_reasons.append(reason)

    check(
        "productization_gating.runtime_execution_ready",
        gate_evaluation.runtime_execution_ready is True,
        "runtime_execution_ready_not_true",
    )
    check(
        "productization_gating.adk_run_allowed",
        gate_evaluation.adk_run_allowed is True,
        "adk_run_allowed_not_true",
    )
    check(
        "controlled_live_llm_preflight.allowed",
        live_preflight["allowed"] is True,
        "controlled_live_llm_preflight_not_allowed",
    )
    check(
        "operator_approval.approved",
        approval.approved is True,
        "operator_approval_not_true",
    )
    check(
        "operator_approval.approval_ref",
        bool(approval.approval_ref),
        "operator_approval_ref_missing",
    )
    check(
        "operator_approval.live_llm_approval_ref",
        bool(approval.live_llm_approval_ref),
        "operator_approval_live_llm_ref_missing",
    )
    check(
        "operator_approval.does_not_trigger_live_llm",
        approval.does_not_trigger_live_llm is False,
        "operator_approval_live_llm_boundary_still_true",
    )
    check(
        "operator_approval.audit_ref_matches_gate",
        bool(approval.audit_ref) and approval.audit_ref == gate.audit_ref,
        "operator_approval_audit_ref_mismatch",
    )
    check(
        "productization_gating.adk_run_performed",
        gate_evaluation.adk_run_performed is False,
        "preflight_adk_run_performed_not_false",
    )
    check(
        "productization_gating.execution_performed",
        gate_evaluation.execution_performed is False,
        "preflight_execution_performed_not_false",
    )
    for field_name, reason in (
        ("sanitized_evidence_ref", "sanitized_evidence_ref_missing"),
        ("governance_summary_output_ref", "governance_summary_output_ref_missing"),
        ("audit_ref", "audit_ref_missing"),
    ):
        check(
            f"productization_gate.{field_name}",
            bool(getattr(gate, field_name)),
            reason,
        )

    if service_bundle or service_bundle_options:
        service_source = service_bundle.get("source") or service_bundle_options.get(
            "source"
        )
        checked_fields["service_bundle.external_persistence_enabled"] = (
            service_bundle.get("external_persistence_enabled") is not True
            and service_bundle_options.get("external_persistence_enabled") is not True
        )
        if (
            service_bundle.get("external_persistence_enabled") is True
            or service_bundle_options.get("external_persistence_enabled") is True
        ):
            blocking_reasons.append("external_persistence_enabled_not_false")
        if service_source == "in_memory":
            warnings.append("service_bundle_source_in_memory")

    for reason in live_preflight["blocking_reasons"]:
        if reason not in blocking_reasons:
            blocking_reasons.append(reason)
    for reason in gate_evaluation.missing_conditions:
        if reason not in blocking_reasons:
            blocking_reasons.append(reason)

    return {
        "allowed": not blocking_reasons,
        "execution_scope": "productized_controlled_live_adk_run",
        "degrade_to_no_live": bool(blocking_reasons),
        "runtime_call_performed": False,
        "live_llm_call_performed": False,
        "ollama_call_performed": False,
        "blocking_reasons": blocking_reasons,
        "warnings": warnings,
        "checked_fields": checked_fields,
        "controlled_live_llm_preflight": live_preflight,
        "productization_gating": gate_evaluation.model_dump(mode="python"),
        "operator_approval": approval.to_metadata(),
        "sanitized_evidence_ref": gate.sanitized_evidence_ref,
        "governance_summary_output_ref": gate.governance_summary_output_ref,
        "audit_ref": gate.audit_ref,
    }


def evaluate_controlled_live_llm_preflight(
    *,
    productization_gate: RuntimeProductizationGateConfigView | None = None,
    operator_approval: OperatorApprovalFacts | Mapping[str, Any] | None = None,
    route_facts: ModelRouteFacts | None = None,
    governance_precondition: LlmGovernancePrecondition | None = None,
) -> dict[str, Any]:
    """Evaluate the explicit controlled-live LLM gate without invoking a model."""

    gate = productization_gate or RuntimeProductizationGateConfigView()
    approval = OperatorApprovalFacts.from_value(operator_approval)
    gate_evaluation = evaluate_runtime_productization_gating(gate)
    route = route_facts or _default_llm_route_facts()
    governance = governance_precondition or LlmGovernancePrecondition(
        allowed=True,
        reason="controlled-live preflight candidate",
        decision="continue_controlled_live",
        governance_decision_ref=gate.governance_summary_output_ref,
        metadata={"source": "runtime_container.controlled_adk_run_entry"},
    )

    checked_fields: dict[str, bool] = {}
    blocking_reasons: list[str] = []

    def check(name: str, condition: bool, reason: str) -> None:
        checked_fields[name] = condition
        if not condition:
            blocking_reasons.append(reason)

    check(
        "productization_gating.live_llm_allowed",
        gate_evaluation.live_llm_allowed is True,
        "live_llm_allowed_not_true",
    )
    check(
        "productization_gating.ollama_allowed",
        gate_evaluation.ollama_allowed is True,
        "ollama_allowed_not_true",
    )
    check(
        "operator_approval.allow_live_llm",
        approval.allow_live_llm is True,
        "operator_approval_allow_live_llm_not_true",
    )
    check(
        "operator_approval.allow_ollama",
        approval.allow_ollama is True,
        "operator_approval_allow_ollama_not_true",
    )
    check(
        "operator_approval.does_not_trigger_live_llm",
        approval.does_not_trigger_live_llm is False,
        "operator_approval_live_llm_boundary_still_true",
    )
    check(
        "operator_approval.approval_ref",
        bool(approval.approval_ref),
        "operator_approval_ref_missing",
    )
    check(
        "operator_approval.live_llm_approval_ref",
        bool(approval.live_llm_approval_ref),
        "operator_approval_live_llm_ref_missing",
    )
    check(
        "operator_approval.audit_ref_matches_gate",
        bool(approval.audit_ref) and approval.audit_ref == gate.audit_ref,
        "operator_approval_audit_ref_mismatch",
    )
    check(
        "productization_gate.sanitized_evidence_ref",
        bool(gate.sanitized_evidence_ref),
        "sanitized_evidence_ref_missing",
    )
    check(
        "productization_gate.governance_summary_output_ref",
        bool(gate.governance_summary_output_ref),
        "governance_summary_output_ref_missing",
    )
    check(
        "productization_gate.audit_ref",
        bool(gate.audit_ref),
        "audit_ref_missing",
    )
    check(
        "route_facts.provider",
        route.provider == "litellm",
        "route_provider_not_litellm",
    )
    check(
        "route_facts.backend_provider",
        route.metadata.get("backend_provider") == "ollama",
        "route_backend_provider_not_ollama",
    )
    check(
        "route_facts.route_kind",
        route.metadata.get("route_kind") == "adk_litellm",
        "route_kind_not_adk_litellm",
    )
    check(
        "route_facts.route_target_matches_model",
        route.metadata.get("route_target") == route.model_name,
        "route_target_model_mismatch",
    )
    check(
        "governance_precondition.allowed",
        governance.allowed is True,
        "governance_precondition_not_allowed",
    )

    return {
        "allowed": not blocking_reasons,
        "execution_scope": "controlled_live_llm_preflight",
        "runtime_call_performed": False,
        "live_llm_call_performed": False,
        "ollama_call_performed": False,
        "degrade_to_no_live": bool(blocking_reasons),
        "blocking_reasons": blocking_reasons,
        "checked_fields": checked_fields,
        "route_facts": {
            "model_name": route.model_name,
            "provider": route.provider,
            "backend_provider": route.metadata.get("backend_provider"),
            "route_kind": route.metadata.get("route_kind"),
        },
        "governance_precondition": {
            "allowed": governance.allowed,
            "decision": governance.decision,
            "governance_decision_ref": governance.governance_decision_ref,
        },
        "operator_approval": approval.to_metadata(),
        "productization_gating": gate_evaluation.model_dump(mode="python"),
    }


def run_productized_controlled_adk_run(
    request: ControlledAdkRunRequest,
) -> dict[str, Any]:
    """Run a controlled ADK-backed runtime only after final preflight passes."""

    controlled_live_requested = _explicit_controlled_live_requested(request)
    if controlled_live_requested:
        final_preflight = evaluate_controlled_live_adk_run_final_preflight(
            productization_gate=request.productization_gate,
            operator_approval=request.operator_approval,
            runtime_assembly_metadata=request.runtime_assembly.metadata,
        )
    else:
        final_preflight = evaluate_controlled_adk_run_final_preflight(
            productization_gate=request.productization_gate,
            operator_approval=request.operator_approval,
            runtime_assembly_metadata=request.runtime_assembly.metadata,
        )
    if not final_preflight["allowed"]:
        return _blocked_result(
            request=request,
            final_preflight=final_preflight,
        )

    runtime_result = request.runtime_assembly.runtime_runner.run(request.runtime_input)
    governance_provider_assembly = _governance_summary_provider_assembly(
        request=request,
    )
    governance_summary_payload = (
        build_runtime_container_governance_summary_payload_from_recorded_run(
            runtime_result=runtime_result,
            recorded_run_evidence_provider=(
                governance_provider_assembly.recorded_run_evidence_provider
            ),
            gating=request.productization_gate,
            evidence_id=request.evidence_id,
        )
    )
    if controlled_live_requested:
        agent_shell_audit = _run_controlled_live_agent_shell(
            request=request,
            final_preflight=final_preflight,
        )
    else:
        agent_shell_audit = _run_no_live_agent_shell(request=request)
    if controlled_live_requested:
        llm_invocation_summary = _run_controlled_live_llm_invocation(
            request=request,
            governance_summary_payload=governance_summary_payload,
        )
    else:
        llm_invocation_summary = _run_no_live_llm_invocation(
            request=request,
            governance_summary_payload=governance_summary_payload,
        )
    tool_audit = _run_no_live_function_tool(request=request)
    governance_summary_payload = {
        **governance_summary_payload,
        "agent_shell_audit": agent_shell_audit,
        "tool_audit": tool_audit,
        "llm_invocation_audit": _llm_invocation_audit_summary(
            llm_invocation_summary
        ),
    }
    tool_summary = _tool_audit_summary(tool_audit)

    return {
        **_base_result(
            request=request,
            final_preflight=final_preflight,
        ),
        "adk_run_allowed": True,
        "adk_run_performed": True,
        "execution_performed": True,
        "runtime_result_summary": _runtime_result_summary(runtime_result),
        "workflow_result_summary": _workflow_result_summary(runtime_result),
        "lifecycle_facts": governance_summary_payload["lifecycle_summary"],
        "run_config_service_bundle_facts": governance_summary_payload[
            "run_config_service_bundle_summary"
        ],
        "governance_summary_payload": governance_summary_payload,
        "governance_summary_payload_ref": (
            request.productization_gate.governance_summary_output_ref
        ),
        **tool_summary,
        **llm_invocation_summary,
        "observability_source": governance_provider_assembly.source,
        "raw_adk_object_included": False,
        "raw_state_values_included": False,
        "artifact_content_included": False,
    }


def _blocked_result(
    *,
    request: ControlledAdkRunRequest,
    final_preflight: dict[str, Any],
) -> dict[str, Any]:
    return {
        **_base_result(request=request, final_preflight=final_preflight),
        "adk_run_allowed": False,
        "adk_run_performed": False,
        "execution_performed": False,
        "runtime_result_summary": None,
        "workflow_result_summary": None,
        "lifecycle_facts": None,
        "run_config_service_bundle_facts": None,
        "governance_summary_payload": None,
        "governance_summary_payload_ref": (
            request.productization_gate.governance_summary_output_ref
        ),
        **_tool_audit_summary(
            _function_tool_not_run_summary(failure_type="preflight_blocked")
        ),
        **_llm_invocation_not_run_summary(failure_type="preflight_blocked"),
        "blocking_result": "runtime_not_executed",
        "raw_adk_object_included": False,
        "raw_state_values_included": False,
        "artifact_content_included": False,
    }


def _base_result(
    *,
    request: ControlledAdkRunRequest,
    final_preflight: dict[str, Any],
) -> dict[str, Any]:
    gate_evaluation = final_preflight["productization_gating"]
    controlled_live_allowed = (
        final_preflight.get("execution_scope") == "productized_controlled_live_adk_run"
        and final_preflight.get("allowed") is True
    )
    return {
        "execution_mode": "productized_controlled_adk_run",
        "controlled_run": True,
        "productized_controlled_run": True,
        "dev_only": False,
        "product_cli": False,
        "runtime_id": request.runtime_input.runtime_id,
        "invocation_id": request.runtime_input.invocation_ref.invocation_id,
        "workflow_id": request.runtime_input.workflow_ref.workflow_id,
        "sanitized": True,
        "sanitized_evidence_ref": request.productization_gate.sanitized_evidence_ref,
        "governance_summary_output_ref": (
            request.productization_gate.governance_summary_output_ref
        ),
        "audit_ref": request.productization_gate.audit_ref,
        "live_llm_allowed": bool(gate_evaluation["live_llm_allowed"]),
        "live_llm_call_performed": False,
        "ollama_allowed": bool(gate_evaluation["ollama_allowed"]),
        "ollama_call_performed": False,
        "controlled_live_llm_preflight": evaluate_controlled_live_llm_preflight(
            productization_gate=request.productization_gate,
            operator_approval=request.operator_approval,
        ),
        "final_preflight": final_preflight,
        "blocking_reasons": list(final_preflight["blocking_reasons"]),
        "warnings": list(final_preflight["warnings"]),
        "summary": {
            "source": "runtime_container.controlled_adk_run_entry",
            "does_not_call_live_llm": not controlled_live_allowed,
            "does_not_call_ollama": not controlled_live_allowed,
            "does_not_enable_external_persistence": True,
            "does_not_enable_tool_eval_memory_mcp_a2a": True,
            "uses_composition_runtime_assembly": True,
            "cognition_agent_readonly_boundary": True,
        },
    }


def _required_support_providers(
    request: ControlledAdkRunRequest,
) -> ControlledRunSupportProviders:
    if request.support_providers is None:
        raise RuntimeError("controlled_run_support_providers_required")
    return request.support_providers


def _governance_summary_provider_assembly(
    *,
    request: ControlledAdkRunRequest,
) -> GovernanceSummaryProviderAssemblyProtocol:
    support = _required_support_providers(request)
    return support.governance_summary_provider_factory(
        runtime_assembly=request.runtime_assembly,
        evidence_bundle_ref=request.productization_gate.sanitized_evidence_ref,
    )


def _run_no_live_llm_invocation(
    *,
    request: ControlledAdkRunRequest,
    governance_summary_payload: Mapping[str, Any],
) -> dict[str, Any]:
    service = request.llm_invocation_service
    if service is None:
        return _llm_invocation_not_run_summary(failure_type="service_unavailable")

    request_id = _llm_invocation_request_id(request)
    facade = RuntimeContainerLlmInvocationFacade(
        service=service,
        metadata={
            "source": "runtime_container.controlled_adk_run_entry",
            "product_entry": "cognition_run",
            "no_live_gate": True,
        },
    )
    invocation_request = build_runtime_container_llm_invocation_request(
        request_id=request_id,
        route_facts=_default_llm_route_facts(),
        governance_precondition=_llm_governance_precondition(
            request=request,
            governance_summary_payload=governance_summary_payload,
        ),
        prompt_ref=f"input-payload-ref://{request.runtime_input.runtime_id}",
        prompt_preview_sanitized=_prompt_preview_from_runtime_input(request),
        metadata={
            "source": "runtime_container.controlled_adk_run_entry",
            "product_entry": "cognition_run",
            "workflow_id": request.runtime_input.workflow_ref.workflow_id,
            "runtime_id": request.runtime_input.runtime_id,
            "no_live_default": True,
            "does_not_call_live_llm": True,
            "does_not_call_ollama": True,
        },
    )
    result = facade.run(invocation_request)
    return _llm_invocation_result_summary(
        result,
        request=request,
        controlled_live=False,
    )


def _run_no_live_agent_shell(
    *,
    request: ControlledAdkRunRequest,
) -> dict[str, Any]:
    support = _required_support_providers(request)
    if support.no_live_agent_shell_runner is None:
        return _agent_shell_not_run_summary(failure_type="agent_shell_runner_unavailable")
    try:
        product_run = support.no_live_agent_shell_runner(
            ControlledRunAgentShellRequest(
                options_metadata=dict(request.runtime_input.metadata),
                input_text=_prompt_preview_from_runtime_input(request),
                invocation_id=(
                    f"agent-shell-{request.runtime_input.invocation_ref.invocation_id}"
                ),
                runtime_id=request.runtime_input.runtime_id,
                metadata={
                    "source": "runtime_container.controlled_adk_run_entry",
                    "audit_ref": request.productization_gate.audit_ref,
                    "sanitized_evidence_ref": (
                        request.productization_gate.sanitized_evidence_ref
                    ),
                    "governance_summary_output_ref": (
                        request.productization_gate.governance_summary_output_ref
                    ),
                },
            )
        )
    except Exception as exc:  # noqa: BLE001
        return _agent_shell_not_run_summary(
            failure_type="agent_shell_run_failed",
            error_type=type(exc).__name__,
        )
    return _audit_mapping(product_run)


def _run_controlled_live_agent_shell(
    *,
    request: ControlledAdkRunRequest,
    final_preflight: Mapping[str, Any],
) -> dict[str, Any]:
    if not final_preflight.get("allowed"):
        return _agent_shell_not_run_summary(
            failure_type="controlled_live_agent_shell_preflight_not_allowed"
        )

    support = _required_support_providers(request)
    if support.controlled_live_agent_shell_runner is None:
        return _agent_shell_not_run_summary(
            failure_type="controlled_live_agent_shell_runner_unavailable"
        )

    try:
        smoke_result = support.controlled_live_agent_shell_runner(
            ControlledRunAgentShellRequest(
                options_metadata=dict(request.runtime_input.metadata),
                input_text=_prompt_preview_from_runtime_input(request),
                invocation_id=(
                    "agent-shell-live-"
                    f"{request.runtime_input.invocation_ref.invocation_id}"
                ),
                runtime_id=request.runtime_input.runtime_id,
                live_enabled=bool(final_preflight.get("allowed")),
                live_client=request.agent_shell_live_client,
                metadata={
                    "source": "runtime_container.controlled_adk_run_entry",
                    "product_entry": "cognition_run",
                    "confirmation_mapping": (
                        "operator_approval_ref_to_adk_tool_confirmation"
                    ),
                    "audit_ref": request.productization_gate.audit_ref,
                    "sanitized_evidence_ref": (
                        request.productization_gate.sanitized_evidence_ref
                    ),
                    "governance_summary_output_ref": (
                        request.productization_gate.governance_summary_output_ref
                    ),
                    "live_llm_approval_ref": (
                        OperatorApprovalFacts.from_value(
                            request.operator_approval
                        ).live_llm_approval_ref
                    ),
                },
            )
        )
    except Exception as exc:  # noqa: BLE001
        return _agent_shell_not_run_summary(
            failure_type="controlled_live_agent_shell_run_failed",
            error_type=type(exc).__name__,
        )
    return _audit_mapping(smoke_result)

def _run_controlled_live_llm_invocation(
    *,
    request: ControlledAdkRunRequest,
    governance_summary_payload: Mapping[str, Any],
) -> dict[str, Any]:
    service = request.llm_invocation_service
    if service is None:
        return _llm_invocation_not_run_summary(failure_type="service_unavailable")

    request_id = _llm_invocation_request_id(request)
    facade = RuntimeContainerLlmInvocationFacade(
        service=service,
        metadata={
            "source": "runtime_container.controlled_adk_run_entry",
            "product_entry": "cognition_run",
            "controlled_live_gate": True,
        },
    )
    invocation_request = build_runtime_container_llm_invocation_request(
        request_id=request_id,
        route_facts=_default_llm_route_facts(),
        governance_precondition=_llm_governance_precondition(
            request=request,
            governance_summary_payload=governance_summary_payload,
            controlled_live=True,
        ),
        prompt_ref=f"input-payload-ref://{request.runtime_input.runtime_id}",
        prompt_preview_sanitized=_prompt_preview_from_runtime_input(request),
        metadata={
            "source": "runtime_container.controlled_adk_run_entry",
            "product_entry": "cognition_run",
            "workflow_id": request.runtime_input.workflow_ref.workflow_id,
            "runtime_id": request.runtime_input.runtime_id,
            "interaction_mode": _interaction_mode_from_runtime_input(request),
            "controlled_live": True,
            "live_llm_allowed": True,
            "ollama_allowed": True,
            **_chat_context_metadata_from_runtime_input(request),
        },
    )
    result = facade.run(invocation_request)
    return _llm_invocation_result_summary(
        result,
        request=request,
        controlled_live=True,
    )


def _run_no_live_function_tool(
    *,
    request: ControlledAdkRunRequest,
) -> dict[str, Any]:
    approval = OperatorApprovalFacts.from_value(request.operator_approval)
    support = _required_support_providers(request)
    if support.no_live_function_tool_runner is None:
        return _function_tool_not_run_summary(
            failure_type="function_tool_runner_unavailable"
        )
    try:
        product_run = support.no_live_function_tool_runner(
            ControlledRunFunctionToolRequest(
                options_metadata=dict(request.runtime_input.metadata),
                task_ref=f"runtime-input://{request.runtime_input.runtime_id}",
                task_kind="controlled_adk_run_product_entry",
                evidence_ref=request.productization_gate.sanitized_evidence_ref,
                invocation_id=(
                    "function-tool-"
                    f"{request.runtime_input.invocation_ref.invocation_id}"
                ),
                runtime_id=request.runtime_input.runtime_id,
                tool_confirmation_granted=_tool_confirmation_granted(approval),
                tool_approval_ref=(
                    approval.tool_confirmation_approval_ref
                    or approval.approval_ref
                ),
                tool_confirmation_decision_source=(
                    approval.tool_confirmation_decision_source
                    or "runtime_container.operator_approval"
                ),
                metadata={
                    "source": "runtime_container.controlled_adk_run_entry",
                    "product_entry": "cognition_run",
                    "audit_ref": request.productization_gate.audit_ref,
                    "sanitized_evidence_ref": (
                        request.productization_gate.sanitized_evidence_ref
                    ),
                    "governance_summary_output_ref": (
                        request.productization_gate.governance_summary_output_ref
                    ),
                },
            )
        )
    except Exception as exc:  # noqa: BLE001
        return _function_tool_not_run_summary(
            failure_type="function_tool_run_failed",
            error_type=type(exc).__name__,
        )
    return _audit_mapping(product_run)


def _function_tool_not_run_summary(
    *,
    failure_type: str,
    error_type: str | None = None,
) -> dict[str, Any]:
    return {
        "tool_evidence_ref": None,
        "tool_run_ref": None,
        "tool_name": None,
        "tool_kind": None,
        "status": "not_run" if error_type is None else "failed",
        "tool_call_allowed": False,
        "tool_call_attempted": False,
        "tool_runtime_call_performed": False,
        "tool_confirmation_required": False,
        "tool_confirmation_granted": False,
        "adk_tool_confirmation_requested": False,
        "tool_approval_ref": None,
        "tool_confirmation_decision_source": None,
        "tool_input_summary": {},
        "tool_output_summary": {},
        "tool_failure_type": failure_type,
        "readonly_facts_embedded": False,
        "does_not_store_raw_tool_input": True,
        "does_not_store_raw_tool_output": True,
        "raw_adk_object_included": False,
        "error_type": error_type,
    }


def _audit_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_governance_audit"):
        audit = value.to_governance_audit()
        if isinstance(audit, Mapping):
            return dict(audit)
    return {}


def _public_refs_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_public_refs"):
        refs = value.to_public_refs()
        if isinstance(refs, Mapping):
            return dict(refs)
    return {}


def _tool_audit_summary(tool_audit: Mapping[str, Any] | None) -> dict[str, Any]:
    audit = _mapping(tool_audit)
    return {
        "tool_evidence_ref": _optional_string(audit.get("tool_evidence_ref")),
        "tool_run_ref": _optional_string(audit.get("tool_run_ref")),
        "tool_status": _optional_string(audit.get("status")),
        "tool_failure_type": _optional_string(audit.get("tool_failure_type")),
        "tool_runtime_call_performed": bool(
            audit.get("tool_runtime_call_performed", False)
        ),
    }


def _tool_confirmation_granted(approval: OperatorApprovalFacts) -> bool | None:
    if approval.allow_tool_confirmation is not None:
        return approval.allow_tool_confirmation
    if approval.tool_confirmation_approval_ref is not None:
        return None
    return approval.approved


def _agent_shell_not_run_summary(
    *,
    failure_type: str,
    error_type: str | None = None,
) -> dict[str, Any]:
    return {
        "agent_shell_evidence_ref": None,
        "agent_shell_run_ref": None,
        "agent_name": None,
        "agent_type": None,
        "app_name": None,
        "session_id": None,
        "requested_invocation_id": None,
        "adk_invocation_id": None,
        "status": "not_run" if error_type is None else "failed",
        "event_count": 0,
        "event_authors": [],
        "no_live_execution_observed": False,
        "runtime_call_performed": False,
        "failure_type": failure_type,
        "error_type": error_type,
        "readonly_facts_embedded": False,
        "does_not_store_prompt": True,
        "does_not_store_raw_response": True,
        "raw_adk_object_included": False,
        "raw_adk_event_included": False,
        "raw_adk_session_included": False,
    }


def _default_llm_route_facts() -> ModelRouteFacts:
    return ModelRouteFacts(
        model_name=DEFAULT_LLM_ROUTE_MODEL_NAME,
        provider="litellm",
        source="runtime_container.controlled_adk_run_entry",
        metadata={
            "backend_provider": "ollama",
            "route_target": DEFAULT_LLM_ROUTE_MODEL_NAME,
            "route_kind": "adk_litellm",
            "route_fact_contract": "schemas.model_routing.ModelRouteFacts",
            "does_not_construct_litellm_object": True,
            "does_not_call_model": True,
        },
    )


def _prompt_preview_from_runtime_input(request: ControlledAdkRunRequest) -> str:
    payload = request.runtime_input.input_payload
    if _interaction_mode_from_runtime_input(request) == "cli_chat":
        chat_preview = _chat_current_input_preview_from_payload(payload)
        if chat_preview:
            return chat_preview
    for key in PROMPT_PREVIEW_KEYS:
        value = payload.get(key)
        if not isinstance(value, str):
            continue
        preview = _normalize_prompt_preview(value)
        if preview:
            return preview
    return DEFAULT_PROMPT_PREVIEW_SANITIZED


def _chat_current_input_preview_from_payload(payload: Mapping[str, Any]) -> str:
    current_input = payload.get("input_summary")
    if not isinstance(current_input, str):
        return ""
    return _normalize_prompt_preview(current_input)


def _chat_context_metadata_from_runtime_input(
    request: ControlledAdkRunRequest,
) -> dict[str, Any]:
    if _interaction_mode_from_runtime_input(request) != "cli_chat":
        return {}

    payload = request.runtime_input.input_payload
    current_input = payload.get("input_summary")
    if not isinstance(current_input, str):
        current_user_input = ""
    else:
        current_user_input = _normalize_prompt_preview(
            current_input,
            limit=CHAT_CONTEXT_TEXT_MAX_LENGTH,
        )

    return {
        "cli_chat_context": {
            "current_user_input": current_user_input,
            "history": _chat_history_items(payload.get("turn_history_summary")),
        }
    }


def _chat_history_items(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list | tuple):
        return []

    items: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, Mapping):
            user_text = _normalize_prompt_preview(
                str(item.get("user") or ""),
                limit=CHAT_CONTEXT_TEXT_MAX_LENGTH,
            )
            assistant_text = _normalize_prompt_preview(
                str(item.get("assistant") or ""),
                limit=CHAT_CONTEXT_TEXT_MAX_LENGTH,
            )
            if user_text or assistant_text:
                items.append({"user": user_text, "assistant": assistant_text})
        elif isinstance(item, str):
            user_text = _normalize_prompt_preview(
                item,
                limit=CHAT_CONTEXT_TEXT_MAX_LENGTH,
            )
            if user_text:
                items.append({"user": user_text, "assistant": ""})
    return items


def _interaction_mode_from_runtime_input(request: ControlledAdkRunRequest) -> str:
    payload = request.runtime_input.input_payload
    if isinstance(payload.get("chat_session_id"), str):
        return "cli_chat"
    return "controlled_run"


def _normalize_prompt_preview(
    value: str,
    *,
    limit: int = PROMPT_PREVIEW_MAX_LENGTH,
) -> str:
    preview = " ".join(value.strip().split())
    if len(preview) > limit:
        return preview[:limit]
    return preview


def _llm_governance_precondition(
    *,
    request: ControlledAdkRunRequest,
    governance_summary_payload: Mapping[str, Any],
    controlled_live: bool = False,
) -> LlmGovernancePrecondition:
    if controlled_live:
        return LlmGovernancePrecondition(
            allowed=True,
            reason="cognition run controlled-live governed LLM service boundary allowed",
            decision="continue_controlled_live",
            governance_decision_ref=(
                request.productization_gate.governance_summary_output_ref
            ),
            metadata={
                "source": "runtime_container.controlled_adk_run_entry",
                "audit_ref": request.productization_gate.audit_ref,
                "sanitized_evidence_ref": (
                    request.productization_gate.sanitized_evidence_ref
                ),
                "governance_summary_output_ref": (
                    request.productization_gate.governance_summary_output_ref
                ),
                "governance_summary_evidence_id": _optional_string(
                    governance_summary_payload.get("evidence_id")
                ),
                "controlled_live_gate": True,
                "live_llm_allowed": True,
                "ollama_allowed": True,
            },
        )
    return LlmGovernancePrecondition(
        allowed=True,
        reason="cognition run no-live governed LLM service boundary allowed",
        decision="continue_no_live",
        governance_decision_ref=request.productization_gate.governance_summary_output_ref,
        metadata={
            "source": "runtime_container.controlled_adk_run_entry",
            "audit_ref": request.productization_gate.audit_ref,
            "sanitized_evidence_ref": request.productization_gate.sanitized_evidence_ref,
            "governance_summary_output_ref": (
                request.productization_gate.governance_summary_output_ref
            ),
            "governance_summary_evidence_id": _optional_string(
                governance_summary_payload.get("evidence_id")
            ),
            "no_live_gate": True,
            "live_llm_allowed": False,
            "ollama_allowed": False,
        },
    )


def _llm_invocation_result_summary(
    result: LlmInvocationResult,
    *,
    request: ControlledAdkRunRequest,
    controlled_live: bool = False,
) -> dict[str, Any]:
    request_id = result.request_id
    support = _required_support_providers(request)
    if support.llm_invocation_readonly_bundle_builder is None:
        return _llm_invocation_not_run_summary(
            failure_type="readonly_bundle_builder_unavailable"
        )
    readonly_bundle = support.llm_invocation_readonly_bundle_builder(
        ControlledRunReadonlyBundleRequest(
            invocation_result=result,
            metadata={
                "source": "runtime_container.controlled_adk_run_entry",
                "product_entry": "cognition_run",
            },
        )
    )
    readonly_refs = _public_refs_mapping(readonly_bundle)
    readonly_facts = dict(readonly_refs["llm_invocation_readonly_facts"])
    display_text = _optional_string(result.metadata.get("sanitized_response_display"))
    if display_text is not None:
        readonly_facts["sanitized_response_display"] = display_text
    return {
        "llm_invocation_result_ref": f"llm-invocation-result://{request_id}",
        "llm_invocation_observation_ref": readonly_refs[
            "llm_invocation_observation_ref"
        ],
        "llm_invocation_summary_ref": readonly_refs["llm_invocation_summary_ref"],
        "llm_invocation_call_allowed": result.call_allowed,
        "llm_invocation_call_attempted": result.call_attempted,
        "llm_invocation_runtime_call_performed": result.runtime_call_performed,
        "llm_invocation_failure_type": (
            result.failure_type.value if result.failure_type is not None else None
        ),
        "live_llm_call_performed": controlled_live and result.runtime_call_performed,
        "ollama_call_performed": controlled_live and result.runtime_call_performed,
        "llm_invocation_readonly_facts": readonly_facts,
    }


def _llm_invocation_audit_summary(
    llm_invocation_summary: Mapping[str, Any],
) -> dict[str, Any] | None:
    result_ref = _optional_string(
        llm_invocation_summary.get("llm_invocation_result_ref")
    )
    observation_ref = _optional_string(
        llm_invocation_summary.get("llm_invocation_observation_ref")
    )
    summary_ref = _optional_string(
        llm_invocation_summary.get("llm_invocation_summary_ref")
    )
    if result_ref is None and observation_ref is None and summary_ref is None:
        return None

    readonly_facts = llm_invocation_summary.get("llm_invocation_readonly_facts")
    live_profile = None
    if isinstance(readonly_facts, Mapping):
        live_profile = _compact_live_profile(readonly_facts.get("live_profile"))

    runtime_call_performed = bool(
        llm_invocation_summary.get("llm_invocation_runtime_call_performed")
    )
    live_llm_call_performed = bool(
        llm_invocation_summary.get("live_llm_call_performed")
    )
    ollama_call_performed = bool(
        llm_invocation_summary.get("ollama_call_performed")
    )
    return {
        "llm_invocation_result_ref": result_ref,
        "llm_invocation_observation_ref": observation_ref,
        "llm_invocation_summary_ref": summary_ref,
        "call_allowed": bool(
            llm_invocation_summary.get("llm_invocation_call_allowed")
        ),
        "call_attempted": bool(
            llm_invocation_summary.get("llm_invocation_call_attempted")
        ),
        "runtime_call_performed": runtime_call_performed,
        "failure_type": _optional_string(
            llm_invocation_summary.get("llm_invocation_failure_type")
        ),
        "controlled_live": (
            live_llm_call_performed or ollama_call_performed or live_profile is not None
        ),
        "live_llm_call_performed": live_llm_call_performed,
        "ollama_call_performed": ollama_call_performed,
        "live_profile": live_profile,
        "readonly_facts_embedded": False,
        "does_not_store_prompt": True,
        "does_not_store_raw_provider_response": True,
    }


def _llm_invocation_not_run_summary(*, failure_type: str) -> dict[str, Any]:
    return {
        "llm_invocation_result_ref": None,
        "llm_invocation_observation_ref": None,
        "llm_invocation_summary_ref": None,
        "llm_invocation_call_allowed": False,
        "llm_invocation_call_attempted": False,
        "llm_invocation_runtime_call_performed": False,
        "llm_invocation_failure_type": failure_type,
        "llm_invocation_readonly_facts": None,
    }


def _llm_invocation_request_id(request: ControlledAdkRunRequest) -> str:
    return f"llm-invocation-{request.runtime_input.invocation_ref.invocation_id}"


def _compact_live_profile(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    allowed_keys = (
        "controlled_live",
        "live_options_source",
        "live_service_profile",
        "configured_model_name",
        "timeout_seconds",
        "temperature",
        "max_tokens",
        "local_no_proxy_applied",
    )
    profile = {
        key: item
        for key in allowed_keys
        if (item := value.get(key)) is not None
        and isinstance(item, bool | int | float | str)
    }
    return profile or None


def _explicit_controlled_live_requested(request: ControlledAdkRunRequest) -> bool:
    approval = OperatorApprovalFacts.from_value(request.operator_approval)
    gate = request.productization_gate
    return (
        gate.request_live_llm is True
        and gate.request_ollama is True
        and gate.allow_live_llm is True
        and gate.allow_ollama is True
        and approval.does_not_trigger_live_llm is False
    )


def _runtime_result_summary(runtime_result: Any) -> dict[str, Any]:
    return {
        "runtime_id": runtime_result.runtime_id,
        "status": _enum_value(runtime_result.status),
        "invocation_id": runtime_result.invocation_ref.invocation_id,
        "event_count": len(runtime_result.events),
        "state_delta_count": len(runtime_result.state_deltas),
        "artifact_delta_count": len(runtime_result.artifact_deltas),
        "error_count": len(runtime_result.errors),
        "metadata_keys": sorted(runtime_result.metadata),
    }


def _workflow_result_summary(runtime_result: Any) -> dict[str, Any] | None:
    workflow_result = runtime_result.workflow_result
    if workflow_result is None:
        return None
    return {
        "workflow_id": workflow_result.workflow_ref.workflow_id,
        "workflow_name": workflow_result.workflow_ref.name,
        "status": _enum_value(workflow_result.status),
        "invocation_id": workflow_result.invocation_ref.invocation_id,
        "event_count": len(workflow_result.events),
        "state_delta_count": len(workflow_result.state_deltas),
        "artifact_delta_count": len(workflow_result.artifact_deltas),
        "error_count": len(workflow_result.errors),
        "metadata_keys": sorted(workflow_result.metadata),
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)
