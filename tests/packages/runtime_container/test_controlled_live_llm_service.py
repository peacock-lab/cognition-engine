from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import composition.llm_invocation_assembly as llm_invocation_assembly
import runtime_container.controlled_live_llm_service as service_module
from config_contexts.runtime import (
    RuntimeConfigSelectionContext,
    RuntimeLiveLlmInvocationOptionsContext,
)
from contract_core.llm_invocation import GovernedLlmInvocationServiceFactory
from runtime_container.controlled_live_llm_service import (
    RUNTIME_CONTAINER_LIVE_LLM_PROVIDER_RESOLUTION_EXCEPTION,
    RUNTIME_CONTAINER_LIVE_LLM_PROVIDER_RESOLUTION_FAILED,
    RuntimeContainerGovernedLlmInvocationServiceFactory,
    build_runtime_container_controlled_live_llm_invocation_service,
    build_runtime_container_governed_llm_invocation_service_factory,
)


def test_controlled_live_llm_service_delegates_to_composition_with_metadata(
    monkeypatch: Any,
) -> None:
    captured: dict[str, Any] = {}

    def fake_build_service(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "controlled-live-service"

    monkeypatch.setattr(
        llm_invocation_assembly,
        "build_controlled_live_adk_governed_llm_invocation_service_from_runtime_config",
        fake_build_service,
    )

    config_context = SimpleNamespace(live_llm=SimpleNamespace(profile="test"))
    service = build_runtime_container_controlled_live_llm_invocation_service(
        config_context=config_context,
        ollama_api_base="http://127.0.0.1:11434",
        timeout_seconds=11,
        max_tokens=32,
        response_preview_limit=200,
        provider_profile_ref="local_ollama",
        model_profile_ref="gemma4_pro_local",
        output_governance_profile_ref="direct_controlled_live",
        metadata={"source": "cognition_cli.run.gateway"},
    )

    assert service == "controlled-live-service"
    assert captured["config_context"] is config_context
    assert captured["ollama_api_base"] == "http://127.0.0.1:11434"
    assert captured["timeout_seconds"] == 11
    assert captured["max_tokens"] == 32
    assert captured["provider_profile_ref"] == "local_ollama"
    assert captured["model_profile_ref"] == "gemma4_pro_local"
    assert captured["output_governance_profile_ref"] == "direct_controlled_live"
    assert captured["metadata"]["source"] == "cognition_cli.run.gateway"
    assert captured["metadata"]["runtime_container_controlled_live_service"] is True
    assert captured["metadata"]["cli_controlled_live"] is True
    assert captured["metadata"]["cli_ollama_api_base_override"] is True
    assert captured["metadata"]["cli_timeout_seconds_override"] is True
    assert captured["metadata"]["cli_chat_controlled_live"] is True
    assert captured["metadata"]["response_preview_limit"] == 200


def test_controlled_live_llm_service_can_use_config_root(
    monkeypatch: Any,
) -> None:
    captured: dict[str, Any] = {}

    def fake_build_service(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "controlled-live-service-from-config-root"

    monkeypatch.setattr(
        llm_invocation_assembly,
        "build_controlled_live_adk_governed_llm_invocation_service_from_config_root",
        fake_build_service,
    )

    service = build_runtime_container_controlled_live_llm_invocation_service(
        config_root="config",
        environment="local",
        timeout_seconds=17,
        metadata={"source": "product_gateway.cognition_run"},
    )

    assert service == "controlled-live-service-from-config-root"
    assert captured["config_root"] == "config"
    assert captured["environment"] == "local"
    assert captured["timeout_seconds"] == 17
    assert captured["metadata"]["source"] == "product_gateway.cognition_run"


def test_controlled_live_llm_factory_satisfies_behavior_contract() -> None:
    factory: GovernedLlmInvocationServiceFactory = (
        build_runtime_container_governed_llm_invocation_service_factory()
    )

    assert isinstance(factory, RuntimeContainerGovernedLlmInvocationServiceFactory)
    assert callable(factory.resolve)


def test_controlled_live_llm_factory_resolves_with_config_context(
    monkeypatch: Any,
) -> None:
    captured: dict[str, Any] = {}

    def fake_build_service(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "factory-controlled-live-service"

    monkeypatch.setattr(
        service_module,
        "build_runtime_container_controlled_live_llm_invocation_service",
        fake_build_service,
    )

    config_context = SimpleNamespace(live_llm=SimpleNamespace(profile="test"))
    factory = build_runtime_container_governed_llm_invocation_service_factory(
        metadata={"factory_note": "raw value must not leak"}
    )

    resolution = factory.resolve(
        config_context=config_context,
        config_selection=RuntimeConfigSelectionContext(
            config_root="config/ignored",
            environment="local",
            profile="dev",
            selection_source="test-selection",
            metadata={"selection_note": "raw value must not leak"},
        ),
        live_llm_options=RuntimeLiveLlmInvocationOptionsContext(
            ollama_api_base="http://127.0.0.1:11434",
            timeout_seconds=11,
            max_tokens=32,
            response_preview_limit=200,
            provider_profile_ref="deepseek_gated",
            model_profile_ref="deepseek_v4_flash_external",
            output_governance_profile_ref="adk_no_output_schema_candidate",
            network_gate_open=True,
            operator_approved=True,
            approval_ref="approval://external-provider",
            audit_ref="audit://external-provider",
            selection_source="product_gateway._operation_flows.execution",
            metadata={"request_note": "raw value must not leak"},
        ),
    )

    assert resolution.service == "factory-controlled-live-service"
    assert resolution.blocking_reasons == ()
    assert resolution.warnings == ()
    assert captured["config_context"] is config_context
    assert captured["config_root"] == "config/ignored"
    assert captured["environment"] == "local"
    assert captured["ollama_api_base"] == "http://127.0.0.1:11434"
    assert captured["timeout_seconds"] == 11
    assert captured["max_tokens"] == 32
    assert captured["response_preview_limit"] == 200
    assert captured["provider_profile_ref"] == "deepseek_gated"
    assert captured["model_profile_ref"] == "deepseek_v4_flash_external"
    assert captured["output_governance_profile_ref"] == (
        "adk_no_output_schema_candidate"
    )
    assert captured["network_gate_open"] is True
    assert captured["operator_approved"] is True
    assert captured["approval_ref"] == "approval://external-provider"
    assert captured["audit_ref"] == "audit://external-provider"
    assert captured["metadata"]["source"] == (
        "product_gateway._operation_flows.execution"
    )
    assert captured["metadata"]["runtime_container_live_llm_factory"] is True
    assert captured["metadata"]["config_profile"] == "dev"
    assert captured["metadata"]["factory_metadata_keys"] == ["factory_note"]
    assert captured["metadata"]["config_metadata_keys"] == ["selection_note"]
    assert captured["metadata"]["live_llm_options_metadata_keys"] == [
        "request_note"
    ]
    assert "raw value must not leak" not in str(captured["metadata"])
    assert resolution.metadata["resolution_source"] == (
        "runtime_container.controlled_live_llm_service.factory"
    )
    assert resolution.metadata["config_profile"] == "dev"


def test_controlled_live_llm_factory_resolves_with_config_root(
    monkeypatch: Any,
) -> None:
    captured: dict[str, Any] = {}

    def fake_build_service(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "factory-controlled-live-service-from-root"

    monkeypatch.setattr(
        service_module,
        "build_runtime_container_controlled_live_llm_invocation_service",
        fake_build_service,
    )

    factory = build_runtime_container_governed_llm_invocation_service_factory()
    resolution = factory.resolve(
        config_selection=RuntimeConfigSelectionContext(
            config_root="config/operation_flow",
            environment="local",
            profile="dev",
            selection_source="product_gateway._operation_flows.execution",
        ),
        live_llm_options=RuntimeLiveLlmInvocationOptionsContext(
            timeout_seconds=17,
            selection_source="product_gateway._operation_flows.execution",
        ),
    )

    assert resolution.service == "factory-controlled-live-service-from-root"
    assert captured["config_context"] is None
    assert captured["config_root"] == "config/operation_flow"
    assert captured["environment"] == "local"
    assert captured["timeout_seconds"] == 17
    assert captured["metadata"]["config_profile"] == "dev"
    assert resolution.metadata["config_metadata_keys"] == []


def test_controlled_live_llm_factory_returns_sanitized_blocking_resolution(
    monkeypatch: Any,
) -> None:
    def fake_build_service(**kwargs: Any) -> str:
        raise RuntimeError("raw secret token must not leak")

    monkeypatch.setattr(
        service_module,
        "build_runtime_container_controlled_live_llm_invocation_service",
        fake_build_service,
    )

    factory = build_runtime_container_governed_llm_invocation_service_factory()
    resolution = factory.resolve(
        config_selection=RuntimeConfigSelectionContext(environment="local"),
        live_llm_options=RuntimeLiveLlmInvocationOptionsContext(
            timeout_seconds=11
        ),
    )

    assert resolution.service is None
    assert resolution.blocking_reasons == (
        RUNTIME_CONTAINER_LIVE_LLM_PROVIDER_RESOLUTION_FAILED,
    )
    assert resolution.warnings == (
        RUNTIME_CONTAINER_LIVE_LLM_PROVIDER_RESOLUTION_EXCEPTION,
    )
    assert resolution.metadata == {
        "failure_type": RUNTIME_CONTAINER_LIVE_LLM_PROVIDER_RESOLUTION_EXCEPTION,
        "runtime_container_live_llm_factory": True,
    }
    assert "raw secret token" not in str(resolution.metadata)
