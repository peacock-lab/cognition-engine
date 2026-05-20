"""Narrow runtime service for governed LLM provider factories."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from contract_core.llm_invocation import GovernedLlmInvocationServiceFactory

from runtime_container.controlled_live_llm_service import (
    build_runtime_container_governed_llm_invocation_service_factory,
)

RUNTIME_CONTAINER_LLM_INVOCATION_PROVIDER_SERVICE_SOURCE = (
    "runtime_container.llm_invocation_provider_service"
)


def build_runtime_container_llm_invocation_service_factory(
    *,
    metadata: Mapping[str, Any] | None = None,
) -> GovernedLlmInvocationServiceFactory:
    """Build the runtime-container provider factory through a narrow service."""

    service_metadata = {
        "source": RUNTIME_CONTAINER_LLM_INVOCATION_PROVIDER_SERVICE_SOURCE,
        "runtime_container_llm_invocation_provider_service": True,
        **dict(metadata or {}),
    }
    return build_runtime_container_governed_llm_invocation_service_factory(
        metadata=service_metadata
    )


__all__ = [
    "RUNTIME_CONTAINER_LLM_INVOCATION_PROVIDER_SERVICE_SOURCE",
    "build_runtime_container_llm_invocation_service_factory",
]
