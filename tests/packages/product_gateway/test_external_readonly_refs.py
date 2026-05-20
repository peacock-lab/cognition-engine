from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from contract_core.external_readonly_evidence import (
    build_external_readonly_evidence_readonly_facts,
    build_external_readonly_evidence_readonly_public_refs,
    external_readonly_evidence_readonly_public_refs_status_dict,
)
from product_gateway.contracts import ProductGatewayEntryKind, ProductGatewayStatus
from product_gateway.external_readonly_refs import (
    EXTERNAL_READONLY_REFS_BLOCKED_REASON,
    EXTERNAL_READONLY_REFS_EMPTY_WARNING,
    EXTERNAL_READONLY_REFS_PURPOSE,
    EXTERNAL_READONLY_REFS_RESPONSE_SOURCE,
    ExternalReadonlyRefsGatewayExecutionResult,
    ExternalReadonlyRefsGatewayInput,
    build_external_readonly_refs_gateway_projection,
    build_external_readonly_refs_gateway_request,
    execute_external_readonly_refs_gateway_request,
    run_external_readonly_refs_gateway_request,
)
from product_gateway.response_summary_projection import (
    project_product_gateway_response_summary,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
PRODUCT_GATEWAY_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "product_gateway" / "src" / "product_gateway"
)


def test_external_readonly_refs_entry_returns_success_response() -> None:
    public_refs = _public_refs_contract()
    gateway_input = ExternalReadonlyRefsGatewayInput(
        request_id="external-readonly/refs-1",
        readonly_public_refs=public_refs,
        governance_summary_ref="governance-summary://external-readonly/refs-1",
        metadata={"owner": "unit-test"},
    )

    request = build_external_readonly_refs_gateway_request(gateway_input)
    projection = build_external_readonly_refs_gateway_projection(gateway_input)
    response = run_external_readonly_refs_gateway_request(gateway_input)

    assert request.entry_kind is ProductGatewayEntryKind.EXTERNAL_READONLY_REFS
    assert request.input_payload["readonly_refs_status"] == "ready"
    assert request.input_payload["external_readonly_evidence_ref_count"] == 2
    assert projection.entry_kind == "external_readonly_refs"
    assert projection.observation_ref_count == 2
    assert response.entry_kind is ProductGatewayEntryKind.EXTERNAL_READONLY_REFS
    assert response.status is ProductGatewayStatus.SUCCESS
    assert response.exit_code == 0
    assert response.governance_summary_ref == (
        "governance-summary://external-readonly/refs-1"
    )
    assert [ref.ref for ref in response.output_refs.evidence_refs] == [
        "evidence://external-readonly/cli-fetch/one.json",
        "evidence://external-readonly/cli-fetch/two.json",
    ]
    assert response.evidence_refs == response.output_refs.evidence_refs
    assert [ref.ref for ref in response.output_refs.additional_refs] == [
        "external-readonly-evidence-observation://observation-1",
        "external-readonly-evidence-observation://observation-2",
    ]
    assert all(
        ref.purpose == EXTERNAL_READONLY_REFS_PURPOSE
        for ref in response.output_refs.additional_refs
    )
    assert response.metadata["source"] == EXTERNAL_READONLY_REFS_RESPONSE_SOURCE
    assert response.metadata["readonly_refs_status"] == "ready"
    assert response.metadata["candidate_count"] == 2


def test_external_readonly_refs_entry_accepts_status_dict() -> None:
    status = external_readonly_evidence_readonly_public_refs_status_dict(
        _public_refs_contract()
    )

    response = run_external_readonly_refs_gateway_request(
        {
            "request_id": "external-readonly/refs-status-dict",
            "readonly_public_refs": status,
        }
    )

    assert response.status is ProductGatewayStatus.SUCCESS
    assert [ref.ref for ref in response.evidence_refs] == [
        "evidence://external-readonly/cli-fetch/one.json",
        "evidence://external-readonly/cli-fetch/two.json",
    ]


def test_external_readonly_refs_summary_projects_additional_refs() -> None:
    response = run_external_readonly_refs_gateway_request(
        {
            "request_id": "external-readonly/refs-summary",
            "readonly_public_refs": _public_refs_contract(),
        }
    )

    summary = project_product_gateway_response_summary(response)
    serialized_summary = json.dumps(summary, ensure_ascii=False, sort_keys=True)

    assert summary["entry_kind"] == "external_readonly_refs"
    assert [ref["ref"] for ref in summary["evidence_refs"]] == [
        "evidence://external-readonly/cli-fetch/one.json",
        "evidence://external-readonly/cli-fetch/two.json",
    ]
    assert [ref["ref"] for ref in summary["additional_refs"]] == [
        "external-readonly-evidence-observation://observation-1",
        "external-readonly-evidence-observation://observation-2",
    ]
    assert [ref["kind"] for ref in summary["additional_refs"]] == [
        "external_readonly_evidence_observation",
        "external_readonly_evidence_observation",
    ]
    assert all(
        ref["purpose"] == EXTERNAL_READONLY_REFS_PURPOSE
        for ref in summary["additional_refs"]
    )
    assert summary["readonly"] is True
    assert summary["summary_only"] is True
    assert summary["refs_only"] is True
    assert summary["candidate_only"] is True
    assert "sanitized_excerpt_preview" not in serialized_summary
    assert "content_hash" not in serialized_summary
    assert "source_urls" not in serialized_summary
    assert "evidence_output_paths" not in serialized_summary
    assert "observation_candidate_ids" not in serialized_summary


def test_external_readonly_refs_execute_returns_summary_only_result() -> None:
    result = execute_external_readonly_refs_gateway_request(
        {
            "request_id": "external-readonly/refs-execute",
            "readonly_public_refs": _public_refs_contract(),
        }
    )

    summary = result.product_response_summary
    serialized_summary = json.dumps(summary, ensure_ascii=False, sort_keys=True)

    assert isinstance(result, ExternalReadonlyRefsGatewayExecutionResult)
    assert not hasattr(result, "product_response")
    assert summary["entry_kind"] == "external_readonly_refs"
    assert summary["metadata"]["source"] == (
        "product_gateway.response_summary_projection"
    )
    assert [ref["ref"] for ref in summary["additional_refs"]] == [
        "external-readonly-evidence-observation://observation-1",
        "external-readonly-evidence-observation://observation-2",
    ]
    assert "sanitized_excerpt_preview" not in serialized_summary
    assert "raw-response-secret-value" not in serialized_summary


def test_external_readonly_refs_mixed_status_stays_success() -> None:
    response = run_external_readonly_refs_gateway_request(
        {
            "request_id": "external-readonly/refs-mixed",
            "readonly_public_refs": _public_refs_contract(
                status="mixed",
                evidence_refs=("evidence://external-readonly/cli-fetch/one.json",),
                observation_refs=(
                    "external-readonly-evidence-observation://observation-1",
                ),
                candidate_count=2,
                blocking_reasons=("evidence_file_missing",),
                warnings=("partial_readonly_refs",),
            ),
        }
    )

    assert response.status is ProductGatewayStatus.SUCCESS
    assert response.exit_code == 0
    assert response.blocking_reasons == []
    assert response.warnings == ["partial_readonly_refs"]
    assert response.metadata["blocking_reason_count"] == 1
    assert response.metadata["warning_count"] == 1


def test_external_readonly_refs_blocked_status_has_blocking_reasons() -> None:
    response = run_external_readonly_refs_gateway_request(
        {
            "request_id": "external-readonly/refs-blocked",
            "readonly_public_refs": _public_refs_contract(
                status="blocked",
                evidence_refs=(),
                observation_refs=(),
                candidate_count=1,
                blocking_reasons=(),
                warnings=(),
            ),
        }
    )

    assert response.status is ProductGatewayStatus.BLOCKED
    assert response.exit_code == 2
    assert response.blocking_reasons == [EXTERNAL_READONLY_REFS_BLOCKED_REASON]
    assert response.output_refs.evidence_refs == []
    assert response.output_refs.additional_refs == []


def test_external_readonly_refs_empty_status_is_skipped() -> None:
    response = run_external_readonly_refs_gateway_request(
        {
            "request_id": "external-readonly/refs-empty",
            "readonly_public_refs": _public_refs_contract(
                status="empty",
                evidence_refs=(),
                observation_refs=(),
                candidate_count=0,
                blocking_reasons=(),
                warnings=(),
            ),
        }
    )

    assert response.status is ProductGatewayStatus.SKIPPED
    assert response.exit_code == 0
    assert response.warnings == [EXTERNAL_READONLY_REFS_EMPTY_WARNING]
    assert response.output_refs.evidence_refs == []
    assert response.output_refs.additional_refs == []


def test_external_readonly_refs_entry_rejects_raw_and_config_values() -> None:
    status = external_readonly_evidence_readonly_public_refs_status_dict(
        _public_refs_contract()
    )
    status["external_readonly_evidence_readonly_facts"][
        "raw_response"
    ] = "raw-response-secret-value"

    with pytest.raises(ValueError, match="raw_response"):
        run_external_readonly_refs_gateway_request(
            {
                "request_id": "external-readonly/refs-raw",
                "readonly_public_refs": status,
            }
        )

    with pytest.raises(ValidationError, match="config_context"):
        ExternalReadonlyRefsGatewayInput(
            request_id="external-readonly/refs-config",
            readonly_public_refs=_public_refs_contract(),
            metadata={"config_context": {"token": "config-secret-value"}},
        )


def test_external_readonly_refs_entry_does_not_leak_source_payloads() -> None:
    response = run_external_readonly_refs_gateway_request(
        {
            "request_id": "external-readonly/refs-no-leak",
            "readonly_public_refs": _public_refs_contract(),
        }
    )
    serialized = json.dumps(response.model_dump(mode="python"), sort_keys=True)

    assert "sanitized_excerpt_preview" not in serialized
    assert "content_hash" not in serialized
    assert "source_urls" not in serialized
    assert "observation_candidate_ids" not in serialized
    assert "evidence_output_paths" not in serialized
    assert "config-secret-value" not in serialized
    assert "raw-response-secret-value" not in serialized


def test_external_readonly_refs_entry_keeps_product_gateway_boundary() -> None:
    source = (PRODUCT_GATEWAY_SOURCE_ROOT / "external_readonly_refs.py").read_text(
        encoding="utf-8"
    )
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
    assert "run_external_readonly_url_fetch" not in source


def test_external_readonly_refs_public_surface_exposes_execute_helper() -> None:
    from product_gateway.external_readonly_refs import __all__ as exported_names

    assert "ExternalReadonlyRefsGatewayExecutionResult" in exported_names
    assert "execute_external_readonly_refs_gateway_request" in exported_names


def _public_refs_contract(
    *,
    status: str = "ready",
    evidence_refs: tuple[str, ...] = (
        "evidence://external-readonly/cli-fetch/one.json",
        "evidence://external-readonly/cli-fetch/two.json",
    ),
    observation_refs: tuple[str, ...] = (
        "external-readonly-evidence-observation://observation-1",
        "external-readonly-evidence-observation://observation-2",
    ),
    candidate_count: int | None = None,
    blocking_reasons: tuple[str, ...] = (),
    warnings: tuple[str, ...] = ("reference_review_ready",),
):
    ready = status == "ready"
    facts = build_external_readonly_evidence_readonly_facts(
        observation_candidate_ids=tuple(
            ref.removeprefix("external-readonly-evidence-observation://")
            for ref in observation_refs
        ),
        evidence_output_paths=tuple(
            f"outputs/external-readonly/cli-fetch/{index}.json"
            for index, _ in enumerate(evidence_refs, start=1)
        ),
        evidence_refs=evidence_refs,
        source_urls=tuple(
            f"https://example.com/{index}"
            for index, _ in enumerate(evidence_refs, start=1)
        ),
        status=status,
        reference_review_ready=ready,
        allowed_for_model_context=ready,
        candidate_count=(
            candidate_count
            if candidate_count is not None
            else len(evidence_refs)
        ),
        blocking_reasons=blocking_reasons,
        warnings=warnings,
        metadata_keys=("source",),
        raw_boundary_flags={
            "raw_response_included": False,
            "raw_html_included": False,
            "response_headers_included": False,
        },
        metadata={"source": "unit-test"},
    )
    return build_external_readonly_evidence_readonly_public_refs(
        external_readonly_evidence_observation_refs=observation_refs,
        external_readonly_evidence_refs=evidence_refs,
        facts=facts,
        metadata={"source": "unit-test"},
    )
