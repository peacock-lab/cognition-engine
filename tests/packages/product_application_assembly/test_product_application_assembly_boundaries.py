from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import product_application_assembly


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = (
    REPO_ROOT
    / "packages"
    / "product_application_assembly"
    / "src"
    / "product_application_assembly"
)
PYPROJECT_PATH = (
    REPO_ROOT / "packages" / "product_application_assembly" / "pyproject.toml"
)


def test_product_application_assembly_public_surface_is_narrow() -> None:
    assert product_application_assembly.__all__ == (
        "ExternalReadonlyRefsProductApplicationAssemblyResult",
        "EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_INTERACTION_MODE",
        "EVIDENCE_SUMMARY_ANSWER_GENERATION_INTERACTION_MODE",
        "PRODUCT_APPLICATION_ASSEMBLY_PACKAGE",
        "PRODUCT_APPLICATION_ASSEMBLY_STATUS",
        "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_ANSWER_POLICY_REF",
        "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_CITATION_POLICY_REF",
        "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_SOURCE",
        "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ARTIFACT_POLICY_REF",
        "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ARTIFACT_SOURCE",
        "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ANSWERABILITY_PREFLIGHT_POLICY_REF",
        "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_POLICY_REF",
        "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_SOURCE",
        "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_GENERATED_RESULT_POLICY_REF",
        "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_GENERATION_SOURCE",
        "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_LLM_REQUEST_POLICY_REF",
        "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_POLICY_REF",
        "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_SOURCE",
        "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_TRACE_POLICY_REF",
        "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_TRACE_SOURCE",
        "PRODUCT_APPLICATION_GOVERNED_EVIDENCE_DIGEST_POLICY_REF",
        "PRODUCT_APPLICATION_GOVERNED_EVIDENCE_DIGEST_SOURCE",
        "assemble_external_readonly_refs_product_application",
        "build_evidence_summary_answer_artifact",
        "build_evidence_summary_answer_context",
        "build_evidence_summary_answer_answerability_preflight_result",
        "build_evidence_summary_answer_follow_up_context",
        "build_evidence_summary_answer_follow_up_seed",
        "build_evidence_summary_answer_llm_invocation_request",
        "build_evidence_summary_answer_result_from_llm_invocation_result",
        "build_evidence_summary_answer_trace",
        "build_governed_evidence_digest_from_external_readonly_facts",
        "build_no_model_evidence_summary_answer_result",
        "evidence_summary_answer_context_status_dict",
        "evidence_summary_answer_artifact_status_dict",
        "evidence_summary_answer_artifact_summary_dict",
        "evidence_summary_answer_follow_up_seed_status_dict",
        "evidence_summary_answer_result_status_dict",
        "evidence_summary_answer_trace_status_dict",
        "evidence_summary_answer_trace_summary_dict",
        "governed_evidence_digest_status_dict",
    )
    assert not hasattr(product_application_assembly, "ProductGatewayResponse")
    assert not hasattr(product_application_assembly, "ProductGatewayRequest")


def test_product_application_assembly_pyproject_declares_distribution() -> None:
    project = _pyproject()["project"]

    assert project["name"] == "cognition-system-product-application-assembly"
    assert project["version"] == "0.8.0"


def test_product_application_assembly_pyproject_dependencies_are_bounded() -> None:
    dependencies = tuple(
        dependency
        for dependency in _pyproject()["project"]["dependencies"]
        if dependency.startswith("cognition-system-")
    )

    assert dependencies == (
        "cognition-system-behavior-contracts==0.8.0",
        "cognition-system-composition==0.8.0",
        "cognition-system-product-gateway==0.8.0",
        "cognition-system-schemas==0.8.0",
    )
    dependency_names = tuple(
        dependency.split("==", maxsplit=1)[0] for dependency in dependencies
    )
    for forbidden in (
        "cognition-system-observability-hub",
        "cognition-system-runtime-container",
        "cognition-system-runtime",
        "cognition-system-adk-adapter",
        "cognition-system-cli",
        "cognition-system-contract-core",
        "cognition-system-external-readonly",
        "cognition-system-operation-flows",
        "cognition-system-product-runtime-assembly",
    ):
        assert forbidden not in dependency_names


def test_product_application_assembly_source_has_no_forbidden_imports() -> None:
    for source_path in PACKAGE_ROOT.rglob("*.py"):
        for imported_module in _absolute_imports(source_path):
            for forbidden_prefix in _forbidden_import_prefixes():
                assert not _matches_module_prefix(
                    imported_module,
                    forbidden_prefix,
                ), (source_path, imported_module)


def test_product_application_assembly_source_has_no_execution_or_config_reads() -> None:
    forbidden_markers = (
        "open(",
        "read_text(",
        "requests",
        "httpx",
        "run_external_readonly_url_fetch",
        "." + "invoke" + "(",
        "completion" + "(",
        "acompletion" + "(",
        "runner" + "." + "run",
        "run" + "_async",
        "config/",
        "Path(",
    )

    for source_path in PACKAGE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        for marker in forbidden_markers:
            assert marker not in source, (source_path, marker)
        assert "product_gateway" + "." + "contracts" not in source
        assert "product_gateway" + "." + "response_summary_projection" not in source
        assert "product_gateway" + "." + "_operation_flows" not in source


def _forbidden_import_prefixes() -> tuple[str, ...]:
    return (
        "observability_hub",
        "runtime_container",
        "runtime",
        "adk_adapter",
        "google" + "." + "adk",
        "lite" + "llm",
        "cognition_cli",
        "cognition_operation_flows",
        "external_readonly",
        "contract_core",
        "product_runtime_assembly",
        "product_gateway" + "." + "contracts",
        "product_gateway" + "." + "response_summary_projection",
        "product_gateway" + "." + "external_readonly_refs_projection",
        "product_gateway" + "." + "_operation_flows",
    )


def _absolute_imports(source_path: Path) -> tuple[str, ...]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.append(node.module)
    return tuple(imports)


def _matches_module_prefix(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(f"{prefix}.")


def _pyproject() -> dict:
    return tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
