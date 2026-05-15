from __future__ import annotations

import re
from pathlib import Path

from composition.controlled_adk_run_provider import (
    build_controlled_adk_run_runtime_assembly,
    build_controlled_adk_run_runtime_assembly_provider,
)
from contract_core.runtime import InvocationRef, RuntimeInput, WorkflowRef
from schemas.runtime import RuntimeStatus


REPO_ROOT = Path(__file__).resolve().parents[3]
PROVIDER_SOURCE = (
    REPO_ROOT
    / "packages"
    / "composition"
    / "src"
    / "composition"
    / "controlled_adk_run_provider.py"
)


def test_controlled_adk_run_provider_builds_no_live_runtime_assembly() -> None:
    provider = build_controlled_adk_run_runtime_assembly_provider()

    assembly = provider(
        {
            "config_root": Path("config"),
            "environment": "local",
            "profile": None,
            "runtime_id": "runtime-provider-173",
            "workflow_id": "workflow-controlled-adk-run",
            "workflow_name": "controlled-adk-run",
            "input_payload": {"message": "hello"},
        }
    )

    assert assembly.assembly_options.workflow_name == "controlled-adk-run"
    assert assembly.assembly_options.service_bundle_options.source == "in_memory"
    assert assembly.assembly_options.run_config_options is not None
    assert assembly.assembly_options.run_config_options.streaming_mode == "none"
    assert assembly.assembly_options.run_config_options.save_live_blob is False
    assert assembly.metadata["metadata"]["does_not_call_live_llm"] is True
    assert assembly.metadata["metadata"]["does_not_call_ollama"] is True
    assert (
        assembly.metadata["metadata"]["does_not_enable_tool_eval_memory_mcp_a2a"]
        is True
    )


def test_controlled_adk_run_provider_runtime_executes_without_live_calls() -> None:
    assembly = build_controlled_adk_run_runtime_assembly(
        {
            "config_root": Path("config"),
            "environment": "local",
            "runtime_id": "runtime-provider-exec-173",
            "workflow_id": "workflow-controlled-adk-run",
            "workflow_name": "controlled-adk-run",
            "input_payload": {"message": "hello"},
        }
    )

    result = assembly.runtime_runner.run(
        RuntimeInput(
            runtime_id="runtime-provider-exec-173",
            workflow_ref=WorkflowRef(
                workflow_id="workflow-controlled-adk-run",
                name="controlled-adk-run",
            ),
            invocation_ref=InvocationRef(
                invocation_id="inv-runtime-provider-exec-173",
                runtime_id="runtime-provider-exec-173",
                workflow_id="workflow-controlled-adk-run",
            ),
            input_payload={"message": "hello"},
        )
    )

    serialized = repr(result)

    assert result.status == RuntimeStatus.SUCCESS
    assert result.workflow_result is not None
    assert result.workflow_result.status == RuntimeStatus.SUCCESS
    assert result.workflow_result.events
    assert result.workflow_result.artifact_deltas == []
    assert "live_model_payload" not in serialized
    assert "raw_adk_object" not in serialized
    assert "artifact_content" not in serialized


def test_controlled_adk_run_provider_does_not_reverse_import_runtime_container() -> None:
    source = PROVIDER_SOURCE.read_text(encoding="utf-8")

    assert not re.search(r"^\s*(?:from|import)\s+runtime_container\b", source, re.M)
