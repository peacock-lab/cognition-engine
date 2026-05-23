"""task config profile explain workflow for governed configuration diagnostics."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

from cognition_operation_flows._core.run_workspace import (
    TwfRunWorkspaceStateCandidate,
    build_twf_run_workspace_policy,
    cleanup_twf_run_workspace,
    twf_run_workspace_status_dict,
    create_twf_run_workspace,
    finalize_twf_run_workspace,
    write_twf_run_workspace_json,
    write_twf_run_workspace_text,
)
from cognition_operation_flows._core.control import (
    TWF_CONFIG_PRECEDENCE,
    MANAGED_GOVERNANCE_PARAMETERS,
    TwfRunContextCandidate,
    build_twf_run_context,
    twf_run_context_status_dict,
    finalize_twf_run_context,
)


TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME = "twf_config_profile_explain_workflow"
TWF_CONFIG_PROFILE_EXPLAIN_TASK_KIND = "config_profile_explain"
TWF_CONFIG_PROFILE_EXPLAIN_TEMPLATE_VERSION = "config_profile_explain_template_v1"
CONFIG_PROFILE_EXPLAIN_DISPLAY_PREVIEW_LIMIT = 4000
CONFIG_PROFILE_EXPLAIN_KEYWORDS = (
    "解释配置",
    "配置为什么",
    "配置生效",
    "配置来源",
    "覆盖关系",
    "当前配置",
    "配置解释",
    "profile",
    "config profile",
    "tool exposure",
    "工具暴露",
    "reference-reader",
    "reference reader",
    "run workspace",
    "运行工作区",
    "live llm",
    "ollama",
    "approval",
    "audit",
    "risk",
    "output budget",
    "live gate",
)
CONFIG_PROFILE_EXPLAIN_FOCUS_TERMS = (
    "tool_exposure",
    "reference_reader",
    "run_workspace",
    "live_llm",
    "ollama",
    "governance_refs",
    "config_precedence",
)
CONFIG_PROFILE_MUTATION_MARKERS = (
    "修改配置",
    "写配置",
    "更新配置",
    "改配置",
    "设置配置",
    "生成配置文件",
)
RUNTIME_OPEN_MARKERS = ("打开", "开启", "启用", "接入", "集成", "上线")
PROTECTED_RUNTIME_TERMS = ("Agent runtime", "Skills runtime", "ADK SkillRegistry")


@dataclass(frozen=True)
class TwfConfigProfileExplainWorkflowRequestCandidate:
    """Request entering the task config profile explain workflow."""

    user_text: str
    chat_session_id: str | None = None
    turn_index: int | None = None
    history: tuple[Mapping[str, str], ...] = ()
    config_context: Any | None = None
    config_root: str | Path | None = None
    environment: str = "local"
    profile: str | None = None
    request_live_llm: bool = False
    request_ollama: bool = False
    allow_live_llm: bool = False
    allow_ollama: bool = False
    ollama_api_base: str | None = None
    live_llm_timeout_seconds: int | None = None
    operator_approved: bool = False
    approval_ref: str | None = None
    audit_ref: str | None = None
    sanitized_evidence_ref: str | None = None
    governance_summary_output_ref: str | None = None
    risk_level: str = "low"
    output_budget: int | None = CONFIG_PROFILE_EXPLAIN_DISPLAY_PREVIEW_LIMIT
    live_gate: str | None = "no_live"
    user_passthrough_parameters: Mapping[str, Any] = field(default_factory=dict)
    reference_paths: tuple[str, ...] = ()
    tool_exposure_profile: str | None = None
    entrypoint_explicit_args: Mapping[str, Any] = field(default_factory=dict)
    session_args: Mapping[str, Any] = field(default_factory=dict)
    run_workspace_root: str | None = None
    run_workspace_enabled: bool = False
    run_workspace_retention_policy: str = "keep"
    run_workspace_cleanup_policy: str = "manual"
    run_workspace_max_write_bytes: int = 65536
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfConfigProfileExplainFactsCandidate:
    """Minimal config explain intent facts."""

    original_text: str
    task_kind: str
    requested_focus: tuple[str, ...] = ()
    matched_terms: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfConfigProfileExplainValueCandidate:
    """One effective configuration value and its source."""

    name: str
    effective_value: str
    source: str
    note: str | None = None


@dataclass(frozen=True)
class TwfConfigProfileExplainContextCandidate:
    """Sanitized configuration explanation context."""

    status: str
    config_context_available: bool
    config_context_source: str
    config_root_sanitized: str
    environment: str
    profile: str | None
    precedence: tuple[str, ...]
    requested_focus: tuple[str, ...]
    tool_exposure_summary: dict[str, Any]
    reference_reader_summary: dict[str, Any]
    run_workspace_summary: dict[str, Any]
    live_llm_summary: dict[str, Any]
    governance_boundary_summary: dict[str, Any]
    effective_values: tuple[TwfConfigProfileExplainValueCandidate, ...]
    risk_boundaries: tuple[str, ...]
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfConfigProfileExplainWorkflowResultCandidate:
    """Final workflow result returned to cognition chat."""

    triggered: bool
    terminal_display_text: str
    request: TwfConfigProfileExplainWorkflowRequestCandidate
    facts: TwfConfigProfileExplainFactsCandidate
    explain_context: TwfConfigProfileExplainContextCandidate
    model_call_count: int = 0
    no_live: bool = True
    fail_safe: bool = False
    task_run_context: TwfRunContextCandidate | None = None
    run_workspace: TwfRunWorkspaceStateCandidate | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def detect_twf_config_profile_explain_request(user_text: str) -> bool:
    """Return whether a turn should route to config profile explain."""

    normalized = _compact_text(user_text)
    if not normalized:
        return False
    lowered = normalized.lower()
    if any(marker in normalized for marker in CONFIG_PROFILE_MUTATION_MARKERS):
        return False
    if _requests_protected_runtime_open(normalized):
        return False
    return any(keyword.lower() in lowered for keyword in CONFIG_PROFILE_EXPLAIN_KEYWORDS)


def extract_twf_config_profile_explain_facts(
    request: TwfConfigProfileExplainWorkflowRequestCandidate,
) -> TwfConfigProfileExplainFactsCandidate:
    """Extract bounded config explain intent facts."""

    normalized = _compact_text(request.user_text)
    lowered = normalized.lower()
    matched_terms = tuple(
        keyword
        for keyword in CONFIG_PROFILE_EXPLAIN_KEYWORDS
        if keyword.lower() in lowered
    )
    focus = _requested_focus(lowered)
    return TwfConfigProfileExplainFactsCandidate(
        original_text=request.user_text,
        task_kind=TWF_CONFIG_PROFILE_EXPLAIN_TASK_KIND,
        requested_focus=focus,
        matched_terms=matched_terms,
        metadata={
            "workflow_stage": "intent_extraction",
            "reference_path_count": len(request.reference_paths),
        },
    )


def run_twf_config_profile_explain_workflow(
    request: TwfConfigProfileExplainWorkflowRequestCandidate,
) -> TwfConfigProfileExplainWorkflowResultCandidate:
    """Run the governed task config profile explain workflow."""

    facts = extract_twf_config_profile_explain_facts(request)
    task_context = _build_config_profile_explain_task_context(request, facts)
    if not task_context.preflight.allowed:
        task_context = finalize_twf_run_context(
            task_context,
            status="blocked",
            metadata={"blocked_before_config_explain": True},
        )
        explain_context = _blocked_explain_context(request, facts, task_context)
        return TwfConfigProfileExplainWorkflowResultCandidate(
            triggered=True,
            terminal_display_text=_preflight_blocked_terminal_display(task_context),
            request=request,
            facts=facts,
            explain_context=explain_context,
            fail_safe=True,
            task_run_context=task_context,
            metadata={
                "workflow": TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
                **_task_context_metadata(task_context),
            },
        )

    run_workspace = _create_config_profile_explain_run_workspace(
        request,
        task_context,
    )
    if run_workspace is not None and not run_workspace.workspace_created:
        task_context = _finalize_task_context_with_run_workspace(
            task_context,
            status="blocked",
            run_workspace=run_workspace,
            metadata={
                "blocked_before_config_explain": True,
                "failure_stage": "run_workspace",
            },
        )
        explain_context = _blocked_explain_context(request, facts, task_context)
        return TwfConfigProfileExplainWorkflowResultCandidate(
            triggered=True,
            terminal_display_text=_workspace_blocked_terminal_display(
                task_context,
                run_workspace,
            ),
            request=request,
            facts=facts,
            explain_context=explain_context,
            fail_safe=True,
            task_run_context=task_context,
            run_workspace=run_workspace,
            metadata={
                "workflow": TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
                **_task_context_metadata(task_context),
                **_run_workspace_metadata(run_workspace),
            },
        )

    explain_context = build_twf_config_profile_explain_context(request, facts)
    display = format_twf_config_profile_explain_for_terminal(explain_context)
    run_workspace = _finalize_config_profile_explain_run_workspace(
        run_workspace,
        status=explain_context.status,
        terminal_display_text=display,
        facts=facts,
        explain_context=explain_context,
    )
    task_context = finalize_twf_run_context(
        task_context,
        status=explain_context.status,
        evidence_refs=run_workspace.evidence_refs if run_workspace else (),
        artifact_refs=_run_workspace_artifact_and_result_refs(run_workspace),
        workspace_ref=run_workspace.workspace_ref if run_workspace else None,
        workspace_created=run_workspace.workspace_created if run_workspace else None,
        retention_policy=run_workspace.retention_policy if run_workspace else None,
        cleanup_policy=run_workspace.cleanup_policy if run_workspace else None,
        workspace_metadata=twf_run_workspace_status_dict(run_workspace),
    )
    return TwfConfigProfileExplainWorkflowResultCandidate(
        triggered=True,
        terminal_display_text=display,
        request=request,
        facts=facts,
        explain_context=explain_context,
        task_run_context=task_context,
        run_workspace=run_workspace,
        metadata={
            "workflow": TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
            **_task_context_metadata(task_context),
            **_config_explain_context_metadata(explain_context),
            **_run_workspace_metadata(run_workspace),
        },
    )


def build_twf_config_profile_explain_context(
    request: TwfConfigProfileExplainWorkflowRequestCandidate,
    facts: TwfConfigProfileExplainFactsCandidate | None = None,
) -> TwfConfigProfileExplainContextCandidate:
    """Build a sanitized explanation context from parsed runtime config views."""

    resolved_facts = facts or extract_twf_config_profile_explain_facts(request)
    config_context = request.config_context
    warnings: list[str] = []
    if config_context is None:
        warnings.append("config_context_unavailable_using_defaults")

    tool_summary, reference_summary = _tool_and_reference_summary(request)
    workspace_summary = _run_workspace_summary(request)
    live_summary = _live_llm_summary(request)
    governance_summary = _governance_boundary_summary(request)
    effective_values = (
        TwfConfigProfileExplainValueCandidate(
            name="tool_exposure_profile",
            effective_value=str(tool_summary["profile_name"]),
            source=str(tool_summary["source"]),
        ),
        TwfConfigProfileExplainValueCandidate(
            name="reference_reader",
            effective_value=str(reference_summary["status"]),
            source=str(reference_summary["source"]),
        ),
        TwfConfigProfileExplainValueCandidate(
            name="run_workspace",
            effective_value="enabled" if workspace_summary["enabled"] else "disabled",
            source=str(workspace_summary["source"]),
        ),
        TwfConfigProfileExplainValueCandidate(
            name="live_llm",
            effective_value=str(live_summary["status"]),
            source=str(live_summary["source"]),
        ),
        TwfConfigProfileExplainValueCandidate(
            name="governance_refs",
            effective_value=str(governance_summary["status"]),
            source="entrypoint_explicit_args",
            note="only presence is reported; raw refs are redacted",
        ),
    )
    return TwfConfigProfileExplainContextCandidate(
        status="succeeded",
        config_context_available=config_context is not None,
        config_context_source=(
            "composition.build_runtime_config_context"
            if config_context is not None
            else "default_values"
        ),
        config_root_sanitized=_sanitize_path_label(request.config_root),
        environment=request.environment or "local",
        profile=request.profile,
        precedence=TWF_CONFIG_PRECEDENCE,
        requested_focus=resolved_facts.requested_focus,
        tool_exposure_summary=tool_summary,
        reference_reader_summary=reference_summary,
        run_workspace_summary=workspace_summary,
        live_llm_summary=live_summary,
        governance_boundary_summary=governance_summary,
        effective_values=effective_values,
        risk_boundaries=(
            "does_not_read_raw_config_directly",
            "does_not_execute_tools",
            "does_not_call_model",
            "does_not_modify_config_files",
            "does_not_open_agent_runtime",
            "does_not_open_skills_runtime",
            "redacts_sensitive_refs",
        ),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "template_version": TWF_CONFIG_PROFILE_EXPLAIN_TEMPLATE_VERSION,
            "redaction_applied": True,
            "does_not_read_raw_config_directly": True,
            "does_not_execute_tools": True,
            "does_not_call_model": True,
        },
    )


def format_twf_config_profile_explain_for_terminal(
    explain_context: TwfConfigProfileExplainContextCandidate,
) -> str:
    """Format the config explain context for terminal display."""

    tool_summary = explain_context.tool_exposure_summary
    reference_summary = explain_context.reference_reader_summary
    workspace_summary = explain_context.run_workspace_summary
    live_summary = explain_context.live_llm_summary
    governance_summary = explain_context.governance_boundary_summary
    lines = [
        "配置解释结果",
        "",
        "配置来源",
        f"- config_root: {explain_context.config_root_sanitized}",
        f"- environment: {explain_context.environment}",
        f"- profile: {explain_context.profile or 'none'}",
        f"- config_context: {explain_context.config_context_source}",
        "",
        "覆盖关系",
        "1. 入口显式参数 > 会话参数 > profile/config > 默认值",
        "",
        "当前有效配置",
        (
            "1. tool exposure profile: "
            f"{tool_summary['profile_name']}（来源：{tool_summary['source']}）"
        ),
        (
            "2. reference-reader: "
            f"{reference_summary['status']}（来源：{reference_summary['source']}）"
        ),
        (
            "3. run workspace: "
            f"{'enabled' if workspace_summary['enabled'] else 'disabled'}"
            f"（来源：{workspace_summary['source']}）"
        ),
        (
            "4. live LLM / Ollama: "
            f"{live_summary['status']}（来源：{live_summary['source']}）"
        ),
        (
            "5. governance refs: "
            f"{governance_summary['status']}（只展示 present/missing，不展示原值）"
        ),
        "",
        "风险边界",
        "1. 本轮不打开 Agent runtime / Skills runtime。",
        "2. 本轮不执行工具。",
        "3. 本轮不修改配置文件。",
        "4. 本轮不输出 secret/token/credential/approval_ref/audit_ref 原值。",
        "",
        "建议动作",
        "1. 若要改变配置，请另开配置修改任务。",
        "2. 若要验证当前配置，请执行 no-live entrypoint smoke。",
        "3. 若涉及真实模型，请显式提供 live gate 所需审批参数。",
    ]
    if explain_context.warnings:
        lines.extend(
            [
                "",
                "warnings",
                *[f"- {warning}" for warning in explain_context.warnings],
            ]
        )
    return "\n".join(lines)


def _tool_and_reference_summary(
    request: TwfConfigProfileExplainWorkflowRequestCandidate,
) -> tuple[dict[str, Any], dict[str, Any]]:
    tool_exposure = getattr(request.config_context, "tool_exposure", None)
    profile_config = (
        tool_exposure.to_profile_config() if tool_exposure is not None else {}
    )
    profile_name = (
        request.tool_exposure_profile
        or getattr(tool_exposure, "default_profile", None)
        or "readonly_reference"
    )
    source = "entrypoint_explicit_args" if request.tool_exposure_profile else (
        "profile_config" if tool_exposure is not None else "default_values"
    )
    profiles = profile_config.get("profiles") if isinstance(profile_config, Mapping) else {}
    profile_mapping = profiles.get(profile_name, {}) if isinstance(profiles, Mapping) else {}
    toolsets = (
        profile_mapping.get("toolsets", ())
        if isinstance(profile_mapping, Mapping)
        else ()
    )
    selected_tool_names: list[str] = []
    reference_policy: Mapping[str, Any] | None = None
    for toolset in toolsets if isinstance(toolsets, Sequence) else ():
        if not isinstance(toolset, Mapping):
            continue
        selected_tool_names.extend(
            str(name)
            for name in toolset.get("tool_filter", toolset.get("allowlist_tool_names", ()))
            if str(name)
        )
        candidate_policy = toolset.get("reference_reader")
        if isinstance(candidate_policy, Mapping):
            reference_policy = candidate_policy
    reference_status = "enabled" if reference_policy is not None else "not_exposed"
    return (
        {
            "profile_name": profile_name,
            "source": source,
            "selected_tool_names": _ordered_unique(selected_tool_names),
            "config_precedence": list(TWF_CONFIG_PRECEDENCE),
            "raw_config_included": False,
        },
        {
            "status": reference_status,
            "source": source,
            "allowed_roots": list(reference_policy.get("allowed_roots", ()))
            if reference_policy
            else [],
            "allowed_files": list(reference_policy.get("allowed_files", ()))
            if reference_policy
            else [],
            "allowed_suffixes": list(reference_policy.get("allowed_suffixes", ()))
            if reference_policy
            else [],
            "max_bytes": reference_policy.get("max_bytes") if reference_policy else None,
            "max_chars": reference_policy.get("max_chars") if reference_policy else None,
            "raw_config_included": False,
        },
    )


def _run_workspace_summary(
    request: TwfConfigProfileExplainWorkflowRequestCandidate,
) -> dict[str, Any]:
    run_workspace = getattr(request.config_context, "run_workspace", None)
    configured = run_workspace.to_policy_kwargs() if run_workspace is not None else {}
    entrypoint_keys = set(request.entrypoint_explicit_args)
    entrypoint_workspace_requested = bool(
        {
            "enable_run_workspace",
            "run_workspace_root",
            "run_workspace_retention_policy",
            "run_workspace_cleanup_policy",
            "run_workspace_max_write_bytes",
        }
        & entrypoint_keys
    )
    enabled_by_default = bool(getattr(run_workspace, "enabled_by_default", False))
    source = "entrypoint_explicit_args" if entrypoint_workspace_requested else (
        "profile_config" if enabled_by_default else "default_values"
    )
    return {
        "enabled": bool(request.run_workspace_enabled),
        "root": request.run_workspace_root,
        "retention_policy": request.run_workspace_retention_policy
        or configured.get("retention_policy", "keep"),
        "cleanup_policy": request.run_workspace_cleanup_policy
        or configured.get("cleanup_policy", "manual"),
        "max_write_bytes": request.run_workspace_max_write_bytes
        or configured.get("max_write_bytes", 65536),
        "source": source,
    }


def _live_llm_summary(
    request: TwfConfigProfileExplainWorkflowRequestCandidate,
) -> dict[str, Any]:
    live_llm = getattr(request.config_context, "live_llm", None)
    entrypoint_keys = set(request.entrypoint_explicit_args)
    entrypoint_live_requested = bool(
        {
            "request_live_llm",
            "request_ollama",
            "allow_live_llm",
            "allow_ollama",
            "ollama_api_base",
            "live_llm_timeout_seconds",
        }
        & entrypoint_keys
    )
    source = "entrypoint_explicit_args" if entrypoint_live_requested else (
        "profile_config" if live_llm is not None else "default_values"
    )
    status = "not_requested"
    if request.request_live_llm or request.request_ollama:
        status = (
            "requested_and_allowed"
            if request.allow_live_llm and request.allow_ollama
            else "requested_not_fully_allowed"
        )
    return {
        "status": status,
        "source": source,
        "request_live_llm": request.request_live_llm,
        "request_ollama": request.request_ollama,
        "allow_live_llm": request.allow_live_llm,
        "allow_ollama": request.allow_ollama,
        "profile": getattr(live_llm, "profile", None),
        "model_name": getattr(live_llm, "model_name", None),
        "ollama_api_base": request.ollama_api_base
        or getattr(live_llm, "ollama_api_base", None),
        "timeout_seconds": request.live_llm_timeout_seconds
        or getattr(live_llm, "timeout_seconds", None),
        "raw_prompt_included": False,
    }


def _governance_boundary_summary(
    request: TwfConfigProfileExplainWorkflowRequestCandidate,
) -> dict[str, Any]:
    refs_present = {
        "approval_ref": bool(request.approval_ref),
        "audit_ref": bool(request.audit_ref),
        "sanitized_evidence_ref": bool(request.sanitized_evidence_ref),
        "governance_summary_output_ref": bool(request.governance_summary_output_ref),
    }
    status = "provided" if all(refs_present.values()) else "missing"
    return {
        "status": status,
        "operator_approved": request.operator_approved,
        "refs_present": refs_present,
        "managed_parameters": sorted(MANAGED_GOVERNANCE_PARAMETERS),
        "raw_refs_included": False,
    }


def _build_config_profile_explain_task_context(
    request: TwfConfigProfileExplainWorkflowRequestCandidate,
    facts: TwfConfigProfileExplainFactsCandidate,
) -> TwfRunContextCandidate:
    return build_twf_run_context(
        workflow_name=TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
        task_kind=TWF_CONFIG_PROFILE_EXPLAIN_TASK_KIND,
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
            "requested_focus": list(facts.requested_focus),
            "does_not_call_model": True,
        },
    )


def _create_config_profile_explain_run_workspace(
    request: TwfConfigProfileExplainWorkflowRequestCandidate,
    task_context: TwfRunContextCandidate,
) -> TwfRunWorkspaceStateCandidate | None:
    if not request.run_workspace_enabled and not request.run_workspace_root:
        return None
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


def _finalize_config_profile_explain_run_workspace(
    run_workspace: TwfRunWorkspaceStateCandidate | None,
    *,
    status: str,
    terminal_display_text: str,
    facts: TwfConfigProfileExplainFactsCandidate,
    explain_context: TwfConfigProfileExplainContextCandidate,
) -> TwfRunWorkspaceStateCandidate | None:
    if run_workspace is None or not run_workspace.workspace_created:
        return run_workspace
    max_write_bytes = int(run_workspace.metadata.get("max_write_bytes") or 65536)
    run_workspace, _ = write_twf_run_workspace_json(
        run_workspace,
        relative_path="evidence/config_explain_context.json",
        payload=_config_explain_context_workspace_payload(explain_context),
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
            "workflow": TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
            "status": status,
            "task_kind": facts.task_kind,
            "requested_focus": list(facts.requested_focus),
            "matched_terms": list(facts.matched_terms),
            "model_call_count": 0,
            "no_live": True,
            "fail_safe": False,
            "template_version": TWF_CONFIG_PROFILE_EXPLAIN_TEMPLATE_VERSION,
            "config_context_available": explain_context.config_context_available,
        },
        kind="result",
        max_write_bytes=max_write_bytes,
    )
    run_workspace = finalize_twf_run_workspace(
        run_workspace,
        status=status,
        metadata={
            "workflow": TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
            "model_call_count": 0,
            "fail_safe": False,
            "template_version": TWF_CONFIG_PROFILE_EXPLAIN_TEMPLATE_VERSION,
        },
    )
    run_workspace, _ = cleanup_twf_run_workspace(run_workspace, status=status)
    return run_workspace


def _config_explain_context_workspace_payload(
    explain_context: TwfConfigProfileExplainContextCandidate,
) -> dict[str, Any]:
    return {
        "status": explain_context.status,
        "config_root_sanitized": explain_context.config_root_sanitized,
        "environment": explain_context.environment,
        "profile": explain_context.profile,
        "requested_focus": list(explain_context.requested_focus),
        "precedence": list(explain_context.precedence),
        "tool_exposure_summary": explain_context.tool_exposure_summary,
        "reference_reader_summary": explain_context.reference_reader_summary,
        "run_workspace_summary": explain_context.run_workspace_summary,
        "live_llm_summary": explain_context.live_llm_summary,
        "governance_boundary_summary": explain_context.governance_boundary_summary,
        "effective_values": [
            {
                "name": value.name,
                "effective_value": value.effective_value,
                "source": value.source,
                "note": value.note,
            }
            for value in explain_context.effective_values
        ],
        "risk_boundaries": list(explain_context.risk_boundaries),
        "warnings": list(explain_context.warnings),
        "blocking_reasons": list(explain_context.blocking_reasons),
        "redaction_applied": True,
        "does_not_read_raw_config_directly": True,
        "does_not_execute_tools": True,
        "does_not_call_model": True,
    }


def _blocked_explain_context(
    request: TwfConfigProfileExplainWorkflowRequestCandidate,
    facts: TwfConfigProfileExplainFactsCandidate,
    task_context: TwfRunContextCandidate,
) -> TwfConfigProfileExplainContextCandidate:
    return TwfConfigProfileExplainContextCandidate(
        status="blocked",
        config_context_available=request.config_context is not None,
        config_context_source="blocked_before_config_explain",
        config_root_sanitized=_sanitize_path_label(request.config_root),
        environment=request.environment,
        profile=request.profile,
        precedence=TWF_CONFIG_PRECEDENCE,
        requested_focus=facts.requested_focus,
        tool_exposure_summary={},
        reference_reader_summary={},
        run_workspace_summary={},
        live_llm_summary={},
        governance_boundary_summary={},
        effective_values=(),
        risk_boundaries=("preflight_blocked",),
        blocking_reasons=task_context.preflight.blocking_reasons,
        warnings=task_context.preflight.warnings,
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


def _preflight_blocked_terminal_display(
    task_context: TwfRunContextCandidate,
) -> str:
    reasons = ", ".join(task_context.preflight.blocking_reasons)
    return "\n".join(
        [
            "配置解释结果",
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
            "配置解释结果",
            "",
            "风险边界",
            f"- run workspace blocked: {reasons or 'unknown'}",
            f"- run_id: {task_context.run_id}",
        ]
    )


def _task_context_metadata(task_context: TwfRunContextCandidate) -> dict[str, Any]:
    return {
        "task_control": twf_run_context_status_dict(task_context),
    }


def _config_explain_context_metadata(
    explain_context: TwfConfigProfileExplainContextCandidate,
) -> dict[str, Any]:
    return {
        "config_explain": {
            "status": explain_context.status,
            "config_context_available": explain_context.config_context_available,
            "requested_focus": list(explain_context.requested_focus),
            "risk_boundaries": list(explain_context.risk_boundaries),
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


def _requested_focus(lowered_text: str) -> tuple[str, ...]:
    focus: list[str] = []
    if "tool exposure" in lowered_text or "工具暴露" in lowered_text:
        focus.append("tool_exposure")
    if "reference-reader" in lowered_text or "reference reader" in lowered_text:
        focus.append("reference_reader")
    if "run workspace" in lowered_text or "运行工作区" in lowered_text:
        focus.append("run_workspace")
    if "live llm" in lowered_text:
        focus.append("live_llm")
    if "ollama" in lowered_text:
        focus.append("ollama")
    if "approval" in lowered_text or "audit" in lowered_text:
        focus.append("governance_refs")
    if "覆盖关系" in lowered_text or "配置生效" in lowered_text:
        focus.append("config_precedence")
    return tuple(_ordered_unique(focus or CONFIG_PROFILE_EXPLAIN_FOCUS_TERMS))


def _requests_protected_runtime_open(value: str) -> bool:
    lowered = value.lower()
    has_runtime = any(term.lower() in lowered for term in PROTECTED_RUNTIME_TERMS)
    if not has_runtime:
        return False
    return any(marker in value for marker in RUNTIME_OPEN_MARKERS)


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
