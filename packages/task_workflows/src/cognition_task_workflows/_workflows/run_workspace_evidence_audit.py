"""task run workspace evidence audit workflow."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any

from cognition_task_workflows._core.run_workspace import (
    TWF_RUN_WORKSPACE_SCHEMA_VERSION,
    TWF_RUN_WORKSPACE_SUBDIRS,
    TwfRunWorkspaceStateCandidate,
    build_twf_run_workspace_policy,
    cleanup_twf_run_workspace,
    twf_run_workspace_status_dict,
    create_twf_run_workspace,
    finalize_twf_run_workspace,
    write_twf_run_workspace_json,
    write_twf_run_workspace_text,
)
from cognition_task_workflows._core.control import (
    TwfRunContextCandidate,
    build_twf_run_context,
    twf_run_context_status_dict,
    finalize_twf_run_context,
)


TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME = (
    "twf_run_workspace_evidence_audit_workflow"
)
TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_TASK_KIND = "run_workspace_evidence_audit"
TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_TEMPLATE_VERSION = (
    "run_workspace_evidence_audit_template_v1"
)
RUN_WORKSPACE_EVIDENCE_AUDIT_DISPLAY_PREVIEW_LIMIT = 4000
AUDIT_REF_PATTERN = re.compile(r"^run-workspace://([a-z0-9-]+)/([a-z0-9-]+)$")
AUDIT_WORKSPACE_KEYWORDS = (
    "审计 run workspace",
    "审计 workspace",
    "检查运行工作区",
    "运行工作区证据",
    "证据完整",
    "证据链",
    "manifest 是否完整",
    "结果文件齐",
    "workspace evidence",
    "evidence audit",
    "run workspace audit",
)
AUDIT_FOCUS_DEFAULTS = ("manifest", "results", "evidence", "artifacts", "boundaries")
AUDIT_FORBIDDEN_PATH_MARKERS = (
    ".env",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "api_key",
    "credential",
    "id_dsa",
    "id_ed25519",
    "id_rsa",
    "password",
    "private_key",
    "secret",
    "service_account",
    "token",
)
AUDIT_FORBIDDEN_JSON_KEYS = (
    "secret",
    "token",
    "credential",
    "raw_response",
    "raw_provider_response",
    "messages",
    "prompt",
    "response_text",
    "live_model_payload",
)
AUDIT_FORBIDDEN_TEXT_MARKERS = (
    "raw_provider_response",
    "raw_response",
    "live_model_payload",
    "artifact_content",
    "messages",
    "response_text",
)
AUDIT_MANIFEST_MAX_BYTES = 65536
AUDIT_JSON_MAX_BYTES = 65536
AUDIT_TERMINAL_SCAN_MAX_BYTES = 8192


@dataclass(frozen=True)
class TwfRunWorkspaceEvidenceAuditWorkflowRequestCandidate:
    """Request entering the run workspace evidence audit workflow."""

    user_text: str
    chat_session_id: str | None = None
    turn_index: int | None = None
    history: tuple[Mapping[str, str], ...] = ()
    audit_run_workspace_path: str | Path | None = None
    audit_run_workspace_ref: str | None = None
    audit_run_workspace_root: str | Path | None = None
    audit_focus: tuple[str, ...] = ()
    approval_ref: str | None = None
    audit_ref: str | None = None
    sanitized_evidence_ref: str | None = None
    risk_level: str = "low"
    output_budget: int | None = RUN_WORKSPACE_EVIDENCE_AUDIT_DISPLAY_PREVIEW_LIMIT
    live_gate: str | None = "no_live"
    user_passthrough_parameters: Mapping[str, Any] = field(default_factory=dict)
    run_workspace_root: str | None = None
    run_workspace_enabled: bool = False
    run_workspace_retention_policy: str = "keep"
    run_workspace_cleanup_policy: str = "manual"
    run_workspace_max_write_bytes: int = 65536
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfRunWorkspaceEvidenceAuditFactsCandidate:
    """Minimal audit intent facts."""

    original_text: str
    task_kind: str
    matched_terms: tuple[str, ...] = ()
    audit_focus: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfRunWorkspaceAuditTargetCandidate:
    """Resolved audited run workspace target."""

    status: str
    workspace_path: str | None = None
    workspace_ref: str | None = None
    workflow_name: str | None = None
    run_id: str | None = None
    manifest_path: str | None = None
    manifest: Mapping[str, Any] = field(default_factory=dict)
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfRunWorkspaceAuditFileCandidate:
    """One audited workspace file observation."""

    kind: str
    relative_path: str
    exists: bool
    bytes: int | None = None
    ref: str | None = None
    json_valid: bool | None = None
    forbidden_markers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfRunWorkspaceAuditFindingCandidate:
    """One sanitized audit finding."""

    severity: str
    code: str
    message: str
    file_ref: str | None = None
    recommendation: str | None = None


@dataclass(frozen=True)
class TwfRunWorkspaceEvidenceAuditContextCandidate:
    """Sanitized run workspace evidence audit context."""

    status: str
    audit_result: str
    target: TwfRunWorkspaceAuditTargetCandidate
    files: tuple[TwfRunWorkspaceAuditFileCandidate, ...]
    findings: tuple[TwfRunWorkspaceAuditFindingCandidate, ...]
    structure_checks: dict[str, Any]
    reference_checks: dict[str, Any]
    boundary_checks: dict[str, Any]
    risk_boundaries: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfRunWorkspaceEvidenceAuditWorkflowResultCandidate:
    """Final run workspace evidence audit workflow result."""

    triggered: bool
    terminal_display_text: str
    request: TwfRunWorkspaceEvidenceAuditWorkflowRequestCandidate
    facts: TwfRunWorkspaceEvidenceAuditFactsCandidate
    audit_context: TwfRunWorkspaceEvidenceAuditContextCandidate
    model_call_count: int = 0
    no_live: bool = True
    fail_safe: bool = False
    task_run_context: TwfRunContextCandidate | None = None
    run_workspace: TwfRunWorkspaceStateCandidate | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def detect_twf_run_workspace_evidence_audit_request(
    user_text: str,
    *,
    audit_target_requested: bool = False,
) -> bool:
    """Return whether a turn should route to run workspace evidence audit."""

    normalized = _compact_text(user_text)
    if not normalized or not audit_target_requested:
        return False
    lowered = normalized.lower()
    return any(keyword.lower() in lowered for keyword in AUDIT_WORKSPACE_KEYWORDS)


def extract_twf_run_workspace_evidence_audit_facts(
    request: TwfRunWorkspaceEvidenceAuditWorkflowRequestCandidate,
) -> TwfRunWorkspaceEvidenceAuditFactsCandidate:
    """Extract bounded run workspace audit intent facts."""

    normalized = _compact_text(request.user_text)
    lowered = normalized.lower()
    matched_terms = tuple(
        keyword
        for keyword in AUDIT_WORKSPACE_KEYWORDS
        if keyword.lower() in lowered
    )
    return TwfRunWorkspaceEvidenceAuditFactsCandidate(
        original_text=request.user_text,
        task_kind=TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_TASK_KIND,
        matched_terms=matched_terms,
        audit_focus=tuple(_ordered_unique(request.audit_focus or AUDIT_FOCUS_DEFAULTS)),
        metadata={
            "workflow_stage": "intent_extraction",
            "audit_target_requested": _audit_target_requested(request),
        },
    )


def run_twf_run_workspace_evidence_audit_workflow(
    request: TwfRunWorkspaceEvidenceAuditWorkflowRequestCandidate,
) -> TwfRunWorkspaceEvidenceAuditWorkflowResultCandidate:
    """Run the governed run workspace evidence audit workflow."""

    facts = extract_twf_run_workspace_evidence_audit_facts(request)
    task_context = _build_evidence_audit_task_context(request, facts)
    if not task_context.preflight.allowed:
        task_context = finalize_twf_run_context(
            task_context,
            status="blocked",
            metadata={"blocked_before_workspace_audit": True},
        )
        target = TwfRunWorkspaceAuditTargetCandidate(
            status="not_started",
            blocking_reasons=task_context.preflight.blocking_reasons,
            warnings=task_context.preflight.warnings,
        )
        audit_context = _audit_context_from_blocked_target(target)
        return TwfRunWorkspaceEvidenceAuditWorkflowResultCandidate(
            triggered=True,
            terminal_display_text=_preflight_blocked_terminal_display(task_context),
            request=request,
            facts=facts,
            audit_context=audit_context,
            fail_safe=True,
            task_run_context=task_context,
            metadata={
                "workflow": TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
                **_task_context_metadata(task_context),
            },
        )

    target = resolve_twf_run_workspace_audit_target(request)
    audit_context = build_twf_run_workspace_evidence_audit_context(request, facts, target)
    display = format_twf_run_workspace_evidence_audit_for_terminal(audit_context)
    run_workspace = _create_audit_output_run_workspace(request, task_context, target)
    if run_workspace is not None and not run_workspace.workspace_created:
        task_context = _finalize_task_context_with_run_workspace(
            task_context,
            status="blocked",
            run_workspace=run_workspace,
            metadata={
                "blocked_before_workspace_audit_result_write": True,
                "failure_stage": "run_workspace",
            },
        )
        return TwfRunWorkspaceEvidenceAuditWorkflowResultCandidate(
            triggered=True,
            terminal_display_text=_workspace_blocked_terminal_display(
                task_context,
                run_workspace,
            ),
            request=request,
            facts=facts,
            audit_context=audit_context,
            fail_safe=True,
            task_run_context=task_context,
            run_workspace=run_workspace,
            metadata={
                "workflow": TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
                **_task_context_metadata(task_context),
                **_run_workspace_metadata(run_workspace),
            },
        )

    workflow_status = audit_context.status
    run_workspace = _finalize_evidence_audit_run_workspace(
        run_workspace,
        status=workflow_status,
        terminal_display_text=display,
        facts=facts,
        audit_context=audit_context,
    )
    task_context = finalize_twf_run_context(
        task_context,
        status=workflow_status,
        evidence_refs=run_workspace.evidence_refs if run_workspace else (),
        artifact_refs=_run_workspace_artifact_and_result_refs(run_workspace),
        workspace_ref=run_workspace.workspace_ref if run_workspace else None,
        workspace_created=run_workspace.workspace_created if run_workspace else None,
        retention_policy=run_workspace.retention_policy if run_workspace else None,
        cleanup_policy=run_workspace.cleanup_policy if run_workspace else None,
        workspace_metadata=twf_run_workspace_status_dict(run_workspace),
        metadata={
            "audit_result": audit_context.audit_result,
            "audited_workspace_ref": target.workspace_ref,
        },
    )
    return TwfRunWorkspaceEvidenceAuditWorkflowResultCandidate(
        triggered=True,
        terminal_display_text=display,
        request=request,
        facts=facts,
        audit_context=audit_context,
        task_run_context=task_context,
        run_workspace=run_workspace,
        metadata={
            "workflow": TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
            **_task_context_metadata(task_context),
            **_audit_context_metadata(audit_context),
            **_run_workspace_metadata(run_workspace),
        },
    )


def resolve_twf_run_workspace_audit_target(
    request: TwfRunWorkspaceEvidenceAuditWorkflowRequestCandidate,
) -> TwfRunWorkspaceAuditTargetCandidate:
    """Resolve and validate the audited workspace target without writing to it."""

    path_input = str(request.audit_run_workspace_path or "").strip()
    ref_input = str(request.audit_run_workspace_ref or "").strip()
    root_input = str(request.audit_run_workspace_root or "").strip()
    blocking: list[str] = []
    warnings: list[str] = []
    if bool(path_input) == bool(ref_input):
        blocking.append("audit_workspace_target_must_be_path_or_ref")
    target_path: Path | None = None
    expected_ref: str | None = None
    expected_workflow: str | None = None
    expected_run_id: str | None = None

    if ref_input:
        match = AUDIT_REF_PATTERN.match(ref_input)
        if not match:
            blocking.append("audit_workspace_ref_invalid")
        elif not root_input:
            blocking.append("audit_workspace_root_required_for_ref")
        else:
            expected_workflow, expected_run_id = match.groups()
            expected_ref = ref_input
            target_path = (
                Path(root_input).expanduser().resolve()
                / expected_workflow
                / expected_run_id
            ).resolve()
    elif path_input:
        target_path = Path(path_input).expanduser().resolve()

    if target_path is not None:
        if _path_has_forbidden_marker(target_path):
            blocking.append("audit_workspace_path_forbidden_marker")
        if not target_path.exists():
            blocking.append("audit_workspace_path_missing")
        elif not target_path.is_dir():
            blocking.append("audit_workspace_path_not_directory")

    manifest_path = target_path / "manifest.json" if target_path else None
    manifest: Mapping[str, Any] = {}
    if target_path is not None and target_path.is_dir():
        if manifest_path is None or not manifest_path.is_file():
            blocking.append("audit_workspace_manifest_missing")
        else:
            loaded_manifest, manifest_blocking, manifest_warnings = _read_json_mapping(
                manifest_path,
                root=target_path,
                max_bytes=AUDIT_MANIFEST_MAX_BYTES,
            )
            manifest = loaded_manifest
            blocking.extend(manifest_blocking)
            warnings.extend(manifest_warnings)
            schema = str(manifest.get("schema_version") or "")
            if schema != TWF_RUN_WORKSPACE_SCHEMA_VERSION:
                blocking.append("audit_workspace_schema_version_invalid")

    workflow_name = _optional_text(manifest.get("workflow_name")) or expected_workflow
    run_id = _optional_text(manifest.get("run_id")) or expected_run_id
    workspace_ref = _optional_text(manifest.get("workspace_ref")) or expected_ref
    if expected_ref and workspace_ref and workspace_ref != expected_ref:
        warnings.append("audit_workspace_ref_manifest_mismatch")
    if expected_workflow and workflow_name and workflow_name != expected_workflow:
        warnings.append("audit_workspace_workflow_manifest_mismatch")
    if expected_run_id and run_id and run_id != expected_run_id:
        warnings.append("audit_workspace_run_id_manifest_mismatch")
    if target_path is not None and manifest.get("workspace_path"):
        manifest_workspace_path = Path(str(manifest["workspace_path"])).expanduser().resolve()
        if manifest_workspace_path != target_path:
            warnings.append("audit_workspace_path_manifest_mismatch")

    return TwfRunWorkspaceAuditTargetCandidate(
        status="blocked" if blocking else "resolved",
        workspace_path=str(target_path) if target_path else None,
        workspace_ref=workspace_ref,
        workflow_name=workflow_name,
        run_id=run_id,
        manifest_path=str(manifest_path) if manifest_path else None,
        manifest=manifest,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "target_source": "ref" if ref_input else ("path" if path_input else "none"),
            "redaction_applied": True,
        },
    )


def build_twf_run_workspace_evidence_audit_context(
    request: TwfRunWorkspaceEvidenceAuditWorkflowRequestCandidate,
    facts: TwfRunWorkspaceEvidenceAuditFactsCandidate,
    target: TwfRunWorkspaceAuditTargetCandidate,
) -> TwfRunWorkspaceEvidenceAuditContextCandidate:
    """Build a sanitized audit context for the target workspace."""

    if target.status == "blocked":
        return _audit_context_from_blocked_target(target)

    root = Path(str(target.workspace_path)).resolve()
    manifest = target.manifest
    files, file_findings = _audit_workspace_files(root, manifest)
    structure_checks, structure_findings = _audit_structure(root, manifest, files)
    reference_checks, reference_findings = _audit_references(manifest, files)
    boundary_checks, boundary_findings = _audit_boundaries(root, files)
    findings = tuple(
        [
            *file_findings,
            *structure_findings,
            *reference_findings,
            *boundary_findings,
        ]
    )
    audit_result = _audit_result_from_findings(findings)
    return TwfRunWorkspaceEvidenceAuditContextCandidate(
        status="succeeded",
        audit_result=audit_result,
        target=target,
        files=files,
        findings=findings,
        structure_checks=structure_checks,
        reference_checks=reference_checks,
        boundary_checks=boundary_checks,
        risk_boundaries=(
            "does_not_modify_audited_workspace",
            "does_not_execute_tools",
            "does_not_call_model",
            "does_not_print_raw_artifact_content",
            "redacts_sensitive_values",
        ),
        warnings=target.warnings,
        metadata={
            "template_version": TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_TEMPLATE_VERSION,
            "audit_focus": list(facts.audit_focus),
            "redaction_applied": True,
            "does_not_modify_audited_workspace": True,
            "does_not_execute_tools": True,
            "does_not_call_model": True,
        },
    )


def format_twf_run_workspace_evidence_audit_for_terminal(
    audit_context: TwfRunWorkspaceEvidenceAuditContextCandidate,
) -> str:
    """Format the audit context for terminal display without raw file content."""

    target = audit_context.target
    structure = audit_context.structure_checks
    references = audit_context.reference_checks
    boundaries = audit_context.boundary_checks
    findings = audit_context.findings
    lines = [
        "运行工作区证据审计结果",
        "",
        "审计对象",
        f"- workspace: {_sanitize_path_label(target.workspace_path)}",
        f"- workflow: {target.workflow_name or 'unknown'}",
        f"- run_id: {target.run_id or 'unknown'}",
        f"- audit_result: {audit_context.audit_result}",
        "",
        "结构完整性",
        f"1. manifest: {structure.get('manifest', 'unknown')}",
        f"2. results: {structure.get('results', 'unknown')}",
        f"3. evidence: {structure.get('evidence', 'unknown')}",
        f"4. artifacts: {structure.get('artifacts', 'unknown')}",
        "",
        "引用一致性",
        f"1. artifact_refs: {references.get('artifact_refs', 'unknown')}",
        f"2. result_refs: {references.get('result_refs', 'unknown')}",
        f"3. evidence_refs: {references.get('evidence_refs', 'unknown')}",
        "",
        "边界检查",
        f"1. sensitive key scan: {boundaries.get('sensitive_key_scan', 'unknown')}",
        f"2. raw response marker scan: {boundaries.get('raw_marker_scan', 'unknown')}",
        "3. model/tool boundary declarations: "
        + str(boundaries.get("boundary_declarations", "unknown")),
        "",
        "发现的问题",
    ]
    if findings:
        lines.extend(
            f"{index}. [{finding.severity}] {finding.code}: {finding.message}"
            for index, finding in enumerate(findings[:8], start=1)
        )
    else:
        lines.append("1. 未发现结构或边界问题。")
    lines.extend(
        [
            "",
            "建议动作",
            *(_recommendation_lines(audit_context)),
        ]
    )
    return "\n".join(lines)


def _audit_workspace_files(
    root: Path,
    manifest: Mapping[str, Any],
) -> tuple[
    tuple[TwfRunWorkspaceAuditFileCandidate, ...],
    tuple[TwfRunWorkspaceAuditFindingCandidate, ...],
]:
    files: list[TwfRunWorkspaceAuditFileCandidate] = []
    findings: list[TwfRunWorkspaceAuditFindingCandidate] = []
    refs_by_kind = {
        "artifact": tuple(_list_values(manifest.get("artifact_refs"))),
        "result": tuple(_list_values(manifest.get("result_refs"))),
        "evidence": tuple(_list_values(manifest.get("evidence_refs"))),
    }
    relative_by_kind: dict[str, set[str]] = {kind: set() for kind in refs_by_kind}
    for kind, refs in refs_by_kind.items():
        for ref in refs:
            relative_path = _relative_path_from_workspace_ref(ref, kind)
            if relative_path is None:
                findings.append(
                    TwfRunWorkspaceAuditFindingCandidate(
                        severity="medium",
                        code=f"{kind}_ref_invalid",
                        message=f"{kind} ref cannot be mapped to workspace file",
                        file_ref=ref,
                        recommendation="Regenerate workspace refs from managed writer.",
                    )
                )
                continue
            relative_by_kind[kind].add(relative_path)

    if not relative_by_kind["result"] and (root / "results" / "workflow_result.json").is_file():
        relative_by_kind["result"].add("results/workflow_result.json")
    for kind, relative_paths in relative_by_kind.items():
        for relative_path in sorted(relative_paths):
            files.append(_audit_one_file(root, kind, relative_path))

    for extra in sorted((root / "results").glob("*.json")) if (root / "results").is_dir() else ():
        relative = str(extra.relative_to(root))
        if relative not in relative_by_kind["result"]:
            files.append(_audit_one_file(root, "result", relative))
    for extra in sorted((root / "evidence").glob("*.json")) if (root / "evidence").is_dir() else ():
        relative = str(extra.relative_to(root))
        if relative not in relative_by_kind["evidence"]:
            files.append(_audit_one_file(root, "evidence", relative))
    terminal_display = root / "artifacts" / "terminal_display.txt"
    if terminal_display.is_file() and "artifacts/terminal_display.txt" not in relative_by_kind["artifact"]:
        files.append(_audit_one_file(root, "artifact", "artifacts/terminal_display.txt"))

    for file in files:
        if file.forbidden_markers:
            findings.append(
                TwfRunWorkspaceAuditFindingCandidate(
                    severity="high",
                    code="forbidden_marker_detected",
                    message="Forbidden key/path marker detected; value redacted.",
                    file_ref=file.ref or file.relative_path,
                    recommendation="Inspect the producing workflow boundary before reuse.",
                )
            )
        if file.json_valid is False:
            findings.append(
                TwfRunWorkspaceAuditFindingCandidate(
                    severity="medium",
                    code="json_invalid",
                    message="JSON file is not valid.",
                    file_ref=file.ref or file.relative_path,
                    recommendation="Regenerate the workspace result/evidence file.",
                )
            )
    return tuple(files), tuple(findings)


def _audit_one_file(root: Path, kind: str, relative_path: str) -> TwfRunWorkspaceAuditFileCandidate:
    resolved = _resolve_audit_relative_path(root, relative_path)
    ref = f"{kind}://run-workspace/{relative_path}"
    if resolved is None:
        return TwfRunWorkspaceAuditFileCandidate(
            kind=kind,
            relative_path=relative_path,
            exists=False,
            ref=ref,
            forbidden_markers=("path_invalid_or_forbidden",),
        )
    if not resolved.exists():
        return TwfRunWorkspaceAuditFileCandidate(
            kind=kind,
            relative_path=relative_path,
            exists=False,
            ref=ref,
        )
    if not resolved.is_file():
        return TwfRunWorkspaceAuditFileCandidate(
            kind=kind,
            relative_path=relative_path,
            exists=False,
            ref=ref,
            warnings=("not_a_file",),
        )
    size = resolved.stat().st_size
    markers: list[str] = []
    json_valid: bool | None = None
    if resolved.suffix == ".json":
        payload, blocking, warnings = _read_json_mapping(
            resolved,
            root=root,
            max_bytes=AUDIT_JSON_MAX_BYTES,
        )
        if blocking:
            json_valid = False
            markers.extend(blocking)
        else:
            json_valid = True
            markers.extend(_scan_forbidden_json_keys(payload))
        return TwfRunWorkspaceAuditFileCandidate(
            kind=kind,
            relative_path=relative_path,
            exists=True,
            bytes=size,
            ref=ref,
            json_valid=json_valid,
            forbidden_markers=tuple(_ordered_unique(markers)),
            warnings=tuple(warnings),
        )
    if relative_path == "artifacts/terminal_display.txt":
        markers.extend(_scan_text_markers(resolved, root=root))
    return TwfRunWorkspaceAuditFileCandidate(
        kind=kind,
        relative_path=relative_path,
        exists=True,
        bytes=size,
        ref=ref,
        json_valid=json_valid,
        forbidden_markers=tuple(_ordered_unique(markers)),
    )


def _audit_structure(
    root: Path,
    manifest: Mapping[str, Any],
    files: Sequence[TwfRunWorkspaceAuditFileCandidate],
) -> tuple[dict[str, Any], tuple[TwfRunWorkspaceAuditFindingCandidate, ...]]:
    findings: list[TwfRunWorkspaceAuditFindingCandidate] = []
    subdir_status = {
        subdir: (root / subdir).is_dir() for subdir in TWF_RUN_WORKSPACE_SUBDIRS
    }
    for subdir, exists in subdir_status.items():
        if not exists:
            findings.append(
                TwfRunWorkspaceAuditFindingCandidate(
                    severity="high",
                    code=f"{subdir}_directory_missing",
                    message=f"Standard workspace subdir missing: {subdir}",
                    recommendation="Regenerate workspace or check cleanup policy.",
                )
            )
    required_fields = (
        "schema_version",
        "workspace_ref",
        "workflow_name",
        "run_id",
        "status",
        "artifact_refs",
        "evidence_refs",
        "result_refs",
    )
    for field_name in required_fields:
        if field_name not in manifest:
            findings.append(
                TwfRunWorkspaceAuditFindingCandidate(
                    severity="medium",
                    code=f"manifest_{field_name}_missing",
                    message=f"Manifest field missing: {field_name}",
                    recommendation="Finalize workspace through managed helper.",
                )
            )
    if not any(file.kind == "result" and file.exists for file in files):
        findings.append(
            TwfRunWorkspaceAuditFindingCandidate(
                severity="high",
                code="result_file_missing",
                message="No result file could be found.",
                recommendation="Check workflow result writing stage.",
            )
        )
    return (
        {
            "manifest": "present" if (root / "manifest.json").is_file() else "missing",
            "results": "present" if subdir_status.get("results") else "missing",
            "evidence": "present" if subdir_status.get("evidence") else "missing",
            "artifacts": "present" if subdir_status.get("artifacts") else "missing",
            "subdirs": subdir_status,
            "result_file_count": sum(1 for file in files if file.kind == "result" and file.exists),
        },
        tuple(findings),
    )


def _audit_references(
    manifest: Mapping[str, Any],
    files: Sequence[TwfRunWorkspaceAuditFileCandidate],
) -> tuple[dict[str, Any], tuple[TwfRunWorkspaceAuditFindingCandidate, ...]]:
    findings: list[TwfRunWorkspaceAuditFindingCandidate] = []
    by_kind = {
        "artifact": [file for file in files if file.kind == "artifact"],
        "result": [file for file in files if file.kind == "result"],
        "evidence": [file for file in files if file.kind == "evidence"],
    }
    for kind, kind_files in by_kind.items():
        for file in kind_files:
            if not file.exists:
                findings.append(
                    TwfRunWorkspaceAuditFindingCandidate(
                        severity="high",
                        code=f"{kind}_file_missing",
                        message=f"Referenced {kind} file is missing.",
                        file_ref=file.ref or file.relative_path,
                        recommendation="Check manifest refs and workspace retention.",
                    )
                )
    return (
        {
            "artifact_refs": _reference_status(manifest.get("artifact_refs"), by_kind["artifact"]),
            "result_refs": _reference_status(manifest.get("result_refs"), by_kind["result"]),
            "evidence_refs": _reference_status(manifest.get("evidence_refs"), by_kind["evidence"]),
        },
        tuple(findings),
    )


def _audit_boundaries(
    root: Path,
    files: Sequence[TwfRunWorkspaceAuditFileCandidate],
) -> tuple[dict[str, Any], tuple[TwfRunWorkspaceAuditFindingCandidate, ...]]:
    findings: list[TwfRunWorkspaceAuditFindingCandidate] = []
    sensitive_markers = [
        marker
        for file in files
        for marker in file.forbidden_markers
        if marker in AUDIT_FORBIDDEN_JSON_KEYS
        or marker in AUDIT_FORBIDDEN_TEXT_MARKERS
        or marker == "path_invalid_or_forbidden"
    ]
    config_context_path = root / "evidence" / "config_explain_context.json"
    boundary_declarations = "not_applicable"
    if config_context_path.is_file():
        payload, blocking, _ = _read_json_mapping(
            config_context_path,
            root=root,
            max_bytes=AUDIT_JSON_MAX_BYTES,
        )
        required = (
            "does_not_read_raw_config_directly",
            "does_not_execute_tools",
            "does_not_call_model",
        )
        missing = [key for key in required if payload.get(key) is not True]
        if blocking:
            boundary_declarations = "unreadable"
        elif missing:
            boundary_declarations = "missing:" + ",".join(missing)
            findings.append(
                TwfRunWorkspaceAuditFindingCandidate(
                    severity="medium",
                    code="boundary_declaration_missing",
                    message="Expected config explain boundary declaration is missing.",
                    file_ref="evidence/config_explain_context.json",
                    recommendation="Regenerate evidence with boundary declarations.",
                )
            )
        else:
            boundary_declarations = "present"
    if sensitive_markers:
        findings.append(
            TwfRunWorkspaceAuditFindingCandidate(
                severity="high",
                code="boundary_sensitive_marker_detected",
                message="Sensitive or raw marker detected; value redacted.",
                recommendation="Inspect producer workflow output boundary.",
            )
        )
    return (
        {
            "sensitive_key_scan": "passed" if not sensitive_markers else "attention_required",
            "raw_marker_scan": "passed" if not sensitive_markers else "attention_required",
            "boundary_declarations": boundary_declarations,
            "forbidden_marker_count": len(sensitive_markers),
        },
        tuple(findings),
    )


def _audit_context_from_blocked_target(
    target: TwfRunWorkspaceAuditTargetCandidate,
) -> TwfRunWorkspaceEvidenceAuditContextCandidate:
    findings = tuple(
        TwfRunWorkspaceAuditFindingCandidate(
            severity="high",
            code=reason,
            message="Audit target could not be resolved.",
            recommendation="Provide a valid run workspace path or ref.",
        )
        for reason in target.blocking_reasons
    )
    return TwfRunWorkspaceEvidenceAuditContextCandidate(
        status="succeeded",
        audit_result="blocked",
        target=target,
        files=(),
        findings=findings,
        structure_checks={"manifest": "not_checked", "results": "not_checked", "evidence": "not_checked", "artifacts": "not_checked"},
        reference_checks={"artifact_refs": "not_checked", "result_refs": "not_checked", "evidence_refs": "not_checked"},
        boundary_checks={"sensitive_key_scan": "not_checked", "raw_marker_scan": "not_checked", "boundary_declarations": "not_checked"},
        risk_boundaries=(
            "does_not_modify_audited_workspace",
            "does_not_execute_tools",
            "does_not_call_model",
            "redacts_sensitive_values",
        ),
        warnings=target.warnings,
        metadata={
            "template_version": TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_TEMPLATE_VERSION,
            "redaction_applied": True,
            "does_not_modify_audited_workspace": True,
            "does_not_execute_tools": True,
            "does_not_call_model": True,
        },
    )


def _create_audit_output_run_workspace(
    request: TwfRunWorkspaceEvidenceAuditWorkflowRequestCandidate,
    task_context: TwfRunContextCandidate,
    target: TwfRunWorkspaceAuditTargetCandidate,
) -> TwfRunWorkspaceStateCandidate | None:
    if not request.run_workspace_enabled and not request.run_workspace_root:
        return None
    if request.run_workspace_root and _audit_output_root_inside_target(
        request.run_workspace_root,
        target.workspace_path,
    ):
        return TwfRunWorkspaceStateCandidate(
            workspace_ref="run-workspace://blocked/audit-output-overlaps-target",
            workspace_path=str(Path(request.run_workspace_root).expanduser().resolve()),
            workflow_name=TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
            run_id=task_context.run_id,
            workspace_created=False,
            retention_policy=request.run_workspace_retention_policy,
            cleanup_policy=request.run_workspace_cleanup_policy,
            manifest_path=str(Path(request.run_workspace_root) / "manifest.json"),
            subdirs=TWF_RUN_WORKSPACE_SUBDIRS,
            blocking_reasons=("audit_output_workspace_overlaps_target",),
        )
    workspace_root = request.run_workspace_root or ".cognition-runs"
    policy = build_twf_run_workspace_policy(
        workspace_root=workspace_root,
        retention_policy=request.run_workspace_retention_policy,
        cleanup_policy=request.run_workspace_cleanup_policy,
        max_write_bytes=request.run_workspace_max_write_bytes,
    )
    return create_twf_run_workspace(
        policy=policy,
        workflow_name=task_context.workflow_name,
        run_id=task_context.run_id,
    )


def _finalize_evidence_audit_run_workspace(
    run_workspace: TwfRunWorkspaceStateCandidate | None,
    *,
    status: str,
    terminal_display_text: str,
    facts: TwfRunWorkspaceEvidenceAuditFactsCandidate,
    audit_context: TwfRunWorkspaceEvidenceAuditContextCandidate,
) -> TwfRunWorkspaceStateCandidate | None:
    if run_workspace is None or not run_workspace.workspace_created:
        return run_workspace
    max_write_bytes = int(run_workspace.metadata.get("max_write_bytes") or 65536)
    run_workspace, _ = write_twf_run_workspace_json(
        run_workspace,
        relative_path="evidence/workspace_audit_context.json",
        payload=_audit_context_workspace_payload(audit_context),
        kind="evidence",
        max_write_bytes=max_write_bytes,
    )
    run_workspace, _ = write_twf_run_workspace_text(
        run_workspace,
        relative_path="artifacts/terminal_display.txt",
        text=terminal_display_text + "\n",
        kind="artifact",
        max_write_bytes=max_write_bytes,
    )
    run_workspace, _ = write_twf_run_workspace_json(
        run_workspace,
        relative_path="results/workflow_result.json",
        payload={
            "workflow": TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
            "status": status,
            "audit_result": audit_context.audit_result,
            "task_kind": facts.task_kind,
            "matched_terms": list(facts.matched_terms),
            "audit_focus": list(facts.audit_focus),
            "model_call_count": 0,
            "no_live": True,
            "fail_safe": False,
            "template_version": TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_TEMPLATE_VERSION,
            "audited_workspace_ref": audit_context.target.workspace_ref,
            "finding_count": len(audit_context.findings),
        },
        kind="result",
        max_write_bytes=max_write_bytes,
    )
    run_workspace = finalize_twf_run_workspace(
        run_workspace,
        status=status,
        metadata={
            "workflow": TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
            "audit_result": audit_context.audit_result,
            "model_call_count": 0,
            "fail_safe": False,
            "template_version": TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_TEMPLATE_VERSION,
        },
    )
    run_workspace, _ = cleanup_twf_run_workspace(run_workspace, status=status)
    return run_workspace


def _audit_context_workspace_payload(
    audit_context: TwfRunWorkspaceEvidenceAuditContextCandidate,
) -> dict[str, Any]:
    target = audit_context.target
    return {
        "status": audit_context.status,
        "audit_result": audit_context.audit_result,
        "audited_workspace_ref": target.workspace_ref,
        "audited_workspace_path_sanitized": _sanitize_path_label(target.workspace_path),
        "workflow_name": target.workflow_name,
        "run_id": target.run_id,
        "manifest_status": audit_context.structure_checks.get("manifest"),
        "structure_checks": audit_context.structure_checks,
        "reference_checks": audit_context.reference_checks,
        "boundary_checks": audit_context.boundary_checks,
        "findings": [
            {
                "severity": finding.severity,
                "code": finding.code,
                "message": finding.message,
                "file_ref": finding.file_ref,
                "recommendation": finding.recommendation,
            }
            for finding in audit_context.findings
        ],
        "risk_boundaries": list(audit_context.risk_boundaries),
        "does_not_modify_audited_workspace": True,
        "does_not_execute_tools": True,
        "does_not_call_model": True,
        "redaction_applied": True,
    }


def _build_evidence_audit_task_context(
    request: TwfRunWorkspaceEvidenceAuditWorkflowRequestCandidate,
    facts: TwfRunWorkspaceEvidenceAuditFactsCandidate,
) -> TwfRunContextCandidate:
    return build_twf_run_context(
        workflow_name=TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
        task_kind=TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_TASK_KIND,
        session_id=request.chat_session_id,
        turn_index=request.turn_index,
        live_model_allowed=False,
        approval_ref=request.approval_ref,
        audit_ref=request.audit_ref,
        sanitized_evidence_ref=request.sanitized_evidence_ref,
        risk_level=request.risk_level,
        output_budget=request.output_budget,
        live_gate=request.live_gate or "no_live",
        user_passthrough_parameters=request.user_passthrough_parameters,
        metadata={
            "workflow_stage": "task_context",
            "matched_terms": list(facts.matched_terms),
            "audit_focus": list(facts.audit_focus),
            "does_not_call_model": True,
            "does_not_execute_tools": True,
        },
    )


def _finalize_task_context_with_run_workspace(
    task_context: TwfRunContextCandidate,
    *,
    status: str,
    run_workspace: TwfRunWorkspaceStateCandidate | None,
    metadata: Mapping[str, Any] | None = None,
) -> TwfRunContextCandidate:
    return finalize_twf_run_context(
        task_context,
        status=status,
        artifact_refs=_run_workspace_artifact_and_result_refs(run_workspace),
        evidence_refs=run_workspace.evidence_refs if run_workspace else (),
        workspace_ref=run_workspace.workspace_ref if run_workspace else None,
        workspace_created=run_workspace.workspace_created if run_workspace else None,
        retention_policy=run_workspace.retention_policy if run_workspace else None,
        cleanup_policy=run_workspace.cleanup_policy if run_workspace else None,
        workspace_metadata=twf_run_workspace_status_dict(run_workspace),
        metadata=metadata,
    )


def _read_json_mapping(
    path: Path,
    *,
    root: Path,
    max_bytes: int,
) -> tuple[Mapping[str, Any], list[str], list[str]]:
    blocking: list[str] = []
    warnings: list[str] = []
    resolved = _resolve_existing_file_under_root(path, root)
    if resolved is None:
        return {}, ["audit_file_path_outside_workspace"], warnings
    if _path_has_forbidden_marker(resolved):
        return {}, ["audit_file_path_forbidden_marker"], warnings
    if resolved.stat().st_size > max_bytes:
        return {}, ["audit_file_exceeds_read_budget"], warnings
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}, ["audit_file_json_invalid"], warnings
    if not isinstance(value, Mapping):
        return {}, ["audit_file_json_not_object"], warnings
    return value, blocking, warnings


def _resolve_audit_relative_path(root: Path, relative_path: str) -> Path | None:
    path = Path(relative_path)
    parts = path.parts
    if path.is_absolute() or not parts or ".." in parts:
        return None
    if parts[0] not in set(TWF_RUN_WORKSPACE_SUBDIRS):
        return None
    if _path_has_forbidden_marker(path):
        return None
    resolved = (root / path).resolve()
    if root not in resolved.parents and root != resolved:
        return None
    return resolved


def _resolve_existing_file_under_root(path: Path, root: Path) -> Path | None:
    resolved = path.resolve()
    if root not in resolved.parents and root != resolved:
        return None
    if not resolved.is_file():
        return None
    return resolved


def _relative_path_from_workspace_ref(ref: str, kind: str) -> str | None:
    expected_prefix = "evidence" if kind == "evidence" else kind
    prefix = f"{expected_prefix}://run-workspace/"
    if not ref.startswith(prefix):
        return None
    parts = ref[len(prefix) :].split("/", 2)
    if len(parts) != 3:
        return None
    relative = parts[2]
    if _resolve_audit_relative_path(Path.cwd(), relative) is None and (
        Path(relative).is_absolute() or ".." in Path(relative).parts
    ):
        return None
    if kind == "artifact" and not relative.startswith("artifacts/"):
        return None
    if kind == "result" and not relative.startswith("results/"):
        return None
    if kind == "evidence" and not (
        relative.startswith("evidence/") or relative.startswith("references/")
    ):
        return None
    return relative


def _scan_forbidden_json_keys(value: Any, path: str = "") -> list[str]:
    markers: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            lowered = key_text.lower()
            if any(
                marker in lowered for marker in AUDIT_FORBIDDEN_JSON_KEYS
            ) and not _safe_negative_boundary_declaration(key_text, item):
                markers.append(key_text)
            child_path = f"{path}.{key_text}" if path else key_text
            markers.extend(_scan_forbidden_json_keys(item, child_path))
    elif isinstance(value, list):
        for item in value:
            markers.extend(_scan_forbidden_json_keys(item, path))
    return _ordered_unique(markers)


def _scan_text_markers(path: Path, *, root: Path) -> list[str]:
    resolved = _resolve_existing_file_under_root(path, root)
    if resolved is None or resolved.stat().st_size > AUDIT_TERMINAL_SCAN_MAX_BYTES:
        return []
    text = resolved.read_text(encoding="utf-8", errors="ignore")
    lowered = text.lower()
    return [
        marker
        for marker in AUDIT_FORBIDDEN_TEXT_MARKERS
        if marker.lower() in lowered
    ]


def _safe_negative_boundary_declaration(key: str, value: Any) -> bool:
    lowered = key.lower()
    if lowered.startswith("does_not_") and value is True:
        return True
    if lowered.endswith("_included") and value is False:
        return True
    if lowered.endswith("_present") and value is False:
        return True
    return False


def _audit_result_from_findings(
    findings: Sequence[TwfRunWorkspaceAuditFindingCandidate],
) -> str:
    if any(finding.severity == "high" for finding in findings):
        return "attention_required"
    if findings:
        return "passed_with_warnings"
    return "passed"


def _reference_status(
    refs_value: Any,
    files: Sequence[TwfRunWorkspaceAuditFileCandidate],
) -> str:
    refs = _list_values(refs_value)
    if refs and all(file.exists for file in files):
        return "consistent"
    if refs and any(not file.exists for file in files):
        return "missing_files"
    if files:
        return "files_without_manifest_refs"
    return "none"


def _recommendation_lines(
    audit_context: TwfRunWorkspaceEvidenceAuditContextCandidate,
) -> list[str]:
    if audit_context.audit_result == "passed":
        return ["1. 可将该 workspace 作为后续审查输入。"]
    if audit_context.audit_result == "blocked":
        return ["1. 请提供有效 run workspace path 或 ref 后重试。"]
    return [
        "1. 先修复 high/medium finding，再作为验收证据使用。",
        "2. 不要将本审计结果直接等同于 governance acceptance。",
    ]


def _preflight_blocked_terminal_display(
    task_context: TwfRunContextCandidate,
) -> str:
    reasons = ", ".join(task_context.preflight.blocking_reasons)
    return "\n".join(
        [
            "运行工作区证据审计结果",
            "",
            "风险边界",
            f"- preflight blocked: {reasons or 'unknown'}",
        ]
    )


def _workspace_blocked_terminal_display(
    task_context: TwfRunContextCandidate,
    run_workspace: TwfRunWorkspaceStateCandidate,
) -> str:
    reasons = ", ".join(run_workspace.blocking_reasons)
    return "\n".join(
        [
            "运行工作区证据审计结果",
            "",
            "风险边界",
            f"- audit output workspace blocked: {reasons or 'unknown'}",
            f"- run_id: {task_context.run_id}",
        ]
    )


def _task_context_metadata(task_context: TwfRunContextCandidate) -> dict[str, Any]:
    return {
        "task_control": twf_run_context_status_dict(task_context),
    }


def _audit_context_metadata(
    audit_context: TwfRunWorkspaceEvidenceAuditContextCandidate,
) -> dict[str, Any]:
    return {
        "workspace_audit": {
            "status": audit_context.status,
            "audit_result": audit_context.audit_result,
            "finding_count": len(audit_context.findings),
            "risk_boundaries": list(audit_context.risk_boundaries),
        }
    }


def _run_workspace_metadata(
    run_workspace: TwfRunWorkspaceStateCandidate | None,
) -> dict[str, Any]:
    status = twf_run_workspace_status_dict(run_workspace)
    return {"run_workspace": status} if status is not None else {}


def _run_workspace_artifact_and_result_refs(
    run_workspace: TwfRunWorkspaceStateCandidate | None,
) -> tuple[str, ...]:
    if run_workspace is None:
        return ()
    return (*run_workspace.artifact_refs, *run_workspace.result_refs)


def _audit_output_root_inside_target(
    output_root: str | Path,
    target_workspace_path: str | None,
) -> bool:
    if not target_workspace_path:
        return False
    output = Path(output_root).expanduser().resolve()
    target = Path(target_workspace_path).expanduser().resolve()
    return output == target or target in output.parents


def _audit_target_requested(
    request: TwfRunWorkspaceEvidenceAuditWorkflowRequestCandidate,
) -> bool:
    return bool(request.audit_run_workspace_path or request.audit_run_workspace_ref)


def _path_has_forbidden_marker(path: Path) -> bool:
    path_text = str(path).lower()
    return any(marker in path_text for marker in AUDIT_FORBIDDEN_PATH_MARKERS)


def _list_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item)]
    return []


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _sanitize_path_label(value: str | Path | None) -> str:
    if value is None:
        return "none"
    text = str(value).strip()
    if not text:
        return "none"
    path = Path(text)
    if not path.is_absolute():
        return text
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return f".../{path.name}"


def _compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
