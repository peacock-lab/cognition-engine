from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from behavior_contracts.evidence_summary_answer import (
    validate_evidence_summary_answer_guards,
)
from product_application_assembly import (
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_ANSWER_POLICY_REF,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_CITATION_POLICY_REF,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_SOURCE,
    build_evidence_summary_answer_context,
    evidence_summary_answer_context_status_dict,
)
from schemas.evidence_summary_answer import (
    EvidenceSummaryAnswerContextSchema,
    validate_evidence_summary_answer_context,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
BUILDER_SOURCE = (
    REPO_ROOT
    / "packages"
    / "product_application_assembly"
    / "src"
    / "product_application_assembly"
    / "evidence_summary_answer_context.py"
)


def test_context_builder_maps_ready_digest_to_answer_context() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-601",
        user_question="What does the governed evidence say?",
        digests=[_ready_digest()],
        model_context_budget=4000,
        metadata={"request_id": "request-601"},
    )
    status = evidence_summary_answer_context_status_dict(context)

    assert isinstance(context, EvidenceSummaryAnswerContextSchema)
    assert context.request_id == "request-601"
    assert context.user_question == "What does the governed evidence say?"
    assert context.digests[0].digest_id == "digest-601"
    assert context.evidence_refs[0].ref == "evidence://external-readonly/item/601"
    assert context.evidence_refs[0].kind == "external_readonly_evidence"
    assert context.evidence_refs[0].purpose == "answer_context"
    assert context.additional_refs[0].ref == "governed-evidence-digest://digest-601"
    assert context.additional_refs[0].kind == "governed_evidence_digest"
    assert context.additional_refs[0].purpose == "digest_context"
    assert (
        context.answer_policy_ref
        == PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_ANSWER_POLICY_REF
    )
    assert (
        context.citation_policy_ref
        == PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_CITATION_POLICY_REF
    )
    assert context.model_context_budget == 4000
    assert (
        context.metadata["source"]
        == PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_SOURCE
    )
    assert context.metadata["digest_count"] == 1
    assert context.metadata["refs_source"] == "derived_from_digest"
    assert validate_evidence_summary_answer_context(status).request_id == "request-601"
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_context_builder_accepts_mapping_digest_input() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-601",
        user_question="What is the answer context?",
        digests=[_ready_digest()],
    )

    assert context.digests[0].digest_ref == "governed-evidence-digest://digest-601"
    assert validate_evidence_summary_answer_guards(
        evidence_summary_answer_context_status_dict(context)
    ).passed is True


def test_context_builder_accepts_explicit_safe_refs() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-601",
        user_question="What does the cited evidence support?",
        digests=[_ready_digest()],
        evidence_refs=[
            {
                "ref": "evidence://external-readonly/item/601",
                "kind": "external_readonly_evidence",
                "purpose": "citation_source",
                "metadata": {"rank": 1},
            }
        ],
        additional_refs=[
            {
                "ref": "governed-evidence-digest://digest-601",
                "kind": "governed_evidence_digest",
                "purpose": "digest_context",
            }
        ],
    )

    assert context.metadata["refs_source"] == "explicit"
    assert context.evidence_refs[0].purpose == "citation_source"
    assert context.evidence_refs[0].metadata == {"rank": 1}
    assert validate_evidence_summary_answer_guards(
        evidence_summary_answer_context_status_dict(context)
    ).passed is True


def test_context_builder_rejects_empty_digests() -> None:
    with pytest.raises(ValidationError):
        build_evidence_summary_answer_context(
            request_id="request-601",
            user_question="What does the governed evidence say?",
            digests=[],
        )


def test_context_builder_rejects_uncovered_evidence_refs() -> None:
    with pytest.raises(ValidationError):
        build_evidence_summary_answer_context(
            request_id="request-601",
            user_question="What does the governed evidence say?",
            digests=[_ready_digest()],
            evidence_refs=[
                {
                    "ref": "evidence://external-readonly/other",
                    "kind": "external_readonly_evidence",
                }
            ],
        )


def test_context_builder_filters_forbidden_metadata() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-601",
        user_question="What does the governed evidence say?",
        digests=[_ready_digest()],
        metadata={
            "safe_label": "accepted",
            "prompt_marker": "ignored",
            "runtime_hint": "ignored",
            "nested": {"safe": "ignored"},
        },
    )
    status = evidence_summary_answer_context_status_dict(context)

    assert context.metadata["safe_label"] == "accepted"
    assert "prompt_marker" not in context.metadata
    assert "runtime_hint" not in context.metadata
    assert "nested" not in context.metadata
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_context_builder_rejects_forbidden_explicit_ref_metadata() -> None:
    with pytest.raises(ValidationError):
        build_evidence_summary_answer_context(
            request_id="request-601",
            user_question="What does the governed evidence say?",
            digests=[_ready_digest()],
            evidence_refs=[
                {
                    "ref": "evidence://external-readonly/item/601",
                    "kind": "external_readonly_evidence",
                    "metadata": {"raw_payload": "forbidden"},
                }
            ],
        )


def test_context_status_dict_accepts_mapping_context() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-601",
        user_question="What does the governed evidence say?",
        digests=[_ready_digest()],
    )
    status = evidence_summary_answer_context_status_dict(
        context.model_dump(mode="json")
    )

    assert status["payload_type"] == "evidence_summary_answer_context"
    assert status["request_id"] == "request-601"
    assert status["digests"][0]["digest_id"] == "digest-601"
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_context_builder_is_exported_from_package_root() -> None:
    assert callable(build_evidence_summary_answer_context)
    assert callable(evidence_summary_answer_context_status_dict)


def test_context_builder_source_has_no_forbidden_imports_or_inputs() -> None:
    source = BUILDER_SOURCE.read_text(encoding="utf-8")

    assert "from external_readonly" not in source
    assert "import external_readonly" not in source
    assert "behavior_contracts" not in source
    assert "contract_core" not in source
    assert "observability_hub" not in source
    assert "runtime_container" not in source
    assert "cognition_cli" not in source
    assert "cognition_operation_flows" not in source
    assert "product_runtime_assembly" not in source
    assert "google.adk" not in source
    assert "litellm" not in source
    assert "adk_adapter" not in source
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
        "digest_id": "digest-601",
        "digest_ref": "governed-evidence-digest://digest-601",
        "evidence_ref": "evidence://external-readonly/item/601",
        "evidence_output_ref": "outputs/external-readonly/601.json",
        "source_url_host": "example.com",
        "source_url_scheme": "https",
        "runtime_status": "governed_summary_facts_ready",
        "status": "ready",
        "reference_review_ready": True,
        "allowed_for_model_context": True,
        "evidence_written": True,
        "content_hash": "b" * 64,
        "total_excerpt_chars": 45,
        "raw_boundary_flags": {},
        "blocking_reasons": [],
        "warnings": [],
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
