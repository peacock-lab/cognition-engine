import pytest
from pydantic import ValidationError
from schemas.evidence_summary_answer import (
    SUMMARY_FACT_ITEM_MAX_CHARS,
    SUMMARY_FACT_MAX_CHARS,
    SUMMARY_FACT_MAX_ITEMS,
)

from config_contexts.runtime import (
    AdapterSelectionConfigView,
    AdkRunConfigView,
    ExecutionMode,
    EvidenceSummaryAnswerPolicyConfigView,
    ResumePolicyConfigView,
    RuntimeConfigContextBundle,
    RuntimeLlmModelAliasConfigView,
    RuntimeLlmModelProfileConfigView,
    RuntimeLlmOutputGovernanceProfileConfigView,
    RuntimeLlmProviderProfileConfigView,
    RuntimeLiveLlmInvocationOptionsContext,
    RuntimeConfigSelectionContext,
    RuntimeConfigView,
    RuntimeLiveLlmConfigView,
    RunWorkspacePolicyConfigView,
    WorkflowExecutionConfigView,
    NodeExecutionConfigView,
    EventPolicyConfigView,
    ArtifactPolicyConfigView,
    RuntimeProductizationGateConfigView,
    SessionPolicyConfigView,
    ReferenceReaderPolicyConfigView,
    ToolExposureConfigView,
    ToolsetExposurePolicyConfigView,
)


def test_runtime_config_view_accepts_declared_fields() -> None:
    view = RuntimeConfigView(
        runtime_name="default-runtime",
        execution_mode=ExecutionMode.LOCAL,
        timeout_seconds=60,
    )

    assert view.runtime_name == "default-runtime"
    assert view.default_adapter == "local"
    assert view.timeout_seconds == 60


def test_runtime_config_selection_context_accepts_declared_fields() -> None:
    context = RuntimeConfigSelectionContext(
        config_root="config/test",
        environment="local",
        profile="dev",
        selection_source="product_gateway.cognition_run",
        metadata={"source": "test-runtime-config-selection"},
    )

    assert context.config_root == "config/test"
    assert context.environment == "local"
    assert context.profile == "dev"
    assert context.selection_source == "product_gateway.cognition_run"


def test_runtime_config_selection_context_rejects_sensitive_metadata() -> None:
    with pytest.raises(ValidationError):
        RuntimeConfigSelectionContext(
            metadata={"nested": {"secret": "must not cross boundary"}}
        )


def test_runtime_live_llm_invocation_options_context_accepts_declared_fields() -> None:
    context = RuntimeLiveLlmInvocationOptionsContext(
        ollama_api_base="http://127.0.0.1:11434",
        timeout_seconds=30,
        max_tokens=64,
        response_preview_limit=200,
        selection_source="product_gateway.cognition_run",
        metadata={"source": "test-runtime-live-llm-options"},
    )

    assert context.ollama_api_base == "http://127.0.0.1:11434"
    assert context.timeout_seconds == 30
    assert context.max_tokens == 64
    assert context.response_preview_limit == 200
    assert context.selection_source == "product_gateway.cognition_run"


def test_runtime_live_llm_invocation_options_context_rejects_invalid_values() -> None:
    with pytest.raises(ValidationError):
        RuntimeLiveLlmInvocationOptionsContext(timeout_seconds=0)

    with pytest.raises(ValidationError):
        RuntimeLiveLlmInvocationOptionsContext(max_tokens=0)

    with pytest.raises(ValidationError):
        RuntimeLiveLlmInvocationOptionsContext(
            metadata={"nested": {"token": "must not cross boundary"}}
        )


def test_adapter_selection_config_view_accepts_declared_fields() -> None:
    view = AdapterSelectionConfigView(
        default_runtime_adapter="adk",
        adk_adapter_enabled=True,
        fallback_adapter="local",
    )

    assert view.default_runtime_adapter == "adk"
    assert view.adk_adapter_enabled is True
    assert view.fallback_adapter == "local"


def test_adk_run_config_view_accepts_declared_mapped_fields() -> None:
    view = AdkRunConfigView(
        max_llm_calls=8,
        response_modalities=("TEXT",),
        support_cfc=False,
        streaming_mode="sse",
        enable_affective_dialog=False,
        save_live_blob=False,
        save_live_audio=False,
        get_session_num_recent_events=4,
        custom_metadata={"source": "runtime-config"},
    )

    assert view.max_llm_calls == 8
    assert view.response_modalities == ("TEXT",)
    assert view.save_live_blob is False
    assert view.custom_metadata == {"source": "runtime-config"}


def test_adk_run_config_view_rejects_retired_save_input_blobs_field() -> None:
    with pytest.raises(ValidationError):
        AdkRunConfigView(save_input_blobs_as_artifacts=True)


def test_adk_run_config_view_registers_deferred_official_fields() -> None:
    view = AdkRunConfigView(
        speech_config={"language_code": "zh-CN"},
        context_window_compression={"kind": "registered-only"},
        tool_thread_pool_config={"max_workers": 2},
    )

    assert view.speech_config == {"language_code": "zh-CN"}
    assert view.context_window_compression == {"kind": "registered-only"}
    assert view.tool_thread_pool_config == {"max_workers": 2}


def test_runtime_config_context_bundle_defaults_empty_adk_run_config_view() -> None:
    bundle = RuntimeConfigContextBundle(
        runtime=RuntimeConfigView(runtime_name="default-runtime"),
        workflow_execution=WorkflowExecutionConfigView(workflow_name="default-workflow"),
        node_execution=NodeExecutionConfigView(),
        resume_policy=ResumePolicyConfigView(),
        event_policy=EventPolicyConfigView(),
        artifact_policy=ArtifactPolicyConfigView(),
        session_policy=SessionPolicyConfigView(),
        adapter_selection=AdapterSelectionConfigView(),
    )

    assert bundle.adk_run_config == AdkRunConfigView()
    assert bundle.session_policy == SessionPolicyConfigView()
    assert bundle.productization_gate == RuntimeProductizationGateConfigView()
    assert bundle.live_llm == RuntimeLiveLlmConfigView()
    assert bundle.tool_exposure == ToolExposureConfigView()
    assert bundle.run_workspace == RunWorkspacePolicyConfigView()
    assert bundle.evidence_summary_answer == EvidenceSummaryAnswerPolicyConfigView()


def test_runtime_live_llm_config_view_accepts_controlled_live_options() -> None:
    view = RuntimeLiveLlmConfigView(
        profile="adk_litellm_ollama",
        model_name="ollama/gemma4-pro:latest",
        ollama_api_base="http://127.0.0.1:11434",
        timeout_seconds=30,
        temperature=0.1,
        max_tokens=32,
        metadata={"source": "test-runtime-live-llm"},
    )

    assert view.enabled_by_default is False
    assert view.timeout_seconds == 30
    assert view.temperature == 0.1
    assert view.max_tokens == 32
    assert view.default_provider_profile_ref == "local_ollama"
    assert view.provider_profiles["local_ollama"].backend_provider == "ollama"
    assert view.default_model_profile_ref == "gemma4_pro_local"
    assert (
        view.model_profiles["gemma4_pro_local"].model_name
        == "ollama/gemma4-pro:latest"
    )
    assert view.default_output_governance_profile_ref == "direct_controlled_live"
    assert (
        view.output_governance_profiles["direct_controlled_live"].mode
        == "direct_controlled_live"
    )
    assert (
        view.model_aliases["gemma4"].model_profile_ref
        == "gemma4_pro_local"
    )
    assert (
        view.model_aliases["deepseek"].output_governance_profile_ref
        == "adk_no_output_schema_candidate"
    )
    assert view.metadata == {"source": "test-runtime-live-llm"}


def test_runtime_live_llm_config_view_rejects_invalid_limits() -> None:
    with pytest.raises(ValidationError):
        RuntimeLiveLlmConfigView(timeout_seconds=0)

    with pytest.raises(ValidationError):
        RuntimeLiveLlmConfigView(max_tokens=0)

    with pytest.raises(ValidationError):
        RuntimeLiveLlmConfigView(temperature=-0.1)


def test_runtime_live_llm_config_view_accepts_profile_contracts() -> None:
    view = RuntimeLiveLlmConfigView(
        default_provider_profile_ref="local_ollama",
        provider_profiles={
            "local_ollama": RuntimeLlmProviderProfileConfigView(),
            "deepseek_gated": RuntimeLlmProviderProfileConfigView(
                backend_provider="deepseek",
                route_kind="adk_litellm_openai_compatible",
                api_base_env_var="DEEPSEEK_API_BASE",
                secret_ref="secret-ref://env/DEEPSEEK_API_KEY",
                network_access="external_gated",
                requires_network_gate=True,
                requires_operator_approval=True,
                requires_audit_ref=True,
                enabled_by_default=False,
                metadata={"candidate_only": True},
            ),
        },
        default_model_profile_ref="gemma4_pro_local",
        model_profiles={
            "gemma4_pro_local": RuntimeLlmModelProfileConfigView(),
            "gemma_governance_26b_64k": RuntimeLlmModelProfileConfigView(
                provider_profile_ref="local_ollama",
                model_name="ollama/gemma-governance-26b-64k:latest",
                model_role="high_quality_candidate",
                timeout_seconds=180,
                max_tokens=1024,
                context_window=65536,
                num_ctx=65536,
                resource_tier="high_memory",
                enabled_by_default=False,
                metadata={"candidate_only": True},
            ),
            "deepseek_v4_flash_external": RuntimeLlmModelProfileConfigView(
                provider_profile_ref="deepseek_gated",
                model_name="deepseek/deepseek-v4-flash",
                model_role="external_low_hardware_candidate",
                timeout_seconds=180,
                max_tokens=256,
                resource_tier="external_managed",
                enabled_by_default=False,
                metadata={
                    "candidate_only": True,
                    "model_family": "deepseek_v4",
                    "thinking_mode": "disabled",
                },
            ),
        },
        default_output_governance_profile_ref="direct_controlled_live",
        output_governance_profiles={
            "direct_controlled_live": RuntimeLlmOutputGovernanceProfileConfigView(),
            "adk_no_output_schema_candidate": (
                RuntimeLlmOutputGovernanceProfileConfigView(
                    mode="adk_no_output_schema",
                    adk_native=True,
                    uses_after_model_callback=True,
                    max_repair_attempts=1,
                    metadata={"candidate_only": True},
                )
            ),
            "adk_output_schema_candidate": (
                RuntimeLlmOutputGovernanceProfileConfigView(
                    mode="adk_output_schema",
                    adk_native=True,
                    uses_output_schema=True,
                    uses_output_key=True,
                    uses_after_model_callback=True,
                    max_repair_attempts=1,
                    metadata={"candidate_only": True},
                )
            ),
        },
    )

    assert view.provider_profiles["deepseek_gated"].network_access == "external_gated"
    assert (
        view.model_profiles["gemma_governance_26b_64k"].context_window
        == 65536
    )
    assert (
        view.model_profiles["deepseek_v4_flash_external"].model_name
        == "deepseek/deepseek-v4-flash"
    )
    assert (
        view.output_governance_profiles["adk_no_output_schema_candidate"].mode
        == "adk_no_output_schema"
    )
    assert (
        view.model_aliases["deepseek"].model_name
        == "deepseek/deepseek-v4-flash"
    )


def test_runtime_live_llm_config_view_rejects_invalid_model_alias_refs() -> None:
    with pytest.raises(ValidationError):
        RuntimeLiveLlmConfigView(
            model_aliases={
                "bad": RuntimeLlmModelAliasConfigView(
                    provider_profile_ref="missing",
                    model_profile_ref="gemma4_pro_local",
                    output_governance_profile_ref="direct_controlled_live",
                )
            }
        )

    with pytest.raises(ValidationError):
        RuntimeLiveLlmConfigView(
            model_aliases={
                "bad": RuntimeLlmModelAliasConfigView(
                    provider_profile_ref="local_ollama",
                    model_profile_ref="gemma4_pro_local",
                    output_governance_profile_ref="direct_controlled_live",
                    model_name="ollama/other:latest",
                )
            }
        )


def test_runtime_llm_provider_profile_rejects_unsafe_external_gated_shape() -> None:
    with pytest.raises(ValidationError):
        RuntimeLlmProviderProfileConfigView(
            backend_provider="deepseek",
            network_access="external_gated",
            requires_network_gate=False,
            requires_operator_approval=True,
            requires_audit_ref=True,
        )

    with pytest.raises(ValidationError):
        RuntimeLlmProviderProfileConfigView(api_base_env_var="DEEPSEEK_API_KEY")

    with pytest.raises(ValidationError):
        RuntimeLlmProviderProfileConfigView(metadata={"api_key": "sk-test"})


def test_runtime_llm_model_profile_rejects_incoherent_limits() -> None:
    with pytest.raises(ValidationError):
        RuntimeLlmModelProfileConfigView(max_tokens=2048, context_window=1024)

    with pytest.raises(ValidationError):
        RuntimeLlmModelProfileConfigView(max_tokens=2048, num_ctx=1024)

    with pytest.raises(ValidationError):
        RuntimeLlmModelProfileConfigView(metadata={"nested": {"token": "bad"}})


def test_runtime_llm_output_governance_profile_rejects_incoherent_flags() -> None:
    with pytest.raises(ValidationError):
        RuntimeLlmOutputGovernanceProfileConfigView(
            mode="direct_controlled_live",
            adk_native=True,
        )

    with pytest.raises(ValidationError):
        RuntimeLlmOutputGovernanceProfileConfigView(
            mode="adk_output_schema",
            adk_native=True,
            uses_output_schema=True,
            uses_output_key=False,
            uses_after_model_callback=True,
        )

    with pytest.raises(ValidationError):
        RuntimeLlmOutputGovernanceProfileConfigView(
            mode="adk_no_output_schema",
            adk_native=True,
            uses_output_schema=True,
            uses_after_model_callback=True,
        )


def test_runtime_live_llm_config_view_rejects_unknown_profile_refs() -> None:
    with pytest.raises(ValidationError):
        RuntimeLiveLlmConfigView(default_provider_profile_ref="missing")

    with pytest.raises(ValidationError):
        RuntimeLiveLlmConfigView(
            model_profiles={
                "broken": RuntimeLlmModelProfileConfigView(
                    provider_profile_ref="missing"
                )
            }
        )

    with pytest.raises(ValidationError):
        RuntimeLiveLlmConfigView(
            output_governance_profiles={
                "": RuntimeLlmOutputGovernanceProfileConfigView()
            }
        )


def test_evidence_summary_answer_policy_config_view_defaults() -> None:
    view = EvidenceSummaryAnswerPolicyConfigView()

    assert view.enabled_by_default is False
    assert view.profile == "smoke_only"
    assert view.exposure_enabled is True
    assert view.allow_model_context is True
    assert view.allow_governed_summary_facts is True
    assert view.allow_answer_generation_success is False
    assert view.requires_live_llm_gate is True
    assert view.answer_generation_service_ref is None
    assert view.llm_provider_factory_ref is None
    assert view.answer_policy_ref == (
        "policy://product-application-assembly/evidence-summary-answer/"
        "answer/minimal-v1"
    )
    assert view.citation_policy_ref == (
        "policy://product-application-assembly/evidence-summary-answer/"
        "citation/minimal-v1"
    )
    assert view.allow_raw_boundary is False
    assert view.allow_sanitized_excerpt_preview is False
    assert view.allow_observability_candidate_body is False
    assert view.citation_required is True
    assert view.allow_citation_exception is False
    assert view.insufficient_evidence_required is True
    assert view.max_summary_facts == SUMMARY_FACT_MAX_ITEMS
    assert view.max_summary_fact_chars == SUMMARY_FACT_ITEM_MAX_CHARS
    assert view.max_total_summary_fact_chars == SUMMARY_FACT_MAX_CHARS
    assert view.model_context_budget == SUMMARY_FACT_MAX_CHARS
    assert view.answer_preview_limit == 1000


def test_evidence_summary_answer_policy_config_view_accepts_declared_policy() -> None:
    view = EvidenceSummaryAnswerPolicyConfigView(
        profile="smoke_only",
        exposure_enabled=True,
        allow_model_context=True,
        allow_governed_summary_facts=True,
        max_summary_facts=12,
        max_summary_fact_chars=250,
        max_total_summary_fact_chars=2000,
        model_context_budget=3000,
        answer_preview_limit=800,
        metadata={"source": "test-runtime-config"},
    )

    assert view.max_summary_facts == 12
    assert view.max_summary_fact_chars == 250
    assert view.max_total_summary_fact_chars == 2000
    assert view.model_context_budget == 3000
    assert view.metadata == {"source": "test-runtime-config"}


def test_evidence_summary_answer_policy_config_view_accepts_controlled_live_generation_policy() -> None:
    view = EvidenceSummaryAnswerPolicyConfigView(
        profile="controlled_live_answer_generation",
        allow_answer_generation_success=True,
        answer_generation_service_ref=(
            "behavior-contract://evidence-summary-answer/generation-service-v1"
        ),
        llm_provider_factory_ref=(
            "provider-factory://evidence-summary-answer/controlled-live/default-v1"
        ),
        answer_policy_ref="policy://evidence-summary-answer/answer-generation-v1",
        citation_policy_ref="policy://evidence-summary-answer/citation-v1",
        metadata={"source": "test-runtime-config"},
    )

    assert view.profile == "controlled_live_answer_generation"
    assert view.allow_answer_generation_success is True
    assert view.requires_live_llm_gate is True


def test_evidence_summary_answer_policy_config_view_rejects_smoke_only_generation_success() -> None:
    with pytest.raises(ValidationError):
        EvidenceSummaryAnswerPolicyConfigView(
            profile="smoke_only",
            allow_answer_generation_success=True,
        )


def test_evidence_summary_answer_policy_config_view_rejects_generation_success_without_refs() -> None:
    with pytest.raises(ValidationError):
        EvidenceSummaryAnswerPolicyConfigView(
            profile="controlled_live_answer_generation",
            allow_answer_generation_success=True,
        )

    with pytest.raises(ValidationError):
        EvidenceSummaryAnswerPolicyConfigView(
            profile="controlled_live_answer_generation",
            allow_answer_generation_success=True,
            answer_generation_service_ref=(
                "behavior-contract://evidence-summary-answer/generation-service-v1"
            ),
        )


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    (
        ("enabled_by_default", True),
        ("requires_live_llm_gate", False),
        ("allow_governed_summary_facts", False),
        ("allow_raw_boundary", True),
        ("allow_sanitized_excerpt_preview", True),
        ("allow_observability_candidate_body", True),
        ("allow_citation_exception", True),
        ("citation_required", False),
        ("insufficient_evidence_required", False),
    ),
)
def test_evidence_summary_answer_policy_config_view_rejects_hard_constraint_changes(
    field_name: str,
    field_value: bool,
) -> None:
    with pytest.raises(ValidationError):
        EvidenceSummaryAnswerPolicyConfigView(**{field_name: field_value})


def test_evidence_summary_answer_policy_config_view_rejects_sensitive_metadata() -> None:
    with pytest.raises(ValidationError):
        EvidenceSummaryAnswerPolicyConfigView(
            metadata={"nested": {"token": "must not cross boundary"}}
        )


def test_evidence_summary_answer_policy_config_view_rejects_incoherent_exposure() -> None:
    with pytest.raises(ValidationError):
        EvidenceSummaryAnswerPolicyConfigView(
            exposure_enabled=False,
            allow_model_context=True,
        )


def test_runtime_productization_gate_config_view_models_explicit_controls() -> None:
    view = RuntimeProductizationGateConfigView(
        gate_id="gate-147",
        request_adk_run=True,
        allow_adk_run=True,
        explicit_operator_approval=True,
        sanitized_evidence_ref="evidence://sanitized/gate-147",
        governance_summary_output_ref="artifact://summary/gate-147",
        audit_ref="audit://gate-147",
    )

    assert view.request_adk_run is True
    assert view.allow_adk_run is True
    assert view.request_live_llm is False


def test_runtime_config_view_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        RuntimeConfigView(runtime_name="default-runtime", unexpected=True)


def test_tool_exposure_config_view_exports_runtime_profile_mapping() -> None:
    view = ToolExposureConfigView(
        default_profile="readonly_reference",
        profiles={
            "readonly_reference": {
                "source_ref": "config://test/tool_exposure",
                "toolsets": [
                    {
                        "toolset_name": "local_reference_tools",
                        "toolset_kind": "toolset",
                        "source_ref": "local-reference-reader://workspace",
                        "allowlist_tool_names": ["local_reference_reader"],
                        "tool_filter": ["local_reference_reader"],
                        "reference_reader": {
                            "allowed_roots": ["tasks", "docs"],
                            "max_bytes": 2048,
                        },
                    }
                ],
            }
        },
    )
    profile_config = view.to_profile_config()

    assert view.default_profile == "readonly_reference"
    assert profile_config["profiles"]["readonly_reference"]["toolsets"][0][
        "toolset_name"
    ] == "local_reference_tools"
    assert profile_config["profiles"]["readonly_reference"]["toolsets"][0][
        "reference_reader"
    ]["allowed_roots"] == ["tasks", "docs"]
    assert profile_config["profiles"]["readonly_reference"]["toolsets"][0][
        "reference_reader"
    ]["allowed_files"] == ["pyproject.toml"]


def test_tool_exposure_config_rejects_allowlist_expansion_and_non_readonly() -> None:
    with pytest.raises(ValidationError):
        ToolsetExposurePolicyConfigView(
            toolset_name="local_reference_tools",
            source_ref="local-reference-reader://workspace",
            allowlist_tool_names=("local_reference_reader",),
            tool_filter=("unapproved_tool",),
        )

    with pytest.raises(ValidationError):
        ToolsetExposurePolicyConfigView(
            toolset_name="local_reference_tools",
            source_ref="local-reference-reader://workspace",
            allowlist_tool_names=("local_reference_reader",),
            readonly_only=False,
        )


def test_reference_reader_policy_rejects_unsafe_roots_and_suffixes() -> None:
    with pytest.raises(ValidationError):
        ReferenceReaderPolicyConfigView(allowed_roots=("../outside",))

    with pytest.raises(ValidationError):
        ReferenceReaderPolicyConfigView(allowed_files=("../pyproject.toml",))

    with pytest.raises(ValidationError):
        ReferenceReaderPolicyConfigView(allowed_suffixes=("md/path",))


def test_run_workspace_policy_exports_runtime_kwargs_and_rejects_unsafe_root() -> None:
    view = RunWorkspacePolicyConfigView(
        workspace_root=".cognition-runs",
        retention_policy="keep",
        cleanup_policy="manual",
        max_write_bytes=4096,
    )

    assert view.to_policy_kwargs() == {
        "workspace_root": ".cognition-runs",
        "retention_policy": "keep",
        "cleanup_policy": "manual",
        "max_write_bytes": 4096,
    }

    with pytest.raises(ValidationError):
        RunWorkspacePolicyConfigView(workspace_root="../outside")


def test_hitl_requires_resume() -> None:
    with pytest.raises(ValidationError):
        ResumePolicyConfigView(enable_hitl=True, enable_resume=False)
