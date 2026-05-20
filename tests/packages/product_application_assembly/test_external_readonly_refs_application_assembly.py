from __future__ import annotations

import json

from contract_core.external_readonly_evidence import (
    ExternalReadonlyEvidenceReadContext,
    ExternalReadonlyEvidenceSummary,
    external_readonly_evidence_read_context_status_dict,
)
from product_application_assembly import (
    ExternalReadonlyRefsProductApplicationAssemblyResult,
    assemble_external_readonly_refs_product_application,
)
from product_application_assembly.external_readonly_refs import (
    PRODUCT_APPLICATION_EXTERNAL_READONLY_REFS_SOURCE,
)


def test_assembles_external_readonly_refs_from_read_context_dataclass() -> None:
    result = assemble_external_readonly_refs_product_application(
        ExternalReadonlyEvidenceReadContext(
            status="ready",
            reference_review_ready=True,
            summaries=(_ready_summary(),),
            evidence_output_paths=(_EVIDENCE_OUTPUT_PATH,),
            evidence_refs=(_EVIDENCE_REF,),
            source_urls=("https://example.com/reference",),
        ),
        request_id="product-application/external-readonly/ready",
        metadata={
            "surface": "unit-test",
            "config_context": {"token": "config-secret-value"},
            "raw_payload": "raw-response-secret-value",
        },
    )

    assert isinstance(result, ExternalReadonlyRefsProductApplicationAssemblyResult)
    assert result.request_id == "product-application/external-readonly/ready"
    assert result.application_metadata["source"] == (
        PRODUCT_APPLICATION_EXTERNAL_READONLY_REFS_SOURCE
    )
    assert result.application_metadata["surface"] == "unit-test"
    assert "config_context" not in result.application_metadata
    assert "raw_payload" not in result.application_metadata

    summary = result.product_response_summary
    assert summary["entry_kind"] == "external_readonly_refs"
    assert summary["status"] == "success"
    assert [ref["ref"] for ref in summary["evidence_refs"]] == [_EVIDENCE_REF]
    assert summary["additional_refs"][0]["ref"].startswith(
        "external-readonly-evidence-observation://"
    )
    assert summary["additional_refs"][0]["kind"] == (
        "external_readonly_evidence_observation"
    )
    assert summary["metadata"]["source"] == (
        "product_gateway" + "." + "response_summary_projection"
    )

    serialized = json.dumps(
        {
            "summary": summary,
            "readonly_public_refs_status": result.readonly_public_refs_status,
            "application_metadata": result.application_metadata,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    assert "sanitized_excerpt_preview" not in serialized
    assert "config-secret-value" not in serialized
    assert "raw-response-secret-value" not in serialized


def test_assembles_external_readonly_refs_from_status_dict() -> None:
    context = ExternalReadonlyEvidenceReadContext(
        status="ready",
        reference_review_ready=True,
        summaries=(_ready_summary(),),
    )

    result = assemble_external_readonly_refs_product_application(
        external_readonly_evidence_read_context_status_dict(context),
        request_id="product-application/external-readonly/status-dict",
    )

    facts = result.readonly_public_refs_status[
        "external_readonly_evidence_readonly_facts"
    ]
    assert facts["status"] == "ready"
    assert result.product_response_summary["status"] == "success"
    assert [ref["ref"] for ref in result.product_response_summary["evidence_refs"]] == [
        _EVIDENCE_REF
    ]


def test_blocked_and_empty_states_follow_product_gateway_summary_semantics() -> None:
    blocked = assemble_external_readonly_refs_product_application(
        ExternalReadonlyEvidenceReadContext(
            status="blocked",
            reference_review_ready=False,
            summaries=(_blocked_summary(),),
        ),
        request_id="product-application/external-readonly/blocked",
    )
    empty = assemble_external_readonly_refs_product_application(
        ExternalReadonlyEvidenceReadContext(
            status="empty",
            reference_review_ready=False,
        ),
        request_id="product-application/external-readonly/empty",
    )

    assert blocked.product_response_summary["status"] == "blocked"
    assert blocked.product_response_summary["exit_code"] == 2
    assert blocked.product_response_summary["blocking_reasons"] == [
        "evidence_file_missing"
    ]
    assert blocked.product_response_summary["evidence_refs"] == []
    assert blocked.product_response_summary["additional_refs"][0]["kind"] == (
        "external_readonly_evidence_observation"
    )
    assert empty.product_response_summary["status"] == "skipped"
    assert empty.product_response_summary["exit_code"] == 0
    assert empty.product_response_summary["evidence_refs"] == []
    assert empty.product_response_summary["additional_refs"] == []
    assert empty.product_response_summary["warnings"] == [
        "external_readonly_readonly_public_refs_empty"
    ]


_EVIDENCE_OUTPUT_PATH = "outputs/external-readonly/cli-fetch/example.json"
_EVIDENCE_REF = "evidence://external-readonly/cli-fetch/example.json"


def _ready_summary() -> ExternalReadonlyEvidenceSummary:
    return ExternalReadonlyEvidenceSummary(
        evidence_output_path=_EVIDENCE_OUTPUT_PATH,
        status="ready",
        reference_review_ready=True,
        evidence_ref=_EVIDENCE_REF,
        source_url="https://example.com/reference",
        allowed_for_model_context=True,
        evidence_written=True,
        runtime_fetch_performed=True,
        transport_called=True,
        external_network_call_performed=True,
        total_excerpt_chars=64,
        warnings=("reference_review_ready",),
        metadata={"source": "unit-test"},
    )


def _blocked_summary() -> ExternalReadonlyEvidenceSummary:
    return ExternalReadonlyEvidenceSummary(
        evidence_output_path=_EVIDENCE_OUTPUT_PATH,
        status="blocked",
        reference_review_ready=False,
        evidence_ref=None,
        allowed_for_model_context=False,
        blocking_reasons=("evidence_file_missing",),
        metadata={"source": "unit-test"},
    )
