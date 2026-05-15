"""Agent-facing task context and advice candidates."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from cognition_agent.governed_run_evidence_context_view import (
    AgentGovernedRunEvidenceContextCandidate,
)
from cognition_agent.models import AgentBaseCandidate, AgentTaskCandidate
from cognition_agent.product_gateway_response_view import (
    AgentProductGatewayResponseViewCandidate,
)


TASK_CONTEXT_VERSION = "agent_task_context_v1"
TASK_CONTEXT_SOURCE = "cognition_agent.task_context"
TASK_ADVICE_VERSION = "agent_task_advice_v1"
TASK_ADVICE_SOURCE = "cognition_agent.task_advice"

FORBIDDEN_TASK_CONTEXT_KEYS = frozenset(
    {
        "api_key",
        "artifact_content",
        "completion",
        "credential",
        "credentials",
        "full_response",
        "message",
        "messages",
        "prompt",
        "raw_provider_response",
        "raw_response",
        "response",
        "response_text",
        "secret",
        "system_prompt",
        "text",
        "token",
    }
)


class AgentTaskContextCandidate(AgentBaseCandidate):
    """Product-facing read-only task context for cognition agent consumers."""

    candidate_type: str = "agent_task_context_candidate"
    context_version: str = TASK_CONTEXT_VERSION
    task_candidate_id: str
    task_intent: str | None = None
    task_goal: str | None = None
    task_input_summary: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    governed_run_evidence_context_candidate_id: str
    governance_summary_candidate_id: str
    llm_invocation_summary_candidate_id: str | None = None
    llm_invocation_result_ref: str | None = None
    llm_invocation_observation_ref: str | None = None
    llm_invocation_summary_ref: str | None = None
    controlled_live: bool = False
    agent_shell_audit_candidate_id: str | None = None
    agent_shell_evidence_ref: str | None = None
    agent_shell_run_ref: str | None = None
    agent_shell_status: str | None = None
    agent_shell_failure_type: str | None = None
    agent_shell_controlled_live: bool = False
    product_gateway_response_view_candidate_id: str | None = None
    product_gateway_request_id: str | None = None
    product_gateway_entry_kind: str | None = None
    product_gateway_status: str | None = None
    product_gateway_exit_code: int | None = None
    product_gateway_response_ref: str | None = None
    product_gateway_governance_summary_ref: str | None = None
    product_gateway_evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    product_gateway_audit_refs: list[dict[str, Any]] = Field(default_factory=list)
    product_gateway_agent_advice_refs: list[dict[str, Any]] = Field(
        default_factory=list
    )
    product_gateway_tool_audit_refs: list[dict[str, Any]] = Field(default_factory=list)
    product_gateway_blocking_reasons: list[str] = Field(default_factory=list)
    product_gateway_warnings: list[str] = Field(default_factory=list)
    product_gateway_ready_for_review: bool | None = None
    ready_for_review: bool = False
    evidence_warnings: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    readonly: bool = True
    candidate_only: bool = True
    execution_enabled: bool = False
    runtime_permission_granted: bool = False
    agent_runtime_enabled: bool = False
    llm_call_enabled: bool = False
    action_execution_enabled: bool = False
    chat_enabled: bool = False
    gateway_enabled: bool = False
    tool_execution_enabled: bool = False

    @model_validator(mode="after")
    def validate_task_context(self) -> "AgentTaskContextCandidate":
        _validate_non_executing_flags(self)
        violations = _forbidden_task_context_key_violations(
            self.model_dump(mode="python")
        )
        if violations:
            raise ValueError("; ".join(violations))
        return self


class AgentTaskAdviceCandidate(AgentBaseCandidate):
    """Read-only advice candidate derived from an agent task context."""

    candidate_type: str = "agent_task_advice_candidate"
    advice_version: str = TASK_ADVICE_VERSION
    task_context_candidate_id: str
    task_candidate_id: str
    agent_shell_audit_candidate_id: str | None = None
    agent_shell_evidence_ref: str | None = None
    agent_shell_run_ref: str | None = None
    agent_shell_status: str | None = None
    agent_shell_failure_type: str | None = None
    agent_shell_controlled_live: bool = False
    product_gateway_response_view_candidate_id: str | None = None
    product_gateway_request_id: str | None = None
    product_gateway_entry_kind: str | None = None
    product_gateway_status: str | None = None
    product_gateway_exit_code: int | None = None
    product_gateway_response_ref: str | None = None
    product_gateway_governance_summary_ref: str | None = None
    product_gateway_evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    product_gateway_audit_refs: list[dict[str, Any]] = Field(default_factory=list)
    product_gateway_agent_advice_refs: list[dict[str, Any]] = Field(
        default_factory=list
    )
    product_gateway_tool_audit_refs: list[dict[str, Any]] = Field(default_factory=list)
    product_gateway_blocking_reasons: list[str] = Field(default_factory=list)
    product_gateway_warnings: list[str] = Field(default_factory=list)
    product_gateway_ready_for_review: bool | None = None
    recommendation: str
    plan_steps: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    next_step: str
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    readonly: bool = True
    candidate_only: bool = True
    execution_enabled: bool = False
    runtime_permission_granted: bool = False
    agent_runtime_enabled: bool = False
    llm_call_enabled: bool = False
    action_execution_enabled: bool = False
    chat_enabled: bool = False
    gateway_enabled: bool = False
    tool_execution_enabled: bool = False

    @model_validator(mode="after")
    def validate_task_advice(self) -> "AgentTaskAdviceCandidate":
        _validate_non_executing_flags(self)
        violations = _forbidden_task_context_key_violations(
            self.model_dump(mode="python")
        )
        if violations:
            raise ValueError("; ".join(violations))
        return self


def build_agent_task_context_candidate(
    *,
    candidate_id: str,
    task: AgentTaskCandidate,
    governed_run_evidence_context: AgentGovernedRunEvidenceContextCandidate,
    task_goal: str | None = None,
    task_input_summary: str | None = None,
    source_refs: list[str] | None = None,
    constraints: list[str] | None = None,
    product_gateway_response_view: AgentProductGatewayResponseViewCandidate | None = None,
    metadata: dict[str, Any] | None = None,
    domain_metadata: dict[str, Any] | None = None,
) -> AgentTaskContextCandidate:
    """Build a non-executing agent task context from read-only evidence."""

    safe_metadata = _safe_mapping(metadata or {}, path="$.metadata")
    safe_domain_metadata = _safe_mapping(
        domain_metadata or {}, path="$.domain_metadata"
    )
    safe_source_refs = _safe_string_list(source_refs or (), path="$.source_refs")
    safe_constraints = _safe_string_list(constraints or (), path="$.constraints")
    evidence_warnings = list(governed_run_evidence_context.warnings)
    warnings = _task_context_warnings(
        task=task,
        governed_run_evidence_context=governed_run_evidence_context,
        product_gateway_response_view=product_gateway_response_view,
    )
    blocking_reasons = _task_context_blocking_reasons(
        task=task,
        product_gateway_response_view=product_gateway_response_view,
    )
    product_gateway_values = _product_gateway_values(product_gateway_response_view)

    return AgentTaskContextCandidate(
        candidate_id=candidate_id,
        source=TASK_CONTEXT_SOURCE,
        summary=_task_context_summary(
            task=task,
            governed_run_evidence_context=governed_run_evidence_context,
            blocking_reasons=blocking_reasons,
        ),
        task_candidate_id=task.candidate_id,
        task_intent=task.task_intent,
        task_goal=_optional_string(task_goal),
        task_input_summary=_optional_string(task_input_summary),
        source_refs=[
            *safe_source_refs,
            *_product_gateway_source_refs(product_gateway_response_view),
        ],
        governed_run_evidence_context_candidate_id=(
            governed_run_evidence_context.candidate_id
        ),
        governance_summary_candidate_id=(
            governed_run_evidence_context.governance_summary_candidate_id
        ),
        llm_invocation_summary_candidate_id=(
            governed_run_evidence_context.llm_invocation_summary_candidate_id
        ),
        llm_invocation_result_ref=governed_run_evidence_context.llm_invocation_result_ref,
        llm_invocation_observation_ref=(
            governed_run_evidence_context.llm_invocation_observation_ref
        ),
        llm_invocation_summary_ref=governed_run_evidence_context.llm_invocation_summary_ref,
        controlled_live=governed_run_evidence_context.controlled_live,
        agent_shell_audit_candidate_id=(
            governed_run_evidence_context.agent_shell_audit_candidate_id
        ),
        agent_shell_evidence_ref=governed_run_evidence_context.agent_shell_evidence_ref,
        agent_shell_run_ref=governed_run_evidence_context.agent_shell_run_ref,
        agent_shell_status=governed_run_evidence_context.agent_shell_status,
        agent_shell_failure_type=(
            governed_run_evidence_context.agent_shell_failure_type
        ),
        agent_shell_controlled_live=(
            governed_run_evidence_context.agent_shell_controlled_live
        ),
        **product_gateway_values,
        ready_for_review=(
            governed_run_evidence_context.ready_for_review
            and _product_gateway_ready_for_task_review(product_gateway_response_view)
        ),
        evidence_warnings=[
            *evidence_warnings,
            *(
                list(product_gateway_response_view.product_gateway_warnings)
                if product_gateway_response_view is not None
                else []
            ),
        ],
        constraints=safe_constraints,
        blocking_reasons=blocking_reasons,
        warnings=warnings,
        governance_refs=[
            *task.governance_refs,
            *governed_run_evidence_context.governance_refs,
            *_product_gateway_governance_refs(product_gateway_response_view),
        ],
        config_refs=[
            *task.config_refs,
            *governed_run_evidence_context.config_refs,
        ],
        metadata={
            "view_semantics": "agent_task_context_product_consumption_view",
            "readonly": True,
            "candidate_only": True,
            "context_version": TASK_CONTEXT_VERSION,
            "adk_context_is_not_created": True,
            "adk_session_is_not_created": True,
            "adk_event_is_not_created": True,
            "adk_artifact_is_not_created": True,
            "agent_runtime_enabled": False,
            "runtime_permission_granted": False,
            "does_not_call_runtime": True,
            "does_not_call_runtime_container": True,
            "does_not_call_composition": True,
            "does_not_call_llm": True,
            "does_not_execute_action": True,
            "does_not_enable_chat": True,
            "does_not_enable_gateway": True,
            "does_not_enable_tool_executor": True,
            "task_candidate_id": task.candidate_id,
            "governed_run_evidence_context_candidate_id": (
                governed_run_evidence_context.candidate_id
            ),
            "product_gateway_response_view_candidate_id": (
                product_gateway_response_view.candidate_id
                if product_gateway_response_view is not None
                else None
            ),
            "does_not_call_product_gateway": True,
            "product_gateway_response_is_readonly_summary": (
                product_gateway_response_view is not None
            ),
            "product_gateway_response_is_not_public_contract": (
                product_gateway_response_view is not None
            ),
            **safe_metadata,
        },
        domain_metadata=safe_domain_metadata,
    )


def build_agent_task_advice_candidate(
    *,
    candidate_id: str,
    task_context: AgentTaskContextCandidate,
    metadata: dict[str, Any] | None = None,
    domain_metadata: dict[str, Any] | None = None,
) -> AgentTaskAdviceCandidate:
    """Build deterministic read-only advice from an agent task context."""

    safe_metadata = _safe_mapping(metadata or {}, path="$.metadata")
    safe_domain_metadata = _safe_mapping(
        domain_metadata or {}, path="$.domain_metadata"
    )
    recommendation = _recommendation(task_context)
    plan_steps = _plan_steps(recommendation)
    risk_notes = _risk_notes(task_context=task_context, recommendation=recommendation)
    next_step = _next_step(recommendation)

    return AgentTaskAdviceCandidate(
        candidate_id=candidate_id,
        source=TASK_ADVICE_SOURCE,
        summary=_task_advice_summary(
            recommendation=recommendation,
            task_context=task_context,
        ),
        task_context_candidate_id=task_context.candidate_id,
        task_candidate_id=task_context.task_candidate_id,
        agent_shell_audit_candidate_id=task_context.agent_shell_audit_candidate_id,
        agent_shell_evidence_ref=task_context.agent_shell_evidence_ref,
        agent_shell_run_ref=task_context.agent_shell_run_ref,
        agent_shell_status=task_context.agent_shell_status,
        agent_shell_failure_type=task_context.agent_shell_failure_type,
        agent_shell_controlled_live=task_context.agent_shell_controlled_live,
        product_gateway_response_view_candidate_id=(
            task_context.product_gateway_response_view_candidate_id
        ),
        product_gateway_request_id=task_context.product_gateway_request_id,
        product_gateway_entry_kind=task_context.product_gateway_entry_kind,
        product_gateway_status=task_context.product_gateway_status,
        product_gateway_exit_code=task_context.product_gateway_exit_code,
        product_gateway_response_ref=task_context.product_gateway_response_ref,
        product_gateway_governance_summary_ref=(
            task_context.product_gateway_governance_summary_ref
        ),
        product_gateway_evidence_refs=list(task_context.product_gateway_evidence_refs),
        product_gateway_audit_refs=list(task_context.product_gateway_audit_refs),
        product_gateway_agent_advice_refs=list(
            task_context.product_gateway_agent_advice_refs
        ),
        product_gateway_tool_audit_refs=list(
            task_context.product_gateway_tool_audit_refs
        ),
        product_gateway_blocking_reasons=list(
            task_context.product_gateway_blocking_reasons
        ),
        product_gateway_warnings=list(task_context.product_gateway_warnings),
        product_gateway_ready_for_review=task_context.product_gateway_ready_for_review,
        recommendation=recommendation,
        plan_steps=plan_steps,
        risk_notes=risk_notes,
        next_step=next_step,
        blocking_reasons=list(task_context.blocking_reasons),
        warnings=list(task_context.warnings),
        governance_refs=list(task_context.governance_refs),
        config_refs=list(task_context.config_refs),
        metadata={
            "view_semantics": "agent_task_advice_candidate",
            "readonly": True,
            "candidate_only": True,
            "advice_version": TASK_ADVICE_VERSION,
            "recommendation_is_governance_decision": False,
            "next_step_is_execution_command": False,
            "adk_context_is_not_created": True,
            "agent_runtime_enabled": False,
            "runtime_permission_granted": False,
            "does_not_call_runtime": True,
            "does_not_call_runtime_container": True,
            "does_not_call_llm": True,
            "does_not_execute_action": True,
            "does_not_enable_chat": True,
            "does_not_enable_gateway": True,
            "does_not_enable_tool_executor": True,
            "task_context_candidate_id": task_context.candidate_id,
            "task_candidate_id": task_context.task_candidate_id,
            "agent_shell_audit_candidate_id": (
                task_context.agent_shell_audit_candidate_id
            ),
            "product_gateway_response_view_candidate_id": (
                task_context.product_gateway_response_view_candidate_id
            ),
            "does_not_call_product_gateway": True,
            "product_gateway_response_is_readonly_summary": (
                task_context.product_gateway_response_view_candidate_id is not None
            ),
            "product_gateway_response_is_not_public_contract": (
                task_context.product_gateway_response_view_candidate_id is not None
            ),
            **safe_metadata,
        },
        domain_metadata=safe_domain_metadata,
    )


def _validate_non_executing_flags(
    candidate: AgentTaskContextCandidate | AgentTaskAdviceCandidate,
) -> None:
    if not candidate.readonly:
        raise ValueError("readonly must remain true.")
    if not candidate.candidate_only:
        raise ValueError("candidate_only must remain true.")
    if candidate.execution_enabled:
        raise ValueError("execution_enabled must remain false.")
    if candidate.runtime_permission_granted:
        raise ValueError("runtime_permission_granted must remain false.")
    if candidate.agent_runtime_enabled:
        raise ValueError("agent_runtime_enabled must remain false.")
    if candidate.llm_call_enabled:
        raise ValueError("llm_call_enabled must remain false.")
    if candidate.action_execution_enabled:
        raise ValueError("action_execution_enabled must remain false.")
    if candidate.chat_enabled:
        raise ValueError("chat_enabled must remain false.")
    if candidate.gateway_enabled:
        raise ValueError("gateway_enabled must remain false.")
    if candidate.tool_execution_enabled:
        raise ValueError("tool_execution_enabled must remain false.")


def _task_context_warnings(
    *,
    task: AgentTaskCandidate,
    governed_run_evidence_context: AgentGovernedRunEvidenceContextCandidate,
    product_gateway_response_view: AgentProductGatewayResponseViewCandidate | None,
) -> list[str]:
    warnings: list[str] = []
    if not task.task_intent:
        warnings.append("task_intent_missing")
    if not governed_run_evidence_context.ready_for_review:
        warnings.append("governed_run_evidence_context_not_ready_for_review")
    warnings.extend(governed_run_evidence_context.warnings)
    if product_gateway_response_view is not None:
        warnings.extend(product_gateway_response_view.product_gateway_warnings)
        if product_gateway_response_view.product_gateway_status == "skipped":
            warnings.append("product_gateway_response_skipped")
    return _unique(warnings)


def _task_context_blocking_reasons(
    *,
    task: AgentTaskCandidate,
    product_gateway_response_view: AgentProductGatewayResponseViewCandidate | None,
) -> list[str]:
    reasons: list[str] = []
    if not task.requires_governance_view:
        reasons.append("task_governance_view_not_required_boundary_violation")
    if product_gateway_response_view is not None:
        reasons.extend(product_gateway_response_view.product_gateway_blocking_reasons)
        if product_gateway_response_view.product_gateway_status == "blocked":
            reasons.append("product_gateway_response_blocked")
        if product_gateway_response_view.product_gateway_status == "failed":
            reasons.append("product_gateway_response_failed")
    return _unique(reasons)


def _recommendation(task_context: AgentTaskContextCandidate) -> str:
    if _non_product_gateway_blocking_reasons(task_context):
        return "defer_until_context_ready"
    if task_context.product_gateway_status == "blocked":
        return "review_product_gateway_blocking_reasons"
    if task_context.product_gateway_status == "failed":
        return "review_product_gateway_failure"
    if task_context.product_gateway_status == "skipped":
        return "continue_with_product_gateway_skipped_review"
    if not task_context.ready_for_review:
        return "collect_governed_run_evidence"
    if (
        task_context.agent_shell_failure_type
        and task_context.agent_shell_failure_type != "live_disabled"
    ):
        return "review_agent_shell_failure"
    if task_context.controlled_live:
        return "continue_with_controlled_agent_review"
    if (
        task_context.agent_shell_controlled_live
        and task_context.agent_shell_status == "success"
    ):
        return "continue_with_controlled_agent_review"
    if task_context.product_gateway_status == "success":
        return "continue_with_product_gateway_review"
    return "continue_with_no_live_review"


def _plan_steps(recommendation: str) -> list[str]:
    if recommendation == "defer_until_context_ready":
        return [
            "review_blocking_reasons",
            "complete_required_task_context",
            "rebuild_agent_task_context_candidate",
        ]
    if recommendation == "collect_governed_run_evidence":
        return [
            "collect_governed_run_evidence_context",
            "verify_governance_summary_and_invocation_refs",
            "rebuild_agent_task_context_candidate",
        ]
    if recommendation == "continue_with_controlled_agent_review":
        return [
            "review_sanitized_task_context",
            "check_evidence_warnings",
            "prepare_candidate_next_action_for_operator_review",
        ]
    if recommendation == "review_agent_shell_failure":
        return [
            "review_agent_shell_audit_refs",
            "classify_agent_shell_failure",
            "prepare_failure_evidence_for_operator_review",
        ]
    if recommendation == "review_product_gateway_blocking_reasons":
        return [
            "review_product_gateway_blocking_reasons",
            "check_product_gateway_response_refs",
            "prepare_product_gateway_evidence_for_operator_review",
        ]
    if recommendation == "review_product_gateway_failure":
        return [
            "review_product_gateway_failure",
            "check_product_gateway_response_refs",
            "prepare_product_gateway_failure_for_operator_review",
        ]
    if recommendation == "continue_with_product_gateway_skipped_review":
        return [
            "review_product_gateway_skipped_response",
            "keep_skipped_limitations_visible",
            "prepare_candidate_next_action_for_operator_review",
        ]
    if recommendation == "continue_with_product_gateway_review":
        return [
            "review_product_gateway_response_summary",
            "check_product_gateway_warnings",
            "prepare_candidate_next_action_for_operator_review",
        ]
    return [
        "review_sanitized_task_context",
        "keep_no_live_limitations_visible",
        "prepare_candidate_next_action_for_operator_review",
    ]


def _risk_notes(
    *,
    task_context: AgentTaskContextCandidate,
    recommendation: str,
) -> list[str]:
    notes: list[str] = []
    if task_context.evidence_warnings:
        notes.append("evidence_warnings_present")
    if recommendation == "continue_with_no_live_review":
        notes.append("no_live_context_cannot_validate_live_execution_quality")
    if recommendation == "collect_governed_run_evidence":
        notes.append("review_context_incomplete")
    if recommendation == "review_agent_shell_failure":
        notes.append("agent_shell_failure_requires_review")
    if recommendation == "review_product_gateway_blocking_reasons":
        notes.append("product_gateway_blocking_reasons_require_review")
    if recommendation == "review_product_gateway_failure":
        notes.append("product_gateway_failure_requires_review")
    if recommendation == "continue_with_product_gateway_skipped_review":
        notes.append("product_gateway_response_skipped")
    if task_context.product_gateway_warnings:
        notes.append("product_gateway_warnings_present")
    if task_context.product_gateway_status:
        notes.append(f"product_gateway_status:{task_context.product_gateway_status}")
    if task_context.agent_shell_failure_type:
        notes.append(f"agent_shell_failure:{task_context.agent_shell_failure_type}")
    if (
        task_context.agent_shell_audit_candidate_id is not None
        and task_context.agent_shell_status in {"skipped", "not_run"}
    ):
        notes.append(f"agent_shell_{task_context.agent_shell_status}")
    if task_context.llm_invocation_result_ref is None:
        notes.append("llm_invocation_result_ref_missing")
    return _unique(notes)


def _next_step(recommendation: str) -> str:
    if recommendation == "defer_until_context_ready":
        return "Resolve blocking reasons before agent product entry review."
    if recommendation == "collect_governed_run_evidence":
        return "Collect governed run evidence context before advice review."
    if recommendation == "continue_with_controlled_agent_review":
        return "Continue with controlled agent review candidate."
    if recommendation == "review_agent_shell_failure":
        return "Review Agent shell failure evidence before product entry review."
    if recommendation == "review_product_gateway_blocking_reasons":
        return "Review product gateway blocking reasons before agent task review."
    if recommendation == "review_product_gateway_failure":
        return "Review product gateway failure evidence before agent task review."
    if recommendation == "continue_with_product_gateway_review":
        return "Continue with product gateway response review candidate."
    if recommendation == "continue_with_product_gateway_skipped_review":
        return "Continue with skipped product gateway response limitations visible."
    return "Continue with no-live agent review candidate."


def _task_context_summary(
    *,
    task: AgentTaskCandidate,
    governed_run_evidence_context: AgentGovernedRunEvidenceContextCandidate,
    blocking_reasons: list[str],
) -> str:
    readiness = (
        "ready"
        if governed_run_evidence_context.ready_for_review and not blocking_reasons
        else "incomplete"
    )
    mode = "controlled_live" if governed_run_evidence_context.controlled_live else "no_live"
    intent = task.task_intent or "unspecified_task_intent"
    return (
        "Agent task context candidate: "
        f"readiness={readiness}, mode={mode}, task_intent={intent}. "
        "This is a product consumption view, not ADK runtime context."
    )


def _task_advice_summary(
    *,
    recommendation: str,
    task_context: AgentTaskContextCandidate,
) -> str:
    return (
        "Agent task advice candidate: "
        f"recommendation={recommendation}, "
        f"warnings={len(task_context.warnings)}, "
        f"blocking_reasons={len(task_context.blocking_reasons)}. "
        "Advice is not execution permission."
    )


def _product_gateway_values(
    product_gateway_response_view: AgentProductGatewayResponseViewCandidate | None,
) -> dict[str, Any]:
    if product_gateway_response_view is None:
        return {}
    return {
        "product_gateway_response_view_candidate_id": (
            product_gateway_response_view.candidate_id
        ),
        "product_gateway_request_id": (
            product_gateway_response_view.product_gateway_request_id
        ),
        "product_gateway_entry_kind": (
            product_gateway_response_view.product_gateway_entry_kind
        ),
        "product_gateway_status": product_gateway_response_view.product_gateway_status,
        "product_gateway_exit_code": (
            product_gateway_response_view.product_gateway_exit_code
        ),
        "product_gateway_response_ref": (
            product_gateway_response_view.product_gateway_response_ref
        ),
        "product_gateway_governance_summary_ref": (
            product_gateway_response_view.product_gateway_governance_summary_ref
        ),
        "product_gateway_evidence_refs": _ref_payloads(
            product_gateway_response_view.product_gateway_evidence_refs
        ),
        "product_gateway_audit_refs": _ref_payloads(
            product_gateway_response_view.product_gateway_audit_refs
        ),
        "product_gateway_agent_advice_refs": _ref_payloads(
            product_gateway_response_view.product_gateway_agent_advice_refs
        ),
        "product_gateway_tool_audit_refs": _ref_payloads(
            product_gateway_response_view.product_gateway_tool_audit_refs
        ),
        "product_gateway_blocking_reasons": list(
            product_gateway_response_view.product_gateway_blocking_reasons
        ),
        "product_gateway_warnings": list(
            product_gateway_response_view.product_gateway_warnings
        ),
        "product_gateway_ready_for_review": (
            product_gateway_response_view.product_gateway_ready_for_review
        ),
    }


def _ref_payloads(values: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "ref": value.ref,
            "kind": value.kind,
            "purpose": value.purpose,
            "metadata": dict(value.metadata),
        }
        for value in values
    ]


def _product_gateway_governance_refs(
    product_gateway_response_view: AgentProductGatewayResponseViewCandidate | None,
) -> list[str]:
    if product_gateway_response_view is None:
        return []
    refs: list[str] = []
    if product_gateway_response_view.product_gateway_governance_summary_ref:
        refs.append(product_gateway_response_view.product_gateway_governance_summary_ref)
    for values in (
        product_gateway_response_view.product_gateway_evidence_refs,
        product_gateway_response_view.product_gateway_audit_refs,
        product_gateway_response_view.product_gateway_tool_audit_refs,
    ):
        refs.extend(value.ref for value in values)
    return _unique(refs)


def _product_gateway_source_refs(
    product_gateway_response_view: AgentProductGatewayResponseViewCandidate | None,
) -> list[str]:
    if product_gateway_response_view is None:
        return []
    refs: list[str] = []
    if product_gateway_response_view.product_gateway_response_ref:
        refs.append(product_gateway_response_view.product_gateway_response_ref)
    for values in (
        product_gateway_response_view.product_gateway_evidence_refs,
        product_gateway_response_view.product_gateway_audit_refs,
        product_gateway_response_view.product_gateway_agent_advice_refs,
        product_gateway_response_view.product_gateway_tool_audit_refs,
    ):
        refs.extend(value.ref for value in values)
    return _unique(refs)


def _product_gateway_ready_for_task_review(
    product_gateway_response_view: AgentProductGatewayResponseViewCandidate | None,
) -> bool:
    if product_gateway_response_view is None:
        return True
    return product_gateway_response_view.product_gateway_ready_for_review


def _non_product_gateway_blocking_reasons(
    task_context: AgentTaskContextCandidate,
) -> list[str]:
    product_gateway_reasons = set(task_context.product_gateway_blocking_reasons)
    product_gateway_reasons.update(
        {"product_gateway_response_blocked", "product_gateway_response_failed"}
    )
    return [
        reason
        for reason in task_context.blocking_reasons
        if reason not in product_gateway_reasons
    ]


def _safe_mapping(value: dict[str, Any], *, path: str) -> dict[str, Any]:
    violations = _forbidden_task_context_key_violations(value, path=path)
    if violations:
        raise ValueError("; ".join(violations))
    return dict(value)


def _safe_string_list(values: list[str] | tuple[str, ...], *, path: str) -> list[str]:
    result: list[str] = []
    for index, value in enumerate(values):
        if not isinstance(value, str):
            raise ValueError(f"expected string at {path}[{index}]")
        violations = _forbidden_task_context_key_violations(value, path=f"{path}[{index}]")
        if violations:
            raise ValueError("; ".join(violations))
        if value:
            result.append(value)
    return result


def _optional_string(value: str | None) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _forbidden_task_context_key_violations(
    value: Any, path: str = "$"
) -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_path = f"{path}.{key}"
            if str(key).lower() in FORBIDDEN_TASK_CONTEXT_KEYS:
                violations.append(f"task context field is forbidden at {key_path}")
            violations.extend(_forbidden_task_context_key_violations(item, key_path))
        return violations
    if isinstance(value, list):
        for index, item in enumerate(value):
            violations.extend(
                _forbidden_task_context_key_violations(item, f"{path}[{index}]")
            )
        return violations
    if isinstance(value, str) and _looks_like_raw_payload(value):
        violations.append(f"raw task context payload is forbidden at {path}")
    return violations


def _looks_like_raw_payload(value: str) -> bool:
    lowered = value.lower()
    return any(
        marker in lowered
        for marker in (
            "raw provider response",
            "raw_response",
            "response_text",
            "system_prompt",
            "api_key",
        )
    )
