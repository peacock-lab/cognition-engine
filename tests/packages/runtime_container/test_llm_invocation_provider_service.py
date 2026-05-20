from __future__ import annotations

from typing import Any

import runtime_container.llm_invocation_provider_service as provider_service
from runtime_container.llm_invocation_provider_service import (
    RUNTIME_CONTAINER_LLM_INVOCATION_PROVIDER_SERVICE_SOURCE,
    build_runtime_container_llm_invocation_service_factory,
)


def test_runtime_container_llm_invocation_provider_service_builds_factory(
    monkeypatch: Any,
) -> None:
    captured: dict[str, Any] = {}
    fake_factory = object()

    def fake_build_factory(**kwargs: Any) -> object:
        captured.update(kwargs)
        return fake_factory

    monkeypatch.setattr(
        provider_service,
        "build_runtime_container_governed_llm_invocation_service_factory",
        fake_build_factory,
    )

    factory = build_runtime_container_llm_invocation_service_factory(
        metadata={"request_kind": "twf"}
    )

    assert factory is fake_factory
    assert captured["metadata"] == {
        "source": RUNTIME_CONTAINER_LLM_INVOCATION_PROVIDER_SERVICE_SOURCE,
        "runtime_container_llm_invocation_provider_service": True,
        "request_kind": "twf",
    }


def test_runtime_container_llm_invocation_provider_service_exports_are_explicit() -> None:
    assert set(provider_service.__all__) == {
        "RUNTIME_CONTAINER_LLM_INVOCATION_PROVIDER_SERVICE_SOURCE",
        "build_runtime_container_llm_invocation_service_factory",
    }
