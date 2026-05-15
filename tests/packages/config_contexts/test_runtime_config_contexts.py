import pytest
from pydantic import ValidationError

from config_contexts.runtime import (
    AdapterSelectionConfigView,
    AdkRunConfigView,
    ExecutionMode,
    ResumePolicyConfigView,
    RuntimeConfigContextBundle,
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
        save_input_blobs_as_artifacts=True,
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
    assert view.metadata == {"source": "test-runtime-live-llm"}


def test_runtime_live_llm_config_view_rejects_invalid_limits() -> None:
    with pytest.raises(ValidationError):
        RuntimeLiveLlmConfigView(timeout_seconds=0)

    with pytest.raises(ValidationError):
        RuntimeLiveLlmConfigView(max_tokens=0)

    with pytest.raises(ValidationError):
        RuntimeLiveLlmConfigView(temperature=-0.1)


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
