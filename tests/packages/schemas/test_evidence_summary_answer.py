from __future__ import annotations

import copy
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas import (
    EvidenceSummaryAnswerContextSchema as RootEvidenceSummaryAnswerContextSchema,
    GovernedEvidenceDigestSchema as RootGovernedEvidenceDigestSchema,
    validate_governed_evidence_digest as root_validate_governed_evidence_digest,
)
from schemas.evidence_summary_answer import (
    EVIDENCE_SUMMARY_ANSWER_CONTEXT_VERSION,
    EVIDENCE_SUMMARY_ANSWER_PRODUCT,
    EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION,
    GOVERNED_EVIDENCE_DIGEST_VERSION,
    EvidenceSummaryAnswerContextSchema,
    EvidenceSummaryAnswerResultSchema,
    GovernedEvidenceDigestSchema,
    validate_evidence_summary_answer_context,
    validate_evidence_summary_answer_result,
    validate_governed_evidence_digest,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_SOURCE_ROOT = REPO_ROOT / "packages" / "schemas" / "src" / "schemas"


def test_governed_evidence_digest_accepts_minimal_public_shape() -> None:
    digest = validate_governed_evidence_digest(_digest())

    assert isinstance(digest, GovernedEvidenceDigestSchema)
    assert digest.product == EVIDENCE_SUMMARY_ANSWER_PRODUCT
    assert digest.payload_type == "governed_evidence_digest"
    assert digest.payload_version == GOVERNED_EVIDENCE_DIGEST_VERSION
    assert digest.digest_ref == "governed-evidence-digest://request-1/digest-1"
    assert digest.evidence_ref == "evidence://external-readonly/request-1/fetch-1"
    assert digest.source_url_host == "example.com"
    assert digest.raw_boundary_flags.raw_payload_included is False
    assert digest.summary_facts == ["The source describes a governed answer context."]


def test_evidence_summary_answer_context_accepts_minimal_public_shape() -> None:
    context = validate_evidence_summary_answer_context(_context())

    assert isinstance(context, EvidenceSummaryAnswerContextSchema)
    assert context.product == EVIDENCE_SUMMARY_ANSWER_PRODUCT
    assert context.payload_type == "evidence_summary_answer_context"
    assert context.payload_version == EVIDENCE_SUMMARY_ANSWER_CONTEXT_VERSION
    assert context.digests[0].digest_id == "digest-1"
    assert context.evidence_refs[0].ref == "evidence://external-readonly/request-1/fetch-1"


def test_evidence_summary_answer_result_accepts_success_with_citation() -> None:
    result = validate_evidence_summary_answer_result(_result())

    assert isinstance(result, EvidenceSummaryAnswerResultSchema)
    assert result.product == EVIDENCE_SUMMARY_ANSWER_PRODUCT
    assert result.payload_type == "evidence_summary_answer_result"
    assert result.payload_version == EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION
    assert result.status == "success"
    assert result.evidence_refs_used[0].ref == "evidence://external-readonly/request-1/fetch-1"
    assert result.digest_refs_used == ["governed-evidence-digest://request-1/digest-1"]


@pytest.mark.parametrize(
    ("payload_kind", "field", "value"),
    [
        ("digest", "product", "other"),
        ("digest", "payload_type", "other"),
        ("digest", "payload_version", "other"),
        ("context", "product", "other"),
        ("context", "payload_type", "other"),
        ("context", "payload_version", "other"),
        ("result", "product", "other"),
        ("result", "payload_type", "other"),
        ("result", "payload_version", "other"),
    ],
)
def test_evidence_summary_answer_rejects_invalid_payload_headers(
    payload_kind: str,
    field: str,
    value: str,
) -> None:
    payload = _payload_for_kind(payload_kind)
    payload[field] = value

    with pytest.raises(ValidationError):
        _validate_payload(payload)


def test_digest_rejects_invalid_digest_ref() -> None:
    digest = _digest()
    digest["digest_ref"] = "digest://request-1/digest-1"

    with pytest.raises(ValidationError):
        validate_governed_evidence_digest(digest)


def test_digest_rejects_invalid_evidence_ref() -> None:
    digest = _digest()
    digest["evidence_ref"] = "evidence://other/request-1/fetch-1"

    with pytest.raises(ValidationError):
        validate_governed_evidence_digest(digest)


def test_digest_rejects_source_url_host_with_path_or_query() -> None:
    digest = _digest()
    digest["source_url_host"] = "example.com/path?x=1"

    with pytest.raises(ValidationError):
        validate_governed_evidence_digest(digest)


def test_digest_rejects_blocked_without_reasons() -> None:
    digest = _digest()
    digest["status"] = "blocked"
    digest["answerability"] = "blocked"
    digest["allowed_for_model_context"] = False
    digest["blocking_reasons"] = []

    with pytest.raises(ValidationError):
        validate_governed_evidence_digest(digest)


def test_digest_rejects_raw_boundary_flags_when_answerable() -> None:
    digest = _digest()
    digest["raw_boundary_flags"] = {"raw_provider_response_included": True}

    with pytest.raises(ValidationError):
        validate_governed_evidence_digest(digest)


@pytest.mark.parametrize(
    "summary_fact",
    [
        "sanitized_excerpt_preview: body text",
        "raw provider response contained facts",
        "config_context value leaked into context",
    ],
)
def test_digest_rejects_raw_markers_in_summary_facts(summary_fact: str) -> None:
    digest = _digest()
    digest["summary_facts"] = [summary_fact]

    with pytest.raises(ValidationError):
        validate_governed_evidence_digest(digest)


def test_context_rejects_evidence_refs_that_do_not_cover_digest_refs() -> None:
    context = _context()
    context["evidence_refs"] = [{"ref": "evidence://external-readonly/other", "kind": "evidence"}]

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_context(context)


@pytest.mark.parametrize("key", ["prompt", "messages", "config_context"])
def test_context_rejects_forbidden_metadata_keys(key: str) -> None:
    context = _context()
    context["metadata"] = {key: "forbidden"}

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_context(context)


def test_result_success_rejects_missing_evidence_refs_used() -> None:
    result = _result()
    result["evidence_refs_used"] = []

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_result(result)


def test_result_insufficient_evidence_requires_reason() -> None:
    result = _result(status="insufficient_evidence")
    result["answer"] = None
    result["answer_preview"] = None
    result["evidence_refs_used"] = []
    result["digest_refs_used"] = []
    result["insufficient_evidence_reason"] = None
    result["llm_runtime_call_performed"] = False

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_result(result)


def test_result_blocked_requires_blocking_reason() -> None:
    result = _result(status="blocked")
    result["answer"] = None
    result["answer_preview"] = None
    result["evidence_refs_used"] = []
    result["digest_refs_used"] = []
    result["blocking_reasons"] = []
    result["llm_runtime_call_performed"] = False

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_result(result)


def test_result_rejects_llm_runtime_flag_inconsistency() -> None:
    result = _result()
    result["llm_call_allowed"] = False
    result["llm_call_attempted"] = True
    result["llm_runtime_call_performed"] = True

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_result(result)


def test_result_rejects_raw_provider_output_metadata() -> None:
    result = _result()
    result["metadata"] = {"response_text": "raw provider output"}

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_result(result)


def test_evidence_summary_answer_schema_has_no_execution_layer_imports() -> None:
    source = (SCHEMA_SOURCE_ROOT / "evidence_summary_answer.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:product_gateway|cognition_cli|behavior_contracts|config_contexts|"
        r"runtime_container|composition|product_runtime_assembly|observability_hub|"
        r"adk_adapter|google\.adk|litellm)\b",
        re.MULTILINE,
    )

    assert forbidden_imports.search(source) is None


def test_schemas_root_exports_evidence_summary_answer_contracts() -> None:
    assert RootGovernedEvidenceDigestSchema is GovernedEvidenceDigestSchema
    assert RootEvidenceSummaryAnswerContextSchema is EvidenceSummaryAnswerContextSchema
    assert root_validate_governed_evidence_digest(_digest()).digest_id == "digest-1"


def _validate_payload(payload: dict[str, object]) -> object:
    payload_type = payload.get("payload_type")
    if payload_type == "governed_evidence_digest":
        return validate_governed_evidence_digest(payload)
    if payload_type == "evidence_summary_answer_context":
        return validate_evidence_summary_answer_context(payload)
    if payload_type == "evidence_summary_answer_result":
        return validate_evidence_summary_answer_result(payload)
    if "digest_ref" in payload:
        return validate_governed_evidence_digest(payload)
    if "digests" in payload:
        return validate_evidence_summary_answer_context(payload)
    return validate_evidence_summary_answer_result(payload)


def _payload_for_kind(payload_kind: str) -> dict[str, object]:
    if payload_kind == "digest":
        return _digest()
    if payload_kind == "context":
        return _context()
    if payload_kind == "result":
        return _result()
    raise AssertionError(f"unknown payload kind: {payload_kind}")


def _digest() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "governed_evidence_digest",
        "payload_version": GOVERNED_EVIDENCE_DIGEST_VERSION,
        "digest_id": "digest-1",
        "digest_ref": "governed-evidence-digest://request-1/digest-1",
        "evidence_ref": "evidence://external-readonly/request-1/fetch-1",
        "evidence_output_ref": "external-readonly-output://request-1/fetch-1",
        "source_url_host": "example.com",
        "source_url_scheme": "https",
        "runtime_status": "success",
        "status": "ready",
        "reference_review_ready": True,
        "allowed_for_model_context": True,
        "evidence_written": True,
        "content_hash": "sha256:abc123",
        "total_excerpt_chars": 128,
        "raw_boundary_flags": {},
        "blocking_reasons": [],
        "warnings": [],
        "summary_facts": ["The source describes a governed answer context."],
        "topic_labels": ["contracts"],
        "risk_labels": [],
        "answerability": "answerable",
        "digest_generation_policy_ref": (
            "policy://evidence-summary-answer/digest-generation-v1"
        ),
        "digest_budget": 4000,
        "metadata": {"source": "schemas.test"},
    }


def _context() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_context",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_CONTEXT_VERSION,
        "request_id": "request-1",
        "user_question": "What does the governed evidence say?",
        "digests": [copy.deepcopy(_digest())],
        "evidence_refs": [
            {
                "ref": "evidence://external-readonly/request-1/fetch-1",
                "kind": "external_readonly_evidence",
                "purpose": "answer_context",
            }
        ],
        "additional_refs": [
            {
                "ref": "governed-evidence-digest://request-1/digest-1",
                "kind": "governed_evidence_digest",
                "purpose": "digest_context",
            }
        ],
        "answer_policy_ref": "policy://evidence-summary-answer/answer-v1",
        "citation_policy_ref": "policy://evidence-summary-answer/citation-v1",
        "model_context_budget": 4000,
        "metadata": {"source": "schemas.test"},
    }


def _result(*, status: str = "success") -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_result",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION,
        "request_id": "request-1",
        "status": status,
        "answer": "The governed evidence supports using a schema first.",
        "answer_preview": "The governed evidence supports using a schema first.",
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
        "metadata": {"source": "schemas.test"},
    }
