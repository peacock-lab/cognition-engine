from __future__ import annotations

import importlib.metadata
import re
from pathlib import Path

import behavior_contracts.runtime as runtime_contracts


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGES_ROOT = REPO_ROOT / "packages"
ADK_ADAPTER_ROOT = PACKAGES_ROOT / "adk_adapter" / "src" / "adk_adapter"
COMPOSITION_ROOT = PACKAGES_ROOT / "composition" / "src" / "composition"
RUNTIME_CONTAINER_ROOT = (
    PACKAGES_ROOT / "runtime_container" / "src" / "runtime_container"
)
PRODUCT_GATEWAY_ROOT = PACKAGES_ROOT / "product_gateway" / "src" / "product_gateway"
COGNITION_AGENT_ROOT = PACKAGES_ROOT / "cognition_agent" / "src" / "cognition_agent"
COGNITION_GOVERNANCE_ROOT = (
    PACKAGES_ROOT / "cognition_governance" / "src" / "cognition_governance"
)
EXPECTED_GOOGLE_ADK_VERSION = "2.1.0"


def test_adk2_workflow_p0_import_path_is_google_adk_workflow() -> None:
    import google.adk.workflow as workflow
    import google.adk.runners as runners

    assert importlib.metadata.version("google-adk") == EXPECTED_GOOGLE_ADK_VERSION
    assert hasattr(workflow, "Workflow")
    assert hasattr(workflow, "BaseNode")
    assert hasattr(workflow, "START")
    assert not _module_exists("google.adk.workflows")
    assert not _module_exists("google.adk.nodes")
    assert hasattr(runners, "Runner")
    assert hasattr(runners, "RunConfig")


def test_raw_adk_workflow_runner_imports_stay_in_adapter_or_composition() -> None:
    raw_adk_import = re.compile(
        r"^\s*(?:from|import)\s+google\.adk\.(?:workflow|runners)\b",
        re.MULTILINE,
    )
    allowed_roots = (ADK_ADAPTER_ROOT, COMPOSITION_ROOT)

    for source_path in PACKAGES_ROOT.rglob("src/**/*.py"):
        source = source_path.read_text(encoding="utf-8")
        if raw_adk_import.search(source) is None:
            continue
        assert _is_relative_to_any(source_path, allowed_roots), source_path


def test_product_governance_agent_runtime_do_not_import_raw_adk() -> None:
    raw_adk_import = re.compile(
        r"^\s*(?:from|import)\s+google\.adk\b",
        re.MULTILINE,
    )
    checked_roots = (
        PRODUCT_GATEWAY_ROOT,
        COGNITION_AGENT_ROOT,
        COGNITION_GOVERNANCE_ROOT,
        RUNTIME_CONTAINER_ROOT,
    )

    for root in checked_roots:
        for source_path in root.rglob("*.py"):
            source = source_path.read_text(encoding="utf-8")
            assert raw_adk_import.search(source) is None, source_path


def test_node_runner_contract_remains_project_minimal_not_adk_scheduler_copy() -> None:
    assert runtime_contracts.NodeRunner.__name__ == "NodeRunner"
    assert runtime_contracts.NodeScheduler.__name__ == "NodeScheduler"
    assert not hasattr(runtime_contracts, "DefaultNodeScheduler")


def _module_exists(module_name: str) -> bool:
    try:
        __import__(module_name)
    except ModuleNotFoundError:
        return False
    return True


def _is_relative_to_any(path: Path, roots: tuple[Path, ...]) -> bool:
    return any(_is_relative_to(path, root) for root in roots)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
