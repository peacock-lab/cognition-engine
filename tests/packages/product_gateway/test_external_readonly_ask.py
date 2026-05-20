from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayExecutionMode,
    ProductGatewayStatus,
)
from product_gateway.external_readonly_ask import (
    EXTERNAL_READONLY_ASK_BLOCKED_REASON,
    EXTERNAL_READONLY_ASK_INSUFFICIENT_EVIDENCE_REASON,
    EXTERNAL_READONLY_ASK_RESPONSE_SOURCE,
    build_external_readonly_ask_gateway_request,
    execute_external_readonly_ask_gateway_request,
    run_external_readonly_ask_gateway_request,
)
from schemas.product_gateway_response_summary import (
    validate_product_gateway_response_summary,
)


PRODUCT_GATEWAY_ROOT = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "product_gateway"
    / "src"
    / "product_gateway"
)


def test_external_readonly_ask_entry_projects_public_summary() -> None:
    gateway_input = _gateway_input(answer_status="success", llm_call_attempted=True)

    request = build_external_readonly_ask_gateway_request(gateway_input)
    response = run_external_readonly_ask_gateway_request(gateway_input)
    execution = execute_external_readonly_ask_gateway_request(gateway_input)

    assert request.entry_kind is ProductGatewayEntryKind.EXTERNAL_READONLY_ASK
    assert request.execution_mode is ProductGatewayExecutionMode.CONTROLLED_LIVE
    assert request.live_options.request_live_llm is True
    assert request.live_options.override_source == EXTERNAL_READONLY_ASK_RESPONSE_SOURCE
    assert response.status is ProductGatewayStatus.SUCCESS
    assert response.exit_code == 0
    assert response.metadata["source"] == EXTERNAL_READONLY_ASK_RESPONSE_SOURCE
    assert response.metadata["llm_call_attempted"] is True
    assert response.evidence_refs[0].purpose == "answer_context"
    assert response.output_refs.additional_refs[0].kind == "governed_evidence_digest"

    summary = execution.product_response_summary
    validated = validate_product_gateway_response_summary(summary)
    assert validated.model_dump(mode="python") == summary
    assert summary["entry_kind"] == "external_readonly_ask"
    assert summary["status"] == "success"
    assert summary["refs_only"] is True
    assert summary["llm_call_enabled"] is False
    assert summary["evidence_refs"][0]["ref"] == (
        "evidence://external-readonly/item/ask"
    )
    assert "answer body" not in repr(summary)


def test_external_readonly_ask_blocks_with_default_reason() -> None:
    response = run_external_readonly_ask_gateway_request(
        _gateway_input(answer_status="blocked", evidence_refs=())
    )

    assert response.status is ProductGatewayStatus.BLOCKED
    assert response.exit_code == 2
    assert response.blocking_reasons == [EXTERNAL_READONLY_ASK_BLOCKED_REASON]


def test_external_readonly_ask_insufficient_evidence_reason_is_explicit() -> None:
    response = run_external_readonly_ask_gateway_request(
        _gateway_input(answer_status="insufficient_evidence", evidence_refs=())
    )

    assert response.status is ProductGatewayStatus.BLOCKED
    assert response.blocking_reasons == [
        EXTERNAL_READONLY_ASK_INSUFFICIENT_EVIDENCE_REASON
    ]


@pytest.mark.parametrize(
    "raw_payload",
    [
        {"metadata": {"answer": "answer body must stay outside gateway summary"}},
        {"metadata": {"raw_provider_response": {"content": "raw"}}},
        {
            "evidence_refs": [
                {
                    "ref": "evidence://external-readonly/item/raw",
                    "kind": "external_readonly_evidence",
                    "metadata": {"prompt": "raw prompt"},
                }
            ],
        },
        {"metadata": {"object_module": "google.adk.runners"}},
    ],
)
def test_external_readonly_ask_rejects_raw_payloads(
    raw_payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        build_external_readonly_ask_gateway_request(_gateway_input(**raw_payload))


def test_external_readonly_ask_keeps_product_gateway_boundary() -> None:
    source = (PRODUCT_GATEWAY_ROOT / "external_readonly_ask.py").read_text(
        encoding="utf-8"
    )

    assert "from product_gateway.response_summary_projection import" in source
    assert "from runtime_container" not in source
    assert "cognition_task_workflows" not in source
    assert "product_application_assembly" not in source
    assert "from google.adk" not in source
    assert "import google.adk" not in source
    assert "from litellm" not in source
    assert "import litellm" not in source
    assert "from adk_adapter" not in source
    assert "import adk_adapter" not in source


def _gateway_input(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "request_id": "external-readonly-ask-request://unit",
        "answer_status": "success",
        "evidence_refs": [
            {
                "ref": "evidence://external-readonly/item/ask",
                "kind": "external_readonly_evidence",
                "purpose": "answer_context",
            }
        ],
        "additional_refs": [
            {
                "ref": "governed-evidence-digest://external-readonly-ask",
                "kind": "governed_evidence_digest",
                "purpose": "digest_context",
            }
        ],
        "blocking_reasons": [],
        "warnings": [],
        "readonly_refs_status": "ready",
        "source_url_present": False,
        "evidence_path_count": 1,
        "model_name": "ollama/gemma4-pro:latest",
        "llm_call_allowed": True,
        "llm_call_attempted": True,
        "llm_runtime_call_performed": True,
        "external_readonly_fetch_performed": False,
        "external_readonly_network_call_performed": False,
        "external_network_call_performed": False,
        "metadata": {"unit_test": True},
    }
    kwargs.update(overrides)
    return kwargs
