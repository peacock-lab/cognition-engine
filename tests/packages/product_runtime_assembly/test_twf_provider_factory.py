from __future__ import annotations

from typing import Any

from config_contexts.runtime import (
    RuntimeConfigSelectionContext,
    RuntimeLiveLlmInvocationOptionsContext,
)
from contract_core.llm_invocation import GovernedLlmInvocationServiceResolution
from product_runtime_assembly import twf_provider_factory
from product_runtime_assembly.twf_provider_factory import (
    DEFAULT_TWF_LLM_INVOCATION_PROVIDER_FACTORY_REF,
    ProductRuntimeAssemblyTwfLlmInvocationServiceFactory,
    build_twf_default_llm_invocation_service_factory,
)


class FakeRuntimeContainerProviderFactory:
    def __init__(self) -> None:
        self.captured: dict[str, Any] = {}

    def resolve(
        self,
        *,
        config_context: object | None = None,
        config_selection: RuntimeConfigSelectionContext,
        live_llm_options: RuntimeLiveLlmInvocationOptionsContext,
    ) -> GovernedLlmInvocationServiceResolution:
        self.captured = {
            "config_context": config_context,
            "config_selection": config_selection,
            "live_llm_options": live_llm_options,
        }
        return GovernedLlmInvocationServiceResolution(
            service=None,
            blocking_reasons=("fake_provider_resolution",),
            metadata={"source": "fake_runtime_container_provider_factory"},
        )


def test_twf_default_provider_factory_is_lazy_runtime_container_wrapper(
    monkeypatch,
) -> None:
    captured_metadata: dict[str, Any] = {}
    runtime_factory = FakeRuntimeContainerProviderFactory()

    def fake_builder(*, metadata: dict[str, Any]):
        captured_metadata.update(metadata)
        return runtime_factory

    monkeypatch.setattr(
        twf_provider_factory,
        "_build_runtime_container_llm_invocation_service_factory",
        fake_builder,
    )

    factory = build_twf_default_llm_invocation_service_factory(
        metadata={"request_id": "twf-provider-factory-test"},
    )
    resolution = factory.resolve(
        config_context={"config": "context"},
        config_selection=RuntimeConfigSelectionContext(
            config_root="config/twf",
            environment="local",
            profile="dev",
        ),
        live_llm_options=RuntimeLiveLlmInvocationOptionsContext(
            ollama_api_base="http://127.0.0.1:11434",
            timeout_seconds=12,
        ),
    )

    assert isinstance(factory, ProductRuntimeAssemblyTwfLlmInvocationServiceFactory)
    assert captured_metadata == {
        "source": "product_runtime_assembly.twf_provider_factory",
        "provider_factory_ref": DEFAULT_TWF_LLM_INVOCATION_PROVIDER_FACTORY_REF,
        "product_runtime_assembly_twf_provider_factory": True,
        "request_id": "twf-provider-factory-test",
    }
    assert runtime_factory.captured["config_context"] == {"config": "context"}
    assert runtime_factory.captured["config_selection"].config_root == "config/twf"
    assert runtime_factory.captured["live_llm_options"].timeout_seconds == 12
    assert resolution.blocking_reasons == ("fake_provider_resolution",)


def test_twf_default_provider_factory_exports_are_explicit() -> None:
    assert twf_provider_factory.__all__ == [
        "DEFAULT_TWF_LLM_INVOCATION_PROVIDER_FACTORY_REF",
        "ProductRuntimeAssemblyTwfLlmInvocationServiceFactory",
        "build_twf_default_llm_invocation_service_factory",
    ]
