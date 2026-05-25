from __future__ import annotations

import pytest

from observability_hub import (
    RawBoundarySummary,
    RuntimeFactEnvelope,
    build_evidence_summary_answer_policy_observation_candidate,
    build_llm_call_observation_candidate,
    build_runtime_fact_envelope,
    build_runtime_fact_from_evidence_summary_answer_observation,
    build_runtime_fact_from_llm_call_observation,
)
from schemas.evidence_summary_answer import (
    EVIDENCE_SUMMARY_ANSWER_PRODUCT,
    EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION,
)
from schemas.llm_invocation import (
    LlmGovernancePrecondition,
    LlmInvocationFailureType,
    LlmInvocationResult,
)
from schemas.model_routing import ModelRouteFacts


_ANSWER_TEXT = "This answer text must not be copied into the runtime fact."
_ANSWER_PREVIEW = "This preview must not be copied into the runtime fact."


def test_builds_runtime_fact_envelope_with_safe_payload_and_refs() -> None:
    fact = build_runtime_fact_envelope(
        source_component="observability_hub.test",
        phase="preflight_completed",
        status="success",
        request_id="request-1",
        trace_ref="evidence-summary-answer-trace://trace-1",
        subject_ref="subject://1",
        safe_payload={"fact_count": 3, "policy_ref": "policy://one"},
        refs=["policy://one", "policy://one", ""],
    )

    assert isinstance(fact, RuntimeFactEnvelope)
    assert fact.correlation_id == "evidence-summary-answer-trace://trace-1"
    assert fact.phase == "preflight_completed"
    assert fact.status == "success"
    assert fact.refs == ["policy://one"]
    assert fact.raw_boundary.raw_absent is True
    assert fact.raw_boundary.raw_blocked is False


def test_rejects_unknown_phase_and_status() -> None:
    with pytest.raises(ValueError, match="phase must be one of"):
        build_runtime_fact_envelope(
            source_component="observability_hub.test",
            phase="not_a_phase",
            status="success",
        )

    with pytest.raises(ValueError, match="status must be one of"):
        build_runtime_fact_envelope(
            source_component="observability_hub.test",
            phase="runtime_completed",
            status="ready",
        )


def test_rejects_raw_boundary_keys_in_safe_payload() -> None:
    with pytest.raises(ValueError, match="raw_provider_response"):
        build_runtime_fact_envelope(
            source_component="observability_hub.test",
            phase="runtime_completed",
            status="failed",
            safe_payload={
                "nested": {
                    "raw_provider_response": "must not cross observability bus"
                }
            },
        )


def test_builds_runtime_fact_from_llm_observation_without_response_preview() -> None:
    observation = build_llm_call_observation_candidate(
        LlmInvocationResult(
            request_id="llm-request-1",
            route_facts=_route_facts(),
            governance_precondition=LlmGovernancePrecondition(
                allowed=True,
                reason="allowed",
                decision="continue",
                governance_decision_ref="governance-decision://1",
            ),
            call_attempted=True,
            call_allowed=True,
            runtime_call_performed=True,
            success=True,
            response_non_empty=True,
            sanitized_response_length=42,
            sanitized_response_preview="sanitized preview must not be copied",
            latency_ms=12,
        )
    )

    fact = build_runtime_fact_from_llm_call_observation(observation)

    assert fact.source_component == "observability_hub.llm_invocation"
    assert fact.phase == "runtime_completed"
    assert fact.status == "success"
    assert fact.request_id == "llm-request-1"
    assert fact.safe_payload["sanitized_response_length"] == 42
    assert "sanitized_response_preview" not in fact.safe_payload
    assert "governance-decision://1" in fact.refs
    assert fact.raw_boundary.metadata["does_not_store_prompt"] is True
    assert fact.raw_boundary.metadata["does_not_store_raw_provider_response"] is True


def test_maps_blocked_llm_observation_to_blocked_runtime_fact() -> None:
    observation = build_llm_call_observation_candidate(
        LlmInvocationResult(
            request_id="llm-request-blocked",
            route_facts=_route_facts(),
            governance_precondition=LlmGovernancePrecondition(
                allowed=False,
                reason="blocked",
                decision="block",
                governance_decision_ref="governance-decision://blocked",
            ),
            call_attempted=False,
            call_allowed=False,
            runtime_call_performed=False,
            success=False,
            failure_type=LlmInvocationFailureType.GOVERNANCE_BLOCKED,
            error_message_sanitized="blocked before runtime",
        )
    )

    fact = build_runtime_fact_from_llm_call_observation(observation)

    assert fact.status == "blocked"
    assert fact.safe_payload["failure_type"] == "governance_blocked"
    assert "governance-decision://blocked" in fact.refs


def test_builds_runtime_fact_from_evidence_summary_answer_observation() -> None:
    observation = build_evidence_summary_answer_policy_observation_candidate(
        _answer_result()
    )

    fact = build_runtime_fact_from_evidence_summary_answer_observation(
        observation
    )

    assert fact.source_component == "observability_hub.evidence_summary_answer"
    assert fact.phase == "answer_trace_finalized"
    assert fact.status == "success"
    assert fact.request_id == "request-1"
    assert fact.safe_payload["answer_present"] is True
    assert fact.safe_payload["answer_preview_present"] is True
    assert fact.safe_payload["summary_fact_count"] == 0
    assert "evidence://external-readonly/request-1/fetch-1" in fact.refs
    assert "governed-evidence-digest://request-1/digest-1" in fact.refs

    serialized = fact.model_dump_json()
    assert _ANSWER_TEXT not in serialized
    assert _ANSWER_PREVIEW not in serialized


def test_raw_boundary_summary_can_be_passed_explicitly() -> None:
    fact = build_runtime_fact_envelope(
        source_component="observability_hub.test",
        phase="runtime_event_recorded",
        status="warning",
        raw_boundary=RawBoundarySummary(
            raw_absent=False,
            raw_blocked=True,
            raw_unavailable_reason="raw payload intentionally omitted",
            blocked_keys=["raw_payload"],
        ),
    )

    assert fact.raw_boundary.raw_absent is False
    assert fact.raw_boundary.raw_blocked is True
    assert fact.raw_boundary.blocked_keys == ["raw_payload"]


def _route_facts() -> ModelRouteFacts:
    return ModelRouteFacts(
        model_name="ollama/gemma4-pro:latest",
        provider="litellm",
        source="adk_adapter.models",
        metadata={
            "backend_provider": "ollama",
            "route_target": "ollama/gemma4-pro:latest",
            "route_kind": "adk_litellm",
        },
    )


def _answer_result() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_result",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION,
        "request_id": "request-1",
        "status": "success",
        "answer": _ANSWER_TEXT,
        "answer_preview": _ANSWER_PREVIEW,
        "evidence_refs_used": [
            {
                "ref": "evidence://external-readonly/request-1/fetch-1",
                "kind": "external_readonly_evidence",
                "purpose": "citation",
            }
        ],
        "digest_refs_used": ["governed-evidence-digest://request-1/digest-1"],
        "additional_refs_used": [],
        "insufficient_evidence_reason": None,
        "citation_failures": [],
        "blocking_reasons": [],
        "warnings": [],
        "llm_call_allowed": True,
        "llm_call_attempted": True,
        "llm_runtime_call_performed": True,
        "raw_boundary_flags": {},
        "metadata": {"source": "observability-hub.test"},
    }
