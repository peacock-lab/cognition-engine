from __future__ import annotations

import hashlib
from pathlib import Path

from behavior_contracts.external_readonly_governed_summary_facts import (
    validate_external_readonly_governed_summary_facts_guards,
)
from external_readonly import (
    ExternalReadonlyAdapterProfile,
    ExternalReadonlyAdapterRecord,
    ExternalReadonlyAdapterRequest,
    ExternalReadonlyEvidenceEnvelope,
    ExternalReadonlyNetworkGateView,
    build_external_readonly_governed_summary_facts,
    external_readonly_evidence_envelope_status_dict,
    external_readonly_governed_summary_facts_status_dict,
    project_external_readonly_adapter_records,
)
from schemas.external_readonly_governed_summary_facts import (
    ExternalReadonlyGovernedSummaryFactsSchema,
    validate_external_readonly_governed_summary_facts,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
PRODUCER_SOURCE = (
    REPO_ROOT
    / "packages"
    / "external_readonly"
    / "src"
    / "external_readonly"
    / "governed_summary_facts.py"
)


def test_governed_summary_facts_builder_accepts_dataclass_envelope() -> None:
    facts = build_external_readonly_governed_summary_facts(
        _envelope(),
        evidence_output_path="outputs/external-readonly/evidence.json",
        evidence_written=True,
    )
    status = external_readonly_governed_summary_facts_status_dict(facts)

    assert facts.status == "ready"
    assert facts.fact_count == 1
    assert facts.reference_review_ready is True
    assert facts.evidence_written is True
    assert facts.allowed_for_model_context is True
    assert facts.facts[0].fact_text == "Visible governed source fact."
    assert facts.facts[0].content_hash == _hash("Visible governed source fact.")
    assert validate_external_readonly_governed_summary_facts(status).status == "ready"
    assert validate_external_readonly_governed_summary_facts_guards(status).passed is True
    assert "sanitized_excerpt" not in str(status)
    assert "sanitized_excerpt_preview" not in str(status)
    assert "model_context_items" not in str(status)


def test_governed_summary_facts_builder_accepts_mapping_envelope() -> None:
    mapping = external_readonly_evidence_envelope_status_dict(_envelope())

    facts = build_external_readonly_governed_summary_facts(
        mapping,
        evidence_written=True,
    )

    assert facts.status == "ready"
    assert facts.fact_count == 1
    assert isinstance(facts, ExternalReadonlyGovernedSummaryFactsSchema)


def test_governed_summary_facts_builder_accepts_provider_adapter_multi_item() -> None:
    projection = project_external_readonly_adapter_records(
        gate=_gate(),
        profile=_profile(),
        request=_adapter_request(),
        records=(
            _record(index=1, text="First governed source fact."),
            _record(index=2, text="Second governed source fact."),
        ),
    )

    assert projection.envelope is not None
    facts = build_external_readonly_governed_summary_facts(
        projection.envelope,
        evidence_written=True,
    )
    status = external_readonly_governed_summary_facts_status_dict(facts)

    assert facts.status == "ready"
    assert facts.fact_count == 2
    assert [fact.fact_index for fact in facts.facts] == [1, 2]
    assert len({fact.fact_ref for fact in facts.facts}) == 2
    assert facts.evidence_ref == projection.envelope.envelope_ref
    assert status["source_url_host"] == "example.com"
    assert validate_external_readonly_governed_summary_facts_guards(status).passed is True
    assert "sanitized_excerpt" not in str(status)
    assert "model_context_items" not in str(status)


def test_governed_summary_facts_builder_blocks_until_evidence_is_written() -> None:
    facts = build_external_readonly_governed_summary_facts(_envelope())
    status = external_readonly_governed_summary_facts_status_dict(facts)

    assert facts.status == "blocked"
    assert facts.allowed_for_model_context is False
    assert facts.facts == []
    assert "evidence_not_written" in facts.blocking_reasons
    assert validate_external_readonly_governed_summary_facts_guards(status).passed is True


def test_governed_summary_facts_builder_blocks_non_ready_envelope() -> None:
    facts = build_external_readonly_governed_summary_facts(
        _envelope(status="blocked", allowed_for_model_context=False),
        evidence_written=True,
    )

    assert facts.status == "blocked"
    assert "upstream_envelope_not_valid" in facts.blocking_reasons
    assert "context_not_allowed" in facts.blocking_reasons
    assert facts.facts == []


def test_governed_summary_facts_builder_empty_for_missing_envelope() -> None:
    facts = build_external_readonly_governed_summary_facts(None)

    assert facts.status == "empty"
    assert facts.allowed_for_model_context is False
    assert facts.facts == []
    assert facts.evidence_ref.startswith("evidence://external-readonly/")


def test_governed_summary_facts_builder_blocks_empty_items() -> None:
    facts = build_external_readonly_governed_summary_facts(
        _envelope(model_context_items=()),
        evidence_written=True,
    )

    assert facts.status == "blocked"
    assert facts.facts == []
    assert "context_items_required" in facts.blocking_reasons


def test_governed_summary_facts_builder_blocks_forbidden_fact_marker() -> None:
    facts = build_external_readonly_governed_summary_facts(
        _envelope(
            model_context_items=(
                _item(text="sanitized_excerpt must remain internal."),
            )
        ),
        evidence_written=True,
    )
    status = external_readonly_governed_summary_facts_status_dict(facts)

    assert facts.status == "blocked"
    assert facts.facts == []
    assert "governed_facts_validation_failed" in facts.blocking_reasons
    assert "sanitized_excerpt" not in str(status)
    assert validate_external_readonly_governed_summary_facts_guards(status).passed is True


def test_governed_summary_facts_builder_blocks_bad_source_url() -> None:
    facts = build_external_readonly_governed_summary_facts(
        _envelope(model_context_items=(_item(source_url="http://example.com/a"),)),
        evidence_written=True,
    )

    assert facts.status == "blocked"
    assert "item_1_source_url_not_https" in facts.blocking_reasons


def test_governed_summary_facts_source_has_no_forbidden_dependencies() -> None:
    source = PRODUCER_SOURCE.read_text(encoding="utf-8")

    assert "behavior_contracts" not in source
    assert "contract_core" not in source
    assert "product_gateway" not in source
    assert "composition" not in source
    assert "product_application_assembly" not in source
    assert "observability_hub" not in source
    assert "cognition_cli" not in source
    assert "runtime_container" not in source
    assert "google.adk" not in source
    assert "litellm" not in source
    assert "adk_adapter" not in source


def _envelope(**overrides: object) -> ExternalReadonlyEvidenceEnvelope:
    item = _item()
    kwargs = {
        "envelope_ref": "evidence://external-readonly/envelope/facts-597",
        "request_ref": "external-readonly-request://url-context/597",
        "status": "valid",
        "allowed_for_model_context": True,
        "model_context_items": (item,),
        "evidence_refs": (item["evidence_ref"],),
        "source_urls": (item["source_url"],),
        "total_excerpt_chars": len(item["sanitized_excerpt"]),
    }
    kwargs.update(overrides)
    return ExternalReadonlyEvidenceEnvelope(**kwargs)


def _item(
    *,
    text: str = "Visible governed source fact.",
    source_url: str = "https://example.com/reference",
    evidence_ref: str = "evidence://external-readonly/item/facts-597",
    citation_index: int = 1,
) -> dict[str, object]:
    return {
        "citation_index": citation_index,
        "evidence_ref": evidence_ref,
        "source_url": source_url,
        "source_title": "Example Reference",
        "retrieved_at": "2026-05-16T10:00:00+00:00",
        "item_type": "fetched_excerpt",
        "sanitized_excerpt": text,
        "content_hash": _hash(text),
    }


def _profile() -> ExternalReadonlyAdapterProfile:
    return ExternalReadonlyAdapterProfile(
        adapter_name="generic_search_adapter",
        provider_name="generic_search_provider",
        provider_family="search",
        supported_operations=("search",),
        adapter_ref="adapter://external-readonly/generic-search",
    )


def _adapter_request() -> ExternalReadonlyAdapterRequest:
    return ExternalReadonlyAdapterRequest(
        request_ref="external-readonly-request://adapter/597",
        operation_family="search",
        query_ref="query://external-readonly/governed-topic",
        envelope_ref="evidence://external-readonly/envelope/adapter-597",
        controlled_output_ref="outputs/external-readonly/adapter/597.json",
    )


def _record(*, index: int, text: str) -> ExternalReadonlyAdapterRecord:
    return ExternalReadonlyAdapterRecord(
        source_url=f"https://example.com/reference/{index}",
        retrieved_at="2026-05-16T10:00:00+00:00",
        sanitized_excerpt=text,
        citation_index=index,
        evidence_ref=f"evidence://external-readonly/provider-adapter/597/{index}",
        source_title=f"Example Reference {index}",
    )


def _gate() -> ExternalReadonlyNetworkGateView:
    return ExternalReadonlyNetworkGateView(
        request_ref="external-readonly-request://adapter/597",
        status="passed",
        network_gate_open=True,
        allowed_for_network_request=True,
        operator_approval_satisfied=True,
        controlled_output_satisfied=True,
        tool_origin="generic_search",
        operation_family="search",
        metadata={
            "approval_ref_present": True,
            "network_gate_ref_present": True,
        },
    )


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
