from __future__ import annotations

import re
from pathlib import Path

from behavior_contracts import ControlledExecutionRuntimeService
from behavior_contracts.controlled_execution import (
    ControlledExecutionRuntimeService as ControlledExecutionRuntimeServiceModuleExport,
)
from config_contexts.runtime import (
    RuntimeConfigSelectionContext,
    RuntimeLiveLlmInvocationOptionsContext,
)
from schemas.controlled_execution import (
    ControlledExecutionRequestSchema,
    ControlledExecutionRuntimeSummarySchema,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
BEHAVIOR_CONTRACTS_ROOT = (
    REPO_ROOT / "packages" / "behavior_contracts" / "src" / "behavior_contracts"
)


class StaticControlledExecutionRuntimeService:
    def __call__(
        self,
        request: ControlledExecutionRequestSchema,
        *,
        config_selection: RuntimeConfigSelectionContext,
        live_llm_options: RuntimeLiveLlmInvocationOptionsContext | None = None,
    ) -> ControlledExecutionRuntimeSummarySchema:
        return ControlledExecutionRuntimeSummarySchema(
            runtime_id=request.runtime_id,
            invocation_id=request.invocation_id,
            workflow_id=request.workflow_id,
            execution_mode="contract_test",
            status="success",
            controlled_run=True,
            productized_controlled_run=True,
            execution_performed=True,
            observability_source=config_selection.selection_source,
            warnings=(
                (
                    "live_llm_options_present"
                    if live_llm_options is not None
                    else "live_llm_options_absent"
                ),
            ),
        )


def test_controlled_execution_runtime_service_accepts_structural_service() -> None:
    service: ControlledExecutionRuntimeService = (
        StaticControlledExecutionRuntimeService()
    )

    summary = service(
        ControlledExecutionRequestSchema(
            runtime_id="runtime-contract",
            invocation_id="invocation-contract",
            workflow_id="workflow-contract",
            input_payload={"input_summary": "sanitized input"},
        ),
        config_selection=RuntimeConfigSelectionContext(
            environment="local",
            selection_source="behavior_contracts_test",
        ),
        live_llm_options=RuntimeLiveLlmInvocationOptionsContext(
            timeout_seconds=7,
        ),
    )

    assert isinstance(summary, ControlledExecutionRuntimeSummarySchema)
    assert summary.runtime_id == "runtime-contract"
    assert summary.status == "success"
    assert summary.warnings == ("live_llm_options_present",)


def test_controlled_execution_runtime_service_is_explicitly_exported() -> None:
    assert (
        ControlledExecutionRuntimeService
        is ControlledExecutionRuntimeServiceModuleExport
    )


def test_controlled_execution_behavior_contract_has_no_runtime_imports() -> None:
    source = (BEHAVIOR_CONTRACTS_ROOT / "controlled_execution.py").read_text(
        encoding="utf-8"
    )
    forbidden_terms = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:runtime_container|product_gateway|composition|adk_adapter|"
        r"google\.adk|litellm)\b|"
        r"\b(?:completion|acompletion|run_async)\s*\(",
        re.MULTILINE,
    )

    assert forbidden_terms.search(source) is None
