from __future__ import annotations

from copy import deepcopy

from behavior_contracts import (
    ExternalReadonlyGovernedSummaryFactsHeaderGuard as RootHeaderGuard,
    validate_external_readonly_governed_summary_facts_guards as root_validate_guards,
)
from behavior_contracts.external_readonly_governed_summary_facts import (
    DEFAULT_EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_GUARDS,
    validate_external_readonly_governed_summary_facts_guards,
)
from schemas.evidence_summary_answer import EXTERNAL_READONLY_EVIDENCE_REF_PREFIX
from schemas.external_readonly_governed_summary_facts import (
    EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_PAYLOAD_TYPE,
    EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_VERSION,
    EXTERNAL_READONLY_GOVERNED_SUMMARY_FACT_REF_PREFIX,
)


EVIDENCE_REF = f"{EXTERNAL_READONLY_EVIDENCE_REF_PREFIX}run-001/fetch-001"
FACT_TEXT = "The source identifies governed evidence summaries as public context."


def test_governed_summary_facts_guards_accept_safe_payload() -> None:
    payload = _ready_payload()

    result = validate_external_readonly_governed_summary_facts_guards(payload)

    assert result.passed is True
    assert result.violations == ()
    assert root_validate_guards(payload).passed is True
    assert RootHeaderGuard().guard_name.endswith("header_guard")
    assert DEFAULT_EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_GUARDS


def test_governed_summary_facts_guards_reject_header_mismatch() -> None:
    payload = _ready_payload()
    payload["payload_version"] = "wrong"

    result = validate_external_readonly_governed_summary_facts_guards(payload)

    assert result.passed is False
    assert any("payload_version" in violation for violation in result.violations)


def test_governed_summary_facts_guards_reject_raw_boundary_key() -> None:
    payload = _ready_payload()
    payload["metadata"] = {"sanitized_excerpt_preview": "must stay private"}

    result = validate_external_readonly_governed_summary_facts_guards(payload)

    assert result.passed is False
    assert any("raw boundary" in violation for violation in result.violations)


def test_governed_summary_facts_guards_reject_sanitized_excerpt_key() -> None:
    payload = _ready_payload()
    payload["metadata"] = {"sanitized_excerpt": "must stay internal"}

    result = validate_external_readonly_governed_summary_facts_guards(payload)

    assert result.passed is False
    assert any("raw boundary" in violation for violation in result.violations)


def test_governed_summary_facts_guards_reject_authorization_key() -> None:
    payload = _ready_payload()
    payload["metadata"] = {"authorization": "Bearer must-not-cross"}

    result = validate_external_readonly_governed_summary_facts_guards(payload)

    assert result.passed is False
    assert any("raw boundary" in violation for violation in result.violations)


def test_governed_summary_facts_guards_reject_raw_boundary_marker() -> None:
    payload = _ready_payload()
    payload["facts"][0]["fact_text"] = "This includes a raw provider response."

    result = validate_external_readonly_governed_summary_facts_guards(payload)

    assert result.passed is False
    assert any("raw boundary" in violation for violation in result.violations)


def test_governed_summary_facts_guards_reject_sanitized_excerpt_marker() -> None:
    payload = _ready_payload()
    fact_text = "sanitized_excerpt must stay internal to external_readonly"
    payload["facts"][0]["fact_text"] = fact_text
    payload["total_fact_chars"] = len(fact_text)

    result = validate_external_readonly_governed_summary_facts_guards(payload)

    assert result.passed is False
    assert any("raw boundary" in violation for violation in result.violations)


def test_governed_summary_facts_guards_allow_public_package_names() -> None:
    payload = _ready_payload()
    fact_text = (
        "The public packages include contract_core, schemas, "
        "behavior_contracts, config_assembly, and config_contexts."
    )
    payload["facts"][0]["fact_text"] = fact_text
    payload["total_fact_chars"] = len(fact_text)

    result = validate_external_readonly_governed_summary_facts_guards(payload)

    assert result.passed is True


def test_governed_summary_facts_guards_reject_config_context_marker() -> None:
    payload = _ready_payload()
    fact_text = "The config_context value must stay inside the runtime boundary."
    payload["facts"][0]["fact_text"] = fact_text
    payload["total_fact_chars"] = len(fact_text)

    result = validate_external_readonly_governed_summary_facts_guards(payload)

    assert result.passed is False
    assert any("raw boundary" in violation for violation in result.violations)


def test_governed_summary_facts_guards_reject_raw_flags() -> None:
    payload = _ready_payload()
    payload["raw_boundary_flags"] = {"raw_payload_included": True}

    result = validate_external_readonly_governed_summary_facts_guards(payload)

    assert result.passed is False
    assert any("raw_payload_included" in violation for violation in result.violations)


def test_governed_summary_facts_guards_reject_invalid_content() -> None:
    payload = _ready_payload()
    payload["source_url_host"] = "https://example.test/a"
    payload["fact_count"] = 2

    result = validate_external_readonly_governed_summary_facts_guards(payload)

    assert result.passed is False
    assert any("source_url_host" in violation for violation in result.violations)
    assert any("fact_count" in violation for violation in result.violations)


def test_governed_summary_facts_guards_accept_chunk_lineage_metadata() -> None:
    payload = _ready_payload()
    payload["facts"][0]["metadata"] = _chunk_metadata()

    result = validate_external_readonly_governed_summary_facts_guards(payload)

    assert result.passed is True


def test_governed_summary_facts_guards_reject_invalid_chunk_lineage_metadata() -> None:
    payload = _ready_payload()
    payload["facts"][0]["metadata"] = {
        **_chunk_metadata(),
        "chunk_index": 3,
        "chunk_count": 2,
    }

    result = validate_external_readonly_governed_summary_facts_guards(payload)

    assert result.passed is False
    assert any("chunk_index" in violation for violation in result.violations)
    assert any("chunk_count" in violation for violation in result.violations)


def test_governed_summary_facts_guards_reject_non_ready_model_context() -> None:
    payload = {
        "payload_type": EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_PAYLOAD_TYPE,
        "payload_version": EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_VERSION,
        "status": "blocked",
        "evidence_ref": EVIDENCE_REF,
        "allowed_for_model_context": True,
        "blocking_reasons": ["not public"],
        "facts": [],
        "fact_count": 0,
        "total_fact_chars": 0,
    }

    result = validate_external_readonly_governed_summary_facts_guards(payload)

    assert result.passed is False
    assert any("model context" in violation for violation in result.violations)


def _ready_payload() -> dict:
    payload = {
        "payload_type": EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_PAYLOAD_TYPE,
        "payload_version": EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_VERSION,
        "status": "ready",
        "evidence_ref": EVIDENCE_REF,
        "source_url_host": "example.test",
        "source_url_scheme": "https",
        "reference_review_ready": True,
        "allowed_for_model_context": True,
        "evidence_written": True,
        "facts": [
            {
                "fact_ref": (
                    f"{EXTERNAL_READONLY_GOVERNED_SUMMARY_FACT_REF_PREFIX}run-001/1"
                ),
                "fact_text": FACT_TEXT,
                "fact_index": 1,
                "evidence_ref": EVIDENCE_REF,
            }
        ],
        "fact_count": 1,
        "total_fact_chars": len(FACT_TEXT),
        "raw_boundary_flags": {},
        "facts_budget": 4000,
        "metadata": {"candidate_only": True},
    }
    return deepcopy(payload)


def _chunk_metadata() -> dict:
    return {
        "source_evidence_ref": EVIDENCE_REF,
        "source_item_index": 1,
        "chunk_index": 1,
        "chunk_count": 2,
        "source_char_start": 0,
        "source_char_end": len(FACT_TEXT),
        "source_excerpt_chars": len(FACT_TEXT) + 25,
        "chunking_strategy_ref": "policy://external-readonly/chunking/fact-slice-v1",
    }
