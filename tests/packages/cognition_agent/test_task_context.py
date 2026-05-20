from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from cognition_agent import (
    TASK_ADVICE_SOURCE,
    TASK_ADVICE_VERSION,
    TASK_CONTEXT_SOURCE,
    TASK_CONTEXT_VERSION,
    AgentTaskAdviceCandidate,
    AgentTaskCandidate,
    AgentTaskContextCandidate,
    build_agent_governance_evidence_summary_view,
    build_agent_governed_run_evidence_context_candidate,
    build_agent_llm_invocation_summary_from_invocation_result,
    build_agent_product_gateway_response_view_candidate,
    build_agent_shell_audit_readonly_view,
    build_agent_task_advice_candidate,
    build_agent_task_context_candidate,
)
from schemas.llm_invocation import (
    LlmGovernancePrecondition,
    LlmInvocationFailureType,
    LlmInvocationResult,
)
from schemas.model_routing import ModelRouteFacts


REPO_ROOT = Path(__file__).resolve().parents[3]
COGNITION_AGENT_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "cognition_agent" / "src" / "cognition_agent"
)


def test_builds_controlled_live_task_context_and_advice_candidates() -> None:
    task = _task_candidate()
    evidence_context = _governed_evidence_context(
        controlled_live=True,
        agent_shell_status="success",
    )
    task_context = build_agent_task_context_candidate(
        candidate_id="agent-task-context-1",
        task=task,
        governed_run_evidence_context=evidence_context,
        task_goal="Review controlled live run.",
        task_input_summary="Controlled live run completed with sanitized evidence.",
        source_refs=["task://agent-task-1"],
        constraints=["candidate_only"],
    )

    assert isinstance(task_context, AgentTaskContextCandidate)
    assert task_context.candidate_type == "agent_task_context_candidate"
    assert task_context.context_version == TASK_CONTEXT_VERSION
    assert task_context.source == TASK_CONTEXT_SOURCE
    assert task_context.task_candidate_id == "agent-task-1"
    assert task_context.governed_run_evidence_context_candidate_id == (
        "agent-governed-run-evidence-context-controlled-live"
    )
    assert task_context.governance_summary_candidate_id == (
        "agent-governance-summary-view-1"
    )
    assert task_context.llm_invocation_summary_candidate_id == "agent-llm-summary-1"
    assert task_context.llm_invocation_result_ref == (
        "llm-invocation-result://llm-request-agent-1"
    )
    assert task_context.agent_shell_audit_candidate_id == "agent-shell-audit-view-1"
    assert task_context.agent_shell_evidence_ref == (
        "agent-shell-evidence://agent-shell-run-1"
    )
    assert task_context.agent_shell_run_ref == "agent-shell-run://agent-shell-run-1"
    assert task_context.agent_shell_status == "success"
    assert task_context.agent_shell_failure_type is None
    assert task_context.agent_shell_controlled_live is True
    assert task_context.controlled_live is True
    assert task_context.ready_for_review is True
    assert task_context.blocking_reasons == []
    assert task_context.warnings == []
    assert task_context.readonly is True
    assert task_context.candidate_only is True
    assert task_context.execution_enabled is False
    assert task_context.runtime_permission_granted is False
    assert task_context.agent_runtime_enabled is False
    assert task_context.llm_call_enabled is False
    assert task_context.chat_enabled is False
    assert task_context.gateway_enabled is False
    assert task_context.tool_execution_enabled is False
    assert task_context.metadata["adk_context_is_not_created"] is True
    assert task_context.metadata["does_not_call_runtime_container"] is True
    assert "config:runtime" in task_context.config_refs

    advice = build_agent_task_advice_candidate(
        candidate_id="agent-task-advice-1",
        task_context=task_context,
    )

    assert isinstance(advice, AgentTaskAdviceCandidate)
    assert advice.candidate_type == "agent_task_advice_candidate"
    assert advice.advice_version == TASK_ADVICE_VERSION
    assert advice.source == TASK_ADVICE_SOURCE
    assert advice.task_context_candidate_id == "agent-task-context-1"
    assert advice.task_candidate_id == "agent-task-1"
    assert advice.agent_shell_audit_candidate_id == "agent-shell-audit-view-1"
    assert advice.agent_shell_evidence_ref == (
        "agent-shell-evidence://agent-shell-run-1"
    )
    assert advice.agent_shell_run_ref == "agent-shell-run://agent-shell-run-1"
    assert advice.agent_shell_status == "success"
    assert advice.agent_shell_failure_type is None
    assert advice.agent_shell_controlled_live is True
    assert advice.recommendation == "continue_with_controlled_agent_review"
    assert advice.plan_steps == [
        "review_sanitized_task_context",
        "check_evidence_warnings",
        "prepare_candidate_next_action_for_operator_review",
    ]
    assert advice.next_step == "Continue with controlled agent review candidate."
    assert advice.risk_notes == []
    assert advice.execution_enabled is False
    assert advice.runtime_permission_granted is False
    assert advice.metadata["recommendation_is_governance_decision"] is False
    assert advice.metadata["next_step_is_execution_command"] is False


def test_no_live_reviewable_context_returns_no_live_advice() -> None:
    task_context = build_agent_task_context_candidate(
        candidate_id="agent-task-context-no-live-1",
        task=_task_candidate(),
        governed_run_evidence_context=_governed_evidence_context(controlled_live=False),
    )

    advice = build_agent_task_advice_candidate(
        candidate_id="agent-task-advice-no-live-1",
        task_context=task_context,
    )

    assert task_context.ready_for_review is True
    assert task_context.controlled_live is False
    assert "llm_invocation_live_disabled" in task_context.evidence_warnings
    assert advice.recommendation == "continue_with_no_live_review"
    assert "no_live_context_cannot_validate_live_execution_quality" in advice.risk_notes


def test_agent_shell_provider_failure_returns_failure_review_advice() -> None:
    task_context = build_agent_task_context_candidate(
        candidate_id="agent-task-context-provider-failure-1",
        task=_task_candidate(),
        governed_run_evidence_context=_governed_evidence_context(
            controlled_live=True,
            agent_shell_status="failure",
            agent_shell_failure_type="provider_error",
        ),
    )

    advice = build_agent_task_advice_candidate(
        candidate_id="agent-task-advice-provider-failure-1",
        task_context=task_context,
    )

    assert task_context.ready_for_review is True
    assert task_context.agent_shell_status == "failure"
    assert task_context.agent_shell_failure_type == "provider_error"
    assert advice.recommendation == "review_agent_shell_failure"
    assert advice.plan_steps == [
        "review_agent_shell_audit_refs",
        "classify_agent_shell_failure",
        "prepare_failure_evidence_for_operator_review",
    ]
    assert (
        advice.next_step
        == "Review Agent shell failure evidence before product entry review."
    )
    assert "agent_shell_failure_requires_review" in advice.risk_notes
    assert "agent_shell_failure:provider_error" in advice.risk_notes


def test_agent_shell_live_disabled_stays_no_live_review_advice() -> None:
    task_context = build_agent_task_context_candidate(
        candidate_id="agent-task-context-live-disabled-1",
        task=_task_candidate(),
        governed_run_evidence_context=_governed_evidence_context(
            controlled_live=False,
            agent_shell_status="skipped",
            agent_shell_failure_type="live_disabled",
        ),
    )

    advice = build_agent_task_advice_candidate(
        candidate_id="agent-task-advice-live-disabled-1",
        task_context=task_context,
    )

    assert task_context.ready_for_review is True
    assert task_context.agent_shell_status == "skipped"
    assert task_context.agent_shell_failure_type == "live_disabled"
    assert advice.recommendation == "continue_with_no_live_review"
    assert "agent_shell_failure:live_disabled" in advice.risk_notes
    assert "agent_shell_skipped" in advice.risk_notes


def test_incomplete_evidence_context_collects_governed_run_evidence() -> None:
    task_context = build_agent_task_context_candidate(
        candidate_id="agent-task-context-incomplete-1",
        task=_task_candidate(),
        governed_run_evidence_context=_governed_evidence_context(
            controlled_live=False,
            include_audit=False,
        ),
    )

    advice = build_agent_task_advice_candidate(
        candidate_id="agent-task-advice-incomplete-1",
        task_context=task_context,
    )

    assert task_context.ready_for_review is False
    assert "governed_run_evidence_context_not_ready_for_review" in task_context.warnings
    assert advice.recommendation == "collect_governed_run_evidence"
    assert advice.next_step == "Collect governed run evidence context before advice review."
    assert "review_context_incomplete" in advice.risk_notes


def test_task_context_consumes_success_product_gateway_response_view() -> None:
    task_context = build_agent_task_context_candidate(
        candidate_id="agent-task-context-product-gateway-success-1",
        task=_task_candidate(),
        governed_run_evidence_context=_governed_evidence_context(
            controlled_live=False
        ),
        product_gateway_response_view=_product_gateway_response_view(status="success"),
    )

    advice = build_agent_task_advice_candidate(
        candidate_id="agent-task-advice-product-gateway-success-1",
        task_context=task_context,
    )

    assert task_context.product_gateway_response_view_candidate_id == (
        "agent-product-gateway-response-view-success"
    )
    assert task_context.product_gateway_request_id == "product-gateway-request-1"
    assert task_context.product_gateway_entry_kind == "agent_shell"
    assert task_context.product_gateway_status == "success"
    assert task_context.product_gateway_ready_for_review is True
    assert task_context.blocking_reasons == []
    assert (
        "product-gateway-response://product-gateway-request-1"
        in task_context.source_refs
    )
    assert "evidence://product-gateway-evidence-1" in task_context.governance_refs
    assert advice.recommendation == "continue_with_product_gateway_review"
    assert advice.product_gateway_status == "success"
    assert advice.product_gateway_response_ref == (
        "product-gateway-response://product-gateway-request-1"
    )


def test_task_context_product_gateway_blocked_returns_review_advice() -> None:
    task_context = build_agent_task_context_candidate(
        candidate_id="agent-task-context-product-gateway-blocked-1",
        task=_task_candidate(),
        governed_run_evidence_context=_governed_evidence_context(
            controlled_live=False
        ),
        product_gateway_response_view=_product_gateway_response_view(status="blocked"),
    )

    advice = build_agent_task_advice_candidate(
        candidate_id="agent-task-advice-product-gateway-blocked-1",
        task_context=task_context,
    )

    assert "product_gateway_blocked" in task_context.product_gateway_blocking_reasons
    assert "product_gateway_response_blocked" in task_context.blocking_reasons
    assert task_context.ready_for_review is False
    assert advice.recommendation == "review_product_gateway_blocking_reasons"
    assert "product_gateway_blocking_reasons_require_review" in advice.risk_notes
    assert advice.next_step == (
        "Review product gateway blocking reasons before agent task review."
    )


def test_task_context_product_gateway_failed_returns_failure_advice() -> None:
    task_context = build_agent_task_context_candidate(
        candidate_id="agent-task-context-product-gateway-failed-1",
        task=_task_candidate(),
        governed_run_evidence_context=_governed_evidence_context(
            controlled_live=False
        ),
        product_gateway_response_view=_product_gateway_response_view(status="failed"),
    )

    advice = build_agent_task_advice_candidate(
        candidate_id="agent-task-advice-product-gateway-failed-1",
        task_context=task_context,
    )

    assert "product_gateway_response_failed" in task_context.blocking_reasons
    assert advice.recommendation == "review_product_gateway_failure"
    assert "product_gateway_failure_requires_review" in advice.risk_notes


def test_task_context_product_gateway_skipped_preserves_warning() -> None:
    task_context = build_agent_task_context_candidate(
        candidate_id="agent-task-context-product-gateway-skipped-1",
        task=_task_candidate(),
        governed_run_evidence_context=_governed_evidence_context(
            controlled_live=False
        ),
        product_gateway_response_view=_product_gateway_response_view(status="skipped"),
    )

    advice = build_agent_task_advice_candidate(
        candidate_id="agent-task-advice-product-gateway-skipped-1",
        task_context=task_context,
    )

    assert task_context.product_gateway_ready_for_review is True
    assert "product_gateway_response_skipped" in task_context.warnings
    assert "product_gateway_warning" in task_context.product_gateway_warnings
    assert advice.recommendation == "continue_with_product_gateway_skipped_review"
    assert "product_gateway_response_skipped" in advice.risk_notes


def test_task_context_rejects_sensitive_raw_payloads() -> None:
    with pytest.raises(ValueError):
        build_agent_task_context_candidate(
            candidate_id="agent-task-context-sensitive-1",
            task=_task_candidate(),
            governed_run_evidence_context=_governed_evidence_context(
                controlled_live=True
            ),
            metadata={"prompt": "raw prompt must not be stored"},
        )


def test_task_context_and_advice_reject_execution_flags() -> None:
    with pytest.raises(ValidationError):
        AgentTaskContextCandidate(
            candidate_id="agent-task-context-invalid-1",
            source=TASK_CONTEXT_SOURCE,
            summary="Invalid task context.",
            task_candidate_id="agent-task-1",
            governed_run_evidence_context_candidate_id="evidence-context-1",
            governance_summary_candidate_id="governance-summary-1",
            execution_enabled=True,
        )

    with pytest.raises(ValidationError):
        AgentTaskAdviceCandidate(
            candidate_id="agent-task-advice-invalid-1",
            source=TASK_ADVICE_SOURCE,
            summary="Invalid task advice.",
            task_context_candidate_id="agent-task-context-1",
            task_candidate_id="agent-task-1",
            recommendation="continue_with_controlled_agent_review",
            next_step="Invalid.",
            gateway_enabled=True,
        )


def test_task_context_source_has_no_execution_dependencies() -> None:
    source = (COGNITION_AGENT_SOURCE_ROOT / "task_context.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:product_gateway|adk_adapter|litellm|google\.adk|runtime_container|runtime|"
        r"observability_hub|composition|cognition_governance|subprocess)\b",
        re.MULTILINE,
    )
    forbidden_calls = re.compile(
        r"\b(?:completion|acompletion|service\.invoke|runner\.run|run_async)\s*\("
    )

    assert forbidden_imports.search(source) is None
    assert forbidden_calls.search(source) is None
    assert "live_enabled=True" not in source


def _task_candidate() -> AgentTaskCandidate:
    return AgentTaskCandidate(
        candidate_id="agent-task-1",
        source="unit-test",
        summary="Review governed run evidence.",
        task_intent="review_governed_run",
        governance_refs=["governance:summary"],
        config_refs=["config:runtime"],
    )


def _governed_evidence_context(
    *,
    controlled_live: bool,
    include_audit: bool = True,
    agent_shell_status: str | None = None,
    agent_shell_failure_type: str | None = None,
):
    return build_agent_governed_run_evidence_context_candidate(
        candidate_id=(
            "agent-governed-run-evidence-context-controlled-live"
            if controlled_live
            else "agent-governed-run-evidence-context-no-live"
        ),
        governance_summary_view=_governance_summary_view(),
        llm_invocation_summary=_llm_invocation_summary(
            success=controlled_live,
            failure_type=(
                None if controlled_live else LlmInvocationFailureType.LIVE_DISABLED
            ),
            runtime_call_performed=controlled_live,
        ),
        llm_invocation_audit=(
            _llm_invocation_audit(controlled_live=controlled_live)
            if include_audit
            else None
        ),
        agent_shell_audit_view=(
            _agent_shell_audit_view(
                controlled_live=controlled_live,
                status=agent_shell_status,
                failure_type=agent_shell_failure_type,
            )
            if agent_shell_status is not None
            else None
        ),
    )


def _governance_summary_view():
    return build_agent_governance_evidence_summary_view(
        candidate_id="agent-governance-summary-view-1",
        governance_evidence_metadata={
            "lifecycle_summary": {
                "summary_id": "adk-lifecycle-summary-agent-1",
                "runtime_id": "runtime-agent-1",
                "workflow_id": "workflow-agent-1",
                "workflow_name": "agent-workflow",
                "status": "success",
                "session": {"session_id": "session-agent-1", "event_count": 2},
                "events": {"event_count": 2, "event_types": ["node_completed"]},
                "context_state": {
                    "state_delta_count": 0,
                    "state_delta_entity_mode": "event_payload_summary_only",
                },
            },
            "run_config_service_bundle_summary": {
                "summary_id": "adk-run-config-service-bundle-summary-agent-1",
                "runtime_id": "runtime-agent-1",
                "workflow_id": "workflow-agent-1",
                "workflow_name": "agent-workflow",
                "status": "success",
                "run_config": {
                    "mapped_fields": ["max_llm_calls"],
                    "unmapped_fields": [],
                    "deferred_fields": [],
                    "no_live_mode": True,
                    "call_attempted": False,
                },
                "service_bundle": {
                    "service_bundle_source": "in_memory",
                    "artifact_service_present": True,
                    "session_service_present": True,
                },
            },
        },
    )


def _llm_invocation_summary(
    *,
    success: bool,
    failure_type: LlmInvocationFailureType | None,
    runtime_call_performed: bool,
):
    return build_agent_llm_invocation_summary_from_invocation_result(
        candidate_id="agent-llm-summary-1",
        invocation_result=LlmInvocationResult(
            request_id="llm-request-agent-1",
            route_facts=ModelRouteFacts(
                model_name="ollama/gemma4-pro:latest",
                provider="litellm",
                source="adk_adapter.models",
                metadata={
                    "backend_provider": "ollama",
                    "route_target": "ollama/gemma4-pro:latest",
                    "route_kind": "adk_litellm",
                },
            ),
            governance_precondition=LlmGovernancePrecondition(
                allowed=True,
                reason="governance_allowed",
                decision="continue_controlled_live" if success else "continue_no_live",
                governance_decision_ref="artifact://governance-summary-agent-1",
            ),
            call_attempted=runtime_call_performed,
            call_allowed=True,
            runtime_call_performed=runtime_call_performed,
            success=success,
            response_non_empty=success,
            sanitized_response_length=2 if success else None,
            sanitized_response_preview="ok" if success else None,
            failure_type=failure_type,
            error_message_sanitized=(
                None if success else (failure_type.value if failure_type else None)
            ),
        ),
    )


def _llm_invocation_audit(*, controlled_live: bool) -> dict[str, object]:
    return {
        "llm_invocation_result_ref": "llm-invocation-result://llm-request-agent-1",
        "llm_invocation_observation_ref": (
            "llm-call-observation://llm-request-agent-1"
        ),
        "llm_invocation_summary_ref": (
            "agent-llm-invocation-summary://llm-request-agent-1"
        ),
        "call_allowed": True,
        "call_attempted": controlled_live,
        "runtime_call_performed": controlled_live,
        "failure_type": None if controlled_live else "live_disabled",
        "controlled_live": controlled_live,
        "live_llm_call_performed": controlled_live,
        "ollama_call_performed": controlled_live,
        "live_profile": (
            {
                "controlled_live": True,
                "live_options_source": (
                    "config_contexts.runtime.RuntimeLiveLlmConfigView"
                ),
                "live_service_profile": "adk_litellm_ollama",
                "configured_model_name": "ollama/gemma4-pro:latest",
                "timeout_seconds": 45,
                "temperature": 0,
                "max_tokens": 64,
                "local_no_proxy_applied": True,
            }
            if controlled_live
            else None
        ),
        "readonly_facts_embedded": False,
        "does_not_store_prompt": True,
        "does_not_store_raw_provider_response": True,
    }


def _agent_shell_audit_view(
    *,
    controlled_live: bool,
    status: str,
    failure_type: str | None,
):
    return build_agent_shell_audit_readonly_view(
        candidate_id="agent-shell-audit-view-1",
        agent_shell_audit={
            "agent_shell_evidence_ref": (
                "agent-shell-evidence://agent-shell-run-1"
            ),
            "agent_shell_run_ref": "agent-shell-run://agent-shell-run-1",
            "agent_name": "task_quality_governance",
            "agent_type": "adk_native_agent",
            "app_name": "cognition-engine",
            "status": status,
            "event_count": 2 if status == "success" else 0,
            "controlled_live": controlled_live,
            "controlled_live_smoke": controlled_live,
            "controlled_live_smoke_enabled": controlled_live,
            "runtime_call_performed": controlled_live and failure_type is None,
            "call_attempted": controlled_live,
            "failure_type": failure_type,
            "error_message_sanitized": failure_type,
            "live_profile": (
                {
                    "live_options_source": (
                        "config_contexts.runtime.RuntimeLiveLlmConfigView"
                    ),
                    "live_service_profile": "adk_litellm_ollama",
                    "configured_model_name": "ollama/gemma4-pro:latest",
                    "timeout_seconds": 45,
                    "temperature": 0,
                    "max_tokens": 64,
                    "enabled_by_default": False,
                }
                if controlled_live
                else None
            ),
        },
    )


def _product_gateway_response_view(*, status: str):
    return build_agent_product_gateway_response_view_candidate(
        candidate_id=f"agent-product-gateway-response-view-{status}",
        summary={
            "product": "product_gateway",
            "payload_type": "product_gateway_response_summary",
            "payload_version": "product_gateway_response_summary_v1",
            "request_id": "product-gateway-request-1",
            "entry_kind": "agent_shell",
            "status": status,
            "exit_code": 0 if status in {"success", "skipped"} else 1,
            "product_gateway_response_ref": (
                "product-gateway-response://product-gateway-request-1"
            ),
            "governance_summary_ref": (
                "governance-summary://product-gateway-request-1"
            ),
            "evidence_refs": [
                {
                    "ref": "evidence://product-gateway-evidence-1",
                    "kind": "evidence",
                    "purpose": "review",
                    "metadata": {"source": "product_gateway.agent_shell"},
                }
            ],
            "audit_refs": [],
            "agent_advice_refs": [],
            "tool_audit_refs": [],
            "blocking_reasons": (
                ["product_gateway_blocked"] if status == "blocked" else []
            ),
            "warnings": (
                ["product_gateway_warning"] if status == "skipped" else []
            ),
            "metadata": {"source": "product_gateway.agent_shell"},
        },
    )
