from __future__ import annotations

from observability_hub import (
    RawBoundarySummary,
    build_evidence_summary_answer_policy_observation_candidate,
    build_llm_call_observation_candidate,
    build_runtime_fact_envelope,
    build_runtime_fact_from_evidence_summary_answer_observation,
    build_runtime_fact_from_llm_call_observation,
    build_runtime_fact_summary_projection,
    runtime_fact_summary_projection_dict,
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


_ANSWER_TEXT = "This answer text must not be copied into the projection."
_ANSWER_PREVIEW = "This answer preview must not be copied into the projection."


def test_projects_successful_runtime_fact_to_safe_summary() -> None:
    fact = build_runtime_fact_from_llm_call_observation(
        build_llm_call_observation_candidate(
            LlmInvocationResult(
                request_id="projection-llm-success",
                route_facts=_route_facts(),
                governance_precondition=LlmGovernancePrecondition(
                    allowed=True,
                    reason="allowed",
                    decision="continue",
                    governance_decision_ref="governance-decision://projection/success",
                ),
                call_attempted=True,
                call_allowed=True,
                runtime_call_performed=True,
                success=True,
                response_non_empty=True,
                sanitized_response_length=42,
                sanitized_response_preview="preview must not be copied",
                latency_ms=12,
            )
        )
    )

    projection = build_runtime_fact_summary_projection(fact)

    assert projection.phase == "runtime_completed"
    assert projection.status == "success"
    assert projection.reason == "runtime_completed_success"
    assert projection.runtime_backed is False
    assert projection.public_schema is False
    assert "governance-decision://projection/success" in projection.refs
    serialized = projection.model_dump_json()
    assert "safe_payload" not in serialized
    assert "preview must not be copied" not in serialized


def test_projects_governance_block_to_product_explanation() -> None:
    fact = build_runtime_fact_from_llm_call_observation(
        build_llm_call_observation_candidate(
            LlmInvocationResult(
                request_id="projection-llm-blocked",
                route_facts=_route_facts(),
                governance_precondition=LlmGovernancePrecondition(
                    allowed=False,
                    reason="operator_approval_not_true",
                    decision="block",
                    governance_decision_ref="governance-decision://projection/blocked",
                ),
                call_attempted=False,
                call_allowed=False,
                runtime_call_performed=False,
                success=False,
                failure_type=LlmInvocationFailureType.GOVERNANCE_BLOCKED,
                error_message_sanitized="blocked before runtime",
            )
        )
    )

    projection = build_runtime_fact_summary_projection(fact)

    assert projection.status == "blocked"
    assert projection.reason == "governance_blocked"
    assert "governance precondition" in projection.user_explanation
    assert projection.recovery_hints


def test_projects_answer_quality_failure_without_answer_body() -> None:
    observation = build_evidence_summary_answer_policy_observation_candidate(
        _answer_result(status="failed"),
        guard_outcome={
            "passed": False,
            "violations": ["llm_answer_quality_contract_violation"],
        },
        schema_validation_passed=True,
        schema_validation_error_count=0,
    )
    fact = build_runtime_fact_from_evidence_summary_answer_observation(
        observation
    )

    projection = build_runtime_fact_summary_projection(fact)

    assert projection.phase == "answer_trace_finalized"
    assert projection.status == "failed"
    assert projection.reason == "answer_quality_contract_failed"
    assert projection.refs == [
        "evidence://external-readonly/projection/fetch-1",
        "governed-evidence-digest://projection/digest-1",
    ]
    serialized = projection.model_dump_json()
    assert _ANSWER_TEXT not in serialized
    assert _ANSWER_PREVIEW not in serialized
    assert "safe_payload" not in serialized


def test_projects_answerability_preflight_block() -> None:
    fact = build_runtime_fact_envelope(
        source_component="product_application_assembly.answerability_preflight",
        phase="preflight_completed",
        status="blocked",
        request_id="projection-preflight-blocked",
        safe_payload={
            "answerability": "insufficient_evidence",
            "blocking_reasons": ["short_evidence_long_generation_request"],
        },
        refs=["governed-evidence-digest://projection/preflight-digest"],
    )

    projection = build_runtime_fact_summary_projection(fact)

    assert projection.reason == "answerability_preflight_blocked"
    assert "before model invocation" in projection.user_explanation
    assert any("narrower question" in hint for hint in projection.recovery_hints)
    assert projection.refs == ["governed-evidence-digest://projection/preflight-digest"]


def test_projection_summarizes_raw_boundary_without_key_leakage() -> None:
    fact = build_runtime_fact_envelope(
        source_component="observability_hub.test",
        phase="runtime_completed",
        status="failed",
        raw_boundary=RawBoundarySummary(
            raw_absent=False,
            raw_blocked=True,
            raw_unavailable_reason="raw_provider_response omitted",
            blocked_keys=["raw_provider_response"],
        ),
    )

    projection = build_runtime_fact_summary_projection(fact)

    assert projection.reason == "raw_boundary_blocked"
    assert projection.raw_boundary_summary["blocked_key_count"] == 1
    assert projection.raw_boundary_summary["raw_unavailable_reason"] == "unavailable"
    serialized = projection.model_dump_json()
    assert "raw_provider_response" not in serialized
    assert "safe_payload" not in serialized


def test_projection_dict_is_json_ready() -> None:
    fact = build_runtime_fact_envelope(
        source_component="observability_hub.test",
        phase="answer_trace_finalized",
        status="success",
        request_id="projection-dict",
        refs=["evidence://projection/dict"],
    )

    projection_dict = runtime_fact_summary_projection_dict(
        build_runtime_fact_summary_projection(fact)
    )

    assert projection_dict["reason"] == "answer_trace_success"
    assert projection_dict["runtime_backed"] is False
    assert projection_dict["public_schema"] is False
    assert projection_dict["refs"] == ["evidence://projection/dict"]


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


def _answer_result(*, status: str) -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_result",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION,
        "request_id": "projection-answer-quality",
        "status": status,
        "answer": _ANSWER_TEXT,
        "answer_preview": _ANSWER_PREVIEW,
        "evidence_refs_used": [
            {
                "ref": "evidence://external-readonly/projection/fetch-1",
                "kind": "external_readonly_evidence",
                "purpose": "citation",
            }
        ],
        "digest_refs_used": ["governed-evidence-digest://projection/digest-1"],
        "additional_refs_used": [],
        "insufficient_evidence_reason": None,
        "citation_failures": [],
        "blocking_reasons": ["llm_answer_quality_contract_violation"],
        "warnings": [],
        "llm_call_allowed": True,
        "llm_call_attempted": True,
        "llm_runtime_call_performed": True,
        "raw_boundary_flags": {},
        "metadata": {"source": "observability-hub.projection-test"},
    }
