from __future__ import annotations

import json
from pathlib import Path

import pytest

from behavior_contracts.evidence_summary_answer import (
    validate_evidence_summary_answer_guards,
)
from product_application_assembly import (
    EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_INTERACTION_MODE,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_SOURCE,
    build_evidence_summary_answer_follow_up_context,
    build_evidence_summary_answer_follow_up_seed,
    evidence_summary_answer_context_status_dict,
    evidence_summary_answer_follow_up_seed_status_dict,
)
from schemas.evidence_summary_answer import (
    EvidenceSummaryAnswerFollowUpSeedSchema,
    validate_evidence_summary_answer_follow_up_seed,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
BUILDER_SOURCE = (
    REPO_ROOT
    / "packages"
    / "product_application_assembly"
    / "src"
    / "product_application_assembly"
    / "evidence_summary_answer_follow_up.py"
)


def test_follow_up_seed_from_success_result_is_public_and_temporary() -> None:
    seed = build_evidence_summary_answer_follow_up_seed(_result())
    status = evidence_summary_answer_follow_up_seed_status_dict(seed)

    assert isinstance(seed, EvidenceSummaryAnswerFollowUpSeedSchema)
    assert seed.follow_up_allowed is True
    assert seed.temporary_only is True
    assert seed.durable_session is False
    assert seed.memory_enabled is False
    assert seed.digest_refs == ["governed-evidence-digest://digest-681"]
    serialized = json.dumps(status, ensure_ascii=False, sort_keys=True)
    assert "The governed evidence supports the initial answer." not in serialized
    assert "What does the governed evidence say?" not in serialized
    assert validate_evidence_summary_answer_follow_up_seed(status).seed_id
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_follow_up_context_reuses_seed_refs_and_existing_digests() -> None:
    seed = build_evidence_summary_answer_follow_up_seed(_result())
    context = build_evidence_summary_answer_follow_up_context(
        seed,
        request_id="request-681/follow-up-1/context",
        follow_up_question="Can you restate the key point?",
        digests=[_ready_digest()],
    )
    status = evidence_summary_answer_context_status_dict(context)

    assert context.user_question == "Can you restate the key point?"
    assert context.evidence_refs[0].ref == "evidence://external-readonly/item/681"
    assert context.metadata["source"] == (
        PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_SOURCE
    )
    assert context.metadata["interaction_mode"] == (
        EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_INTERACTION_MODE
    )
    assert context.metadata["follow_up"] is True
    assert context.metadata["temporary_only"] is True
    assert context.metadata["durable_session"] is False
    assert context.metadata["memory_enabled"] is False
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_follow_up_context_rejects_uncovered_digest_refs() -> None:
    seed = build_evidence_summary_answer_follow_up_seed(_result())
    digest = _ready_digest()
    digest["digest_ref"] = "governed-evidence-digest://other"

    with pytest.raises(ValueError):
        build_evidence_summary_answer_follow_up_context(
            seed,
            request_id="request-681/follow-up-1/context",
            follow_up_question="Can you restate the key point?",
            digests=[digest],
        )


def test_follow_up_builder_is_exported_from_package_root() -> None:
    assert callable(build_evidence_summary_answer_follow_up_context)
    assert callable(build_evidence_summary_answer_follow_up_seed)
    assert callable(evidence_summary_answer_follow_up_seed_status_dict)


def test_follow_up_builder_source_has_no_execution_layer_imports() -> None:
    source = BUILDER_SOURCE.read_text(encoding="utf-8")

    assert "from external_readonly" not in source
    assert "behavior_contracts" not in source
    assert "contract_core" not in source
    assert "runtime_container" not in source
    assert "cognition_cli" not in source
    assert "product_runtime_assembly" not in source
    assert "google.adk" not in source
    assert "litellm" not in source
    assert "adk_adapter" not in source


def _result() -> dict[str, object]:
    return {
        "product": "evidence_summary_answer",
        "payload_type": "evidence_summary_answer_result",
        "payload_version": "evidence_summary_answer_result_v1",
        "request_id": "request-681/context",
        "status": "success",
        "answer": "The governed evidence supports the initial answer.",
        "answer_preview": "The governed evidence supports the initial answer.",
        "evidence_refs_used": [
            {
                "ref": "evidence://external-readonly/item/681",
                "kind": "external_readonly_evidence",
                "purpose": "answer_context",
            }
        ],
        "digest_refs_used": ["governed-evidence-digest://digest-681"],
        "additional_refs_used": [
            {
                "ref": "governed-evidence-digest://digest-681",
                "kind": "governed_evidence_digest",
                "purpose": "digest_context",
            }
        ],
        "insufficient_evidence_reason": None,
        "citation_failures": [],
        "blocking_reasons": [],
        "warnings": [],
        "llm_call_allowed": True,
        "llm_call_attempted": True,
        "llm_runtime_call_performed": True,
        "raw_boundary_flags": {},
        "metadata": {"source": "product_application_assembly.test"},
    }


def _ready_digest() -> dict[str, object]:
    return {
        "product": "evidence_summary_answer",
        "payload_type": "governed_evidence_digest",
        "payload_version": "governed_evidence_digest_v1",
        "digest_id": "digest-681",
        "digest_ref": "governed-evidence-digest://digest-681",
        "evidence_ref": "evidence://external-readonly/item/681",
        "evidence_output_ref": "outputs/external-readonly/681.json",
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
