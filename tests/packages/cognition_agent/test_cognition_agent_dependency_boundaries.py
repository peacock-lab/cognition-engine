from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "packages" / "cognition_agent"
SOURCE_ROOT = PACKAGE_ROOT / "src" / "cognition_agent"


def test_cognition_agent_package_is_release_dependency_without_entrypoints() -> None:
    root_pyproject = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    project_dependencies = root_pyproject["project"]["dependencies"]
    project_scripts = root_pyproject["project"].get("scripts", {})

    assert "cognition-system-cognition-agent==0.8.3" in project_dependencies
    assert "cognition_agent.entrypoints.governance_summary" not in str(
        project_scripts
    )
    assert root_pyproject["tool"]["uv"]["sources"][
        "cognition-system-cognition-agent"
    ] == {"workspace": True}

    uv_lock = REPO_ROOT / "uv.lock"
    if uv_lock.exists():
        assert "name = \"cognition-system-cognition-agent\"" in uv_lock.read_text(
            encoding="utf-8"
        )


def test_cognition_agent_source_has_no_forbidden_imports() -> None:
    forbidden_import = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:product_gateway|cognition_governance|runtime_container|"
        r"adk_adapter|composition|"
        r"runtime|observability_hub|config_assembly|config_contexts|scripts|"
        r"subprocess|google\.adk)\b",
        re.MULTILINE,
    )

    for source_path in SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_import.search(source) is None, source_path


def test_cognition_agent_source_does_not_read_configuration_center() -> None:
    forbidden_usage = re.compile(
        r"(?:config_assembly|assemble_runtime_config_payload|Path\\([\"']config[\"']\\))"
    )

    for source_path in SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_usage.search(source) is None, source_path


def test_cognition_agent_does_not_define_runtime_chat_gateway_or_tool_classes() -> None:
    forbidden_class_names = {
        "AgentRuntime",
        "ToolExecutor",
        "ChatSession",
        "LLMClient",
        "Gateway",
        "AgentAction",
        "AgentDecision",
    }
    declared_class_names: set[str] = set()

    for source_path in SOURCE_ROOT.rglob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        declared_class_names.update(
            node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        )

    assert declared_class_names.isdisjoint(forbidden_class_names)
    assert all(
        name.endswith("Candidate") or name.endswith("ViewCandidate")
        for name in declared_class_names
        if name.startswith("Agent")
    )
