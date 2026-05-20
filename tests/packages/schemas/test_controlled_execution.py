from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas.controlled_execution import (
    CONTROLLED_EXECUTION_REQUEST_VERSION,
    CONTROLLED_EXECUTION_RUNTIME_SUMMARY_VERSION,
    ControlledExecutionRequestSchema,
    ControlledExecutionRuntimeSummarySchema,
    controlled_execution_request_to_mapping,
    controlled_execution_runtime_summary_to_mapping,
    validate_controlled_execution_request,
    validate_controlled_execution_runtime_summary,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_SOURCE_ROOT = REPO_ROOT / "packages" / "schemas" / "src" / "schemas"


def test_controlled_execution_request_accepts_public_shape() -> None:
    request = validate_controlled_execution_request(_request())

    assert isinstance(request, ControlledExecutionRequestSchema)
    assert request.payload_type == "controlled_execution_request"
    assert request.payload_version == CONTROLLED_EXECUTION_REQUEST_VERSION
    assert request.runtime_id == "runtime-1"
    assert request.invocation_id == "request-1"
    assert request.operator_approved is True
    assert request.request_live_llm is True
    assert request.metadata == {"source": "test"}


def test_controlled_execution_request_rejects_config_selection_fields() -> None:
    payload = _request()
    payload["config_root"] = "config/test"
    payload["environment"] = "local"
    payload["profile"] = "dev"

    with pytest.raises(ValidationError):
        validate_controlled_execution_request(payload)


def test_controlled_execution_request_rejects_raw_and_runtime_payloads() -> None:
    raw_payload = _request()
    raw_payload["input_payload"] = {"raw_prompt": "must not cross boundary"}
    with pytest.raises(ValidationError):
        validate_controlled_execution_request(raw_payload)

    runtime_object_payload = _request()
    runtime_object_payload["metadata"] = {
        "object_module": "runtime_container.internal"
    }
    with pytest.raises(ValidationError):
        validate_controlled_execution_request(runtime_object_payload)


def test_controlled_execution_request_to_mapping_preserves_runtime_fields() -> None:
    request = validate_controlled_execution_request(_request())
    mapping = controlled_execution_request_to_mapping(request)

    assert mapping["runtime_id"] == "runtime-1"
    assert mapping["invocation_id"] == "request-1"
    assert mapping["input_payload"] == {"input_summary": "已脱敏输入"}
    assert mapping["operator_approved"] is True
    assert mapping["request_live_llm"] is True
    assert mapping["allow_ollama"] is True
    assert "payload_type" not in mapping
    assert "payload_version" not in mapping
    assert "config_root" not in mapping
    assert "environment" not in mapping
    assert "profile" not in mapping


def test_controlled_execution_runtime_summary_accepts_public_shape() -> None:
    summary = validate_controlled_execution_runtime_summary(_summary())

    assert isinstance(summary, ControlledExecutionRuntimeSummarySchema)
    assert summary.payload_type == "controlled_execution_runtime_summary"
    assert summary.payload_version == CONTROLLED_EXECUTION_RUNTIME_SUMMARY_VERSION
    assert summary.runtime_id == "runtime-1"
    assert summary.status == "success"
    assert summary.sanitized is True
    assert summary.execution_performed is True


@pytest.mark.parametrize("status", ["success", "blocked", "failed", "provider_failed"])
def test_controlled_execution_runtime_summary_accepts_frozen_statuses(
    status: str,
) -> None:
    summary_payload = _summary(status=status)
    if status == "blocked":
        summary_payload["blocking_reasons"] = ("operator_approval_not_true",)

    summary = validate_controlled_execution_runtime_summary(summary_payload)

    assert summary.status == status


def test_controlled_execution_runtime_summary_rejects_blocked_without_reasons() -> None:
    with pytest.raises(ValidationError):
        validate_controlled_execution_runtime_summary(_summary(status="blocked"))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("payload_type", "other"),
        ("payload_version", "other"),
        ("status", "other"),
        ("sanitized", False),
    ],
)
def test_controlled_execution_runtime_summary_rejects_invalid_header_or_flags(
    field: str,
    value: object,
) -> None:
    summary_payload = _summary()
    summary_payload[field] = value

    with pytest.raises(ValidationError):
        validate_controlled_execution_runtime_summary(summary_payload)


def test_controlled_execution_runtime_summary_rejects_raw_payloads() -> None:
    raw_payload = _summary()
    raw_payload["final_preflight"] = {"raw_response": "must not cross boundary"}
    with pytest.raises(ValidationError):
        validate_controlled_execution_runtime_summary(raw_payload)

    runtime_object_payload = _summary()
    runtime_object_payload["lifecycle_facts"] = {
        "object_module": "runtime_container.internal"
    }
    with pytest.raises(ValidationError):
        validate_controlled_execution_runtime_summary(runtime_object_payload)


def test_controlled_execution_runtime_summary_to_mapping_preserves_cli_fields() -> None:
    summary = validate_controlled_execution_runtime_summary(
        _summary(
            sanitized_response_display="脱敏展示",
            sanitized_response_preview="脱敏预览",
        )
    )
    mapping = controlled_execution_runtime_summary_to_mapping(summary)

    assert mapping["runtime_id"] == "runtime-1"
    assert mapping["blocking_reasons"] == []
    assert mapping["warnings"] == ["warn"]
    assert mapping["sanitized_response_display"] == "脱敏展示"
    assert mapping["sanitized_response_preview"] == "脱敏预览"
    assert "payload_type" not in mapping
    assert "payload_version" not in mapping


def test_controlled_execution_runtime_summary_schema_has_no_execution_imports() -> None:
    source = (SCHEMA_SOURCE_ROOT / "controlled_execution.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:product_gateway|runtime_container|composition|adk_adapter|"
        r"google\.adk|litellm)\b",
        re.MULTILINE,
    )

    assert forbidden_imports.search(source) is None


def _summary(
    *,
    status: str = "success",
    sanitized_response_display: str | None = None,
    sanitized_response_preview: str | None = None,
) -> dict[str, object]:
    return {
        "runtime_id": "runtime-1",
        "invocation_id": "request-1",
        "workflow_id": "workflow-1",
        "execution_mode": "controlled_live",
        "status": status,
        "controlled_run": True,
        "productized_controlled_run": True,
        "sanitized": True,
        "adk_run_allowed": True,
        "adk_run_performed": True,
        "execution_performed": True,
        "live_llm_allowed": True,
        "live_llm_call_performed": True,
        "ollama_allowed": True,
        "ollama_call_performed": True,
        "llm_invocation_call_allowed": True,
        "llm_invocation_call_attempted": True,
        "llm_invocation_runtime_call_performed": True,
        "sanitized_evidence_ref": "evidence://request-1",
        "audit_ref": "audit://request-1",
        "governance_summary_payload_ref": "governance://payload",
        "tool_evidence_ref": "tool-evidence://request-1",
        "tool_run_ref": "tool-run://request-1",
        "llm_invocation_result_ref": "llm-result://request-1",
        "llm_invocation_observation_ref": "llm-observation://request-1",
        "llm_invocation_summary_ref": "llm-summary://request-1",
        "sanitized_response_display": sanitized_response_display,
        "sanitized_response_preview": sanitized_response_preview,
        "final_preflight": {"allowed": True},
        "controlled_live_llm_preflight": {"allowed": True},
        "lifecycle_facts": {"phase": "completed"},
        "run_config_service_bundle_facts": {"profile": "local"},
        "blocking_reasons": (),
        "warnings": ("warn",),
    }


def _request() -> dict[str, object]:
    return {
        "runtime_id": "runtime-1",
        "invocation_id": "request-1",
        "workflow_id": "workflow-1",
        "workflow_name": "workflow name",
        "input_payload": {"input_summary": "已脱敏输入"},
        "operator_approved": True,
        "approval_ref": "approval://request-1",
        "audit_ref": "audit://request-1",
        "sanitized_evidence_ref": "evidence://request-1",
        "governance_summary_output_ref": "governance://request-1",
        "request_live_llm": True,
        "request_ollama": True,
        "allow_live_llm": True,
        "allow_ollama": True,
        "live_llm_approval_ref": "approval://live-request-1",
        "metadata": {"source": "test"},
    }
