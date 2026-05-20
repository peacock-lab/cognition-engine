"""Default product runtime assembly for cognition-run."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from config_contexts.runtime import (
    RuntimeConfigSelectionContext,
    RuntimeLiveLlmInvocationOptionsContext,
)
from contract_core.controlled_execution import (
    ControlledExecutionRequestSchema,
    ControlledExecutionRuntimeSummarySchema,
)
from product_gateway.cognition_run import (
    CognitionRunGatewayExecutionResult,
    CognitionRunGatewayInput,
    execute_cognition_run_gateway_request,
    run_cognition_run_gateway_request,
)

DEFAULT_COGNITION_RUN_RUNTIME_SERVICE_REF = (
    "product_runtime_assembly.cognition_run.default_runtime_service"
)


def execute_cognition_run_with_default_runtime(
    gateway_input: CognitionRunGatewayInput | Mapping[str, Any],
    *,
    entry_runner: Any | None = None,
    llm_invocation_service: Any | None = None,
    agent_shell_live_client: Any | None = None,
) -> CognitionRunGatewayExecutionResult:
    """Execute cognition-run through the default governed runtime service."""

    return execute_cognition_run_gateway_request(
        gateway_input,
        runtime_service=_default_runtime_service(
            entry_runner=entry_runner,
            llm_invocation_service=llm_invocation_service,
            agent_shell_live_client=agent_shell_live_client,
        ),
        runtime_service_ref=DEFAULT_COGNITION_RUN_RUNTIME_SERVICE_REF,
    )


def run_cognition_run_with_default_runtime(
    gateway_input: CognitionRunGatewayInput | Mapping[str, Any],
    *,
    entry_runner: Any | None = None,
    llm_invocation_service: Any | None = None,
    agent_shell_live_client: Any | None = None,
):
    """Run cognition-run and return only the product gateway response."""

    return run_cognition_run_gateway_request(
        gateway_input,
        runtime_service=_default_runtime_service(
            entry_runner=entry_runner,
            llm_invocation_service=llm_invocation_service,
            agent_shell_live_client=agent_shell_live_client,
        ),
        runtime_service_ref=DEFAULT_COGNITION_RUN_RUNTIME_SERVICE_REF,
    )


def _default_runtime_service(
    *,
    entry_runner: Any | None,
    llm_invocation_service: Any | None,
    agent_shell_live_client: Any | None,
):
    def default_runtime_service(
        request: ControlledExecutionRequestSchema,
        *,
        config_selection: RuntimeConfigSelectionContext,
        live_llm_options: RuntimeLiveLlmInvocationOptionsContext | None = None,
    ) -> ControlledExecutionRuntimeSummarySchema:
        service_kwargs = {
            "llm_invocation_service": llm_invocation_service,
            "agent_shell_live_client": agent_shell_live_client,
        }
        if entry_runner is not None:
            service_kwargs["entry_runner"] = entry_runner
        return _run_default_controlled_execution_service(
            request,
            config_selection=config_selection,
            live_llm_options=live_llm_options,
            **service_kwargs,
        )

    return default_runtime_service


def _run_default_controlled_execution_service(
    request: ControlledExecutionRequestSchema,
    **kwargs: Any,
) -> ControlledExecutionRuntimeSummarySchema:
    from runtime_container.controlled_execution_service import (
        run_controlled_execution_service,
    )

    return run_controlled_execution_service(request, **kwargs)


__all__ = [
    "DEFAULT_COGNITION_RUN_RUNTIME_SERVICE_REF",
    "execute_cognition_run_with_default_runtime",
    "run_cognition_run_with_default_runtime",
]
