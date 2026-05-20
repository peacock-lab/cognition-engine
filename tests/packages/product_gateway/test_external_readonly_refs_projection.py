from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from contract_core.external_readonly_evidence import (
    build_external_readonly_evidence_readonly_facts,
    build_external_readonly_evidence_readonly_public_refs,
    external_readonly_evidence_readonly_public_refs_status_dict,
)
from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayResponse,
    ProductGatewayStatus,
)
from product_gateway.external_readonly_refs_projection import (
    EXTERNAL_READONLY_EVIDENCE_OBSERVATION_REF_KIND,
    EXTERNAL_READONLY_EVIDENCE_REF_KIND,
    EXTERNAL_READONLY_READONLY_PUBLIC_REFS_PURPOSE,
    EXTERNAL_READONLY_REFS_PROJECTION_SOURCE,
    project_external_readonly_readonly_public_refs_to_product_gateway_output_refs,
)
from product_gateway.response_summary_projection import (
    project_product_gateway_response_summary,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
PRODUCT_GATEWAY_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "product_gateway" / "src" / "product_gateway"
)


def test_projects_contract_object_to_product_gateway_output_refs() -> None:
    output_refs = (
        project_external_readonly_readonly_public_refs_to_product_gateway_output_refs(
            _public_refs_contract()
        )
    )

    assert [ref.ref for ref in output_refs.evidence_refs] == [
        "evidence://external-readonly/cli-fetch/one.json",
        "evidence://external-readonly/cli-fetch/two.json",
    ]
    assert [ref.kind for ref in output_refs.evidence_refs] == [
        EXTERNAL_READONLY_EVIDENCE_REF_KIND,
        EXTERNAL_READONLY_EVIDENCE_REF_KIND,
    ]
    assert [ref.ref for ref in output_refs.additional_refs] == [
        "external-readonly-evidence-observation://observation-1",
        "external-readonly-evidence-observation://observation-2",
    ]
    assert [ref.kind for ref in output_refs.additional_refs] == [
        EXTERNAL_READONLY_EVIDENCE_OBSERVATION_REF_KIND,
        EXTERNAL_READONLY_EVIDENCE_OBSERVATION_REF_KIND,
    ]
    assert all(
        ref.purpose == EXTERNAL_READONLY_READONLY_PUBLIC_REFS_PURPOSE
        for ref in [*output_refs.evidence_refs, *output_refs.additional_refs]
    )
    metadata = output_refs.evidence_refs[0].metadata
    assert metadata == {
        "source": EXTERNAL_READONLY_REFS_PROJECTION_SOURCE,
        "payload_type": "external_readonly_evidence_readonly_public_refs",
        "payload_version": "external_readonly_evidence_readonly_public_refs_v1",
        "status": "ready",
        "candidate_count": 2,
        "reference_review_ready": True,
        "allowed_for_model_context": True,
        "readonly": True,
        "refs_only": True,
        "candidate_only": True,
        "blocking_reason_count": 0,
        "warning_count": 1,
        "raw_response_included": False,
        "raw_html_included": False,
        "response_headers_included": False,
    }


def test_projects_status_dict_and_deduplicates_refs() -> None:
    status = external_readonly_evidence_readonly_public_refs_status_dict(
        _public_refs_contract()
    )
    status["external_readonly_evidence_refs"].append(
        "evidence://external-readonly/cli-fetch/one.json"
    )
    status["external_readonly_evidence_observation_refs"].append(
        "external-readonly-evidence-observation://observation-1"
    )

    output_refs = (
        project_external_readonly_readonly_public_refs_to_product_gateway_output_refs(
            status
        )
    )

    assert [ref.ref for ref in output_refs.evidence_refs] == [
        "evidence://external-readonly/cli-fetch/one.json",
        "evidence://external-readonly/cli-fetch/two.json",
    ]
    assert [ref.ref for ref in output_refs.additional_refs] == [
        "external-readonly-evidence-observation://observation-1",
        "external-readonly-evidence-observation://observation-2",
    ]


def test_projection_does_not_leak_raw_payload_or_config_context_values() -> None:
    status = external_readonly_evidence_readonly_public_refs_status_dict(
        _public_refs_contract()
    )
    serialized_input = json.dumps(status, ensure_ascii=False, sort_keys=True)

    output_refs = (
        project_external_readonly_readonly_public_refs_to_product_gateway_output_refs(
            status
        )
    )
    serialized_output = json.dumps(
        output_refs.model_dump(mode="python"),
        ensure_ascii=False,
        sort_keys=True,
    )

    assert "config_context_token_value" not in serialized_input
    assert "authorization-secret-value" not in serialized_input
    assert "raw-response-secret-value" not in serialized_input
    assert "sanitized_excerpt_preview" not in serialized_output
    assert "content_hash" not in serialized_output
    assert "source_urls" not in serialized_output
    assert "observation_candidate_ids" not in serialized_output
    assert "evidence_output_paths" not in serialized_output
    assert "metadata_keys" not in serialized_output
    assert "config_context_token_value" not in serialized_output
    assert "authorization-secret-value" not in serialized_output
    assert "raw-response-secret-value" not in serialized_output


def test_projection_rejects_bad_refs_and_raw_payload_keys() -> None:
    bad_evidence_ref = external_readonly_evidence_readonly_public_refs_status_dict(
        _public_refs_contract()
    )
    bad_evidence_ref["external_readonly_evidence_refs"] = ["file://leak.json"]

    with pytest.raises(ValueError, match="external_readonly_evidence_refs"):
        project_external_readonly_readonly_public_refs_to_product_gateway_output_refs(
            bad_evidence_ref
        )

    bad_observation_ref = external_readonly_evidence_readonly_public_refs_status_dict(
        _public_refs_contract()
    )
    bad_observation_ref["external_readonly_evidence_observation_refs"] = [
        "evidence://external-readonly/not-observation"
    ]

    with pytest.raises(
        ValueError,
        match="external_readonly_evidence_observation_refs",
    ):
        project_external_readonly_readonly_public_refs_to_product_gateway_output_refs(
            bad_observation_ref
        )

    raw_payload = external_readonly_evidence_readonly_public_refs_status_dict(
        _public_refs_contract()
    )
    raw_payload["external_readonly_evidence_readonly_facts"][
        "sanitized_excerpt_preview"
    ] = "raw-response-secret-value"

    with pytest.raises(ValueError, match="sanitized_excerpt_preview"):
        project_external_readonly_readonly_public_refs_to_product_gateway_output_refs(
            raw_payload
        )


def test_projection_rejects_bad_raw_boundary_flag_types() -> None:
    status = external_readonly_evidence_readonly_public_refs_status_dict(
        _public_refs_contract()
    )
    status["external_readonly_evidence_readonly_facts"]["raw_boundary_flags"][
        "raw_response_included"
    ] = "yes"

    with pytest.raises(ValueError, match="raw_response_included"):
        project_external_readonly_readonly_public_refs_to_product_gateway_output_refs(
            status
        )


def test_observation_refs_enter_response_summary_additional_refs() -> None:
    output_refs = (
        project_external_readonly_readonly_public_refs_to_product_gateway_output_refs(
            _public_refs_contract()
        )
    )
    response = ProductGatewayResponse(
        request_id="external-readonly/request-refs",
        entry_kind=ProductGatewayEntryKind.EXTERNAL_READONLY_FETCH,
        status=ProductGatewayStatus.SUCCESS,
        output_refs=output_refs,
        evidence_refs=output_refs.evidence_refs,
        metadata={"source": "product_gateway.external_readonly_refs_projection"},
    )

    summary = project_product_gateway_response_summary(response)
    serialized_summary = json.dumps(summary, ensure_ascii=False, sort_keys=True)

    assert [ref["ref"] for ref in summary["evidence_refs"]] == [
        "evidence://external-readonly/cli-fetch/one.json",
        "evidence://external-readonly/cli-fetch/two.json",
    ]
    assert [ref["ref"] for ref in summary["additional_refs"]] == [
        "external-readonly-evidence-observation://observation-1",
        "external-readonly-evidence-observation://observation-2",
    ]
    assert all(
        ref["kind"] == "external_readonly_evidence_observation"
        for ref in summary["additional_refs"]
    )
    assert "sanitized_excerpt_preview" not in serialized_summary
    assert "content_hash" not in serialized_summary
    assert "source_urls" not in serialized_summary
    assert "evidence_output_paths" not in serialized_summary
    assert "observation_candidate_ids" not in serialized_summary


def test_external_readonly_refs_projection_keeps_product_gateway_boundary() -> None:
    source = (
        PRODUCT_GATEWAY_SOURCE_ROOT / "external_readonly_refs_projection.py"
    ).read_text(encoding="utf-8")
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:behavior_contracts|composition|observability_hub|runtime_container|"
        r"external_readonly|adk_adapter|google\.adk|litellm)\b",
        re.MULTILINE,
    )

    assert forbidden_imports.search(source) is None
    assert "open(" not in source
    assert "read_text(" not in source
    assert "requests" not in source
    assert "httpx" not in source
    assert "run_external_readonly" not in source


def _public_refs_contract():
    facts = build_external_readonly_evidence_readonly_facts(
        observation_candidate_ids=("observation-1", "observation-2"),
        evidence_output_paths=(
            "outputs/external-readonly/cli-fetch/one.json",
            "outputs/external-readonly/cli-fetch/two.json",
        ),
        evidence_refs=(
            "evidence://external-readonly/cli-fetch/one.json",
            "evidence://external-readonly/cli-fetch/two.json",
        ),
        source_urls=(
            "https://example.com/one",
            "https://example.com/two",
        ),
        status="ready",
        reference_review_ready=True,
        allowed_for_model_context=True,
        candidate_count=2,
        warnings=("reference_review_ready",),
        metadata_keys=("config_context", "source"),
        raw_boundary_flags={
            "raw_response_included": False,
            "raw_html_included": False,
            "response_headers_included": False,
        },
        metadata={
            "source": "unit-test",
            "config_context": {"token": "config_context_token_value"},
            "authorization": "authorization-secret-value",
            "raw_response": "raw-response-secret-value",
        },
    )
    return build_external_readonly_evidence_readonly_public_refs(
        external_readonly_evidence_observation_refs=(
            "external-readonly-evidence-observation://observation-1",
            "external-readonly-evidence-observation://observation-2",
        ),
        external_readonly_evidence_refs=(
            "evidence://external-readonly/cli-fetch/one.json",
            "evidence://external-readonly/cli-fetch/two.json",
        ),
        facts=facts,
        metadata={
            "source": "unit-test",
            "config_context": {"token": "config_context_token_value"},
            "authorization": "authorization-secret-value",
        },
    )
