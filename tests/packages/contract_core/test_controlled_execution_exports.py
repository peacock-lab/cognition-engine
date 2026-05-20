from __future__ import annotations

import re
from pathlib import Path

from behavior_contracts.controlled_execution import (
    ControlledExecutionRuntimeService,
)
from schemas.controlled_execution import (
    ControlledExecutionRequestSchema,
    ControlledExecutionRuntimeSummarySchema,
    controlled_execution_request_to_mapping,
    controlled_execution_runtime_summary_to_mapping,
    validate_controlled_execution_request,
    validate_controlled_execution_runtime_summary,
)

from contract_core import controlled_execution


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_CORE_ROOT = REPO_ROOT / "packages" / "contract_core" / "src" / "contract_core"


def test_controlled_execution_reexports_runtime_summary_contracts() -> None:
    assert controlled_execution.ControlledExecutionRuntimeService is (
        ControlledExecutionRuntimeService
    )
    assert controlled_execution.ControlledExecutionRequestSchema is (
        ControlledExecutionRequestSchema
    )
    assert controlled_execution.validate_controlled_execution_request is (
        validate_controlled_execution_request
    )
    assert controlled_execution.controlled_execution_request_to_mapping is (
        controlled_execution_request_to_mapping
    )
    assert controlled_execution.ControlledExecutionRuntimeSummarySchema is (
        ControlledExecutionRuntimeSummarySchema
    )
    assert controlled_execution.validate_controlled_execution_runtime_summary is (
        validate_controlled_execution_runtime_summary
    )
    assert controlled_execution.controlled_execution_runtime_summary_to_mapping is (
        controlled_execution_runtime_summary_to_mapping
    )


def test_controlled_execution_exports_are_explicit() -> None:
    expected_exports = {
        "ControlledExecutionRuntimeService",
        "ControlledExecutionRequestSchema",
        "ControlledExecutionRuntimeSummarySchema",
        "ControlledExecutionRuntimeSummaryStatus",
        "validate_controlled_execution_request",
        "validate_controlled_execution_runtime_summary",
        "controlled_execution_request_to_mapping",
        "controlled_execution_runtime_summary_to_mapping",
    }

    assert expected_exports <= set(controlled_execution.__all__)


def test_controlled_execution_contract_core_has_no_runtime_imports() -> None:
    source = (CONTRACT_CORE_ROOT / "controlled_execution.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:product_gateway|runtime_container|composition|adk_adapter|"
        r"google\.adk|litellm)\b",
        re.MULTILINE,
    )

    assert forbidden_imports.search(source) is None
