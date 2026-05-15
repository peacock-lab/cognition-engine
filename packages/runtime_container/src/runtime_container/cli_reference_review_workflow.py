"""CLI reference review workflow for governed document review tasks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any

from contract_core.llm_invocation import (
    GovernedLlmInvocationService,
    LlmGovernancePrecondition,
    LlmInvocationResult,
)
from contract_core.model_routing import ModelRouteFacts
from runtime_container.cli_plan_workflow import (
    DEFAULT_PLAN_MODEL_NAME,
    PLAN_DISPLAY_PREVIEW_LIMIT,
    detect_cli_plan_request,
)
from runtime_container.cli_reference_reader import (
    REFERENCE_READER_TOOL_NAME,
    CliReferenceReadRequestCandidate,
    read_cli_reference,
)
from runtime_container.cli_run_workspace import (
    CliRunWorkspaceStateCandidate,
    build_cli_run_workspace_policy,
    cleanup_cli_run_workspace,
    cli_run_workspace_status_dict,
    create_cli_run_workspace,
    finalize_cli_run_workspace,
    write_cli_run_workspace_json,
    write_cli_run_workspace_text,
)
from runtime_container.cli_task_control import (
    CliTaskRunContextCandidate,
    build_cli_task_run_context,
    cli_task_run_context_status_dict,
    finalize_cli_task_run_context,
)
from runtime_container.cli_tool_exposure_profile import (
    cli_tool_exposure_profile_status_dict,
    resolve_cli_tool_exposure_profile,
)
from runtime_container.cli_tool_loading_validation import (
    cli_tool_loading_gate_status_dict,
    validate_cli_tool_loading_gate,
)
from runtime_container.llm_invocation_facade import (
    RuntimeContainerLlmInvocationFacade,
    build_runtime_container_llm_invocation_request,
)


CLI_REFERENCE_REVIEW_WORKFLOW_NAME = "cli_reference_review_workflow"
CLI_REFERENCE_REVIEW_TASK_KIND = "reference_review"
CLI_REFERENCE_REVIEW_TEMPLATE_VERSION = "reference_review_template_v1"
REFERENCE_REVIEW_CONTEXT_TOTAL_CHAR_LIMIT = 1800
REFERENCE_REVIEW_PROMPT_PREVIEW_LIMIT = 80
REFERENCE_REVIEW_KEYWORDS = (
    "审查",
    "复核",
    "检查",
    "评审",
    "总结",
    "提炼",
    "对比",
    "差异",
    "风险",
    "问题",
    "建议",
    "是否符合",
    "是否一致",
    "是否需要更新",
    "看看",
)
REFERENCE_REVIEW_STRONG_KEYWORDS = (
    "审查",
    "复核",
    "检查",
    "评审",
    "对比",
    "差异",
    "风险",
    "问题",
    "是否符合",
    "是否一致",
    "是否需要更新",
)
REFERENCE_REVIEW_TOPIC_HINTS = (
    "主线",
    "任务包",
    "结果包",
    "路线图",
    "策略",
    "ADR",
    "文档",
    "资料",
    "验收",
    "边界",
)
REFERENCE_REVIEW_NO_LIVE_NOTE = (
    "no-live 路径：本轮基于受控资料 excerpt 生成规则化审查结果，未调用模型。"
)
REFERENCE_REVIEW_FAIL_SAFE_MESSAGE = (
    "reference review workflow 已进入受控失败边界：本轮未展示 raw provider response。"
)
REFERENCE_REVIEW_TEMPLATE_SECTIONS = (
    "主要结论",
    "判断依据",
    "发现的问题",
    "风险边界",
    "建议动作",
)
REFERENCE_REVIEW_ALIGNMENT_MARKERS = (
    "符合当前主线",
    "符合主线",
    "当前主线",
    "通过",
    "收口",
    "继续推进",
)
REFERENCE_REVIEW_BOUNDARY_MARKERS = (
    "禁止",
    "暂不",
    "不需要",
    "不应",
    "关闭",
    "阻止",
    "风险",
    "边界",
)
REFERENCE_REVIEW_RUNTIME_BOUNDARY_MARKERS = (
    *REFERENCE_REVIEW_BOUNDARY_MARKERS,
    "未打开",
    "未接入",
    "没有打开",
    "没有接入",
    "继续关闭",
    "保持关闭",
)
REFERENCE_REVIEW_PROTECTED_RUNTIME_TERMS = (
    "Agent runtime",
    "Skills runtime",
    "ADK SkillRegistry",
)
REFERENCE_REVIEW_RUNTIME_ENABLE_MARKERS = (
    "打开",
    "开启",
    "启用",
    "接入",
    "集成",
    "开始集成",
    "上线",
    "运行",
)
REFERENCE_REVIEW_RUNTIME_DENY_MARKERS = (
    "不打开",
    "不应打开",
    "不得打开",
    "不要打开",
    "禁止打开",
    "不接入",
    "不应接入",
    "不得接入",
    "暂不接入",
    "保持关闭",
    "另开评议",
)
REFERENCE_REVIEW_RUNTIME_BOUNDARY_ACTION = (
    "保持 {terms} 关闭；如需重新打开，另开评议任务并补充审批、"
    "风险分级和验收证据。"
)


@dataclass(frozen=True)
class CliReferenceReviewWorkflowRequestCandidate:
    """Request entering the governed CLI reference review workflow."""

    user_text: str
    chat_session_id: str | None = None
    turn_index: int | None = None
    history: tuple[Mapping[str, str], ...] = ()
    live_model_allowed: bool = False
    llm_invocation_service: GovernedLlmInvocationService | None = None
    approval_ref: str | None = None
    audit_ref: str | None = None
    sanitized_evidence_ref: str | None = None
    risk_level: str = "low"
    output_budget: int | None = PLAN_DISPLAY_PREVIEW_LIMIT
    live_gate: str | None = None
    user_passthrough_parameters: Mapping[str, Any] = field(default_factory=dict)
    reference_paths: tuple[str, ...] = ()
    reference_repo_root: str | None = None
    reference_profile_name: str = "readonly_reference"
    reference_profile_config: Mapping[str, Any] | None = None
    reference_session_args: Mapping[str, Any] = field(default_factory=dict)
    reference_cli_explicit_args: Mapping[str, Any] = field(default_factory=dict)
    run_workspace_root: str | None = None
    run_workspace_enabled: bool = False
    run_workspace_retention_policy: str = "keep"
    run_workspace_cleanup_policy: str = "manual"
    run_workspace_max_write_bytes: int = 65536
    model_name: str = DEFAULT_PLAN_MODEL_NAME
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CliReferenceReviewFactsCandidate:
    """Minimal facts extracted from a reference review request."""

    original_text: str
    task_kind: str
    review_intents: tuple[str, ...] = ()
    topic_hints: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CliReferenceReviewContextCandidate:
    """Bounded reference context consumed by the review workflow."""

    status: str
    requested_references: tuple[str, ...] = ()
    consumed_reference_count: int = 0
    reference_excerpts: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CliReferenceReviewDraftCandidate:
    """Review draft before final terminal formatting."""

    draft_text: str
    prompt_preview_sanitized: str | None
    model_call_count: int = 0
    source: str = "local_reference_rules"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CliReferenceReviewWorkflowResultCandidate:
    """Final result returned to the CLI chat entrypoint."""

    triggered: bool
    terminal_display_text: str
    request: CliReferenceReviewWorkflowRequestCandidate
    facts: CliReferenceReviewFactsCandidate
    reference_context: CliReferenceReviewContextCandidate
    draft: CliReferenceReviewDraftCandidate | None
    model_call_count: int = 0
    no_live: bool = False
    fail_safe: bool = False
    task_run_context: CliTaskRunContextCandidate | None = None
    run_workspace: CliRunWorkspaceStateCandidate | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def detect_cli_reference_review_request(
    user_text: str,
    *,
    reference_paths: Sequence[str] = (),
) -> bool:
    """Return whether a turn should route to reference review."""

    normalized = _compact_text(user_text)
    if not normalized or not tuple(path for path in reference_paths if path.strip()):
        return False
    has_review_intent = any(
        keyword.lower() in normalized.lower()
        for keyword in REFERENCE_REVIEW_KEYWORDS
    )
    if not has_review_intent:
        return False
    has_strong_review_intent = any(
        keyword.lower() in normalized.lower()
        for keyword in REFERENCE_REVIEW_STRONG_KEYWORDS
    )
    if detect_cli_plan_request(user_text) and not has_strong_review_intent:
        return False
    return True


def extract_cli_reference_review_facts(
    request: CliReferenceReviewWorkflowRequestCandidate,
) -> CliReferenceReviewFactsCandidate:
    """Extract bounded review intent facts from the user request."""

    normalized = _compact_text(request.user_text)
    review_intents = tuple(
        keyword
        for keyword in REFERENCE_REVIEW_KEYWORDS
        if keyword.lower() in normalized.lower()
    )
    topic_hints = tuple(
        hint for hint in REFERENCE_REVIEW_TOPIC_HINTS if hint.lower() in normalized.lower()
    )
    return CliReferenceReviewFactsCandidate(
        original_text=request.user_text,
        task_kind=CLI_REFERENCE_REVIEW_TASK_KIND,
        review_intents=review_intents,
        topic_hints=topic_hints,
        metadata={
            "workflow_stage": "intent_extraction",
            "reference_path_count": len(request.reference_paths),
        },
    )


def run_cli_reference_review_workflow(
    request: CliReferenceReviewWorkflowRequestCandidate,
) -> CliReferenceReviewWorkflowResultCandidate:
    """Run the governed CLI reference review workflow."""

    facts = extract_cli_reference_review_facts(request)
    task_context = _build_reference_review_task_context(request, facts)
    if not task_context.preflight.allowed:
        task_context = finalize_cli_task_run_context(
            task_context,
            status="blocked",
            metadata={"blocked_before_reference_read": True},
        )
        reference_context = CliReferenceReviewContextCandidate(status="not_started")
        return CliReferenceReviewWorkflowResultCandidate(
            triggered=True,
            terminal_display_text=_preflight_blocked_terminal_display(task_context),
            request=request,
            facts=facts,
            reference_context=reference_context,
            draft=None,
            fail_safe=True,
            task_run_context=task_context,
            metadata={
                "workflow": CLI_REFERENCE_REVIEW_WORKFLOW_NAME,
                **_task_context_metadata(task_context),
            },
        )

    run_workspace = _create_reference_review_run_workspace(request, task_context)
    if run_workspace is not None and not run_workspace.workspace_created:
        task_context = _finalize_task_context_with_run_workspace(
            task_context,
            status="blocked",
            run_workspace=run_workspace,
            metadata={
                "blocked_before_reference_read": True,
                "failure_stage": "run_workspace",
            },
        )
        reference_context = CliReferenceReviewContextCandidate(status="not_started")
        return CliReferenceReviewWorkflowResultCandidate(
            triggered=True,
            terminal_display_text=_workspace_blocked_terminal_display(
                task_context,
                run_workspace,
            ),
            request=request,
            facts=facts,
            reference_context=reference_context,
            draft=None,
            fail_safe=True,
            task_run_context=task_context,
            run_workspace=run_workspace,
            metadata={
                "workflow": CLI_REFERENCE_REVIEW_WORKFLOW_NAME,
                **_task_context_metadata(task_context),
                **_run_workspace_metadata(run_workspace),
            },
        )

    reference_context = _build_reference_review_context(request, task_context)
    if reference_context.status == "blocked":
        display = _reference_blocked_terminal_display(task_context, reference_context)
        run_workspace = _finalize_reference_review_run_workspace(
            run_workspace,
            status="blocked",
            terminal_display_text=display,
            facts=facts,
            reference_context=reference_context,
            model_call_count=0,
            fail_safe=True,
        )
        task_context = finalize_cli_task_run_context(
            task_context,
            status="blocked",
            evidence_refs=(
                *reference_context.evidence_refs,
                *(run_workspace.evidence_refs if run_workspace else ()),
            ),
            artifact_refs=_run_workspace_artifact_and_result_refs(run_workspace),
            workspace_ref=run_workspace.workspace_ref if run_workspace else None,
            workspace_created=run_workspace.workspace_created if run_workspace else None,
            retention_policy=run_workspace.retention_policy if run_workspace else None,
            cleanup_policy=run_workspace.cleanup_policy if run_workspace else None,
            workspace_metadata=cli_run_workspace_status_dict(run_workspace),
            metadata={
                "blocked_before_model_call": True,
                "failure_stage": "reference_context",
            },
        )
        return CliReferenceReviewWorkflowResultCandidate(
            triggered=True,
            terminal_display_text=display,
            request=request,
            facts=facts,
            reference_context=reference_context,
            draft=None,
            fail_safe=True,
            task_run_context=task_context,
            run_workspace=run_workspace,
            metadata={
                "workflow": CLI_REFERENCE_REVIEW_WORKFLOW_NAME,
                **_task_context_metadata(task_context),
                **_reference_context_metadata(reference_context),
                **_run_workspace_metadata(run_workspace),
            },
        )

    draft = build_cli_reference_review_draft(request, facts, reference_context)
    status = "succeeded"
    fail_safe = False
    if draft.source == "controlled_live_failed":
        status = "failed"
        fail_safe = True
        display = _failed_terminal_display(reference_context)
    else:
        display = format_cli_reference_review_for_terminal(
            draft,
            facts,
            reference_context,
            no_live=not request.live_model_allowed,
        )
    run_workspace = _finalize_reference_review_run_workspace(
        run_workspace,
        status=status,
        terminal_display_text=display,
        facts=facts,
        reference_context=reference_context,
        model_call_count=draft.model_call_count,
        fail_safe=fail_safe,
    )
    task_context = finalize_cli_task_run_context(
        task_context,
        status=status,
        evidence_refs=(
            *reference_context.evidence_refs,
            *(run_workspace.evidence_refs if run_workspace else ()),
        ),
        artifact_refs=(
            f"candidate-artifact://{task_context.run_id}/terminal_display",
            *_run_workspace_artifact_and_result_refs(run_workspace),
        ),
        workspace_ref=run_workspace.workspace_ref if run_workspace else None,
        workspace_created=run_workspace.workspace_created if run_workspace else None,
        retention_policy=run_workspace.retention_policy if run_workspace else None,
        cleanup_policy=run_workspace.cleanup_policy if run_workspace else None,
        workspace_metadata=cli_run_workspace_status_dict(run_workspace),
        metadata={"failure_stage": "review_generation"} if fail_safe else {},
    )
    return CliReferenceReviewWorkflowResultCandidate(
        triggered=True,
        terminal_display_text=display,
        request=request,
        facts=facts,
        reference_context=reference_context,
        draft=draft,
        model_call_count=draft.model_call_count,
        no_live=not request.live_model_allowed,
        fail_safe=fail_safe,
        task_run_context=task_context,
        run_workspace=run_workspace,
        metadata={
            "workflow": CLI_REFERENCE_REVIEW_WORKFLOW_NAME,
            **_task_context_metadata(task_context),
            **_reference_context_metadata(reference_context),
            **_run_workspace_metadata(run_workspace),
        },
    )


def build_cli_reference_review_draft(
    request: CliReferenceReviewWorkflowRequestCandidate,
    facts: CliReferenceReviewFactsCandidate,
    reference_context: CliReferenceReviewContextCandidate,
) -> CliReferenceReviewDraftCandidate:
    """Build a local or controlled-live reference review draft."""

    prompt_preview = build_cli_reference_review_prompt_preview(
        facts,
        reference_context,
    )
    if not request.live_model_allowed:
        return CliReferenceReviewDraftCandidate(
            draft_text=_local_reference_review_draft(facts, reference_context),
            prompt_preview_sanitized=prompt_preview,
            model_call_count=0,
            source="local_reference_rules",
            metadata={
                "no_live": True,
                "review_template_version": CLI_REFERENCE_REVIEW_TEMPLATE_VERSION,
            },
        )
    llm_result = _invoke_reference_review_llm(
        request,
        prompt_preview=prompt_preview,
        reference_context=reference_context,
    )
    if not llm_result.success or not llm_result.response_non_empty:
        return CliReferenceReviewDraftCandidate(
            draft_text="",
            prompt_preview_sanitized=prompt_preview,
            model_call_count=1,
            source="controlled_live_failed",
            metadata={
                "failure_type": llm_result.failure_type,
                "error_message_sanitized": llm_result.error_message_sanitized,
            },
        )
    return CliReferenceReviewDraftCandidate(
        draft_text=_llm_display_text(llm_result),
        prompt_preview_sanitized=prompt_preview,
        model_call_count=1,
        source="controlled_live",
        metadata={
            "llm_invocation_result_ref": llm_result.request_id,
            "sanitized_response_length": llm_result.sanitized_response_length,
            "review_template_version": CLI_REFERENCE_REVIEW_TEMPLATE_VERSION,
        },
    )


def build_cli_reference_review_prompt_preview(
    facts: CliReferenceReviewFactsCandidate,
    reference_context: CliReferenceReviewContextCandidate,
) -> str:
    """Build a compact sanitized prompt preview for governed LLM calls."""

    labels = tuple(reference_context.metadata.get("reference_labels", ()))
    parts = [
        "资料审查",
        _join_or_default(facts.review_intents, "审查"),
        _join_or_default(facts.topic_hints, "主题未指定"),
        "资料:" + _join_or_default(labels, "已读取"),
        "输出结论、依据、问题、风险、建议",
    ]
    return _preview_text("，".join(parts), REFERENCE_REVIEW_PROMPT_PREVIEW_LIMIT)


def format_cli_reference_review_for_terminal(
    draft: CliReferenceReviewDraftCandidate,
    facts: CliReferenceReviewFactsCandidate,
    reference_context: CliReferenceReviewContextCandidate,
    *,
    no_live: bool,
) -> str:
    """Build final terminal display text for the review workflow."""

    labels = tuple(reference_context.metadata.get("reference_labels", ()))
    evidence_lines = _evidence_lines(labels, reference_context.evidence_refs)
    scope_lines = [f"- {line}" for line in evidence_lines] or ["- 未生成证据引用"]
    draft_text = draft.draft_text.strip()
    result_lines = _review_display_lines(draft_text)
    lines = [
        "资料审查结果",
        "",
        "审查范围",
        *scope_lines,
        "",
        "审查输出",
        *result_lines,
        "",
        "证据引用",
        *scope_lines,
    ]
    if no_live:
        lines.extend(("", "执行说明", f"- {REFERENCE_REVIEW_NO_LIVE_NOTE}"))
    if facts.review_intents:
        lines.extend(("", "识别意图", "- " + "、".join(facts.review_intents)))
    return "\n".join(lines)


def _review_display_lines(draft_text: str) -> list[str]:
    if not draft_text:
        return _fallback_review_template_lines("模型未返回可展示审查内容。")
    try:
        decoded = json.loads(draft_text)
    except json.JSONDecodeError:
        return _plain_review_lines(draft_text)
    if not isinstance(decoded, dict):
        return _plain_review_lines(draft_text)

    response = decoded.get("response_to_user") or decoded.get("response")
    if isinstance(response, str) and response.strip():
        return _plain_review_lines(response.strip())

    conclusion = _decoded_string(
        decoded,
        (
            "main_conclusion",
            "conclusion",
            "alignment_judgement",
            "alignment",
            "符合性判断",
            "主要结论",
        ),
    )
    evidence_basis = _decoded_items(
        decoded,
        ("evidence_basis", "basis", "判断依据", "依据"),
    )
    issues = _decoded_items(
        decoded,
        ("issues", "problems", "发现的问题", "问题"),
    )
    risk_boundaries = _decoded_items(
        decoded,
        ("risk_boundaries", "risks", "boundaries", "风险边界", "风险"),
    )
    suggestions = _decoded_items(
        decoded,
        ("suggestions", "next_actions", "actions", "建议动作", "建议"),
    )
    review_context_text = "\n".join(
        item
        for item in (
            conclusion,
            *evidence_basis,
            *issues,
            *risk_boundaries,
            *suggestions,
        )
        if item
    )
    safe_suggestions = _sanitize_review_suggestions(
        suggestions or ("继续按当前主线推进，并在下一任务前复核证据引用。",),
        context_text=review_context_text,
    )

    lines: list[str] = []
    _append_review_section(
        lines,
        "主要结论",
        (conclusion or "模型未明确给出符合性判断，请结合证据引用人工复核。",),
        bullet="-",
    )
    _append_review_section(
        lines,
        "判断依据",
        evidence_basis
        or ("模型未单独列出判断依据，请以审查范围与证据引用回看资料。",),
    )
    _append_review_section(
        lines,
        "发现的问题",
        issues or ("模型未单独列出具体问题，仍需保留人工复核。",),
    )
    _append_review_section(
        lines,
        "风险边界",
        risk_boundaries
        or ("模型未单独声明风险边界，不得据此扩大执行范围。",),
    )
    _append_review_section(
        lines,
        "建议动作",
        safe_suggestions,
    )
    return lines


def _plain_review_lines(draft_text: str) -> list[str]:
    lines = [line for line in draft_text.splitlines() if line.strip()]
    if _has_review_template_sections(lines):
        return _sanitize_review_template_lines(lines, context_text=draft_text)
    return _fallback_review_template_lines(draft_text)


def _fallback_review_template_lines(main_text: str) -> list[str]:
    lines: list[str] = []
    _append_review_section(lines, "主要结论", (_compact_text(main_text),), bullet="-")
    _append_review_section(
        lines,
        "判断依据",
        ("模型输出未拆分判断依据，请以审查范围与证据引用回看资料。",),
    )
    _append_review_section(
        lines,
        "发现的问题",
        ("模型输出未单独列出问题，仍需保留人工复核。",),
    )
    _append_review_section(
        lines,
        "风险边界",
        ("模型输出未单独列出风险边界，不得据此扩大执行范围。",),
    )
    _append_review_section(
        lines,
        "建议动作",
        ("按证据引用复核资料后，再决定是否进入下一任务。",),
    )
    return lines


def _has_review_template_sections(lines: Sequence[str]) -> bool:
    joined = "\n".join(lines)
    return sum(section in joined for section in REFERENCE_REVIEW_TEMPLATE_SECTIONS) >= 3


def _decoded_string(decoded: Mapping[str, Any], keys: Sequence[str]) -> str:
    for key in keys:
        value = decoded.get(key)
        if isinstance(value, str) and value.strip():
            return _compact_text(value)
    return ""


def _decoded_items(decoded: Mapping[str, Any], keys: Sequence[str]) -> tuple[str, ...]:
    for key in keys:
        value = decoded.get(key)
        if isinstance(value, str) and value.strip():
            return (_compact_text(value),)
        if isinstance(value, list | tuple):
            items = tuple(
                _compact_text(str(item))
                for item in value
                if str(item).strip()
            )
            if items:
                return items
    return ()


def _sanitize_review_suggestions(
    suggestions: Sequence[str],
    *,
    context_text: str,
) -> tuple[str, ...]:
    return tuple(
        _sanitize_review_suggestion(item, context_text=context_text)
        for item in suggestions
        if item
    )


def _sanitize_review_template_lines(
    lines: Sequence[str],
    *,
    context_text: str,
) -> list[str]:
    sanitized: list[str] = []
    in_suggestion_section = False
    for line in lines:
        stripped = line.strip()
        if stripped in REFERENCE_REVIEW_TEMPLATE_SECTIONS:
            in_suggestion_section = stripped == "建议动作"
            sanitized.append(line)
            continue
        if in_suggestion_section:
            sanitized.append(
                _sanitize_review_suggestion_line(line, context_text=context_text)
            )
            continue
        sanitized.append(line)
    return sanitized


def _sanitize_review_suggestion_line(line: str, *, context_text: str) -> str:
    prefix_match = re.match(r"^(\s*(?:[-*]|\d+[.．、])\s*)(.*)$", line)
    if prefix_match is None:
        return _sanitize_review_suggestion(line, context_text=context_text)
    prefix, body = prefix_match.groups()
    return prefix + _sanitize_review_suggestion(body, context_text=context_text)


def _sanitize_review_suggestion(item: str, *, context_text: str) -> str:
    compact = _compact_text(item)
    if not _review_suggestion_needs_boundary_intercept(
        compact,
        context_text=context_text,
    ):
        return compact
    terms = " / ".join(_protected_runtime_terms(f"{compact}\n{context_text}"))
    return REFERENCE_REVIEW_RUNTIME_BOUNDARY_ACTION.format(
        terms=terms or "Agent runtime / Skills runtime",
    )


def _review_suggestion_needs_boundary_intercept(
    item: str,
    *,
    context_text: str,
) -> bool:
    if not _contains_protected_runtime_term(item):
        return False
    if not any(marker in item for marker in REFERENCE_REVIEW_RUNTIME_ENABLE_MARKERS):
        return False
    if any(marker in item for marker in REFERENCE_REVIEW_RUNTIME_DENY_MARKERS):
        return False
    return _contains_protected_runtime_boundary(context_text)


def _contains_protected_runtime_boundary(value: str) -> bool:
    if not _contains_protected_runtime_term(value):
        return False
    return any(marker in value for marker in REFERENCE_REVIEW_RUNTIME_BOUNDARY_MARKERS)


def _contains_protected_runtime_term(value: str) -> bool:
    return any(term in value for term in REFERENCE_REVIEW_PROTECTED_RUNTIME_TERMS)


def _protected_runtime_terms(value: str) -> tuple[str, ...]:
    terms = [
        term for term in REFERENCE_REVIEW_PROTECTED_RUNTIME_TERMS if term in value
    ]
    return tuple(_ordered_unique(terms))


def _append_review_section(
    lines: list[str],
    title: str,
    items: Sequence[str],
    *,
    bullet: str = "numbered",
) -> None:
    if lines:
        lines.append("")
    lines.append(title)
    if bullet == "-":
        lines.extend(f"- {item}" for item in items if item)
        return
    lines.extend(
        f"{index}. {item}"
        for index, item in enumerate((item for item in items if item), start=1)
    )


def _build_reference_review_task_context(
    request: CliReferenceReviewWorkflowRequestCandidate,
    facts: CliReferenceReviewFactsCandidate,
) -> CliTaskRunContextCandidate:
    return build_cli_task_run_context(
        workflow_name=CLI_REFERENCE_REVIEW_WORKFLOW_NAME,
        task_kind=facts.task_kind,
        session_id=request.chat_session_id,
        turn_index=request.turn_index,
        live_model_allowed=request.live_model_allowed,
        approval_ref=request.approval_ref,
        audit_ref=request.audit_ref,
        sanitized_evidence_ref=request.sanitized_evidence_ref,
        risk_level=request.risk_level,
        output_budget=request.output_budget,
        live_gate=request.live_gate,
        user_passthrough_parameters=request.user_passthrough_parameters,
        metadata={
            "source": "runtime_container.cli_reference_review_workflow",
            "review_intents": list(facts.review_intents),
            "topic_hints": list(facts.topic_hints),
        },
    )


def _build_reference_review_context(
    request: CliReferenceReviewWorkflowRequestCandidate,
    task_context: CliTaskRunContextCandidate,
) -> CliReferenceReviewContextCandidate:
    requested_references = tuple(_ordered_unique(request.reference_paths))
    if not requested_references:
        return CliReferenceReviewContextCandidate(
            status="blocked",
            blocking_reasons=("reference_paths_required",),
            metadata={"workflow_stage": "reference_context"},
        )

    repo_root = Path(request.reference_repo_root or Path.cwd()).expanduser().resolve()
    exposure = resolve_cli_tool_exposure_profile(
        profile_name=request.reference_profile_name,
        profile_config=request.reference_profile_config,
        repo_root=repo_root,
        session_args=request.reference_session_args,
        cli_explicit_args=request.reference_cli_explicit_args,
    )
    exposure_status = cli_tool_exposure_profile_status_dict(exposure)
    loading_gate = validate_cli_tool_loading_gate(
        exposure,
        operator_approved=bool(request.approval_ref),
        approval_ref=request.approval_ref,
    )
    loading_gate_status = cli_tool_loading_gate_status_dict(loading_gate)
    blocking: list[str] = list(exposure.blocking_reasons)
    warnings: list[str] = list(exposure.warnings)
    if exposure.status != "resolved":
        blocking.append("reference_tool_exposure_profile_blocked")
    blocking.extend(
        f"tool_loading_gate:{reason}" for reason in loading_gate.blocking_reasons
    )
    warnings.extend(loading_gate.warnings)
    if loading_gate.status != "passed":
        blocking.append("tool_loading_validation_blocked")
    if REFERENCE_READER_TOOL_NAME not in exposure.exposed_tool_names:
        blocking.append("reference_reader_not_exposed")
    if REFERENCE_READER_TOOL_NAME not in loading_gate.allowed_tool_names:
        blocking.append("reference_reader_not_allowed_by_risk_gate")
    if exposure.reference_reader_policy is None:
        blocking.append("reference_reader_policy_missing")

    read_results = []
    reference_excerpts: list[str] = []
    evidence_refs: list[str] = []
    reference_labels: list[str] = []
    if not blocking and exposure.reference_reader_policy is not None:
        for reference in requested_references:
            read_result = read_cli_reference(
                CliReferenceReadRequestCandidate(
                    reference=reference,
                    policy=exposure.reference_reader_policy,
                    purpose="cli_reference_review",
                    task_run_id=task_context.run_id,
                )
            )
            read_results.append(read_result)
            label = _reference_label(read_result.resolved_path, reference)
            reference_labels.append(label)
            warnings.extend(read_result.warnings)
            if read_result.evidence_ref:
                evidence_refs.append(read_result.evidence_ref)
            if not read_result.allowed:
                blocking.extend(
                    f"reference_read_blocked:{reason}"
                    for reason in read_result.blocking_reasons
                )
            else:
                reference_excerpts.append(
                    _reference_excerpt(
                        reference_label=label,
                        excerpt=read_result.content_excerpt,
                    )
                )

    bounded_excerpts = tuple(_bounded_reference_excerpts(reference_excerpts))
    status = "blocked" if blocking else "succeeded"
    return CliReferenceReviewContextCandidate(
        status=status,
        requested_references=requested_references,
        consumed_reference_count=0 if blocking else len(bounded_excerpts),
        reference_excerpts=() if blocking else bounded_excerpts,
        evidence_refs=tuple(_ordered_unique(evidence_refs)),
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "workflow_stage": "reference_context",
            "reference_reader_requested": True,
            "tool_exposure_profile": exposure_status,
            "tool_loading_gate": loading_gate_status,
            "reference_labels": tuple(reference_labels),
            "read_statuses": [
                {
                    "reference": result.reference,
                    "status": result.status,
                    "resolved_path": result.resolved_path,
                    "evidence_ref": result.evidence_ref,
                    "digest": result.reference_digest,
                    "line_count": result.line_count,
                    "char_count": result.char_count,
                    "truncated": result.truncated,
                    "redacted_line_count": result.redacted_line_count,
                    "blocking_reasons": list(result.blocking_reasons),
                    "warnings": list(result.warnings),
                }
                for result in read_results
            ],
            "does_not_execute_external_tools": True,
            "does_not_access_network": True,
        },
    )


def _local_reference_review_draft(
    facts: CliReferenceReviewFactsCandidate,
    reference_context: CliReferenceReviewContextCandidate,
) -> str:
    labels = tuple(reference_context.metadata.get("reference_labels", ()))
    excerpts_text = "\n".join(reference_context.reference_excerpts)
    findings = _reference_findings(excerpts_text)
    topic = "、".join(facts.topic_hints) if facts.topic_hints else "资料本身"
    alignment = (
        "资料与当前主线存在明确承接信号。"
        if findings["alignment_terms"]
        else "资料未显式给出完整符合性结论，需要人工结合上下文确认。"
    )
    lines = [
        "主要结论",
        (
            f"- {alignment}本轮已读取 "
            f"{reference_context.consumed_reference_count} 份受控资料，"
            f"审查主题聚焦 {topic}。"
        ),
    ]
    if labels:
        lines.append("- 覆盖资料：" + "、".join(labels) + "。")
    lines.extend(["", "判断依据"])
    if findings["alignment_terms"]:
        lines.append("1. 资料中出现主线 / 通过 / 收口类信号，可作为符合性判断依据。")
    else:
        lines.append("1. 资料 excerpt 未直接给出完整符合性声明，不能替代人工终审。")
    if findings["keyword_hits"]:
        lines.append("2. 命中能力关键词：" + "、".join(findings["keyword_hits"]) + "。")
    elif labels:
        lines.append("2. 依据受控资料标签与 reference-reader 证据引用进行回看。")
    lines.extend(["", "发现的问题"])
    if findings["risk_terms"]:
        lines.append(
            "1. 资料中出现风险 / 禁止 / 暂不接入类表述，需要在后续任务边界中保留。"
        )
    else:
        lines.append("1. 未从受控 excerpt 中识别到明显问题词，但仍需人工复核上下文。")
    if findings["next_step_terms"]:
        lines.append("2. 资料中存在下一步或后续任务信号，应转化为明确实施边界。")
    else:
        lines.append("2. 未识别到明确下一步信号，建议补充后续动作。")
    lines.extend(["", "风险边界"])
    if findings["risk_terms"]:
        lines.append("1. 风险 / 边界信号：" + "、".join(findings["risk_terms"]) + "。")
    else:
        lines.append("1. 暂未识别到显式风险边界，下一任务仍不得扩大运行时范围。")
    if "Agent runtime" in findings["keyword_hits"]:
        lines.append("2. Agent runtime 相关内容只能作为观察或关闭边界，不得自动打开。")
    if "Skills runtime" in findings["keyword_hits"]:
        lines.append("3. Skills runtime 相关内容只能作为观察或关闭边界，不得自动打开。")
    lines.extend(["", "建议动作"])
    lines.append("1. 下一任务只承接资料中明确允许的主线，不反推 Agent / Skills runtime。")
    lines.append("2. 保留 reference-reader、Tools gate 与 run workspace 证据链。")
    if findings["next_step_terms"]:
        lines.append("3. 将下一步信号转化为任务包中的明确验收标准。")
    else:
        lines.append("3. 先补足下一步动作，再决定是否进入实施任务。")
    return "\n".join(lines)


def _reference_findings(excerpts_text: str) -> dict[str, list[str]]:
    next_step_markers = ("下一步", "建议", "进入", "实施", "真实", "验收")
    keyword_markers = (
        "CLI",
        "task workflow",
        "reference-reader",
        "run workspace",
        "Agent runtime",
        "Skills runtime",
        "status_summary",
    )
    return {
        "risk_terms": [
            marker
            for marker in REFERENCE_REVIEW_BOUNDARY_MARKERS
            if marker in excerpts_text
        ],
        "next_step_terms": [
            marker for marker in next_step_markers if marker in excerpts_text
        ],
        "keyword_hits": [
            marker for marker in keyword_markers if marker.lower() in excerpts_text.lower()
        ],
        "alignment_terms": [
            marker
            for marker in REFERENCE_REVIEW_ALIGNMENT_MARKERS
            if marker.lower() in excerpts_text.lower()
        ],
    }


def _invoke_reference_review_llm(
    request: CliReferenceReviewWorkflowRequestCandidate,
    *,
    prompt_preview: str,
    reference_context: CliReferenceReviewContextCandidate,
) -> LlmInvocationResult:
    service = request.llm_invocation_service
    if service is None:
        raise ValueError(
            "llm_invocation_service is required for controlled-live reference review"
        )
    facade = RuntimeContainerLlmInvocationFacade(
        service=service,
        metadata={
            "source": "runtime_container.cli_reference_review_workflow",
            "workflow": CLI_REFERENCE_REVIEW_WORKFLOW_NAME,
            "purpose": "reference_review",
        },
    )
    invocation_request = build_runtime_container_llm_invocation_request(
        request_id=(
            "cli-reference-review-"
            f"{request.chat_session_id or 'session'}-{request.turn_index or 0}"
        ),
        route_facts=ModelRouteFacts(
            model_name=request.model_name,
            provider="litellm",
            source="runtime_container.cli_reference_review_workflow",
            metadata={
                "backend_provider": "ollama",
                "route_target": request.model_name,
                "route_kind": "adk_litellm",
                "does_not_call_model": True,
            },
        ),
        governance_precondition=LlmGovernancePrecondition(
            allowed=True,
            reason="cli_reference_review_controlled_live_allowed",
            decision="continue",
            governance_decision_ref=request.approval_ref,
            metadata={
                "audit_ref_present": bool(request.audit_ref),
                "sanitized_evidence_ref_present": bool(request.sanitized_evidence_ref),
                "risk_level": request.risk_level,
                "output_budget": request.output_budget,
            },
        ),
        prompt_ref=(
            "cli-reference-review-input://"
            f"{request.chat_session_id or 'session'}/{request.turn_index or 0}"
        ),
        prompt_preview_sanitized=prompt_preview,
        metadata={
            "source": "runtime_container.cli_reference_review_workflow",
            "interaction_mode": CLI_REFERENCE_REVIEW_WORKFLOW_NAME,
            "workflow_stage": "reference_review",
            "controlled_live": True,
            "live_llm_allowed": True,
            "ollama_allowed": True,
            "risk_level": request.risk_level,
            "output_budget": request.output_budget,
            "reference_context_status": reference_context.status,
            "reference_context_evidence_ref_count": len(reference_context.evidence_refs),
            "review_template_version": CLI_REFERENCE_REVIEW_TEMPLATE_VERSION,
            "reference_labels": list(
                reference_context.metadata.get("reference_labels", ())
            ),
            "reference_review_context": {
                "current_user_input": request.user_text,
                "reference_labels": list(
                    reference_context.metadata.get("reference_labels", ())
                ),
                "evidence_refs": list(reference_context.evidence_refs),
                "reference_excerpts": list(reference_context.reference_excerpts),
            },
        },
    )
    return facade.run(invocation_request)


def _create_reference_review_run_workspace(
    request: CliReferenceReviewWorkflowRequestCandidate,
    task_context: CliTaskRunContextCandidate,
) -> CliRunWorkspaceStateCandidate | None:
    if not request.run_workspace_enabled and not request.run_workspace_root:
        return None
    workspace_root = request.run_workspace_root or ".cognition-runs"
    policy = build_cli_run_workspace_policy(
        workspace_root=workspace_root,
        retention_policy=request.run_workspace_retention_policy,
        cleanup_policy=request.run_workspace_cleanup_policy,
        max_write_bytes=request.run_workspace_max_write_bytes,
    )
    return create_cli_run_workspace(
        policy=policy,
        workflow_name=task_context.workflow_name,
        run_id=task_context.run_id,
    )


def _finalize_reference_review_run_workspace(
    run_workspace: CliRunWorkspaceStateCandidate | None,
    *,
    status: str,
    terminal_display_text: str,
    facts: CliReferenceReviewFactsCandidate,
    reference_context: CliReferenceReviewContextCandidate,
    model_call_count: int,
    fail_safe: bool,
) -> CliRunWorkspaceStateCandidate | None:
    if run_workspace is None or not run_workspace.workspace_created:
        return run_workspace
    max_write_bytes = int(run_workspace.metadata.get("max_write_bytes") or 65536)
    if reference_context.status != "not_started":
        run_workspace, _ = write_cli_run_workspace_json(
            run_workspace,
            relative_path="evidence/reference_context.json",
            payload=_reference_context_workspace_payload(reference_context),
            kind="evidence",
            max_write_bytes=max_write_bytes,
        )
        for index, excerpt in enumerate(reference_context.reference_excerpts, start=1):
            run_workspace, _ = write_cli_run_workspace_text(
                run_workspace,
                relative_path=f"references/reference-{index:03d}.txt",
                text=excerpt,
                kind="reference",
                max_write_bytes=max_write_bytes,
            )
    run_workspace, _ = write_cli_run_workspace_text(
        run_workspace,
        relative_path="artifacts/terminal_display.txt",
        text=terminal_display_text + "\n",
        kind="artifact",
        max_write_bytes=max_write_bytes,
    )
    run_workspace, _ = write_cli_run_workspace_json(
        run_workspace,
        relative_path="results/workflow_result.json",
        payload={
            "workflow": CLI_REFERENCE_REVIEW_WORKFLOW_NAME,
            "status": status,
            "task_kind": facts.task_kind,
            "review_intents": list(facts.review_intents),
            "topic_hints": list(facts.topic_hints),
            "model_call_count": model_call_count,
            "fail_safe": fail_safe,
            "review_template_version": CLI_REFERENCE_REVIEW_TEMPLATE_VERSION,
            "reference_context_status": reference_context.status,
            "reference_evidence_refs": list(reference_context.evidence_refs),
        },
        kind="result",
        max_write_bytes=max_write_bytes,
    )
    run_workspace = finalize_cli_run_workspace(
        run_workspace,
        status=status,
        metadata={
            "workflow": CLI_REFERENCE_REVIEW_WORKFLOW_NAME,
            "model_call_count": model_call_count,
            "fail_safe": fail_safe,
            "review_template_version": CLI_REFERENCE_REVIEW_TEMPLATE_VERSION,
        },
    )
    run_workspace, _ = cleanup_cli_run_workspace(run_workspace, status=status)
    return run_workspace


def _finalize_task_context_with_run_workspace(
    task_context: CliTaskRunContextCandidate,
    *,
    status: str,
    run_workspace: CliRunWorkspaceStateCandidate | None,
    metadata: Mapping[str, Any] | None = None,
) -> CliTaskRunContextCandidate:
    return finalize_cli_task_run_context(
        task_context,
        status=status,
        artifact_refs=_run_workspace_artifact_and_result_refs(run_workspace),
        evidence_refs=run_workspace.evidence_refs if run_workspace else (),
        workspace_ref=run_workspace.workspace_ref if run_workspace else None,
        workspace_created=run_workspace.workspace_created if run_workspace else None,
        retention_policy=run_workspace.retention_policy if run_workspace else None,
        cleanup_policy=run_workspace.cleanup_policy if run_workspace else None,
        workspace_metadata=cli_run_workspace_status_dict(run_workspace),
        metadata=metadata,
    )


def _task_context_metadata(task_context: CliTaskRunContextCandidate) -> dict[str, Any]:
    return {"task_control": cli_task_run_context_status_dict(task_context)}


def _run_workspace_metadata(
    run_workspace: CliRunWorkspaceStateCandidate | None,
) -> dict[str, Any]:
    status = cli_run_workspace_status_dict(run_workspace)
    return {"run_workspace": status} if status is not None else {}


def _reference_context_metadata(
    reference_context: CliReferenceReviewContextCandidate,
) -> dict[str, Any]:
    return {
        "reference_context": {
            "status": reference_context.status,
            "requested_references": list(reference_context.requested_references),
            "consumed_reference_count": reference_context.consumed_reference_count,
            "evidence_refs": list(reference_context.evidence_refs),
            "blocking_reasons": list(reference_context.blocking_reasons),
            "warnings": list(reference_context.warnings),
            "reference_labels": list(
                reference_context.metadata.get("reference_labels", ())
            ),
        }
    }


def _reference_context_workspace_payload(
    reference_context: CliReferenceReviewContextCandidate,
) -> dict[str, Any]:
    return {
        "status": reference_context.status,
        "requested_references": list(reference_context.requested_references),
        "consumed_reference_count": reference_context.consumed_reference_count,
        "evidence_refs": list(reference_context.evidence_refs),
        "blocking_reasons": list(reference_context.blocking_reasons),
        "warnings": list(reference_context.warnings),
        "reference_labels": list(reference_context.metadata.get("reference_labels", ())),
        "tool_loading_gate": dict(
            reference_context.metadata.get("tool_loading_gate", {})
        ),
        "read_statuses": list(reference_context.metadata.get("read_statuses", ())),
    }


def _run_workspace_artifact_and_result_refs(
    run_workspace: CliRunWorkspaceStateCandidate | None,
) -> tuple[str, ...]:
    if run_workspace is None:
        return ()
    return (*run_workspace.artifact_refs, *run_workspace.result_refs)


def _preflight_blocked_terminal_display(
    task_context: CliTaskRunContextCandidate,
) -> str:
    reasons = ", ".join(task_context.preflight.blocking_reasons)
    return "\n".join(
        [
            "CLI reference review workflow 已被 preflight 阻止。",
            f"run_id: {task_context.run_id}",
            f"blocking_reasons: {reasons or 'unknown'}",
            "未读取资料，未调用模型。",
        ]
    )


def _workspace_blocked_terminal_display(
    task_context: CliTaskRunContextCandidate,
    run_workspace: CliRunWorkspaceStateCandidate,
) -> str:
    reasons = ", ".join(run_workspace.blocking_reasons)
    return "\n".join(
        [
            "CLI run workspace 已阻止本轮执行。",
            f"run_id: {task_context.run_id}",
            f"blocking_reasons: {reasons or 'unknown'}",
            "未读取资料，未调用模型。",
        ]
    )


def _reference_blocked_terminal_display(
    task_context: CliTaskRunContextCandidate,
    reference_context: CliReferenceReviewContextCandidate,
) -> str:
    reasons = ", ".join(reference_context.blocking_reasons)
    return "\n".join(
        [
            "CLI reference review workflow 的 reference reader 已阻止本轮执行。",
            f"run_id: {task_context.run_id}",
            f"blocking_reasons: {reasons or 'unknown'}",
            "未调用模型，未展示未脱敏资料全文。",
        ]
    )


def _failed_terminal_display(
    reference_context: CliReferenceReviewContextCandidate,
) -> str:
    evidence_refs = ", ".join(reference_context.evidence_refs) or "none"
    return "\n".join(
        [
            REFERENCE_REVIEW_FAIL_SAFE_MESSAGE,
            f"reference_context_status: {reference_context.status}",
            f"evidence_refs: {evidence_refs}",
        ]
    )


def _llm_display_text(result: LlmInvocationResult) -> str:
    display = result.metadata.get("sanitized_response_display")
    if isinstance(display, str) and display.strip():
        return display.strip()
    preview = result.sanitized_response_preview
    if preview and preview.strip():
        return preview.strip()
    return ""


def _evidence_lines(labels: Sequence[str], refs: Sequence[str]) -> list[str]:
    lines: list[str] = []
    for index, ref in enumerate(refs):
        label = labels[index] if index < len(labels) else f"reference-{index + 1}"
        lines.append(f"{label}：{ref}")
    return lines


def _reference_excerpt(*, reference_label: str, excerpt: str) -> str:
    return "\n".join(
        item
        for item in (
            f"reference: {reference_label}",
            excerpt.strip(),
        )
        if item
    )


def _bounded_reference_excerpts(excerpts: Sequence[str]) -> list[str]:
    remaining = REFERENCE_REVIEW_CONTEXT_TOTAL_CHAR_LIMIT
    bounded: list[str] = []
    for excerpt in excerpts:
        if remaining <= 0:
            break
        normalized = excerpt[:remaining]
        bounded.append(normalized)
        remaining -= len(normalized)
    return bounded


def _reference_label(resolved_path: str | None, requested_reference: str) -> str:
    path = Path(resolved_path) if resolved_path else Path(requested_reference)
    return path.name or requested_reference


def _join_or_default(values: Sequence[str], default: str) -> str:
    return "、".join(value for value in values if value) or default


def _preview_text(value: str, limit: int) -> str:
    normalized = _compact_text(value)
    return normalized[:limit]


def _compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
