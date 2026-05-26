from __future__ import annotations

import re
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PRODUCT_GATEWAY_ROOT = (
    REPO_ROOT / "packages" / "product_gateway" / "src" / "product_gateway"
)


def test_product_gateway_package_root_public_surface_is_minimal() -> None:
    import product_gateway

    assert product_gateway.__all__ == ()
    assert not hasattr(product_gateway, "ProductGatewayRequest")
    assert not hasattr(product_gateway, "ProductGatewayResponse")
    assert not hasattr(product_gateway, "execute_cognition_run_gateway_request")
    assert not hasattr(
        product_gateway,
        "build_product_gateway_memory_deletion_request",
    )


def test_product_gateway_package_root_does_not_export_operation_flow_surfaces() -> None:
    import product_gateway

    root_source = (PRODUCT_GATEWAY_ROOT / "__init__.py").read_text(
        encoding="utf-8"
    )
    forbidden_export_markers = (
        "ProductGatewayOperationFlow",
        "PRODUCT_GATEWAY_OPERATION_FLOW_",
        "PRODUCT_GATEWAY_REFERENCE_READER",
        "build_product_gateway_operation_flow_",
        "execute_internal_operation_flow_workflow",
        "resolve_product_gateway_operation_flow_",
        "create_product_gateway_operation_flow_",
        "write_product_gateway_operation_flow_",
        "finalize_product_gateway_operation_flow_",
        "build_cli_operation_flow_",
        "execute_cli_operation_flow_workflow",
        "persist_cli_operation_flow_status_summary",
    )
    forbidden_root_names = (
        "InternalOperationFlowRouteInput",
        "InternalOperationFlowRouteProjection",
        "InternalOperationFlowExecutionContext",
        "InternalOperationFlowExecutionInput",
        "InternalOperationFlowExecutionResult",
        "InternalOperationFlowGovernanceRefs",
        "InternalOperationFlowReferenceWorkspaceControls",
        "InternalOperationFlowToolExposureResolution",
        "build_internal_operation_flow_route_projection",
        "build_internal_operation_flow_route_request",
        "build_internal_operation_flow_execution_request",
        "build_internal_operation_flow_plan_request_draft",
        "build_internal_operation_flow_reference_review_request_draft",
        "build_internal_operation_flow_config_profile_explain_request_draft",
        "build_internal_operation_flow_run_workspace_evidence_audit_request_draft",
        "build_internal_operation_flow_run_workspace_policy",
        "build_internal_operation_flow_tools_status",
        "build_internal_operation_flow_skill_capability_projection_status",
        "execute_internal_operation_flow_workflow",
        "build_cli_operation_flow_route_projection",
        "execute_cli_operation_flow_workflow",
        "persist_cli_operation_flow_status_summary",
    )

    assert "product_gateway." + "operation_flow_" not in root_source
    assert "product_gateway.cli_surface" not in root_source
    assert "from product_gateway." not in root_source
    for exported_name in product_gateway.__all__:
        for marker in forbidden_export_markers:
            assert marker not in exported_name
    for forbidden_name in forbidden_root_names:
        assert forbidden_name not in product_gateway.__all__
        assert not hasattr(product_gateway, forbidden_name)
    assert "_operation_flows" not in root_source


def test_product_gateway_legacy_cognition_run_cli_helper_is_retired() -> None:
    legacy_cli_root = PRODUCT_GATEWAY_ROOT / "cli"

    assert not (legacy_cli_root / "cognition_run.py").exists()
    assert not (legacy_cli_root / "presenter.py").exists()
    assert not (legacy_cli_root / "__init__.py").exists()
    assert tuple(legacy_cli_root.glob("*.py")) == ()
    assert (PRODUCT_GATEWAY_ROOT / "cli_surface.py").exists()


def test_product_gateway_operation_flow_backend_lives_under_internal_namespace() -> None:
    legacy_prefix = "product_gateway." + "operation_flow_"
    legacy_backend_files = tuple(PRODUCT_GATEWAY_ROOT.glob("operation_flow_*.py"))
    internal_root = PRODUCT_GATEWAY_ROOT / "_operation_flows"
    internal_init_source = (internal_root / "__init__.py").read_text(
        encoding="utf-8"
    )

    assert legacy_backend_files == ()
    assert internal_root.is_dir()
    assert "__all__" not in internal_init_source
    assert legacy_prefix not in internal_init_source


def test_product_gateway_public_projections_do_not_use_compatibility_names() -> None:
    import product_gateway

    forbidden_class = re.compile(r"\bclass\s+\w*CompatibilityProjection\b")
    forbidden_builder = re.compile(
        r"\bdef\s+build_\w+_compatibility_projection\b"
    )

    for exported_name in product_gateway.__all__:
        assert "CompatibilityProjection" not in exported_name
        assert "compatibility_projection" not in exported_name

    for source_path in PRODUCT_GATEWAY_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_class.search(source) is None, source_path
        assert forbidden_builder.search(source) is None, source_path


def test_product_gateway_source_has_no_execution_or_provider_dependencies() -> None:
    forbidden_modules = (
        r"google\.adk|adk_adapter|litellm|"
        r"cognition_agent|cognition_governance|composition|observability_hub|"
        r"product_application_assembly|schemas\.adk_tool|behavior_contracts"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+(?:" + forbidden_modules + r")\b",
        re.MULTILINE,
    )

    for source_path in PRODUCT_GATEWAY_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path


def test_product_gateway_does_not_import_runtime_container() -> None:
    forbidden_runtime_container_import = re.compile(
        r"^\s*(?:from|import)\s+runtime_container",
        re.MULTILINE,
    )
    forbidden_runtime_container_symbols = (
        "runtime_container.controlled_adk_run_request_builder",
        "runtime_container.controlled_adk_run_entry",
        "runtime_container.entrypoints.cognition",
        "runtime_container.llm_invocation_provider_service",
        "runtime_container.workflow_registry",
        "ControlledAdkRunRequestBuildInput",
        "ControlledAdkRunRequest",
        "ControlledExecutionServiceInput",
        "ControlledRunEntryRunner",
        "ControlledRunFacadeInput",
        "ControlledRunFacadeResult",
        "build_controlled_adk_run_request_from_registry",
        "build_controlled_run_request_from_facade_input",
        "coerce_controlled_run_facade_input",
        "run_controlled_run_facade",
        "run_productized_controlled_adk_run",
    )

    for source_path in PRODUCT_GATEWAY_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_runtime_container_import.search(source) is None, source_path
        assert "controlled_live_llm_service" not in source, source_path
        for symbol in forbidden_runtime_container_symbols:
            assert symbol not in source, (source_path, symbol)


def test_product_gateway_only_imports_allowed_contract_core_surfaces() -> None:
    allowed_contract_core_import = re.compile(
        r"^\s*from\s+contract_core\."
        r"(?:controlled_execution|external_readonly_evidence|llm_invocation)"
        r"\s+import\s+",
        re.MULTILINE,
    )
    forbidden_contract_core_import = re.compile(
        r"^\s*(?:from|import)\s+contract_core"
        r"(?!(?:\.controlled_execution|\.external_readonly_evidence|"
        r"\.llm_invocation)\s+import\s+)",
        re.MULTILINE,
    )

    contract_core_imports = 0
    for source_path in PRODUCT_GATEWAY_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        contract_core_imports += len(allowed_contract_core_import.findall(source))
        assert forbidden_contract_core_import.search(source) is None, source_path

    assert contract_core_imports == 7


def test_product_gateway_external_readonly_uses_backend_api_without_runtime_container() -> None:
    source = (PRODUCT_GATEWAY_ROOT / "external_readonly.py").read_text(
        encoding="utf-8"
    )

    assert "from external_readonly import" in source
    assert "runtime_container.external_readonly" not in source
    assert "from runtime_container" not in source


def test_product_gateway_imports_only_narrow_operation_flow_services() -> None:
    allowed_operation_flow_imports = (
        re.compile(
            r"^\s*from\s+cognition_operation_flows\.product_entry_service\s+import\s+",
            re.MULTILINE,
        ),
    )
    forbidden_operation_flow_import = re.compile(
        r"^\s*(?:from|import)\s+cognition_operation_flows"
        r"(?!(?:\.product_entry_service)\s+import\s+)",
        re.MULTILINE,
    )
    forbidden_private_markers = (
        "cognition_operation_flows._product_entry",
        "cognition_operation_flows._workflows",
        "cognition_operation_flows._requests",
        "cognition_operation_flows._core",
        "cognition_operation_flows._llm",
        "cognition_operation_flows._tools",
        "cognition_operation_flows._skills",
        "cognition_operation_flows._agents",
        "cognition_operation_flows._external_readonly",
    )

    operation_flow_imports = 0
    for source_path in PRODUCT_GATEWAY_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        operation_flow_imports += sum(
            len(allowed_import.findall(source))
            for allowed_import in allowed_operation_flow_imports
        )
        assert forbidden_operation_flow_import.search(source) is None, source_path
        for marker in forbidden_private_markers:
            assert marker not in source, (source_path, marker)

    assert operation_flow_imports == 5


def test_product_gateway_operation_flow_main_chain_uses_product_entry_service_only() -> None:
    main_chain_files = (
        PRODUCT_GATEWAY_ROOT / "_operation_flows" / "route.py",
        PRODUCT_GATEWAY_ROOT / "_operation_flows" / "request.py",
        PRODUCT_GATEWAY_ROOT / "_operation_flows" / "execution.py",
    )
    product_entry_import = re.compile(
        r"^\s*from\s+cognition_operation_flows\.product_entry_service\s+import\s+",
        re.MULTILINE,
    )
    forbidden_main_chain_import = re.compile(
        r"^\s*(?:from|import)\s+cognition_operation_flows"
        r"(?!(?:\.product_entry_service)\s+import\s+)",
        re.MULTILINE,
    )

    for source_path in main_chain_files:
        source = source_path.read_text(encoding="utf-8")
        assert product_entry_import.search(source) is not None, source_path
        assert forbidden_main_chain_import.search(source) is None, source_path


def test_product_gateway_declares_operation_flows_dependency() -> None:
    pyproject = tomllib.loads(
        (REPO_ROOT / "packages" / "product_gateway" / "pyproject.toml").read_text()
    )

    assert "cognition-system-operation-flows==0.8.3" in pyproject["project"][
        "dependencies"
    ]
    assert "cognition-system-runtime-container==0.8.3" not in pyproject["project"][
        "dependencies"
    ]
    assert "cognition-system-runtime-container" not in pyproject["tool"]["uv"][
        "sources"
    ]
    assert "cognition-system-composition==0.8.3" not in pyproject["project"][
        "dependencies"
    ]
    assert "cognition-system-composition" not in pyproject["tool"]["uv"]["sources"]
    assert "cognition-system-config-assembly==0.8.3" not in pyproject["project"][
        "dependencies"
    ]
    assert "cognition-system-config-contexts==0.8.3" in pyproject["project"][
        "dependencies"
    ]
    assert "cognition-system-config-assembly" not in pyproject["tool"]["uv"]["sources"]
    assert "cognition-system-config-contexts" in pyproject["tool"]["uv"]["sources"]


def test_product_gateway_source_does_not_read_config_or_execute_runtime() -> None:
    forbidden_patterns = (
        "config/",
        "Path(\"config",
        "Path('config",
        "config_assembly",
        "assemble_runtime_config_payload",
        "build_runtime_config_contexts",
        "open(",
        "read_text(",
        "runtime_container.entrypoints.cognition",
        "run_productized_controlled_adk_run",
    )

    for source_path in PRODUCT_GATEWAY_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            # The bridge may read a governed evidence archive; config/runtime reads
            # remain covered by the explicit forbidden markers above.
            if (
                pattern == "read_text("
                and source_path.name == "external_readonly_ask_bridge.py"
            ):
                continue
            assert pattern not in source, (source_path, pattern)
