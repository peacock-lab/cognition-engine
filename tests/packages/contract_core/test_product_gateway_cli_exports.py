from __future__ import annotations

import re
from pathlib import Path

from behavior_contracts.product_gateway_cli import (
    ProductGatewayCliTaskWorkflowHeaderGuard,
)
from schemas.product_gateway_cli import (
    ProductGatewayCliTwfExecutionInputSchema,
    ProductGatewayCliTwfExecutionResultSchema,
    ProductGatewayCliTwfLatestPlanSnapshotSchema,
    ProductGatewayCliTwfRouteInputSchema,
)

from contract_core import product_gateway_cli


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_CORE_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "contract_core" / "src" / "contract_core"
)


def test_product_gateway_cli_facade_reexports_contracts() -> None:
    assert (
        product_gateway_cli.ProductGatewayCliTwfRouteInputSchema
        is ProductGatewayCliTwfRouteInputSchema
    )
    assert (
        product_gateway_cli.ProductGatewayCliTaskWorkflowHeaderGuard
        is ProductGatewayCliTaskWorkflowHeaderGuard
    )
    assert (
        product_gateway_cli.ProductGatewayCliTwfExecutionInputSchema
        is ProductGatewayCliTwfExecutionInputSchema
    )
    assert (
        product_gateway_cli.ProductGatewayCliTwfExecutionResultSchema
        is ProductGatewayCliTwfExecutionResultSchema
    )
    assert (
        product_gateway_cli.ProductGatewayCliTwfLatestPlanSnapshotSchema
        is ProductGatewayCliTwfLatestPlanSnapshotSchema
    )


def test_product_gateway_cli_facade_exports_are_explicit() -> None:
    expected_exports = {
        "PRODUCT_GATEWAY_CLI_TWF_PLAN_WORKFLOW_NAME",
        "ProductGatewayCliTwfRouteInputSchema",
        "ProductGatewayCliTwfRouteProjectionSchema",
        "ProductGatewayCliTwfRequestDraftInputSchema",
        "ProductGatewayCliTwfExecutionInputSchema",
        "ProductGatewayCliTwfExecutionResultSchema",
        "ProductGatewayCliTwfLatestPlanSnapshotSchema",
        "ProductGatewayCliTwfStatusSummaryPersistenceSchema",
        "validate_product_gateway_cli_surface_guards",
    }

    assert expected_exports <= set(product_gateway_cli.__all__)


def test_product_gateway_cli_facade_has_no_forbidden_imports() -> None:
    source = (CONTRACT_CORE_SOURCE_ROOT / "product_gateway_cli.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:product_gateway|cognition_operation_flows|runtime_container|"
        r"composition|adk_adapter|google\.adk|litellm)\b",
        re.MULTILINE,
    )

    assert forbidden_imports.search(source) is None
