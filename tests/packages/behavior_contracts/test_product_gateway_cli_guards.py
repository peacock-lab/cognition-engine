from __future__ import annotations

import re
from pathlib import Path

from behavior_contracts.product_gateway_cli import (
    ProductGatewayCliSurfaceNoRawPayloadGuard,
    ProductGatewayCliSurfaceNoRuntimeLeakageGuard,
    ProductGatewayCliTaskWorkflowHeaderGuard,
    validate_product_gateway_cli_surface_guards,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
BEHAVIOR_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "behavior_contracts" / "src" / "behavior_contracts"
)


def test_product_gateway_cli_surface_guards_accept_safe_contract() -> None:
    result = validate_product_gateway_cli_surface_guards(
        {
            "workflow_name": "twf_plan_workflow",
            "sanitized_user_text": "做一个方案",
            "metadata": {"source": "test"},
        }
    )

    assert result.passed is True
    assert result.violations == ()


def test_product_gateway_cli_surface_guards_reject_raw_payload() -> None:
    result = ProductGatewayCliSurfaceNoRawPayloadGuard().validate(
        {"metadata": {"raw_response": "not allowed"}}
    )

    assert result.passed is False
    assert "raw or sensitive" in result.violations[0]


def test_product_gateway_cli_surface_guards_reject_runtime_leakage() -> None:
    result = ProductGatewayCliSurfaceNoRuntimeLeakageGuard().validate(
        {"metadata": {"object_module": "composition.runtime"}}
    )

    assert result.passed is False
    assert "runtime object" in result.violations[0]


def test_product_gateway_cli_surface_header_guard_rejects_unknown_workflow() -> None:
    result = ProductGatewayCliTaskWorkflowHeaderGuard().validate(
        {"workflow_name": "unknown_workflow"}
    )

    assert result.passed is False
    assert "unsupported task workflow name" in result.violations[0]


def test_product_gateway_cli_surface_header_guard_checks_execution_input() -> None:
    result = ProductGatewayCliTaskWorkflowHeaderGuard().validate(
        {"request_draft_input": {"workflow_name": "unknown_workflow"}}
    )

    assert result.passed is False
    assert "unsupported task workflow name" in result.violations[0]


def test_product_gateway_cli_surface_guards_have_no_execution_layer_imports() -> None:
    source = (BEHAVIOR_SOURCE_ROOT / "product_gateway_cli.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:product_gateway|cognition_operation_flows|runtime_container|"
        r"composition|adk_adapter|google\.adk|litellm)\b",
        re.MULTILINE,
    )

    assert forbidden_imports.search(source) is None
