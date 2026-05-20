from __future__ import annotations

from pathlib import Path

from behavior_contracts.evidence_summary_answer import (
    validate_evidence_summary_answer_guards,
)
from product_application_assembly import (
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_POLICY_REF,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_SOURCE,
    build_evidence_summary_answer_context,
    build_no_model_evidence_summary_answer_result,
    evidence_summary_answer_result_status_dict,
)
from schemas.evidence_summary_answer import (
    EvidenceSummaryAnswerResultSchema,
    validate_evidence_summary_answer_result,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
BUILDER_SOURCE = (
    REPO_ROOT
    / "packages"
    / "product_application_assembly"
    / "src"
    / "product_application_assembly"
    / "evidence_summary_answer_result.py"
)


def test_no_model_result_blocks_answerable_context_without_answer() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[_ready_digest()],
    )

    result = build_no_model_evidence_summary_answer_result(context)
    status = evidence_summary_answer_result_status_dict(result)

    assert isinstance(result, EvidenceSummaryAnswerResultSchema)
    assert result.status == "blocked"
    assert result.answer is None
    assert result.answer_preview is None
    assert result.blocking_reasons == [
        "answer_generation_not_configured_for_answerable_context"
    ]
    assert result.evidence_refs_used == []
    assert result.digest_refs_used == ["governed-evidence-digest://digest-603"]
    assert result.additional_refs_used[0].ref == "governed-evidence-digest://digest-603"
    assert result.llm_call_allowed is False
    assert result.llm_call_attempted is False
    assert result.llm_runtime_call_performed is False
    assert (
        result.metadata["source"]
        == PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_SOURCE
    )
    assert (
        result.metadata["policy_ref"]
        == PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_POLICY_REF
    )
    assert result.metadata["context_payload_type"] == "evidence_summary_answer_context"
    assert (
        result.metadata["context_payload_version"]
        == "evidence_summary_answer_context_v1"
    )
    assert result.metadata["digest_count"] == 1
    assert result.metadata["no_model"] is True
    assert validate_evidence_summary_answer_result(status).request_id == "request-603"
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_no_model_result_blocks_all_blocked_context_with_digest_reasons() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[
            _blocked_digest(
                digest_id="digest-603-a",
                reason="reference_review_not_ready",
            ),
            _blocked_digest(
                digest_id="digest-603-b",
                reason="external_readonly_evidence_not_written",
            ),
        ],
    )

    result = build_no_model_evidence_summary_answer_result(context)

    assert result.status == "blocked"
    assert result.blocking_reasons == [
        "reference_review_not_ready",
        "external_readonly_evidence_not_written",
    ]
    assert result.insufficient_evidence_reason is None
    assert validate_evidence_summary_answer_guards(
        evidence_summary_answer_result_status_dict(result)
    ).passed is True


def test_no_model_result_uses_blocked_fallback_when_reasons_are_absent() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[_answerability_blocked_digest_without_reason()],
    )

    result = build_no_model_evidence_summary_answer_result(context)

    assert result.status == "blocked"
    assert result.blocking_reasons == ["all_governed_evidence_digests_blocked"]
    assert validate_evidence_summary_answer_guards(
        evidence_summary_answer_result_status_dict(result)
    ).passed is True


def test_no_model_result_marks_non_answerable_non_blocked_context_insufficient() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[_empty_digest()],
    )

    result = build_no_model_evidence_summary_answer_result(context)

    assert result.status == "insufficient_evidence"
    assert result.insufficient_evidence_reason == "no_answerable_governed_evidence_digest"
    assert result.blocking_reasons == []
    assert result.answer is None
    assert result.answer_preview is None
    assert result.llm_call_allowed is False
    assert result.llm_call_attempted is False
    assert result.llm_runtime_call_performed is False
    assert validate_evidence_summary_answer_guards(
        evidence_summary_answer_result_status_dict(result)
    ).passed is True


def test_no_model_result_accepts_mapping_context_and_status_dict_accepts_mapping() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[_ready_digest()],
    )

    result = build_no_model_evidence_summary_answer_result(
        context.model_dump(mode="json")
    )
    status = evidence_summary_answer_result_status_dict(
        result.model_dump(mode="json")
    )

    assert status["payload_type"] == "evidence_summary_answer_result"
    assert status["status"] == "blocked"
    assert status["answer"] is None
    assert status["answer_preview"] is None
    assert status["raw_boundary_flags"] == {}
    assert validate_evidence_summary_answer_result(status).status == "blocked"
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_no_model_result_filters_forbidden_metadata() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[_ready_digest()],
    )

    result = build_no_model_evidence_summary_answer_result(
        context,
        metadata={
            "safe_label": "accepted",
            "prompt_marker": "ignored",
            "runtime_hint": "ignored",
            "raw_marker": "ignored",
            "safe_value_rejected": "response_text",
            "nested": {"safe": "ignored"},
        },
    )
    status = evidence_summary_answer_result_status_dict(result)

    assert result.metadata["safe_label"] == "accepted"
    assert "prompt_marker" not in result.metadata
    assert "runtime_hint" not in result.metadata
    assert "raw_marker" not in result.metadata
    assert "safe_value_rejected" not in result.metadata
    assert "nested" not in result.metadata
    assert validate_evidence_summary_answer_result(status).request_id == "request-603"
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_no_model_result_never_produces_success_or_answer_fields() -> None:
    for digest in (_ready_digest(), _blocked_digest(), _empty_digest()):
        context = build_evidence_summary_answer_context(
            request_id="request-603",
            user_question="What does the governed evidence say?",
            digests=[digest],
        )

        result = build_no_model_evidence_summary_answer_result(context)

        assert result.status != "success"
        assert result.answer is None
        assert result.answer_preview is None


def test_no_model_result_is_exported_from_package_root() -> None:
    assert callable(build_no_model_evidence_summary_answer_result)
    assert callable(evidence_summary_answer_result_status_dict)


def test_no_model_result_source_has_no_forbidden_imports_or_inputs() -> None:
    source = BUILDER_SOURCE.read_text(encoding="utf-8")

    assert "from external_readonly" not in source
    assert "import external_readonly" not in source
    assert "behavior_contracts" not in source
    assert "contract_core" not in source
    assert "observability_hub" not in source
    assert "runtime_container" not in source
    assert "cognition_cli" not in source
    assert "cognition_task_workflows" not in source
    assert "product_runtime_assembly" not in source
    assert "google.adk" not in source
    assert "litellm" not in source
    assert "adk_adapter" not in source
    assert "provider_response" not in source
    assert "raw_provider_response" not in source
    assert "sanitized_excerpt" not in source
    assert "sanitized_excerpt_preview" not in source
    assert "model_context_items" not in source
    assert "ExternalReadonlyEvidenceEnvelope" not in source
    assert "ExternalReadonlyEvidenceSummary" not in source
    assert "ExternalReadonlyEvidenceReadContext" not in source
    assert "ProductGatewayResponse" not in source
    assert "observability_candidate_body" not in source
    assert "config_context" not in source


def _ready_digest() -> dict[str, object]:
    return {
        "product": "evidence_summary_answer",
        "payload_type": "governed_evidence_digest",
        "payload_version": "governed_evidence_digest_v1",
        "digest_id": "digest-603",
        "digest_ref": "governed-evidence-digest://digest-603",
        "evidence_ref": "evidence://external-readonly/item/603",
        "evidence_output_ref": "outputs/external-readonly/603.json",
        "source_url_host": "example.com",
        "source_url_scheme": "https",
        "runtime_status": "governed_summary_facts_ready",
        "status": "ready",
        "reference_review_ready": True,
        "allowed_for_model_context": True,
        "evidence_written": True,
        "content_hash": "c" * 64,
        "total_excerpt_chars": 45,
        "raw_boundary_flags": {},
        "blocking_reasons": [],
        "warnings": ["review_scope_limited"],
        "summary_facts": ["The source describes a governed answer context."],
        "topic_labels": ["contracts"],
        "risk_labels": [],
        "answerability": "answerable",
        "digest_generation_policy_ref": (
            "policy://product-application-assembly/governed-evidence-digest/minimal-v1"
        ),
        "digest_budget": 4000,
        "metadata": {"source": "product_application_assembly.test"},
    }


def _blocked_digest(
    *,
    digest_id: str = "digest-603",
    reason: str = "reference_review_not_ready",
) -> dict[str, object]:
    return {
        **_ready_digest(),
        "digest_id": digest_id,
        "digest_ref": f"governed-evidence-digest://{digest_id}",
        "evidence_ref": f"evidence://external-readonly/item/{digest_id}",
        "status": "blocked",
        "reference_review_ready": False,
        "allowed_for_model_context": False,
        "evidence_written": False,
        "total_excerpt_chars": 0,
        "blocking_reasons": [reason],
        "warnings": [],
        "summary_facts": [],
        "answerability": "blocked",
    }


def _answerability_blocked_digest_without_reason() -> dict[str, object]:
    return {
        **_ready_digest(),
        "status": "empty",
        "allowed_for_model_context": False,
        "evidence_written": False,
        "total_excerpt_chars": 0,
        "blocking_reasons": [],
        "warnings": [],
        "summary_facts": [],
        "answerability": "blocked",
    }


def _empty_digest() -> dict[str, object]:
    return {
        **_ready_digest(),
        "status": "empty",
        "allowed_for_model_context": False,
        "evidence_written": True,
        "total_excerpt_chars": 0,
        "blocking_reasons": [],
        "warnings": ["upstream_governed_summary_facts_empty"],
        "summary_facts": [],
        "answerability": "insufficient_evidence",
    }
