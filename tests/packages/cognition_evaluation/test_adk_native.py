from __future__ import annotations

import tomllib
from pathlib import Path

from cognition_evaluation import detect_adk_native_evaluation_capability


PACKAGE_ROOT = Path(__file__).resolve().parents[3] / "packages" / "cognition_evaluation"


def test_detect_adk_native_evaluation_capability_is_safe_snapshot() -> None:
    capability = detect_adk_native_evaluation_capability()

    assert capability.module_available is True
    assert capability.agent_evaluator_available is True
    assert capability.eval_config_available is True
    assert capability.eval_metric_available is True
    assert capability.raw_object_exported is False
    assert isinstance(capability.eval_status_values, list)
    assert all(isinstance(item, str) for item in capability.optional_dependency_warnings)


def test_cognition_evaluation_package_metadata_keeps_runtime_boundary() -> None:
    pyproject = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text())
    tool_config = pyproject["tool"]["cognition_evaluation"]

    assert pyproject["project"]["name"] == "cognition-system-evaluation"
    assert tool_config["status"] == "product_level_evaluation"
    assert tool_config["adk_native_evaluation_capability_enabled"] is True
    assert tool_config["architecture_boundary_evaluation_enabled"] is True
    assert tool_config["contract_boundary_evaluation_enabled"] is True
    assert tool_config["configuration_boundary_evaluation_enabled"] is True
    assert tool_config["adk_raw_object_export_enabled"] is False
    assert tool_config["runtime_execution_enabled"] is False
    assert tool_config["governance_decision_enabled"] is False
    assert tool_config["observability_persistence_enabled"] is False
    assert tool_config["product_gateway_entry_enabled"] is False
    assert tool_config["publishable"] is True
    assert tool_config["release_configured"] is True
