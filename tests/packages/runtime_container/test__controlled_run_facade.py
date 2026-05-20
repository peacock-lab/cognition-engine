from __future__ import annotations

import re
from pathlib import Path

import pytest

from runtime_container._controlled_run_facade import (
    ControlledRunFacadeInput,
    ControlledRunFacadeResult,
    build_controlled_run_request_from_facade_input,
    coerce_controlled_run_facade_input,
    run_controlled_run_facade,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_CONTAINER_ROOT = (
    REPO_ROOT / "packages" / "runtime_container" / "src" / "runtime_container"
)
PRODUCT_GATEWAY_ROOT = (
    REPO_ROOT / "packages" / "product_gateway" / "src" / "product_gateway"
)


def test_controlled_run_facade_input_can_be_built_from_mapping() -> None:
    facade_input = coerce_controlled_run_facade_input(
        {
            "runtime_id": "runtime-facade-225",
            "input_payload": {"case_id": "case-225"},
            "metadata": {"source": "test_controlled_run_facade"},
        }
    )

    assert facade_input.runtime_id == "runtime-facade-225"
    assert facade_input.invocation_id == "inv-runtime-facade-225"
    assert facade_input.config_root == Path("config")
    assert facade_input.input_payload == {"case_id": "case-225"}
    assert facade_input.metadata == {"source": "test_controlled_run_facade"}


def test_controlled_run_facade_rejects_raw_payload() -> None:
    with pytest.raises(ValueError, match="forbidden raw payload"):
        coerce_controlled_run_facade_input(
            {
                "runtime_id": "runtime-facade-raw-225",
                "input_payload": {"raw_prompt": "do not carry raw prompt"},
            }
        )


def test_controlled_run_facade_maps_fields_to_controlled_request() -> None:
    request = build_controlled_run_request_from_facade_input(
        {
            "runtime_id": "runtime-facade-map-225",
            "workflow_id": "workflow-controlled-adk-run",
            "workflow_name": "controlled-adk-run",
            "environment": "local",
            "profile": "test",
            "input_payload": {"case_id": "case-map-225"},
            "operator_approved": True,
            "approval_ref": "approval://facade-map-225",
            "audit_ref": "audit://facade-map-225",
            "sanitized_evidence_ref": "evidence://facade-map-225",
            "governance_summary_output_ref": "summary://facade-map-225",
            "allow_tool_confirmation": True,
            "tool_confirmation_approval_ref": "tool-approval://facade-map-225",
            "tool_confirmation_decision_source": "operator://facade-map-225",
        }
    )

    assert request.runtime_input.runtime_id == "runtime-facade-map-225"
    assert request.runtime_input.invocation_ref.invocation_id == (
        "inv-runtime-facade-map-225"
    )
    assert request.runtime_input.input_payload == {"case_id": "case-map-225"}
    assert request.productization_gate.sanitized_evidence_ref == (
        "evidence://facade-map-225"
    )
    assert request.productization_gate.governance_summary_output_ref == (
        "summary://facade-map-225"
    )
    assert request.operator_approval.approval_ref == "approval://facade-map-225"
    assert request.operator_approval.tool_confirmation_approval_ref == (
        "tool-approval://facade-map-225"
    )


def test_controlled_run_facade_allowed_no_live_returns_narrow_result() -> None:
    result = run_controlled_run_facade(
        ControlledRunFacadeInput(
            runtime_id="runtime-facade-allowed-225",
            input_payload={"case_id": "case-allowed-225"},
            operator_approved=True,
            approval_ref="approval://facade-allowed-225",
            audit_ref="audit://facade-allowed-225",
            sanitized_evidence_ref="evidence://facade-allowed-225",
            governance_summary_output_ref="summary://facade-allowed-225",
        )
    )

    assert isinstance(result, ControlledRunFacadeResult)
    assert result.status == "success"
    assert result.execution_performed is True
    assert result.adk_run_performed is True
    assert result.live_llm_call_performed is False
    assert result.ollama_call_performed is False
    assert result.tool_status == "success"
    result_payload = result.to_mapping()
    assert "raw_adk_object_included" not in result_payload
    assert "raw_state_values_included" not in result_payload
    assert "artifact_content_included" not in result_payload
    assert "raw_provider_response" not in result_payload
    assert "raw_tool_input" not in result_payload


def test_controlled_run_facade_result_preserves_sanitized_runtime_facts() -> None:
    result = ControlledRunFacadeResult.from_entry_result(
        {
            "runtime_id": "runtime-facts-448",
            "invocation_id": "inv-facts-448",
            "workflow_id": "workflow-facts-448",
            "adk_run_allowed": True,
            "adk_run_performed": True,
            "execution_performed": True,
            "final_preflight": {"allowed": True, "execution_scope": "test"},
            "controlled_live_llm_preflight": {
                "allowed": False,
                "blocking_reasons": ["live_llm_allowed_not_true"],
            },
            "lifecycle_facts": {"status": "completed"},
            "run_config_service_bundle_facts": {"artifact_service": "in_memory"},
            "llm_invocation_readonly_facts": {
                "result": {
                    "sanitized_response_preview": "preview text",
                    "sanitized_response_display": "display text",
                }
            },
        }
    )
    payload = result.to_mapping()

    assert result.status == "success"
    assert payload["final_preflight"]["allowed"] is True
    assert payload["controlled_live_llm_preflight"]["allowed"] is False
    assert payload["lifecycle_facts"] == {"status": "completed"}
    assert payload["run_config_service_bundle_facts"] == {
        "artifact_service": "in_memory"
    }
    assert payload["sanitized_response_preview"] == "preview text"
    assert payload["sanitized_response_display"] == "display text"


def test_controlled_run_facade_blocks_missing_approval_without_runtime_execution() -> None:
    result = run_controlled_run_facade(
        {
            "runtime_id": "runtime-facade-blocked-225",
            "input_payload": {"case_id": "case-blocked-225"},
        }
    )

    assert isinstance(result, ControlledRunFacadeResult)
    assert result.status == "blocked"
    assert result.execution_performed is False
    assert result.adk_run_performed is False
    assert result.blocking_reasons
    assert "operator_approval_not_true" in result.blocking_reasons


def test_controlled_run_facade_carries_controlled_live_preflight_fields() -> None:
    request = build_controlled_run_request_from_facade_input(
        {
            "runtime_id": "runtime-facade-live-225",
            "input_payload": {"case_id": "case-live-225"},
            "operator_approved": True,
            "approval_ref": "approval://facade-live-225",
            "audit_ref": "audit://facade-live-225",
            "sanitized_evidence_ref": "evidence://facade-live-225",
            "governance_summary_output_ref": "summary://facade-live-225",
            "request_live_llm": True,
            "request_ollama": True,
            "allow_live_llm": True,
            "allow_ollama": True,
            "live_llm_approval_ref": "approval://facade-live-llm-225",
        }
    )

    assert request.productization_gate.request_live_llm is True
    assert request.productization_gate.request_ollama is True
    assert request.productization_gate.allow_live_llm is True
    assert request.productization_gate.allow_ollama is True
    assert request.operator_approval.live_llm_approval_ref == (
        "approval://facade-live-llm-225"
    )


def test_runtime_container_does_not_import_product_gateway() -> None:
    forbidden_import = re.compile(
        r"^\s*(?:from|import)\s+product_gateway\b",
        re.MULTILINE,
    )

    for source_path in RUNTIME_CONTAINER_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_import.search(source) is None, source_path


def test_controlled_run_facade_does_not_import_cli_entrypoint_or_tests() -> None:
    source = (
        RUNTIME_CONTAINER_ROOT / "_controlled_run_facade.py"
    ).read_text(encoding="utf-8")

    assert "runtime_container.entrypoints.cognition" not in source
    assert "tests." not in source


def test_product_gateway_does_not_import_runtime_container_after_default_assembly() -> None:
    forbidden_import = re.compile(
        r"^\s*(?:from|import)\s+runtime_container",
        re.MULTILINE,
    )
    forbidden_symbols = (
        "runtime_container.controlled_adk_run_request_builder",
        "runtime_container.controlled_adk_run_entry",
        "runtime_container.entrypoints.cognition",
        "runtime_container.workflow_registry",
        "ControlledAdkRunRequestBuildInput",
        "ControlledAdkRunRequest",
        "ControlledRunEntryRunner",
        "ControlledRunFacadeInput",
        "ControlledRunFacadeResult",
        "build_controlled_adk_run_request_from_registry",
        "build_controlled_run_request_from_facade_input",
        "coerce_controlled_run_facade_input",
        "run_controlled_run_facade",
        "run_productized_controlled_adk_run",
    )

    for source_path in PRODUCT_GATEWAY_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_import.search(source) is None, source_path
        assert "controlled_live_llm_service" not in source, source_path
        for symbol in forbidden_symbols:
            assert symbol not in source, (source_path, symbol)
