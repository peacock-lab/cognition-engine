from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from schemas import (
    ExternalReadonlyGovernedSummaryFactsSchema as RootExportedFactsSchema,
    validate_external_readonly_governed_summary_facts as root_validate_facts,
)
from schemas.evidence_summary_answer import (
    EXTERNAL_READONLY_EVIDENCE_REF_PREFIX,
    SUMMARY_FACT_ITEM_MAX_CHARS,
    SUMMARY_FACT_MAX_ITEMS,
)
from schemas.external_readonly_governed_summary_facts import (
    EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_PAYLOAD_TYPE,
    EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_VERSION,
    EXTERNAL_READONLY_GOVERNED_SUMMARY_FACT_REF_PREFIX,
    ExternalReadonlyGovernedSummaryFactsSchema,
    validate_external_readonly_governed_summary_facts,
)


EVIDENCE_REF = f"{EXTERNAL_READONLY_EVIDENCE_REF_PREFIX}run-001/fetch-001"
FACT_TEXT = "The source identifies governed evidence summaries as public context."
CONTENT_HASH = "a" * 64


def test_governed_summary_facts_schema_accepts_ready_bundle() -> None:
    payload = _ready_payload()

    model = validate_external_readonly_governed_summary_facts(payload)

    assert isinstance(model, ExternalReadonlyGovernedSummaryFactsSchema)
    assert model.status == "ready"
    assert model.allowed_for_model_context is True
    assert model.fact_count == 1
    assert model.total_fact_chars == len(FACT_TEXT)
    assert root_validate_facts(payload).status == "ready"
    assert RootExportedFactsSchema.model_validate(payload).status == "ready"


def test_governed_summary_facts_schema_accepts_blocked_bundle() -> None:
    model = validate_external_readonly_governed_summary_facts(
        {
            "payload_type": EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_PAYLOAD_TYPE,
            "payload_version": EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_VERSION,
            "status": "blocked",
            "evidence_ref": EVIDENCE_REF,
            "blocking_reasons": ["source boundary was not public"],
        }
    )

    assert model.status == "blocked"
    assert model.allowed_for_model_context is False
    assert model.fact_count == 0


def test_governed_summary_facts_schema_accepts_empty_bundle() -> None:
    model = validate_external_readonly_governed_summary_facts(
        {
            "payload_type": EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_PAYLOAD_TYPE,
            "payload_version": EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_VERSION,
            "status": "empty",
            "evidence_ref": EVIDENCE_REF,
        }
    )

    assert model.status == "empty"
    assert model.facts == []
    assert model.total_fact_chars == 0


@pytest.mark.parametrize(
    "mutate",
    (
        lambda payload: payload.update({"payload_type": "wrong"}),
        lambda payload: payload["facts"][0].update({"fact_ref": "bad-ref"}),
        lambda payload: payload.update({"evidence_ref": "bad-ref"}),
        lambda payload: payload.update({"source_url_host": "https://example.test/a"}),
        lambda payload: payload.update({"fact_count": 2}),
        lambda payload: payload.update({"total_fact_chars": 1}),
        lambda payload: payload["facts"][0].update({"fact_text": " "}),
        lambda payload: payload["facts"][0].update(
            {"fact_text": "x" * (SUMMARY_FACT_ITEM_MAX_CHARS + 1)}
        ),
        lambda payload: payload["facts"][0].update(
            {"fact_text": "raw payload should never cross this boundary"}
        ),
        lambda payload: payload.update(
            {"metadata": {"sanitized_excerpt_preview": "must stay private"}}
        ),
        lambda payload: payload.update(
            {"metadata": {"sanitized_excerpt": "must stay internal"}}
        ),
        lambda payload: payload.update(
            {"metadata": {"authorization": "Bearer must-not-cross"}}
        ),
        lambda payload: payload.update(
            {"raw_boundary_flags": {"sanitized_excerpt_preview_included": True}}
        ),
        lambda payload: payload.update({"content_hash": "not-a-sha256"}),
    ),
)
def test_governed_summary_facts_schema_rejects_invalid_payloads(mutate) -> None:
    payload = _ready_payload()
    mutate(payload)

    with pytest.raises(ValidationError):
        validate_external_readonly_governed_summary_facts(payload)


def test_governed_summary_facts_schema_rejects_too_many_facts() -> None:
    payload = _ready_payload()
    facts = []
    for index in range(1, SUMMARY_FACT_MAX_ITEMS + 2):
        text = f"Fact {index}"
        facts.append(
            {
                "fact_ref": (
                    f"{EXTERNAL_READONLY_GOVERNED_SUMMARY_FACT_REF_PREFIX}{index}"
                ),
                "fact_text": text,
                "fact_index": index,
                "evidence_ref": EVIDENCE_REF,
            }
        )
    payload["facts"] = facts
    payload["fact_count"] = len(facts)
    payload["total_fact_chars"] = sum(len(fact["fact_text"]) for fact in facts)

    with pytest.raises(ValidationError):
        validate_external_readonly_governed_summary_facts(payload)


def test_governed_summary_facts_schema_rejects_sanitized_excerpt_marker() -> None:
    payload = _ready_payload()
    fact_text = "sanitized_excerpt must stay internal to external_readonly"
    payload["facts"][0]["fact_text"] = fact_text
    payload["total_fact_chars"] = len(fact_text)

    with pytest.raises(ValidationError):
        validate_external_readonly_governed_summary_facts(payload)


def test_governed_summary_facts_schema_allows_public_package_names() -> None:
    payload = _ready_payload()
    fact_text = (
        "The public packages include contract_core, schemas, "
        "behavior_contracts, config_assembly, and config_contexts."
    )
    payload["facts"][0]["fact_text"] = fact_text
    payload["total_fact_chars"] = len(fact_text)

    model = validate_external_readonly_governed_summary_facts(payload)

    assert model.status == "ready"


def test_governed_summary_facts_schema_rejects_config_context_marker() -> None:
    payload = _ready_payload()
    fact_text = "The config_context value must stay inside the runtime boundary."
    payload["facts"][0]["fact_text"] = fact_text
    payload["total_fact_chars"] = len(fact_text)

    with pytest.raises(ValidationError):
        validate_external_readonly_governed_summary_facts(payload)


def test_governed_summary_facts_schema_rejects_empty_model_context() -> None:
    payload = _ready_payload()
    payload["facts"] = []
    payload["fact_count"] = 0
    payload["total_fact_chars"] = 0

    with pytest.raises(ValidationError):
        validate_external_readonly_governed_summary_facts(payload)


def _ready_payload() -> dict:
    payload = {
        "payload_type": EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_PAYLOAD_TYPE,
        "payload_version": EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_VERSION,
        "status": "ready",
        "evidence_ref": EVIDENCE_REF,
        "evidence_output_path": ".cognition-runs/run-001/external-readonly.json",
        "source_url_host": "example.test",
        "source_url_scheme": "https",
        "reference_review_ready": True,
        "allowed_for_model_context": True,
        "evidence_written": True,
        "content_hash": CONTENT_HASH,
        "facts": [
            {
                "fact_ref": (
                    f"{EXTERNAL_READONLY_GOVERNED_SUMMARY_FACT_REF_PREFIX}run-001/1"
                ),
                "fact_text": FACT_TEXT,
                "fact_index": 1,
                "evidence_ref": EVIDENCE_REF,
                "source_url_host": "example.test",
                "content_hash": CONTENT_HASH,
            }
        ],
        "fact_count": 1,
        "total_fact_chars": len(FACT_TEXT),
        "raw_boundary_flags": {},
        "generation_policy_ref": "policy://external-readonly/governed-summary-facts",
        "facts_budget": 4000,
        "metadata": {"candidate_only": True},
    }
    return deepcopy(payload)
