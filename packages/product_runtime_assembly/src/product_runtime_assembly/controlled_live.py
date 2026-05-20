"""Default product runtime assembly for controlled-live."""

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
from product_gateway.controlled_live import (
    ControlledLiveGatewayInput,
    run_controlled_live_gateway_request,
)

DEFAULT_CONTROLLED_LIVE_RUNTIME_SERVICE_REF = (
    "product_runtime_assembly.controlled_live.default_runtime_service"
)


def run_controlled_live_with_default_runtime(
    gateway_input: ControlledLiveGatewayInput | Mapping[str, Any],
    *,
    entry_runner: Any | None = None,
    llm_invocation_service: Any | None = None,
    agent_shell_live_client: Any | None = None,
):
    """Run controlled-live through the default governed runtime service."""

    return run_controlled_live_gateway_request(
        gateway_input,
        runtime_service=_default_runtime_service(
            entry_runner=entry_runner,
            llm_invocation_service=llm_invocation_service,
            agent_shell_live_client=agent_shell_live_client,
        ),
        runtime_service_ref=DEFAULT_CONTROLLED_LIVE_RUNTIME_SERVICE_REF,
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
    "DEFAULT_CONTROLLED_LIVE_RUNTIME_SERVICE_REF",
    "run_controlled_live_with_default_runtime",
]
