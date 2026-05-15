from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import get_type_hints

from adk_adapter import (
    AdkGovernedLlmInvocationOptions,
    AdkGovernedLlmInvocationService,
)
from behavior_contracts.llm_invocation import GovernedLlmInvocationService
from config_contexts.runtime import (
    AdapterSelectionConfigView,
    ArtifactPolicyConfigView,
    EventPolicyConfigView,
    NodeExecutionConfigView,
    ResumePolicyConfigView,
    RuntimeConfigContextBundle,
    RuntimeConfigView,
    RuntimeLiveLlmConfigView,
    WorkflowExecutionConfigView,
)
from composition import (
    LlmInvocationServiceAssembly,
    LlmInvocationServiceAssemblyOptions,
    build_adk_governed_llm_invocation_service,
    build_controlled_live_adk_governed_llm_invocation_service,
    build_controlled_live_adk_governed_llm_invocation_service_from_runtime_config,
    build_controlled_live_llm_invocation_service_assembly,
    build_controlled_live_llm_invocation_service_assembly_from_runtime_config,
    build_llm_invocation_service_assembly,
)
from schemas.llm_invocation import LlmGovernancePrecondition
from schemas.model_routing import ModelRouteFacts


REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSITION_SOURCE_ROOT = REPO_ROOT / "packages" / "composition" / "src" / "composition"


def test_composition_assembles_adk_governed_llm_invocation_service() -> None:
    route_facts = _route_facts()
    governance_precondition = LlmGovernancePrecondition(
        allowed=True,
        reason="composition_precondition_allowed",
        decision="continue",
        governance_decision_ref="governance-decision-1",
    )
    assembly = build_llm_invocation_service_assembly(
        assembly_options=LlmInvocationServiceAssemblyOptions(
            route_facts=route_facts,
            governance_precondition=governance_precondition,
            metadata={"source": "composition-test"},
        )
    )

    assert isinstance(assembly, LlmInvocationServiceAssembly)
    assert isinstance(assembly.service, AdkGovernedLlmInvocationService)
    assert assembly.assembly_options.service_options.live_enabled is False
    assert assembly.assembly_options.route_facts is route_facts
    assert assembly.assembly_options.governance_precondition is governance_precondition
    assert assembly.metadata["service_contract"] == (
        "behavior_contracts.llm_invocation.GovernedLlmInvocationService"
    )
    assert assembly.metadata["does_not_invoke_service"] is True
    assert assembly.metadata["runtime_connected"] is False
    assert assembly.metadata["runtime_container_connected"] is False
    assert assembly.metadata["observability_candidate_created"] is False
    assert assembly.metadata["assembly_options"]["route_facts"]["provider"] == "litellm"
    assert (
        assembly.metadata["assembly_options"]["route_facts"]["metadata"][
            "backend_provider"
        ]
        == "ollama"
    )
    assert (
        assembly.metadata["assembly_options"]["governance_precondition"]["decision"]
        == "continue"
    )


def test_composition_exposes_service_through_behavior_contract_annotation() -> None:
    service = build_adk_governed_llm_invocation_service()
    hints = get_type_hints(build_adk_governed_llm_invocation_service)

    assert isinstance(service, AdkGovernedLlmInvocationService)
    assert hints["return"] is GovernedLlmInvocationService


def test_composition_can_carry_explicit_no_live_service_options() -> None:
    options = LlmInvocationServiceAssemblyOptions(
        service_options=AdkGovernedLlmInvocationOptions(
            live_enabled=False,
            metadata={"assembly_test": "no-live"},
        )
    )

    assembly = build_llm_invocation_service_assembly(assembly_options=options)

    assert assembly.assembly_options.service_options is options.service_options
    assert assembly.metadata["assembly_options"]["service_options"]["live_enabled"] is False
    assert assembly.metadata["assembly_options"]["service_options"]["metadata_keys"] == [
        "assembly_test"
    ]


def test_composition_assembles_controlled_live_service_without_invoking_it() -> None:
    assembly = build_controlled_live_llm_invocation_service_assembly(
        ollama_api_base="http://127.0.0.1:11434",
        timeout_seconds=9,
        max_tokens=16,
        metadata={"assembly_test": "controlled-live"},
    )

    assert isinstance(assembly.service, AdkGovernedLlmInvocationService)
    assert assembly.assembly_options.service_options.live_enabled is True
    assert assembly.assembly_options.service_options.ollama_api_base == (
        "http://127.0.0.1:11434"
    )
    assert assembly.assembly_options.service_options.timeout_seconds == 9
    assert assembly.assembly_options.service_options.max_tokens == 16
    assert assembly.metadata["does_not_invoke_service"] is True
    assert assembly.metadata["runtime_container_connected"] is False
    assert (
        assembly.metadata["assembly_options"]["service_options"]["metadata_keys"]
        == [
            "assembly_test",
            "controlled_live",
            "live_service_profile",
            "source",
        ]
    )
    assert assembly.metadata["assembly_options"]["metadata"]["controlled_live"] is True


def test_composition_assembles_controlled_live_service_from_runtime_config() -> None:
    config_context = _runtime_config_context(
        live_llm=RuntimeLiveLlmConfigView(
            profile="adk_litellm_ollama",
            model_name="ollama/gemma4-pro:latest",
            ollama_api_base="http://127.0.0.1:11434",
            timeout_seconds=17,
            temperature=0.2,
            max_tokens=24,
            metadata={"source": "composition-test-config"},
        )
    )

    assembly = build_controlled_live_llm_invocation_service_assembly_from_runtime_config(
        config_context=config_context,
        timeout_seconds=19,
        metadata={"cli_timeout_seconds_override": True},
    )

    assert isinstance(assembly.service, AdkGovernedLlmInvocationService)
    assert assembly.assembly_options.service_options.live_enabled is True
    assert assembly.assembly_options.service_options.ollama_api_base == (
        "http://127.0.0.1:11434"
    )
    assert assembly.assembly_options.service_options.timeout_seconds == 19
    assert assembly.assembly_options.service_options.temperature == 0.2
    assert assembly.assembly_options.service_options.max_tokens == 24
    metadata = assembly.metadata["assembly_options"]["metadata"]
    assert metadata["live_options_source"] == (
        "config_contexts.runtime.RuntimeLiveLlmConfigView"
    )
    assert metadata["live_service_profile"] == "adk_litellm_ollama"
    assert metadata["configured_model_name"] == "ollama/gemma4-pro:latest"
    assert metadata["timeout_seconds"] == 19
    assert metadata["max_tokens"] == 24
    assert metadata["config_metadata_keys"] == ["source"]
    assert metadata["config_metadata"] == {"source": "composition-test-config"}
    assert metadata["cli_timeout_seconds_override"] is True
    assert assembly.metadata["does_not_invoke_service"] is True


def test_composition_exposes_controlled_live_service_through_contract() -> None:
    service = build_controlled_live_adk_governed_llm_invocation_service(
        metadata={"assembly_test": "controlled-live-contract"}
    )
    hints = get_type_hints(build_controlled_live_adk_governed_llm_invocation_service)

    assert isinstance(service, AdkGovernedLlmInvocationService)
    assert hints["return"] is GovernedLlmInvocationService


def test_composition_exposes_config_driven_controlled_live_service_through_contract() -> None:
    service = build_controlled_live_adk_governed_llm_invocation_service_from_runtime_config(
        config_context=_runtime_config_context()
    )
    hints = get_type_hints(
        build_controlled_live_adk_governed_llm_invocation_service_from_runtime_config
    )

    assert isinstance(service, AdkGovernedLlmInvocationService)
    assert hints["return"] is GovernedLlmInvocationService


def test_composition_llm_invocation_assembly_source_does_not_execute_service() -> None:
    source = (COMPOSITION_SOURCE_ROOT / "llm_invocation_assembly.py").read_text(
        encoding="utf-8"
    )
    forbidden_calls = re.compile(
        r"\b(?:completion|acompletion|runner\.run|run_async)\s*\("
    )

    assert ".invoke(" not in source
    assert "service.invoke" not in source
    assert "LlmInvocationRequest(" not in source
    assert forbidden_calls.search(source) is None
    assert "CE_ENABLE_LIVE_LLM_SMOKE" not in source
    assert "import runtime_container" not in source
    assert "from runtime_container" not in source


def test_composition_llm_invocation_assembly_does_not_use_runtime_builders() -> None:
    source = (COMPOSITION_SOURCE_ROOT / "llm_invocation_assembly.py").read_text(
        encoding="utf-8"
    )

    assert "build_standard_runtime_runner" not in source
    assert "RuntimeDependencies" not in source
    assert "RuntimeContainer" not in source


def test_composition_llm_invocation_public_exports_are_available() -> None:
    signature = inspect.signature(build_llm_invocation_service_assembly)

    assert "assembly_options" in signature.parameters
    assert LlmInvocationServiceAssembly.__name__ == "LlmInvocationServiceAssembly"
    assert (
        LlmInvocationServiceAssemblyOptions.__name__
        == "LlmInvocationServiceAssemblyOptions"
    )


def _route_facts() -> ModelRouteFacts:
    return ModelRouteFacts(
        model_name="ollama/gemma4-pro:latest",
        provider="litellm",
        source="adk_adapter.models",
        metadata={
            "backend_provider": "ollama",
            "route_target": "ollama/gemma4-pro:latest",
            "route_kind": "adk_litellm",
        },
    )


def _runtime_config_context(
    *,
    live_llm: RuntimeLiveLlmConfigView | None = None,
) -> RuntimeConfigContextBundle:
    return RuntimeConfigContextBundle(
        runtime=RuntimeConfigView(runtime_name="composition-test-runtime"),
        workflow_execution=WorkflowExecutionConfigView(
            workflow_name="composition-test-workflow"
        ),
        node_execution=NodeExecutionConfigView(),
        resume_policy=ResumePolicyConfigView(),
        event_policy=EventPolicyConfigView(),
        artifact_policy=ArtifactPolicyConfigView(),
        adapter_selection=AdapterSelectionConfigView(),
        live_llm=live_llm or RuntimeLiveLlmConfigView(),
    )
