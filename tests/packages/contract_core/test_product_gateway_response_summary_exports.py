from __future__ import annotations

import re
from pathlib import Path

from behavior_contracts.product_gateway_response_summary import (
    ProductGatewayResponseSummaryHeaderGuard,
)
from schemas.product_gateway_response_summary import ProductGatewayResponseSummarySchema

from contract_core import product_gateway_response_summary


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_CORE_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "contract_core" / "src" / "contract_core"
)


def test_product_gateway_response_summary_facade_reexports_contracts() -> None:
    assert (
        product_gateway_response_summary.ProductGatewayResponseSummarySchema
        is ProductGatewayResponseSummarySchema
    )
    assert (
        product_gateway_response_summary.ProductGatewayResponseSummaryHeaderGuard
        is ProductGatewayResponseSummaryHeaderGuard
    )


def test_product_gateway_response_summary_facade_exports_are_explicit() -> None:
    expected_exports = {
        "PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION",
        "ProductGatewayResponseSummarySchema",
        "ProductGatewayResponseSummaryHeaderGuard",
        "validate_product_gateway_response_summary",
        "validate_product_gateway_response_summary_guards",
    }

    assert expected_exports <= set(product_gateway_response_summary.__all__)


def test_product_gateway_response_summary_facade_has_no_forbidden_imports() -> None:
    source = (
        CONTRACT_CORE_SOURCE_ROOT / "product_gateway_response_summary.py"
    ).read_text(encoding="utf-8")
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:product_gateway|cognition_agent|cognition_governance|config_contexts|"
        r"runtime_container|composition|adk_adapter|google\.adk|litellm)\b",
        re.MULTILINE,
    )

    assert forbidden_imports.search(source) is None
