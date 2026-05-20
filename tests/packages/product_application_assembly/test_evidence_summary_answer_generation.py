from __future__ import annotations

from pathlib import Path

import pytest
from behavior_contracts.evidence_summary_answer import (
    EVIDENCE_SUMMARY_ANSWER_QUALITY_BLOCKING_REASON,
    validate_evidence_summary_answer_guards,
    validate_evidence_summary_answer_llm_request_boundary,
    validate_evidence_summary_answer_result_mapping,
)
from product_application_assembly import (
    EVIDENCE_SUMMARY_ANSWER_GENERATION_INTERACTION_MODE,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_GENERATED_RESULT_POLICY_REF,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_GENERATION_SOURCE,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_LLM_REQUEST_POLICY_REF,
    build_evidence_summary_answer_context,
    build_evidence_summary_answer_llm_invocation_request,
    build_evidence_summary_answer_result_from_llm_invocation_result,
)
from schemas.evidence_summary_answer import EvidenceSummaryAnswerResultSchema
from schemas.llm_invocation import (
    LlmGovernancePrecondition,
    LlmInvocationFailureType,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from schemas.model_routing import ModelRouteFacts


REPO_ROOT = Path(__file__).resolve().parents[3]
BUILDER_SOURCE = (
    REPO_ROOT
    / "packages"
    / "product_application_assembly"
    / "src"
    / "product_application_assembly"
    / "evidence_summary_answer_generation.py"
)


def test_generation_request_mapper_builds_guarded_llm_request() -> None:
    request = build_evidence_summary_answer_llm_invocation_request(
        _context(),
        route_facts=_route_facts(),
        governance_precondition=_governance_precondition(),
        generation_policy_facts=_generation_policy(),
    )
    serialized = request.model_dump(mode="json")

    assert isinstance(request, LlmInvocationRequest)
    assert request.request_id == "request-607/llm"
    assert request.prompt_ref == "prompt://evidence-summary-answer/request-607"
    assert request.prompt_preview_sanitized == "What does the governed evidence say?"
    assert request.metadata["source"] == (
        PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_GENERATION_SOURCE
    )
    assert request.metadata["policy_ref"] == (
        PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_LLM_REQUEST_POLICY_REF
    )
    assert (
        request.metadata["interaction_mode"]
        == EVIDENCE_SUMMARY_ANSWER_GENERATION_INTERACTION_MODE
    )
    assert request.metadata["answerable_digest_count"] == 1
    assert request.metadata["no_fetch_search"] is True
    assert request.metadata["service_ref"] == (
        "behavior-contract://evidence-summary-answer/generation-service-v1"
    )
    request_context = request.metadata["evidence_summary_answer_context"]
    assert request_context["summary_facts"] == [
        "The governed evidence supports schema-first answer generation."
    ]
    assert request_context["answer_constraints"] == [
        "Use only governed summary facts and listed refs.",
        "Write only the final user-facing natural language answer.",
        "Start directly with the answer, without labels or wrappers.",
        "Do not output JSON, YAML, code blocks, protocol fields, or debug fields.",
        (
            "Do not start with {, [, a code fence, thought, analysis, "
            "reasoning, or scratchpad."
        ),
        (
            "Do not output visible reasoning such as thought, analysis, "
            "reasoning, chain_of_thought, scratchpad, or internal_thought."
        ),
        "Use the user's language when practical.",
        (
            "Return insufficient evidence in natural language when facts do "
            "not support an answer."
        ),
        "Cite visible evidence refs when making evidence-backed claims.",
    ]
    assert request_context["evidence_refs"] == [
        {
            "ref": "evidence://external-readonly/item/607",
            "kind": "external_readonly_evidence",
            "purpose": "answer_context",
        }
    ]
    assert request_context["digest_refs"] == [
        "governed-evidence-digest://digest-607"
    ]
    assert "external_readonly_answer_context" not in serialized["metadata"]
    assert "product_response_summary" not in serialized["metadata"]
    assert "sanitized_excerpt_preview" not in str(serialized)
    assert "ProductGatewayResponse" not in str(serialized)
    assert validate_evidence_summary_answer_llm_request_boundary(serialized).passed


def test_generation_request_mapper_rejects_context_without_answerable_digest() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-607",
        user_question="What does the governed evidence say?",
        digests=[_empty_digest()],
    )

    with pytest.raises(ValueError, match="no_answerable_governed_evidence_digest"):
        build_evidence_summary_answer_llm_invocation_request(
            context,
            route_facts=_route_facts(),
            governance_precondition=_governance_precondition(),
            generation_policy_facts=_generation_policy(),
        )


def test_generation_result_composer_builds_guarded_success_result() -> None:
    result = build_evidence_summary_answer_result_from_llm_invocation_result(
        _context(),
        _success_llm_result(),
        generation_policy_facts=_generation_policy(),
    )
    serialized = result.model_dump(mode="json")

    assert isinstance(result, EvidenceSummaryAnswerResultSchema)
    assert result.status == "success"
    assert result.answer == (
        "The governed evidence supports schema-first answer generation with visible refs."
    )
    assert result.answer_preview == (
        "The governed evidence supports schema-first answer generation."
    )
    assert result.evidence_refs_used[0].ref == "evidence://external-readonly/item/607"
    assert result.digest_refs_used == ["governed-evidence-digest://digest-607"]
    assert result.additional_refs_used[0].ref == "governed-evidence-digest://digest-607"
    assert result.llm_call_allowed is True
    assert result.llm_call_attempted is True
    assert result.llm_runtime_call_performed is True
    assert result.metadata["source"] == (
        PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_GENERATION_SOURCE
    )
    assert result.metadata["policy_ref"] == (
        PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_GENERATED_RESULT_POLICY_REF
    )
    assert result.metadata["llm_route_provider"] == "litellm"
    assert "sanitized_response_display" not in result.metadata
    assert "response_text" not in result.metadata
    assert validate_evidence_summary_answer_result_mapping(serialized).passed
    assert validate_evidence_summary_answer_guards(serialized).passed


def test_generation_result_composer_blocks_when_llm_call_not_allowed() -> None:
    result = build_evidence_summary_answer_result_from_llm_invocation_result(
        _context(),
        _blocked_llm_result(),
        generation_policy_facts=_generation_policy(),
    )

    assert result.status == "blocked"
    assert result.answer is None
    assert result.blocking_reasons == [
        "evidence_summary_answer_llm_call_not_allowed",
        "llm_invocation_failure:governance_blocked",
    ]
    assert result.llm_call_allowed is False
    assert result.llm_call_attempted is False
    assert result.llm_runtime_call_performed is False
    assert validate_evidence_summary_answer_guards(
        result.model_dump(mode="json")
    ).passed


def test_generation_result_composer_marks_failed_llm_invocation() -> None:
    result = build_evidence_summary_answer_result_from_llm_invocation_result(
        _context(),
        _failed_llm_result(),
        generation_policy_facts=_generation_policy(),
    )

    assert result.status == "failed"
    assert result.answer is None
    assert result.blocking_reasons == [
        "llm_invocation_failure:live_call_failure"
    ]
    assert result.llm_call_allowed is True
    assert result.llm_call_attempted is True
    assert result.llm_runtime_call_performed is True
    assert validate_evidence_summary_answer_guards(
        result.model_dump(mode="json")
    ).passed


def test_generation_result_composer_fails_empty_sanitized_success() -> None:
    result = build_evidence_summary_answer_result_from_llm_invocation_result(
        _context(),
        _empty_success_llm_result(),
        generation_policy_facts=_generation_policy(),
    )

    assert result.status == "failed"
    assert result.answer is None
    assert result.blocking_reasons == ["llm_success_without_sanitized_answer"]
    assert validate_evidence_summary_answer_guards(
        result.model_dump(mode="json")
    ).passed


def test_generation_result_composer_fails_visible_reasoning_answer() -> None:
    result = build_evidence_summary_answer_result_from_llm_invocation_result(
        _context(),
        _success_llm_result(
            answer='{ "thought": "The user wants a concise answer."'
        ),
        generation_policy_facts=_generation_policy(),
    )

    serialized = result.model_dump(mode="json")

    assert result.status == "failed"
    assert result.answer is None
    assert result.answer_preview is None
    assert result.blocking_reasons == [
        EVIDENCE_SUMMARY_ANSWER_QUALITY_BLOCKING_REASON
    ]
    assert result.llm_call_allowed is True
    assert result.llm_call_attempted is True
    assert result.llm_runtime_call_performed is True
    assert validate_evidence_summary_answer_guards(serialized).passed


def test_generation_result_composer_fails_when_citation_refs_are_missing() -> None:
    context = _context().model_copy(update={"evidence_refs": []})

    result = build_evidence_summary_answer_result_from_llm_invocation_result(
        context,
        _success_llm_result(),
        generation_policy_facts=_generation_policy(),
    )

    assert result.status == "failed"
    assert result.answer is None
    assert result.citation_failures == ["citation_refs_missing"]
    assert validate_evidence_summary_answer_guards(
        result.model_dump(mode="json")
    ).passed


def test_generation_result_composer_marks_non_answerable_context_insufficient() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-607",
        user_question="What does the governed evidence say?",
        digests=[_empty_digest()],
    )

    result = build_evidence_summary_answer_result_from_llm_invocation_result(
        context,
        _success_llm_result(),
        generation_policy_facts=_generation_policy(),
    )

    assert result.status == "insufficient_evidence"
    assert result.answer is None
    assert result.insufficient_evidence_reason == (
        "no_answerable_governed_evidence_digest"
    )
    assert result.llm_runtime_call_performed is False
    assert validate_evidence_summary_answer_guards(
        result.model_dump(mode="json")
    ).passed


def test_generation_result_composer_blocks_when_policy_disables_success() -> None:
    result = build_evidence_summary_answer_result_from_llm_invocation_result(
        _context(),
        _success_llm_result(),
        generation_policy_facts={
            "profile": "smoke_only",
            "allow_answer_generation_success": False,
        },
    )

    assert result.status == "blocked"
    assert result.answer is None
    assert result.blocking_reasons == ["answer_generation_policy_not_enabled"]
    assert result.llm_runtime_call_performed is False
    assert validate_evidence_summary_answer_guards(
        result.model_dump(mode="json")
    ).passed


def test_generation_mapper_exports_from_package_root() -> None:
    assert callable(build_evidence_summary_answer_llm_invocation_request)
    assert callable(build_evidence_summary_answer_result_from_llm_invocation_result)


def test_generation_mapper_source_has_no_forbidden_imports_or_inputs() -> None:
    source = BUILDER_SOURCE.read_text(encoding="utf-8")

    assert "from behavior_contracts.evidence_summary_answer import" in source
    assert "contract_core" not in source
    assert "config_contexts" not in source
    assert "runtime_container" not in source
    assert "cognition_cli" not in source
    assert "product_runtime_assembly" not in source
    assert "observability_hub" not in source
    assert "google.adk" not in source
    assert "adk_adapter" not in source
    assert "provider_response" not in source
    assert "raw_provider_response" not in source
    assert "sanitized_excerpt" not in source
    assert "model_context_items" not in source
    assert "ProductGatewayResponse" not in source
    assert "external_readonly_answer_context" not in source
    assert "product_response_summary" not in source


def _context():
    return build_evidence_summary_answer_context(
        request_id="request-607",
        user_question="What does the governed evidence say?",
        digests=[_ready_digest()],
    )


def _route_facts() -> ModelRouteFacts:
    return ModelRouteFacts(
        model_name="ollama/gemma4-pro:latest",
        provider="litellm",
        source="product_application_assembly.test",
        metadata={
            "route_kind": "adk_litellm",
            "route_target": "ollama/gemma4-pro:latest",
        },
    )


def _governance_precondition() -> LlmGovernancePrecondition:
    return LlmGovernancePrecondition(
        allowed=True,
        reason="evidence_summary_answer_generation_policy_allowed",
        decision="allow",
        governance_decision_ref="approval://test/evidence-summary-answer",
        metadata={"source": "product_application_assembly.test"},
    )


def _success_llm_result(
    *,
    answer: str = (
        "The governed evidence supports schema-first answer generation with visible refs."
    ),
    preview: str = "The governed evidence supports schema-first answer generation.",
) -> LlmInvocationResult:
    return LlmInvocationResult(
        request_id="request-607/llm",
        route_facts=_route_facts(),
        governance_precondition=_governance_precondition(),
        call_attempted=True,
        call_allowed=True,
        runtime_call_performed=True,
        success=True,
        response_non_empty=True,
        sanitized_response_length=len(answer),
        sanitized_response_preview=preview,
        metadata={"sanitized_response_display": answer},
    )


def _blocked_llm_result() -> LlmInvocationResult:
    return LlmInvocationResult(
        request_id="request-607/llm",
        route_facts=_route_facts(),
        governance_precondition=LlmGovernancePrecondition(
            allowed=False,
            reason="generation_governance_blocked",
            decision="block",
            metadata={"source": "product_application_assembly.test"},
        ),
        call_attempted=False,
        call_allowed=False,
        runtime_call_performed=False,
        success=False,
        response_non_empty=False,
        failure_type=LlmInvocationFailureType.GOVERNANCE_BLOCKED,
    )


def _failed_llm_result() -> LlmInvocationResult:
    return LlmInvocationResult(
        request_id="request-607/llm",
        route_facts=_route_facts(),
        governance_precondition=_governance_precondition(),
        call_attempted=True,
        call_allowed=True,
        runtime_call_performed=True,
        success=False,
        response_non_empty=False,
        failure_type=LlmInvocationFailureType.LIVE_CALL_FAILURE,
        error_message_sanitized="provider unavailable",
    )


def _empty_success_llm_result() -> LlmInvocationResult:
    return LlmInvocationResult(
        request_id="request-607/llm",
        route_facts=_route_facts(),
        governance_precondition=_governance_precondition(),
        call_attempted=True,
        call_allowed=True,
        runtime_call_performed=True,
        success=True,
        response_non_empty=False,
    )


def _generation_policy() -> dict[str, object]:
    return {
        "profile": "controlled_live_answer_generation",
        "allow_answer_generation_success": True,
        "answer_generation_service_ref": (
            "behavior-contract://evidence-summary-answer/generation-service-v1"
        ),
        "llm_provider_factory_ref": (
            "provider-factory://evidence-summary-answer/controlled-live/default-v1"
        ),
        "answer_policy_ref": "policy://evidence-summary-answer/answer-generation-v1",
        "citation_policy_ref": "policy://evidence-summary-answer/citation-v1",
    }


def _ready_digest() -> dict[str, object]:
    return {
        "product": "evidence_summary_answer",
        "payload_type": "governed_evidence_digest",
        "payload_version": "governed_evidence_digest_v1",
        "digest_id": "digest-607",
        "digest_ref": "governed-evidence-digest://digest-607",
        "evidence_ref": "evidence://external-readonly/item/607",
        "evidence_output_ref": "outputs/external-readonly/607.json",
        "source_url_host": "example.com",
        "source_url_scheme": "https",
        "runtime_status": "governed_summary_facts_ready",
        "status": "ready",
        "reference_review_ready": True,
        "allowed_for_model_context": True,
        "evidence_written": True,
        "content_hash": "d" * 64,
        "total_excerpt_chars": 63,
        "raw_boundary_flags": {},
        "blocking_reasons": [],
        "warnings": [],
        "summary_facts": [
            "The governed evidence supports schema-first answer generation."
        ],
        "topic_labels": ["contracts"],
        "risk_labels": [],
        "answerability": "answerable",
        "digest_generation_policy_ref": (
            "policy://evidence-summary-answer/digest-generation-v1"
        ),
        "digest_budget": 4000,
        "metadata": {"source": "product_application_assembly.test"},
    }


def _empty_digest() -> dict[str, object]:
    digest = _ready_digest()
    digest["status"] = "empty"
    digest["answerability"] = "insufficient_evidence"
    digest["summary_facts"] = []
    return digest
