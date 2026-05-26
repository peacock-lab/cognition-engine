from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "packages" / "operation_flows"
SOURCE_ROOT = PACKAGE_ROOT / "src"
TASK_WORKFLOWS_PACKAGE_ROOT = SOURCE_ROOT / "cognition_operation_flows"

sys.path.insert(0, str(SOURCE_ROOT))

import cognition_operation_flows  # noqa: E402
from cognition_operation_flows._core.descriptors import (  # noqa: E402
    OperationFlowDescriptorCandidate,
    build_operation_flow_descriptor_candidate,
)
from cognition_operation_flows._core.registry import (  # noqa: E402
    build_operation_flow_registry_candidate,
    resolve_operation_flow_descriptor_candidate,
)


def test_operation_flow_descriptor_defaults_to_candidate_channel_neutral() -> None:
    descriptor = build_operation_flow_descriptor_candidate(
        workflow_id="plan-workflow-candidate",
        workflow_name="Plan workflow candidate",
        workflow_kind="plan",
        metadata={"source": "test"},
    )

    assert descriptor.candidate_only is True
    assert descriptor.channel_neutral is True
    assert descriptor.owner_package == "cognition_operation_flows"
    assert descriptor.product_gateway_entry_required is True
    assert descriptor.channel_private_workflow is False
    assert descriptor.product_gateway_owns_workflow is False
    assert descriptor.runtime_container_internal_workflow is False
    assert descriptor.workflow_execution_enabled is False
    assert descriptor.public_contract_enabled is False
    assert descriptor.execution_boundary == "no_execution"


@pytest.mark.parametrize(
    "field_name, value",
    [
        ("candidate_only", False),
        ("channel_neutral", False),
        ("product_gateway_entry_required", False),
        ("channel_private_workflow", True),
        ("product_gateway_owns_workflow", True),
        ("runtime_container_internal_workflow", True),
        ("workflow_execution_enabled", True),
    ],
)
def test_operation_flow_descriptor_rejects_boundary_drift(
    field_name: str,
    value: bool,
) -> None:
    payload = {
        "workflow_id": "drift-workflow",
        "workflow_name": "Drift workflow",
        "workflow_kind": "custom_candidate",
        field_name: value,
    }

    with pytest.raises(ValidationError):
        OperationFlowDescriptorCandidate.model_validate(payload)


def test_operation_flow_descriptor_rejects_raw_payload_metadata() -> None:
    with pytest.raises(ValidationError):
        build_operation_flow_descriptor_candidate(
            workflow_id="raw-workflow",
            workflow_name="Raw workflow",
            workflow_kind="custom_candidate",
            metadata={"raw_prompt": "不得进入候选描述符"},
        )


def test_operation_flow_registry_resolves_descriptors_without_execution() -> None:
    descriptor = build_operation_flow_descriptor_candidate(
        workflow_id="reference-review-workflow-candidate",
        workflow_name="Reference review workflow candidate",
        workflow_kind="reference_review",
    )
    registry = build_operation_flow_registry_candidate([descriptor])

    resolved = resolve_operation_flow_descriptor_candidate(
        registry,
        "reference-review-workflow-candidate",
    )

    assert registry.candidate_only is True
    assert registry.workflow_execution_enabled is False
    assert resolved == descriptor
    assert resolve_operation_flow_descriptor_candidate(registry, "missing") is None


def test_operation_flow_registry_rejects_duplicate_workflow_ids() -> None:
    descriptor = build_operation_flow_descriptor_candidate(
        workflow_id="duplicate-workflow",
        workflow_name="Duplicate workflow",
        workflow_kind="plan",
    )

    with pytest.raises(ValidationError):
        build_operation_flow_registry_candidate([descriptor, descriptor])


def test_operation_flows_root_public_surface_is_minimal() -> None:
    forbidden_root_symbols = (
        "OperationFlowDescriptorCandidate",
        "OperationFlowPlanWorkflowRequestCandidate",
        "OperationFlowWorkflowRequestDraftCandidate",
        "OPERATION_FLOW_PLAN_WORKFLOW_NAME",
        "build_operation_flow_plan_request_draft",
        "build_operation_flow_workflow_request_from_operation_flow_draft",
        "run_operation_flow_plan_workflow",
        "review_operation_flow_external_readonly_tool_design",
        "build_operation_flow_skill_projection_status_summary",
        "OperationFlowLlmInvocationFacade",
    )

    assert cognition_operation_flows.__all__ == ()
    for symbol_name in forbidden_root_symbols:
        assert not hasattr(cognition_operation_flows, symbol_name), symbol_name


def test_operation_flows_package_is_channel_neutral_and_release_configured() -> None:
    pyproject = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text())
    tool_config = pyproject["tool"]["cognition_operation_flows"]

    assert pyproject["project"]["name"] == "cognition-system-operation-flows"
    assert tool_config["status"] == "product_level_governed_operation_flows"
    assert tool_config["channel_neutral"] is True
    assert tool_config["workflow_execution_enabled"] is False
    assert tool_config["operation_flow_descriptor_candidate_enabled"] is True
    assert tool_config["operation_flow_router_candidate_enabled"] is True
    assert tool_config["operation_control_candidate_enabled"] is True
    assert tool_config["run_workspace_candidate_enabled"] is True
    assert tool_config["skill_projection_context_candidate_enabled"] is True
    assert tool_config["request_draft_candidate_enabled"] is True
    assert tool_config["runtime_container_dependency_enabled"] is False
    assert tool_config["runtime_dependency_enabled"] is True
    assert tool_config["contract_core_dependency_enabled"] is True
    assert tool_config["config_contexts_dependency_enabled"] is True
    assert tool_config["product_gateway_dependency_enabled"] is False
    assert tool_config["channel_adapter_dependency_enabled"] is False
    assert tool_config["publishable"] is True
    assert tool_config["release_configured"] is True


def test_operation_flows_in_v070_root_package_and_release_list() -> None:
    root_pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    release_script = (REPO_ROOT / "scripts" / "release_multi_package.py").read_text(
        encoding="utf-8"
    )

    assert "cognition-system-operation-flows==0.8.3" in root_pyproject[
        "project"
    ]["dependencies"]
    assert '"cognition-system-operation-flows"' in release_script
    assert '"packages/operation_flows"' in release_script


def test_external_readonly_private_subpackage_layout_and_boundaries() -> None:
    external_readonly_private_root = (
        TASK_WORKFLOWS_PACKAGE_ROOT / "_external_readonly"
    )
    expected_modules = (
        "__init__.py",
        "evidence.py",
        "network_gate.py",
        "provider_adapter.py",
        "tool_design.py",
    )
    external_boundary_roots = (
        REPO_ROOT / "packages" / "product_gateway" / "src" / "product_gateway",
        REPO_ROOT / "packages" / "cli" / "src" / "cognition_cli",
        REPO_ROOT / "packages" / "runtime_container" / "src" / "runtime_container",
        REPO_ROOT / "packages" / "composition" / "src" / "composition",
    )

    assert external_readonly_private_root.is_dir()
    assert tuple(
        sorted(
            source_path.name
            for source_path in external_readonly_private_root.glob("*.py")
        )
    ) == expected_modules
    assert tuple(TASK_WORKFLOWS_PACKAGE_ROOT.glob("operation_flow_external_readonly_*.py")) == ()
    for source_root in external_boundary_roots:
        for source_path in source_root.rglob("*.py"):
            source = source_path.read_text(encoding="utf-8")
            assert "cognition_operation_flows._external_readonly" not in source, (
                source_path,
                "cognition_operation_flows._external_readonly",
            )


def test_tools_skills_agents_private_subpackage_layout_and_boundaries() -> None:
    expected_subpackages = {
        "_tools": (
            "__init__.py",
            "exposure_profile.py",
            "loading_validation.py",
            "readonly_tool_design.py",
            "reference_reader.py",
            "toolset_admission.py",
        ),
        "_skills": (
            "__init__.py",
            "capability_projection.py",
            "projection_context.py",
            "registry_admission.py",
        ),
        "_agents": (
            "__init__.py",
            "workflow_admission.py",
            "workflow_registry_observation.py",
        ),
    }
    removed_root_modules = (
        "operation_flow_readonly_tool_design.py",
        "operation_flow_reference_reader.py",
        "operation_flow_tool_exposure_profile.py",
        "operation_flow_tool_loading_validation.py",
        "operation_flow_toolset_admission.py",
        "skill_projection_context.py",
        "operation_flow_skill_capability_projection.py",
        "operation_flow_skill_registry_admission.py",
        "operation_flow_agent_workflow_admission.py",
        "operation_flow_agent_workflow_registry_observation.py",
    )
    forbidden_private_import_markers = (
        "cognition_operation_flows._tools",
        "cognition_operation_flows._skills",
        "cognition_operation_flows._agents",
    )
    external_boundary_roots = (
        REPO_ROOT / "packages" / "product_gateway" / "src" / "product_gateway",
        REPO_ROOT / "packages" / "cli" / "src" / "cognition_cli",
        REPO_ROOT / "packages" / "runtime_container" / "src" / "runtime_container",
        REPO_ROOT / "packages" / "composition" / "src" / "composition",
    )

    for subpackage_name, expected_modules in expected_subpackages.items():
        subpackage_root = TASK_WORKFLOWS_PACKAGE_ROOT / subpackage_name
        assert subpackage_root.is_dir()
        assert tuple(
            sorted(source_path.name for source_path in subpackage_root.glob("*.py"))
        ) == expected_modules
    for module_name in removed_root_modules:
        assert not (TASK_WORKFLOWS_PACKAGE_ROOT / module_name).exists()
    for exported_name in cognition_operation_flows.__all__:
        assert "AgentWorkflow" not in exported_name
        assert not exported_name.startswith("OperationFlowAgent")
    for source_root in external_boundary_roots:
        for source_path in source_root.rglob("*.py"):
            source = source_path.read_text(encoding="utf-8")
            for marker in forbidden_private_import_markers:
                assert marker not in source, (source_path, marker)


def test_workflows_requests_core_llm_private_layout_and_boundaries() -> None:
    expected_root_modules = (
        "__init__.py",
        "product_entry_service.py",
    )
    expected_subpackages = {
        "_workflows": (
            "__init__.py",
            "config_profile_explain.py",
            "plan.py",
            "reference_review.py",
            "run_workspace_evidence_audit.py",
        ),
        "_requests": (
            "__init__.py",
            "builder.py",
            "drafts.py",
            "intent_detectors.py",
            "registry.py",
        ),
        "_core": (
            "__init__.py",
            "boundaries.py",
            "control.py",
            "descriptors.py",
            "registry.py",
            "run_workspace.py",
        ),
        "_llm": (
            "__init__.py",
            "invocation.py",
        ),
    }
    removed_root_modules = (
        "boundaries.py",
        "control.py",
        "descriptors.py",
        "intent_detectors.py",
        "registry.py",
        "run_workspace.py",
        "operation_flow_config_profile_explain_workflow.py",
        "operation_flow_llm_invocation.py",
        "operation_flow_plan_workflow.py",
        "operation_flow_reference_review_workflow.py",
        "operation_flow_registry.py",
        "operation_flow_request_builder.py",
        "operation_flow_request_drafts.py",
        "operation_flow_run_workspace_evidence_audit_workflow.py",
    )
    forbidden_private_import_markers = (
        "cognition_operation_flows._workflows",
        "cognition_operation_flows._requests",
        "cognition_operation_flows._core",
        "cognition_operation_flows._llm",
    )
    external_boundary_roots = (
        REPO_ROOT / "packages" / "product_gateway" / "src" / "product_gateway",
        REPO_ROOT / "packages" / "cli" / "src" / "cognition_cli",
        REPO_ROOT / "packages" / "runtime_container" / "src" / "runtime_container",
        REPO_ROOT / "packages" / "composition" / "src" / "composition",
    )

    assert tuple(
        sorted(
            source_path.name
            for source_path in TASK_WORKFLOWS_PACKAGE_ROOT.glob("*.py")
        )
    ) == expected_root_modules
    for subpackage_name, expected_modules in expected_subpackages.items():
        subpackage_root = TASK_WORKFLOWS_PACKAGE_ROOT / subpackage_name
        assert subpackage_root.is_dir()
        assert tuple(
            sorted(source_path.name for source_path in subpackage_root.glob("*.py"))
        ) == expected_modules
    for module_name in removed_root_modules:
        assert not (TASK_WORKFLOWS_PACKAGE_ROOT / module_name).exists()
    for source_root in external_boundary_roots:
        for source_path in source_root.rglob("*.py"):
            source = source_path.read_text(encoding="utf-8")
            for marker in forbidden_private_import_markers:
                assert marker not in source, (source_path, marker)
