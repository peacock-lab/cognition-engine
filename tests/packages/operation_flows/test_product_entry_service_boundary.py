from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import cognition_operation_flows.product_entry_service as product_entry_service
from cognition_operation_flows.product_entry_service import (
    OPERATION_FLOW_PRODUCT_ENTRY_CONFIG_PROFILE_EXPLAIN_FLOW_NAME,
    OPERATION_FLOW_PRODUCT_ENTRY_PLAN_FLOW_NAME,
    OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_READER_TOOL_NAME,
    OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_REVIEW_FLOW_NAME,
    OPERATION_FLOW_PRODUCT_ENTRY_RUN_WORKSPACE_EVIDENCE_AUDIT_FLOW_NAME,
    build_operation_flow_product_entry_config_profile_explain_request_draft,
    build_operation_flow_product_entry_plan_request_draft,
    build_operation_flow_product_entry_reference_review_request_draft,
    build_operation_flow_product_entry_run_workspace_policy,
    build_operation_flow_product_entry_run_workspace_evidence_audit_request_draft,
    build_operation_flow_product_entry_skill_capability_projection_status,
    build_operation_flow_product_entry_tools_status,
    build_operation_flow_product_entry_request,
    create_operation_flow_product_entry_run_workspace,
    extract_operation_flow_product_entry_external_readonly_evidence_context,
    finalize_operation_flow_product_entry_run_workspace,
    get_operation_flow_product_entry_default_model_name,
    get_operation_flow_product_entry_result_display_text,
    resolve_operation_flow_product_entry_tool_exposure_profile,
    restore_operation_flow_product_entry_run_workspace_snapshot,
    route_operation_flow_product_entry_turn,
    run_operation_flow_product_entry,
    operation_flow_product_entry_result_updates_latest_plan,
    write_operation_flow_product_entry_run_workspace_json,
    write_operation_flow_product_entry_run_workspace_text,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
PRODUCT_ENTRY_SERVICE_PATH = (
    REPO_ROOT
    / "packages"
    / "operation_flows"
    / "src"
    / "cognition_operation_flows"
    / "product_entry_service.py"
)
PRODUCT_ENTRY_PACKAGE_ROOT = PRODUCT_ENTRY_SERVICE_PATH.parent
PRODUCT_ENTRY_PRIVATE_PACKAGE_PATH = (
    PRODUCT_ENTRY_PACKAGE_ROOT / "_product_entry"
)
PRODUCT_ENTRY_EXTERNAL_READONLY_REFS_PATH = (
    PRODUCT_ENTRY_PRIVATE_PACKAGE_PATH / "external_readonly_refs.py"
)
PRODUCT_ENTRY_PRIVATE_MODULE_PATHS = tuple(
    sorted(
        source_path
        for source_path in PRODUCT_ENTRY_PRIVATE_PACKAGE_PATH.glob("*.py")
        if source_path.name != "__init__.py"
    )
)
PRODUCT_ENTRY_MODULE_PATHS = (
    PRODUCT_ENTRY_SERVICE_PATH,
    PRODUCT_ENTRY_PRIVATE_PACKAGE_PATH / "__init__.py",
    *PRODUCT_ENTRY_PRIVATE_MODULE_PATHS,
)

EXPECTED_PRODUCT_ENTRY_PUBLIC_SYMBOLS = (
    "OPERATION_FLOW_PRODUCT_ENTRY_CONFIG_PROFILE_EXPLAIN_FLOW_NAME",
    "OPERATION_FLOW_PRODUCT_ENTRY_PLAN_FLOW_NAME",
    "OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_READER_FORBIDDEN_PATH_MARKERS",
    "OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_READER_FORBIDDEN_SEGMENTS",
    "OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_READER_TOOL_NAME",
    "OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_REVIEW_FLOW_NAME",
    "OPERATION_FLOW_PRODUCT_ENTRY_RUN_WORKSPACE_EVIDENCE_AUDIT_FLOW_NAME",
    "OperationFlowProductEntryReferenceReaderPolicyCandidate",
    "OperationFlowProductEntryRouteResultCandidate",
    "OperationFlowProductEntryToolExposureResolutionCandidate",
    "build_operation_flow_product_entry_config_profile_explain_request_draft",
    "build_operation_flow_product_entry_plan_request_draft",
    "build_operation_flow_product_entry_reference_review_request_draft",
    "build_operation_flow_product_entry_run_workspace_evidence_audit_request_draft",
    "build_operation_flow_product_entry_run_workspace_policy",
    "build_operation_flow_product_entry_skill_capability_projection_status",
    "build_operation_flow_product_entry_tools_status",
    "build_operation_flow_product_entry_request",
    "create_operation_flow_product_entry_run_workspace",
    "extract_operation_flow_product_entry_external_readonly_evidence_context",
    "finalize_operation_flow_product_entry_run_workspace",
    "get_operation_flow_product_entry_default_model_name",
    "get_operation_flow_product_entry_result_display_text",
    "route_operation_flow_product_entry_turn",
    "restore_operation_flow_product_entry_run_workspace_snapshot",
    "resolve_operation_flow_product_entry_tool_exposure_profile",
    "run_operation_flow_product_entry",
    "operation_flow_product_entry_result_updates_latest_plan",
    "write_operation_flow_product_entry_run_workspace_json",
    "write_operation_flow_product_entry_run_workspace_text",
)


@dataclass(frozen=True)
class ProductEntryRefsFixture:
    approval_ref: str | None = "approval://product-entry/test"
    audit_ref: str | None = "audit://product-entry/test"
    sanitized_evidence_ref: str | None = "evidence://product-entry/test"
    governance_summary_output_ref: str | None = "artifact://product-entry/test"
    live_llm_approval_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProductEntryControlsFixture:
    reference_paths: tuple[str, ...] = ("tasks/b1/example.md",)
    reference_repo_root: str | None = "/repo"
    external_readonly_evidence_paths: tuple[str, ...] = ()
    external_readonly_evidence_repo_root: str | None = None
    reference_profile_name: str | None = "readonly_reference"
    tool_exposure_profile: str | None = "readonly_reference"
    run_workspace_root: str | None = "/tmp/operation_flow-product-entry"
    run_workspace_enabled: bool = True
    run_workspace_retention_policy: str | None = "keep"
    run_workspace_cleanup_policy: str | None = "manual"
    run_workspace_max_write_bytes: int | None = 4096
    audit_run_workspace_path: str | None = None
    audit_run_workspace_ref: str | None = None
    audit_run_workspace_root: str | None = None
    audit_focus: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


def test_product_entry_service_has_no_reverse_product_or_runtime_imports() -> None:
    forbidden_import_markers = (
        "from product_gateway",
        "import product_gateway",
        "from runtime_container",
        "import runtime_container",
        "from composition",
        "import composition",
        "from cognition_cli",
        "import cognition_cli",
        "from observability_hub",
        "import observability_hub",
        "from behavior_contracts",
        "import behavior_contracts",
    )

    assert PRODUCT_ENTRY_PRIVATE_PACKAGE_PATH.is_dir()
    assert PRODUCT_ENTRY_PRIVATE_MODULE_PATHS
    assert tuple(PRODUCT_ENTRY_PACKAGE_ROOT.glob("_product_entry_*.py")) == ()
    for source_path in PRODUCT_ENTRY_MODULE_PATHS:
        source = source_path.read_text(encoding="utf-8")
        for marker in forbidden_import_markers:
            assert marker not in source, (source_path, marker)


def test_product_entry_service_keeps_canonical_public_symbols() -> None:
    assert len(product_entry_service.__all__) == 30
    assert tuple(product_entry_service.__all__) == (
        EXPECTED_PRODUCT_ENTRY_PUBLIC_SYMBOLS
    )
    for symbol_name in EXPECTED_PRODUCT_ENTRY_PUBLIC_SYMBOLS:
        assert hasattr(product_entry_service, symbol_name)


def test_product_entry_external_readonly_context_returns_none_without_context() -> None:
    workflow_result = SimpleNamespace(
        reference_context=SimpleNamespace(metadata={})
    )

    assert extract_operation_flow_product_entry_external_readonly_evidence_context(
        workflow_result
    ) is None


def test_product_entry_external_readonly_context_extractor_returns_context() -> None:
    context = {
        "status": "ready",
        "reference_review_ready": True,
        "evidence_output_paths": (
            "outputs/external-readonly/cli-fetch/example.json",
        ),
        "evidence_refs": (
            "evidence://external-readonly/cli-fetch/example.json",
        ),
        "source_urls": ("https://example.com/",),
        "blocking_reasons": (),
        "warnings": ("reference_review_ready",),
        "summaries": (
            {
                "sanitized_excerpt_preview": "workflow-local excerpt",
                "raw_response_included": False,
                "raw_html_included": False,
                "response_headers_included": False,
            },
        ),
        "metadata": {"source": "unit-test"},
    }
    workflow_result = SimpleNamespace(
        reference_context=SimpleNamespace(
            metadata={"external_readonly_evidence_context": context}
        )
    )

    extracted = extract_operation_flow_product_entry_external_readonly_evidence_context(
        workflow_result
    )

    assert extracted is context
    assert extracted["status"] == "ready"
    assert extracted["evidence_refs"] == (
        "evidence://external-readonly/cli-fetch/example.json",
    )
    assert extracted["summaries"] == context["summaries"]


def test_product_entry_external_readonly_context_extractor_has_no_mapping_policy() -> None:
    source = PRODUCT_ENTRY_EXTERNAL_READONLY_REFS_PATH.read_text(
        encoding="utf-8"
    )

    assert (
        "extract_operation_flow_product_entry_external_readonly_evidence_context"
        in source
    )
    assert "external_readonly_evidence_context" in source
    forbidden_mapper_markers = (
        "contract_core.external_readonly_evidence",
        "build_external_readonly_evidence_readonly_public_refs_from_read_context",
        "external_readonly_evidence_readonly_public_refs_status_dict",
        "build_operation_flow_product_entry_"
        "external_readonly_refs_status",
        "build_external_readonly_evidence_readonly_facts",
        "build_external_readonly_evidence_readonly_public_refs(",
        "def _candidate_count",
        "def _metadata_keys",
        "def _raw_boundary_flags",
        "_FORBIDDEN_METADATA_KEY_MARKERS",
    )
    for marker in forbidden_mapper_markers:
        assert marker not in source


def test_product_entry_service_routes_product_entry_turn() -> None:
    result = route_operation_flow_product_entry_turn(
        sanitized_user_text="我要建一个鱼塘，500平米大，请帮我设计建设方案",
        chat_session_id="session-product-entry-service",
        turn_index=1,
        run_workspace_requested=True,
        source="test_product_entry_service",
    )

    assert result.route.matched is True
    assert result.route.workflow_name == OPERATION_FLOW_PRODUCT_ENTRY_PLAN_FLOW_NAME
    assert result.route.task_kind == "plan_design"
    assert result.route.requires_workspace is True
    assert result.registry_workflow_count == 4
    assert OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_REVIEW_FLOW_NAME in (
        result.registry_workflow_names
    )
    assert result.route_status["workflow_name"] == OPERATION_FLOW_PRODUCT_ENTRY_PLAN_FLOW_NAME


def test_product_entry_service_builds_all_request_drafts_from_entry_objects() -> None:
    refs = ProductEntryRefsFixture()
    controls = ProductEntryControlsFixture()

    plan = build_operation_flow_product_entry_plan_request_draft(
        sanitized_user_text="我要建一个鱼塘，请给建设方案",
        governance_refs=refs,
        controls=controls,
        route_summary={"matched": True},
    )
    reference_review = build_operation_flow_product_entry_reference_review_request_draft(
        sanitized_user_text="请审查这些资料",
        governance_refs=refs,
        controls=controls,
    )
    config_profile = build_operation_flow_product_entry_config_profile_explain_request_draft(
        sanitized_user_text="请解释当前配置为什么这样生效",
        governance_refs=refs,
        controls=controls,
        entrypoint_explicit_args={"profile": "local-live"},
        session_args={"environment": "local"},
    )
    evidence_audit = (
        build_operation_flow_product_entry_run_workspace_evidence_audit_request_draft(
            sanitized_user_text="请审计 run workspace",
            governance_refs=refs,
            controls=ProductEntryControlsFixture(
                audit_run_workspace_path="/tmp/operation_flow-product-entry/run",
                audit_run_workspace_root="/tmp/operation_flow-product-entry",
                audit_focus=("manifest", "results"),
            ),
        )
    )

    assert plan.workflow_name == OPERATION_FLOW_PRODUCT_ENTRY_PLAN_FLOW_NAME
    assert reference_review.workflow_name == (
        OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_REVIEW_FLOW_NAME
    )
    assert config_profile.workflow_name == (
        OPERATION_FLOW_PRODUCT_ENTRY_CONFIG_PROFILE_EXPLAIN_FLOW_NAME
    )
    assert evidence_audit.workflow_name == (
        OPERATION_FLOW_PRODUCT_ENTRY_RUN_WORKSPACE_EVIDENCE_AUDIT_FLOW_NAME
    )
    assert plan.governance_refs.approval_ref == "approval://product-entry/test"
    assert plan.controls.reference_paths == ("tasks/b1/example.md",)
    assert evidence_audit.controls.audit_focus == ("manifest", "results")


def test_product_entry_service_builds_workflow_request_and_result_helpers() -> None:
    draft = build_operation_flow_product_entry_plan_request_draft(
        sanitized_user_text="我要建一个鱼塘，请给建设方案",
        governance_refs={"approval_ref": "approval://product-entry/request"},
        controls={"reference_paths": ("tasks/b1/example.md",)},
    )

    request = build_operation_flow_product_entry_request(
        draft,
        model_name=get_operation_flow_product_entry_default_model_name(),
    )

    assert request.user_text == "我要建一个鱼塘，请给建设方案"
    assert request.reference_paths == ("tasks/b1/example.md",)
    assert request.approval_ref == "approval://product-entry/request"
    assert get_operation_flow_product_entry_result_display_text(object()) == ""
    assert operation_flow_product_entry_result_updates_latest_plan(object()) is False


def test_product_entry_service_resolves_tools_and_skill_projection_status(
    tmp_path: Path,
) -> None:
    resolution = resolve_operation_flow_product_entry_tool_exposure_profile(
        profile_name="readonly_reference",
        repo_root=tmp_path,
        entrypoint_explicit_args={},
    )
    tools_status = build_operation_flow_product_entry_tools_status(
        profile_name="readonly_reference",
        profile_config=None,
        repo_root=str(tmp_path),
        entrypoint_explicit_args={},
        operator_approved=False,
        approval_ref=None,
    )
    skill_status = build_operation_flow_product_entry_skill_capability_projection_status()

    assert resolution.status == "resolved"
    assert OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_READER_TOOL_NAME in (
        resolution.exposed_tool_names
    )
    assert resolution.reference_reader_policy is not None
    assert tools_status["profile_name"] == "readonly_reference"
    assert tools_status["reference_reader_status"] == "enabled"
    assert OPERATION_FLOW_PRODUCT_ENTRY_REFERENCE_READER_TOOL_NAME in (
        tools_status["loading_allowed_tool_names"]
    )
    assert skill_status["runtime_enabled"] is False
    assert skill_status["skill_file_loading_enabled"] is False


def test_product_entry_service_run_workspace_roundtrip(tmp_path: Path) -> None:
    policy = build_operation_flow_product_entry_run_workspace_policy(
        workspace_root=tmp_path,
        retention_policy="keep",
        cleanup_policy="manual",
        max_write_bytes=4096,
    )
    workspace = create_operation_flow_product_entry_run_workspace(
        policy=policy,
        workflow_name=OPERATION_FLOW_PRODUCT_ENTRY_PLAN_FLOW_NAME,
        run_id="product-entry-run",
    )
    workspace, artifact_write = write_operation_flow_product_entry_run_workspace_json(
        workspace,
        relative_path="artifacts/status.json",
        payload={"ok": True},
        kind="artifact",
        max_write_bytes=4096,
    )
    workspace, result_write = write_operation_flow_product_entry_run_workspace_text(
        workspace,
        relative_path="results/result.txt",
        text="done",
        kind="result",
        max_write_bytes=4096,
    )
    finalized = finalize_operation_flow_product_entry_run_workspace(
        workspace,
        status="succeeded",
        metadata={"source": "test_product_entry_service"},
    )
    restored = restore_operation_flow_product_entry_run_workspace_snapshot(
        {
            "workspace_ref": finalized.workspace_ref,
            "workspace_path": finalized.workspace_path,
            "workflow_name": finalized.workflow_name,
            "run_id": finalized.run_id,
            "workspace_created": finalized.workspace_created,
            "retention_policy": finalized.retention_policy,
            "cleanup_policy": finalized.cleanup_policy,
            "manifest_path": finalized.manifest_path,
            "subdirs": finalized.subdirs,
            "artifact_refs": finalized.artifact_refs,
            "evidence_refs": finalized.evidence_refs,
            "result_refs": finalized.result_refs,
            "cleanup_performed": finalized.cleanup_performed,
            "blocking_reasons": finalized.blocking_reasons,
            "warnings": finalized.warnings,
            "metadata": finalized.metadata,
        }
    )

    assert workspace.workspace_created is True
    assert artifact_write.status == "succeeded"
    assert result_write.status == "succeeded"
    assert artifact_write.ref in finalized.artifact_refs
    assert result_write.ref in finalized.result_refs
    assert restored.workspace_ref == finalized.workspace_ref
    assert restored.metadata["source"] == "test_product_entry_service"


def test_product_entry_service_rejects_unknown_workflow_run() -> None:
    with pytest.raises(ValueError, match="unsupported OperationFlow workflow"):
        run_operation_flow_product_entry("unknown_operation_flow_workflow", object())
