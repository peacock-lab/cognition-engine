from __future__ import annotations

from pathlib import Path

from google.adk.tools import FunctionTool

from adk_adapter import AdkFunctionToolOptions
from composition import (
    AdkFunctionToolAssembly,
    AdkFunctionToolAssemblyOptions,
    run_controlled_live_low_risk_external_tool_smoke,
    run_no_live_adk_function_tool_product_entry,
)
from composition.runtime import RuntimeCompositionOptions


def test_adk_function_tool_assembly_injects_native_tool_into_agent() -> None:
    assembly = AdkFunctionToolAssembly(
        assembly_options=AdkFunctionToolAssemblyOptions(
            app_name="tool-test-app",
            user_id="tool-test-user",
            agent_name="tool_agent",
            metadata={"source": "test"},
        )
    )

    tool = assembly.build_tool()
    agent = assembly.build_agent()
    metadata = assembly.metadata()

    assert isinstance(tool, FunctionTool)
    assert tool.name == "review_task_context"
    assert agent.name == "tool_agent"
    assert len(agent.tools) == 1
    assert agent.tools[0].name == "review_task_context"
    assert metadata["assembly"] == "composition.adk_tool_assembly"
    assert metadata["tool_name"] == "review_task_context"
    assert metadata["tool_count"] == 1
    assert metadata["observability_candidate"] == (
        "observability_hub.adk_tool_evidence"
    )
    assert "instruction" not in metadata["assembly_options"]


def test_no_live_adk_function_tool_product_entry_builds_governance_audit(
    tmp_path: Path,
) -> None:
    config_root = _write_tool_runtime_config(tmp_path)

    product_run = run_no_live_adk_function_tool_product_entry(
        options=RuntimeCompositionOptions(config_root=config_root, environment="local"),
        task_ref="task://211",
        task_kind="implementation_task",
        evidence_ref="evidence://211",
        invocation_id="tool-run-211",
        runtime_id="runtime-tool-211",
    )
    audit = product_run.to_governance_audit()

    assert audit["tool_evidence_ref"].startswith(
        "adk-tool-call-evidence://adk-tool-call-evidence-"
    )
    assert audit["tool_run_ref"] == "adk-function-tool-run://tool-run-211"
    assert audit["tool_name"] == "review_task_context"
    assert audit["tool_kind"] == "deterministic_no_live_task_review"
    assert audit["status"] == "success"
    assert audit["tool_call_allowed"] is True
    assert audit["tool_call_attempted"] is True
    assert audit["tool_runtime_call_performed"] is True
    assert audit["tool_confirmation_required"] is True
    assert audit["tool_confirmation_granted"] is True
    assert audit["adk_tool_confirmation_requested"] is False
    assert audit["tool_approval_ref"] is None
    assert audit["tool_failure_type"] is None
    assert audit["tool_input_summary"]["argument_keys"] == [
        "evidence_ref",
        "task_kind",
        "task_ref",
    ]
    assert audit["tool_output_summary"]["recommendation"] == "review_ready"
    assert audit["readonly_facts_embedded"] is False
    assert audit["does_not_store_raw_tool_input"] is True
    assert audit["does_not_store_raw_tool_output"] is True
    assert audit["raw_adk_object_included"] is False


def test_no_live_adk_function_tool_product_entry_uses_configured_confirmation(
    tmp_path: Path,
) -> None:
    config_root = _write_tool_runtime_config(
        tmp_path,
        default_require_confirmation=False,
    )

    product_run = run_no_live_adk_function_tool_product_entry(
        options=RuntimeCompositionOptions(config_root=config_root, environment="local"),
        task_ref="task://216",
        task_kind="implementation_task",
        evidence_ref="evidence://216",
        invocation_id="tool-run-216",
        runtime_id="runtime-tool-216",
    )
    audit = product_run.to_governance_audit()

    assert audit["status"] == "success"
    assert audit["tool_runtime_call_performed"] is True
    assert audit["tool_confirmation_required"] is False
    assert audit["tool_confirmation_granted"] is True
    assert audit["adk_tool_confirmation_requested"] is False
    assert audit["tool_failure_type"] is None


def test_no_live_adk_function_tool_product_entry_maps_confirmation_required(
    tmp_path: Path,
) -> None:
    config_root = _write_tool_runtime_config(tmp_path)

    product_run = run_no_live_adk_function_tool_product_entry(
        options=RuntimeCompositionOptions(config_root=config_root, environment="local"),
        task_ref="task://214",
        task_kind="implementation_task",
        evidence_ref="evidence://214",
        invocation_id="tool-run-214-required",
        runtime_id="runtime-tool-214",
        assembly_options=AdkFunctionToolAssemblyOptions(
            tool_options=AdkFunctionToolOptions(
                tool_name="review_task_context",
                tool_kind="deterministic_no_live_task_review",
                require_confirmation=True,
            )
        ),
        tool_confirmation_granted=None,
        tool_approval_ref="approval://tool-214",
        tool_confirmation_decision_source="test.operator_approval",
    )
    audit = product_run.to_governance_audit()

    assert audit["status"] == "failed"
    assert audit["tool_runtime_call_performed"] is False
    assert audit["tool_confirmation_required"] is True
    assert audit["tool_confirmation_granted"] is False
    assert audit["adk_tool_confirmation_requested"] is True
    assert audit["tool_approval_ref"] == "approval://tool-214"
    assert audit["tool_confirmation_decision_source"] == "test.operator_approval"
    assert audit["tool_failure_type"] == "tool_confirmation_required"
    assert audit["does_not_store_raw_tool_input"] is True
    assert audit["does_not_store_raw_tool_output"] is True


def test_no_live_adk_function_tool_product_entry_maps_confirmation_granted(
    tmp_path: Path,
) -> None:
    config_root = _write_tool_runtime_config(tmp_path)

    product_run = run_no_live_adk_function_tool_product_entry(
        options=RuntimeCompositionOptions(config_root=config_root, environment="local"),
        task_ref="task://214",
        task_kind="implementation_task",
        evidence_ref="evidence://214",
        invocation_id="tool-run-214-granted",
        runtime_id="runtime-tool-214",
        assembly_options=AdkFunctionToolAssemblyOptions(
            tool_options=AdkFunctionToolOptions(
                tool_name="review_task_context",
                tool_kind="deterministic_no_live_task_review",
                require_confirmation=True,
            )
        ),
        tool_confirmation_granted=True,
        tool_approval_ref="approval://tool-214",
        tool_confirmation_decision_source="test.operator_approval",
    )
    audit = product_run.to_governance_audit()

    assert audit["status"] == "success"
    assert audit["tool_runtime_call_performed"] is True
    assert audit["tool_confirmation_required"] is True
    assert audit["tool_confirmation_granted"] is True
    assert audit["adk_tool_confirmation_requested"] is False
    assert audit["tool_approval_ref"] == "approval://tool-214"
    assert audit["tool_failure_type"] is None


def test_controlled_live_low_risk_external_tool_smoke_blocks_when_disabled(
    tmp_path: Path,
) -> None:
    config_root = _write_tool_runtime_config(
        tmp_path,
        low_risk_tool_allowlist=("deterministic_external_echo",),
    )

    product_run = run_controlled_live_low_risk_external_tool_smoke(
        options=RuntimeCompositionOptions(config_root=config_root, environment="local"),
        message_ref="message://217",
        invocation_id="tool-run-217-disabled",
        runtime_id="runtime-tool-217",
    )
    audit = product_run.to_governance_audit()

    assert audit["status"] == "failed"
    assert audit["tool_name"] == "deterministic_external_echo"
    assert audit["tool_call_allowed"] is False
    assert audit["tool_call_attempted"] is False
    assert audit["tool_runtime_call_performed"] is False
    assert audit["tool_failure_type"] == "tool_smoke_disabled"


def test_controlled_live_low_risk_external_tool_smoke_blocks_not_allowlisted(
    tmp_path: Path,
) -> None:
    config_root = _write_tool_runtime_config(
        tmp_path,
        low_risk_tool_allowlist=(),
    )

    product_run = run_controlled_live_low_risk_external_tool_smoke(
        options=RuntimeCompositionOptions(config_root=config_root, environment="local"),
        message_ref="message://217",
        invocation_id="tool-run-217-not-allowlisted",
        runtime_id="runtime-tool-217",
        controlled_live_external_tool_smoke_enabled=True,
        smoke_override_source="test.operator_smoke",
    )
    audit = product_run.to_governance_audit()

    assert audit["status"] == "failed"
    assert audit["tool_call_allowed"] is False
    assert audit["tool_runtime_call_performed"] is False
    assert audit["tool_failure_type"] == "tool_not_in_low_risk_allowlist"


def test_controlled_live_low_risk_external_tool_smoke_requires_confirmation(
    tmp_path: Path,
) -> None:
    config_root = _write_tool_runtime_config(
        tmp_path,
        low_risk_tool_allowlist=("deterministic_external_echo",),
    )

    product_run = run_controlled_live_low_risk_external_tool_smoke(
        options=RuntimeCompositionOptions(config_root=config_root, environment="local"),
        message_ref="message://217",
        invocation_id="tool-run-217-confirmation-required",
        runtime_id="runtime-tool-217",
        controlled_live_external_tool_smoke_enabled=True,
        smoke_override_source="test.operator_smoke",
        tool_confirmation_granted=None,
        tool_approval_ref="approval://tool-217",
        tool_confirmation_decision_source="test.operator_approval",
    )
    audit = product_run.to_governance_audit()

    assert audit["status"] == "failed"
    assert audit["tool_call_allowed"] is True
    assert audit["tool_runtime_call_performed"] is False
    assert audit["tool_confirmation_required"] is True
    assert audit["adk_tool_confirmation_requested"] is True
    assert audit["tool_failure_type"] == "tool_confirmation_required"


def test_controlled_live_low_risk_external_tool_smoke_runs_when_confirmed(
    tmp_path: Path,
) -> None:
    config_root = _write_tool_runtime_config(
        tmp_path,
        low_risk_tool_allowlist=("deterministic_external_echo",),
    )

    product_run = run_controlled_live_low_risk_external_tool_smoke(
        options=RuntimeCompositionOptions(config_root=config_root, environment="local"),
        message_ref="message://217",
        message_kind="external_smoke",
        echo_label="safe",
        invocation_id="tool-run-217-confirmed",
        runtime_id="runtime-tool-217",
        controlled_live_external_tool_smoke_enabled=True,
        smoke_override_source="test.operator_smoke",
        tool_confirmation_granted=True,
        tool_approval_ref="approval://tool-217",
        tool_confirmation_decision_source="test.operator_approval",
    )
    audit = product_run.to_governance_audit()

    assert audit["status"] == "success"
    assert audit["tool_call_allowed"] is True
    assert audit["tool_runtime_call_performed"] is True
    assert audit["tool_confirmation_required"] is True
    assert audit["tool_confirmation_granted"] is True
    assert audit["tool_output_summary"]["result_kind"] == (
        "deterministic_external_echo"
    )
    assert audit["tool_output_summary"]["recommendation"] == (
        "external_tool_smoke_ready"
    )
    assert "message://217" not in repr(audit)


def _write_tool_runtime_config(
    tmp_path: Path,
    *,
    default_require_confirmation: bool = True,
    low_risk_tool_allowlist: tuple[str, ...] = (),
) -> Path:
    config_root = tmp_path / "config"
    (config_root / "base").mkdir(parents=True)
    (config_root / "env").mkdir()
    (config_root / "base" / "runtime.yaml").write_text(
        f"""
runtime:
  runtime_name: tool-runtime
workflow_execution:
  workflow_name: tool-workflow
node_execution: {{}}
resume_policy: {{}}
event_policy: {{}}
artifact_policy: {{}}
adapter_selection:
  default_runtime_adapter: adk
  adk_adapter_enabled: true
adk_run_config:
  max_llm_calls: 2
  streaming_mode: none
tool_confirmation:
  default_require_confirmation: {str(default_require_confirmation).lower()}
  default_mode: operator_required
  controlled_live_external_tool_smoke_enabled: false
  auto_confirmation_allowed: false
  low_risk_tool_allowlist:
{_yaml_list(low_risk_tool_allowlist)}
""",
        encoding="utf-8",
    )
    return config_root


def _yaml_list(values: tuple[str, ...]) -> str:
    if not values:
        return "    []"
    return "\n".join(f"    - {value}" for value in values)
