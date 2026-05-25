"""task reference review workflow for governed document review tasks."""

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
from contract_core.external_readonly_evidence import (
    build_external_readonly_evidence_read_context,
    external_readonly_evidence_read_context_status_dict,
)
from cognition_operation_flows._workflows.plan import (
    DEFAULT_PLAN_MODEL_NAME,
    PLAN_DISPLAY_PREVIEW_LIMIT,
    detect_operation_flow_plan_request,
)
from cognition_operation_flows._tools.reference_reader import (
    REFERENCE_READER_TOOL_NAME,
    OperationFlowReferenceReadRequestCandidate,
    read_operation_flow_reference,
)
from cognition_operation_flows._core.run_workspace import (
    OperationFlowRunWorkspaceStateCandidate,
    build_operation_flow_run_workspace_policy,
    cleanup_operation_flow_run_workspace,
    operation_flow_run_workspace_status_dict,
    create_operation_flow_run_workspace,
    finalize_operation_flow_run_workspace,
    write_operation_flow_run_workspace_json,
    write_operation_flow_run_workspace_text,
)
from cognition_operation_flows._core.control import (
    OperationFlowRunContextCandidate,
    build_operation_flow_run_context,
    operation_flow_run_context_status_dict,
    finalize_operation_flow_run_context,
)
from cognition_operation_flows._tools.exposure_profile import (
    operation_flow_tool_exposure_profile_status_dict,
    resolve_operation_flow_tool_exposure_profile,
)
from cognition_operation_flows._tools.loading_validation import (
    operation_flow_tool_loading_gate_status_dict,
    validate_operation_flow_tool_loading_gate,
)
from cognition_operation_flows._llm.invocation import (
    OperationFlowLlmInvocationFacade,
    build_operation_flow_llm_invocation_request,
)
from cognition_operation_flows._skills.capability_projection import (
    build_default_operation_flow_skill_capability_projection_status_summary,
    operation_flow_skill_projection_status_summary_status_dict,
)
OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME = "operation_flow_reference_review_workflow"
OPERATION_FLOW_REFERENCE_REVIEW_TASK_KIND = "reference_review"
OPERATION_FLOW_REFERENCE_REVIEW_TEMPLATE_VERSION = "reference_review_template_v2"
REFERENCE_REVIEW_CONTEXT_TOTAL_CHAR_LIMIT = 1800
REFERENCE_REVIEW_PROMPT_PREVIEW_LIMIT = 80
REFERENCE_REVIEW_KEYWORDS = (
    "审查",
    "复核",
    "检查",
    "评审",
    "读取",
    "总结",
    "摘要",
    "整理",
    "梳理",
    "专有名词",
    "术语",
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
    "读取",
    "摘要",
    "整理",
    "梳理",
    "专有名词",
    "术语",
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
REFERENCE_REVIEW_LIVE_FALLBACK_NOTE = (
    "controlled-live 路径：真实模型调用失败，已基于受控资料 excerpt "
    "生成规则化摘要；未展示 raw provider response。"
)
REFERENCE_REVIEW_TEMPLATE_SECTIONS = (
    "主要结论",
    "判断依据",
    "发现的问题",
    "风险边界",
    "建议动作",
    "英文专有名词与中文语义注释",
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
REFERENCE_REVIEW_INTERNAL_STRUCTURE_BLOCKED_MESSAGE = (
    "模型输出包含内部结构或原始响应片段，已在显示层屏蔽；"
    "请按证据引用重新审查。"
)
REFERENCE_REVIEW_INTERNAL_STRUCTURE_MARKERS = (
    "system_context",
    "protocol_support",
    "response_strategy",
    "raw_provider_response",
    "raw_prompt",
    "system_prompt",
    "live_model_payload",
    "raw_response",
    "response_text",
    "messages",
)
REFERENCE_REVIEW_TERMINOLOGY_MARKERS = (
    "专有名词",
    "术语",
    "英文名词",
    "英文专有",
    "英文词",
    "中文语义注释",
    "语义注释",
)
REFERENCE_REVIEW_TERMINOLOGY_SECTION = "英文专有名词与中文语义注释"
REFERENCE_REVIEW_EXTERNAL_READONLY_EVIDENCE_SECTION = "外部只读证据摘要"
REFERENCE_REVIEW_SKILL_READONLY_HINT = (
    "Skills capability projection 仅作为 reference-review 的只读输出规程提示；"
    "不得加载 Skill 文件、不得读取 resources、不得执行 scripts、不得暴露工具、"
    "不得注入 prompt_context。"
)
REFERENCE_REVIEW_TERMINOLOGY_TERM_LIMIT = 24


@dataclass(frozen=True)
class OperationFlowReferenceReviewWorkflowRequestCandidate:
    """Request entering the governed task reference review workflow."""

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
    reference_entrypoint_explicit_args: Mapping[str, Any] = field(default_factory=dict)
    external_readonly_evidence_paths: tuple[str, ...] = ()
    external_readonly_evidence_repo_root: str | None = None
    run_workspace_root: str | None = None
    run_workspace_enabled: bool = False
    run_workspace_retention_policy: str = "keep"
    run_workspace_cleanup_policy: str = "manual"
    run_workspace_max_write_bytes: int = 65536
    model_name: str = DEFAULT_PLAN_MODEL_NAME
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationFlowReferenceReviewFactsCandidate:
    """Minimal facts extracted from a reference review request."""

    original_text: str
    task_kind: str
    review_intents: tuple[str, ...] = ()
    topic_hints: tuple[str, ...] = ()
    requested_outputs: tuple[str, ...] = ()
    terminology_output_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationFlowReferenceReviewContextCandidate:
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
class OperationFlowReferenceReviewDraftCandidate:
    """Review draft before final terminal formatting."""

    draft_text: str
    prompt_preview_sanitized: str | None
    model_call_count: int = 0
    source: str = "local_reference_rules"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationFlowReferenceReviewWorkflowResultCandidate:
    """Final result returned to the product channel entrypoint."""

    triggered: bool
    terminal_display_text: str
    request: OperationFlowReferenceReviewWorkflowRequestCandidate
    facts: OperationFlowReferenceReviewFactsCandidate
    reference_context: OperationFlowReferenceReviewContextCandidate
    draft: OperationFlowReferenceReviewDraftCandidate | None
    model_call_count: int = 0
    no_live: bool = False
    fail_safe: bool = False
    task_run_context: OperationFlowRunContextCandidate | None = None
    run_workspace: OperationFlowRunWorkspaceStateCandidate | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def detect_operation_flow_reference_review_request(
    user_text: str,
    *,
    reference_paths: Sequence[str] = (),
    external_readonly_evidence_paths: Sequence[str] = (),
) -> bool:
    """Return whether a turn should route to reference review."""

    normalized = _compact_text(user_text)
    has_reference_material = bool(
        tuple(path for path in reference_paths if path.strip())
        or tuple(path for path in external_readonly_evidence_paths if path.strip())
    )
    if not normalized or not has_reference_material:
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
    if detect_operation_flow_plan_request(user_text) and not has_strong_review_intent:
        return False
    return True


def extract_operation_flow_reference_review_facts(
    request: OperationFlowReferenceReviewWorkflowRequestCandidate,
) -> OperationFlowReferenceReviewFactsCandidate:
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
    terminology_output_requested = _reference_review_requests_terminology(normalized)
    requested_outputs = (
        ("terminology_glossary",) if terminology_output_requested else ()
    )
    return OperationFlowReferenceReviewFactsCandidate(
        original_text=request.user_text,
        task_kind=OPERATION_FLOW_REFERENCE_REVIEW_TASK_KIND,
        review_intents=review_intents,
        topic_hints=topic_hints,
        requested_outputs=requested_outputs,
        terminology_output_requested=terminology_output_requested,
        metadata={
            "workflow_stage": "intent_extraction",
            "reference_path_count": len(request.reference_paths),
            "external_readonly_evidence_path_count": len(
                request.external_readonly_evidence_paths
            ),
            "terminology_output_requested": terminology_output_requested,
            "requested_outputs": list(requested_outputs),
        },
    )


def run_operation_flow_reference_review_workflow(
    request: OperationFlowReferenceReviewWorkflowRequestCandidate,
) -> OperationFlowReferenceReviewWorkflowResultCandidate:
    """Run the governed task reference review workflow."""

    facts = extract_operation_flow_reference_review_facts(request)
    task_context = _build_reference_review_task_context(request, facts)
    if not task_context.preflight.allowed:
        task_context = finalize_operation_flow_run_context(
            task_context,
            status="blocked",
            metadata={"blocked_before_reference_read": True},
        )
        reference_context = OperationFlowReferenceReviewContextCandidate(status="not_started")
        return OperationFlowReferenceReviewWorkflowResultCandidate(
            triggered=True,
            terminal_display_text=_preflight_blocked_terminal_display(task_context),
            request=request,
            facts=facts,
            reference_context=reference_context,
            draft=None,
            fail_safe=True,
            task_run_context=task_context,
            metadata={
                "workflow": OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
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
        reference_context = OperationFlowReferenceReviewContextCandidate(status="not_started")
        return OperationFlowReferenceReviewWorkflowResultCandidate(
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
                "workflow": OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
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
        task_context = finalize_operation_flow_run_context(
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
            workspace_metadata=operation_flow_run_workspace_status_dict(run_workspace),
            metadata={
                "blocked_before_model_call": True,
                "failure_stage": "reference_context",
            },
        )
        return OperationFlowReferenceReviewWorkflowResultCandidate(
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
                "workflow": OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
                **_task_context_metadata(task_context),
                **_reference_context_metadata(reference_context),
                **_run_workspace_metadata(run_workspace),
            },
        )

    draft = build_operation_flow_reference_review_draft(request, facts, reference_context)
    status = "succeeded"
    fail_safe = False
    if draft.source == "controlled_live_failed":
        status = "failed"
        fail_safe = True
        display = _failed_terminal_display(reference_context)
    else:
        display = format_operation_flow_reference_review_for_terminal(
            draft,
            facts,
            reference_context,
            no_live=not request.live_model_allowed,
            fallback_note=_controlled_live_fallback_note(draft),
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
    task_context = finalize_operation_flow_run_context(
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
        workspace_metadata=operation_flow_run_workspace_status_dict(run_workspace),
        metadata={"failure_stage": "review_generation"} if fail_safe else {},
    )
    return OperationFlowReferenceReviewWorkflowResultCandidate(
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
            "workflow": OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
            **_task_context_metadata(task_context),
            **_reference_context_metadata(reference_context),
            **_run_workspace_metadata(run_workspace),
        },
    )


def build_operation_flow_reference_review_draft(
    request: OperationFlowReferenceReviewWorkflowRequestCandidate,
    facts: OperationFlowReferenceReviewFactsCandidate,
    reference_context: OperationFlowReferenceReviewContextCandidate,
) -> OperationFlowReferenceReviewDraftCandidate:
    """Build a local or controlled-live reference review draft."""

    prompt_preview = build_operation_flow_reference_review_prompt_preview(
        facts,
        reference_context,
    )
    terminology_items = (
        _reference_terminology_items(reference_context.reference_excerpts)
        if facts.terminology_output_requested
        else ()
    )
    skill_readonly_hint = _reference_review_skill_readonly_hint_status()
    if not request.live_model_allowed:
        return OperationFlowReferenceReviewDraftCandidate(
            draft_text=_local_reference_review_draft(
                facts,
                reference_context,
                terminology_items=terminology_items,
                skill_readonly_hint=skill_readonly_hint,
            ),
            prompt_preview_sanitized=prompt_preview,
            model_call_count=0,
            source="local_reference_rules",
            metadata={
                "no_live": True,
                "review_template_version": OPERATION_FLOW_REFERENCE_REVIEW_TEMPLATE_VERSION,
                "terminology_output_requested": facts.terminology_output_requested,
                "terminology_items": list(terminology_items),
                "skills_readonly_hint": skill_readonly_hint,
            },
        )
    llm_result = _invoke_reference_review_llm(
        request,
        facts=facts,
        prompt_preview=prompt_preview,
        reference_context=reference_context,
        terminology_items=terminology_items,
        skill_readonly_hint=skill_readonly_hint,
    )
    if not llm_result.success or not llm_result.response_non_empty:
        return OperationFlowReferenceReviewDraftCandidate(
            draft_text=_local_reference_review_draft(
                facts,
                reference_context,
                terminology_items=terminology_items,
                skill_readonly_hint=skill_readonly_hint,
            ),
            prompt_preview_sanitized=prompt_preview,
            model_call_count=1,
            source="controlled_live_failed_local_fallback",
            metadata={
                "failure_type": llm_result.failure_type,
                "error_message_sanitized": llm_result.error_message_sanitized,
                "fallback_source": "local_reference_rules",
                "raw_provider_response_displayed": False,
                "terminology_output_requested": facts.terminology_output_requested,
                "terminology_items": list(terminology_items),
                "skills_readonly_hint": skill_readonly_hint,
            },
        )
    return OperationFlowReferenceReviewDraftCandidate(
        draft_text=_llm_display_text(llm_result),
        prompt_preview_sanitized=prompt_preview,
        model_call_count=1,
        source="controlled_live",
        metadata={
            "llm_invocation_result_ref": llm_result.request_id,
            "sanitized_response_length": llm_result.sanitized_response_length,
            "review_template_version": OPERATION_FLOW_REFERENCE_REVIEW_TEMPLATE_VERSION,
            "terminology_output_requested": facts.terminology_output_requested,
            "terminology_items": list(terminology_items),
            "skills_readonly_hint": skill_readonly_hint,
        },
    )


def build_operation_flow_reference_review_prompt_preview(
    facts: OperationFlowReferenceReviewFactsCandidate,
    reference_context: OperationFlowReferenceReviewContextCandidate,
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
    if facts.terminology_output_requested:
        parts.append("输出英文术语分类和中文语义注释")
        parts.append("Skills只读规程提示")
    return _preview_text("，".join(parts), REFERENCE_REVIEW_PROMPT_PREVIEW_LIMIT)


def format_operation_flow_reference_review_for_terminal(
    draft: OperationFlowReferenceReviewDraftCandidate,
    facts: OperationFlowReferenceReviewFactsCandidate,
    reference_context: OperationFlowReferenceReviewContextCandidate,
    *,
    no_live: bool,
    fallback_note: str | None = None,
) -> str:
    """Build final terminal display text for the review workflow."""

    labels = tuple(reference_context.metadata.get("reference_labels", ()))
    evidence_lines = _evidence_lines(labels, reference_context.evidence_refs)
    external_evidence_lines = _external_readonly_evidence_ref_lines(reference_context)
    evidence_reference_lines = [
        *(f"- {line}" for line in evidence_lines),
        *(f"- {line}" for line in external_evidence_lines),
    ] or ["- 未生成证据引用"]
    scope_lines = [f"- {line}" for line in evidence_lines] or ["- 未生成本地资料证据引用"]
    external_summary_lines = _external_readonly_evidence_summary_lines(
        reference_context
    )
    draft_text = draft.draft_text.strip()
    result_lines = _review_display_lines(draft_text)
    if facts.terminology_output_requested and REFERENCE_REVIEW_TERMINOLOGY_SECTION not in (
        "\n".join(result_lines)
    ):
        terminology_items = draft.metadata.get("terminology_items")
        if isinstance(terminology_items, list | tuple):
            glossary_lines = _terminology_display_lines(terminology_items)
        else:
            glossary_lines = ()
        _append_review_section(
            result_lines,
            REFERENCE_REVIEW_TERMINOLOGY_SECTION,
            glossary_lines
            or ("未在受控 excerpt 中识别到稳定英文专有名词，建议人工复核原文。",),
        )
    lines = [
        "资料审查结果",
        "",
        "审查范围",
        *scope_lines,
    ]
    if external_summary_lines:
        lines.extend(
            (
                "",
                REFERENCE_REVIEW_EXTERNAL_READONLY_EVIDENCE_SECTION,
                *external_summary_lines,
            )
        )
    lines.extend(
        (
            "",
            "审查输出",
            *result_lines,
            "",
            "证据引用",
            *evidence_reference_lines,
        )
    )
    if no_live:
        lines.extend(("", "执行说明", f"- {REFERENCE_REVIEW_NO_LIVE_NOTE}"))
    elif fallback_note:
        lines.extend(("", "执行说明", f"- {fallback_note}"))
    if facts.review_intents:
        lines.extend(("", "识别意图", "- " + "、".join(facts.review_intents)))
    return "\n".join(lines)


def _controlled_live_fallback_note(
    draft: OperationFlowReferenceReviewDraftCandidate,
) -> str | None:
    if draft.source != "controlled_live_failed_local_fallback":
        return None
    failure_type = draft.metadata.get("failure_type")
    error_message = draft.metadata.get("error_message_sanitized")
    details = []
    if failure_type:
        details.append(f"failure_type={_metadata_text(failure_type)}")
    if error_message:
        details.append(f"error_message_sanitized={_metadata_text(error_message)}")
    if details:
        return REFERENCE_REVIEW_LIVE_FALLBACK_NOTE + " " + "；".join(details)
    return REFERENCE_REVIEW_LIVE_FALLBACK_NOTE


def _metadata_text(value: Any) -> str:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)


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
    terminology_items = _decoded_terminology_items(
        decoded,
        (
            "terminology_items",
            "english_terms",
            "glossary",
            "terms",
            "英文专有名词",
            "术语注释",
            REFERENCE_REVIEW_TERMINOLOGY_SECTION,
        ),
    )
    review_context_text = "\n".join(
        item
        for item in (
            conclusion,
            *evidence_basis,
            *issues,
            *risk_boundaries,
            *suggestions,
            *terminology_items,
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
    if terminology_items:
        _append_review_section(
            lines,
            REFERENCE_REVIEW_TERMINOLOGY_SECTION,
            terminology_items,
        )
    return lines


def _plain_review_lines(draft_text: str) -> list[str]:
    lines = [line for line in draft_text.splitlines() if line.strip()]
    if _has_review_template_sections(lines):
        return _sanitize_review_template_lines(lines, context_text=draft_text)
    return _fallback_review_template_lines(draft_text)


def _fallback_review_template_lines(main_text: str) -> list[str]:
    lines: list[str] = []
    _append_review_section(
        lines,
        "主要结论",
        (_safe_review_main_text(main_text),),
        bullet="-",
    )
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
            return _safe_review_fragment(value)
    return ""


def _decoded_items(decoded: Mapping[str, Any], keys: Sequence[str]) -> tuple[str, ...]:
    for key in keys:
        value = decoded.get(key)
        if isinstance(value, str) and value.strip():
            return (_safe_review_fragment(value),)
        if isinstance(value, list | tuple):
            items = tuple(
                _safe_review_fragment(str(item))
                for item in value
                if str(item).strip()
            )
            if items:
                return items
    return ()


def _decoded_terminology_items(
    decoded: Mapping[str, Any],
    keys: Sequence[str],
) -> tuple[str, ...]:
    for key in keys:
        value = decoded.get(key)
        if isinstance(value, str) and value.strip():
            return (_safe_review_fragment(value),)
        if isinstance(value, list | tuple):
            items: list[str] = []
            for item in value:
                if isinstance(item, Mapping):
                    display = _terminology_display_line_from_mapping(item)
                    if display:
                        items.append(display)
                    continue
                item_text = _safe_review_fragment(str(item))
                if item_text:
                    items.append(item_text)
            if items:
                return tuple(items)
    return ()


def _terminology_display_line_from_mapping(item: Mapping[str, Any]) -> str:
    term = _compact_text(
        str(
            item.get("term")
            or item.get("name")
            or item.get("english")
            or item.get("英文")
            or ""
        )
    )
    readable = _compact_text(
        str(
            item.get("readable")
            or item.get("spaced_term")
            or item.get("display")
            or ""
        )
    )
    note = _compact_text(
        str(
            item.get("note")
            or item.get("meaning")
            or item.get("中文语义注释")
            or item.get("translation")
            or ""
        )
    )
    category = _compact_text(str(item.get("category") or item.get("分类") or ""))
    if not term and not readable and not note:
        return ""
    display_term = readable or _readable_english_term(term)
    original = f"（{term}）" if term and term != display_term else ""
    category_prefix = f"{category}：" if category else ""
    note_text = note or _terminology_note(term or display_term)
    return _safe_review_fragment(
        f"{category_prefix}{display_term}{original}：{note_text}"
    )


def _safe_review_main_text(value: str) -> str:
    if _contains_internal_structure_marker(value):
        return REFERENCE_REVIEW_INTERNAL_STRUCTURE_BLOCKED_MESSAGE
    return _compact_text(value)


def _safe_review_fragment(value: str) -> str:
    if _contains_internal_structure_marker(value):
        return REFERENCE_REVIEW_INTERNAL_STRUCTURE_BLOCKED_MESSAGE
    return _compact_text(value)


def _contains_internal_structure_marker(value: str) -> bool:
    normalized = value.lower()
    return any(
        marker in normalized
        for marker in REFERENCE_REVIEW_INTERNAL_STRUCTURE_MARKERS
    )


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
                _safe_review_template_line(
                    _sanitize_review_suggestion_line(line, context_text=context_text)
                )
            )
            continue
        sanitized.append(_safe_review_template_line(line))
    return sanitized


def _safe_review_template_line(line: str) -> str:
    if not _contains_internal_structure_marker(line):
        return line
    prefix_match = re.match(r"^(\s*(?:[-*]|\d+[.．、])\s*)(.*)$", line)
    if prefix_match is None:
        return REFERENCE_REVIEW_INTERNAL_STRUCTURE_BLOCKED_MESSAGE
    prefix, _body = prefix_match.groups()
    return prefix + REFERENCE_REVIEW_INTERNAL_STRUCTURE_BLOCKED_MESSAGE


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
    request: OperationFlowReferenceReviewWorkflowRequestCandidate,
    facts: OperationFlowReferenceReviewFactsCandidate,
) -> OperationFlowRunContextCandidate:
    return build_operation_flow_run_context(
        workflow_name=OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
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
            "source": "cognition_operation_flows._workflows.reference_review",
            "review_intents": list(facts.review_intents),
            "topic_hints": list(facts.topic_hints),
        },
    )


def _build_reference_review_context(
    request: OperationFlowReferenceReviewWorkflowRequestCandidate,
    task_context: OperationFlowRunContextCandidate,
) -> OperationFlowReferenceReviewContextCandidate:
    requested_references = tuple(_ordered_unique(request.reference_paths))
    requested_external_evidence = tuple(
        _ordered_unique(
            [
                path.strip()
                for path in request.external_readonly_evidence_paths
                if path.strip()
            ]
        )
    )
    if not requested_references and not requested_external_evidence:
        return OperationFlowReferenceReviewContextCandidate(
            status="blocked",
            blocking_reasons=("reference_material_required",),
            metadata={"workflow_stage": "reference_context"},
        )

    repo_root = Path(request.reference_repo_root or Path.cwd()).expanduser().resolve()
    exposure_status: dict[str, Any] | None = None
    loading_gate_status: dict[str, Any] | None = None
    reference_reader_policy = None
    blocking: list[str] = []
    warnings: list[str] = []
    if requested_references:
        exposure = resolve_operation_flow_tool_exposure_profile(
            profile_name=request.reference_profile_name,
            profile_config=request.reference_profile_config,
            repo_root=repo_root,
            session_args=request.reference_session_args,
            entrypoint_explicit_args=request.reference_entrypoint_explicit_args,
        )
        exposure_status = operation_flow_tool_exposure_profile_status_dict(exposure)
        loading_gate = validate_operation_flow_tool_loading_gate(
            exposure,
            operator_approved=bool(request.approval_ref),
            approval_ref=request.approval_ref,
        )
        loading_gate_status = operation_flow_tool_loading_gate_status_dict(loading_gate)
        reference_reader_policy = exposure.reference_reader_policy
        blocking.extend(exposure.blocking_reasons)
        warnings.extend(exposure.warnings)
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
        if reference_reader_policy is None:
            blocking.append("reference_reader_policy_missing")

    read_results = []
    reference_excerpts: list[str] = []
    evidence_refs: list[str] = []
    reference_labels: list[str] = []
    external_evidence_status: dict[str, Any] | None = None
    if not blocking and reference_reader_policy is not None:
        for reference in requested_references:
            read_result = read_operation_flow_reference(
                OperationFlowReferenceReadRequestCandidate(
                    reference=reference,
                    policy=reference_reader_policy,
                    purpose="operation_flow_reference_review",
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
    if requested_external_evidence:
        external_evidence_root = Path(
            request.external_readonly_evidence_repo_root
            or request.reference_repo_root
            or Path.cwd()
        ).expanduser().resolve()
        external_evidence_context = build_external_readonly_evidence_read_context(
            requested_external_evidence,
            repo_root=external_evidence_root,
        )
        external_evidence_status = (
            external_readonly_evidence_read_context_status_dict(
                external_evidence_context
            )
        )
        warnings.extend(
            f"external_readonly_evidence:{reason}"
            for reason in external_evidence_context.warnings
        )
        if external_evidence_context.status == "blocked":
            blocking.extend(
                f"external_readonly_evidence_blocked:{reason}"
                for reason in external_evidence_context.blocking_reasons
            )

    bounded_excerpts = tuple(_bounded_reference_excerpts(reference_excerpts))
    status = "blocked" if blocking else "succeeded"
    return OperationFlowReferenceReviewContextCandidate(
        status=status,
        requested_references=requested_references,
        consumed_reference_count=0 if blocking else len(bounded_excerpts),
        reference_excerpts=() if blocking else bounded_excerpts,
        evidence_refs=tuple(_ordered_unique(evidence_refs)),
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "workflow_stage": "reference_context",
            "reference_reader_requested": bool(requested_references),
            "tool_exposure_profile": exposure_status,
            "tool_loading_gate": loading_gate_status,
            "reference_labels": tuple(reference_labels),
            "external_readonly_evidence_requested": bool(
                requested_external_evidence
            ),
            "external_readonly_evidence_paths": requested_external_evidence,
            "external_readonly_evidence_context": external_evidence_status,
            "external_readonly_evidence_integration_mode": "prepared_only",
            "external_readonly_evidence_prompt_injection_enabled": False,
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
    facts: OperationFlowReferenceReviewFactsCandidate,
    reference_context: OperationFlowReferenceReviewContextCandidate,
    *,
    terminology_items: Sequence[Mapping[str, Any]] = (),
    skill_readonly_hint: Mapping[str, Any] | None = None,
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
    risk_index = 2
    if "Agent runtime" in findings["keyword_hits"]:
        lines.append(f"{risk_index}. Agent runtime 相关内容只能作为观察或关闭边界，不得自动打开。")
        risk_index += 1
    if "Skills runtime" in findings["keyword_hits"]:
        lines.append(f"{risk_index}. Skills runtime 相关内容只能作为观察或关闭边界，不得自动打开。")
        risk_index += 1
    if facts.terminology_output_requested:
        lines.append(f"{risk_index}. {REFERENCE_REVIEW_SKILL_READONLY_HINT}")
    lines.extend(["", "建议动作"])
    lines.append("1. 下一任务只承接资料中明确允许的主线，不反推 Agent / Skills runtime。")
    lines.append("2. 保留 reference-reader、Tools gate 与 run workspace 证据链。")
    if findings["next_step_terms"]:
        lines.append("3. 将下一步信号转化为任务包中的明确验收标准。")
    else:
        lines.append("3. 先补足下一步动作，再决定是否进入实施任务。")
    if facts.terminology_output_requested:
        lines.extend(["", REFERENCE_REVIEW_TERMINOLOGY_SECTION])
        glossary_lines = _terminology_display_lines(terminology_items)
        if glossary_lines:
            lines.extend(
                f"{index}. {line}"
                for index, line in enumerate(glossary_lines, start=1)
            )
            next_index = len(glossary_lines) + 1
        else:
            lines.append("1. 未在受控 excerpt 中识别到稳定英文专有名词，建议人工复核原文。")
            next_index = 2
        if skill_readonly_hint:
            lines.append(
                f"{next_index}. Skills readonly hint："
                "本节采用 Skills 只读能力提示的输出规程，不加载 Skill runtime。"
            )
    return "\n".join(lines)


def _reference_findings(excerpts_text: str) -> dict[str, list[str]]:
    next_step_markers = ("下一步", "建议", "进入", "实施", "真实", "验收")
    keyword_markers = (
        "operation flow",
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


def _reference_review_requests_terminology(normalized_text: str) -> bool:
    return any(
        marker.lower() in normalized_text.lower()
        for marker in REFERENCE_REVIEW_TERMINOLOGY_MARKERS
    )


def _reference_review_skill_readonly_hint_status() -> dict[str, Any]:
    summary = build_default_operation_flow_skill_capability_projection_status_summary()
    status = operation_flow_skill_projection_status_summary_status_dict(summary)
    return {
        "status": status.get("status"),
        "source": status.get("source"),
        "workflow_name": OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
        "allowed_use": status.get("allowed_use_summary", {}).get(
            OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
            [],
        ),
        "skill_ids": [
            skill_id
            for skill_id in status.get("skill_ids", [])
            if skill_id == "skill.reference.review"
        ],
        "capability_ids": [
            capability_id
            for capability_id in status.get("capability_ids", [])
            if capability_id == "capability.reference.review"
        ],
        "evidence_refs": [
            evidence_ref
            for evidence_ref in status.get("evidence_refs", [])
            if "reference-review" in evidence_ref
        ],
        "runtime_enabled": False,
        "skill_file_loading_enabled": False,
        "resources_loading_enabled": False,
        "scripts_execution_enabled": False,
        "tool_exposure_enabled": False,
        "agent_runtime_enabled": False,
        "prompt_context_enabled": False,
        "public_schema_enabled": False,
        "hint": REFERENCE_REVIEW_SKILL_READONLY_HINT,
    }


def _reference_terminology_items(
    reference_excerpts: Sequence[str],
) -> tuple[dict[str, str], ...]:
    text = "\n".join(reference_excerpts)
    if not text.strip():
        return ()
    ordered_terms: list[str] = []

    known_phrases = (
        "route projection summary",
        "product response refs/status",
        "workflow read context",
        "evidence summary",
        "runtime facade sanitized summary",
        "reference path",
        "reference reader",
        "local reference reader",
        "reference review",
        "operation flow",
        "run workspace",
        "Agent runtime",
        "Skills runtime",
        "Skill runtime",
        "ADK SkillRegistry",
        "SkillToolset",
        "MCPToolset",
        "Google Search",
        "URL context",
        "Code Execution",
        "LiteLLM",
        "Ollama",
        "PyPI",
        "RAG",
        "CLI",
        "ADK",
        "MCP",
    )
    lower_text = text.lower()
    for phrase in known_phrases:
        if phrase.lower() in lower_text:
            ordered_terms.append(phrase)

    patterns = (
        r"\b[A-Z][A-Za-z0-9]*(?:[A-Z][a-z0-9]+){1,}\b",
        r"\b[a-z][a-z0-9]*(?:[_-][a-z0-9]+)+\b",
        r"\b[a-z][a-z0-9]*(?:/[a-z][a-z0-9]*)+\b",
    )
    for pattern in patterns:
        ordered_terms.extend(re.findall(pattern, text))

    items: list[dict[str, str]] = []
    for term in _ordered_unique(ordered_terms):
        if len(items) >= REFERENCE_REVIEW_TERMINOLOGY_TERM_LIMIT:
            break
        if not _looks_like_reference_term(term):
            continue
        readable = _readable_english_term(term)
        items.append(
            {
                "term": term,
                "readable": readable,
                "category": _terminology_category(term),
                "note": _terminology_note(term),
            }
        )
    return tuple(items)


def _looks_like_reference_term(term: str) -> bool:
    compact = term.strip()
    if len(compact) < 2:
        return False
    lower = compact.lower()
    if lower in {"http", "https", "utf", "true", "false", "none"}:
        return False
    return any(
        marker in lower
        for marker in (
            "adk",
            "agent",
            "capability",
            "cli",
            "context",
            "evidence",
            "gateway",
            "litellm",
            "memory",
            "mcp",
            "model",
            "ollama",
            "product",
            "profile",
            "projection",
            "pypi",
            "reader",
            "reference",
            "runtime",
            "skill",
            "summary",
            "tool",
            "operation_flow",
            "url",
            "workflow",
            "_",
            "-",
            "/",
        )
    )


def _readable_english_term(term: str) -> str:
    compact = term.strip()
    if not compact:
        return ""
    if "_" in compact or "-" in compact:
        return re.sub(r"[_-]+", " ", compact)
    if "/" in compact and compact.lower() == compact:
        return compact.replace("/", " / ")
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", compact)
    spaced = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", spaced)
    parts = spaced.split()
    if not parts:
        return compact
    normalized_parts = [
        part if part.isupper() else (part if index == 0 else part.lower())
        for index, part in enumerate(parts)
    ]
    return " ".join(normalized_parts)


def _terminology_category(term: str) -> str:
    lower = term.lower()
    if any(marker in lower for marker in ("skill", "adk", "mcp")):
        return "Skills / ADK 能力边界"
    if "memory" in lower:
        return "Memory 治理"
    if any(
        marker in lower
        for marker in ("reference", "reader", "evidence", "url", "search", "rag")
    ):
        return "资料读取与证据"
    if any(marker in lower for marker in ("workflow", "operation_flow", "task")):
        return "workflow 与操作控制"
    if any(marker in lower for marker in ("runtime", "litellm", "ollama", "model")):
        return "运行时与模型调用"
    if any(marker in lower for marker in ("gateway", "product")):
        return "产品入口与契约"
    return "模块、对象与配置"


def _terminology_note(term: str) -> str:
    lower = term.lower().replace("_", " ").replace("-", " ")
    known_notes = {
        "adk": "Google Agent Development Kit，智能体开发工具包。",
        "mcp": "Model Context Protocol，模型上下文协议；当前只做只读工具方向评估。",
        "agent runtime": "Agent 运行时；当前作为关闭边界，不自动打开。",
        "skills runtime": "Skills 运行时；当前保持关闭，只允许只读投影提示。",
        "skill runtime": "Skill 运行时；当前保持关闭，只允许只读投影提示。",
        "adk skillregistry": "ADK 的 Skill 注册表能力；当前不调用。",
        "skillregistry": "Skill 注册表对象；当前不调用 ADK SkillRegistry。",
        "skill registry": "Skill 注册表对象；当前不调用 ADK SkillRegistry。",
        "skilltoolset": "ADK Skills 工具集能力；当前仅观察和设计，不运行。",
        "mcptoolset": "MCP 工具集能力；当前仅观察和设计，不运行。",
        "google search": "Google 搜索资料工具候选，属于外部只读资料工具方向。",
        "url context": "URL 上下文资料工具候选，属于外部只读资料工具方向。",
        "code execution": "代码执行工具；当前暂缓，不进入只读资料主链。",
        "rag": "检索增强生成能力；当前暂缓。",
        "litellm": "多模型调用适配库，用于模型路由和 provider 适配。",
        "ollama": "本地模型服务，用于 local-live 路线。",
        "pypi": "Python 包发布平台。",
        "cli": "命令行入口或命令行通道。",
        "candidate only": "候选态边界，表示尚未进入 runtime 或公共契约。",
        "reference only": "只读引用边界，表示只能读取受控摘要或投影。",
        "no live": "不调用真实模型的本地规则路径。",
        "controlled live": "受治理审批后的真实模型调用路径。",
        "allowed files": "明确允许读取的单文件白名单。",
        "evidence ref": "证据引用，用于追踪资料读取或结果来源。",
        "reference path": "受控资料路径。",
        "reference reader": "本地只读资料读取器。",
        "local reference reader": "本地只读资料读取器。",
        "reference review": "资料审查 workflow。",
        "operation flow": "任务型 workflow，承接特定操作控制结构。",
        "cognition operation flows": "认知系统任务 workflow 包，承接通道无关任务能力。",
        "operation_flow reference review workflow": "OperationFlow 资料审查 workflow 的内部标识。",
        "terminology items": "术语条目列表，用于稳定展示英文名词与中文语义注释。",
        "run workspace": "单次任务运行工作区，用于保存证据、摘要和结果。",
        "route projection summary": "路由投影摘要，用于展示任务路由判断。",
        "product response refs/status": "产品响应引用和状态，用于产品入口输出契约。",
        "workflow read context": "workflow 读取上下文，用于传递只读资料摘要。",
        "evidence summary": "证据摘要，用于展示证据引用和完整性。",
        "runtime facade sanitized summary": "运行时门面脱敏摘要，用于跨模块安全展示运行结果。",
    }
    if lower in known_notes:
        return known_notes[lower]
    if "memory" in lower and "candidate" in lower:
        return "Memory 治理候选对象，尚未进入公共 schema 或 runtime。"
    if "projection" in lower:
        return "受控投影对象或摘要，只暴露审查后的可见信息。"
    if "candidate" in lower:
        return "候选对象或候选契约，表示尚未公共化或运行时化。"
    if "context" in lower:
        return "上下文对象，用于在受控边界内传递信息。"
    if "summary" in lower:
        return "摘要对象，用于稳定展示关键信息。"
    if "runtime" in lower:
        return "运行时能力或运行时边界，需要受治理控制。"
    if "workflow" in lower:
        return "任务 workflow 相关对象或能力。"
    if "gateway" in lower:
        return "产品网关相关对象，用于产品入口收口。"
    if "reader" in lower or "reference" in lower:
        return "资料读取或资料引用相关对象。"
    return "项目中的英文专有名词，需结合上下文按模块名或对象名理解。"


def _terminology_display_lines(
    terminology_items: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    lines: list[str] = []
    for item in terminology_items:
        if not isinstance(item, Mapping):
            continue
        display = _terminology_display_line_from_mapping(item)
        if display:
            lines.append(display)
    return tuple(lines)


def _invoke_reference_review_llm(
    request: OperationFlowReferenceReviewWorkflowRequestCandidate,
    *,
    facts: OperationFlowReferenceReviewFactsCandidate,
    prompt_preview: str,
    reference_context: OperationFlowReferenceReviewContextCandidate,
    terminology_items: Sequence[Mapping[str, Any]],
    skill_readonly_hint: Mapping[str, Any],
) -> LlmInvocationResult:
    service = request.llm_invocation_service
    if service is None:
        raise ValueError(
            "llm_invocation_service is required for controlled-live reference review"
        )
    facade = OperationFlowLlmInvocationFacade(
        service=service,
        metadata={
            "source": "cognition_operation_flows._workflows.reference_review",
            "workflow": OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
            "purpose": "reference_review",
        },
    )
    invocation_request = build_operation_flow_llm_invocation_request(
        request_id=(
            "operation_flow-reference-review-"
            f"{request.chat_session_id or 'session'}-{request.turn_index or 0}"
        ),
        route_facts=ModelRouteFacts(
            model_name=request.model_name,
            provider="litellm",
            source="cognition_operation_flows._workflows.reference_review",
            metadata={
                "backend_provider": "ollama",
                "route_target": request.model_name,
                "route_kind": "adk_litellm",
                "does_not_call_model": True,
            },
        ),
        governance_precondition=LlmGovernancePrecondition(
            allowed=True,
            reason="operation_flow_reference_review_controlled_live_allowed",
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
            "operation_flow-reference-review-input://"
            f"{request.chat_session_id or 'session'}/{request.turn_index or 0}"
        ),
        prompt_preview_sanitized=prompt_preview,
        metadata={
            "source": "cognition_operation_flows._workflows.reference_review",
            "interaction_mode": OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
            "workflow_stage": "reference_review",
            "controlled_live": True,
            "live_llm_allowed": True,
            "ollama_allowed": True,
            "risk_level": request.risk_level,
            "output_budget": request.output_budget,
            "requested_outputs": list(facts.requested_outputs),
            "terminology_output_requested": facts.terminology_output_requested,
            "reference_context_status": reference_context.status,
            "reference_context_evidence_ref_count": len(reference_context.evidence_refs),
            "review_template_version": OPERATION_FLOW_REFERENCE_REVIEW_TEMPLATE_VERSION,
            "skills_readonly_hint": dict(skill_readonly_hint),
            "terminology_items": [dict(item) for item in terminology_items],
            "external_readonly_evidence_prepared": bool(
                reference_context.metadata.get("external_readonly_evidence_context")
            ),
            "external_readonly_evidence_prompt_injection_enabled": False,
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
    request: OperationFlowReferenceReviewWorkflowRequestCandidate,
    task_context: OperationFlowRunContextCandidate,
) -> OperationFlowRunWorkspaceStateCandidate | None:
    if not request.run_workspace_enabled and not request.run_workspace_root:
        return None
    workspace_root = request.run_workspace_root or ".cognition-runs"
    policy = build_operation_flow_run_workspace_policy(
        workspace_root=workspace_root,
        retention_policy=request.run_workspace_retention_policy,
        cleanup_policy=request.run_workspace_cleanup_policy,
        max_write_bytes=request.run_workspace_max_write_bytes,
    )
    return create_operation_flow_run_workspace(
        policy=policy,
        workflow_name=task_context.workflow_name,
        run_id=task_context.run_id,
    )


def _finalize_reference_review_run_workspace(
    run_workspace: OperationFlowRunWorkspaceStateCandidate | None,
    *,
    status: str,
    terminal_display_text: str,
    facts: OperationFlowReferenceReviewFactsCandidate,
    reference_context: OperationFlowReferenceReviewContextCandidate,
    model_call_count: int,
    fail_safe: bool,
) -> OperationFlowRunWorkspaceStateCandidate | None:
    if run_workspace is None or not run_workspace.workspace_created:
        return run_workspace
    max_write_bytes = int(run_workspace.metadata.get("max_write_bytes") or 65536)
    if reference_context.status != "not_started":
        run_workspace, _ = write_operation_flow_run_workspace_json(
            run_workspace,
            relative_path="evidence/reference_context.json",
            payload=_reference_context_workspace_payload(reference_context),
            kind="evidence",
            max_write_bytes=max_write_bytes,
        )
        for index, excerpt in enumerate(reference_context.reference_excerpts, start=1):
            run_workspace, _ = write_operation_flow_run_workspace_text(
                run_workspace,
                relative_path=f"references/reference-{index:03d}.txt",
                text=excerpt,
                kind="reference",
                max_write_bytes=max_write_bytes,
            )
    run_workspace, _ = write_operation_flow_run_workspace_text(
        run_workspace,
        relative_path="artifacts/terminal_display.txt",
        text=terminal_display_text + "\n",
        kind="artifact",
        max_write_bytes=max_write_bytes,
    )
    run_workspace, _ = write_operation_flow_run_workspace_json(
        run_workspace,
        relative_path="results/workflow_result.json",
        payload={
            "workflow": OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
            "status": status,
            "task_kind": facts.task_kind,
            "review_intents": list(facts.review_intents),
            "topic_hints": list(facts.topic_hints),
            "model_call_count": model_call_count,
            "fail_safe": fail_safe,
            "review_template_version": OPERATION_FLOW_REFERENCE_REVIEW_TEMPLATE_VERSION,
            "reference_context_status": reference_context.status,
            "reference_evidence_refs": list(reference_context.evidence_refs),
        },
        kind="result",
        max_write_bytes=max_write_bytes,
    )
    run_workspace = finalize_operation_flow_run_workspace(
        run_workspace,
        status=status,
        metadata={
            "workflow": OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
            "model_call_count": model_call_count,
            "fail_safe": fail_safe,
            "review_template_version": OPERATION_FLOW_REFERENCE_REVIEW_TEMPLATE_VERSION,
        },
    )
    run_workspace, _ = cleanup_operation_flow_run_workspace(run_workspace, status=status)
    return run_workspace


def _finalize_task_context_with_run_workspace(
    task_context: OperationFlowRunContextCandidate,
    *,
    status: str,
    run_workspace: OperationFlowRunWorkspaceStateCandidate | None,
    metadata: Mapping[str, Any] | None = None,
) -> OperationFlowRunContextCandidate:
    return finalize_operation_flow_run_context(
        task_context,
        status=status,
        artifact_refs=_run_workspace_artifact_and_result_refs(run_workspace),
        evidence_refs=run_workspace.evidence_refs if run_workspace else (),
        workspace_ref=run_workspace.workspace_ref if run_workspace else None,
        workspace_created=run_workspace.workspace_created if run_workspace else None,
        retention_policy=run_workspace.retention_policy if run_workspace else None,
        cleanup_policy=run_workspace.cleanup_policy if run_workspace else None,
        workspace_metadata=operation_flow_run_workspace_status_dict(run_workspace),
        metadata=metadata,
    )


def _task_context_metadata(task_context: OperationFlowRunContextCandidate) -> dict[str, Any]:
    return {"operation_control": operation_flow_run_context_status_dict(task_context)}


def _run_workspace_metadata(
    run_workspace: OperationFlowRunWorkspaceStateCandidate | None,
) -> dict[str, Any]:
    status = operation_flow_run_workspace_status_dict(run_workspace)
    return {"run_workspace": status} if status is not None else {}


def _reference_context_metadata(
    reference_context: OperationFlowReferenceReviewContextCandidate,
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
            "external_readonly_evidence_context": (
                reference_context.metadata.get("external_readonly_evidence_context")
            ),
        }
    }


def _reference_context_workspace_payload(
    reference_context: OperationFlowReferenceReviewContextCandidate,
) -> dict[str, Any]:
    tool_loading_gate = reference_context.metadata.get("tool_loading_gate")
    return {
        "status": reference_context.status,
        "requested_references": list(reference_context.requested_references),
        "consumed_reference_count": reference_context.consumed_reference_count,
        "evidence_refs": list(reference_context.evidence_refs),
        "blocking_reasons": list(reference_context.blocking_reasons),
        "warnings": list(reference_context.warnings),
        "reference_labels": list(reference_context.metadata.get("reference_labels", ())),
        "tool_loading_gate": (
            dict(tool_loading_gate) if isinstance(tool_loading_gate, Mapping) else None
        ),
        "read_statuses": list(reference_context.metadata.get("read_statuses", ())),
        "external_readonly_evidence_context": (
            reference_context.metadata.get("external_readonly_evidence_context")
        ),
    }


def _run_workspace_artifact_and_result_refs(
    run_workspace: OperationFlowRunWorkspaceStateCandidate | None,
) -> tuple[str, ...]:
    if run_workspace is None:
        return ()
    return (*run_workspace.artifact_refs, *run_workspace.result_refs)


def _preflight_blocked_terminal_display(
    task_context: OperationFlowRunContextCandidate,
) -> str:
    reasons = ", ".join(task_context.preflight.blocking_reasons)
    return "\n".join(
        [
            "task reference review workflow 已被 preflight 阻止。",
            f"run_id: {task_context.run_id}",
            f"blocking_reasons: {reasons or 'unknown'}",
            "未读取资料，未调用模型。",
        ]
    )


def _workspace_blocked_terminal_display(
    task_context: OperationFlowRunContextCandidate,
    run_workspace: OperationFlowRunWorkspaceStateCandidate,
) -> str:
    reasons = ", ".join(run_workspace.blocking_reasons)
    return "\n".join(
        [
            "task run workspace 已阻止本轮执行。",
            f"run_id: {task_context.run_id}",
            f"blocking_reasons: {reasons or 'unknown'}",
            "未读取资料，未调用模型。",
        ]
    )


def _reference_blocked_terminal_display(
    task_context: OperationFlowRunContextCandidate,
    reference_context: OperationFlowReferenceReviewContextCandidate,
) -> str:
    reasons = ", ".join(reference_context.blocking_reasons)
    return "\n".join(
        [
            "task reference review workflow 的 reference reader 已阻止本轮执行。",
            f"run_id: {task_context.run_id}",
            f"blocking_reasons: {reasons or 'unknown'}",
            "未调用模型，未展示未脱敏资料全文。",
        ]
    )


def _failed_terminal_display(
    reference_context: OperationFlowReferenceReviewContextCandidate,
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


def _external_readonly_evidence_ref_lines(
    reference_context: OperationFlowReferenceReviewContextCandidate,
) -> list[str]:
    summaries = _external_readonly_evidence_summaries(reference_context)
    lines: list[str] = []
    for index, summary in enumerate(summaries, start=1):
        evidence_ref = _mapping_text(summary, "evidence_ref")
        source_url = _mapping_text(summary, "source_url")
        archive_path = _mapping_text(summary, "evidence_output_path")
        if not evidence_ref:
            continue
        details = "；".join(
            item
            for item in (
                f"source_url={source_url}" if source_url else "",
                f"archive={archive_path}" if archive_path else "",
            )
            if item
        )
        suffix = f"（{details}）" if details else ""
        lines.append(f"external-readonly-{index}：{evidence_ref}{suffix}")
    return lines


def _external_readonly_evidence_summary_lines(
    reference_context: OperationFlowReferenceReviewContextCandidate,
) -> list[str]:
    summaries = _external_readonly_evidence_summaries(reference_context)
    if not summaries:
        return []
    lines: list[str] = []
    for index, summary in enumerate(summaries, start=1):
        source_url = _mapping_text(summary, "source_url") or "unknown"
        evidence_ref = _mapping_text(summary, "evidence_ref") or "unknown"
        content_hash = _mapping_text(summary, "content_hash") or "unknown"
        archive_path = _mapping_text(summary, "evidence_output_path") or "unknown"
        preview = _preview_text(
            _mapping_text(summary, "sanitized_excerpt_preview"),
            220,
        )
        total_excerpt_chars = summary.get("total_excerpt_chars")
        total_text = (
            f"{total_excerpt_chars}"
            if isinstance(total_excerpt_chars, int)
            else "unknown"
        )
        lines.extend(
            (
                f"{index}. source_url: {source_url}",
                f"   evidence_ref: {evidence_ref}",
                f"   archive: {archive_path}",
                f"   content_hash: {content_hash}",
                f"   total_excerpt_chars: {total_text}",
                f"   sanitized_excerpt_preview: {preview or '未提供脱敏摘要预览'}",
                (
                    "   边界: 仅展示已归档脱敏摘要；reference-review 本轮未联网、"
                    "未上传、未展示 raw response / raw HTML / response headers。"
                ),
            )
        )
    return lines


def _external_readonly_evidence_summaries(
    reference_context: OperationFlowReferenceReviewContextCandidate,
) -> tuple[Mapping[str, Any], ...]:
    context = reference_context.metadata.get("external_readonly_evidence_context")
    if not isinstance(context, Mapping):
        return ()
    if context.get("status") != "ready":
        return ()
    raw_summaries = context.get("summaries")
    if not isinstance(raw_summaries, Sequence) or isinstance(raw_summaries, str):
        return ()
    return tuple(
        summary for summary in raw_summaries if isinstance(summary, Mapping)
    )


def _mapping_text(mapping: Mapping[str, Any], key: str) -> str:
    value = mapping.get(key)
    return _compact_text(value) if isinstance(value, str) else ""


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
