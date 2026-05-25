"""Default operation flow provider factory assembly."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from config_contexts.runtime import (
    RuntimeConfigContextBundle,
    RuntimeConfigSelectionContext,
    RuntimeLiveLlmInvocationOptionsContext,
)
from contract_core.llm_invocation import (
    GovernedLlmInvocationServiceFactory,
    GovernedLlmInvocationServiceResolution,
)

DEFAULT_OPERATION_FLOW_LLM_INVOCATION_PROVIDER_FACTORY_REF = (
    "product_runtime_assembly.operation_flow_provider_factory.default"
)


@dataclass(frozen=True)
class ProductRuntimeAssemblyOperationFlowLlmInvocationServiceFactory:
    """Lazy default factory for operation flow governed LLM invocation services."""

    metadata: Mapping[str, Any]

    def resolve(
        self,
        *,
        config_context: RuntimeConfigContextBundle | None = None,
        config_selection: RuntimeConfigSelectionContext,
        live_llm_options: RuntimeLiveLlmInvocationOptionsContext,
    ) -> GovernedLlmInvocationServiceResolution:
        runtime_factory = _build_runtime_container_llm_invocation_service_factory(
            metadata=self.metadata,
        )
        return runtime_factory.resolve(
            config_context=config_context,
            config_selection=config_selection,
            live_llm_options=live_llm_options,
        )


def build_operation_flow_default_llm_invocation_service_factory(
    *,
    metadata: Mapping[str, Any] | None = None,
) -> GovernedLlmInvocationServiceFactory:
    """Build the default operation flow LLM provider factory for product runtime assembly."""

    assembly_metadata = {
        "source": "product_runtime_assembly.operation_flow_provider_factory",
        "provider_factory_ref": DEFAULT_OPERATION_FLOW_LLM_INVOCATION_PROVIDER_FACTORY_REF,
        "product_runtime_assembly_operation_flow_provider_factory": True,
        **dict(metadata or {}),
    }
    return ProductRuntimeAssemblyOperationFlowLlmInvocationServiceFactory(
        metadata=assembly_metadata,
    )


def _build_runtime_container_llm_invocation_service_factory(
    *,
    metadata: Mapping[str, Any],
) -> GovernedLlmInvocationServiceFactory:
    from runtime_container.llm_invocation_provider_service import (
        build_runtime_container_llm_invocation_service_factory,
    )

    return build_runtime_container_llm_invocation_service_factory(
        metadata=metadata,
    )


__all__ = [
    "DEFAULT_OPERATION_FLOW_LLM_INVOCATION_PROVIDER_FACTORY_REF",
    "ProductRuntimeAssemblyOperationFlowLlmInvocationServiceFactory",
    "build_operation_flow_default_llm_invocation_service_factory",
]
