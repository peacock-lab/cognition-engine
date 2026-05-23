from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from behavior_contracts.evidence_summary_answer import (
    validate_evidence_summary_answer_guards,
)
from product_application_assembly import (
    PRODUCT_APPLICATION_GOVERNED_EVIDENCE_DIGEST_POLICY_REF,
    build_governed_evidence_digest_from_external_readonly_facts,
    governed_evidence_digest_status_dict,
)
from schemas.evidence_summary_answer import validate_governed_evidence_digest
from schemas.external_readonly_governed_summary_facts import (
    EXTERNAL_READONLY_GOVERNED_SUMMARY_FACT_REF_PREFIX,
    ExternalReadonlyGovernedSummaryFactsSchema,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
PRODUCER_SOURCE = (
    REPO_ROOT
    / "packages"
    / "product_application_assembly"
    / "src"
    / "product_application_assembly"
    / "governed_evidence_digest.py"
)


def test_digest_builder_maps_ready_governed_facts_to_answerable_digest() -> None:
    digest = build_governed_evidence_digest_from_external_readonly_facts(
        _ready_facts(),
        topic_labels=("contracts",),
        metadata={"request_id": "request-599"},
    )
    status = governed_evidence_digest_status_dict(digest)

    assert digest.status == "ready"
    assert digest.answerability == "answerable"
    assert digest.allowed_for_model_context is True
    assert digest.summary_facts == ["The source describes public governed facts."]
    assert digest.evidence_ref == "evidence://external-readonly/item/599"
    assert digest.evidence_output_ref == "outputs/external-readonly/599.json"
    assert digest.source_url_host == "example.com"
    assert digest.source_url_scheme == "https"
    assert digest.total_excerpt_chars == len(digest.summary_facts[0])
    assert digest.digest_budget == 4000
    assert (
        digest.digest_generation_policy_ref
        == PRODUCT_APPLICATION_GOVERNED_EVIDENCE_DIGEST_POLICY_REF
    )
    assert (
        digest.metadata["total_excerpt_chars_source"]
        == "governed_summary_facts.total_fact_chars"
    )
    assert validate_governed_evidence_digest(status).status == "ready"
    assert validate_evidence_summary_answer_guards(status).passed is True
    assert "sanitized_excerpt" not in str(status)
    assert "sanitized_excerpt_preview" not in str(status)
    assert "model_context_items" not in str(status)


def test_digest_builder_accepts_mapping_input() -> None:
    digest = build_governed_evidence_digest_from_external_readonly_facts(
        _ready_facts().model_dump(mode="json"),
        digest_id="digest-599",
    )

    assert digest.digest_id == "digest-599"
    assert digest.digest_ref == "governed-evidence-digest://digest-599"
    assert digest.status == "ready"
    assert digest.answerability == "answerable"


def test_digest_builder_maps_blocked_facts_to_blocked_digest() -> None:
    digest = build_governed_evidence_digest_from_external_readonly_facts(
        _blocked_facts()
    )
    status = governed_evidence_digest_status_dict(digest)

    assert digest.status == "blocked"
    assert digest.answerability == "blocked"
    assert digest.allowed_for_model_context is False
    assert digest.summary_facts == []
    assert "source_policy_blocked" in digest.blocking_reasons
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_digest_builder_maps_empty_facts_to_insufficient_digest() -> None:
    digest = build_governed_evidence_digest_from_external_readonly_facts(
        _empty_facts()
    )
    status = governed_evidence_digest_status_dict(digest)

    assert digest.status == "empty"
    assert digest.answerability == "insufficient_evidence"
    assert digest.allowed_for_model_context is False
    assert digest.summary_facts == []
    assert "upstream_governed_summary_facts_empty" in digest.warnings
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_digest_builder_rejects_invalid_facts_mapping_without_digest() -> None:
    payload = _ready_facts().model_dump(mode="json")
    payload["facts"][0]["fact_text"] = "sanitized_excerpt must remain upstream"

    with pytest.raises(ValidationError):
        build_governed_evidence_digest_from_external_readonly_facts(payload)


def test_digest_status_dict_compacts_raw_boundary_flags() -> None:
    status = governed_evidence_digest_status_dict(
        build_governed_evidence_digest_from_external_readonly_facts(_ready_facts())
    )

    assert status["raw_boundary_flags"] == {}


def test_digest_builder_is_exported_from_package_root() -> None:
    assert callable(build_governed_evidence_digest_from_external_readonly_facts)
    assert callable(governed_evidence_digest_status_dict)


def test_digest_producer_source_has_no_forbidden_imports_or_inputs() -> None:
    source = PRODUCER_SOURCE.read_text(encoding="utf-8")

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


def _ready_facts() -> ExternalReadonlyGovernedSummaryFactsSchema:
    fact_text = "The source describes public governed facts."
    return ExternalReadonlyGovernedSummaryFactsSchema(
        status="ready",
        evidence_ref="evidence://external-readonly/item/599",
        evidence_output_path="outputs/external-readonly/599.json",
        source_url_host="example.com",
        source_url_scheme="https",
        reference_review_ready=True,
        allowed_for_model_context=True,
        evidence_written=True,
        content_hash="a" * 64,
        facts=[
            {
                "fact_ref": (
                    f"{EXTERNAL_READONLY_GOVERNED_SUMMARY_FACT_REF_PREFIX}599-1"
                ),
                "fact_text": fact_text,
                "fact_index": 1,
                "evidence_ref": "evidence://external-readonly/item/599",
                "source_url_host": "example.com",
                "content_hash": "a" * 64,
            }
        ],
        fact_count=1,
        total_fact_chars=len(fact_text),
        generation_policy_ref=(
            "policy://external-readonly/governed-summary-facts/minimal-v1"
        ),
        facts_budget=4000,
        metadata={"candidate_only": True},
    )


def _blocked_facts() -> ExternalReadonlyGovernedSummaryFactsSchema:
    return ExternalReadonlyGovernedSummaryFactsSchema(
        status="blocked",
        evidence_ref="evidence://external-readonly/item/599",
        allowed_for_model_context=False,
        blocking_reasons=["source_policy_blocked"],
        facts_budget=4000,
    )


def _empty_facts() -> ExternalReadonlyGovernedSummaryFactsSchema:
    return ExternalReadonlyGovernedSummaryFactsSchema(
        status="empty",
        evidence_ref="evidence://external-readonly/item/599",
        allowed_for_model_context=False,
        facts_budget=4000,
    )
